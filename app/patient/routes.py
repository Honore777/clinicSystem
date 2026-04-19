from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
from app import db
from app.notifications import create_notification
from app.auth.decorators import login_required_patient

bp = Blueprint('patient', __name__)


@bp.route('/')
def index():
    # show clinics with city and a primary photo when available
    # support a simple `q` search param to filter by clinic name/description/city
    q = request.args.get('q')
    city = request.args.get('city')
    # Base query: join city and pick a primary photo when available.
    # We keep it ordered by city then creation date, then group in Python
    # so the template can render clinics by city like a directory.
    params = []
    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append('(c.name LIKE %s OR c.description LIKE %s OR ct.name LIKE %s)')
        params.extend([like, like, like])
    if city:
        conditions.append('ct.name = %s')
        params.append(city)

    where_clause = ''
    if conditions:
        where_clause = 'WHERE ' + ' AND '.join(conditions)

    sql = f'''
        SELECT c.id, c.name, c.slug, c.description, c.address, ct.name as city_name,
               cp.file_path as primary_photo,
               (SELECT AVG(rating) FROM clinic_review WHERE clinic_id = c.id) as avg_rating,
               c.services
        FROM clinic c
        LEFT JOIN city ct ON c.city_id = ct.id
        LEFT JOIN clinic_photo cp ON cp.clinic_id = c.id AND cp.is_primary = 1
        {where_clause}
        ORDER BY ct.name ASC, c.created_at DESC
        LIMIT 200'''
    # pass an empty tuple when no params to avoid passing `None` into
    # cursor.execute(query, params) which can behave differently across
    # DB drivers/environments
    rows = db.query_db(sql, tuple(params) if params else (),) or []
    # Parse services field for each clinic (JSON or comma-separated string, but avoid splitting every letter)
    import json
    for row in rows:
        services = row.get('services')
        parsed = []
        if services:
            try:
                # Try JSON decode if it looks like a JSON array
                parsed = json.loads(services) if isinstance(services, str) and services.strip().startswith('[') else services
                if isinstance(parsed, str):
                    parsed = [s.strip() for s in parsed.split(',') if s.strip()]
            except Exception:
                parsed = [s.strip() for s in services.split(',') if s.strip()]
        row['services'] = parsed if isinstance(parsed, list) else []

    # Featured clinics: top 6 by rating, fallback to most recent
    featured_sql = '''
         SELECT c.id, c.name, c.slug, c.description, c.address, ct.name as city_name,
             cp.file_path as primary_photo,
             (SELECT AVG(rating) FROM clinic_review WHERE clinic_id = c.id) as avg_rating,
             c.services
         FROM clinic c
         LEFT JOIN city ct ON c.city_id = ct.id
         LEFT JOIN clinic_photo cp ON cp.clinic_id = c.id AND cp.is_primary = 1
         WHERE c.is_verified = 1
         ORDER BY (avg_rating IS NULL), avg_rating DESC, c.created_at DESC
         LIMIT 6'''
    featured_clinics = db.query_db(featured_sql) or []

    # Parse `services` for featured clinics the same way we parse the main
    # clinics list above so templates receive a list instead of a raw string.
    import json
    for c in featured_clinics:
        services = c.get('services')
        parsed = []
        if services:
            try:
                parsed = json.loads(services) if isinstance(services, str) and services.strip().startswith('[') else services
                if isinstance(parsed, str):
                    parsed = [s.strip() for s in parsed.split(',') if s.strip()]
            except Exception:
                parsed = [s.strip() for s in services.split(',') if s.strip()]
        c['services'] = parsed if isinstance(parsed, list) else []

    # List of all cities with clinics (plus key featured cities like Kigali/Musanze/Rubavu)
    cities_sql = '''
        SELECT DISTINCT ct.name
        FROM city ct
        JOIN clinic c ON c.city_id = ct.id
        ORDER BY ct.name ASC
    '''
    city_rows = db.query_db(cities_sql) or []
    city_names = [row['name'] for row in city_rows if row.get('name')]

    # Ensure core featured locations always appear as cards even if no clinic yet
    featured_base = ['Kigali', 'Musanze', 'Rubavu']
    city_set = set(city_names)
    for base in featured_base:
        city_set.add(base)
    city_list = sorted(city_set)

    # Group clinics by city name for the UI
    clinics_by_city = {}
    for row in rows:
        city = row.get('city_name') or 'Other'
        clinics_by_city.setdefault(city, []).append(row)

    return render_template(
        'index.html',
        clinics_by_city=clinics_by_city,
        featured_clinics=featured_clinics,
        city_list=city_list,
        q=q,
        city=city,
    )


