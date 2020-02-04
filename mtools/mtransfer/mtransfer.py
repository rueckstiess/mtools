#!/usr/bin/env python

import argparse
import os
import re
import sys
import bson
import wiredtiger

from mtools.util.cmdlinetool import BaseCmdLineTool
from mtools.version import __version__

codec_options = bson.codec_options.CodecOptions(uuid_representation=bson.binary.STANDARD)


class MTransferTool(BaseCmdLineTool):
    def __init__(self):
        BaseCmdLineTool.__init__(self)

        self.argparser.description = ('Import and export databases between MongoDB deployments '
                                      'for WiredTiger storage with directoryPerDB configuration.')

        self.argparser.add_argument('--dbpath', dest='dbpath', default='.', nargs=1,
                                    help='MongoDB database path')

        self.argparser.add_argument('--force', action='store_true',
                                    help='ignore safety checks')

        self.argparser.add_argument('--verbose', action='store_true',
                                    help='enable verbose output')

        self.argparser.add_argument('command', choices=['export', 'import'])

        self.argparser.add_argument('database', nargs=1, type=str,
                                    help='name of the database to export / import')

    def run(self, arguments=None):
        BaseCmdLineTool.run(self, arguments)

        self.dbpath = self.args['dbpath'][0]
        self.force = self.args['force']
        self.verbose = self.args['verbose']

        # Read storage.bson, sanity check.
        try:
            storage_raw = open(os.path.join(self.dbpath, 'storage.bson'), 'rb').read()
        except Exception as e:
            sys.stderr.write('Failed to open storage.bson in "{0}": {1}\n'.format(self.dbpath, e))
            return

        settings = bson.decode(storage_raw)["storage"]["options"]
        if not settings["directoryPerDB"]:
            sys.stderr.write('Requires a database created with --directoryperdb\n')
            return
        if settings["directoryForIndexes"] or settings.get("groupCollections", False):
            sys.stderr.write('Incompatible storage settings detected: '
                             'directoryForIndexes or groupCollections\n')
            if not self.force:
                return

        self.database = self.args['database'][0]
        self.nsprefix = self.database + '.'

        mtransfer_dir = os.path.join(self.dbpath, self.database)
        mtransfer_file = os.path.join(mtransfer_dir, 'mtransfer.bson')

        if self.args['command'] == 'export':
            if not os.path.exists(mtransfer_dir):
                sys.stderr.write('Expected source directory "{0}" does not exist. '
                                 'Check the database name is correct.\n'.format(mtransfer_dir))
                return
            if not self.force and os.path.exists(mtransfer_file):
                sys.stderr.write('Output file "{0}" already exists\n'.format(mtransfer_file))
                return
            with open(mtransfer_file, 'wb') as outf:
                self.doExport(outf)
        elif self.args['command'] == 'import':
            if not os.path.exists(mtransfer_dir):
                sys.stderr.write('Expected target directory "{0}" does not exist. '
                                 'Check the database name is correct.\n'.format(mtransfer_dir))
                return
            if not os.path.exists(mtransfer_file):
                sys.stderr.write('Cannot import: mtransfer file "{0}" does not exist.\n'.
                                 format(mtransfer_file))
                return
            with open(mtransfer_file, 'rb') as inf:
                self.doImport(inf)

    def message(self, msg):
        if self.verbose:
            print(msg)

    def doExport(self, outf):
        # Attempt to connect to the specified WiredTiger database
        try:
            conn = wiredtiger.wiredtiger_open(
                self.dbpath,
                'log=(compressor=snappy,path=journal,recover=error),readonly=true')
        except Exception as e:
            sys.stderr.write('Failed to open dbpath "{0}": {1}\n'.format(self.dbpath, e))
            return

        session = conn.open_session()

        # Find all collections in the database
        catalog = session.open_cursor('table:_mdb_catalog')
        sizeStorer = session.open_cursor('table:sizeStorer')
        wtMeta = session.open_cursor('metadata:')
        wtMetaCreate = session.open_cursor('metadata:create')
        for _, meta_raw in catalog:
            meta = bson.decode(meta_raw, codec_options=codec_options)
            ns = meta[u'ns']
            if not ns or not ns.startswith(self.nsprefix):
                continue
            assert ns == meta[u'md'][u'ns']

            # Iterate through indexes first
            indexes = {}
            for idxName, idxIdent in meta[u'idxIdent'].items():
                ident = str('table:' + idxIdent)
                filename = ident[len('table:'):] + '.wt'
                file_ident = 'file:' + filename
                wtmeta_file = wtMeta[file_ident]
                wtmeta_table = wtMetaCreate[ident]
                basename = filename[len(self.nsprefix):]
                indexes[idxName] = {'filename': basename,
                                    'wtmeta_table': wtmeta_table,
                                    'wtmeta_file': wtmeta_file}

            collname = ns[len(self.nsprefix):]
            ident = str('table:' + meta[u'ident'])
            size = bson.decode(sizeStorer[ident.encode()])
            filename = ident[len('table:'):] + '.wt'
            file_ident = 'file:' + filename
            wtmeta_file = wtMeta[file_ident]
            wtmeta_table = wtMetaCreate[ident]
            basename = filename[len(self.nsprefix):]
            export = {
                'collname': collname,
                'filename': basename,
                'mdb_catalog': meta,
                'sizeStorer': size,
                'wtmeta_table': wtmeta_table,
                'wtmeta_file': wtmeta_file,
                'indexes': indexes,
                'version': __version__,
            }
            self.message(str(export))
            outf.write(bson.encode(export, codec_options=codec_options))

        conn.close()

    def doImport(self, inf):
        try:
            conn = wiredtiger.wiredtiger_open(
                self.dbpath,
                'log=(enabled=false,compressor=snappy,path=journal,recover=error)')
        except Exception as e:
            sys.stderr.write('Failed to open dbpath "{0}": {1}\n'.format(self.dbpath, e))
            return

        try:
            self._doImport(conn, inf)
        except Exception as e:
            sys.stderr.write('Import failed: {0}'.format(e))

        print('Import complete')

        conn.close()

    def _doImport(self, conn, inf):
        app_metadata_re = re.compile(r'app_metadata=\(.*?\)')

        session = conn.open_session()
        session.begin_transaction()

        catalog = session.open_cursor('table:_mdb_catalog')
        sizeStorer = session.open_cursor('table:sizeStorer')
        wtMeta = session.open_cursor('metadata:', None, 'readonly=false')

        # Get the maximum file ID in the WT catalog: we will be appending
        session.create('file:_mtransfer')
        newfile_meta = wtMeta['file:_mtransfer']
        self.message('Got new file metadata "{0}"'.format(newfile_meta))
        session.drop('file:_mtransfer')
        file_id = int(re.search(r',id=(\d+),', newfile_meta).group(1))

        # Get the maximum ID in the MDB catalog: we will be appending
        catalog.prev()
        maxID = catalog.get_key()

        for export in bson.decode_file_iter(inf, codec_options=codec_options):
            if not os.path.exists(
                    os.path.join(self.dbpath, self.database, export['filename'])):
                sys.stderr.write(
                    'File "{0}" referenced in export missing during import'.
                    format(export['filename']))
                if not self.force:
                    return

            if not self.force and export['version'] != __version__:
                sys.stderr.write(
                    'Database was exported with mtools version {0}, '
                    'current version {1} may not be compatible'.
                    format(export['version'], __version__))
                return

            # Figure out the new namespace
            ns = self.database + '.' + export['collname']

            # First process the indexes
            idxIdent = {}
            for idxName, idx in export['indexes'].items():
                ident = self.database + '/' + idx['filename'][:-3]
                table_uri = 'table:' + ident
                colgroup_uri = 'colgroup:' + ident
                file_uri = 'file:' + ident + '.wt'
                # Do a regular "session.create" for the table, then overwrite
                # the "file:" metadata with the original
                app_metadata = app_metadata_re.search(idx['wtmeta_file']).group(0)
                # For older style index metadata, update the namespace
                app_metadata = re.sub(r'"ns" : ".*?"', '"ns" : "{0}"'.format(ns), app_metadata)
                self.message('For index "{0}", app_metadata = "{1}"'.format(idxName, app_metadata))
                wtMeta[table_uri] = (app_metadata +
                                     ',colgroups=,collator=,columns=,key_format=u,value_format=u')
                wtMeta[colgroup_uri] = (app_metadata +
                                        ',collator=,columns=,source="' + file_uri + '",type=file')
                wtMeta[file_uri] = (idx['wtmeta_file'] + ',' + app_metadata +
                                    (',id={0:d}'.format(file_id)))
                file_id += 1
                idxIdent[idxName] = ident
                self.message('Adding index "{0}" with ident "{1}"'.format(idxName, ident))

            # Figure out the WT URIs
            ident = self.database + '/' + export['filename'][:-3]
            table_uri = 'table:' + ident
            colgroup_uri = 'colgroup:' + ident
            file_uri = 'file:' + ident + '.wt'

            # Do a regular "session.create" for the table, then overwrite the
            # "file:" metadata with the original
            app_metadata = app_metadata_re.search(export['wtmeta_file']).group(0)
            self.message('For collection "{0}", app_metadata = "{1}"'.format(ns, app_metadata))
            wtMeta[table_uri] = (app_metadata +
                                 ',colgroups=,collator=,columns=,key_format=q,value_format=u')
            wtMeta[colgroup_uri] = (app_metadata +
                                    ',collator=,columns=,source="' + file_uri + '",type=file')
            wtMeta[file_uri] = (export['wtmeta_file'] + ',' + app_metadata +
                                (',id={0:d}'.format(file_id)))
            file_id += 1

            sizeStorer[ident.encode()] = bson.encode(export['sizeStorer'])

            # Fix the catalog entry to refer to the new namespace and new table names
            catalog_entry = export['mdb_catalog']
            catalog_entry[u'ns'] = ns
            catalog_entry[u'md'][u'ns'] = ns
            catalog_entry[u'ident'] = ident
            catalog_entry[u'idxIdent'] = idxIdent
            for i in range(len(catalog_entry[u'md'][u'indexes'])):
                catalog_entry[u'md'][u'indexes'][i][u'spec'][u'ns'] = ns
            maxID += 1
            self.message('Adding catalog entry {0} -> {1}'.format(maxID, catalog_entry))
            catalog[maxID] = bson.encode(catalog_entry, codec_options=codec_options)

        session.commit_transaction()


def main():
    tool = MTransferTool()
    tool.run()
    return 0  # we need to return an integer


if __name__ == '__main__':
    sys.exit(main())
