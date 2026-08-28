import pytest

pytestmark = pytest.mark.asyncio


async def test_register_and_login(client):
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "jane@example.com", "password": "supersecret123", "full_name": "Jane Doe"},
    )
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert body["email"] == "jane@example.com"
    assert "hashed_password" not in body

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "jane@example.com", "password": "supersecret123"}
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]


async def test_login_with_wrong_password_fails(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "correcthorse123", "full_name": "Bob"},
    )
    resp = await client.post("/api/v1/auth/login", json={"email": "bob@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


async def test_duplicate_registration_conflict(client):
    payload = {"email": "dup@example.com", "password": "supersecret123", "full_name": "Dup User"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_with_valid_token(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "supersecret123", "full_name": "Carol"},
    )
    login = await client.post("/api/v1/auth/login", json={"email": "carol@example.com", "password": "supersecret123"})
    token = login.json()["access_token"]

    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "carol@example.com"
