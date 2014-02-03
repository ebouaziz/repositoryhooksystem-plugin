#!/usr/bin/env python
"""
Repository Change Listener plugin for trac

This module provides an entry point for trac callable
from the command line
"""

import os
import sys

from optparse import OptionParser
from repository_hook_system.interface import IRepositoryChangeListener
from trac.core import *
from trac.env import open_environment


class RepositoryChangeListener(object):
    # XXX this doesn't need to be a class...yet!

    def __init__(self, env, project, hook, options):
        """
        * project : path to the trac project environment
        * hook : name of the hook called from
        * args : arguments for the particular implementation of IRepositoryChangeListener
        """

        # open the trac environment
        #env = open_environment(project)
        repo = env.get_repository()
        repo.sync()

        # find the active listeners
        listeners = ExtensionPoint(IRepositoryChangeListener).extensions(env)

        # find the listener for the given repository type and invoke the hook
        for listener in listeners:
            if env.config.get('trac', 'repository_type') in listener.type():
                # @@SD changeset = listener.changeset(repo, hook, *args)
                subscribers = listener.subscribers(hook)
                for subscriber in subscribers:
                    subscriber.invoke(**vars(options))  # @@SD


def filename():
    return os.path.abspath(__file__.rstrip('c'))


def command_line(projects, hook, *args):
    """return a generic command line for invoking this file"""

    # arguments to the command line
    # XXX this could be returned as a list, if there is a reason to do so
    retval = [sys.executable, filename()]

    # enable passing just one argument
    if isinstance(projects, basestring):
        projects = [projects]

    # append the projects to the command line
    for project in projects:
        retval.extend(['-p', project])

    # add the hook
    retval.extend(['--hook', hook])

    # add the arguments
    retval.extend(args)

    return ' '.join(retval)


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

    RepositoryChangeListener(options.project, options.hook, options)
