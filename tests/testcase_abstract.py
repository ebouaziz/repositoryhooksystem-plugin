#!/usr/bin/env python
# -*- coding: utf-8 -*-

from random import randint
from subprocess import Popen, PIPE
from xml.etree import ElementTree
import re
import sys
import urlparse
import xml.etree.ElementTree as et
from trac.tests.functional import *


# Test case exception
class TestCaseError(Exception):
    pass

class TestSuiteEnvironment(SvnFunctionalTestEnvironment):

    """
    TestSuiteEnvironment class, Trac test environment used for test suites
    creation.

    This class implements post_create method:
        * init created repository structure
        * update environment trac.ini file
    """

    def __init__(self, dirname, port, url):
        """
        __init__ method.

        :param dirname:
        :type dirname:
        :param port:
        :type port:
        :param url:
        :type url:
        """
        SvnFunctionalTestEnvironment.__init__(self, dirname, port, url)
        if not getattr(self, "logfile", None):
            self.logfile = logfile

        # Add component
        self._tracadmin('component', 'add', 'Triage')
        self._tracadmin('component', 'add', 'None')
        self._tracadmin('component', 'add', 'Component')

    def _init_repository(self):
        """
        This method inits repository structure as following:
            * branches
                * components (empty)
            * sandboxes
                * components (empty)
            * trunk
                * components (empty)
            * vendor
                * components (empty)

        The following svn hooks are created:
            * pre-commit hook file
            * post-commit hook file

        REMARK: self.dirname is path to Trac created test env
        """

        # Creates repository structure
        directories = []
        for item in ('branches', 'trunk', 'sandboxes', 'vendor'):
            directories.append(item)
            directories.append('/'.join([item, 'component']))

        commit_message = 'Create repository structure.'
        self.svn_mkdir(directories, commit_message)

        # Creates svn hooks
        svn_hooks_path = os.path.join(self.repo_path_for_initenv(), 'hooks')
        trac_dir = os.path.abspath(os.path.join(self.dirname, '..'))
        trac_env = os.path.abspath(os.path.join(self.dirname, 'trac'))

        # Creates egg cache folder
        egg_cache_path = os.path.join(self.dirname, 'egg_cache')
        os.makedirs(egg_cache_path)

        # Get trac plugins path
        plugins_path = os.environ.get('TRAC_PLUGINS_PATH',
                                      os.path.join('/tmp', 'plugins'))

        # Trac hook module
        trac_hook_script = os.environ.get('TRAC_HOOKS_PATH',
                                          os.path.join(plugins_path,
                                                       'trac_hook.py'))
        # Python PATH
        python_path = os.environ.get('PYTHONPATH', trac_dir)

        # Python used to start trac env
        trac_python = os.environ.get('TRAC_PYTHON', 'python')

        # Post commit hook
        post_commit = '#!/bin/sh\n' \
                      'REPOS="$1"\n' \
                      'REV="$2"\n' \
                      'SCRIPT=%s\n' \
                      'export PYTHON_EGG_CACHE=%s\n' \
                      'export PYTHONPATH=%s\n' \
                      'TRAC_ENV=%s\n' \
                      '%s $SCRIPT --hook=post-commit --user=admin ' \
                      '--project=$TRAC_ENV --repository=$REPOS svn ' \
                      '--revision=$REV' % (trac_hook_script,
                                           egg_cache_path,
                                           python_path,
                                           trac_env,
                                           trac_python)

        hook_path = os.path.join(svn_hooks_path, 'post-commit')
        with open(hook_path, 'wt') as fd:
            fd.write(post_commit)
        os.chmod(hook_path, 0o777)

        # Pre commit hook
        pre_commit = '#!/bin/sh\n' \
                     'REPOS="$1"\n' \
                     'TXN="$2"\n' \
                     'SCRIPT=%s\n' \
                     'export PYTHON_EGG_CACHE=%s\n' \
                     'export PYTHONPATH=%s\n' \
                     'TRAC_ENV=%s\n' \
                     '%s $SCRIPT --hook=pre-commit --user=admin ' \
                     '--project=$TRAC_ENV --repository=$REPOS svn ' \
                     '--transaction=$TXN' % (trac_hook_script,
                                             egg_cache_path,
                                             python_path,
                                             trac_env,
                                             trac_python)
        hook_path = os.path.join(svn_hooks_path, 'pre-commit')
        with open(hook_path, 'wt') as fd:
            fd.write(pre_commit)
        os.chmod(hook_path, 0o777)

    def _init_trac_ini(self, env):
        """
        This method initialises environment Trac.ini file.

        :param env: Trac environment
        :type env:
        """

        # Get trac plugins path
        plugins_path = os.environ.get('TRAC_PLUGINS_PATH', '/tmp/plugins')

        config = env.config
        config.set('components',
                   'repository_hook_system.*',
                   'enabled')
        config.set('trac',
                   'plugins_dir',
                   plugins_path)
        config.set('inherit',
                   'plugins_dir',
                   plugins_path)
        config.set(r'revtree',
                   r'branch_re',
                   r'^(?:(?P<branch>trunk|(?:branches|sandboxes|vendor|'
                   r'platforms)/(?P<branchname>[^/]+))|(?P<tag>tags/'
                   r'(?P<tagname>[^/]+)))(?:/(?P<path>.*))?$')
        config.set('ticket',
                   'default_component',
                   'Component')

        config.save()

    def post_create(self, env):
        """
        Post create method, this method is called after Trac environment
        creation.

        This method completes test environment creation by initializing test
        repository structure, and updating trac.ini environment configuration
        file.

        :param env: Trac environment
        :type env: TestSuiteEnvironment object
        """
        SvnFunctionalTestEnvironment.post_create(self, env)

        # Init repository structure
        self._init_repository()

        # Init trac.ini configuration
        self._init_trac_ini(env)

    def process_call(self, args, path='', environ=None):
        """
        This method is used to invoke command line,

        :param args: command line
        :type args:str or list(str)
        :param path: path where command will be executed, this path is relative
        to the test environment working directory.

        :type path: str
        :param environ: Python environment for command execution
        :type environ:Python environment object
        :raises: Exception if command execution result returns non zero value
        """
        cwd = os.path.join(self.work_dir(), path)

        environ = environ or os.environ.copy()
        environ['LC_ALL'] = 'C'  # Force English messages
        # print '>>> run', args
        proc = Popen(args, stdout=PIPE, stderr=PIPE,
                     close_fds=close_fds, cwd=cwd, env=environ)
        (data, error) = proc.communicate()
        if proc.wait():
            self.logfile.write(error)
            raise TestCaseError('%s' % error)

        self.logfile.write(data)
        return data


