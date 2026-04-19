import os
from flask import Flask


def create_app():
    # Ensure Flask looks for templates/static at the project root `templates/` and `static/`
    ROOT = os.path.dirname(os.path.dirname(__file__))
    template_folder = os.path.join(ROOT, 'templates')
    static_folder = os.path.join(ROOT, 'static')
    app = Flask(__name__, instance_relative_config=True, template_folder=template_folder, static_folder=static_folder)
    # Load default config (edit /instance/config.py, .env, or set env vars)
    # If a .env file exists, load it so environment vars are available early
    try:
        from dotenv import load_dotenv
        # load .env in project root if present
        load_dotenv()
    except Exception:
        pass

    app.config.from_object('app.config.Config')
    try:
        app.config.from_pyfile('config.py')
    except FileNotFoundError:
        # instance/config.py optional for local secrets
        pass

    # initialize extensions / helpers
    from app import db
    db.init_app(app)
    # CSRF protection for Flask-WTF forms
    try:
        from flask_wtf import CSRFProtect
        csrf = CSRFProtect()
        csrf.init_app(app)
    except Exception:
        # if Flask-WTF not installed yet, skip; requirements updated earlier
        pass

    # register blueprints
    from app.patient.routes import bp as patient_bp
    from app.clinic.routes import bp as clinic_bp
    from app.admin.routes import bp as admin_bp
    from app.auth.routes import bp as auth_bp
    from app.notifications_routes import bp as notifications_bp
    from app.reports.routes import bp as reports_bp

    app.register_blueprint(patient_bp)
    app.register_blueprint(clinic_bp, url_prefix='/clinic')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reports_bp)

    # Inject unread notification count into templates so header can display a bell badge
    @app.context_processor
    def inject_notification_unread_count():
        from flask import session
        unread = 0
        try:
            if session.get('patient_id'):
                pid = session.get('patient_id')
                row = db.query_db("SELECT COUNT(*) as cnt FROM notification WHERE recipient_type = 'patient' AND recipient_id = %s AND read_at IS NULL", (pid,), one=True)
                if row:
                    unread = row.get('cnt') if isinstance(row, dict) else list(row.values())[0]
            elif session.get('staff_id'):
                staff = db.query_db('SELECT clinic_id FROM staff WHERE id = %s', (session.get('staff_id'),), one=True)
                if staff and staff.get('clinic_id'):
                    row = db.query_db("SELECT COUNT(*) as cnt FROM notification WHERE recipient_type = 'clinic' AND recipient_id = %s AND read_at IS NULL", (staff['clinic_id'],), one=True)
                    if row:
                        unread = row.get('cnt') if isinstance(row, dict) else list(row.values())[0]
        except Exception:
            unread = 0
        return dict(notification_unread_count=unread)

    return app
