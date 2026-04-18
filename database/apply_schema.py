"""Apply the SQL schema file to the configured MySQL server.

Usage:
  python database/apply_schema.py

Reads DB connection info from app config (instance/config.py or env/.env).
This script will:
 - create the database if it doesn't exist
 - execute each top-level SQL statement in database/schema.sql

Note: This is a simple runner intended for development. Be careful running
against production databases.
"""
import os
import pymysql
from app import create_app


def read_sql_file(path):
    with open(path, 'r', encoding='utf8') as f:
        return f.read()


def split_statements(sql):
    # naive split by semicolon; sufficient for straightforward DDL files
    parts = []
    cur = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('--') or stripped.startswith('/*'):
            continue
        cur.append(line)
        if stripped.endswith(';'):
            parts.append('\n'.join(cur))
            cur = []
    if cur:
        parts.append('\n'.join(cur))
    return [p.strip().rstrip(';') for p in parts if p.strip()]


def apply():
    app = create_app()
    with app.app_context():
        cfg = app.config
        host = cfg.get('MYSQL_HOST', 'localhost')
        port = int(cfg.get('MYSQL_PORT', 3306))
        user = cfg.get('MYSQL_USER', 'root')
        password = cfg.get('MYSQL_PASSWORD', '')
        dbname = cfg.get('MYSQL_DB', 'clinic_system')

        # connect to server (no specific db) to create database if needed
        conn = pymysql.connect(host=host, user=user, password=password, port=port, charset='utf8mb4')
        try:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
        finally:
            conn.close()

        # connect to the target db and execute statements
        conn = pymysql.connect(host=host, user=user, password=password, db=dbname, port=port, charset='utf8mb4')
        sql_text = read_sql_file(os.path.join(os.path.dirname(__file__), 'schema.sql'))
        statements = split_statements(sql_text)
        try:
            with conn.cursor() as cur:
                for stmt in statements:
                    try:
                        cur.execute(stmt)
                    except Exception as e:
                        print('Error executing statement:', e)
                        print('Statement was:\n', stmt[:2000])
                        raise
            conn.commit()
        finally:
            conn.close()


if __name__ == '__main__':
    print('Applying schema...')
    apply()
    print('Schema applied.')
