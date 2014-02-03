"""
interfaces for listening to repository changes
and configuration of hooks
"""

from trac.core import Interface

# interfaces for subscribers


class IRepositoryHookSubscriber(Interface):

    """
    interface for subscribers to repository hooks
    """

    def is_available(repository, hookname):
        """can this subscriber be invoked on this hook?"""

    def invoke(**kwargs):
        """what to do on a commit"""

# interfaces for the hook system


class IRepositoryChangeListener(Interface):

    """listeners to changes from repository hooks"""

    def type():
        """list of types of repository to listen for changes"""

    def available_hooks():
        """hooks available for the repository"""

    def subscribers(hookname):  # XXX needed? -> elsewhere?
        """returns activated subscribers for a given hook"""
        # XXX this should probably be moved, as it puts
        # the burden of knowing the subscriber on essentially
        # the repository.  This is better done in infrastructure
        # outside the repository;
        # or maybe this isn't horrible if an abstract base class
        # is used for this interface

    def invoke_hook(repo, hookname, *args):
        """fires the given hook"""


class IRepositoryHookAdminContributer(Interface):

    """
    contributes to the webadmin panel for the RepositoryHookSystem
    """
    # XXX there should probably an equivalent on the level of
    # IRepositoryHookSubscribers

    def render(hookname, req):
        """extra HTML to display in the webadmin panel for the hook"""


class IRepositoryHookSystem(IRepositoryChangeListener):

    """
    mixed-in interface for a complete hook system;
    implementers should be able to listen for changes (IRepositoryChangeListener)
    as well as setup the hooks (IRepositoryHookSetup)
    and contribute to the webadmin interface (IRepositoryHookAdminContributer)
    """
