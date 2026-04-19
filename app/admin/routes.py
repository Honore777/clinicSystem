from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.auth.decorators import superadmin_required
from app.notifications import create_notification
from .forms import CreateStaffForm
from werkzeug.security import generate_password_hash

bp = Blueprint('admin', __name__)

"""
Admin blueprint: superadmin-only UI to manage clinics and staff.

Important:
- Routes are guarded by `superadmin_required` decorator which redirects to
    staff login if the user is not a superadmin.
- Staff creation uses a hashed password (Werkzeug) and stores the role.
"""


@bp.route('/')
@superadmin_required
def index():
    # Summary counts
    def get_count(sql, params=None):
        row = db.query_db(sql, params, one=True)
        if row is None:
            return 0
        if isinstance(row, dict):
            return list(row.values())[0]
        return row[0]

    total_clinics = get_count('SELECT COUNT(*) FROM clinic')
    total_pending = get_count("SELECT COUNT(*) FROM appointment_request WHERE status = 'pending'")
    total_unread = get_count("SELECT COUNT(*) FROM notification WHERE recipient_type = 'clinic' AND read_at IS NULL")

    # Check whether `is_active` column exists in clinic table
    col = db.query_db("SELECT COUNT(*) as cnt FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clinic' AND COLUMN_NAME = 'is_active'", one=True)
    has_is_active = bool(col and int(col.get('cnt', 0)) > 0)

    if has_is_active:
        clinics = db.query_db('''SELECT c.id, c.name, c.is_verified, c.is_active,
                                   ct.name as city_name,
                                   (SELECT COUNT(*) FROM appointment_request ar WHERE ar.clinic_id = c.id AND ar.status = 'pending') as pending_requests,
                                   (SELECT COUNT(*) FROM notification n WHERE n.recipient_type = 'clinic' AND n.recipient_id = c.id AND n.read_at IS NULL) as unread_notifications
                                FROM clinic c LEFT JOIN city ct ON c.city_id = ct.id
                                ORDER BY c.created_at DESC''') or []
    else:
        clinics = db.query_db('''SELECT c.id, c.name, c.is_verified as is_active,
                                   ct.name as city_name,
                                   (SELECT COUNT(*) FROM appointment_request ar WHERE ar.clinic_id = c.id AND ar.status = 'pending') as pending_requests,
                                   (SELECT COUNT(*) FROM notification n WHERE n.recipient_type = 'clinic' AND n.recipient_id = c.id AND n.read_at IS NULL) as unread_notifications
                                FROM clinic c LEFT JOIN city ct ON c.city_id = ct.id
                                ORDER BY c.created_at DESC''') or []

    return render_template('admin/dashboard.html', total_clinics=total_clinics, total_pending=total_pending, total_unread=total_unread, clinics=clinics, has_is_active=has_is_active)


@bp.route('/clinics')
@superadmin_required
def clinics():
    # join city name for clearer admin listing
    clinics = db.query_db('''SELECT c.id, c.name, c.is_verified, ct.name as city_name
                             FROM clinic c LEFT JOIN city ct ON c.city_id = ct.id
                             ORDER BY c.created_at DESC''') or []
    return render_template('admin/clinics.html', clinics=clinics)


@bp.route('/clinics/<int:clinic_id>/verify', methods=['POST'])
@superadmin_required
def verify_clinic(clinic_id):
    db.query_db('UPDATE clinic SET is_verified = 1 WHERE id = %s', (clinic_id,), commit=True)
    flash('Clinic verified')
    return redirect(url_for('admin.index'))


@bp.route('/clinics/<int:clinic_id>/delete', methods=['POST'])
@superadmin_required
def delete_clinic(clinic_id):
    try:
        db.query_db('DELETE FROM clinic WHERE id = %s', (clinic_id,), commit=True)
        flash('Clinic deleted')
    except Exception as e:
        flash('Failed to delete clinic: ' + str(e))
    return redirect(url_for('admin.index'))


@bp.route('/staff', methods=['GET', 'POST'])
@superadmin_required
def staff():
    form = CreateStaffForm()
    clinics = db.query_db('SELECT id, name FROM clinic ORDER BY name') or []
    form.clinic_id.choices = [(0, '— none —')] + [(c['id'], c['name']) for c in clinics]
    if form.validate_on_submit():
        pwd = generate_password_hash(form.password.data)
        clinic_id = form.clinic_id.data or None
        if clinic_id == 0:
            clinic_id = None
        db.query_db('INSERT INTO staff (clinic_id, name, email, phone, password_hash, role) VALUES (%s,%s,%s,%s,%s,%s)',
                    (clinic_id, form.name.data, form.email.data, form.phone.data, pwd, form.role.data), commit=True)
        flash('Staff created')
        return redirect(url_for('admin.staff'))
    staff_list = db.query_db('''SELECT s.id, s.name, s.email, s.role, c.name as clinic_name
                                FROM staff s LEFT JOIN clinic c ON s.clinic_id = c.id
                                ORDER BY s.created_at DESC''') or []
    return render_template('admin/staff.html', form=form, staff_list=staff_list)


@bp.route('/clinics/<int:clinic_id>/toggle', methods=['POST'])
@superadmin_required
def toggle_clinic(clinic_id):
    # Toggle `is_active` if exists, otherwise toggle `is_verified` as fallback
    col = db.query_db("SELECT COUNT(*) as cnt FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'clinic' AND COLUMN_NAME = 'is_active'", one=True)
    has_is_active = bool(col and int(col.get('cnt', 0)) > 0)
    try:
        if has_is_active:
            cur = db.query_db('SELECT is_active FROM clinic WHERE id = %s', (clinic_id,), one=True)
            new = 1 if not cur.get('is_active') else 0
            db.query_db('UPDATE clinic SET is_active = %s WHERE id = %s', (new, clinic_id), commit=True)
            flash('Clinic activation updated')
        else:
            cur = db.query_db('SELECT is_verified FROM clinic WHERE id = %s', (clinic_id,), one=True)
            new = 1 if not cur.get('is_verified') else 0
            db.query_db('UPDATE clinic SET is_verified = %s WHERE id = %s', (new, clinic_id), commit=True)
            flash('Clinic verification toggled (no is_active column present)')
    except Exception as e:
        flash('Failed to update clinic: ' + str(e))
    return redirect(url_for('admin.index'))


@bp.route('/clinics/<int:clinic_id>/alert', methods=['POST'])
@superadmin_required
def alert_clinic(clinic_id):
    message = request.form.get('message') or 'Superadmin: please review pending approvals.'
    try:
        create_notification(recipient_type='clinic', recipient_id=clinic_id, message=message)
        flash('Alert sent to clinic')
    except Exception as e:
        flash('Failed to send alert: ' + str(e))
    return redirect(url_for('admin.index'))


@bp.route('/clinics/<int:clinic_id>/requests')
@superadmin_required
def clinic_requests(clinic_id):
    clinic = db.query_db('SELECT id, name FROM clinic WHERE id = %s', (clinic_id,), one=True)
    requests = db.query_db('''SELECT ar.*, p.name as patient_name
                               FROM appointment_request ar
                               LEFT JOIN patient p ON ar.patient_id = p.id
                               WHERE ar.clinic_id = %s AND ar.status = 'pending'
                               ORDER BY ar.created_at DESC''', (clinic_id,)) or []
    return render_template('admin/clinic_requests.html', clinic=clinic, requests=requests)
