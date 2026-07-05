"""Smoke tests: app serves, and non-ASCII content survives every hop.

The unicode tests are regressions for the Windows cp1252 crash where
unencoded read_text()/write_text() used the locale codec (task 0.1,
originally a 500 from index() reading dashboard/index.html).
"""


def test_index_serves(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Agentic OS" in r.text


def test_index_survives_non_ascii(client, server):
    html = server.BASE_DIR / "dashboard" / "index.html"
    original = html.read_text(encoding="utf-8")
    try:
        html.write_text(original + "\n<!-- déjà‑vu ✓ 🚀 -->\n", encoding="utf-8")
        r = client.get("/")
        assert r.status_code == 200
        assert "déjà‑vu ✓ 🚀" in r.text
    finally:
        html.write_text(original, encoding="utf-8")


def test_settings_endpoint(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_status_endpoint(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert "agents" in body


def test_brain_roundtrip_with_unicode(client):
    payload = "# Notes\n\nCafé ↔ 東京 — emoji: 🧠✨\n"
    r = client.put("/api/brain/memory.md", json={"content": payload})
    assert r.status_code == 200
    r = client.get("/api/brain/memory.md")
    assert r.status_code == 200
    assert "Café ↔ 東京 — emoji: 🧠✨" in r.json()["content"]


def test_isolation_no_real_state_touched(server, app_home):
    # The app must be rooted in the temp home, not the repo checkout
    assert str(server.BASE_DIR).startswith(str(app_home))
