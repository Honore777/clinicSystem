#!/usr/bin/env python3
import os
import sys
from pprint import pprint

# Ensure project root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app, db

app = create_app()
with app.app_context():
    rows = db.query_db('''SELECT id, name, city_id, slug, is_verified, IFNULL(is_active, 1) AS is_active, created_at
                         FROM clinic
                         ORDER BY created_at DESC
                         LIMIT 200''') or []

    if not rows:
        print('No clinics found in the database.')
    else:
        print(f'Found {len(rows)} clinics:')
        for r in rows:
            print(f"- id={r.get('id')} name={r.get('name')!r} city_id={r.get('city_id')} slug={r.get('slug')} verified={r.get('is_verified')} active={r.get('is_active')} created_at={r.get('created_at')}")

    counts = db.query_db("SELECT COUNT(*) as total, SUM(CASE WHEN is_verified = 1 THEN 1 ELSE 0 END) as verified, SUM(CASE WHEN COALESCE(is_active,1) = 1 THEN 1 ELSE 0 END) as active FROM clinic", one=True)
    print('\nSummary:')
    pprint(counts)

    # Show the most recent 5 clinics with their city name (if any)
    recent = db.query_db('''SELECT c.id, c.name, c.slug, ct.name as city_name, c.is_verified, IFNULL(c.is_active,1) as is_active, c.created_at
                              FROM clinic c LEFT JOIN city ct ON c.city_id = ct.id
                              ORDER BY c.created_at DESC LIMIT 10''') or []
    print('\nMost recent clinics with city names:')
    for r in recent:
        print(f"- id={r.get('id')} name={r.get('name')!r} city={r.get('city_name')!r} verified={r.get('is_verified')} active={r.get('is_active')} created_at={r.get('created_at')}")
