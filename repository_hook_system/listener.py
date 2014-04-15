#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repository Change Listener plugin for trac

This module provides an entry point for trac callable
from the command line
"""

from optparse import OptionParser
from repository_hook_system.errors import HookStatus
from repository_hook_system.interface import IRepositoryChangeListener
from trac.core import *
from trac.env import open_environment
from trac.util.text import exception_to_unicode, to_unicode
import os
import sys


class RepositoryChangeListener(object):
    def __init__(self):
        super(RepositoryChangeListener, self).__init__()

    def process(self, env, project, hook, options):
        self.env = env

        # find the active listeners
        listeners = ExtensionPoint(IRepositoryChangeListener).extensions(env)

        # find the listener for the given repository type and invoke the hook
        status = []
        for listener in listeners:
            if env.config.get('trac', 'repository_type') in listener.type():
                # Listener prepare hook context
                try:
                    listener.prepare_hook_ctx(**vars(options))
                except Exception as e:
                    self.env.log.error(exception_to_unicode(e, traceback=True))
                    return False

                self.env.log.debug(to_unicode('Call listener subscribers ' \
                                              'for hook=%s' % hook))

                # Invoke subscriber for this hook
                subscribers = listener.subscribers(hook)
                for subscriber in subscribers:
                    try:
                        self.env.log.debug(to_unicode('Call subscribers ' \
                                                      'for hook=%s' % hook))

                        subscriber.invoke(**vars(options))
                    # Hook status
                    except HookStatus as e:
                        status.append(e.status)
                    # Other exceptions
                    except Exception as e:

                        self.env.log.info(exception_to_unicode(e,
                                                               traceback=True))
                        status.append(1)  # Force an error code
        return not any(status)


def filename():
    return os.path.abspath(__file__.rstrip('c'))


def option_parser():
    parser = OptionParser()
    parser.add_option('-p', '--project', '--projects',
                      dest='project', action='append',
                      default=[],
                      help='projects to apply to',
                      )
    parser.add_option('--hook',
                      dest='hook',
                      help='hook called')
    return parser


__version__ = "1.0"


def _parse_options():
    import argparse

    optparser = argparse.ArgumentParser(prog='Repository hook system listener',
                                        version='%s' % __version__,
                                        add_help=True)

    # Generic options
    optparser.add_argument('-p', '--project',
                           dest='project',
                           required=True,
                           help='Path to the Trac project.')

    optparser.add_argument('-r', '--repository',
                           dest='repository',
                           required=True,
                           help='Path to repository.')

    optparser.add_argument('-u', '--user',
                           dest='user',
                           required=True,
                           help='Author modification name.')

    optparser.add_argument('--hook',
                           dest='hook',
                           required=True,
                           help='Hook name')

    # SVN hook specific options
    subparsers = optparser.add_subparsers(dest='hook-type',
                                          help='SVN specific options')

    # SVN options
    svn_parser = subparsers.add_parser('svn',
                                       help='svn hook options.')
    svn_parser.add_argument('-r', '--revision',
                            dest='revision',
                            default=None,
                            help='Repository revision number (post-commit).')

    svn_parser.add_argument('-t', '--transaction',
                            dest='transaction',
                            default=None,
                            help='Transaction number (pre-commit).')

    svn_parser.add_argument('-a', '--action',
                            dest='action',
                            default=None,
                            help='subversion action code (A|D|M).')

    svn_parser.add_argument('-n', '--name',
                            dest='propname',
                            default=None,
                            help='Property name (post-revprop-change, '
                                 'pre-revprop-change).')

    # Parse line options
    return optparser.parse_args()


if __name__ == '__main__':

    # Get command line options
    options = _parse_options()

    env = open_environment(options.project)

    rcl = RepositoryChangeListener()
    if rcl.process(env, options.project, options.hook, options):
        status = 0
    else:
        status = 1
    sys.exit(status)
