import os
from urllib.parse import urlparse


class Config:
    # Allow loading from env; users can also create instance/config.py or .env
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret')

    # Support DATABASE_URL pattern (e.g. mysql+pymysql://user:pass@host:3306/db)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        parsed = urlparse(DATABASE_URL)
        MYSQL_HOST = parsed.hostname or os.environ.get('MYSQL_HOST', 'localhost')
        MYSQL_PORT = parsed.port or int(os.environ.get('MYSQL_PORT', 3306))
        MYSQL_USER = parsed.username or os.environ.get('MYSQL_USER', 'root')
        MYSQL_PASSWORD = parsed.password or os.environ.get('MYSQL_PASSWORD', '')
        MYSQL_DB = parsed.path.lstrip('/') if parsed.path else os.environ.get('MYSQL_DB', 'clinic_system')
    else:
        MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
        MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
        MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
        MYSQL_DB = os.environ.get('MYSQL_DB', 'clinic_system')

    # File uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    # Email / notifications (Brevo / Sendinblue)
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@example.com')
