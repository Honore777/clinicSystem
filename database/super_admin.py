#!/usr/bin/env python3
import os
import sys
import getpass

# Ensure project root is on sys.path so `app` package can be imported when running this script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app, db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    name = input("Full name: ").strip()
    email = input("Email: ").strip()
    phone = input("Phone (optional): ").strip() or None
    pwd = getpass.getpass("Password: ")
    pwd2 = getpass.getpass("Confirm password: ")
    if pwd != pwd2:
        print("Passwords do not match"); sys.exit(1)
    pwd_hash = generate_password_hash(pwd)
    db.query_db(
        "INSERT INTO staff (clinic_id, name, email, phone, password_hash, role) VALUES (%s,%s,%s,%s,%s,%s)",
        (None, name, email, phone, pwd_hash, 'superadmin'),
        commit=True
    )
    print("Created superadmin:", email)