class TestFunctionalTestSuite(FunctionalTestSuite):

    """
    Test suite used to create functional test suite.
    """
    env_class = TestSuiteEnvironment

    def setUp(self, port=None):
        """
        This method is used to setup test suite before tests running.

        :param port: tcp port used for trac server creation
        :type port: str or int

        REMARK: tickets can be created only after Trac server creation.
        """
        FunctionalTestSuite.setUp(self, port=port)


class TestCaseAbstract(FunctionalTwillTestCaseSetup):

    """
    TestCase Abstract class, this class provides generic methods for writing
    tests.
    """

    def do_delivers(self, ticket_info=None):
        # Creates tickets for sandbox
        summary = 'ticket for delivers'

        info = ticket_info or {'keywords': ""}
        ticket_id = self._tester.create_ticket(summary=summary,
                                               info=info)
        revs = self.sandbox_create(ticket_id, close=True)

        # Update trunk
        self.svn_update('trunk')

        # Merge trunk with sandbox
        self.svn_merge('trunk', 'sandboxes/t%s' % ticket_id, revs)
        commit_msg = 'Delivers [%s:%s]' % revs
        rev = self.svn_commit('trunk', commit_msg)

        # Verify revision log
        commit_msg = '%s\n * #%s (Component):' \
                     ' %s' % (commit_msg, ticket_id, summary)
        self.verify_log_rev('trunk', commit_msg, rev)

        # Verify sandbox ticket
        msg = r'Delivered in [%s] (from /sandboxes/t%s to /trunk)' % \
              (rev, ticket_id)
        self.verify_ticket_entry(ticket_id, rev, msg, 'trunk')

        return (ticket_id, rev)

    def svn_co(self, path=''):
        cmd = ['svn', 'co',
               self._testenv.repo_url(),
               os.path.join(self._testenv.work_dir(), path)]
        self._testenv.process_call(cmd)

    def svn_cp(self, src, dest, msg):
        """
        SVN copy method, used to make a copy of a repository component. For
        example used to create sandbox from trunk.

        :param src: source for copy, relative path to test repository
        :type src: str
        :param dest: destination for copy, relative path to test
        repository structure
        :type dest: str
        :param msg: commit message
        :type msg: str
        :raises: Exception if revision can not be parsed from output
        """

        cmd = ['svn', 'cp',
               urlparse.urljoin(self._testenv.repo_url() + '/', src),
               urlparse.urljoin(self._testenv.repo_url() + '/', dest),
               '-m', msg]

        output = self._testenv.process_call(cmd)
        try:
            rev = re.search(r'Committed revision ([0-9]+)\.', output).group(1)
        except Exception as e:
            args = e.args + (output, )
            raise Exception(*args)

        # Update repository root
        self.svn_update('')

        return int(rev)

    def svn_add(self, path, filename, data):
        """
        SVN method to add a file to the specified path, the created file is
        added by using svn add command.

        :param path: path used for file creation
        :type path: str
        :param filename: file name to add
        :type filename: str
        :param data: file data
        :type data: str
        """
        # Create file
        path = path[1:] if path.startswith(os.sep) else path
        file_path = os.path.join(self._testenv.work_dir(), path, filename)
        with open(file_path, 'wt') as fd:
            fd.write(data)

        # Add created file
        self._testenv.process_call(['svn', 'add', filename], path=path)

    def svn_commit(self, path, msg):
        """
        SVN method to commit modified files in specified path.

        :param path: path used for commit operation
        :type path: str
        :param msg: commit msg
        :type msg: str
        :raises: Exception if revision can not be parsed from output
        """
        cmd = ['svn', 'ci', '-m', msg]

        output = self._testenv.process_call(cmd, path=path)
        try:
            revision = re.search(r'Committed revision ([0-9]+)\.',
                                 output).group(1)
        except Exception as e:
            args = e.args + (output, )
            raise Exception(*args)

        self.svn_update('')

        return int(revision)

    def svn_update(self, path):
        """
        SVN update command, used to update specified path

        :param path: path to update
        :type path: str
        :raises: Exception if revision can not be parsed from output
        """

        cmd = ['svn', 'up', os.path.join(self._testenv.work_dir(), path)]

        output = self._testenv.process_call(cmd, path=path)
        try:
            rev = re.search(r'(Updated to revision|At revision) ([0-9]+)\.',
                            output).group(2)
        except Exception as e:
            args = e.args + (output, )
            raise Exception(*args)
        return int(rev)

    def svn_property_set(self, path, property_name, property_value):
        """

        :param path: path on which property must be set
        :param property_name: property name
        :param property_value: property value
        """

        cmd = ['svn', 'propset', property_name, property_value,
               os.path.join(self._testenv.work_dir(), path)]

        output = self._testenv.process_call(cmd, path=path)
        try:
            re.search(r"property 'svn:externals' set on '\.'", output).group(0)
        except Exception as e:
            args = e.args + (output, )
            raise Exception(*args)

    def svn_merge(self, path, source, revs):
        """
        SVN merge command

        :param path: path used for merging
        :type path: str
        :param source: merging sources
        :type source: str
        :param revs: revision to merge
        :type revs: tuple(rev1, rev2)
        :raises: Exception if revision can not be parsed from output
        """

        if len(revs) > 1:
            cset = '-r%s:%s' % (revs[0] - 1, revs[1])
            merge_msg = 'Recording mergeinfo for merge of r%s through r%s'
        else:
            cset = '-c %s' % revs[0]

            if revs[0] < 0:
                merge_msg = 'Recording mergeinfo for reverse merge of r%s'
            else:
                merge_msg = 'Recording mergeinfo for merge of r%s'
            revs = abs(revs[0])

        cmd = ['svn',
               'merge',
               cset,
               self._testenv.repo_url() + '/' + source]

        output = self._testenv.process_call(cmd, path=path)

        match = re.search(merge_msg % revs, output)
        if not match:
            raise TestCaseError("Error during merging %s for "
                                "revision(s)='%s'" % (source, revs))

    def svn_log_rev(self, path, rev):
        """
        SVN log for revision
        """

        cmd = ['svn', 'log', '-r%s' % rev]

        output = self._testenv.process_call(cmd, path=path)

        return ("\n".join(output.splitlines()[2:-1])).strip()

    def verify_log_rev(self, path, msg, rev):
        output = self.svn_log_rev(path, rev)
        if output.strip().find(msg) == -1:
            raise TestCaseError("Invalid revision log message='%s'" % output)

    def verify_ticket_entry(self, ticket_id, revision, msg, title_path):
        """
        This method is used to verify if an entry is properly created, in
        a Trac ticket.

        :param ticket_id: ticket id
        :type ticket_id: str or int
        :param revision: commit revision
        :type revision: str or int
        :param msg: commit message
        :type msg: str
        :raises: raises TestCaseError
        """

        # Go to the ticket page
        self._tester.go_to_ticket(ticket_id)

        # Verify ticket message
        xhtml = tc.get_browser().get_html()
        xhtml = re.sub(' xmlns="[^"]+"', '', xhtml, count=1)

        # Hack to support unknown entities
        # cf. http://en.wikipedia.org/wiki/
        # List_of_XML_and_HTML_character_entity_references web page
        class AllEntities:

            def __getitem__(self, key):
                # key associated to entity
                return key

        parser = ElementTree.XMLParser()
        parser.parser.UseForeignDTD(True)
        parser.entity = AllEntities()

        xml_tree = et.XML(xhtml, parser=parser)

        # xpath request
        xpath = './/div[@class="comment searchable"]/p/a' \
                '[@href="/changeset/%s"]/..' % revision
        result = xml_tree.findall(xpath)
        if len(result) != 1:
            raise TestCaseError("Missing for ticket='%s', commit message='%s'" %
                                (ticket_id, msg))

        item = result[0]
        ticket_msg = ("".join(item.itertext())).replace('\n', '')
        ticket_msg = ticket_msg.encode('ascii', errors='ignore')
        print >>sys.stderr, "actual ticket message:", ticket_msg
        print >>sys.stderr, "expected ticket message:", msg
        if msg != ticket_msg.strip():
            raise TestCaseError("Invalid commit message=' %s' for "
                                "ticket='%s'" % (ticket_msg, ticket_id))

        # Verify title
        if title_path:
            title = self.svn_log_rev(title_path, revision)
            xpath = './/a[@href="/changeset/%s"]' % revision
            result = item.findall(xpath)
            if len(result) != 1:
                raise TestCaseError("Invalid title message for commit=' %s', "
                                    "ticket='%s'" % (ticket_msg, ticket_id))
            item = result[0]
            if item.get('title') != title.replace('\n', ' '):
                raise TestCaseError("Invalid title message for commit=' %s', "
                                    "ticket='%s'" % (ticket_msg, ticket_id))

    def branch_create(self, branch, commit_msg, branch_from='trunk'):
        # Creates branch
        revision = self.svn_cp(branch_from, branch, commit_msg)

        # Verify revision log
        self.verify_log_rev(branch, commit_msg, revision)

        return revision

    def sandbox_create(self, ticket_id, branch_from='trunk',
                       close=True):
        sandbox_path = 'sandboxes/t%s' % ticket_id

        # Creates sandbox from trunk/component
        commit_msg = 'Creates t%s for #%s' % (ticket_id, ticket_id)
        revision = self.svn_cp(branch_from, sandbox_path, commit_msg)
        print >>sys.stderr, "revision", revision
        first_rev = revision

        # Verify revision log
        self.verify_log_rev(sandbox_path, commit_msg, revision)

        # Verify ticket entry
        commit_msg = "(In [%s]) %s" % (revision, commit_msg)
        self.verify_ticket_entry(ticket_id, revision, commit_msg, sandbox_path)

        # Add file data
        alea = randint(2, 200000)
        self.svn_add(sandbox_path, 'driver_%s.py' % alea, '# Dummy code')

        # Commit added file
        commit_msg = 'Refs #%s, Add driver_%s.py module' % (ticket_id, alea)
        revision = self.svn_commit(sandbox_path, commit_msg)
        last_rev = revision

        # Verify revision log
        self.verify_log_rev(sandbox_path, commit_msg, revision)

        # Verify ticket entry
        commit_msg = "(In [%s]) %s" % (revision, commit_msg)
        self.verify_ticket_entry(ticket_id, revision, commit_msg, sandbox_path)

        if close is True:
            # Add an other file data
            self.svn_add(sandbox_path, 'driver-i2c_%s.py' % alea, '# Header')

            # Commit and closes ticket
            commit_msg = 'Closes #%s, Add driver-i2c_%s.py module' % \
                        (ticket_id, alea)
            revision = self.svn_commit(sandbox_path, commit_msg)
            self.verify_log_rev(sandbox_path, commit_msg, revision)
            last_rev = revision

            # Verify ticket entry
            commit_msg = "(In [%s]) %s" % (revision, commit_msg)
            self.verify_ticket_entry(ticket_id, revision, commit_msg,
                                     sandbox_path)

        return (first_rev, last_rev)
