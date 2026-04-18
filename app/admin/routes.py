from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.auth.decorators import superadmin_required
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
    return render_template('admin_index.html')


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
    return redirect(url_for('admin.clinics'))


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
