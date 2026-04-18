from functools import wraps
from flask import session, redirect, url_for, flash, g
from app import db


def role_required(*roles):
    """Decorator factory to require one or more roles.

    Usage:
      @role_required('patient')
      @role_required('superadmin')
      @role_required('clinicadmin', 'superadmin')

    Roles supported:
      - 'patient' : session must have `patient_id` and patient loaded into `g.patient`
      - staff roles (e.g. 'superadmin', 'clinicadmin', 'staff') : session must have `staff_id`
        and `g.staff` will be loaded. Use 'staff' to allow any staff role.

    The decorator checks the currently-logged-in session (patient vs staff) and validates
    the user's role against the allowed roles. Redirects to the appropriate login page
    with a flash message when not authorized.
    """

    allowed = set(r.lower() for r in roles)

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Prefer staff session if present, otherwise patient.
            sid = session.get('staff_id')
            pid = session.get('patient_id')

            # If staff session present, validate staff role
            if sid:
                staff = db.query_db('SELECT id, clinic_id, name, email, role FROM staff WHERE id = %s', (sid,), one=True)
                if not staff:
                    session.clear()
                    flash('Please log in')
                    return redirect(url_for('auth.staff_login'))
                g.staff = staff
                # normalize stored roles to common names used by decorators
                raw_role = (staff.get('role') or '').lower()
                # map schema roles to semantic roles used in decorators
                role_map = {
                    'manager': 'clinicadmin',
                    'staff': 'staff',
                    'superadmin': 'superadmin'
                }
                staff_role = role_map.get(raw_role, raw_role)
                # Allow any staff if 'staff' in allowed, or match specific role
                if 'staff' in allowed or staff_role in allowed:
                    return f(*args, **kwargs)
                flash('Access denied')
                return redirect(url_for('auth.staff_login'))

            # Else check patient session
            if pid:
                if 'patient' not in allowed:
                    flash('Access denied')
                    return redirect(url_for('auth.login'))
                patient = db.query_db('SELECT id, name, phone, email, city_id FROM patient WHERE id = %s', (pid,), one=True)
                if not patient:
                    session.clear()
                    flash('Please log in')
                    return redirect(url_for('auth.login'))
                g.patient = patient
                return f(*args, **kwargs)

            # No valid session
            # Choose login redirect based on allowed roles preference
            if any(r in ('superadmin', 'clinicadmin', 'staff') for r in allowed):
                flash('Please log in as staff')
                return redirect(url_for('auth.staff_login'))
            flash('Please log in')
            return redirect(url_for('auth.login'))

        return wrapped

    return decorator


# Backwards-compatible aliases using the new decorator
def login_required_patient(f):
    return role_required('patient')(f)


def staff_required(f):
    return role_required('staff')(f)


def superadmin_required(f):
    return role_required('superadmin')(f)
