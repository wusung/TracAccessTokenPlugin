# -*- coding: utf-8 -*-

"""
web_ui.py - Advanced Access Token Generator Plugin for Trac

This module defines a Trac extension point for generating access tokens backend.

See TracTracAccessTokenBackend for more details.
"""

import pkg_resources

try:
    import simplejson as json
except ImportError:
    import json

from trac.web.chrome import ITemplateProvider
from trac.prefs import IPreferencePanelProvider

from trac.core import Component
from trac.core import ExtensionPoint
from trac.core import implements
from trac.perm import IPermissionGroupProvider
from trac.util.translation import _
from trac.web.chrome import add_stylesheet, add_script, add_notice
from trac.util.datefmt import datetime_now, utc

import operator
import hashlib

PACKAGE = 'tracaccesstoken'
CONFIG_SECTION_NAME = 'auth_token_plugin'
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

        content_type = req.get_header('Content-Type') or 'application/json'
        new_token = []
        if req.method == 'POST':
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
                                (req.authname,
                                 hashlib.sha224(t['accessToken']).hexdigest(),
                                 t['description'],
                                 datetime_now(utc),
                                 datetime_now(utc)))
                    self.env.log.info("New access token for %s", req.authname)
                    add_notice(req, _('Your access tokens have been saved.'))
            else:
                # Read request body
                content_len = int(req.get_header('content-length') or 0)
                new_token = json.loads(req.read(content_len))
                if new_token:
                    with self.env.db_transaction as db:
                        c = db.cursor()
                        t = new_token
                        db(
                            "INSERT INTO kkbox_trac_access_token ("
                            "username, access_token, description, change_time, create_time) "
                            "VALUES (%s,%s,%s,%s,%s)",
                            (req.authname,
                             hashlib.sha224(t['accessToken']).hexdigest(),
                             t['description'],
                             datetime_now(utc),
                             datetime_now(utc)))
                    self.env.log.info("New access token for %s at %s" %
                                      (req.authname, datetime_now(utc)))
        elif req.method == 'DELETE':
            if 'token_id' in req.query_string:
                token_id = req.query_string.replace('token_id=', '')
                with self.env.db_transaction as db:
                    db("""DELETE FROM kkbox_trac_access_token
                          WHERE id=%s""", (token_id,))
                self.env.log.info("Delete access token id=%s", token_id)

        elif req.method == 'PUT':
            if 'token_id' in req.query_string:
                token_id = req.query_string.replace('token_id=', '')
                content_len = int(req.get_header('content-length') or 0)
                body = json.loads(req.read(content_len))
                change_time = datetime_now(utc)
                with self.env.db_transaction as db:
                    db("""UPDATE kkbox_trac_access_token
                          SET description=%s,
                              change_time=%s
                          WHERE id=%s""", (body['description'], change_time, token_id, ))
                    self.env.log.info("Update access token for %s id=%s at %s" %
                                      (req.authname, token_id, change_time))
        elif req.method == 'GET':
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
                """, (req.authname,)):
                new_token.append(_from_database(*row))
            new_token = json.dumps(new_token)
            self.env.log.info("New access token for %s", new_token)
        return 'prefs_tokens.html', {
            'tokens': new_token
        }
