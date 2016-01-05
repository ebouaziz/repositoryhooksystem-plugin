#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
testcase_TK_XX.py module

Test Cases are coded as following:
      TK_XX
        TK: trunk test cases.
        XX: test number.
"""

from testcase_abstract import (TestCaseAbstract, TestFunctionalTestSuite,
                               TestCaseError)
from trac.tests.functional import *
import inspect


class TK_01(TestCaseAbstract):

    """
    Test name: TK_01, case delivers sandbox on trunk

    Objective:
        * Verify sandbox creation message in ticket
        * Verify sandbox commit message in ticket
        * Verify sandbox close message in ticket
        * Verify trunk delivers message
        * Verify sandbox delivered message

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * Expected ticket messages:
            * (In [x]) Creates tx for #1
            * (In [x]) Refs #x, Add driver.py module
            * (In [x]) Closes #x, Add driver-i2c.py module
    """

    def runTest(self):
        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'ThisOne', '09/04/18')

        try:
            self.do_delivers()
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'ThisOne')


class TK_02(TestCaseAbstract):

    """
    Test name: TK_02, case delivers no closed sandbox on trunk, deliver is
    rejected.

    Objective:
        * Verify sandbox creation message in ticket
        * Verify sandbox commit message in ticket
        * Verify sandbox close message in ticket
        * Verify trunk delivers message
        * Verify sandbox delivered message

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * Error message displayed
            * Not all tickets closed, delivery rejected
    """

    def runTest(self):
        # Creates tickets for sandbox
        summary = 'ticket for delivers'
        ticket_id = self._tester.create_ticket(summary=summary,
                                               info={'keywords': ""})
        revs = self.sandbox_create(ticket_id, close=False)

        # Update trunk
        self.svn_update('trunk')

        # Merge trunk with sandbox
        self.svn_merge('trunk',
                       'sandboxes/t%s' % ticket_id,
                       revs)

        with self.assertRaises(TestCaseError) as cm:
            commit_msg = 'Delivers [%s:%s]' % revs
            self.svn_commit('trunk', commit_msg)

        msg = cm.exception.message
        expected_msg = 'Commit blocked by pre-commit hook'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))

        expected_msg = 'Not all tickets closed, delivery rejected'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))


class TK_03(TestCaseAbstract):

    """
    Test name: TK_03, case bring and revert a commit

    Objective:
        * Verify sandbox creation message in ticket
        * Verify sandbox commit message in ticket
        * Verify revert message
        * Verify sandbox ticket revert message

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * Expected ticket messages:
            * (In [x]) Creates tx for #1
            * (In [x]) Refs #x, Add driver.py module
    """

    def runTest(self):
        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'ThisOne', '09/04/18')

        try:
            # Creates tickets for sandbox
            ticket_id, deliver_rev = self.do_delivers()

            # Revert brings
            cset = deliver_rev
            self.svn_merge('trunk', 'trunk', (-1 * cset, ))

            with self.assertRaises(TestCaseError) as cm:
                # Commit reverts
                commit_msg = 'Reverts [%s]' % cset
                self.svn_commit('trunk', commit_msg)

                msg = cm.exception.message
                expected_msg = 'Commit blocked by pre-commit hook'
                self.assertFalse(msg.find(expected_msg) == -1,
                                 msg="Missing error message='%s', got "
                                 "message='%s'" % (expected_msg, msg))

                expected_msg = 'No known action in log message !'
                self.assertFalse(msg.find(expected_msg) == -1,
                                 msg="Missing error message='%s', got "
                                 "message='%s'" % (expected_msg, msg))

            os.system("rm -r %s" % os.path.join(self._testenv.work_dir()))
            os.mkdir(self._testenv.work_dir())

            # checkout fresh copy
            self.svn_co()
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'ThisOne')


class TK_04(TestCaseAbstract):

    """
    Test name: TK_04, case multi branches commit, the commit is rejected

    Objective:
        * Verify that multi-branches commit is rejected by pre-commit

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * Error messages are displayed:
            * Commit blocked by pre-commit hook
            * Multiple branches in commit not allowed
    """

    def runTest(self):
        summary = 'ticket for test'
        ticket_id = self._tester.create_ticket(summary=summary,
                                               info={'keywords': ""})

        # Update root repository
        self.svn_update('')

        # Creates files
        for item in ('trunk', 'branches', 'vendor'):
            self.svn_add('%s/component' % item, 'test.py', '# dummy code')

        with self.assertRaises(TestCaseError) as cm:
            self.svn_commit('', 'Refs #%s, multi-branches commit' % ticket_id)

        msg = cm.exception.message
        expected_msg = 'Commit blocked by pre-commit hook'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))

        expected_msg = 'Multiple branches in commit not allowed'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))


class TK_05(TestCaseAbstract):

    """
    Test name: TK_05, case delivers with invalid ticket component Triage

    Objective:
        * Verify delivery is rejected by pre-commit hook

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * Error messages are displayed:
            * Commit blocked by pre-commit hook
            * No valid component, delivery rejected
    """

    def runTest(self):
        with self.assertRaises(TestCaseError) as cm:
            self.do_delivers(ticket_info=dict(component='Triage'))

        msg = cm.exception.message
        expected_msg = 'Commit blocked by pre-commit hook'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))

        expected_msg = 'Please correct component for #'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))


class TK_06(TestCaseAbstract):

    """
    Test name: TK_06, case delivers with invalid ticket component None

    Objective:
        * Verify delivery is rejected by pre-commit hook

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * Error messages are displayed:
            * Commit blocked by pre-commit hook
            * No valid component, delivery rejected
    """

    def runTest(self):
        with self.assertRaises(TestCaseError) as cm:
            self.do_delivers(ticket_info=dict(component='None'))

        msg = cm.exception.message
        expected_msg = 'Commit blocked by pre-commit hook'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))

        expected_msg = 'Please correct component for #'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))


class TK_07(TestCaseAbstract):

    """
    Test name: TK_07, case brings from vendor in sandbox and delivers on
    trunk

    Objective:
        * Verify brings from vendor in sandbox and delivers on
    trunk work properly

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * Expected ticket message:
            * (In [x]) Brings [y] (from /vendor/component)
    """

    def runTest(self):
        self.svn_update('')

        # Create file in vendor
        self.svn_add('vendor/component', 'vendor1.py', '# Dummy header')

        commit_msg = 'Admins , Add vendor.py'
        vendor_rev = self.svn_commit('vendor/component', commit_msg)
        self.verify_log_rev('vendor/component', commit_msg, vendor_rev)

        # Create sandbox
        summary = 'ticket for sandbox'
        ticket_id = self._tester.create_ticket(summary=summary,
                                               info={'keywords': ""})

        self.sandbox_create(ticket_id, 'trunk', close=False)
        sandbox_path = 'sandboxes/t%s' % ticket_id

        # Merge sandbox with vendor changeset
        self.svn_merge(sandbox_path, 'vendor/component', (vendor_rev,))
        commit_msg = 'Brings [%s]' % vendor_rev
        rev = self.svn_commit(sandbox_path, commit_msg)

        msg = 'Brings [%s] (from [source:/vendor/component@%s /vendor/' \
              'component])' % (vendor_rev, vendor_rev)
        self.verify_log_rev(sandbox_path, msg, rev)

        msg = '(In [%s]) Brings [%s] (from /vendor/component)' % (rev,
                                                                 vendor_rev)
        self.verify_ticket_entry(ticket_id, rev, msg, sandbox_path)


class TK_08(TestCaseAbstract):

    """
    Test name: TK_08, update svn:externals

    Objective:
        * Verify

    Conditions:
        * Repository structure:
            * branches
                * component (empty)
            * sandboxes
                * component (empty)
            * trunk
                * component (empty)
            * vendor
                * component (empty)

    Pass Criteria:
        * No error on commit
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        branch_rev = self.svn_update('branches')

        # Set svn:external property
        self.svn_property_set('trunk', 'svn:externals',
                              '%s/branches@%s misc' % \
                              (self._testenv.repo_path_for_initenv(),
                               branch_rev))

        # REMARK: project is created under ../trac/testenv/trac by functional
        # test framework so in commit message we indicate trac as project name
        self.svn_commit('trunk',
                        'Externals [trac:source:branches@%s]' % branch_rev)


