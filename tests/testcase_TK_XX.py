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
        self.do_delivers()


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

        expected_msg = 'Please correct component of #'
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

        expected_msg = 'Please correct component of #'
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
    Test name: TK_09, sandbox from trunk, no open milestone, no close allowed

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
        print "milestone created"

        # create ticket
        summary = 'ticket for tk_09'
        info = {'milestone': 'Next'}
        ticket_id = self._tester.create_ticket(summary=summary, info=info)
        print "ticket created"

        # create sandbox (open + commit + close)
        with self.assertRaises(TestCaseError) as cm:
            self.sandbox_create(ticket_id, close=True)
            print "sandbox created and closed" # should not be displayed

        msg = cm.exception.message
        expected_msg = 'No defined next milestone'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', got "
                         "message='%s'" % (expected_msg, msg))



def functionalSuite(suite=None):
    if not has_svn:
        raise Exception("Missing python-subversion module")

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
        #suite.addTest(TK_01())
        #suite.addTest(TK_02())
        #suite.addTest(TK_03())
        #suite.addTest(TK_04())
        #suite.addTest(TK_05())
        #suite.addTest(TK_06())
        #suite.addTest(TK_07())
        #suite.addTest(TK_08())
        suite.addTest(TK_09())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='functionalSuite')
