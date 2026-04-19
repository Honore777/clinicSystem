from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash, g, session
import os
import json
from app import db
from werkzeug.security import generate_password_hash
from .forms import ClinicOnboardForm, ClinicStaffForm
from app.auth.decorators import staff_required, role_required
from app.notifications import create_notification

bp = Blueprint('clinic', __name__)

"""
Clinic blueprint handles onboarding and staff-facing pages.

Notes:
- `onboard` is publicly accessible to let clinics submit their details; upon
    creation the clinic is unverified and a superadmin must verify it.
- File uploads are saved under the configured `UPLOAD_FOLDER` and referenced
    from `clinic_photo` for flexible gallery display.
- `dashboard` and approval endpoints are protected by `staff_required` which
    checks for `session['staff_id']`.
"""


@bp.route('/onboard', methods=['GET', 'POST'])
def onboard():
    form = ClinicOnboardForm()
    # populate city choices
    cities = db.query_db('SELECT id, name FROM city ORDER BY name') or []
    form.city_id.choices = [(c['id'], c['name']) for c in cities]
    # Normalize website input when submitted without a scheme so the URL
    # validator accepts values like 'www.example.com'. Do this before
    # `validate_on_submit()` so the form sees the normalized value.
    if request.method == 'POST':
        raw_site = request.form.get('website')
        if raw_site and not raw_site.startswith(('http://', 'https://')):
            form.website.data = 'https://' + raw_site
    if form.validate_on_submit():
        name = form.name.data
        slug = form.slug.data or name.lower().replace(' ', '-')
        description = form.description.data
        city_id = form.city_id.data
        address = form.address.data
        contact_phone = form.contact_phone.data
        contact_email = form.contact_email.data
        website = form.website.data
        services = [s.strip() for s in (form.services.data or '').split(',') if s.strip()]
        latitude = form.latitude.data
        longitude = form.longitude.data
        insert_sql = ('INSERT INTO clinic (city_id, name, slug, description, contact_phone, contact_email, address, services) '
                      'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)')
        try:
            db.query_db(insert_sql, (city_id, name, slug, description, contact_phone, contact_email, address, json.dumps(services)), commit=True)
            # fetch created clinic id
            clinic = db.query_db('SELECT id FROM clinic WHERE slug = %s', (slug,), one=True)
            clinic_id = clinic['id']
            # optionally create a clinic admin account if admin fields provided
            # admin fields are optional; when provided we'll create a staff row
            admin_name = form.admin_name.data if hasattr(form, 'admin_name') else None
            admin_email = form.admin_email.data if hasattr(form, 'admin_email') else None
            admin_password = form.admin_password.data if hasattr(form, 'admin_password') else None
            if admin_email and admin_password:
                try:
                    pwd_hash = generate_password_hash(admin_password)
                    # schema uses 'manager' for clinic admin; map to that role
                    db.query_db('INSERT INTO staff (clinic_id, name, email, phone, password_hash, role) VALUES (%s,%s,%s,%s,%s,%s)',
                                (clinic_id, admin_name or 'Clinic Admin', admin_email, None, pwd_hash, 'manager'), commit=True)
                    # log the new clinic admin in directly so they can land
                    # in their dashboard without passing through staff login
                    session.clear()
                    session['staff_id'] = db.query_db('SELECT LAST_INSERT_ID() as id', one=True)['id']
                    session['staff_role'] = 'manager'
                    flash('Clinic administrator created')
                except Exception as e:
                    # don't fail the whole request if staff creation failed; log and flash
                    flash('Clinic created but failed to create admin: ' + str(e))

            # handle uploaded photos
            photos = []
            uploaded = request.files.getlist('photos')
            if uploaded:
                upload_root = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
                clinic_dir = os.path.join(upload_root, 'clinics', str(clinic_id))
                os.makedirs(clinic_dir, exist_ok=True)
                for f in uploaded:
                    if f and f.filename:
                        fn = f.filename.replace(' ', '_')
                        save_path = os.path.join(clinic_dir, fn)
                        f.save(save_path)
                        rel_path = os.path.join('uploads', 'clinics', str(clinic_id), fn).replace('\\', '/')
                        photos.append('/static/' + rel_path)
                # save photo metadata in clinic_photo table
                for idx, p in enumerate(photos):
                    is_primary = 1 if idx == 0 else 0
                    db.query_db(
                        'INSERT INTO clinic_photo (clinic_id, file_path, is_primary) VALUES (%s, %s, %s)',
                        (clinic_id, p, is_primary),
                        commit=True
                    )
            flash('Clinic created; pending verification')
            return redirect(url_for('clinic.dashboard'))
        except Exception as e:
            flash('Failed to create clinic: ' + str(e))
            return redirect(url_for('clinic.onboard'))
    # If POST and validation failed, show concise errors so the user knows
    # what to fix (templates don't show WTForms errors inline by default).
    if request.method == 'POST' and not form.validate():
        # aggregate errors
        errs = []
        for f, errors in form.errors.items():
            for e in errors:
                errs.append(f"{f}: {e}")
        if errs:
            flash('Please fix the form errors: ' + '; '.join(errs))

    # template placed under templates/clinic/clinic_onboard.html
    return render_template('clinic/clinic_onboard.html', form=form)



