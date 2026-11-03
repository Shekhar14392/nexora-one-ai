import os
from fastapi.testclient import TestClient
import pytest

@pytest.fixture(scope="module")
def client():
    if os.path.exists("test_nexora.db"):
        os.remove("test_nexora.db")
    from app.main import app
    with TestClient(app) as c:
        yield c

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

def test_register_login_me(client):
    r = client.post("/auth/register", json={"email": "owner1@example.com", "password": "S3curePass!23",
                                            "full_name": "Test Owner", "organization_name": "TestOrg"})
    assert r.status_code == 201, r.text
    tokens = r.json()
    assert tokens["role"] == "user"
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/auth/me", headers=h)
    assert me.status_code == 200 and me.json()["email"] == "owner1@example.com"
    r2 = client.post("/auth/login", json={"email": "owner1@example.com", "password": "S3curePass!23"})
    assert r2.status_code == 200 and "refresh_token" in r2.json()
    # duplicate registration is rejected
    r3 = client.post("/auth/register", json={"email": "owner1@example.com", "password": "S3curePass!23"})
    assert r3.status_code == 409

def test_refresh_and_wrong_password(client):
    r = client.post("/auth/login", json={"email": "owner1@example.com", "password": "wrong-password-1"})
    assert r.status_code == 401
    reg = client.post("/auth/register", json={"email": "refresher@example.com", "password": "S3curePass!23"})
    refresh = client.post("/auth/refresh", json={"refresh_token": reg.json()["refresh_token"]})
    assert refresh.status_code == 200

def test_user_cannot_access_admin(client):
    tokens = client.post("/auth/register", json={"email": "plain@example.com", "password": "S3curePass!23"}).json()
    r = client.get("/admin/users", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 403

def test_license_flow(client):
    # no token at all -> unauthorized
    assert client.post("/admin/licenses/issue", json={}).status_code in (401, 403)
    tokens = client.post("/auth/register", json={"email": "lic@example.com", "password": "S3curePass!23"}).json()
    assert client.post("/admin/licenses/issue", json={"kind": "commercial"},
                       headers={"Authorization": f"Bearer {tokens['access_token']}"}).status_code == 403

def test_checkout_without_gateway(client):
    tokens = client.post("/auth/register", json={"email": "bill@example.com", "password": "S3curePass!23"}).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post("/billing/checkout", json={"plan_code": "pro", "period": "monthly"}, headers=h)
    assert r.status_code == 200 and r.json()["provider"] == "manual"
    # subscription must NOT be active without verified payment
    s = client.get("/billing/subscription", headers=h).json()
    assert s["status"] == "pending"

def test_content_generation_fallback(client):
    tokens = client.post("/auth/register", json={"email": "content@example.com", "password": "S3curePass!23"}).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post("/marketing/content/generate", json={"kind": "blog", "topic": "AI marketing for bakeries"}, headers=h)
    assert r.status_code == 201
    assert "template draft" in r.json()["body"] or len(r.json()["body"]) > 50

def test_lead_scoring(client):
    tokens = client.post("/auth/register", json={"email": "leadz@example.com", "password": "S3curePass!23"}).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    r = client.post("/crm/leads", json={"name": "Asha", "email": "asha@example.com", "phone": "+91 90000 00000",
                                        "source": "referral"}, headers=h)
    assert r.status_code == 201 and r.json()["score"] == 80
