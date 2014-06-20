#!/usr/bin/env python
# -*- coding: utf-8 -*-

# trac-revprop-hook
# ----------------------------------------------------------------------------
# Copyright (c) 2007 Emmanuel Blot
# ----------------------------------------------------------------------------

# This Subversion unified pre/post-revprop-change hook script is meant to
# interface to the Trac (http://www.edgewall.com/products/trac/) issue
# tracking/wiki/etc system.
#
# It should be called from the 'pre-revprop-change' and 'post-revprop-change'
# scripts in Subversion, such as via:
#
#  REPOS="$1"
#  REV="$2"
#  AUTHOR="$3"
#  PROPNAME="$4"
#  TRAC_ENV="/somewhere/trac/project/"
#
#  cat | trac-revprop-hook -d "$REPOS" -p "$TRAC_ENV" -a "$AUTHOR" -r "$REV" \
#                          -p "$PROPNAME" <pre>|<post> "$"
#

from .repproxy import RepositoryProxy
from ConfigParser import ConfigParser
from repository_hook_system.errors import HookStatus
import os
import re
import sys


OK = 0
ERROR = 1

configpath = '/local/var/svn/config/access.conf'

changeset_cmd_pattern = \
    re.compile(r'^(?P<action>Delivers|Brings)(?P<force>\!)?\s+'
               r'\[(?P<first>\d+)(?::(?P<second>\d+))?\]([^:]|$)')


class RevpropHook(object):

    '''Hook script for revision property changes'''

    def __init__(self, env, post, project, rev, name, value,
                 action=None, author=None, repos=None):
        if not os.path.isdir(os.environ['PYTHON_EGG_CACHE']):
            raise AssertionError("Invalid egg cache directory: %s" %
                                 os.environ['PYTHON_EGG_CACHE'])
        self.env = env
        self.repospath = self.env.config.get('trac', 'repository_dir')
        self.rev = int(rev)
        self.name = name
        self.value = value
        self.author = author
        self.action = action

        # sanity check: hook script repository match Trac repository
        if repos and self.repospath != repos:
            print >> sys.stderr, 'Invalid/incoherent repository %s %s' % \
                (self.repospath, repos)
            raise HookStatus(-ERROR)

        (type, prop) = name.split(':')

        if post:
            if type == 'svn':
                # on post-revprop-change, update Trac w/ SVN properties
                # custom properties are not cached anyway ;-(
                self._update_trac()
            raise HookStatus(0)

        if type == 'svn':
            if prop == 'log':
                self._verify_log_msg()
                raise HookStatus(0)
            if self._is_admin(self.author):
                if prop == 'author':
                    raise HookStatus(0)
        elif type == 'rth':
            try:
                func = getattr(self, '_verify_rth_%s' % prop)
                # if the property is a valid one and the request is about
                # deletion
                if func and self.action == 'D':
                    raise HookStatus(OK)
                if not func():
                    print >> sys.stderr, 'Invalid value for property %s: %s' % \
                                         (self.name, self.value)
                    raise HookStatus(-ERROR)

                raise HookStatus(OK)
            except AttributeError:
                # unexpected property, will be catched later
                pass
        print >> sys.stderr, 'This property (%s) cannot be modified' % name
        raise HookStatus(-ERROR)

    def _verify_log_msg(self):
        #regex = re.compile(changeset_cmd_pattern, re.IGNORECASE)
        regex = changeset_cmd_pattern
        self.proxy = RepositoryProxy(self.repospath)
        oldlog = self.proxy.get_revision_log_message(self.rev)
        oldmo = regex.search(oldlog)
        if oldmo:
            newmo = regex.search(self.value)
            if (not newmo):
                print >> sys.stderr, \
                    'Missing message:\n  was: "%s"' % oldlog.split('\n')[0]
                raise HookStatus(-ERROR)
            if (oldmo.group('first') != newmo.group('first')) or \
               (oldmo.group('second') != newmo.group('second')):
                if not self._is_admin(self.author) or not newmo.group('force'):
                    print >> sys.stderr, \
                        'Original parameters should be kept unaltered:\n' \
                        '  "%s"' % oldlog.split('\n')[0]
                    raise HookStatus(-ERROR)

    def _verify_rth_deliver(self):
        # check that source revision are ordered integers
        try:
            prev = 1
            for src in self.value.split(','):
                rev = int(src)
                if rev < prev:
                    return None
                prev = rev
            return True
        except ValueError:
            return None

    def _verify_rth_bring(self):
        # check that source revision are ordered integers
        try:
            prev = 1
            for src in self.value.split(','):
                rev = int(src)
                if rev < prev:
                    return None
                prev = rev
            return True
        except ValueError:
            return None

    def _update_trac(self):
        # update Trac cache with the updated value
        repos = self.env.get_repository()
        repos.sync_changeset(self.rev)

    def _is_admin(self, author):
        '''
        Verify whether the author has administrator privileges
        '''
        config = ConfigParser()
        if not os.path.isfile(configpath):
            raise AssertionError('Unable to find Subversion ACL for admins')
        config.read(configpath)
        admins = config.get('groups', 'admins')
        if not admins:
            raise AssertionError(
                'Unable to retrieve Subversion ACL for admins')
        if not author.lower() in [s.strip() for s in admins.lower().split(',')]:
            return False
        return True