@bp.route('/dashboard')
@role_required('clinicadmin', 'staff', 'superadmin')
def dashboard():
    """Dashboard for clinic staff.

    - Managers (clinic admins) and staff see requests only for their clinic.
    - Superadmin can see all clinics' requests from their own admin UI, but we
      still allow access here for debugging.
    """

    staff = getattr(g, 'staff', None)
    base_sql = """SELECT ar.*, p.name as patient_name, p.phone as patient_phone
                   FROM appointment_request ar
                   JOIN patient p ON ar.patient_id = p.id"""
    rows = []
    clinic_id = staff['clinic_id'] if staff and staff.get('role') != 'superadmin' and staff.get('clinic_id') else None

    # Pending requests for this clinic
    if clinic_id:
        sql = base_sql + " WHERE ar.clinic_id = %s AND ar.status = 'pending' ORDER BY ar.created_at DESC"
        rows = db.query_db(sql, (clinic_id,)) or []
    else:
        sql = base_sql + " WHERE ar.status = 'pending' ORDER BY ar.created_at DESC"
        rows = db.query_db(sql) or []

    # Stats for summary cards (handle None and dict/tuple return)
    stats = {'pending': 0, 'approved': 0, 'total': 0}
    def get_count(sql, params=None):
        row = db.query_db(sql, params, one=True)
        if row is None:
            return 0
        if isinstance(row, dict):
            return list(row.values())[0]
        return row[0]

    if clinic_id:
        stats['pending'] = get_count("SELECT COUNT(*) FROM appointment_request WHERE clinic_id = %s AND status = 'pending'", (clinic_id,))
        stats['approved'] = get_count("SELECT COUNT(*) FROM appointment_request WHERE clinic_id = %s AND status = 'approved'", (clinic_id,))
        stats['total'] = get_count("SELECT COUNT(*) FROM appointment_request WHERE clinic_id = %s", (clinic_id,))
    else:
        stats['pending'] = get_count("SELECT COUNT(*) FROM appointment_request WHERE status = 'pending'")
        stats['approved'] = get_count("SELECT COUNT(*) FROM appointment_request WHERE status = 'approved'")
        stats['total'] = get_count("SELECT COUNT(*) FROM appointment_request")

    # load recent notifications relevant to this clinic (include patient name when linked)
    notifications = []
    try:
        if clinic_id:
            notifications = db.query_db(
                """SELECT n.*, p.name as patient_name
                   FROM notification n
                   LEFT JOIN appointment_request ar ON n.appointment_request_id = ar.id
                   LEFT JOIN patient p ON ar.patient_id = p.id
                   WHERE n.recipient_type = 'clinic' AND n.recipient_id = %s
                   ORDER BY n.created_at DESC
                   LIMIT 10""",
                (clinic_id,),
            ) or []
        else:
            # superadmin: show recent clinic notifications across all clinics
            notifications = db.query_db(
                """SELECT n.*, p.name as patient_name, c.name as clinic_name
                   FROM notification n
                   LEFT JOIN appointment_request ar ON n.appointment_request_id = ar.id
                   LEFT JOIN patient p ON ar.patient_id = p.id
                   LEFT JOIN clinic c ON n.recipient_id = c.id
                   WHERE n.recipient_type = 'clinic'
                   ORDER BY n.created_at DESC
                   LIMIT 10""",
            ) or []
    except Exception:
        notifications = []

    # mark clinic notifications as read when staff views the dashboard
    try:
        if clinic_id:
            db.query_db(
                "UPDATE notification SET read_at = CURRENT_TIMESTAMP WHERE recipient_type = 'clinic' AND recipient_id = %s AND read_at IS NULL",
                (clinic_id,),
                commit=True,
            )
    except Exception:
        pass

    return render_template('clinic/dashboard.html', requests=rows, stats=stats, notifications=notifications)


