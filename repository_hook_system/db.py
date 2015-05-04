#-----------------------------------------------------------------------------
# Copyright (C) 2015 Neotion
# All rights reserved.
#-----------------------------------------------------------------------------

__all__ = ['Db']

class Db(object):
    """
    """

    VERSION = 1

    def __init__(self, env):
        self.env = env
        self.log = env.log

    @staticmethod
    def _get_db_version(env):
        try:
            rows = env.db_query(
                "SELECT value FROM system WHERE name='rhsversion'")
            return int(rows[0][0])
        except:
            return 0

    def verify(self):
        self.log.debug('Verify Database')
        ver = self._get_db_version(self.env)
        if ver != Db.VERSION:
            self.log.error('Database version is %s, expected %s' %
                           (ver, Db.VERSION))
            return False
        return True

    def upgrade(self):
        self.log.debug('Upgrade Database')
        ver = self._get_db_version(self.env)
        # Perform incremental upgrades.
        for i in range(ver + 1, self.VERSION + 1):
            script_name = 'db%i' % i
            m = __import__('repository_hook_system.dbs.%s' % script_name,
                           globals(), locals(), ['do_upgrade'])
            m.do_upgrade(self.env)

    def add_association(self, assoc):
        self.env.db_transaction("INSERT INTO rhs_br_ms_assoc "
                                "(branch, ms_prefix) VALUES ('%s', '%s')" %
                                (assoc['name'], assoc['prefix']))

    def remove_association(self, assoc):
        self.env.db_transaction("DELETE FROM rhs_br_ms_assoc "
                                "WHERE branch='%s'" % assoc['name'])

    def list_associations(self):
        rows = self.env.db_query("SELECT branch,ms_prefix FROM rhs_br_ms_assoc")
        return [{'name': n, 'prefix': p} for n, p in rows]

    def get_milestone_prefix(self, branch_name):
        rows = self.env.db_query("SELECT ms_prefix FROM rhs_br_ms_assoc "
                                 "WHERE branch=%s" % branch_name)
        row = rows[0] if rows else None
        if not row:
            return None
        else:
            return row[0]
