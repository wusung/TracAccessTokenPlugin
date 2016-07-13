# -*- coding: utf-8 -*-

import hashlib
import json
import re

from datetime import datetime
from trac.core import *
from trac.web.chrome import add_warning
from trac.web.api import (
    RequestDone, HTTPUnsupportedMediaType, HTTPInternalError,
    HTTP_STATUS
)
from trac.web.main import IRequestHandler
from trac.web.chrome import (
    ITemplateProvider,
    INavigationContributor,
    add_stylesheet,
    add_script,
    add_ctxtnav
)
from trac.util import as_bool, get_reporter_id, lazy
from trac.util.datefmt import (
    datetime_now, format_date_or_datetime, from_utimestamp,
    get_date_format_hint, get_datetime_format_hint, parse_date, to_utimestamp,
    user_time, utc, to_timestamp, to_datetime
)
from trac.util.text import (
    exception_to_unicode, empty, is_obfuscated, shorten_line
)
from trac.web.chrome import (
    Chrome, INavigationContributor, ITemplateProvider,
    add_ctxtnav, add_link, add_notice, add_script, add_script_data,
    add_stylesheet, add_warning, auth_link, chrome_info_script, prevnext_nav,
    web_context
)
from trac.ticket.model import Milestone, Ticket
from trac.ticket.notification import TicketNotifyEmail

from tracaccesstoken.constants import NAME_RPC_TIMESTAMP

__all__ = ['TicketAPI']