@bp.route('/clinic/<int:clinic_id>')
def clinic_profile(clinic_id):
    clinic = db.query_db('SELECT c.*, ct.name as city_name FROM clinic c LEFT JOIN city ct ON c.city_id = ct.id WHERE c.id = %s', (clinic_id,), one=True)
    doctors = db.query_db('SELECT id, name, specialty, working_hours FROM doctor WHERE clinic_id = %s', (clinic_id,)) or []
    photos = db.query_db('SELECT file_path, caption, is_primary FROM clinic_photo WHERE clinic_id = %s ORDER BY is_primary DESC, id ASC', (clinic_id,)) or []
    # Fetch latest reviews for this clinic (rating + comment + patient name)
    reviews = db.query_db('''SELECT cr.id, cr.rating, cr.comment, cr.created_at,
                                    p.name as patient_name
                             FROM clinic_review cr
                             LEFT JOIN patient p ON cr.patient_id = p.id
                             WHERE cr.clinic_id = %s
                             ORDER BY cr.created_at DESC
                             LIMIT 20''', (clinic_id,)) or []
    # parse JSON fields for display (services may be stored as JSON string)
    import json
    services = []
    if clinic and clinic.get('services'):
        try:
            services = json.loads(clinic['services']) if isinstance(clinic['services'], str) else clinic['services']
        except Exception:
            services = [s.strip() for s in (clinic.get('services') or '').split(',') if s.strip()]
    # prepare a simple google maps embed query using address (fallback if lat/lng not stored)
    map_query = ''
    if clinic:
        addr = clinic.get('address') or clinic.get('contact_email') or clinic.get('name')
        from urllib.parse import quote_plus
        map_query = quote_plus(addr)
    return render_template('clinic_profile.html', clinic=clinic, doctors=doctors, reviews=reviews, photos=photos, services=services, map_query=map_query)


@bp.route('/request', methods=['POST'])
def create_request():
    # Require login for appointment requests
    patient_id = session.get('patient_id')
    if not patient_id:
        flash('You must be logged in as a patient to request an appointment.')
        return redirect(request.referrer or url_for('patient.index'))
    clinic_id = request.form.get('clinic_id')
    doctor_id = request.form.get('doctor_id') or None
    start = request.form.get('requested_start')
    end = request.form.get('requested_end')
    reason = request.form.get('reason')
    if not start or not end:
        flash('Please provide both start and end times for your request.')
        return redirect(request.referrer or url_for('patient.index'))
    try:
        sql = '''INSERT INTO appointment_request
                 (patient_id, clinic_id, doctor_id, requested_start, requested_end, reason)
                 VALUES (%s,%s,%s,%s,%s,%s)'''
        db.query_db(sql, (patient_id, clinic_id, doctor_id, start, end, reason), commit=True)
        row = db.query_db('SELECT LAST_INSERT_ID() as id', one=True)
        req_id = row['id'] if row else None
        # Notify clinic and patient in-app
        if clinic_id and req_id:
            create_notification(
                recipient_type='clinic',
                recipient_id=int(clinic_id),
                appointment_request_id=req_id,
                message='New appointment request received.',
            )
        if patient_id and req_id:
            create_notification(
                recipient_type='patient',
                recipient_id=int(patient_id),
                appointment_request_id=req_id,
                message='Your appointment request has been submitted.',
            )
        flash('Appointment request submitted successfully!')
    except Exception as e:
        flash('Failed to submit appointment request: ' + str(e))
    # After submitting a request, send the user to their dashboard so they
    # immediately see the styled request card and any notifications.
    return redirect(url_for('patient.dashboard'))


@bp.route('/clinic/<int:clinic_id>/reviews', methods=['POST'])
@login_required_patient
def create_review(clinic_id):
    """Create a simple 1-5 star review for a clinic.

    - Uses the logged-in patient id from the session.
    - Stores rating (1-5) and an optional comment.
    """

    pid = session.get('patient_id')
    if not pid:
        return redirect(url_for('auth.login'))

    try:
        rating = int(request.form.get('rating', 0))
    except ValueError:
        rating = 0
    comment = (request.form.get('comment') or '').strip()

    if rating < 1 or rating > 5:
        flash('Rating must be between 1 and 5')
        return redirect(url_for('patient.clinic_profile', clinic_id=clinic_id))

    db.query_db(
        'INSERT INTO clinic_review (clinic_id, patient_id, rating, comment) VALUES (%s,%s,%s,%s)',
        (clinic_id, pid, rating, comment or None),
        commit=True,
    )
    flash('Thank you for your review')
    return redirect(url_for('patient.clinic_profile', clinic_id=clinic_id))


