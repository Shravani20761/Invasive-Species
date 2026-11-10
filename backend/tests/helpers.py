def register(client, email="citizen@example.com", password="password123", name="Field Observer"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
