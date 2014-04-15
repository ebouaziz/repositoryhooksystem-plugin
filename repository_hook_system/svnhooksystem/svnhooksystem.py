# -*- coding: utf-8 -*-

"""
implementation of the RepositoryChangeListener interface for svn
"""

from genshi.builder import tag
from repository_hook_system.interface import (IRepositoryChangeListener,
                                              IRepositoryHookAdminContributer,
                                              IRepositoryHookSubscriber)
from trac.core import *
from trac.util.text import exception_to_unicode
from trac.wiki.formatter import format_to_html
import os
import sys
import time


# from trac.config import ListOption

class SVNHookSystem(Component):
    """implementation of IRepositoryChangeListener for SVN repositories"""

    sync_timeout = 3.
    sync_delay = .2

    implements(IRepositoryChangeListener,
               IRepositoryHookAdminContributer)

    listeners = ExtensionPoint(IRepositoryHookSubscriber)
    hooks = ['pre-commit', 'post-commit',
             'pre-revprop-change', 'post-revprop-change']

    def filename(self, hookname):
        location = self.env.config.get('trac', 'repository_dir')
        return os.path.join(location, 'hooks', hookname)

    ### methods for IRepositoryHookAdminContributer
    def render(self, hookname, req):
        filename = self.filename(hookname)

        def safe_wiki_to_html(context, text):
            try:
                return format_to_html(self.env, context, text)
            except Exception, e:
                self.log.error('Unable to render component documentation: %s',
                               exception_to_unicode(e, traceback=True))
                return tag.pre(text)
        try:
            contents = file(filename).read()  # check for CRLF here too?
            return tag.textarea(contents, rows='25', cols='80',
                                name='hook-file-contents',
                                readonly="readonly")
        except IOError:
            return "No %s hook file yet exists" % hookname

    ### methods for IRepositoryChangeListener
    def type(self):
        """
        Types of supported repository types.

        :returns: list of supported repositoty types
        :returns type: list of string
        """
        return ['svn', 'svnsync']

    def available_hooks(self):
        return self.hooks

    def prepare_hook_ctx(self, hook, revision, **kwargs):
        """
        Prepare context before calling hook subscribers.

        The context preparation consists of repository synchronization in case
        of post-commit hook call.

        :param hook: hook name
        :type hook: str
        :param revision: revision if any
        :type revision: str or int
        :raises: Exception when repository synchronization fail

        REMARK: for repo.sync(), feedback callback is not call in case of error
        e.g in case of concurrency raise condition, so call
        repo.get_youngest_rev() to get the youngest repository revision.
        """

        if hook == 'post-commit':
            self.log.debug("Synchronize repository for" \
                           " revision='%s'", revision)

            start_time = time.time()
            while True:
                # Synchronize repository
                repo = self.env.get_repository()
                repo.sync()

                # Verify if repository sync
                rev = repo.get_youngest_rev()
                if int(rev) >= int(revision):
                    break

                if (time.time() - start_time) >= self.sync_timeout:
                    # Print error on std error for svn hook
                    msg = 'Trac repository synchronization timeout\n'
                    sys.stderr.write(msg)

                    raise Exception(msg)
                time.sleep(self.sync_delay)

    def subscribers(self, hookname):
        """
        Return a list of subscribers that support hook name.

        :param hookname: hook name
        """

        return [subscriber for subscriber in self.listeners
                if subscriber.is_available(self.type(), hookname)]
