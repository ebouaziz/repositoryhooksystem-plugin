#!/usr/bin/env python
# -*- coding: utf-8 -*-

# trac-commit-hook
# ----------------------------------------------------------------------------
# Copyright (c) 2004 Stephen Hansen
# Copyright (c) 2005-2007 Emmanuel Blot, Jerome Souquieres
# Copyright (c) 2009-2011 Remi Verchere
# Copyright (c) 2015 Neotion
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
# ----------------------------------------------------------------------------

from ConfigParser import ConfigParser
from datetime import datetime, timedelta
from repository_hook_system.db import Db
from repository_hook_system.errors import HookStatus
from repproxy import RepositoryProxy
from trac.config import Option
from trac.ticket import Ticket, Milestone
from trac.ticket.notification import TicketNotifyEmail
from trac.util.datefmt import utc, to_timestamp, to_datetime
from trac.env import open_environment
import os
import re
import sys


OK = 0
ERROR = 1

#
# Patterns to match message logs
#
ticket_cmd_pattern = \
    re.compile(r'^(?P<action>Refs|Closes|Fixes)(?P<force>\!)?\s+'
               r'#(?P<ticket>[0-9]+)')
changeset_cmd_pattern = \
    re.compile(r'^(?P<action>Delivers|Brings)(?P<force>\!)?\s+'
               r'\[(?P<first>\d+)(?::(?P<second>\d+))?\]([^:]|$)')
create_pattern = \
    re.compile(r'^(?P<action>Creates)\s+[^#]*(#(?P<ticket>\d+)([\W]|$))?')
terminate_pattern = \
    re.compile(r'^(?P<action>Terminates)(?P<force>\!)?\s')
admin_pattern = \
    re.compile(r'^(?P<action>Admins)')
externals_pattern = \
    re.compile(r'^(?P<action>Externals).+\[(?P<project>\w+)'
               r':?source:?(?P<url>[a-zA-Z0-9\/._-]+)@(?P<rev>[0-9]+)\]')

sandbox_pattern = re.compile(r'^/sandboxes/.*')
branch_pattern = re.compile(r'^/(branches|platforms)/(?P<pname>\w+)-.+')
ticket_pattern = re.compile(r'#(?P<ticket>\d+)')
#
# SVN properties
deliver_prop_name = 'rth:deliver'
bring_prop_name = 'rth:bring'
export_prop_name = 'rth:export'
externals_prop_name = 'svn:externals'
mergeinfo_prop_name = 'svn:mergeinfo'
#
# SVN directories
#
dev_branch_dirs = ['/sandboxes']
admin_branch_dirs = ['/tags', '/branches', '/platforms']
trunk_directory = '/trunk'
config_path = '/local/var/svn/config/access.conf'
vendor_directory = '/vendor'

# Milestones
#
EXCLUDED_MILESTONES = [u'Unclassified']
TBD_MILESTONE = u'Next'
NA_MILESTONE = u'NotApplicable'


