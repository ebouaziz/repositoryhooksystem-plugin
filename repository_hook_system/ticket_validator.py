#from genshi.builder import tag
from repository_hook_system.interface import IRepositoryHookSubscriber
from repository_hook_system.trac_commit_hook import CommitHook
from trac.config import BoolOption, Option, IntOption
from trac.core import Component, implements
from trac.ticket.api import ITicketManipulator
from trac.util.translation import tag_

"""
def validate_ticket(ticket):
    if ticket['status'] == 'closed':
        for c in forbidden_components_on_close:
            if ticket['component'] == c:
                yield 'component', tag_('Fix ticket component before closing')
        for m in forbidden_milestones_on_close:
            if ticket['milestone'] == m:
                yield 'milestone', tag_('Fix ticket milestone before closing')
"""

class TicketChangeValidator(Component):
    #implements(ITicketManipulator, IRepositoryHookSubscriber)
    implements(ITicketManipulator)

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
        if ticket['status'] == 'closed' and \
                not req.perm.has_permission('TICKET_ADMIN'):
            if ticket['component'] in self._fbden_cp_on_close:
                yield 'component', tag_('Fix ticket component before closing')
            if ticket['milestone'] in self._fbden_ms_on_close:
                yield 'milestone', tag_('Fix ticket milestone before closing')

    """
    # IRepositoryHookSubscriber implementation
    def is_available(self, repository, hookname):
        return (hookname == 'pre-commit')

    def invoke(self, project, repository, user, transaction, **kwargs):
        PreCommitHook(self.env, project=project, rev=None,
                      txn=transaction, rep=repository)
    """

"""
class PreCommitHook(CommitHook):

    def finalize(self, result):
        if OK == result:
            self._update_log(self.log)
        raise HookStatus(result)

    def _cmd_closes(self, ticket_id):
        # simulate ticket close and call validator
        ticket = Ticket(self.env, ticket_id)
        ticket['status'] = 'closed'
        ticket['resolution'] = 'fixed'

        for f, m in validate_ticket(ticket):
            print >> sys.stderr, m
            self.finalize(ERROR)
        return OK
"""
"""
def toto(self):
    field = 'reporter'
    yield None, tag_("A ticket with the summary %(summary)s"
                     " already exists.",
                      summary=tag.em("Testing ticket manipulator"))
    yield field, tag_("The ticket %(field)s is %(status)s.",
                      field=tag.strong(field),
                      status=tag.em("invalid"))
"""