class TK_09(TestCaseAbstract):

    """
    Test name: TK_09, sandbox from trunk, no open valid milestone,
               no close allowed

    Objective:
        * check that ticket cannot be closed if no suitable
          milestone is available

    Pass Criteria:
        * close operation should fail
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # this does not work anymore as the roadmap page loads content
        # dynamically
        # self._tester.create_milestone('Next', '09/04/18')

        # remove predefined milestones
        self._testenv._tracadmin('milestone', 'remove', 'milestone1')
        self._testenv._tracadmin('milestone', 'remove', 'milestone2')
        self._testenv._tracadmin('milestone', 'remove', 'milestone3')
        self._testenv._tracadmin('milestone', 'remove', 'milestone4')

        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'Next', '09/04/18')

        try:
            # create ticket
            summary = 'ticket for tk_09'
            info = {'milestone': 'Next'}
            ticket_id = self._tester.create_ticket(summary=summary, info=info)

            # create sandbox (open + commit + close)
            with self.assertRaises(TestCaseError) as cm:
                self.sandbox_create(ticket_id, close=True)

            msg = cm.exception.message
            expected_msg = 'No defined next milestone for branch'
            self.assertFalse(msg.find(expected_msg) == -1,
                             msg="Missing error message='%s', got "
                             "message='%s'" % (expected_msg, msg))
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'Next')


class TK_10(TestCaseAbstract):

    """
    Test name: TK_10, sandbox from trunk, one open milestone,
               other milestone set manually, close allowed

    Objective:
        * check that ticket can be closed if a valid milestone is set manually
          and that the milestone is not altered

    Pass Criteria:
        * close operation should succeed
        * milestone should be left as "thisone"
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # remove predefined milestones
        self._testenv._tracadmin('milestone', 'remove', 'milestone1')
        self._testenv._tracadmin('milestone', 'remove', 'milestone2')
        self._testenv._tracadmin('milestone', 'remove', 'milestone3')
        self._testenv._tracadmin('milestone', 'remove', 'milestone4')

        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'Next', '09/04/18')
        # create an opened milestone
        self._testenv._tracadmin('milestone', 'add', 'notthisone', '09/04/16')
        # create an completed milestone
        self._testenv._tracadmin('milestone', 'add', 'thisone', '09/04/17')
        self._testenv._tracadmin('milestone', 'complete', 'thisone', '01/01/17')

        try:
            # create ticket
            summary = 'ticket for tk_10'
            info = {'milestone': 'Next'}
            ticket_id = self._tester.create_ticket(summary=summary, info=info)
            self.sandbox_create(ticket_id, close=False)
            self._tester.ticket_set_milestone(ticket_id, 'thisone')
            # close ticket
            sandbox_path = 'sandboxes/t%s' % ticket_id
            self.svn_add(sandbox_path, 'driver-i2c_213.py', '# Header')
            commit_msg = 'Closes #%s, Add driver-i2c_123.py module' % ticket_id
            revision = self.svn_commit(sandbox_path, commit_msg)
            # check rev msg and ticket
            self.verify_log_rev(sandbox_path, commit_msg, revision)
            commit_msg = "(In [%s]) %s" % (revision, commit_msg)
            self.verify_ticket_entry(ticket_id, revision, commit_msg,
                                     sandbox_path, "thisone")
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'Next')
            self._testenv._tracadmin('milestone', 'remove', 'notthisone')
            self._testenv._tracadmin('milestone', 'remove', 'thisone')


