"""Seed script to create initial cities and a superadmin user.

Run:
  python database/seed.py

This uses the app's DB helper and requires the app config to point to a valid DB.
"""
import os
import sys

# Ensure project root is on sys.path so `from app import ...` works
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from app import create_app
    from werkzeug.security import generate_password_hash
    from app import db
except Exception as e:
    print('Error importing application. Are you running this script from the project root or database folder?')
    print('Exception:', e)
    raise


def seed():
    app = create_app()
    with app.app_context():
        # create cities if not exists
        cities = ['Kigali', 'Musanze', 'Bugesera', 'Rubavu']
        for c in cities:
            exists = db.query_db('SELECT id FROM city WHERE name = %s', (c,), one=True)
            if not exists:
                db.query_db('INSERT INTO city (name, slug) VALUES (%s,%s)', (c, c.lower()), commit=True)
        # create superadmin staff
        admin_email = 'admin@clinic.local'
        existing = db.query_db('SELECT id FROM staff WHERE email = %s', (admin_email,), one=True)
        if not existing:
            pwd = generate_password_hash('adminpass')
            db.query_db('INSERT INTO staff (clinic_id, name, email, phone, password_hash, role) VALUES (%s,%s,%s,%s,%s,%s)',
                        (None, 'Super Admin', admin_email, '0000000000', pwd, 'superadmin'), commit=True)
        print('Seeding complete')


if __name__ == '__main__':
    try:
        seed()
    except Exception as e:
        print('Seeding failed:', e)
        raise