class CommitHook(object):

    """
    The base class for pre and post -commit hooks

    Contains the base mechanism for parsing log messages looking for
    action keywords and some commun functions.
    """

    # TODO remove this temporary setting once new policy is deployed everywhere
    enforce_milestone_policy_on_close = Option('ticket',
        'enforce_milestone_policy_on_close', True,
        """Allows to disable the new milestone policy""")
    forbidden_milestones_on_close = Option('ticket',
        'forbidden_milestones_on_close', 'Next',
        """A ticket cannot be closed if its milestone is in that list""")
    forbidden_components_on_close = Option('ticket',
        'forbidden_components_on_close', 'Triage, None',
        """A ticket cannot be closed if its component is in that list""")
    project_name_re = Option('ticket', 'project_name_re',
        r'/(branches|platforms)/(?P<name>[A-Za-z0-9]+)'
        r'(_(?P<cert>(cert|dvt)))?(\-(?P<ext>[0-9\.xyz]+))?',
        """RE to guess the projet name from the branch name""")

    _ticket_cmds = {'closes': '_cmd_closes',
                    'fixes': '_cmd_closes',
                    'refs': '_cmd_refs'}

    _changeset_cmds = {'delivers': '_cmd_delivers',
                       'brings': '_cmd_brings'}

    def __init__(self,
                 env,
                 project=None,
                 rev=None,
                 txn=None,
                 rep=None):
        self.env = env
        self.db = Db(env)
        # needed to use Options
        self.config = self.env.config
        self.project_name_cre = re.compile(self.project_name_re)

        # Initialization
        self._fbden_cp_on_close = [
            c.strip() for c in self.forbidden_components_on_close.split(',')]
        self._fbden_ms_on_close = [
            m.strip() for m in self.forbidden_milestones_on_close.split(',')]
        self._init_proxy(rep, rev, txn)
        if rev:
            self.rev = int(rev)
        self.txn = txn
        self.rep = rep
        self.now = datetime.now(utc)
        self.project = project
        self.author = self._get_author()
        self.log = self._get_log()
        if not os.path.isdir(os.environ['PYTHON_EGG_CACHE']):
            raise AssertionError("Invalid egg cache directory: %s" %
                                 os.environ['PYTHON_EGG_CACHE'])

        bre = self.env.config.get('revtree', 'branch_re')
        self.bcre = re.compile(bre)

        # Nearly empty log message
        if not self.log:
            print>>sys.stderr, 'Log message is invalid'
            self.finalize(ERROR)

        # Check if multiple branches txn commit
        if self._is_txn_with_multiple_branches():
            print >> sys.stderr, 'Multiple branches in commit not allowed'
            self.finalize(ERROR)

        # Check if we move a branch
        if self._is_branch_move():
            print >>sys.stderr, 'Do never, EVER move a branch !!'
            self.finalize(ERROR)

        # Administration commit
        administration = admin_pattern.search(self.log)
        if administration:
            self._cmd_admins()
            self.finalize(OK)

        # Branch deletion
        terminate = terminate_pattern.search(self.log)
        if terminate:
            rc = self._cmd_terminates(terminate.group('force') and True)
            self.finalize(OK)

        # Branch creation
        creation_cmd = create_pattern.search(self.log)
        if creation_cmd:
            cmd_dict = creation_cmd.groupdict()
            rc = self._cmd_creates(cmd_dict.setdefault('ticket', None))
            self.finalize(rc)

        # Changeset-related commands
        chgset_cmd = changeset_cmd_pattern.search(self.log)
        if chgset_cmd:
            cmd = chgset_cmd.group('action').lower()
            if cmd in CommitHook._changeset_cmds:
                func = getattr(self, CommitHook._changeset_cmds[cmd])
                rc = func(
                    chgset_cmd.group('first'), chgset_cmd.group('second'),
                    chgset_cmd.group('force') and True)
                self.finalize(rc)
            else:
                print >> sys.stderr, 'Invalid changeset action'
                self.finalize(ERROR)

        # Ticket-related commands
        ticket_cmd = ticket_cmd_pattern.search(self.log)
        if ticket_cmd:
            cmd = ticket_cmd.group('action').lower()
            if cmd in CommitHook._ticket_cmds:
                func = getattr(self, CommitHook._ticket_cmds[cmd])
                rc = func(int(ticket_cmd.group('ticket')),
                          ticket_cmd.group('force') and True)
                self.finalize(rc)
            else:
                print>>sys.stderr, 'No supported action in log message!'
                self.finalize(ERROR)

        # Externals changes commands
        externals = externals_pattern.search(self.log)
        if externals:
            project = externals.group('project').lower()
            url = externals.group('url').lower()
            rev = externals.group('rev').lower()
            rc = self._cmd_externals(project, url, rev)
            self.finalize(rc)

        # Unrecognized log message
        print>>sys.stderr, 'No known action in log message!'
        self.finalize(ERROR)

    def _next_milestone(self, prefix=None):
        """
        Returns the next milestone (i.e. the first non-completed milestone by
        chronological order)
        """
        xms = EXCLUDED_MILESTONES + [TBD_MILESTONE]
        candidates_ms = Milestone.select(self.env, False)
        if prefix is None:
            ms = [m.name for m in candidates_ms if m.name not in xms]
        else:
            ms = [m.name for m in candidates_ms if m.name not in xms
                  and m.name.lower().startswith(prefix.lower())]
        return ms and ms[0] or None

    def _collect_branch_revs(self, rev1, rev2):
        """
        Collect all revisions sitting on the branch between rev1 and rev2

        @return the revision list
        """
        if not rev1:
            print >> sys.stderr, 'Source revision not specified'
            self.finalize(ERROR)
        rev1 = int(rev1)

        if not rev2:
            rev2 = rev1
        else:
            rev2 = int(rev2)

        if rev1 > rev2:
            print >> sys.stderr, 'Revision range is invalid %d:%d' \
                % (rev1, rev2)
            self.finalize(ERROR)

        branch1 = self.proxy.find_revision_branch(rev1, self.bcre)

        if not branch1:
            print >> sys.stderr, 'Revision %d does not exist' % rev1
            self.finalize(ERROR)

        branch2 = self.proxy.find_revision_branch(rev2, self.bcre)

        if not branch2:
            print >> sys.stderr, 'Revision %d does not exist' % rev2
            self.finalize(ERROR)

        if branch1 != branch2:
            print >> sys.stderr, 'Revisions (%d,%d) not coherent: %s,%s' \
                                 % (rev1, rev2, branch1, branch2)
            self.finalize(ERROR)

        revisions = []
        for rev in range(rev1, rev2 + 1):
            try:
                revbranch = self.proxy.find_revision_branch(rev, self.bcre)
            except AssertionError as e:
                print >> sys.stderr, "Error: %s" % e
                self.finalize(ERROR)
            if not revbranch:
                continue
            if revbranch != branch1:
                continue
            revisions.append('%d' % rev)

        return revisions

    def _collect_tickets(self, revisions, branchname=None):
        """
        Build a dictionary of all tickets referenced by the revision list,
        following bring links

        @param revisions a list of revisions
        @return a dictionary of tickets: the key is the ticket number,
                the value is the list of revisions related to this ticket.
                Each revision is itself a list [author, log]
        """

        ticket_dict = {}
        for rev in revisions:
            # if we bring from the trunk, then retrieve properties with
            # "Delivers" msg
            if (branchname == trunk_directory or
                    self._is_branch_type(branchname, admin_branch_dirs)):
                bring_prop = self.proxy.get_revision_property(int(rev),
                                                              deliver_prop_name)
            else:
                bring_prop = self.proxy.get_revision_property(int(rev),
                                                              bring_prop_name)
            if bring_prop and len(bring_prop) > 0:
                bring_revs = bring_prop.split(',')
                subticket_dict = self._collect_tickets(bring_revs, branchname)
                ticket_dict.update(subticket_dict)

            rev_log = self.proxy.get_revision_log_message(int(rev))
            rev_author = self.proxy.get_revision_author(int(rev))
            mo = ticket_cmd_pattern.match(rev_log)
            if mo:
                tkid = int(mo.group('ticket'))
                if tkid in ticket_dict:
                    ticket_dict[tkid].append([rev_author, rev_log])
                else:
                    ticket_dict[tkid] = [[rev_author, rev_log]]
            mo = create_pattern.match(rev_log)
            if mo:
                tkid = int(mo.group('ticket'))
                if tkid in ticket_dict:
                    ticket_dict[tkid].append([rev_author, rev_log])
                else:
                    ticket_dict[tkid] = [[rev_author, rev_log]]
        return ticket_dict

    def _is_txn_with_multiple_branches(self):
        # Get txn branch
        try:
            self.proxy.find_txn_branch(self.bcre)
        except AssertionError as _excpt:  # Several branches specified reject
            return True
        return False

    def _is_ticket_closed(self, ticket_id):
        """
        Check if a ticket is closed
        """
        try:
            ticket = Ticket(self.env, ticket_id)
            is_closed = ticket['status'] == 'closed'
            return is_closed
        except Exception as e:
            print >> sys.stderr, "Error: %s" % e
            self.finalize(ERROR)

    def _is_ticket_open(self, ticket_id):
        """
        Check if a ticket is open
        """
        return not self._is_ticket_closed(ticket_id)

    def _is_ticket_invalid_component(self, ticket_id):
        """
        Check if component is set as "None" or "Triage"
        """
        try:
            ticket = Ticket(self.env, ticket_id)
            self.env.log.debug("Component for #%s is %s", ticket_id,
                               ticket['component'])
            return ticket['component'] in self._fbden_cp_on_close
        except Exception as e:
            print >> sys.stderr, "Error: %s" % e
            self.finalize(ERROR)

    def _is_ticket_invalid_milestone(self, ticket_id):
        """
        Check if milestone is set as "Next"
        """
        try:
            ticket = Ticket(self.env, ticket_id)
            return ticket['milestone'] in self._fbden_ms_on_close
        except Exception as e:
            print >> sys.stderr, "Error: %s" % e
            self.finalize(ERROR)

    def _is_admin(self, author):
        """
        Verify whether the author has administrator privileges
        """
        config = ConfigParser()
        if not os.path.isfile(config_path):
            raise AssertionError('env: %s' % os.environ.keys())
            raise AssertionError('Unable to find Subversion ACL for admins: %s'
                                 % config_path)
        config.read(config_path)
        admins = config.get('groups', 'admins')
        if not admins:
            raise AssertionError(
                'Unable to retrieve Subversion ACL for admins')
        if not author.lower() in [s.strip() for s in admins.lower().split(',')]:
            return False
        return True

    def _is_branch_type(self, dir_path, branches):
        """
        Tell whether a directory is located inside a branch group or not
        """
        if not dir_path or not branches:
            return False
        for dev_br in branches:
            if dir_path[:len(dev_br)] == dev_br:
                return True
        return False

    def _get_milestone_and_project(self):
        """
        Find branch the current transaction was copied from
        Deduce the applicable milestone
        Intended for _cmd_closes pre and post commit hooks
        """
        # current branch
        if self.txn:
            self.env.log.debug("> _get_milestone_and_project transaction")
            branch = self.proxy.find_txn_branch(self.bcre)
        elif self.rev:
            self.env.log.debug("> _get_milestone_and_project project")
            branch = self.proxy.find_revision_branch(self.rev, self.bcre)
        else:
            self.env.log.debug("> _get_milestone_and_project WTF???")

        # fetch revision history of the branch
        history = [h for h in self.proxy.get_history(self.youngest, branch, None)]

        # get branch it was created from
        src = self.proxy.get_revision_copy_source(history[-1][0])
        if src is None:
            print >> sys.stderr, 'Cannot get branch copy source for (%s)' \
                % history[-1][1]
            self.finalize(ERROR)
        src_rev, src_branch = src

        # chose a milestone
        bname = src_branch.rsplit('/', 1)[-1]

        # from exceptions defined in the database
        prefix = self.db.get_milestone_prefix(src_branch)

        # or from the general rule
        if not prefix:
            m = self.project_name_cre.match(src_branch)
            if m:
                prefix = m.group('name')
            else:
                self.env.log.info("Cannot get project name from branch for "
                                  "'%s'", src_branch)
        milestone = self._next_milestone(prefix)
        self.env.log.debug("prefix '%s', milestone '%s'",
                           prefix, milestone)

        # if no milestone, use default value if defined in Trac config
        if milestone is None:
            milestone = self.env.config.get('ticket',
                                            'default_closing_milestone', None)
        self.env.log.debug("prefix '%s', milestone '%s', type %s",
                           prefix, milestone, type(milestone))
        return milestone, bname


