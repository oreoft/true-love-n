# -*- coding: utf-8 -*-
"""
Database Engine - 数据库引擎
"""

import sqlite3


def create_db_and_table():
    conn = sqlite3.connect('mc_devices.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mc_devices (
        sender TEXT PRIMARY KEY,
        device_id TEXT NOT NULL
    );
    ''')
    conn.commit()
    conn.close()

