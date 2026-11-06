import httpx


class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._p = payload

    def json(self):
        return self._p


def _register(client, email):
    tokens = client.post("/auth/register", json={"email": email, "password": "S3curePass!23"}).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _enable_paypal(monkeypatch):
    monkeypatch.setattr("app.config.settings.paypal_client_id", "test-id")
    monkeypatch.setattr("app.config.settings.paypal_client_secret", "test-secret")


def test_checkout_paypal_creates_order(client, monkeypatch):
    h = _register(client, "pp@example.com")
    _enable_paypal(monkeypatch)
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if "/v1/oauth2/token" in url:
            return FakeResp(200, {"access_token": "tok"})
        return FakeResp(201, {"id": "PP-ORDER-1",
                              "links": [{"rel": "approve", "href": "https://paypal.example/approve"}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    r = client.post("/billing/checkout", json={"plan_code": "pro", "period": "monthly", "provider": "paypal"},
                    headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "paypal" and body["order_id"] == "PP-ORDER-1"
    assert body["approval_url"] == "https://paypal.example/approve"
    assert "/v1/oauth2/token" in calls[0] and "/v2/checkout/orders" in calls[1]
    invoices = client.get("/billing/invoices", headers=h).json()
    assert invoices[0]["status"] == "due"
    # subscription stays pending until the PayPal capture webhook verifies
    sub = client.get("/billing/subscription", headers=h).json()
    assert sub["status"] == "pending"


def test_checkout_paypal_gateway_rejected(client, monkeypatch):
    h = _register(client, "ppbad@example.com")
    _enable_paypal(monkeypatch)

    def fake_post(url, **kwargs):
        if "/v1/oauth2/token" in url:
            return FakeResp(200, {"access_token": "tok"})
        return FakeResp(400, {"message": "invalid request"})

    monkeypatch.setattr(httpx, "post", fake_post)
    r = client.post("/billing/checkout", json={"plan_code": "pro", "period": "monthly", "provider": "paypal"},
                    headers=h)
    assert r.status_code == 502


def test_checkout_paypal_bad_credentials(client, monkeypatch):
    h = _register(client, "ppauth@example.com")
    _enable_paypal(monkeypatch)
    monkeypatch.setattr(httpx, "post", lambda url, **k: FakeResp(401, {}))
    r = client.post("/billing/checkout", json={"plan_code": "pro", "period": "monthly", "provider": "paypal"},
                    headers=h)
    assert r.status_code == 502