class TK_11(TestCaseAbstract):

    """
    Test name: TK_11, sandbox from trunk, two open milestones,
               close ticket, close allowed

    Objective:
        * check that ticket can be closed if a valid milestone exist
        * check that the milestone is automatically set correctly

    Pass Criteria:
        * close operation should succeed
        * milestone should be set automatically to "SDK2-thisone"
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # remove predefined milestones
        self._testenv._tracadmin('milestone', 'remove', 'milestone1')
        self._testenv._tracadmin('milestone', 'remove', 'milestone2')
        self._testenv._tracadmin('milestone', 'remove', 'milestone3')
        self._testenv._tracadmin('milestone', 'remove', 'milestone4')

        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'Next', '09/04/18')
        # create two opened milestones
        self._testenv._tracadmin('milestone', 'add', 'notthisone', '01/01/16')
        self._testenv._tracadmin('milestone', 'add',
                                 'SDK2-thisone', '09/04/17')
        self._testenv._tracadmin('milestone', 'add',
                                 'SDK2-notthisone', '01/01/18')

        try:
            # create ticket
            summary = 'ticket for tk_11'
            info = {'milestone': 'Next'}
            ticket_id = self._tester.create_ticket(summary=summary, info=info)
            self.sandbox_create(ticket_id, close=False)
            # close ticket
            sandbox_path = 'sandboxes/t%s' % ticket_id
            self.svn_add(sandbox_path, 'driver-i2c_213.py', '# Header')
            commit_msg = 'Closes #%s, Add driver-i2c_123.py module' % ticket_id
            revision = self.svn_commit(sandbox_path, commit_msg)
            # check rev msg and ticket
            self.verify_log_rev(sandbox_path, commit_msg, revision)
            commit_msg = "(In [%s]) %s" % (revision, commit_msg)
            self.verify_ticket_entry(ticket_id, revision, commit_msg,
                                     sandbox_path, "SDK2-thisone")
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'Next')
            self._testenv._tracadmin('milestone', 'remove', 'notthisone')
            self._testenv._tracadmin('milestone', 'remove', 'SDK2-notthisone')
            self._testenv._tracadmin('milestone', 'remove', 'SDK2-thisone')


class TK_12(TestCaseAbstract):

    """
    Test name: TK_12, sandbox from a branch, one open milestone not matching
               the branch name, close forbidden

    Objective:
        * check that ticket cannot be closed

    Pass Criteria:
        * close operation should fails
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # remove predefined milestones
        self._testenv._tracadmin('milestone', 'remove', 'milestone1')
        self._testenv._tracadmin('milestone', 'remove', 'milestone2')
        self._testenv._tracadmin('milestone', 'remove', 'milestone3')
        self._testenv._tracadmin('milestone', 'remove', 'milestone4')
        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'Next', '09/04/18')
        # create two opened milestones
        self._testenv._tracadmin('milestone', 'add',
                                 'lameproject-notthisone', '01/01/18')

        try:
            branchname = 'superproject'
            # create ticket
            summary = 'ticket for tk_12'
            info = {'milestone': 'Next'}
            ticket_id = self._tester.create_ticket(summary=summary, info=info)
            # create project branch
            branch = 'branches/'+branchname+'-1.x'
            self.branch_create(branch, "Creates new branch for TK_12")
            # create sandbox from
            with self.assertRaises(TestCaseError) as cm:
                self.sandbox_create(ticket_id, branch_from=branch, close=True)
            # check error message
            msg = cm.exception.message
            expected_msg = 'No defined next milestone for branch'
            self.assertFalse(msg.find(expected_msg) == -1,
                             msg="Missing error message='%s', got "
                             "message='%s'" % (expected_msg, msg))
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'Next')
            self._testenv._tracadmin('milestone', 'remove',
                                     'lameproject-notthisone')


