import pymysql
from flask import current_app, g


def get_db():
    if 'db' not in g:
        cfg = current_app.config
        conn = pymysql.connect(
            host=cfg['MYSQL_HOST'],
            user=cfg['MYSQL_USER'],
            password=cfg['MYSQL_PASSWORD'],
            db=cfg['MYSQL_DB'],
            port=cfg['MYSQL_PORT'],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            charset='utf8mb4'
        )
        g.db = conn
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def query_db(query, args=(), one=False, commit=False):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(query, args)
        if commit:
            db.commit()
        if cur.description:
            rows = cur.fetchall()
            return (rows[0] if rows and one else rows)
        return None