@bp.route('/staff', methods=['GET', 'POST'])
@role_required('clinicadmin')
def manage_staff():
    """Allow a clinic admin (manager) to create staff users for their clinic.

    - Uses ClinicStaffForm with a fixed clinic id from g.staff.
    - Created users get role='staff' and can log in via staff login.
    """

    form = ClinicStaffForm()
    staff_user = getattr(g, 'staff', None)
    clinic_id = staff_user.get('clinic_id') if staff_user else None
    if not clinic_id:
        flash('No clinic associated with this admin account.')
        return redirect(url_for('clinic.dashboard'))

    if form.validate_on_submit():
        pwd_hash = generate_password_hash(form.password.data)
        db.query_db(
            'INSERT INTO staff (clinic_id, name, email, phone, password_hash, role) VALUES (%s,%s,%s,%s,%s,%s)',
            (clinic_id, form.name.data, form.email.data, form.phone.data, pwd_hash, 'staff'),
            commit=True,
        )
        flash('User created for this clinic')
        return redirect(url_for('clinic.manage_staff'))

    staff_list = db.query_db(
        'SELECT id, name, email, phone, role FROM staff WHERE clinic_id = %s ORDER BY created_at DESC',
        (clinic_id,),
    ) or []

    return render_template('clinic/staff.html', form=form, staff_list=staff_list)


