# Team Tracker App

A professional web application converted from the analysed Excel tracker `DQ - Testing Tracker - 2026.xlsm`.

For a manager-ready overview of the architecture, operations, security, sync options, and source ownership, see [DQ Team Tracker: End-to-End Guide](docs/manager-guide.md).

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

## Jira Tab

The app includes a simple read-only Jira tab. Configure it with Jira Cloud API credentials in `.env` or the Render environment:

```text
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_AUTH_MODE=basic
JIRA_PROJECT_KEY=ABC
```

Create the API token in Jira under **Profile -> Personal settings -> Security -> API tokens**. The token stays server-side; the browser only receives issue data. `JIRA_PROJECT_KEY` is optional. When it is blank, the tab lists the latest issues visible to the configured Jira account. Restart the app after changing these settings, then open the `Jira` tab.

For Jira Server/Data Center or an internal Jira endpoint using a bearer token, use:

```text
JIRA_BASE_URL=https://your-jira-host
JIRA_AUTH_MODE=bearer
JIRA_API_TOKEN=your-bearer-token
JIRA_EMAIL=
JIRA_PROJECT_KEY=ABC
```

## Render Cold Start Page

The free Render web service may take time to wake after inactivity. Open the static DQ Team Tracker launch page first instead of bookmarking the application URL directly:

`https://naren-tracker-launch.onrender.com/`

The launch page stays visible while it checks the application health endpoint and automatically opens Team Tracker once Render is ready. To open a specific page after the application wakes, append its path, for example `https://naren-tracker-launch.onrender.com/?path=/monthly`.

## Cloudflare Cold Start Proxy

To show the DQ Team Tracker loading page on every refresh, deploy `cloudflare/worker.js` as a Cloudflare Worker. The Worker is an always-available proxy: it forwards normal requests to Render and shows the branded loading page only while the Render service is waking.

1. Create a free Cloudflare account, then open **Workers & Pages** and select **Create application** -> **Create Worker**.
2. Name it `dq-team-tracker-proxy`, replace the generated Worker code with `cloudflare/worker.js`, and select **Deploy**.
3. Open the generated `https://dq-team-tracker-proxy.<your-subdomain>.workers.dev` address and sign in to Team Tracker there.
4. Bookmark and share the Worker address, not the `onrender.com` application address. Refreshes through the Worker show the DQ Team Tracker loading page instead of Render's cold-start screen.

For a production-friendly address, attach a custom domain to the Worker in Cloudflare. Do not point the domain directly to Render; it must remain attached to the Worker. Cookies are specific to the Worker/custom-domain address, so users may need to sign in once after switching from the direct Render URL.

## Workbook Import

Use the Import page to upload `.xlsx` or `.xlsm` files. The importer reads the analysed source sheets:

- `DQ Task Tracker`
- `Daily Report - FT`
- `Daily Report - BT`

Supported modes:

- `merge`: update existing tracker tickets and add new rows
- `replace`: soft-delete existing tracker/work-log rows before import
- `add`: reject duplicate tracker tickets

## Local Windows Workbook Sync

If the SharePoint library is synchronized to OneDrive on a Windows PC, use `scripts/sync_local_workbook.ps1` as a no-premium alternative to Power Automate and GitHub Actions. It uploads the locally synchronized workbook directly to Team Tracker; the PC must be powered on, signed in, and online.

1. Copy `scripts/local_workbook_sync.config.ps1.example` to `scripts/local_workbook_sync.config.ps1`.
2. Set the local SharePoint-synchronized workbook path and the Render `WEBHOOK_TOKEN` in the copied file. The local configuration file is ignored by Git.
3. Test it from PowerShell: `powershell -ExecutionPolicy Bypass -File .\scripts\sync_local_workbook.ps1`.
4. In Windows Task Scheduler, create a task that starts at sign-in and repeats every 5 minutes. Its action is `powershell.exe` with arguments `-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\nsr467\team-tracker-app\scripts\sync_local_workbook.ps1"`.

The script imports with `replace` mode, so the dashboard reflects the workbook after each successful run. It stores the last successfully uploaded SHA-256 hash in the ignored `scripts/local_workbook_sync.state` file and skips the upload when the workbook content has not changed. The scheduled task still checks every five minutes, but unchanged checks do not contact Render. Do not use a workbook path still being copied by OneDrive; wait for its sync status to finish first.

## Excel Online Run Script Sync

The direct Excel Online Run Script workflow is separate from the scheduled GitHub Actions sync. To configure the direct one-click workflow once:

1. Open the Import page and copy the `Office Script JSON Sync Endpoint`.
2. Open the workbook in Teams or Excel Online, select **Automate** -> **New Script**, and paste the contents of `scripts/excel_office_sync.ts`.
3. Replace `SYNC_URL` in the script with the copied endpoint and save it.
4. Run the script whenever the workbook changes. It reads `DQ Task Tracker` and `Daily Report - FT`, then replaces the application data with the workbook contents.

The endpoint includes the webhook token, so do not commit a customized script containing the endpoint. The repository version contains only a placeholder. The script must be run from Excel Online; it is not executed automatically by the application.

### Power Automate limitation

Power Automate can trigger an Office Script when the SharePoint workbook is modified, but Office Scripts executed by Power Automate cannot make `fetch` calls to external APIs. Therefore, `scripts/excel_office_sync.ts` is for manual Excel Online execution only and will fail in Power Automate with `fetch is not defined`.

For a Power Automate flow, use `scripts/excel_power_automate_sync.ts` with this flow:

1. Trigger: SharePoint **When a file is created or modified (properties only)** for the workbook.
2. Action: Excel Online (Business) **Run script from SharePoint library** using `excel_power_automate_sync.ts`.
3. Action: send the returned `sheets` and `mode` to `/api/imports/office-script-sync` using an HTTP or equivalent custom connector action.

There is no way for Power Automate to update this Team Tracker application with zero delivery action. If HTTP is prohibited, use the existing scheduled GitHub Actions SharePoint sync instead, or build a Power Automate custom connector/database integration. The flow can still trigger the script without an HTTP trigger; the HTTP action is only the outbound step that delivers the result to Team Tracker.

## Security Notes

- Do not use `.env.example` values in production.
- Put production secrets in environment variables or a secret manager.
- Set `SECURE_COOKIES=true` when the app is served over HTTPS.
- Keep `WEBHOOK_TOKEN` separate from `SECRET_KEY`; append it to the Office Script or Power Automate webhook URL at configuration time.
- Use PostgreSQL for shared deployment.
- Put the app behind HTTPS.
- Prefer Microsoft Entra ID for organization login in production.
