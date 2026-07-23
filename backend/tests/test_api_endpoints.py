import pytest
from app import auth

@pytest.mark.asyncio
async def test_auth_token_success(async_client):
    """Test POST /auth/token with valid demo credentials."""
    response = await async_client.post(
        "/auth/token",
        json={"username": auth.DEMO_USERNAME, "password": auth.DEMO_PASSWORD}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_auth_token_invalid(async_client):
    """Test POST /auth/token with invalid credentials returns 401."""
    response = await async_client.post(
        "/auth/token",
        json={"username": auth.DEMO_USERNAME, "password": "wrong_password"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_rings_unauthenticated(async_client):
    """Test GET /rings without Bearer token returns 401 Unauthorized."""
    response = await async_client.get("/rings")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_rings_authenticated(async_client, auth_headers):
    """Test GET /rings with valid Bearer token returns 200 OK."""
    response = await async_client.get("/rings", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_transaction_score_unauthenticated(async_client):
    """Test GET /transactions/{id}/score without Bearer token returns 401."""
    response = await async_client.get("/transactions/00000000-0000-0000-0000-000000000001/score")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_transaction_score_authenticated(async_client, auth_headers):
    """Test GET /transactions/{id}/score with valid Bearer token."""
    response = await async_client.get(
        "/transactions/00000000-0000-0000-0000-000000000000/score",
        headers=auth_headers
    )
    # Returns 404 if transaction ID doesn't exist or 200 if present; key is that it passes auth (not 401)
    assert response.status_code in (200, 404)

@pytest.mark.asyncio
async def test_get_dashboard_metrics(async_client):
    """Test GET /dashboard/metrics returns 200 OK."""
    response = await async_client.get("/dashboard/metrics")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
