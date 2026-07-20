from __future__ import annotations


def test_conversation_command(client):
    resp = client.post("/assistant/command", json={"text": "Hello there", "session_id": "s1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "s1"
    assert body["text"]
    assert body["plan"]["steps"][0]["capability"] == "conversation"


def test_home_automation_routing(client):
    resp = client.post(
        "/assistant/command",
        json={"text": "Turn on the living room lights", "session_id": "s2"},
    )
    assert resp.status_code == 200
    step = resp.json()["plan"]["steps"][0]
    assert step["capability"] == "home_automation"
    assert step["status"] == "done"


def test_multi_step_plan(client):
    resp = client.post(
        "/assistant/command",
        json={
            "text": "Turn off the kitchen light and bring me my water bottle",
            "session_id": "s3",
        },
    )
    assert resp.status_code == 200
    steps = resp.json()["plan"]["steps"]
    caps = {s["capability"] for s in steps}
    assert "home_automation" in caps
    assert "robot" in caps


def test_history_endpoint(client):
    client.post("/assistant/command", json={"text": "Hi", "session_id": "hist"})
    resp = client.get("/assistant/history/hist")
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert messages[0]["role"] == "user"
    assert messages[-1]["role"] == "assistant"
