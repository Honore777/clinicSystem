from flask import Blueprint, render_template
from app.auth.decorators import superadmin_required
from app import db
import pandas as pd

bp = Blueprint('reports', __name__)


@bp.route('/admin/reports')
@superadmin_required
def index():
    # Use db.query_db for scalar counts to avoid pandas.read_sql issues with DBAPI connections
    def get_count(sql):
        row = db.query_db(sql, one=True)
        if not row:
            return 0
        if isinstance(row, dict):
            val = next(iter(row.values()))
        else:
            val = row[0]
        try:
            return int(val)
        except Exception:
            try:
                return int(float(val))
            except Exception:
                return 0

    totals = {
        'total_appointments': get_count('SELECT COUNT(*) as total_appointments FROM appointment'),
        'total_patients': get_count('SELECT COUNT(*) as total_patients FROM patient'),
        'active_clinics': get_count("SELECT COUNT(*) as active_clinics FROM clinic WHERE COALESCE(is_active,1)=1"),
        'pending_requests': get_count("SELECT COUNT(*) as pending_requests FROM appointment_request WHERE status='pending'"),
    }

    # Top clinics: use db.query_db and render a small HTML snippet via pandas
    top_rows = db.query_db("SELECT c.name as clinic_name, COUNT(ar.id) as total_requests FROM clinic c LEFT JOIN appointment_request ar ON ar.clinic_id = c.id GROUP BY c.id ORDER BY total_requests DESC LIMIT 5") or []
    try:
        top_clinics_html = pd.DataFrame(top_rows).to_html(index=False, classes='min-w-full text-sm', border=0) if top_rows else ''
    except Exception:
        top_clinics_html = ''

    return render_template('reports/index.html', totals=totals, top_clinics_html=top_clinics_html)


@bp.route('/admin/reports/run')
@superadmin_required
def run_report():
    # Keep a simple run endpoint that expects a `name` query and renders a full table
    from flask import request
    name = request.args.get('name')
    conn = db.get_db()
    df = None
    title = 'Report'
    error = None
    try:
        if name == 'appointments_per_clinic':
            rows = db.query_db("SELECT c.name as clinic_name, COUNT(a.id) as total_appointments FROM clinic c LEFT JOIN appointment a ON a.clinic_id = c.id GROUP BY c.id ORDER BY total_appointments DESC") or []
            df = pd.DataFrame(rows)
            title = 'Total appointments per clinic'
        elif name == 'top_clinics_by_requests':
            rows = db.query_db("SELECT c.name as clinic_name, COUNT(ar.id) as total_requests FROM clinic c LEFT JOIN appointment_request ar ON ar.clinic_id = c.id GROUP BY c.id ORDER BY total_requests DESC") or []
            df = pd.DataFrame(rows)
            title = 'Most requested clinics (by requests)'
        elif name == 'number_of_patients':
            row = db.query_db("SELECT COUNT(*) as total_patients FROM patient", one=True)
            df = pd.DataFrame([row]) if row else pd.DataFrame()
            title = 'Total number of patients'
        else:
            error = 'Unknown report'
    except Exception as e:
        error = str(e)

    table = None
    if df is not None and not df.empty:
        table = df.to_html(index=False, classes='min-w-full text-sm', border=0)

    return render_template('reports/show.html', title=title, table=table, error=error)
