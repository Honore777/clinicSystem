#!/usr/bin/env python3
import os
import sys
from pprint import pprint

# Ensure project root is importable when running from database/ folder
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app, db

app = create_app()
with app.app_context():
    # Check whether column exists
    row = db.query_db(
        "SELECT COUNT(*) as cnt FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clinic' AND COLUMN_NAME = 'is_active'",
        one=True,
    )
    cnt = 0
    if row:
        if isinstance(row, dict):
            cnt = int(row.get('cnt') or 0)
        else:
            cnt = int(list(row)[0])

    if cnt > 0:
        print("Column `is_active` already exists on `clinic`.")
    else:
        print("Adding column `is_active` to `clinic` table...")
        try:
            db.query_db("ALTER TABLE clinic ADD COLUMN is_active TINYINT(1) DEFAULT 1", commit=True)
            print("Added column `is_active`.")
        except Exception as e:
            print("Failed to add column `is_active`:", e)
            sys.exit(1)

    # Print a brief clinic summary after ensuring the column exists
    rows = db.query_db(
        '''SELECT id, name, city_id, slug, is_verified, IFNULL(is_active, 1) AS is_active, created_at
           FROM clinic
           ORDER BY created_at DESC
           LIMIT 50'''
    ) or []

    if not rows:
        print('No clinics found in the database.')
    else:
        print(f'Found {len(rows)} clinics:')
        for r in rows:
            print(f"- id={r.get('id')} name={r.get('name')!r} city_id={r.get('city_id')} slug={r.get('slug')} verified={r.get('is_verified')} active={r.get('is_active')} created_at={r.get('created_at')}")

    counts = db.query_db(
        "SELECT COUNT(*) as total, SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) as verified, SUM(CASE WHEN COALESCE(is_active,1) = 1 THEN 1 ELSE 0 END) as active FROM clinic",
        one=True,
    )
    print('\nSummary:')
    pprint(counts)
