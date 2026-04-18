# Clinic System (MVP)

This is a Flask + MySQL clinic appointment marketplace prototype.

Quick start (development):

1. Copy `.env.example` to `.env` and fill DB credentials.
2. Install Python deps: `pip install -r requirements.txt`.
3. Apply schema:

```powershell
python -m database.apply_schema
```

4. Seed data:

```powershell
python .\database\seed.py
```

5. Run dev server:

```powershell
$Env:FLASK_APP='run.py'
$Env:FLASK_ENV='development'
python -m flask run
```

Project structure highlights:
- `app/` — Flask app package (blueprints under `auth`, `clinic`, `admin`, `patient`)
- `templates/` — Jinja2 templates; modular partials in `templates/partials`
- `database/` — schema and helper scripts

Branding: Blue (`--brand-500`) and white backgrounds are used across templates.

If you want, I can now:
- Continue finishing UI templates and add more inline docs, or
- Implement more RBAC details and automated tests.

Tell me which area to continue next.