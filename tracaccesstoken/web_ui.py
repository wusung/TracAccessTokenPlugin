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

import operator

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
        add_script(req, PACKAGE + '/js/advsearch.js')

        new_token = []
        if req.method == 'POST':
            new_token = req.args.get('tokens')
            if new_token:
                add_notice(req, _('Your access tokens have been saved.'))
        self.log.debug("*" * 30  + json.dumps(new_token))
        return 'prefs_tokens.html', {
            'tokens': new_token
        }