class PreCommitHook(CommitHook):

    '''
    Handles pre-commit-hook
    '''

    def _init_proxy(self, rep, rev, txn):
        '''
        Initialize the proxy with the specified transaction
        '''
        self.proxy = RepositoryProxy(rep, txn)
        self.youngest = self.proxy.get_youngest_revision()
        if self.youngest == 0:
            raise HookStatus(OK)
        return OK

    def _get_author(self):
        '''
        Get the transaction author
        '''
        author = self.proxy.get_txn_author()
        return author

    def _get_log(self):
        '''
        Get the transaction log message
        '''
        log = self.proxy.get_txn_log_message()
        if len(log) < 2:
            return None
        # Be sure the first letter is uppercased
        log = log.split(' ')
        log[0] = log[0].title()
        log = ' '.join(log)
        return log

    def _update_log(self, log):
        '''
        Update the transaction log message
        '''
        self.proxy.set_txn_log_message(log)

    def _is_txn_branch_directory(self):
        '''
        Check if the directory of the transaction is a branch directory
        (located under the branches directory)
        '''
        dst_branch = self.proxy.find_txn_branch(self.bcre)
        return self._is_branch_type(dst_branch, dev_branch_dirs)

    def _is_branch_move(self):
        '''
        Check if a branch is moved
        - must be only 2 path changes (del + add)
        - must be a path under /branches/ dir
        '''

        # Branch is
        changed_paths = []
        for change_gen in self.proxy.get_txn_changed_paths():
            changed_paths.append(change_gen)

        changed_paths = []
        for change_gen in self.proxy.get_txn_changed_paths():
            changed_paths.append(change_gen)
        # Only 2 path changes
        if(len(changed_paths) != 2):
            return False
        # check if one path is deleted, and the other is added
        if not (changed_paths[0][1] == self.proxy.PATH_DELETE and
                changed_paths[1][1] == self.proxy.PATH_ADD) \
            and not (changed_paths[0][1] == self.proxy.PATH_ADD and
                     changed_paths[1][1] == self.proxy.PATH_DELETE):
            return False
        # now, check that path is directly under /branches
        if not (len(changed_paths[0][0].split('/')) ==
                len(changed_paths[1][0].split('/')) == 2):
            return False
        return True

    def finalize(self, result):
        if OK == result:
            self._update_log(self.log)
        raise HookStatus(result)

    def _cmd_admins(self):
        '''
        Administrative commit
        '''
        if not self._is_admin(self.author):
            print >>sys.stderr, 'Only administrator can execute admin commits'
            self.finalize(ERROR)
        return OK

    def _cmd_externals(self, project, url, rev):
        '''
        Update only svn:externals
        '''
        for path, _ in self.proxy.get_txn_changed_paths():
            if not self.proxy.get_txn_path_property(path, externals_prop_name)\
               and not self.proxy.get_txn_path_property(path,
                                                        mergeinfo_prop_name):
                sys.stderr.write('Not a valid %s change for %s\n' \
                    % (externals_prop_name, path))

        # Open Trac project environment
        project = self.project.replace(self.project.split('/')[-1], project)
        try:
            extenv = open_environment(project)
        except:
            sys.stderr.write("Invalid external project='%s'\n" % project)
            self.finalize(ERROR)

        # Get node corresponding to url specified in commit message
        try:
            # check project:url:rev exists
            extrepo = extenv.get_repository()
            extrepo.get_node(url, rev)
        except:
            print>>sys.stderr, 'Invalid external path or revision'
            self.finalize(ERROR)
        return OK

    def _cmd_creates(self, ticket_str):
        '''
        Branch creation
        Check operation source and destination
        Copy import/symweek/symver properties from new branch
        '''
        self.env.log.debug("> pre_cmd_creates %s", ticket_str)
        src = self.proxy.get_txn_copy_source()
        if not src:
            print >> sys.stderr, 'Cannot locate source revision ' \
                                 '(not a copy ?)'
            self.finalize(ERROR)
        dstbranch = self.proxy.find_txn_branch(self.bcre)
        if not dstbranch and self._is_admin(self.author):
            print >> sys.stderr, 'No branch, admin, try "tag"'
            dstbranch = self.proxy.find_txn_branch(self.bcre, btag='tag')
        if not dstbranch:
            print >> sys.stderr, 'Destination branch is invalid'
            self.finalize(ERROR)

        # Check if the dst branch does not exist
        try:
            lrev = self.proxy.get_history(
                self.youngest,
                dstbranch,
                0).next()[0]
        except Exception as e:
            lrev = None
        if lrev:
            print >> sys.stderr, \
                'Destination branch %s already exists at [%s]' \
                % (dstbranch, lrev)
            self.finalize(ERROR)

        if self._is_admin(self.author) and \
                self._is_branch_type(dstbranch, admin_branch_dirs):
            self.env.log.debug("< pre_cmd_creates (admin)")
            return OK

        if not ticket_str:
            print >> sys.stderr, 'No ticket associated to the new branch'
            self.finalize(ERROR)
        ticket_id = int(ticket_str)
        if not self._is_ticket_open(ticket_id):
            print >> sys.stderr, 'Associated ticket #%d is not open' % \
                ticket_id
            self.finalize(ERROR)

        if self._is_branch_type(dstbranch, dev_branch_dirs):
            self.env.log.debug("< pre_cmd_creates (1)")
            return OK
        print >> sys.stderr, 'Admin ? %d' % self._is_admin(self.author)
        print >> sys.stderr, 'Branch type ? %d' % \
            self._is_branch_type(dstbranch, admin_branch_dirs)
        print >> sys.stderr, 'Branch %s' % dstbranch
        print >> sys.stderr, 'Cannot create a new branch outside %s' \
            % dev_branch_dirs
        self.finalize(ERROR)

    def _cmd_terminates(self, force):
        """
        Branch deletion
        Check that this is a valid and owned branch
        """
        change_gen = self.proxy.get_txn_changed_paths()
        try:
            item = change_gen.next()
        except StopIteration:
            sys.stderr.write('No deleted path in the submitted revision\n')
            self.finalize(ERROR)
        try:
            change_gen.next()
        except StopIteration:
            pass
        else:
            sys.stderr.write('Termination of more than one branch is not '
                              'allowed\n')
            self.finalize(ERROR)
        (path, change) = item
        if change != RepositoryProxy.PATH_DELETE:
            print >> sys.stderr, "The branch %s is not being deleted" % path
            self.finalize(ERROR)
        if not force:
            dstbranch = self.proxy.find_txn_branch(self.bcre)
            if not self._is_branch_type(dstbranch, dev_branch_dirs):
                print >> sys.stderr, 'Cannot terminates a non-branch dir (%s)' \
                    % dev_branch_dirs
                self.finalize(ERROR)
            youngest = self.proxy.get_youngest_path_revision(path)
            # now checks that the deleter is the creator of the branch
            revs = [h[0] for h in self.proxy.get_history(youngest, path, 0)]
            if not revs:
                print >> sys.stderr, 'Malformed branch, cannot find ancestor ' \
                                     'from %s (%d)' % (path, youngest)
            first_rev = revs[-1]
            init_author = self.proxy.get_revision_author(first_rev)
            if init_author != self.author:
                print >> sys.stderr, 'Cannot delete a non self-owned branch ' \
                                     '%s, owned by %s' \
                                     % (path, init_author)
                self.finalize(ERROR)
        return OK

    def _pre_cmd_closes(self, ticket_id):
        if not self._is_ticket_open(ticket_id):
            print >> sys.stderr, 'The ticket %d mentioned in the log ' \
                'message must be open.' % ticket_id
            self.finalize(ERROR)
        if not self._is_txn_branch_directory():
            print >> sys.stderr, 'Cannot apply changes to a non-branch dir' \
                                 ' (%s)' % dev_branch_dirs
            self.finalize(ERROR)

    def _cmd_closes(self, ticket_id, force):
        """
        Ticket close
        Check that the component is set correctly
        Check that the ticket is open
        Check that the operation occurs in a branch
        Find what branch the sandbox was copied from
        Deduce the applicable milestone
        """
        # check component
        self.env.log.debug("> pre_cmd_closes")
        if not self._is_admin(self.author) or not force:
            if self._is_ticket_invalid_component(ticket_id):
                print >> sys.stderr, 'Please correct component for #%d' \
                                     % ticket_id
                self.finalize(ERROR)

        # check ticket closed and operation occurs in a branch
        self._pre_cmd_closes(ticket_id)

        # find original branch and target milestone
        if self.enforce_milestone_policy_on_close:
            milestone, branch = self._get_milestone_and_project()
            if milestone is None and self._is_ticket_invalid_milestone(ticket_id):
                if not self._is_admin(self.author) or not force:
                    msg = "No defined next milestone for branch '%s'" % branch
                    print >> sys.stderr, msg
                    self.env.log.debug("  %s", msg)
                    self.finalize(ERROR)
        self.env.log.debug("< pre_cmd_closes")
        return OK

    def _cmd_refs(self, ticket_id, force):
        '''
        Ticket reference
        Same pre-conditions as closes except for the milestone processing
        '''
        self.env.log.debug("> pre_cmd_refs: #%s, %s" % (ticket_id, force))
        self._pre_cmd_closes(ticket_id)
        self.env.log.debug("< pre_cmd_refs")
        return OK

    def _cmd_brings(self, rev1, rev2, force):
        '''
        Branch import
        Check revision range validity
        Check operation source and destination
        Collect all tickets related to this revision
        '''
        # Get all revisions to bring
        revisions = self._collect_branch_revs(rev1, rev2)
        if not revisions:
            print >> sys.stderr, "Revisions %s %s %s" % (rev1, rev2, revisions)
            self.finalize(ERROR)
        # On error, the transaction is destroyed, so it is safe to apply the
        # property even if the hook fails.
        self.proxy.set_txn_property(bring_prop_name, ','.join(revisions))

        dstbranch = self.proxy.find_txn_branch(self.bcre)
        if not dstbranch:
            print >> sys.stderr, 'Unable to locate bring destination'
            self.finalize(ERROR)
        branch1 = self.proxy.find_revision_branch(int(rev1), self.bcre)
        if dstbranch == branch1:
            print >> sys.stderr, 'Cannot bring to self (%s -> %s)' % \
                (branch1, dstbranch)
            self.finalize(ERROR)

        if dstbranch == trunk_directory:
            if not branch1.startswith(vendor_directory):
                sys.stderr.write('Cannot bring to trunk (from %s)\n' % branch1)
                self.finalize(ERROR)
            else:
                # No ticket to update from a vendor merge
                return OK

        # Try to collect all tickets. This will be used in the post-commit
        tickets = self._collect_tickets(revisions)

        # Build the new log including all tickets
        if not rev2:
            rev2 = rev1
        log = self.log.decode('utf8')
        log = '%s%s (from [source:%s@%s %s])' % \
            (log[0].upper(), log[1:], branch1, rev2, branch1,)
        self.log = log.encode('utf8')

        return OK

    def _cmd_reverts(self, rev1, rev2, force, recursive=False):
        '''
        Changeset revert
        Check revision range validity
        Check operation source and destination
        Collect all tickets related to this revision
        '''
        if not self._is_admin(self.author):
            print >> sys.stderr, "Only administrator can revert changes"
            self.finalize(ERROR)

        # Get all revisions to revert
        if rev2:
            print >> sys.stderr, "Cannot revert more than one changeset at once"
            self.finalize(ERROR)

        dstbranch = self.proxy.find_txn_branch(self.bcre)
        if not dstbranch:
            print >> sys.stderr, 'Unable to locate revert branch'
            self.finalize(ERROR)

        # Get log message of changeset to revert (need to be on the same
        # branch)
        logmsg = self.proxy.get_revision_log_message(int(rev1))
        logp = changeset_cmd_pattern.search(logmsg)
        if logp:
            first = logp.group('first')
            second = logp.group('second')
            # Try to collect all tickets. This will be used in the post-commit
            revisions = self._collect_branch_revs(first, second)
            if not revisions:
                print >> sys.stderr, "Revisions %s %s %s" % \
                    (first, second, revisions)
                self.finalize(ERROR)
            tickets = self._collect_tickets(revisions)
            # if we get no tickets, try to find the ones with revision we
            # reverted
            if not tickets:
                self._cmd_reverts(first, second, force, True)

        # Build the new log
        if not recursive:
            # build new log
            log = self.log.decode('utf8')
            log = '%s%s' % (log[0].upper(), log[1:])
            if logmsg:
                log += " (''was: %s" % logmsg.splitlines()[0]
                if len(logmsg.splitlines()) > 1:
                    log += u'...'
                log += "'')"
            self.log = log.encode('utf8')

        return OK

    def _camel_case(self, text):
        if re.search("^[A-Z][a-z].*[A-Z][a-z]", text):
            return "!"
        return ""

    def _cmd_delivers(self, rev1, rev2, force):
        '''
        Branch delivery
        Check revision range validity
        Check operation source and destination
        Check trunk availability
        Build consolidated log message
        '''
        # Get all revisions to deliver
        self.env.log.debug("> pre_cmd_delivers [%s:%s]", rev1, rev2)
        revisions = self._collect_branch_revs(rev1, rev2)
        if not revisions:
            print >> sys.stderr, "Revisions %s %s %s" % (rev1, rev2, revisions)
            self.finalize(ERROR)

        # On error, the transaction is destroyed, so it is safe to apply the
        # property even if the hook fails.
        self.proxy.set_txn_property(deliver_prop_name, ','.join(revisions))

        # Check that the destination branch is ok
        dstbranch = self.proxy.find_txn_branch(self.bcre)
        if not dstbranch:
            print >> sys.stderr, 'Unable to locate delivery destination'
            self.finalize(ERROR)

        # Ensure the branch is not delivered to self
        branch1 = self.proxy.find_revision_branch(int(rev1), self.bcre)
        if dstbranch == branch1:
            print >> sys.stderr, 'Cannot deliver to self (%s -> %s)' % \
                (branch1, dstbranch)
            self.finalize(ERROR)

        # Ensure that the 'branch creation' revision is not selected as a
        # source
        print >> sys.stderr, "Branch: (%s) [%s]" % (rev1, branch1)
        brevs = [h[0]
                 for h in self.proxy.get_history(int(rev1), branch1, None)]
        if rev1 == brevs[0]:
            print >> sys.stderr, \
                'Cannot deliver the initial branch revision (%d)' % rev1
            self.finalize(ERROR)

        # If source branch is not a developer branch
        # Brings back a stabilisation branch back to the trunk
        if (dstbranch == trunk_directory) and \
                self._is_branch_type(branch1, admin_branch_dirs):
            return OK

        # /vendor branch should not accept delivery
        if dstbranch.startswith(vendor_directory):
            print >> sys.stderr, \
                'Cannot deliver to %s branch' % dstbranch
            self.finalize(ERROR)

        # Common case: developer branch delivery to trunk
        tickets = self._collect_tickets(revisions).keys()

        if not self._is_admin(self.author) or not force:
            if not tickets:
                print >> sys.stderr, 'No ticket tied to the source branch'
                self.finalize(ERROR)
            # Check if tickets are closed
            opentkts = []
            for tid in tickets:
                if not self._is_ticket_closed(tid):
                    opentkts.append(tid)
            if opentkts:
                print >> sys.stderr, 'Not all tickets closed, ' \
                    'delivery rejected\n'
                if len(opentkts) > 1:
                    print >> sys.stderr, 'Please close tickets %s' % \
                        ', '.join(['#%d' % tid for tid in opentkts])
                else:
                    print >> sys.stderr, 'Please close ticket #%d' % opentkts[
                        0]
                self.finalize(ERROR)
            # Check if ticket components are valid
            cptkts = []
            for tid in tickets:
                if self._is_ticket_invalid_component(tid):
                    cptkts.append(tid)
            if cptkts:
                print >> sys.stderr, 'No valid component, delivery rejected\n'
                if len(cptkts) > 1:
                    print >> sys.stderr, 'Please correct component of %s' % \
                        ', '.join(['#%d' % tid for tid in cptkts])
                else:
                    print >> sys.stderr, 'Please correct component of #%d' % \
                        cptkts[0]
                self.finalize(ERROR)

        # Build the new log including all tickets
        log = self.log.decode('utf8')
        log = log[0].upper() + log[1:] + '\n'
        log += u'\n'.join([u' * #%s (%s%s): %s' %
                           (tid,
                            self._camel_case(
                               Ticket(self.env, tid)['component']),
                               Ticket(self.env, tid)['component'],
                               Ticket(self.env, tid)['summary'])
                           for tid in tickets])
        self.log = log.encode('utf8')

        # Check if there is a next milestone defined in Trac
        # This is a bit too conservative, as a next milestone is only needed if
        # tickets are to be closed. Oh well...
        ms = self._next_milestone()
        if not ms:
            print >> sys.stderr, 'No defined next milestone, ' \
                                 'please fix up roadmap'
            self.finalize(ERROR)

        self.env.log.debug("< pre_cmd_delivers")
        return OK


