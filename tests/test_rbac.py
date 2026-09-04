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
