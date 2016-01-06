#!/bin/sh
# -*- coding: utf-8 -*-

# useful checks:
# * libsvn module linked in the virtualenv
# * access.conf file available

GREEN_COLOR="\\033[1;32m"

# Cleanup
echo "------------ Cleanup ------------"
rm -rf /tmp/trac
rm -rf /tmp/repositoryhooksystem-plugin
rm -rf /tmp/plugins

echo "------------ Export symbols ------------"
export TRAC_PATH=/tmp/trac
export PYTHONPATH=${TRAC_PATH}
export TRAC_HOOKS_PATH=${TRAC_PATH}/hooks/trac/trac_hook.py
export TRAC_PLUGINS_PATH=/tmp/plugins

echo "------------ Activate virtual env ------------"
. /usr/local/py-2.7.3/bin/activate # activate virtual env

# Python to use for Trac env launch
export TRAC_PYTHON=`which python`

# Trac sources installation
echo "------------ Clone trac sources ------------"
cd /tmp
git clone git@git.neotion.pro:trac.git
cd /tmp/trac
git checkout neotion-trunk
python setup.py bdist_egg

# Repository hook system plugin
echo "------------ Clone repositoryhooksystem sources ------------"
cd /tmp
git clone git@git.neotion.pro:repositoryhooksystem-plugin.git
cd repositoryhooksystem-plugin
git checkout neotion
python setup.py bdist_egg

# Install plugins
echo "------------ Install plugins ------------"
mkdir -p /tmp/plugins
cp ./dist/*.egg /tmp/plugins

# Clean
rm -rf dist build

# Test running
cd /tmp/repositoryhooksystem-plugin

TESTCASES="./tests/testcase_TK_XX.py ./tests/testcase_BR_XX.py ./tests/testcase_SB_XX.py"

for TESTCASE in ${TESTCASES}; do
    echo "------------ Run ${TESTCASE} ------------"
    python ${TESTCASE}
done
