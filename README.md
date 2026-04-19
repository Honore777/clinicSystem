# Clinic System

Clinic System is a Flask + MySQL web application for discovering clinics, requesting appointments, managing clinic operations, and running superadmin reports.

It supports three primary actor groups:
- Patients: browse clinics, request appointments, leave reviews, manage profile, cancel requests with a required message.
- Clinic staff/managers: review pending requests, approve/decline requests, manage clinic staff.
- Superadmin: verify/activate/deactivate/delete clinics, manage staff, send clinic alerts, view reports.


## 1. Tech Stack

- Backend: Flask
- Database: MySQL (via PyMySQL)
- Forms + CSRF: Flask-WTF / WTForms
- Data analysis/report rendering: pandas
- Templates/UI: Jinja2 + Tailwind CSS classes
- Auth: session-based (patient and staff sessions)


## 2. Core Features

- Clinic onboarding with image upload
- Patient and staff authentication
- Role-based access control (`patient`, `staff`, `clinicadmin`, `superadmin`)
- Appointment request lifecycle:
	- patient submits request
	- clinic approves or declines
	- approved request creates a confirmed appointment row
- Required-message cancellation flow for patients
- In-app notification system for patient/clinic events
- Superadmin dashboard for clinic operations
- Reports page with simple SQL-based metrics shown as cards/table


## 3. Project Structure

```
clinic_system/
├─ app/
│  ├─ __init__.py            # app factory, blueprint registration, context processor
│  ├─ config.py              # env-based configuration
│  ├─ db.py                  # MySQL connection + query helper
│  ├─ auth/                  # patient/staff auth + role decorators
│  ├─ patient/               # public browsing + patient dashboard/actions
│  ├─ clinic/                # clinic onboarding + clinic staff dashboard/actions
│  ├─ admin/                 # superadmin dashboard + clinic/staff management
│  ├─ reports/               # superadmin reports routes
│  ├─ notifications.py       # helper to create notifications
│  └─ notifications_routes.py# notifications listing endpoints
├─ templates/                # Jinja templates
├─ static/                   # static assets + uploads folder
├─ database/
│  ├─ schema.sql             # schema definition
│  ├─ apply_schema.py        # apply schema script
│  ├─ seed.py                # seed demo data
│  ├─ super_admin.py         # create superadmin user
│  ├─ add_is_active.py       # add clinic.is_active if missing
│  └─ print_clinics.py       # quick diagnostics
├─ scripts/
│  └─ df_cli.py              # simple pandas SQL script
├─ run.py                    # app entry point
├─ requirements.txt
└─ README.md
```


## 4. Setup and Run (Windows PowerShell)

### 4.1 Create and activate environment

```powershell
conda activate system_env
```

or use your preferred venv.

### 4.2 Install dependencies

```powershell
pip install -r requirements.txt
```

### 4.3 Configure environment

Create `.env` in project root and set at least:

```env
SECRET_KEY=change-me
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=clinic_system
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16777216
```

Notes:
- `DATABASE_URL` is also supported (see `app/config.py`).
- `instance/config.py` can override config for local secrets.

### 4.4 Apply schema and seed

```powershell
python -m database.apply_schema
python .\database\seed.py
```

### 4.5 (Optional) create superadmin

```powershell
python .\database\super_admin.py
```

### 4.6 Run app

```powershell
$Env:FLASK_APP='run.py'
$Env:FLASK_ENV='development'
python -m flask run
```

Open: `http://127.0.0.1:5000`


## 5. Authentication and Roles

### Patient auth
- Register: `GET/POST /auth/register`
- Login: `GET/POST /auth/login`
- Logout: `GET /auth/logout`

### Staff auth
- Staff login: `GET/POST /auth/staff/login`

### Role enforcement
- `app/auth/decorators.py` enforces role-based access.
- Session keys:
	- patient: `session['patient_id']`
	- staff: `session['staff_id']`, `session['staff_role']`


