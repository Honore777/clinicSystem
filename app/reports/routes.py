from flask import Blueprint, render_template, request
import pandas as pd

from app import db
from app.auth.decorators import superadmin_required

bp = Blueprint('reports', __name__)


@bp.route('/report')
@superadmin_required
def report():
    """Run a read-only SQL query via pandas and show the resulting DataFrame.

    Usage (superadmin only): /report?sql=<your_sql>
    If no `sql` param is provided, a default report is shown.
    """
    sql = request.args.get('sql')
    if not sql:
        sql = "SELECT status, COUNT(*) as count FROM appointment_request GROUP BY status"

    # Use the app's DB connection (pymysql connection) with pandas
    conn = db.get_db()
    try:
        df = pd.read_sql(sql, conn)
    except Exception as e:
        return (f"Query failed: {e}"), 400

    table_html = df.to_html(classes='min-w-full text-sm', index=False, border=0)
    return render_template('reports/report.html', table_html=table_html, sql=sql)
