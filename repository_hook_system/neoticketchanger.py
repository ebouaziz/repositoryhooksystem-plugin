"""
annotes and closes tickets based on an SVN commit message;
port of http://trac.edgewall.org/browser/trunk/contrib/trac-post-commit-hook
"""

from repository_hook_system.interface import IRepositoryHookSubscriber
from repository_hook_system.trac_commit_hook import (PostCommitHook,
                                                     PreCommitHook)
from repository_hook_system.trac_revprop_hook import RevpropHook
from trac.core import *
import sys


# Revision property change hooks
class PreRevPropChange(Component):

    """annotes and closes tickets on repository commit messages"""

    implements(IRepositoryHookSubscriber)

    def is_available(self, repository, hookname):
        """
        Verify if hook name is valid.

        :param repository: repository type
        :param hookname: hook name
        """
        return (hookname == 'pre-revprop-change')

    def invoke(self, project, revision, propname,
               action, user, repository, **kwargs):

        # grab the first line from stdin (we don't care about other lines for
        # new)
        value = sys.stdin.readline()

        RevpropHook(self.env, None, project, revision, propname, value,
                    action, user, repository)


class PostRevPropChange(Component):

    """annotes and closes tickets on repository commit messages"""

    implements(IRepositoryHookSubscriber)

    def is_available(self, repository, hookname):
        """
        Verify if hook name is valid.

        :param repository: repository type
        :param hookname: hook name
        """
        return (hookname == 'post-revprop-change')

    def invoke(self, project, revision, propname,
               action, user, repository, **kwargs):

        # grab the first line from stdin (we don't care about other lines for
        # new)
        value = sys.stdin.readline()

        RevpropHook(self.env, True, project, revision, propname, value,
                    action, user, repository)


# Commit hooks
class PreCommit(Component):

    """annotes and closes tickets on repository commit messages"""

    implements(IRepositoryHookSubscriber)

    def is_available(self, repository, hookname):
        """
        Verify if hook name is valid.

        :param repository: repository type
        :param hookname: hook name
        """
        return (hookname == 'pre-commit')

    def invoke(self, project, repository, user, transaction, **kwargs):
        """
        Invoke by hook system on pre_commit operation

        :param project: Project path, Trac env project
        :param repository: repository path
        :param user: author of the modification
        :param transaction: transaction name for pre_commit
        """
        PreCommitHook(self.env,
                      project=project,
                      rev=None,
                      txn=transaction,
                      rep=repository)


class PostCommit(Component):

    """annotes and closes tickets on repository commit messages"""

    implements(IRepositoryHookSubscriber)

    def is_available(self, repository, hookname):
        """
        Verify if hook name is valid.

        :param repository: repository type
        :param hookname: hook name
        """
        return (hookname == 'post-commit')

    def invoke(self, project, repository, user, revision, **kwargs):
        """
        Invoke by hook system on post_commit operation

        :param project: Project path, Trac env project
        :param repository: repository path
        :param user: author of the modification
        :param revision: revision for post_commit
        """
        PostCommitHook(self.env,
                       project=project,
                       rev=revision,
                       txn=None,
                       rep=repository)
