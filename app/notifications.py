"""Simple in-app notification helper.

This module centralizes inserts into the `notification` table so routes can
call a single function instead of repeating raw SQL. For now, notifications
are in-app only (channel = 'in_app'), but the schema supports others.
"""

from app import db


def create_notification(*, recipient_type, recipient_id, message,
                        appointment_id=None, appointment_request_id=None,
                        channel='in_app'):
    """Insert a notification row.

    Parameters
    ----------
    recipient_type: str
        One of 'patient', 'clinic', 'staff', 'admin'.
    recipient_id: int | None
        The id in the corresponding table (or clinic id when type='clinic').
    message: str
        Short human-readable message (shown in the UI later).
    appointment_id: int | None
        Optional related appointment id.
    appointment_request_id: int | None
        Optional related appointment_request id.
    channel: str
        Channel hint; kept as 'in_app' for now.
    """

    sql = (
        "INSERT INTO notification (appointment_id, appointment_request_id, "
        "recipient_type, recipient_id, channel, message) "
        "VALUES (%s,%s,%s,%s,%s,%s)"
    )
    db.query_db(
        sql,
        (appointment_id, appointment_request_id, recipient_type, recipient_id, channel, message),
        commit=True,
    )
