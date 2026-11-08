def _register(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "S3curePass!23",
                                            "full_name": "Voice Owner", "organization_name": "VoiceOrg"})
    return r.json()

def test_voice_agent_flow(client):
    tokens = _register(client, "voice1@example.com")
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    # no token -> unauthorized
    assert client.get("/voice/agents").status_code in (401, 403)
    # create agent
    r = client.post("/voice/agents", json={"name": "Sales Caller", "language": "te",
                                           "script": "Hi, this is NEXORA AI."}, headers=h)
    assert r.status_code == 201, r.text
    agent_id = r.json()["id"]
    agents = client.get("/voice/agents", headers=h).json()
    assert any(a["id"] == agent_id for a in agents)
    # bad phone rejected
    bad = client.post(f"/voice/agents/{agent_id}/calls", json={"to_phone": "9876543210"}, headers=h)
    assert bad.status_code == 400
    # queue a call
    q = client.post(f"/voice/agents/{agent_id}/calls", json={"to_phone": "+919876543210"}, headers=h)
    assert q.status_code == 201 and q.json()["status"] == "queued"
    call_id = q.json()["id"]
    # dial attempt with no provider configured: honest not_configured, never claims dialed
    d = client.post(f"/voice/calls/{call_id}/dial", headers=h)
    assert d.status_code == 200
    body = d.json()
    assert body["status"] == "not_configured"
    assert "NOT dialed" in body["note"]
    calls = client.get("/voice/calls", headers=h).json()
    assert any(c["id"] == call_id and c["status"] == "not_configured" for c in calls)
    # other user's org cannot see this agent
    t2 = _register(client, "voice2@example.com")
    h2 = {"Authorization": f"Bearer {t2['access_token']}"}
    assert client.post(f"/voice/agents/{agent_id}/calls",
                       json={"to_phone": "+919876543210"}, headers=h2).status_code == 404
