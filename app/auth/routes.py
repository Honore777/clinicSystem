from flask import Blueprint, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from .forms import RegisterForm, LoginForm, StaffLoginForm

bp = Blueprint('auth', __name__, url_prefix='/auth')

"""
Authentication routes for patients and staff.

Design notes (inline):
- Register: creates a `patient` row with a password hash (Werkzeug PBKDF2).
- Login: verifies the password hash and stores `patient_id` in `session`.
- Staff login: verifies staff credentials and stores `staff_id` and `staff_role`.

We prefer session-based auth for this small MVP. Session keys are simple
integers referencing rows in `patient` / `staff` tables. Decorators in
`app.auth.decorators` enforce access control on protected routes.
"""


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        password_hash = generate_password_hash(password)
        sql = 'INSERT INTO patient (name, phone, email, password_hash) VALUES (%s,%s,%s,%s)'
        try:
            db.query_db(sql, (name, phone, email, password_hash), commit=True)
        except Exception as e:
            flash('Registration failed: ' + str(e))
            return redirect(url_for('auth.register'))
        flash('Registered. Please log in')
        return redirect(url_for('auth.login'))
    return render_template('auth_register.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    from .forms import StaffLoginForm
    staff_form = StaffLoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.query_db('SELECT * FROM patient WHERE email = %s', (email,), one=True)
        if not user or not user.get('password_hash'):
            flash('Invalid credentials')
            return redirect(url_for('auth.login'))
        if not check_password_hash(user['password_hash'], password):
            flash('Invalid credentials')
            return redirect(url_for('auth.login'))
        session.clear()
        session['patient_id'] = user['id']
        return redirect(url_for('patient.index'))
    return render_template('auth_login.html', form=form, staff_form=staff_form)


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('patient.index'))


@bp.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    form = StaffLoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        staff = db.query_db('SELECT * FROM staff WHERE email = %s', (email,), one=True)
        if not staff or not check_password_hash(staff['password_hash'], password):
            flash('Invalid credentials')
            return redirect(url_for('auth.staff_login'))
        session.clear()
        session['staff_id'] = staff['id']
        session['staff_role'] = staff.get('role')
        return redirect(url_for('clinic.dashboard'))
    return render_template('auth_staff_login.html', form=form)
