# -*- coding: utf-8 -*-

import re
import json

from trac.core import *
from trac.web.chrome import add_warning
from trac.web.api import RequestDone
from trac.web.api import HTTPUnsupportedMediaType
from trac.web.api import HTTPInternalError
from trac.web.main import IRequestHandler
from trac.web.chrome import ITemplateProvider
from trac.web.chrome import INavigationContributor
from trac.web.chrome import add_stylesheet
from trac.web.chrome import add_script
from trac.web.chrome import add_ctxtnav

__all__ = ['RPCWeb']


class RPCWeb(Component):
    implements(
        IRequestHandler,
        # ITemplateProvider,
        # INavigationContributor
    )

    # IRequestHandler methods
    def match_request_old(self, req):
        """ Look for available protocols serving at requested path and
            content-type. """
        content_type = req.get_header('Content-Type') or 'text/html'
        must_handle_request = req.path_info in ('/ticket', '/login/rpc')
        for protocol in self.protocols:
            for p_path, p_type in protocol.rpc_match():
                if req.path_info in ['/%s' % p_path, '/login/%s' % p_path]:
                    must_handle_request = True
                    if content_type.startswith(p_type):
                        req.args['protocol'] = protocol
                        return True
        # No protocol call, need to handle for docs or error if handled path
        return must_handle_request

    def match_request(self, req):
        return re.match(r'/ticket', req.path_info) is not None

    def process_request(self, req):
        self._do_auth(req)

    def _do_auth(self, req):
        #if req.method == 'POST':
        content_type = req.get_header('Content-Type') or 'application/json'

        content = {
            'data': [{
                'name': 'test'
            }]
        }

        self.log.debug("%s" % json.dumps(content))
        req.send_response(201)
        req.send_header('Content-Type', content_type)
        req.send_header('Content-Length', len(json.dumps(content)))
        req.end_headers()
        req.write(json.dumps(content))

        #return None

    def process_request_old(self, req):
        if req.method == 'POST':
            content_type = req.get_header('Content-Type') or 'text/html'

        protocol = req.args.get('protocol', None)
        content_type = req.get_header('Content-Type') or 'text/html'
        if protocol:
            # Perform the method call
            self.log.debug("RPC incoming request of content type '%s' "
                           "dispatched to %s" % (content_type, repr(protocol)))
            self._rpc_process(req, protocol, content_type)
        elif accepts_mimetype(req, 'text/html') \
                or content_type.startswith('text/html'):
            return self._dump_docs(req)
        else:
            # Attempt at API call gone wrong. Raise a plain-text 415 error
            body = "No protocol matching Content-Type '%s' at path '%s'." % (
                content_type, req.path_info)
            self.log.error(body)
            req.send_error(None, template='', content_type='text/plain',
                           status=HTTPUnsupportedMediaType.code, env=None, data=body)