class TicketNotifyEmailEx(TicketNotifyEmail):

    def __init__(self, env, excluded_rcpts=None, *args, **kwargs):
        TicketNotifyEmail.__init__(self, env, *args, **kwargs)
        self.excluded_rcpts = excluded_rcpts or []

    def send(self, torcpts, ccrcpts):
        # Remove excluded names from to sending mail list
        torcpts = [rcpt for rcpt in torcpts if rcpt not in self.excluded_rcpts]

        if torcpts or ccrcpts:
            TicketNotifyEmail.send(self, torcpts, ccrcpts)


class PostCommitHook(CommitHook):

    '''
    Handles post-commit-hook
    '''

    def _init_proxy(self, rep, rev, txn):
        '''
        Initialize the proxy for the specified revision
        '''
        # Initial repository creation
        if rev < 2:
            self.finalize(OK)
        self.proxy = RepositoryProxy(rep)
        self.youngest = self.proxy.get_youngest_revision()
        return OK

    def _get_log(self):
        '''
        Get the revision log message
        '''
        log = self.proxy.get_revision_log_message(self.rev)
        return log

    def _update_log(self, log):
        '''
        Update the transaction log message
        '''

        # Svn side
        self.proxy.set_revision_log_message(self.rev, log)

        # Trac side update revision log
        repo = self.env.get_repository()
        repo.sync_changeset(self.rev)

    def _get_author(self):
        '''
        Get the revision author
        '''
        author = self.proxy.get_revision_author(self.rev)
        return author

    def _cmd_imports(self, label, week, version):
        # Nothing to do, the properties have been set during the pre-commit
        return OK

    def _is_txn_with_multiple_branches(self):
        # Nothing to do, check have been done during the pre-commit
        return False

    def _is_branch_move(self):
        # Nothing to do, check have been done during the pre-commit
        return False

    def _cmd_admins(self):
        # Nothing to do
        return OK

    def _cmd_externals(self, project, ticket, rev):
        # Nothing to do, done by pre-commit
        return OK

    def _cmd_terminates(self, force):
        """
        Branch deletion
        Add back-link to the termination revision in all related tickets
        """
        path = self.proxy.get_revision_changed_paths(self.rev).next()[0]

        # We only want to update ticket related to developer branches
        update_ticket = False
        for dev_path in dev_branch_dirs:
            if path.startswith(dev_path.lstrip('/')):
                update_ticket = True
                break
        if not update_ticket:
            return OK

        revs = []
        for h in self.proxy.get_history(self.rev - 1, path, True):
            if h[1].lstrip('/') != path:
                break
            revs.append(h[0])
        revs.reverse()

        # Get all revisions of the terminated branch
        revisions = self._collect_branch_revs(revs[0], revs[-1])
        # Get all tickets related to these revisions
        tickets = self._collect_tickets(revisions)

        for tktid in tickets:
            ticket = Ticket(self.env, int(tktid))
            # Get date (last changed value timestamp +1), as time is a unique
            # field in DB)
            changetime = ticket.values.get('changetime')
            changetime = to_timestamp(changetime) + 1
            changetime = to_datetime(changetime, tzinfo=utc)
            ticket.save_changes(self.author,
                                'Sandbox [source:%s@%d /%s] terminated at [%s]' %
                                (path, revs[-1], path, self.rev), changetime)
        return OK

    def _cmd_creates(self, ticket_str):
        """
        Sandbox creation
        Add back-link to the revision in the ticket
        Mark the ticket as accepted
        """
        self.env.log.debug("> post_cmd_creates #%s, rev=%s",
                           ticket_str, self.rev)
        if ticket_str:
            ticket_id = int(ticket_str)
            ticket_msg = '(In [%d]) %s' % (self.rev, self.log)
            try:
                ticket = Ticket(self.env, ticket_id)
                if ticket['owner'] != self.author:
                    ticket['owner'] = self.author
                if ticket['status'] == 'new':
                    ticket['status'] = 'accepted'
                    ticket.save_changes(self.author, ticket_msg, self.now)

                    # Notify only on accepted for creates operation
                    tn = TicketNotifyEmailEx(self.env, [self._get_author(), ])
                    tn.notify(ticket, newticket=0, modtime=self.now)
                else:
                    ticket.save_changes(self.author, ticket_msg, self.now)
            except Exception as e:
                from trac.util import get_last_traceback
                self.env.log.error("Error post_cmd_create('%s'):\n%s",
                                   ticket_str, get_last_traceback())
                print>>sys.stderr, 'Unexpected error while processing ticket' \
                                   ' ID %d: %s' % (ticket_id, e)
                print >>sys.stderr, 'Traceback:\n', get_last_traceback()
        self.env.log.debug("< post_cmd_creates")
        return OK

    def _cmd_closes(self, ticket_id, force):
        """
        Ticket closes
        Add backlink to the revision in the ticket
        Set the milestone
        Close the ticket
        """
        self.env.log.debug("> post_cmd_closes, #%s force=%s", ticket_id, force)
        ticket_msg = "(In [%d]) %s" % (self.rev, self.log)
        # FIXME: replace self.now with the actual svn:date commit time
        # fix this in other script locations as well...
        commit_date = self.now
        try:
            ticket = Ticket(self.env, ticket_id)
            if self.enforce_milestone_policy_on_close:
                milestone, project = self._get_milestone_and_project()
                self.env.log.debug("  ms '%s', pj '%s'", milestone, project)
                if milestone is not None and \
                        self._is_ticket_invalid_milestone(ticket_id):
                    ticket['milestone'] = milestone
            ticket['status'] = 'closed'
            ticket['resolution'] = 'fixed'
            ticket.save_changes(self.author, ticket_msg, commit_date)
            self.env.log.debug("saved ticket changes")
        except Exception as e:
            from trac.util import get_last_traceback
            print>>sys.stderr, 'Unexpected error while processing ticket ' \
                               'ID %s: %s' % (ticket_id, e)
            print >>sys.stderr, 'Traceback:\n', get_last_traceback()
            self.env.log.error("error %s", e)
            self.env.log.error('Traceback:\n%s', get_last_traceback())
            return ERROR
        try:
            # we do not want a notification failure to prevent from
            # backing up the revision
            self.env.log.debug("try notif")
            tn = TicketNotifyEmailEx(self.env, [self._get_author(), ])
            tn.notify(ticket, newticket=0, modtime=commit_date)
            self.env.log.debug("sent notif")
        except Exception as e:
            from trac.util import get_last_traceback
            print>>sys.stderr, 'Unexpected error while processing ticket ' \
                               'ID %s: %s' % (ticket_id, e)
            print >>sys.stderr, 'Traceback:\n', get_last_traceback()
        self.env.log.debug("< post_cmd_closes")
        return OK

    def _cmd_refs(self, ticket_id, force):
        '''
        Ticket reference
        Add backlink to the revision in the ticket
        '''
        self.env.log.debug("> post_cmd_refs #%s", ticket_id)
        ticket_msg = "(In [%d]) %s" % (self.rev, self.log)
        try:
            ticket = Ticket(self.env, ticket_id)
            ticket.save_changes(self.author, ticket_msg, self.now)
            tn = TicketNotifyEmailEx(self.env, [self._get_author(), ])
            tn.notify(ticket, newticket=0, modtime=self.now)
            return OK
        except Exception as e:
            from trac.util import get_last_traceback
            print>>sys.stderr, 'Unexpected error while processing ticket ' \
                               'ID %s: %s' % (ticket_id, e)
            print >>sys.stderr, 'Traceback:\n', get_last_traceback()
            return ERROR

    def _cmd_brings(self, rev1, rev2, force):
        '''
        Branch import
        Add backlink to the revision in all related tickets
        '''
        # Get all revisions to bring
        self.env.log.debug("> post_cmd_brings [%s:%s]", rev1, rev2)
        revisions = self._collect_branch_revs(rev1, rev2)

        # Get src and dst branches
        srcbranch = self.proxy.find_revision_branch(int(rev1), self.bcre)
        dstbranch = self.proxy.find_revision_branch(int(self.rev), self.bcre)

        # Case sandbox
        if sandbox_pattern.match(dstbranch):
            history_iterator = self.proxy.get_history(self.rev, dstbranch, 0)

            for rev, _ in history_iterator:
                pass
            rev_log = self.proxy.get_revision_log_message(rev)

            mo = ticket_pattern.search(rev_log)
            if mo:
                tktid = mo.group('ticket')
                ticket = Ticket(self.env, int(tktid))
                ticket.save_changes(self.author, "(In [%d]) %s" %
                                    (self.rev, self.log), self.now)

        # Get all tickets related to these revisions
        tickets = self._collect_tickets(revisions, srcbranch)
        for tktid in tickets:
            ticket = Ticket(self.env, int(tktid))
            ticket.save_changes(self.author,
                                'Brought in [%s] (from [source:%s@%s %s] '
                                'to [source:%s@%s %s])' %
                                (self.rev, srcbranch, rev1, srcbranch,
                                 dstbranch, self.rev, dstbranch), self.now +
                                timedelta(seconds=1))
        if tickets:
            log = "%s ticket(s) %s" % (self.log,
                                       " ".join(['#%s' % k for k in
                                                 tickets.keys()]))
            self._update_log(log)

        return OK

    def _cmd_reverts(self, rev1, rev2, force, recursive=False):
        '''
        Branch revert
        Add backlink to the revision in all related tickets
        '''

        # Get all revisions to revert
        if rev2:
            print >> sys.stderr, "Cannot revert more than one changeset at once"
            self.finalize(ERROR)

        # Get src and dst branches
        srcbranch = self.proxy.find_revision_branch(int(rev1), self.bcre)
        dstbranch = self.proxy.find_revision_branch(int(self.rev), self.bcre)

        # Get log message of changeset to revert (need to be on the same
        # branch)
        logmsg = self.proxy.get_revision_log_message(int(rev1))
        logp = changeset_cmd_pattern.search(logmsg)
        if logp:
            first = logp.group('first')
            second = logp.group('second')
            revisions = self._collect_branch_revs(first, second)

            # Get all tickets related to these revisions
            tickets = self._collect_tickets(revisions, srcbranch)
            if not tickets:
                self._cmd_reverts(first, second, force, True)

            for tktid in tickets:
                ticket = Ticket(self.env, int(tktid))
                if logmsg:
                    log = " (''was: %s" % logmsg.splitlines()[0]
                    log += "'')"
                self.log = log.encode('utf8')
                ticket.save_changes(self.author,
                                    'Reverted in [%s] in [source:%s@%s %s] %s' %
                                    (self.rev, dstbranch, self.rev, dstbranch, log), self.now)

        if not recursive:
            # change log of previous invalid commit
            logmsg = logmsg.decode('utf-8')
            logmsg = '%s (\'\'reverted in [%s]\'\')' % (logmsg, self.rev)
            logmsg = logmsg.encode('utf-8')
            print >> sys.stderr, rev1, logmsg
            self.proxy.set_revision_log_message(int(rev1), logmsg)

            # delete rth:bring or rth:deliver
            if logmsg.startswith('Delivers'):
                self.proxy.set_revision_property(int(rev1), deliver_prop_name,
                                                 None)
            elif logmsg.startswith('Brings'):
                self.proxy.set_revision_property(int(rev1), bring_prop_name,
                                                 None)

            # Trac side update revision log
            repo = self.env.get_repository()
            repo.sync_changeset(self.rev)

        return OK

    def _cmd_delivers(self, rev1, rev2, force):
        '''
        Branch delivery
        Add backlink to the revision in all related tickets
        Update all closed tickets milestone
        '''
        # Get all revisions to deliver
        self.env.log.debug("> post_cmd_delivers [%s:%s]", rev1, rev2)
        revisions = self._collect_branch_revs(rev1, rev2)

        next_ms = self._next_milestone()

        # Get src and dst branches
        srcbranch = self.proxy.find_revision_branch(int(rev1), self.bcre)
        dstbranch = self.proxy.find_revision_branch(int(self.rev), self.bcre)

        # Get all tickets related to these revisions
        tickets = self._collect_tickets(revisions, srcbranch)

        for tktid in tickets:
            ticket = Ticket(self.env, int(tktid))
            if ticket['status'] == 'closed':
                if ticket['milestone'] == TBD_MILESTONE:
                    # if dstbranch is not trunk:
                    if dstbranch == trunk_directory:
                        ticket['milestone'] = next_ms
                    else:
                        ticket['milestone'] = NA_MILESTONE
            ticket.save_changes(self.author,
                                'Delivered in [%s] (from [source:%s@%s %s] to '
                                '[source:%s@%s %s])' %
                                (self.rev, srcbranch, rev1, srcbranch,
                                 dstbranch, self.rev, dstbranch), self.now)
            tn = TicketNotifyEmailEx(self.env, [self._get_author(), ])
            tn.notify(ticket, newticket=0, modtime=self.now)
        return OK

    def finalize(self, result):
        # Resync with repository
        repo = self.env.get_repository()
        repo.sync()

        if result == OK:
            try:
                eventfile = "%s/events/%d.tag" % (self.project, self.rev)
                fp = open(eventfile, "w")
                fp.write('please backup this revision\n')
                fp.close()
            except IOError as e:
                print >> sys.stderr, 'Error, can\'t create TAG file: %s' % e
        raise HookStatus(result)
