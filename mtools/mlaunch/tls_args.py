#!/usr/bin/env python3
"""TLS and SSL argument builders for mlaunch."""

# PyMongo stores these as True. Every other mapped option keeps its value.
_PYMONGO_TRUE_FLAGS = {
    'ssl': (
        'sslAllowInvalidCertificates',
        'sslAllowInvalidHostnames',
    ),
    'tls': (
        'tlsAllowInvalidCertificates',
        'tlsAllowInvalidHostnames',
    ),
}

# SSL names are the pre-4.2 spellings. TLS names are the client-side options
# that PyMongo accepts under a different key.
_PYMONGO_RENAMES = {
    'ssl': {
        'sslClientCertificate': 'tlsCertificateKeyFile',
        'sslClientPEMKeyPassword': 'tlsCertificateKeyFilePassword',
        'sslAllowInvalidCertificates': 'tlsAllowInvalidCertificates',
        'sslAllowInvalidHostnames': 'tlsAllowInvalidHostnames',
        'sslCAFile': 'tlsCAFile',
        'sslCRLFile': 'tlsCRLFile',
    },
    'tls': {
        'tlsClientCertificateKeyFile': 'tlsCertificateKeyFile',
        'tlsClientCertificateKeyFilePassword': 'tlsCertificateKeyFilePassword',
        'tlsAllowInvalidCertificates': 'tlsAllowInvalidCertificates',
        'tlsAllowInvalidHostnames': 'tlsAllowInvalidHostnames',
        'tlsCAFile': 'tlsCAFile',
        'tlsCRLFile': 'tlsCRLFile',
    },
}


class TlsArgsMixin(object):
    """Build mongod argv and PyMongo options from the TLS/SSL parsers."""

    def _get_ssl_server_args(self):
        return self._security_server_args('ssl')

    def _get_tls_server_args(self):
        return self._security_server_args('tls')

    def _get_ssl_pymongo_options(self, args):
        return self._security_pymongo_options(args, 'ssl')

    def _get_tls_pymongo_options(self, args):
        return self._security_pymongo_options(args, 'tls')

    def _security_server_args(self, prefix):
        """Join set TLS/SSL options into a mongod argument string."""
        s = ''
        server_args = getattr(self, '%s_server_args' % prefix)
        if not server_args:
            return s

        shared_args = getattr(self, '%s_args' % prefix)
        for parser in shared_args, server_args:
            for action in parser._group_actions:
                name = action.dest
                value = self.args.get(name)
                if value:
                    if value is True:
                        s += ' --%s' % (name,)
                    else:
                        s += ' --%s "%s"' % (name, value)

        return s

    def _security_pymongo_options(self, args, prefix):
        """Map parsed TLS/SSL options onto PyMongo client keyword names."""
        opts = {}
        server_args = getattr(self, '%s_server_args' % prefix)
        if not server_args:
            return opts

        renames = _PYMONGO_RENAMES[prefix]
        true_flags = _PYMONGO_TRUE_FLAGS[prefix]
        for action in server_args._group_actions:
            value = args.get(action.dest)
            if value:
                opts['tls'] = True
                # A set SSL server option implies this PyMongo flag.
                if prefix == 'ssl':
                    opts['tlsAllowInvalidCertificates'] = True

        shared_args = getattr(self, '%s_args' % prefix)
        client_args = getattr(self, '%s_client_args' % prefix)
        for parser in shared_args, client_args:
            for action in parser._group_actions:
                name = action.dest
                value = args.get(name)
                if value:
                    opts['tls'] = True
                    if name in renames:
                        renamed = renames[name]
                        if name in true_flags:
                            opts[renamed] = True
                        else:
                            opts[renamed] = value

        return opts
