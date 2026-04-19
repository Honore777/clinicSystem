#!/usr/bin/env python3
"""Minimal CLI: run one SQL, print DataFrame info.

Usage examples:
  python scripts/df_cli.py --sql "SELECT id, name FROM clinic LIMIT 5"
  python scripts/df_cli.py --report clinics

This script is intentionally simple: it creates the app context,
opens the DB connection via `db.get_db()`, runs a single query with
`pandas.read_sql`, and prints `shape`, `columns`, and `size`.
"""
import os
import sys
import argparse
import pandas as pd

# make project importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app, db


# 1. Initialize the App
app = create_app()


with app.app_context():
    conn= db.get_db()
    # 2. Put your SQL here
    sql = "SELECT * FROM clinic LIMIT 10"
    sql2="SELECT c.name AS city, c.is_verified, c.created_at FROM clinic c LEFT JOIN city ci ON ci.id=c.city_id" 
    ""
    
    # 3. Read and print
    df = pd.read_sql(sql2, conn)
    
    print(df.shape)
    print(df.columns)
    print(df.describe)