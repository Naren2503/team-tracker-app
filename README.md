# Team Tracker App

A professional web application converted from the analysed Excel tracker `DQ - Testing Tracker - 2026.xlsm`.

## Stack

- FastAPI backend with server-rendered responsive pages
- SQLAlchemy models, SQLite for local development, PostgreSQL-compatible architecture
- Jinja templates, CSS, and small JavaScript enhancements
- OpenPyXL Excel parsing
- Cookie-based local authentication with hashed passwords
- Backend-enforced role-based access control

## Setup

```powershell
cd C:\Users\nsr467\team-tracker-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a long random `SECRET_KEY`, plus a development `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD`.

## Run

```powershell
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Workbook Import

Use the Import page to upload `.xlsx` or `.xlsm` files. The importer reads the analysed source sheets:

- `DQ Task Tracker`
- `Daily Report - FT`
- `Daily Report - BT`

Supported modes:

- `merge`: update existing tracker tickets and add new rows
- `replace`: soft-delete existing tracker/work-log rows before import
- `add`: reject duplicate tracker tickets

## Security Notes

- Do not use `.env.example` values in production.
- Put production secrets in environment variables or a secret manager.
- Use PostgreSQL for shared deployment.
- Put the app behind HTTPS.
- Prefer Microsoft Entra ID for organization login in production.
