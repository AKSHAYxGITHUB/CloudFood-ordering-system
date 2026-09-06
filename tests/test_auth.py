from tests.conftest import login


def test_signup_creates_customer(client):
    resp = client.post(
        "/auth/signup",
        data={
            "name": "New User",
            "email": "newuser@example.com",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Account created" in resp.data or b"log in" in resp.data.lower()


def test_login_with_valid_credentials(client):
    resp = login(client, "customer@foodies.com", "Customer123!")
    assert resp.status_code == 200
    assert b"Restaurants" in resp.data


def test_login_with_invalid_password_fails(client):
    resp = login(client, "customer@foodies.com", "wrong-password")
    assert b"Invalid email or password" in resp.data


def test_account_lockout_after_repeated_failures(client, app):
    for _ in range(app.config["MAX_FAILED_LOGIN_ATTEMPTS"]):
        login(client, "customer@foodies.com", "wrong-password")

    resp = login(client, "customer@foodies.com", "Customer123!")
    assert b"locked" in resp.data.lower()


def test_admin_dashboard_requires_admin_role(client):
    login(client, "customer@foodies.com", "Customer123!")
    resp = client.get("/admin/", follow_redirects=True)
    assert resp.status_code == 403


def test_admin_login_reaches_dashboard(client):
    resp = login(client, "admin@foodies.com", "ChangeMe123!")
    assert b"Dashboard" in resp.data or b"Restaurant Admin" in resp.data
