#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
testcase_SB_XX.py module

Test Cases are coded as following:
      SB_XX
        SB: sandboxes test cases.
        XX: test number.
"""

from testcase_abstract import (TestCaseAbstract, TestFunctionalTestSuite,
    TestCaseError)
from trac.tests.functional import *
import inspect
import sys


class SB_01(TestCaseAbstract):

    """
    Test name: SB_01

    Objective:
        * Verify creation message in ticket
        * Verify commit message in ticket
        * Verify close message in ticket

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
        # Creates tickets for sandboxes and trunk
        ticket_id = self._tester.create_ticket(summary='ticket',
                                               info={'keywords': ""})
        print >>sys.stderr, "SB_01.runTest.1"
        self.sandbox_create(ticket_id, close=True)
        print >>sys.stderr, "SB_01.runTest.2"


class SB_02(TestCaseAbstract):

    """
    Test name: SB_02, case commit on closed sandbox, failure must be reported

    Objective:
        * Verify creation message in ticket
        * Verify commit message in ticket
        * Verify close message in ticket
        * Verify commit is not allowed on closed sandbox

    Conditions:
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
        * Error message displayed:
            * The ticket x mentionned in the log message must be open.
    """

    def runTest(self):
        # Creates tickets for sandboxes and trunk
        print >>sys.stderr, "SB_02.runTest.1"
        ticket_id = self._tester.create_ticket(summary='ticket',
                                               info={'keywords': ""})
        sandbox_path = 'sandboxes/t%s' % ticket_id

        self.sandbox_create(ticket_id, close=True)

        # Update sandbox
        self.svn_update('sandboxes')

        # Add file data
        self.svn_add(sandbox_path, 'driver-spi.py', '# Driver spi module')

        # Try to commit on closed sandbox
        with self.assertRaises(TestCaseError) as cm:
            commit_msg = 'Refs #%s, Add driver.py module' % ticket_id
            self.svn_commit(sandbox_path, commit_msg)

        msg = cm.exception.message
        expected_msg = 'Commit blocked by pre-commit hook'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', get " \
                         "message='%s'" % (expected_msg, msg))

        expected_msg = "The ticket %s mentionned" \
                       " in the log message must be open." % ticket_id
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', get " \
                         "message='%s'" % (expected_msg, msg))


class SB_03(TestCaseAbstract):

    """
    Test name: SB_03, Verify that commit log the action command is followed
    by a least a space character.

    Objective:
        * Verify log action command is properly formated.

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
        * Error message must be displayed:
            * No known action in log message !
    """

    def runTest(self):
        # Creates tickets for sandboxes and trunk
        print >>sys.stderr, "SB_03.runTest.1"
        ticket_id = self._tester.create_ticket(summary='ticket',
                                               info={'keywords': ""})
        sandbox_path = 'sandboxes/t%s' % ticket_id

        commands = ['Creates', 'Refs', 'Closes', 'Fixes', 'Delivers', 'Brings',
                    'Terminates', 'Externals']

        for cmd in commands:
            with self.assertRaises(TestCaseError) as cm:
                commit_msg = '%s# Test missing space after command' % cmd
                self.svn_cp('trunk', sandbox_path, commit_msg)

            msg = cm.exception.message
            expected_msg = 'Commit blocked by pre-commit hook'
            self.assertFalse(msg.find(expected_msg) == -1,
                             msg="Missing error message='%s', get " \
                             "message='%s'" % (expected_msg, msg))

            expected_msg = 'No known action in log message !'
            self.assertFalse(msg.find(expected_msg) == -1,
                             msg="Missing error message='%s', get " \
                             "message='%s'" % (expected_msg, msg))


class SB_04(TestCaseAbstract):

    """
    Test name: SB_04, Verify that Creates is rejected when destination
    branch already exist.

    Objective:
        * Verify creation branch rejected if already exist.

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
        * Error message must be displayed:
            * Destination branch /branches/test already exists at [x]
    """

    def runTest(self):
        # Create test branch
        print >>sys.stderr, "SB_04.runTest.1"
        ci_msg = 'Creates test branch'
        rev = self.branch_create('branches/test', ci_msg, 'trunk')
        print >>sys.stderr, "SB_04.runTest.2"

        with self.assertRaises(TestCaseError) as cm:
            # Try to create a branch that already exist
            print >>sys.stderr, "SB_04.runTest.3"
            self.branch_create('branches/test', ci_msg, 'trunk')
            print >>sys.stderr, "SB_04.runTest.4"

        msg = cm.exception.message
        expected_msg = 'Commit blocked by pre-commit hook'
        print >>sys.stderr, "SB_04.runTest.5"
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', get " \
                         "message='%s'" % (expected_msg, msg))
        print >>sys.stderr, "SB_04.runTest.6"

        expected_msg = 'Destination branch ' \
                       '/branches/test already exists at [%s]' % rev
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', get " \
                         "message='%s'" % (expected_msg, msg))
        print >>sys.stderr, "SB_04.runTest.7"


class SB_05(TestCaseAbstract):

    """
    Test name: SB_05, case delivers sandbox on vendor/component,
    delivers must be rejected.

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
        * Delivers error message must displayed:
            * Cannot deliver to /vendor/component branch
    """

    def runTest(self):
        # Creates tickets for sandbox
        print >>sys.stderr, "SB_05.runTest.1"
        summary = 'ticket for delivers'
        ticket_id = self._tester.create_ticket(summary=summary,
                                               info={'keywords': ""})
        revs = self.sandbox_create(ticket_id, close=True)

        # Merge vendor/component with sandbox
        self.svn_merge('vendor/component', 'sandboxes/t%s' % ticket_id, revs)

        with self.assertRaises(TestCaseError) as cm:
            # Try to delivers on vendor
            commit_msg = 'Delivers [%s:%s]' % revs
            self.svn_commit('vendor/component', commit_msg)

        msg = cm.exception.message
        expected_msg = 'Commit blocked by pre-commit hook'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', get " \
                         "message='%s'" % (expected_msg, msg))

        expected_msg = 'Cannot deliver to /vendor/component branch'
        self.assertFalse(msg.find(expected_msg) == -1,
                         msg="Missing error message='%s', get " \
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
        suite.addTest(SB_01())
        suite.addTest(SB_02())
        suite.addTest(SB_03())
        suite.addTest(SB_04())
        suite.addTest(SB_05())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='functionalSuite')