@bp.route('/request/<int:req_id>/approve', methods=['POST'])
@role_required('clinicadmin', 'staff', 'superadmin')
def approve(req_id):
    # Approval handler: checks for conflicts and, if none, creates an
    # appointment and marks the request as approved. Responds with
    # a flash+redirect for normal requests, or a small HTML fragment
    # when called via HTMX so the UI can update in-place.
    req = db.query_db('SELECT * FROM appointment_request WHERE id = %s', (req_id,), one=True)
    if not req:
        msg = 'Appointment request not found.'
        if request.headers.get('HX-Request'):
            return render_template('clinic/_action_result.html', message=msg, status='error'), 404
        flash(msg)
        return redirect(url_for('clinic.dashboard'))

    # Basic conflict check: ensure no existing confirmed appointment overlaps
    start = req['requested_start']
    end = req['requested_end']
    doctor_id = req['doctor_id']
    clinic_id = req['clinic_id']

    if doctor_id:
        conflict_sql = ('SELECT COUNT(1) as cnt FROM appointment '
                        'WHERE clinic_id = %s AND doctor_id = %s '
                        'AND NOT (confirmed_end <= %s OR confirmed_start >= %s)')
        cnt_row = db.query_db(conflict_sql, (clinic_id, doctor_id, start, end), one=True)
        cnt = cnt_row.get('cnt') if isinstance(cnt_row, dict) else (cnt_row[0] if cnt_row else 0)
    else:
        conflict_sql = ('SELECT COUNT(1) as cnt FROM appointment '
                        'WHERE clinic_id = %s '
                        'AND NOT (confirmed_end <= %s OR confirmed_start >= %s)')
        cnt_row = db.query_db(conflict_sql, (clinic_id, start, end), one=True)
        cnt = cnt_row.get('cnt') if isinstance(cnt_row, dict) else (cnt_row[0] if cnt_row else 0)

    if cnt and int(cnt) > 0:
        msg = 'This time conflicts with an existing appointment; please choose a different slot.'
        if request.headers.get('HX-Request'):
            return render_template('clinic/_action_result.html', message=msg, status='conflict'), 409
        flash(msg)
        return redirect(url_for('clinic.dashboard'))

    # Ensure staff is authorized for this clinic (unless superadmin)
    staff = getattr(g, 'staff', None)
    if staff and staff.get('role') != 'superadmin' and staff.get('clinic_id') != clinic_id:
        msg = 'You are not authorized to approve requests for this clinic.'
        if request.headers.get('HX-Request'):
            return render_template('clinic/_action_result.html', message=msg, status='forbidden'), 403
        flash(msg)
        return redirect(url_for('clinic.dashboard'))

    insert_sql = 'INSERT INTO appointment (appointment_request_id, clinic_id, doctor_id, confirmed_start, confirmed_end) VALUES (%s,%s,%s,%s,%s)'
    try:
        db.query_db(insert_sql, (req_id, clinic_id, doctor_id, start, end), commit=True)
        db.query_db('UPDATE appointment_request SET status = %s WHERE id = %s', ('approved', req_id), commit=True)
        # send simple notifications so patient/clinic can see status
        try:
            create_notification(
                recipient_type='patient',
                recipient_id=req['patient_id'],
                appointment_id=None,
                appointment_request_id=req_id,
                message='Your appointment has been approved.',
            )
            create_notification(
                recipient_type='clinic',
                recipient_id=clinic_id,
                appointment_id=None,
                appointment_request_id=req_id,
                message='An appointment request was approved.',
            )
        except Exception:
            # do not roll back booking if notifications fail
            pass
    except Exception as e:
        msg = 'Failed to approve appointment: ' + str(e)
        if request.headers.get('HX-Request'):
            return render_template('clinic/_action_result.html', message=msg, status='error'), 500
        flash(msg)
        return redirect(url_for('clinic.dashboard'))

    success_msg = 'Appointment request approved.'
    if request.headers.get('HX-Request'):
        return render_template('clinic/_action_result.html', message=success_msg, status='approved'), 200
    flash(success_msg)
    return redirect(url_for('clinic.dashboard'))


@bp.route('/request/<int:req_id>/decline', methods=['POST'])
@role_required('clinicadmin', 'staff', 'superadmin')
def decline(req_id):
    """Decline an appointment request.

    - Updates status to 'declined'.
    - Notifies the patient and clinic in-app.
    """

    req = db.query_db('SELECT * FROM appointment_request WHERE id = %s', (req_id,), one=True)
    if not req:
        msg = 'Appointment request not found.'
        if request.headers.get('HX-Request'):
            return render_template('clinic/_action_result.html', message=msg, status='error'), 404
        flash(msg)
        return redirect(url_for('clinic.dashboard'))

    staff = getattr(g, 'staff', None)
    clinic_id = req['clinic_id']
    if staff and staff.get('role') != 'superadmin' and staff.get('clinic_id') != clinic_id:
        msg = 'You are not authorized to decline requests for this clinic.'
        if request.headers.get('HX-Request'):
            return render_template('clinic/_action_result.html', message=msg, status='forbidden'), 403
        flash(msg)
        return redirect(url_for('clinic.dashboard'))

    db.query_db('UPDATE appointment_request SET status = %s WHERE id = %s', ('declined', req_id), commit=True)

    try:
        create_notification(
            recipient_type='patient',
            recipient_id=req['patient_id'],
            appointment_request_id=req_id,
            message='Your appointment request was declined.',
        )
        create_notification(
            recipient_type='clinic',
            recipient_id=clinic_id,
            appointment_request_id=req_id,
            message='An appointment request was declined.',
        )
    except Exception:
        pass

    success_msg = 'Appointment request declined.'
    if request.headers.get('HX-Request'):
        return render_template('clinic/_action_result.html', message=success_msg, status='declined'), 200
    flash(success_msg)
    return redirect(url_for('clinic.dashboard'))
