# -*- coding: utf-8 -*-

"""
web_ui.py - Advanced Access Token Generator Plugin for Trac

This module defines a Trac extension point for generating access tokens backend.

See TracTracAccessTokenBackend for more details.
"""

import itertools
from operator import itemgetter
import pkg_resources
import re

try:
    import simplejson as json
except ImportError:
    import json

from trac.perm import IPermissionRequestor
from trac.ticket.api import ITicketChangeListener
from trac.web.chrome import INavigationContributor
from trac.web.chrome import ITemplateProvider
from trac.web.main import IRequestHandler
from trac.prefs import IPreferencePanelProvider

from genshi.builder import tag, Element
from trac.core import Component
from trac.core import ExtensionPoint
from trac.core import implements
from trac.mimeview import Context
from trac.perm import PermissionSystem
from trac.perm import IPermissionGroupProvider
from trac.util.html import html
from trac.util.presentation import Paginator
from trac.util.translation import _
from trac.web.chrome import add_stylesheet, add_warning, add_script, add_notice
from trac.wiki.formatter import extract_link
from trac.util.datefmt import to_utimestamp, datetime_now, utc

import operator
import hashlib
import pprint

PACKAGE = 'tracaccesstoken'
CONFIG_SECTION_NAME = 'access_token_plugin'
CONFIG_FIELD = {
    'menu_label': (
        CONFIG_SECTION_NAME,
        'menu_label',
        'Access Tokens',
    ),
    'ticket_status': (
        CONFIG_SECTION_NAME,
        'ticket_status',
        'new, accepted, assigned, reopened, closed',
    ),
    'ticket_status_enable': (
        CONFIG_SECTION_NAME,
        'ticket_status_enable',
        'new, accepted, assigned, reopened, closed',
    ),
    'insensitive_group': (
        CONFIG_SECTION_NAME,
        'insensitive_group',
        'intern,outsourcing',
    ),
    'sensitive_keyword': (
        CONFIG_SECTION_NAME,
        'isensitive_keyword',
        'secret',
    ),
}
# --- any() from Python 2.5 ---
try:
    from __builtin__ import any
except ImportError:
    def any(items):
        for item in items:
            if item:
                return True
        return False

# ---all() from Python 2.5 ---
try:
    from __builtin__ import all
except ImportError:
    def all(items):
        return reduce(operator.__and__, items)

__all__ = ("any", "all")


def _get_config_values(config, option_name):
    values = config.get(*CONFIG_FIELD[option_name])
    return [value.strip() for value in values.split(',')]


class AccessTokenBackendException(Exception):
    """
    Raised by Access Token Backends when there is a problem generating the access token.
    """


class AccessTokenBackendPlugin(Component):
    implements(
        # INavigationContributor,
        # IPermissionRequestor,
        # IRequestHandler,
        ITemplateProvider,
        IPreferencePanelProvider
    )

    group_providers = ExtensionPoint(IPermissionGroupProvider)

    # IPermissionRequestor methods
    def get_permission_actions(self):
        return ['SEARCH_VIEW']

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        return [('tracaccesstoken', pkg_resources.resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return [pkg_resources.resource_filename(__name__, 'templates')]

    # IPreferencePanelProvider methods
    def get_preference_panels(self, req):
        """
        Implement IPreferencePanelProvider.get_preference_panels method

        Add access token entry in Preferences
        """
        label = self.config.get(*CONFIG_FIELD['menu_label'])
        yield ('accesstoken', label)

    def render_preference_panel(self, req, panel):
        """
        Implement IPreferencePanelProvider.render_preference_panel method

        Add request handler for accesstoken POST request
        """

        add_stylesheet(req, PACKAGE + '/css/advsearch.css')
        add_script(req, PACKAGE + '/js/hat.js')
        add_script(req, PACKAGE + '/js/advsearch.js')

        self.log.debug(req.method);
        content_type = req.get_header('Content-Type') or 'application/json'
        new_token = []
        action = req.args.get('action')
        token_id = req.args.get('token_id')

        if req.args.get('tokens'):
            new_token = json.loads(req.args.get('tokens'))

        if action == 'POST':
            if content_type == 'text/html':
                new_token = req.args.get('tokens')
                if new_token:
                    tokens = json.loads(new_token)
                    with self.env.db_transaction as db:
                        for t in tokens:
                            db(
                                "INSERT INTO kkbox_trac_access_token ("
                                "username, access_token, description, change_time, create_time) "
                                "VALUES (%s,%s,%s,%s,%s)",
                                (req.perm.username,
                                 hashlib.sha224(t['accessToken']).hexdigest(),
                                 t['description'],
                                 datetime_now(utc),
                                 datetime_now(utc)))
                    self.env.log.info("New access token for %s", req.perm.username)
                    add_notice(req, _('Your access tokens have been saved.'))
            else:
                # Read request body
                #content_len = int(req.get_header('content-length') or 0)
                new_token = {
                    'accessToken': req.args.get('accessToken'),
                    'description': req.args.get('description'),
                }
                if new_token:
                    with self.env.db_transaction as db:
                        c = db.cursor()
                        t = new_token
                        db(
                            "INSERT INTO kkbox_trac_access_token ("
                            "username, access_token, description, change_time, create_time) "
                            "VALUES (%s,%s,%s,%s,%s)",
                            (req.perm.username,
                             hashlib.sha224(t['accessToken']).hexdigest(),
                             t['description'],
                             datetime_now(utc),
                             datetime_now(utc)))
                    self.env.log.info("New access token for %s at %s" %
                                      (req.perm.username, datetime_now(utc)))
        elif action == 'DELETE':
            if 'token_id' in req.query_string:
                with self.env.db_transaction as db:
                    db("""DELETE FROM kkbox_trac_access_token
                          WHERE id=%s""", (token_id,))
                self.env.log.info("Delete access token id=%s", token_id)

        elif action == 'PUT':
            if 'token_id' in req.query_string:
                body = req.args.get('description')
                change_time = datetime_now(utc)
                with self.env.db_transaction as db:
                    db("""UPDATE kkbox_trac_access_token
                          SET description=%s,
                              change_time=%s
                          WHERE id=%s""", (body, change_time, token_id, ))
                    self.env.log.info("Update access token for %s id=%s at %s" %
                                      (req.perm.username, token_id, change_time))
        else:
            def _from_database(id_, access_token, description_, create_time):
                return {
                    'id': id_,
                    'accessToken': access_token,
                    'description': description_,
                    'creationTime': create_time
                }

            for row in self.env.db_query("""
                SELECT id AS id_, access_token, description, create_time
                FROM kkbox_trac_access_token
                WHERE username=%s
                ORDER BY create_time DESC
                """, (req.perm.username,)):
                new_token.append(_from_database(*row))
            new_token = json.dumps(new_token)
            self.env.log.info("New access token for %s", new_token)
        return 'prefs_tokens.html', {
            'tokens': new_token
        }
