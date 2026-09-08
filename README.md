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

Edit `.env` and set long, separate random values for `SECRET_KEY` and `WEBHOOK_TOKEN`, plus a development `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD`.

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

## Automatic SharePoint Sync

For a free automatic sync, use GitHub Actions with Microsoft Graph. The workflow in `.github/workflows/sharepoint-sync.yml` runs every 30 minutes and can also be started manually.

Configure these GitHub repository secrets:

- `MS_TENANT_ID`
- `MS_CLIENT_ID`
- `MS_CLIENT_SECRET`
- `SHAREPOINT_SITE_ID`
- `SHAREPOINT_DRIVE_ID`
- `SHAREPOINT_FILE_PATH`, for example `General/DQ - Testing Tracker - 2026.xlsm`
- `TEAM_TRACKER_WEBHOOK_TOKEN`

Optional secret:

- `SHAREPOINT_ITEM_ID`, if you prefer a fixed drive item ID instead of `SHAREPOINT_FILE_PATH`

Optional repository variable:

- `TEAM_TRACKER_BASE_URL`, defaults to `https://naren2503-team-tracker.onrender.com`

The Microsoft Entra app used for `MS_CLIENT_ID` needs Microsoft Graph application access to read the SharePoint file, such as `Sites.Read.All`, with admin consent.

## Security Notes

- Do not use `.env.example` values in production.
- Put production secrets in environment variables or a secret manager.
- Set `SECURE_COOKIES=true` when the app is served over HTTPS.
- Keep `WEBHOOK_TOKEN` separate from `SECRET_KEY`; append it to the Office Script or Power Automate webhook URL at configuration time.
- Use PostgreSQL for shared deployment.
- Put the app behind HTTPS.
- Prefer Microsoft Entra ID for organization login in production.