class TicketAPI(Component):
    """ An interface to Trac's ticketing system. """
    implements(
        IRequestHandler,
        # ITemplateProvider,
        # INavigationContributor
    )

    # IRequestHandler methods
    def match_request(self, req):
        return re.match(r'/api/tickets', req.path_info) is not None

    def process_request(self, req):
        self._process_new_ticket_request(req)

    # Internal methods

    def _authorization(self, req):
        return req.args.get('Authorization') or req.get_header('Authorization')

    def _process_new_ticket_request(self, req):
        if req.method == 'POST':
            content_type = req.get_header('Content-Type') or 'application/json'

            if 'TICKET_CREATE' not in req.perm:
                content = {
                    'message': 'forbidden',
                    'description': "%s privileges are required to perform this operation. "
                                   "You don't have the required permissions." % 'TICKET_CREATE'
                }
                req.send_response(403)
                req.send_header('Content-Type', content_type)
                req.send_header('Content-Length', len(json.dumps(content)))
                req.end_headers()
                req.write(json.dumps(content))
                return None

            authorization = self._authorization(req)
            if not authorization:
                content = {
                    'message': 'Empty credentials',
                    'description': "The access token is incorrect."
                }
                req.send_response(401)
                req.send_header('Content-Type', content_type)
                req.send_header('Content-Length', len(json.dumps(content)))
                req.end_headers()
                req.write(json.dumps(content))
                return None
            else:
                access_token = str(authorization).replace('token ', '')
                authname = ''
                for username in self.env.db_query("""
                    SELECT username
                    FROM kkbox_trac_access_token
                    WHERE access_token=%s
                    ORDER BY create_time DESC
                    """, (hashlib.sha224(access_token).hexdigest(),)):
                    authname = username
                if not authname:
                    content = {
                        'message': 'Bad credentials',
                        'description': "The access token is incorrect."
                    }
                    req.send_response(401)
                    req.send_header('Content-Type', content_type)
                    req.send_header('Content-Length', len(json.dumps(content)))
                    req.end_headers()
                    req.write(json.dumps(content))
                    return None

            try:
                ticket_id = self._create(req, authname)
                content = {
                    'ticket_id': ticket_id
                }
                req.send_response(201)
            except ValueError as ex:
                self.log.error('_create() failed. %s', ex)
                content = {
                    'message': 'invalid_json_value',
                    'description': 'Invalid request body'
                }
                req.send_response(400)
            except Exception as ex:
                self.log.error('_create() failed. %s', ex)
                content = {
                    'message': 'invalid_json_value',
                    'description': 'Invalid request body'
                }
                req.send_response(400)

            # Build response
            req.send_header('Content-Type', content_type)
            req.send_header('Content-Length', len(json.dumps(content)))
            req.end_headers()
            req.write(json.dumps(content))
        else:
            pass

    def _create(self, req, authname_):
        """ Create a new ticket, returning the ticket ID.
        Overriding 'when' requires admin permission. """

        content_len = int(req.get_header('content-length') or 0)

        # Read request body
        post_body = json.loads(req.read(content_len))
        self.log.debug('BODY=%s' % post_body)

        # Prepare props
        summary = post_body['summary'] or ''
        description = ''
        author = post_body['author'] or authname_
        reporter = post_body['reporter'] or authname_
        attributes = {}
        for key, value in post_body.iteritems():
            attributes[key] = value
        notify = False
        when = None

        # Validate inputs
        if not summary:
            raise ValueError('Empty field. Field name = summary')
        if not author:
            raise ValueError('Empty field. Field name = author')

        # Prepare ticket
        t = Ticket(self.env)
        t['summary'] = summary
        t['description'] = description
        t['reporter'] = reporter
        for k, v in attributes.iteritems():
            t[k] = v
        t['status'] = 'new'
        t['resolution'] = ''
        # custom author?
        if author and not (req.authname == 'anonymous' or 'TICKET_ADMIN' in req.perm(t.resource)):
            # only allow custom author if anonymous is permitted or user is admin
            self.log.warn("RPC ticket.create: %r not allowed to change author "
                          "to %r for comment on #%d", req.authname, author, id)
            author = ''
        t['author'] = author or req.authname

        # custom create timestamp?
        when = when or getattr(req, NAME_RPC_TIMESTAMP, None)
        if when and 'TICKET_ADMIN' not in req.perm:
            self.log.warn("RPC ticket.create: %r not allowed to create with "
                          "non-current timestamp (%r)", req.authname, when)
            when = None
        when = when or to_datetime(None, utc)
        t.insert(when=when)
        if notify:
            try:
                tn = TicketNotifyEmail(self.env)
                tn.notify(t, newticket=True)
            except Exception, e:
                self.log.exception("Failure sending notification on creation "
                                   "of ticket #%s: %s" % (t.id, e))
        return t.id

    def _prepare_data(self, req, ticket, absurls=False):
        return {'ticket': ticket, 'to_utimestamp': to_utimestamp,
                'context': web_context(req, ticket.resource, absurls=absurls),
                'preserve_newlines': self.must_preserve_newlines,
                'emtpy': empty}

    def _prepare_fields(self, req, ticket, field_changes=None):
        context = web_context(req, ticket.resource)
        fields = []
        for field in ticket.fields:
            name = field['name']
            type_ = field['type']

            # ensure sane defaults
            field.setdefault('optional', False)
            field.setdefault('options', [])
            field.setdefault('skip', False)
            field.setdefault('editable', True)

            # enable a link to custom query for all choice fields
            if type_ not in ['text', 'textarea', 'time']:
                field['rendered'] = self._query_link(req, name, ticket[name])

            # per field settings
            if name in ('summary', 'reporter', 'description', 'owner',
                        'status', 'resolution', 'time', 'changetime'):
                field['skip'] = True
            elif name == 'milestone' and not field.get('custom'):
                milestones = [Milestone(self.env, opt)
                              for opt in field['options']]
                milestones = [m for m in milestones
                              if 'MILESTONE_VIEW' in req.perm(m.resource)]
                field['editable'] = milestones != []
                groups = group_milestones(milestones, ticket.exists
                                          and 'TICKET_ADMIN' in req.perm(ticket.resource))
                field['options'] = []
                field['optgroups'] = [
                    {'label': label, 'options': [m.name for m in milestones]}
                    for (label, milestones) in groups]
                milestone = Resource('milestone', ticket[name])
                field['rendered'] = render_resource_link(self.env, context,
                                                         milestone, 'compact')
            elif name == 'cc':
                cc_changed = field_changes is not None and 'cc' in field_changes
                if ticket.exists and \
                                'TICKET_EDIT_CC' not in req.perm(ticket.resource):
                    cc = ticket._old.get('cc', ticket['cc'])
                    cc_action, cc_entry, cc_list = self._toggle_cc(req, cc)
                    cc_update = 'cc_update' in req.args \
                                and 'revert_cc' not in req.args
                    field['edit_label'] = {
                        'add': _("Add to Cc"),
                        'remove': _("Remove from Cc"),
                        None: _("Cc")}[cc_action]
                    field['cc_action'] = cc_action
                    field['cc_entry'] = cc_entry
                    field['cc_update'] = cc_update
                    if cc_changed:
                        field_changes['cc']['cc_update'] = cc_update
                if cc_changed:
                    # normalize the new CC: list; also remove the
                    # change altogether if there's no real change
                    old_cc_list = self._cc_list(field_changes['cc']['old'])
                    new_cc_list = self._cc_list(field_changes['cc']['new']
                                                .replace(' ', ','))
                    if new_cc_list == old_cc_list:
                        del field_changes['cc']
                    else:
                        field_changes['cc']['new'] = ','.join(new_cc_list)

            # per type settings
            if type_ in ('radio', 'select'):
                if ticket.exists and field['editable']:
                    value = ticket[name]
                    options = field['options']
                    optgroups = []
                    for x in field.get('optgroups', []):
                        optgroups.extend(x['options'])
                    if value and \
                            (value not in options and
                                     value not in optgroups):
                        # Current ticket value must be visible,
                        # even if it's not among the possible values
                        options.append(value)
            elif type_ == 'checkbox':
                value = ticket[name]
                if value in ('1', '0'):
                    field['rendered'] = self._query_link(req, name, value,
                                                         _("yes") if value == '1' else _("no"))
            elif type_ == 'text':
                if field.get('format') == 'reference':
                    field['rendered'] = self._query_link(req, name,
                                                         ticket[name])
                elif field.get('format') == 'list':
                    field['rendered'] = self._query_link_words(context, name,
                                                               ticket[name])
            elif type_ == 'time':
                value = ticket[name]
                field['timevalue'] = value
                format = field.get('format', 'datetime')
                if isinstance(value, datetime):
                    field['edit'] = user_time(req, format_date_or_datetime,
                                              format, value)
                else:
                    field['edit'] = value or ''
                locale = getattr(req, 'lc_time', None)
                if format == 'date':
                    field['format_hint'] = get_date_format_hint(locale)
                else:
                    field['format_hint'] = get_datetime_format_hint(locale)

            fields.append(field)

        return fields

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