class TK_13(TestCaseAbstract):

    """
    Test name: TK_13, sandbox from branch, two open milestones, one matching
               the branch name, close ticket, close allowed

    Objective:
        * check that ticket can be closed if a valid milestone exists
        * check that the milestone is automatically set correctly

    Pass Criteria:
        * close operation should succeed
        * milestone should be set automatically the matching milestone
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # remove predefined milestones
        self._testenv._tracadmin('milestone', 'remove', 'milestone1')
        self._testenv._tracadmin('milestone', 'remove', 'milestone2')
        self._testenv._tracadmin('milestone', 'remove', 'milestone3')
        self._testenv._tracadmin('milestone', 'remove', 'milestone4')

        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'Next', '09/04/18')
        # create two opened milestones
        self._testenv._tracadmin('milestone', 'add', 'notthisone', '01/01/17')
        branchname = 'superproject'
        self._testenv._tracadmin('milestone', 'add',
                                 branchname+'-thisone', '01/01/18')

        try:
            # create ticket
            summary = 'ticket for tk_13'
            info = {'milestone': 'Next'}
            ticket_id = self._tester.create_ticket(summary=summary, info=info)
            # create project branch
            branch = 'branches/'+branchname+'-2.x'
            self.branch_create(branch, "Creates new branch for TK_13")
            # sandbox
            self.sandbox_create(ticket_id, branch_from=branch, close=True)
            self.verify_ticket_milestone(ticket_id, branchname+'-thisone')
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'Next')
            self._testenv._tracadmin('milestone', 'remove', 'notthisone')
            self._testenv._tracadmin('milestone', 'remove',
                                     branchname+'-thisone')


class TK_14(TestCaseAbstract):

    """
    Test name: TK_14, sandbox from branch, two open milestones, one matching
               the branch name, exception entry for the branch,
               close ticket, close allowed

    Objective:
        * check that ticket can be closed if a valid milestone exists
        * check that the milestone is automatically set correctly

    Pass Criteria:
        * close operation should succeed
        * milestone should be set automatically according to the registered
          exception
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # remove predefined milestones
        self._testenv._tracadmin('milestone', 'remove', 'milestone1')
        self._testenv._tracadmin('milestone', 'remove', 'milestone2')
        self._testenv._tracadmin('milestone', 'remove', 'milestone3')
        self._testenv._tracadmin('milestone', 'remove', 'milestone4')

        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'Next', '09/04/18')
        # create two opened milestones
        branchname = 'superproject_dvt'
        self._testenv._tracadmin('milestone', 'add',
                                 branchname+'-notthisone', '01/01/18')
        self._testenv._tracadmin('milestone', 'add',
                                 'Historical-msname', '01/01/19')

        try:
            # create ticket
            summary = 'ticket for tk_14'
            info = {'milestone': 'Next'}
            ticket_id = self._tester.create_ticket(summary=summary, info=info)
            # create project branch
            branch = 'branches/'+branchname+'-3.y'
            self.branch_create(branch, "Creates new branch for TK_14")
            # sandbox
            self.sandbox_create(ticket_id, branch_from=branch, close=True)
            self.verify_ticket_milestone(ticket_id, 'Historical-msname')
        finally:
            self._testenv._tracadmin('milestone', 'remove', 'Next')
            self._testenv._tracadmin('milestone', 'remove', 'Historical-msname')
            self._testenv._tracadmin('milestone', 'remove',
                                     branchname+'-notthisone')


