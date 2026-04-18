"""Test DB connection using app config and print helpful diagnostics.

Usage:
  python database/test_connection.py

This will display the DB host/user/db (masking the password) and attempt a PyMySQL connection,
printing any error details to help debug authentication/plugin issues.
"""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from app import create_app
except Exception as e:
    print('Failed to import app:', e)
    raise

import pymysql


def mask(s):
    if not s:
        return '(empty)'
    return s[0] + '••••' + s[-1]


def main():
    app = create_app()
    with app.app_context():
        cfg = app.config
        host = cfg.get('MYSQL_HOST')
        port = cfg.get('MYSQL_PORT')
        user = cfg.get('MYSQL_USER')
        password = cfg.get('MYSQL_PASSWORD')
        db = cfg.get('MYSQL_DB')

        print('Using DB config:')
        print('  host:', host)
        print('  port:', port)
        print('  user:', user)
        print('  password set:', 'yes' if password else 'no')
        print('  db:', db)

        try:
            conn = pymysql.connect(host=host, port=int(port), user=user, password=password, db=db, charset='utf8mb4')
            print('Connection OK')
            conn.close()
        except Exception as e:
            print('Connection FAILED:')
            traceback.print_exc()


if __name__ == '__main__':
    main()
