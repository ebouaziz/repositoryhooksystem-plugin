from repository_hook_system.interface import IRepositoryHookSubscriber
from repository_hook_system.trac_commit_hook import CommitHook
from trac.config import BoolOption, Option
from trac.core import Component, implements
from trac.ticket.api import ITicketManipulator
from trac.util.translation import tag_


class TicketChangeValidator(Component):
    #implements(ITicketManipulator, IRepositoryHookSubscriber)
    implements(ITicketManipulator)

    # TODO: get ldap parameters from [ldap] section
    LDAP_URL = 'ldap://ldap.neotion.pro'
    LDAP_BASE_DN = 'dc=neotion,dc=com'
    LDAP_PEOPLE = 'ou=people'
    ALLOWED_USERS = ('< default >',)

    enforce_valid_ldap_user = BoolOption('ticket',
        'enforce_valid_ldap_user', False,
        """Whether to enforce reporter and owner to be valid ldap users""")
    forbidden_milestones_on_close = Option('ticket',
        'forbidden_milestones_on_close', 'Next',
        """A ticket cannot be closed if its milestone is in that list""")
    forbidden_components_on_close = Option('ticket',
        'forbidden_components_on_close', 'Triage, None',
        """A ticket cannot be closed if its component is in that list""")

    def __init__(self):
        super(TicketChangeValidator, self).__init__()
        self._fbden_cp_on_close = [
            c.strip() for c in self.forbidden_components_on_close.split(',')]
        self._fbden_ms_on_close = [
            m.strip() for m in self.forbidden_milestones_on_close.split(',')]

    # ITicketManipulator implementation
    def prepare_ticket(self, req, ticket, fields, actions):
        pass

    def validate_ticket(self, req, ticket):
        self.env.log.debug('    ticket.values: %s' % ticket.values)
        self.env.log.debug('    ticket._old: %s' % ticket._old)
        # check that the component and milestone are not in the forbidden list
        # when the ticket is closed
        if ticket['status'] == 'closed' and \
                not req.perm.has_permission('TICKET_ADMIN'):
            if ticket['component'] in self._fbden_cp_on_close:
                yield 'component', tag_('Fix ticket component before closing')
            if ticket['milestone'] in self._fbden_ms_on_close:
                yield 'milestone', tag_('Fix ticket milestone before closing')

        if self.enforce_valid_ldap_user:
            self.env.log.debug('    checking users')
            import ldap
            # check that the reporter and owner are valid LDAP users

            # connect to the ldap server
            con = ldap.initialize(self.LDAP_URL)
            con.simple_bind_s()

            for field in ('reporter', 'owner'):
                self.env.log.debug('    checking ticket %s' % field)
                if field not in ticket.values:
                    self.env.log.debug('        not filled yet')
                    continue
                user = ticket.values[field]
                self.env.log.debug('      user is %s' % user)
                if user in self.ALLOWED_USERS:
                    self.env.log.debug('        allowed special value')
                    continue
                if ticket.exists and field not in ticket._old:
                    self.env.log.debug('      nothing new')
                    # case of a ticket modification and user unchanged
                    # the user can be a former employee
                    base_dn = self.LDAP_BASE_DN
                else:
                    self.env.log.debug('      ticket creation or value edit')
                    # case of ticket creation or modification of the user
                    # a current employee should be assigned
                    base_dn = ','.join((self.LDAP_PEOPLE, self.LDAP_BASE_DN))

                # user must have an email and a givenname (to discard non-human)
                filter_ = '(&(mail=%s@neotion.com)(givenname=*))' % user

                self.env.log.debug('      base_dn: %s' % base_dn)
                self.env.log.debug('      filter_: %s' % filter_)
                # send request
                res = con.search_s(base_dn, ldap.SCOPE_SUBTREE,
                                   filter_, ['uid'])
                # report issue if any
                if not res:
                    self.env.log.debug('      bad value, warning issued')
                    yield (field,
                           tag_("'%s' is not a valid user" % user))
