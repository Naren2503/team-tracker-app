def login(client, email):
    response = client.post("/login", data={"email": email, "password": "Password12345!"}, follow_redirects=False)
    assert response.status_code == 303


def test_viewer_cannot_create_tracker_record(client):
    login(client, "viewer@test.local")
    response = client.post("/api/tracker", json={"ticket_id": "DQ9000", "status": "Pending"})
    assert response.status_code == 403


def test_viewer_cannot_access_admin_operations(client):
    login(client, "viewer@test.local")
    response = client.get("/api/admin/users")
    assert response.status_code == 403


def test_admin_can_create_user(client):
    login(client, "admin@test.local")
    response = client.post("/api/admin/users", json={"email": "new@test.local", "display_name": "New User", "password": "Password12345!", "role_id": 3, "active": True})
    assert response.status_code == 200
    assert response.json()["email"] == "new@test.local"


def test_viewer_pages_and_export_do_not_expose_admin_records(client):
    login(client, "admin@test.local")
    create_response = client.post("/api/tracker", json={"ticket_id": "ADMIN-ONLY", "status": "Pending"})
    assert create_response.status_code == 200

    login(client, "viewer@test.local")
    tracker_page = client.get("/tracker")
    assert tracker_page.status_code == 200
    assert "ADMIN-ONLY" not in tracker_page.text
    assert 'href="/import"' not in tracker_page.text

    import_page = client.get("/import", follow_redirects=False)
    assert import_page.status_code in {302, 307}
    assert import_page.headers["location"] == "/"

    export = client.get("/api/exports/tracker.csv")
    assert export.status_code == 200
    assert "ADMIN-ONLY" not in export.text


def test_public_webhook_rejects_previous_hardcoded_token(client):
    response = client.post("/api/imports/webhook?token=team-tracker-sync", content=b"not-an-excel-file")
    assert response.status_code == 403

    configured = client.post("/api/imports/webhook?token=test-webhook-secret", content=b"not-an-excel-file")
    assert configured.status_code == 400
    assert configured.json()["detail"].startswith("Uploaded file is not a valid Excel file")


def test_import_page_shows_configured_sync_urls(client):
    login(client, "admin@test.local")
    response = client.get("/import")
    assert response.status_code == 200
    assert "team-tracker-sync" not in response.text
    assert "token=test-webhook-secret&amp;mode=replace" in response.text
    assert "/api/imports/webhook" in response.text
    assert "/api/imports/office-script-sync" in response.text


def test_office_script_sync_accepts_workbook_grid(client):
    response = client.post(
        "/api/imports/office-script-sync?token=test-webhook-secret&mode=replace",
        json={
            "sheets": {
                "DQ Task Tracker": [
                    ["Ticket ID", "Date Started", "Date Ended", "Tester", "DQ Status"],
                    ["DQ9001", "2026-01-01", None, "Tester", "In progress"],
                ]
            },
            "mode": "replace",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["successful_rows"] == 1


def test_admin_user_list_does_not_expose_password_hashes(client):
    login(client, "admin@test.local")
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    assert all("password_hash" not in user for user in response.json())


def test_admin_user_validation_returns_controlled_errors(client):
    login(client, "admin@test.local")
    duplicate = client.post("/api/admin/users", json={"email": "ADMIN@test.local", "display_name": "Duplicate", "password": "Password12345!", "role_id": 1, "active": True})
    assert duplicate.status_code == 409

    users = client.get("/api/admin/users").json()
    admin_id = next(user["id"] for user in users if user["email"] == "admin@test.local")
    invalid_role = client.put(f"/api/admin/users/{admin_id + 1}", json={"role_id": 9999})
    assert invalid_role.status_code == 400
    self_deactivate = client.put(f"/api/admin/users/{admin_id}", json={"active": False})
    assert self_deactivate.status_code == 400


def test_login_cookie_can_be_marked_secure(client, monkeypatch):
    from types import SimpleNamespace
    from app.routers import auth

    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(secure_cookies=True, session_minutes=480))
    response = client.post("/login", data={"email": "admin@test.local", "password": "Password12345!"}, follow_redirects=False)
    assert "Secure" in response.headers["set-cookie"]
