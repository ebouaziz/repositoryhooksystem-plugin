#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
testcase_BR_XX.py module

Test Cases are coded as following:
      BR_XX
        BR: branches test cases.
        XX: test number.
"""

import os
import unittest
from testcase_abstract import TestCaseAbstract, TestFunctionalTestSuite
from trac.tests.functional import *
import inspect


class BR_01(TestCaseAbstract):

    """
    Test name: BR_01, case brings from trunk to branch

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
        # Creates tickets for sandbox
        summary = 'ticket for delivers'
        ticket_id = self._tester.create_ticket(summary=summary,
                                               info={'keywords': ""})
        revs = self.sandbox_create(ticket_id, branch_from='trunk/')

        # Creates brings branch
        ci_msg = 'Creates brings branch'
        revision = self.branch_create('branches/brings', ci_msg)
        self.svn_update('branches')
        self.verify_log_rev('branches/brings', ci_msg, revision)

        # Update trunk
        self.svn_update('trunk')

        # Merge trunk with sandbox
        self.svn_merge('trunk', 'sandboxes/t%s' % ticket_id, revs)
        ci_msg = 'Delivers [%s:%s]' % revs
        trunk_rev = self.svn_commit('trunk', ci_msg)

        ci_msg = '%s\n * #%s (Component): %s' % (ci_msg, ticket_id, summary)
        self.verify_log_rev('trunk', ci_msg, trunk_rev)

        # Verify sandbox ticket
        msg = 'Delivered in [%s] (from /sandboxes/t%s to /trunk)' % \
              (trunk_rev, ticket_id)
        self.verify_ticket_entry(ticket_id, trunk_rev, msg, 'trunk')

        # Brings trunk revision on branch
        self.svn_merge('branches/brings', 'trunk', (trunk_rev,))
        ci_msg = 'Brings [%s]' % trunk_rev
        revision = self.svn_commit('branches/brings', ci_msg)

        ci_msg = 'Brings [%s] (from [source:/trunk@%s /trunk]) ' \
                 'ticket(s) #%s' % (trunk_rev, trunk_rev, ticket_id)
        self.verify_log_rev('branches/brings', ci_msg, revision)

        # Verify ticket
        msg = r'Brought in [%s] (from /trunk to /branches/brings)' % revision
        self.verify_ticket_entry(ticket_id, revision, msg, 'branches/brings')


class BR_02(TestCaseAbstract):

    """
    Test name: BR_02, case brings from trunk to branch with multiple tickets.

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

    def _sandbox_delivers(self):
        # Creates tickets for sandbox
        summary = 'ticket for delivers'
        ticket_id = self._tester.create_ticket(summary=summary,
                                               info={'keywords': ""})
        revs = self.sandbox_create(ticket_id, branch_from='trunk/')

        # Update trunk
        self.svn_update('trunk')

        # Merge trunk with sandbox
        self.svn_merge('trunk', 'sandboxes/t%s' % ticket_id, revs)
        ci_msg = 'Delivers [%s:%s]' % revs
        trunk_rev = self.svn_commit('trunk', ci_msg)

        ci_msg = '%s\n * #%s (Component): %s' % (ci_msg, ticket_id, summary)
        self.verify_log_rev('trunk', ci_msg, trunk_rev)

        # Verify sandbox ticket
        msg = r'Delivered in [%s] (from /sandboxes/t%s to /trunk)' % \
              (trunk_rev, ticket_id)
        self.verify_ticket_entry(ticket_id, trunk_rev, msg, 'trunk')

        return ticket_id, trunk_rev

    def runTest(self):
        # Creates brings branch if necessary
        if not os.path.isdir(os.path.join(self._testenv.work_dir(),
                                          'branches/brings')):
            ci_msg = 'Creates brings branch'
            revision = self.branch_create('branches/brings', ci_msg)
            self.svn_update('branches')
            self.verify_log_rev('branches/brings', ci_msg, revision)

        # First delivers sandbox
        ticket_id1, trunk_rev1 = self._sandbox_delivers()

        # second delivers sandbox
        ticket_id2, trunk_rev2 = self._sandbox_delivers()

        revs = (trunk_rev1, trunk_rev2)
        tickets = (ticket_id1, ticket_id2)

        # Bring trunk revision on branch
        self.svn_merge('branches/brings', 'trunk', revs)
        ci_msg = 'Brings [%s:%s]' % revs
        revision = self.svn_commit('branches/brings', ci_msg)

        args = []
        args.extend(revs)
        args.append(revs[-1])
        args.extend(tickets)
        ci_msg = 'Brings [%s:%s] (from [source:/trunk@%s /trunk]) ' \
                 'ticket(s) #%s #%s' % tuple(args)
        self.verify_log_rev('branches/brings', ci_msg, revision)

        # Verify tickets
        msg = r'Brought in [%s] (from /trunk to /branches/brings)' % revision
        self.verify_ticket_entry(ticket_id1, revision, msg, 'branches/brings')

        msg = r'Brought in [%s] (from /trunk to /branches/brings)' % revision
        self.verify_ticket_entry(ticket_id2, revision, msg, 'branches/brings')


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
        suite.addTest(BR_01())
        suite.addTest(BR_02())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='functionalSuite')
