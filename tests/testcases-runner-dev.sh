#!/bin/sh
# -*- coding: utf-8 -*-

# this version of the runner runs the plugin as it is in the current directory,
# instead of checking it out.
# It also uses the current python env


GREEN_COLOR="\\033[1;32m"

RHS_ROOT=$PWD

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

#echo "------------ Activate virtual env ------------"
#. /usr/local/py-2.7.3/bin/activate # activate virtual env

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
echo "------------ Build repositoryhooksystem sources ------------"
cd $RHS_ROOT
python setup.py bdist_egg

# Install plugins
echo "------------ Install plugins ------------"
mkdir -p /tmp/plugins
cp ./dist/*.egg /tmp/plugins

# Clean
rm -rf dist build

# Test running
#cd /tmp/repositoryhooksystem-plugin

TESTCASES="./tests/testcase_TK_XX.py ./tests/testcase_BR_XX.py ./tests/testcase_SB_XX.py"

for TESTCASE in ${TESTCASES}; do
    echo "------------ Run ${TESTCASE} ------------"
    python ${TESTCASE} -v
done
