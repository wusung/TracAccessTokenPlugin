# -*- coding: utf-8 -*-

import hashlib
import json
import re

from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.db import DatabaseManager
from trac.ticket.model import Milestone, Ticket
from trac.ticket.notification import TicketNotifyEmail
from trac.perm import PermissionSystem
from trac.perm import IPermissionGroupProvider
from trac.util.datefmt import (
    get_date_format_hint, get_datetime_format_hint, to_utimestamp,
    user_time, utc, to_datetime
)
from trac.web.main import IRequestHandler
from tracaccesstoken.constants import NAME_RPC_TIMESTAMP

import db_default

__all__ = ['TicketAPI']


NUMBERS_RE = re.compile(r'\d+', re.U)


class TicketAPI(Component):
    """ An interface to Trac's ticketing system. """
    implements(
        IRequestHandler,
        IEnvironmentSetupParticipant,
        # ITemplateProvider,
        # INavigationContributor
    )
    group_providers = ExtensionPoint(IPermissionGroupProvider)

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        self.found_db_version = 0
        self.upgrade_environment(self.env.get_db_cnx())

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        cursor.execute("SELECT value FROM system WHERE name=%s",
                       (db_default.name,))
        value = cursor.fetchone()
        try:
            self.found_db_version = int(value[0])
            if self.found_db_version < db_default.version:
                return True
        except:
            self.found_db_version = 0
            return True

        return False

    def upgrade_environment(self, db):
        db_manager, _ = DatabaseManager(self.env)._get_connector()

        # update the version
        old_data = {}  # {table.name: (cols, rows)}
        cursor = db.cursor()
        if not self.found_db_version:
            cursor.execute("INSERT INTO system (name, value) VALUES (%s, %s)",
                           (db_default.name, db_default.version))
        else:
            cursor.execute("UPDATE system SET value=%s WHERE name=%s",
                           (db_default.version, db_default.name))
            for table in db_default.tables:
                cursor.execute("SELECT * FROM " + table.name)
                cols = [x[0] for x in cursor.description]
                rows = cursor.fetchall()
                old_data[table.name] = (cols, rows)
                cursor.execute("DROP TABLE " + table.name)

        # insert the default table
        for table in db_default.tables:
            for sql in db_manager.to_sql(table):
                cursor.execute(sql)

            # add old data
            if table.name in old_data:
                cols, rows = old_data[table.name]
                sql = 'INSERT INTO %s (%s) VALUES (%s)' % \
                      (table.name, ','.join(cols), ','.join(['%s'] * len(cols)))
                for row in rows:
                    cursor.execute(sql, row)

    # IRequestHandler methods
    def match_request(self, req):
        return '/api/tickets' in req.path_info

    def process_request(self, req):
        self._process_new_ticket_request(req)

    # Internal methods

    @staticmethod
    def _authorization(req):
        return req.args.get('Authorization') or req.get_header('Authorization')

    def _process_new_ticket_request(self, req):
        if req.method == 'POST':
            content_type = req.get_header('Content-Type') or 'application/json'

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
                return
            else:
                access_token = str(authorization).replace('token ', '').strip()
                username = ''
                for username in self.env.db_query("""
                    SELECT username
                    FROM kkbox_trac_access_token
                    WHERE access_token=%s
                    ORDER BY create_time DESC
                    """, (hashlib.sha224(access_token).hexdigest(),)):
                    username = username[0]
                if not username:
                    content = {
                        'message': 'Bad credentials',
                        'description': "The access token is incorrect."
                    }
                    req.send_response(401)
                    req.send_header('Content-Type', content_type)
                    req.send_header('Content-Length', len(json.dumps(content)))
                    req.end_headers()
                    req.write(json.dumps(content))
                    return

            allow_create_ticket = 'TICKET_CREATE' in self._get_groups(username)
            if not allow_create_ticket:
                content = {
                    'message': 'forbidden',
                    'description': "%s privileges are required to perform this operation for %s. "
                                   "You don't have the required permissions." % ('TICKET_CREATE', username)
                }
                req.send_response(403)
                req.send_header('Content-Type', content_type)
                req.send_header('Content-Length', len(json.dumps(content)))
                req.end_headers()
                req.write(json.dumps(content))
                return

            try:
                ticket_id = self._create(req, username)
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
            return
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
        #author = post_body['author']
        #reporter = post_body['reporter'] or authname_
        attributes = {}
        for key, value in post_body.iteritems():
            attributes[key] = value
        author = ''
        if 'reporter' in post_body:
            author = post_body['reporter']
        notify = False
        when = None

        # Validate inputs
        if not summary:
            raise ValueError('Empty field. Field name = summary')
        #if not author:
        #    raise ValueError('Empty field. Field name = author')

        # Prepare ticket
        t = Ticket(self.env)
        t['summary'] = summary
        t['description'] = description
        for k, v in attributes.iteritems():
            t[k] = v
        t['status'] = 'new'
        t['resolution'] = ''

        # custom author?
        if author and not (authname_ == 'anonymous' or 'TICKET_ADMIN' in self._get_groups(authname_)):
            # only allow custom author if anonymous is permitted or user is admin
            self.log.warn("RPC ticket.create: %r not allowed to change author "
                          "to %r for comment on #%s", authname_, author, t['ticket_id'])
            author = ''

        t['reporter'] = author or authname_
        t['author'] = author or authname_

        # custom create timestamp?
        when = when or getattr(req, NAME_RPC_TIMESTAMP, None)
        if when and 'TICKET_ADMIN' not in self._get_groups(authname_):
            self.log.warn("RPC ticket.create: %r not allowed to create with "
                          "non-current timestamp (%r)", authname_, when)
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

    def _get_groups(self, user):
        self.log.debug(PermissionSystem(self.env).get_user_permissions(user))
        return PermissionSystem(self.env).get_user_permissions(user)