@bp.route('/patient/profile', methods=['GET', 'POST'])
@login_required_patient
def edit_profile():
    # Simple profile edit page for logged-in patients
    from flask import g
    from .forms import PatientProfileForm

    patient = g.patient
    form = PatientProfileForm()

    # populate city choices
    cities = db.query_db('SELECT id, name FROM city ORDER BY name') or []
    form.city_id.choices = [(0, '— none —')] + [(c['id'], c['name']) for c in cities]

    if request.method == 'GET':
        form.name.data = patient.get('name')
        form.phone.data = patient.get('phone')
        form.email.data = patient.get('email')
        form.preferred_language.data = patient.get('preferred_language') or 'rw'
        form.city_id.data = patient.get('city_id') or 0

    if form.validate_on_submit():
        try:
            city_id = form.city_id.data or None
            if city_id == 0:
                city_id = None
            db.query_db(
                'UPDATE patient SET name=%s, phone=%s, email=%s, preferred_language=%s, city_id=%s WHERE id = %s',
                (form.name.data, form.phone.data, form.email.data or None, form.preferred_language.data, city_id, patient['id']),
                commit=True,
            )
            flash('Profile updated')
            return redirect(url_for('patient.dashboard'))
        except Exception as e:
            flash('Failed to update profile: ' + str(e))

    return render_template('patient/edit_profile.html', form=form)


@bp.route('/request/<int:req_id>/cancel', methods=['GET', 'POST'])
@login_required_patient
def cancel_request(req_id):
    """Allow a patient to cancel their appointment request with a required message."""
    pid = session.get('patient_id')
    if not pid:
        return redirect(url_for('auth.login'))

    req = db.query_db('SELECT * FROM appointment_request WHERE id = %s', (req_id,), one=True)
    if not req or req.get('patient_id') != pid:
        flash('Request not found or not authorized')
        return redirect(url_for('patient.dashboard'))

    if request.method == 'POST':
        message = (request.form.get('message') or '').strip()
        if not message:
            flash('Please provide a cancellation message')
            return render_template('patient/cancel_request.html', request=req)
        try:
            # Remove any confirmed appointment tied to this request
            db.query_db('DELETE FROM appointment WHERE appointment_request_id = %s', (req_id,), commit=True)
            # Mark request as declined (use existing status)
            db.query_db("UPDATE appointment_request SET status = 'declined' WHERE id = %s", (req_id,), commit=True)
            # Notify clinic and patient
            if req.get('clinic_id'):
                create_notification(recipient_type='clinic', recipient_id=req['clinic_id'], message=f"Patient canceled request #{req_id}: {message}")
            create_notification(recipient_type='patient', recipient_id=pid, message=f"You canceled request #{req_id}: {message}")
            flash('Appointment request canceled')
            return redirect(url_for('patient.dashboard'))
        except Exception as e:
            flash('Failed to cancel request: ' + str(e))
            return redirect(url_for('patient.dashboard'))

    return render_template('patient/cancel_request.html', request=req)


@bp.route('/patient/dashboard')
def dashboard():
    # patient dashboard: show recent requests and appointments for logged-in patient
    pid = None
    # session-based check: if patient logged in via session
    from flask import session
    pid = session.get('patient_id')
    if not pid:
        return redirect(url_for('auth.login'))
    # Load recent requests with clinic names for better display
    requests = db.query_db(
        '''SELECT ar.*, c.name as clinic_name
           FROM appointment_request ar
           LEFT JOIN clinic c ON ar.clinic_id = c.id
           WHERE ar.patient_id = %s
           ORDER BY ar.created_at DESC''',
        (pid,)
    ) or []

    appointments = db.query_db(
        'SELECT a.*, c.name as clinic_name FROM appointment a JOIN clinic c ON a.clinic_id = c.id WHERE a.appointment_request_id IN (SELECT id FROM appointment_request WHERE patient_id = %s)',
        (pid,)
    ) or []

    # Recent notifications for this patient (include related clinic when available)
    notifications = db.query_db(
        '''SELECT n.*, c.name as clinic_name, ar.id as request_id
           FROM notification n
           LEFT JOIN appointment_request ar ON n.appointment_request_id = ar.id
           LEFT JOIN clinic c ON ar.clinic_id = c.id
           WHERE n.recipient_type = 'patient' AND n.recipient_id = %s
           ORDER BY n.created_at DESC
           LIMIT 20''',
        (pid,)
    ) or []

    # mark patient notifications as read when viewing dashboard
    try:
        db.query_db(
            "UPDATE notification SET read_at = CURRENT_TIMESTAMP WHERE recipient_type = 'patient' AND recipient_id = %s AND read_at IS NULL",
            (pid,),
            commit=True,
        )
    except Exception:
        pass

    return render_template('patient/dashboard.html', requests=requests, appointments=appointments, notifications=notifications)
