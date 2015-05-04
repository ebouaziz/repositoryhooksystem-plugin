# -*- coding: utf-8 -*-

from trac.db import Table, Column, Index, DatabaseManager

VERSION = 1
SCHEMA = [
    Table('rhs_br_ms_assoc', key='branch')[
        Column('branch'),
        Column('ms_prefix')]]


def do_upgrade(env):
    db_connector, _ = DatabaseManager(env)._get_connector()

    with env.db_transaction as db:
        for table in SCHEMA:
            for stmt in db_connector.to_sql(table):
                db(stmt)
        db("INSERT INTO system (name, value) VALUES ('%s', %s)",
           ('rhsversion', VERSION))