## 6. Main User Flows

### 6.1 Patient flow
1. Browse clinics: `GET /`
2. View clinic details: `GET /clinic/<clinic_id>`
3. Submit request: `POST /request`
4. Track updates in dashboard: `GET /patient/dashboard`
5. Edit profile: `GET/POST /patient/profile`
6. Cancel request with mandatory reason:
	 - `GET/POST /request/<req_id>/cancel`

### 6.2 Clinic manager/staff flow
1. Staff login
2. Dashboard: `GET /clinic/dashboard`
3. Approve pending request: `POST /clinic/request/<req_id>/approve`
4. Decline pending request: `POST /clinic/request/<req_id>/decline`
5. Manage clinic staff (manager only): `GET/POST /clinic/staff`

### 6.3 Superadmin flow
1. Superadmin login redirects to `GET /admin/`
2. Manage clinics from dashboard:
	 - verify: `POST /admin/clinics/<clinic_id>/verify`
	 - toggle active: `POST /admin/clinics/<clinic_id>/toggle`
	 - delete: `POST /admin/clinics/<clinic_id>/delete`
	 - alert clinic: `POST /admin/clinics/<clinic_id>/alert`
3. Manage staff: `GET/POST /admin/staff`
4. View reports: `GET /admin/reports`


## 7. Reports Module

Reports are intentionally simple and use direct SQL aggregation, then render results in templates.

Current report metrics on `/admin/reports`:
1. Total appointments
2. Total patients
3. Active clinics
4. Pending requests
5. Top clinics by request count

Detailed report view endpoint:
- `GET /admin/reports/run?name=appointments_per_clinic`
- `GET /admin/reports/run?name=top_clinics_by_requests`
- `GET /admin/reports/run?name=number_of_patients`


## 8. Database Overview

Schema is defined in `database/schema.sql`.

Main tables:
- `city`
- `clinic`
- `clinic_photo`
- `doctor`
- `patient`
- `appointment_request`
- `appointment`
- `staff`
- `notification`
- `clinic_review`

Important relationships:
- `appointment_request` links patient, clinic, and optional doctor.
- `appointment` references `appointment_request` (one-to-one via unique key).
- `staff` may be clinic-scoped or superadmin-level.
- `notification` references optional appointment/request metadata.


## 9. Notification Behavior

Notifications are created for key events, including:
- new appointment request
- request approved/declined
- patient cancellation with reason
- superadmin alert to clinic

Unread badge count is injected globally via app context processor in `app/__init__.py`.


## 10. Utility Scripts

### Data and diagnostics

```powershell
python .\database\test_connection.py
python .\database\list_tables.py
python .\database\print_clinics.py
python .\database\add_is_active.py
```

### Simple DataFrame script

`scripts/df_cli.py` is a minimal script for running one SQL query and inspecting the resulting DataFrame.


## 11. Security Notes

- Keep secrets in `.env` or `instance/config.py`; never commit credentials.
- Rotate any leaked OAuth/API credentials immediately.
- CSRF protection is enabled for Flask-WTF forms.
- Use HTTPS and stronger production secrets/config before deployment.


## 12. Known Limitations / Next Improvements

- Add automated tests for core flows (auth, approval, cancellation, admin actions).
- Add formal migration framework (Alembic or lightweight migration runner).
- Add audit logs for admin actions (verify/delete/toggle).
- Improve report exports (CSV download option).
- Add soft-delete for clinics (instead of hard delete) if needed for compliance.


## 13. Troubleshooting

### App cannot connect to MySQL
- Verify `MYSQL_*` values in `.env`.
- Run `python .\database\test_connection.py`.

### `is_active` column missing
- Run:

```powershell
python .\database\add_is_active.py
```

### Templates fail with endpoint build errors
- Confirm endpoint names in routes and templates match exactly.
- Restart Flask server after route changes.


## 14. License and Usage

This project is currently an internal prototype/MVP. Add your preferred license before public distribution.