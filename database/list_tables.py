"""List tables in the app-configured MySQL database for diagnosis.

Usage:
  python database/list_tables.py
"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from app import create_app
except Exception as e:
    print('Failed to import app:', e)
    raise

import pymysql


def main():
    app = create_app()
    with app.app_context():
        cfg = app.config
        host = cfg.get('MYSQL_HOST')
        port = cfg.get('MYSQL_PORT')
        user = cfg.get('MYSQL_USER')
        password = cfg.get('MYSQL_PASSWORD')
        db = cfg.get('MYSQL_DB')

        print(f'Connecting to {user}@{host}:{port} db={db}')
        conn = pymysql.connect(host=host, port=int(port), user=user, password=password, db=db, charset='utf8mb4')
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT DATABASE()')
                print('Active database:', cur.fetchone())
                cur.execute('SHOW TABLES')
                rows = cur.fetchall()
                print('\nTables:')
                for r in rows:
                    print(' -', r[0])
        finally:
            conn.close()


if __name__ == '__main__':
    main()
