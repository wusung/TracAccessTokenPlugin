#!/usr/bin/env python
# -*- coding: utf-8 -*-

from trac.db import Table, Column, Index, DatabaseManager

version = 2
name = 'kkbox_trac_access_token'
tables = [
    Table(name, key='id')[
        Column('id', auto_increment=True),
        Column('access_token'),
        Column('description'),
        Column('username'),
        Column('change_time', type='int64'),
        Column('create_time', type='int64'),
        Column('last_use_time', type='int64')
    ]
]
