"""
implementation of the RepositoryChangeListener interface for svn
"""

from genshi.builder import tag
from repository_hook_system.interface import (IRepositoryChangeListener,
                                              IRepositoryHookAdminContributer,
                                              IRepositoryHookSubscriber)
from trac.config import Option, ListOption
from trac.core import *
from trac.util.text import exception_to_unicode
from trac.wiki.formatter import format_to_html
import os


# from trac.config import ListOption

class SVNHookSystem(Component):
    """implementation of IRepositoryChangeListener for SVN repositories"""

    implements(IRepositoryChangeListener,
               IRepositoryHookAdminContributer)

    listeners = ExtensionPoint(IRepositoryHookSubscriber)
    hooks = ['pre-commit', 'post-commit',
             'pre-revprop-change', 'post-revprop-change']

    _svnlook = Option('svn', 'svnlook', default='/usr/bin/svnlook')

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
        return ['svn', 'svnsync']

    def available_hooks(self):
        return self.hooks

    def subscribers(self, hookname):
        """returns the active subscribers for a given hook name"""

        # XXX this is all SCM-agnostic;  should be moved out
        return [subscriber for subscriber in self.listeners
                if subscriber.is_available(self.type(), hookname)]
#                 if subscriber.__class__.__name__
#                 in getattr(self, hookname, [])
#                 and subscriber.is_available(self.type(), hookname)]

# @@ SD by default all hooks supported
for hook in SVNHookSystem.hooks:
    setattr(SVNHookSystem, hook,
            ListOption('repository-hooks', hook, default='',
            doc="active listeners for SVN changes on the %s hook" % hook))
