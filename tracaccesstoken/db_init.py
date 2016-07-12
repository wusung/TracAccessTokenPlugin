#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from trac.db import Table, Column, Index, DatabaseManager
from trac.env import Environment

schema = [
    Table('kkbox_trac_access_token', key='id')[
        Column('id', auto_increment=True),
        Column('access_token'),
        Column('description'),
        Column('username'),
        Column('change_time', type='int64'),
        Column('create_time', type='int64')
    ]
]

parser = argparse.ArgumentParser()
parser.add_argument("path", help="The root path of Trac environment")
parser.add_argument("-c", "--create-tables", action="store_true",
                    help = "Create tables",)
parser.add_argument("-d", "--drop-tables", action="store_true",
                    help="Drop tables",)
args = parser.parse_args()

env = Environment(args.path)
databaseManager = DatabaseManager(env)


def create_tables():
    databaseManager.create_tables(schema)


def drop_tables():
    databaseManager.drop_tables(schema)


if __name__ == '__main__':
    if args.create_tables:
        create_tables()
    elif args.drop_tables:
        drop_tables()
    else:
        pass
