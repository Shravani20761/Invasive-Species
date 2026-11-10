from tests.helpers import auth_header, register


def test_register_login_and_me(client):
    created = register(client)
    assert created["user"]["role"] == "citizen"
    me = client.get("/api/auth/me", headers=auth_header(created["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "citizen@example.com"

    login = client.post("/api/auth/login", json={"email": "citizen@example.com", "password": "password123"})
    assert login.status_code == 200
    bad = client.post("/api/auth/login", json={"email": "citizen@example.com", "password": "wrong-password"})
    assert bad.status_code == 401


def test_register_cannot_choose_a_privileged_role(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "password": "password123", "full_name": "A Person", "role": "admin"},
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "citizen"


def test_empty_overview_does_not_crash(client):
    headers = auth_header(register(client, email="empty@example.com")["access_token"])
    response = client.get("/api/analytics/overview", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_sightings"] == 0
    assert body["active_clusters"] == 0
    assert body["open_alerts"] == 0


def test_citizen_cannot_manage_species_or_settings(client):
    token = register(client)["access_token"]
    headers = auth_header(token)
    species = client.post(
        "/api/species",
        headers=headers,
        json={
            "common_name": "Test plant",
            "scientific_name": "Testus plantus",
            "category": "plant",
            "classification": "native",
        },
    )
    assert species.status_code == 403
    settings = client.get("/api/settings", headers=headers)
    assert settings.status_code == 403
    missing = client.get("/api/auth/me")
    assert missing.status_code == 401
