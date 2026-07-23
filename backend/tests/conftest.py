import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Add backend directory to sys.path so app modules can be imported
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app import auth, database

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="module")
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture(scope="module")
def valid_token():
    return auth.create_access_token(data={"sub": auth.DEMO_USERNAME})

@pytest.fixture(scope="module")
def auth_headers(valid_token):
    return {"Authorization": f"Bearer {valid_token}"}
