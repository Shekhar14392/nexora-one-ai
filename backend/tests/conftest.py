import os, sys
os.environ["NEXORA_JWT_SECRET"] = "test-secret-for-ci-only-0123456789abcdef"
os.environ["NEXORA_ENV"] = "development"
os.environ["NEXORA_DATABASE_URL"] = "sqlite:///./test_nexora.db"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    import os
    if os.path.exists("test_nexora.db"):
        os.remove("test_nexora.db")
    from app.main import app
    with TestClient(app) as c:
        yield c