class TK_15(TestCaseAbstract):

    """
    Test name: TK_15, sandbox created from trunk and immediately deleted

    Objective:
        * check that the termination message is added to the ticket

    Pass Criteria:
        * termination message in the ticket
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # remove predefined milestones
        self._testenv._tracadmin('milestone', 'remove', 'milestone1')
        self._testenv._tracadmin('milestone', 'remove', 'milestone2')
        self._testenv._tracadmin('milestone', 'remove', 'milestone3')
        self._testenv._tracadmin('milestone', 'remove', 'milestone4')

        # create 'Next' milestone using admin interface
        self._testenv._tracadmin('milestone', 'add', 'Next', '09/04/18')
        self._testenv._tracadmin('milestone', 'add', 'ThisOne', '09/04/18')

        try:
            # create ticket
            summary = 'ticket for tk_15'
            info = {'milestone': 'Next'}
            ticket_id = self._tester.create_ticket(summary=summary, info=info)

            # create sandbox
            sandbox_path = 'sandboxes/t%s' % ticket_id
            self.create_sandbox(ticket_id, "trunk", sandbox_path)

            # terminate sandbox
            self.terminate_sandbox((ticket_id,), sandbox_path)

        finally:
            self._testenv._tracadmin('milestone', 'remove', 'Next')
            self._testenv._tracadmin('milestone', 'remove', 'ThisOne')


class TK_16(TestCaseAbstract):
    """
    Test name: TK_16, a ticket is used to bring another ticket from the trunk
               to a branch. The ticket new does not have a refs/fixes commit,
               only a brings message.
               This is a regression test for #tools865

    Objective:
        * check that the pre-commit hook can find the associated ticket from
          the sandbox creation message

    Pass Criteria:
        * the delivery on the destination branch must succeed
        * the delivery message must appear on the new ticket
        * the bring message must appear in the original ticket
    """

    def runTest(self):
        # Update trunk
        self.svn_update('')

        # create branch from trunk
        self.branch_create('branches/my_branch', 'Admins! branch creation')

        # create ticket to be brought
        summary = 'ticket for tk_16'
        ticket_id, rev = self.do_delivers()

        # create ticket used to bring 1st ticket to branch
        summary = 'bring tk_16 to my_branch'
        ticket_id_2 = self._tester.create_ticket(summary=summary)
        sb_path = 'sandboxes/t%s' % ticket_id_2
        rev_2 = self.create_sandbox(ticket_id_2, 'branches/my_branch',
                                    sb_path)

        # bring previous deliver in new sandbox
        self.svn_merge(sb_path, 'trunk', (rev,))
        commit_msg = 'Brings [%s]' % rev
        rev = self.svn_commit(sb_path, commit_msg)

        # check that the original ticket as a message stating it has been
        # brought to the new sandbox
        msg = 'Brought in [%s] (from /trunk to %s)' % (rev, sb_path, )
        self.verify_ticket_entry(ticket_id, rev, msg, sb_path)

        # deliver new sandbox to branch
        self.svn_merge('branches/my_branch', sb_path, (rev,))
        commit_msg = 'Delivers [%s]' % rev
        try:
            rev = self.svn_commit('branches/my_branch', commit_msg)
        except Exception, e:
            raise AssertionError("Delivery failed: %s" % e)

        # check that the delivery message appears in the new ticket
        msg = 'Delivered in [%s] (from /%s to /branches/my_branch)' % \
              (rev, sb_path, )
        self.verify_ticket_entry(ticket_id_2, rev, msg, sb_path)

def functionalSuite(suite=None):
    if not has_svn:
        raise Exception("Missing python-subversion module, you may need to "
            "copy it from you subversion installation to you virtualenv.")

    def is_testcase(obj):
        """ is_testcase """

        if inspect.isclass(obj) and getattr(obj, "runTest", False):
            return True

        return False

    _, file_name = os.path.split(__file__)
    module_name = file_name.replace('.py', '')
    with file("./%s_test_docs.txt" % module_name, "wt") as _fd:
        module = __import__(module_name)

        testcases = inspect.getmembers(module, is_testcase)

        _fd.write("=== %s ===\n\n" % module_name)
        for _, test in testcases:
            _fd.write("{{{\n%s\n}}}\n\n\n" % inspect.getdoc(test))

    if not suite:
        suite = TestFunctionalTestSuite()
        suite.addTest(TK_01())
        suite.addTest(TK_02())
        suite.addTest(TK_03())
        suite.addTest(TK_04())
        suite.addTest(TK_05())
        suite.addTest(TK_06())
        suite.addTest(TK_07())
        suite.addTest(TK_08())
        suite.addTest(TK_09())
        suite.addTest(TK_10())
        suite.addTest(TK_11())
        suite.addTest(TK_12())
        suite.addTest(TK_13())
        suite.addTest(TK_14())
        suite.addTest(TK_15())
        suite.addTest(TK_16())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='functionalSuite')
