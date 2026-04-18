from flask import Blueprint, render_template
from flask import session
from app import db

bp = Blueprint('notifications', __name__)


@bp.route('/notifications')
def index():
    """Simple notifications list for the logged-in user.

    - For patients: shows notifications where recipient_type='patient'.
    - For clinic staff: shows notifications where recipient_type='clinic' for
      their clinic, plus 'staff' entries for their staff id if we add those
      later.
    """

    nid = None
    notifications = []

    patient_id = session.get('patient_id')
    staff_id = session.get('staff_id')

    if patient_id:
        notifications = db.query_db(
            """SELECT n.*, c.name as clinic_name, ar.id as request_id
                   FROM notification n
                   LEFT JOIN appointment_request ar ON n.appointment_request_id = ar.id
                   LEFT JOIN clinic c ON ar.clinic_id = c.id
                   WHERE n.recipient_type = 'patient' AND n.recipient_id = %s
                   ORDER BY n.created_at DESC
                   LIMIT 50""",
            (patient_id,),
        ) or []
        # mark patient notifications as read when viewing the feed
        try:
            db.query_db(
                "UPDATE notification SET read_at = CURRENT_TIMESTAMP WHERE recipient_type = 'patient' AND recipient_id = %s AND read_at IS NULL",
                (patient_id,),
                commit=True,
            )
        except Exception:
            pass
    elif staff_id:
        # load staff to get clinic id
        staff = db.query_db('SELECT clinic_id FROM staff WHERE id = %s', (staff_id,), one=True)
        if staff and staff.get('clinic_id'):
            notifications = db.query_db(
                """SELECT n.*, p.name as patient_name
                       FROM notification n
                       LEFT JOIN appointment_request ar ON n.appointment_request_id = ar.id
                       LEFT JOIN patient p ON ar.patient_id = p.id
                       WHERE n.recipient_type = 'clinic' AND n.recipient_id = %s
                       ORDER BY n.created_at DESC
                       LIMIT 50""",
                (staff['clinic_id'],),
            ) or []
            # mark clinic notifications as read for this clinic
            try:
                db.query_db(
                    "UPDATE notification SET read_at = CURRENT_TIMESTAMP WHERE recipient_type = 'clinic' AND recipient_id = %s AND read_at IS NULL",
                    (staff['clinic_id'],),
                    commit=True,
                )
            except Exception:
                pass

    return render_template('notifications/index.html', notifications=notifications)
