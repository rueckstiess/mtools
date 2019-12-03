#!/usr/bin/env python

import argparse, os, re, sys
import bson, wiredtiger

from mtools.util.cmdlinetool import BaseCmdLineTool

codec_options = bson.codec_options.CodecOptions(uuid_representation=bson.binary.STANDARD)

class MTransferTool(BaseCmdLineTool):
    def __init__(self):
        BaseCmdLineTool.__init__(self)

        self.argparser.description = ('Imports and exports databases to/from MongoDB.')

        self.argparser.add_argument('--dbpath', dest='dbpath', default='.', nargs=1,
                                    help='MongoDB database path')

        self.argparser.add_argument('--verbose', action='store_true',
                                    help='enable verbose output')

        self.argparser.add_argument('command', choices=['export', 'import'])

        self.argparser.add_argument('database', nargs=1, type=str,
                                    help='name of the database to export / import')

    def run(self, arguments=None):
        BaseCmdLineTool.run(self, arguments)

        self.dbpath = self.args['dbpath']
        self.verbose = self.args['verbose']

        # Read storage.bson, sanity check.
        try:
            storage_raw = open(os.path.join(self.dbpath, 'storage.bson'), 'r').read()
        except Exception as e:
            sys.stderr.write('Failed to open storage.bson in "%s": %s\n' % (self.dbpath, e))
            return

        settings = bson.decode(storage_raw)["storage"]["options"]
        if not settings["directoryPerDB"]:
            sys.stderr.write('requires a database created with --directoryperdb\n')
            return
        if settings["directoryForIndexes"] or settings.get("groupCollections", False):
            sys.stderr.write('incompatible storage settings\n')
            return

        self.database = self.args['database'][0]
        self.nsprefix = self.database + '.'

        mtransfer_file = os.path.join(self.dbpath, self.database, 'mtransfer.bson')

        if self.args['command'] == 'export':
            if os.path.exists(mtransfer_file):
                sys.stderr.write('Output file "%s" already exists\n' % (mtransfer_file))
                return
            with open(mtransfer_file, 'w') as outf:
                self.doExport(outf)
        elif self.args['command'] == 'import':
            with open(mtransfer_file, 'r') as inf:
                self.doImport(inf)

    def message(self, msg):
        if self.verbose:
            print(msg)

    def doExport(self, outf):
        # Attempt to connect to the specified WiredTiger database
        try:
            conn = wiredtiger.wiredtiger_open(self.dbpath, 'log=(compressor=snappy,path=journal,recover=error),readonly=true')
        except Exception as e:
            sys.stderr.write('Failed to open dbpath "%s": %s\n' % (self.dbpath, e))
            return

        session = conn.open_session()

        # Find all collections in the database
        catalog = session.open_cursor('table:_mdb_catalog')
        sizeStorer = session.open_cursor('table:sizeStorer')
        wtMeta = session.open_cursor('metadata:')
        wtMetaCreate = session.open_cursor('metadata:create')
        for _, meta_raw in catalog:
            meta = bson.decode(meta_raw, codec_options = codec_options)
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
                indexes[idxName] = {'filename' : basename, 'wtmeta_table' : wtmeta_table, 'wtmeta_file' : wtmeta_file }

            collname = ns[len(self.nsprefix):]
            ident = str('table:' + meta[u'ident'])
            size = bson.decode(sizeStorer[ident])
            filename = ident[len('table:'):] + '.wt'
            file_ident = 'file:' + filename
            wtmeta_file = wtMeta[file_ident]
            wtmeta_table = wtMetaCreate[ident]
            basename = filename[len(self.nsprefix):]
            export = {'collname' : collname, 'filename' : basename, 'mdb_catalog' : meta, 'sizeStorer' : size, 'wtmeta_table' : wtmeta_table, 'wtmeta_file' : wtmeta_file, 'indexes' : indexes }
            self.message(str(export))
            outf.write(bson.encode(export, codec_options = codec_options))

        conn.close()

    def doImport(self, inf):
        try:
            conn = wiredtiger.wiredtiger_open(self.dbpath, 'log=(enabled,compressor=snappy,path=journal,recover=error)')
        except Exception as e:
            sys.stderr.write('Failed to open dbpath "%s": %s\n' % (self.dbpath, e))
            return
        
        try:
            self._doImport(conn, inf)
        except Exception as e:
            sys.stderr.write('Import failed: %s' % e)

        conn.close()

    def _doImport(self, conn, inf):
        app_metadata_re = re.compile(r'app_metadata=\(.*?\)')

        session = conn.open_session()
        session.begin_transaction()

        catalog = session.open_cursor('table:_mdb_catalog')
        sizeStorer = session.open_cursor('table:sizeStorer')
        wtMeta = session.open_cursor('metadata:', None, 'readonly=false')

        # Get the maximum ID in the catalog: we will be appending
        catalog.prev()
        maxID = catalog.get_key()

        # TODO: update the sizeStorer entry for _mdb_catalog
        mdb_size = bson.decode(sizeStorer['table:_mdb_catalog'])

        for export in bson.decode_file_iter(inf, codec_options = codec_options):
            if not os.path.exists(os.path.join(self.dbpath, self.database, export['filename'])):
                sys.stderr.write('File "%s" referenced in export missing during import' % (export['filename']))
                return

            # First process the indexes
            idxIdent = {}
            for idxName, idx in export['indexes'].items():
                ident = self.database + '/' + idx['filename'][:-3]
                table_uri = 'table:' + ident
                colgroup_uri = 'colgroup:' + ident
                file_uri = 'file:' + ident + '.wt'
                # Do a regular "session.create" for the table, then overwrite the "file:" metadata with the original
                app_metadata = app_metadata_re.search(idx['wtmeta_file']).group(0)
                self.message('For index "%s", app_metadata = "%s"' % (idxName, app_metadata))
                wtMeta[table_uri] = app_metadata + ',colgroups=,collator=,columns=,key_format=u,value_format=u'
                wtMeta[colgroup_uri] = app_metadata + ',collator=,columns=,source="' + file_uri + '",type=file'
                wtMeta[file_uri] = idx['wtmeta_file']
                idxIdent[idxName] = ident
                self.message('Adding index "%s" with ident "%s"' % (idxName, ident))
            
            # Figure out the new namespace and WT URIs
            ns = self.database + '.' + export['collname']
            ident = self.database + '/' + export['filename'][:-3]
            table_uri = 'table:' + ident
            colgroup_uri = 'colgroup:' + ident
            file_uri = 'file:' + ident + '.wt'

            # Do a regular "session.create" for the table, then overwrite the "file:" metadata with the original
            app_metadata = app_metadata_re.search(export['wtmeta_file']).group(0)
            self.message('For collection "%s", app_metadata = "%s"' % (ns, app_metadata))
            wtMeta[table_uri] = app_metadata + ',colgroups=,collator=,columns=,key_format=q,value_format=u'
            wtMeta[colgroup_uri] = app_metadata + ',collator=,columns=,source="' + file_uri + '",type=file'
            wtMeta[file_uri] = export['wtmeta_file']

            sizeStorer[ident] = bson.encode(export['sizeStorer'])

            # Fix the catalog entry to refer to the new namespace and new table names
            catalog_entry = export['mdb_catalog']
            catalog_entry[u'ns'] = ns
            catalog_entry[u'md'][u'ns'] = ns
            catalog_entry[u'ident'] = ident
            catalog_entry[u'idxIdent'] = idxIdent
            maxID += 1
            self.message('Adding catalog entry %d -> %s' % (maxID, catalog_entry))
            catalog[maxID] = bson.encode(catalog_entry, codec_options = codec_options)

        session.commit_transaction()

def main():
    tool = MTransferTool()
    tool.run()
    return 0  # we need to return an integer


if __name__ == '__main__':
    sys.exit(main())