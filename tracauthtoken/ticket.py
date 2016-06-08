# -*- coding: utf-8 -*-

from trac.core import *
from trac.web.chrome import add_warning
from trac.ticket.api import TicketSystem
from trac.ticket.notification import TicketNotifyEmail
from trac.ticket.model import Milestone, Ticket


__all__ = ['TicketRPC']


class TicketRPC(Component):
    """ An interface to Trac's ticketing system. """

    def create(self, req, summary, description, attributes={}, notify=False, when=None):
        """ Create a new ticket, returning the ticket ID.
        Overriding 'when' requires admin permission. """
        t = model.Ticket(self.env)
        t['summary'] = summary
        t['description'] = description
        t['reporter'] = req.authname
        for k, v in attributes.iteritems():
            t[k] = v
        t['status'] = 'new'
        t['resolution'] = ''
        # custom create timestamp?
        when = when or getattr(req, NAME_RPC_TIMESTAMP, None)
        if when and not 'TICKET_ADMIN' in req.perm:
            self.log.warn("RPC ticket.create: %r not allowed to create with "
                          "non-current timestamp (%r)", req.authname, when)
            when = None
        t.insert(when=when)
        if notify:
            try:
                tn = TicketNotifyEmail(self.env)
                tn.notify(t, newticket=True)
            except Exception, e:
                self.log.exception("Failure sending notification on creation "
                                   "of ticket #%s: %s" % (t.id, e))
        return t.id
