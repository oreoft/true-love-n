import sqlite3


def create_db_and_table():
    conn = sqlite3.connect('mc_devices.db')  # 这将创建一个名为'user_devices.db'的数据库文件
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mc_devices (
        sender TEXT PRIMARY KEY,
        device_id TEXT NOT NULL
    );
    ''')
    conn.commit()
    conn.close()
