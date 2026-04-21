import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest_asyncio.fixture
async def client(set_test_db):
    import db.database as dbmod
    await dbmod.init_db()
    from web.app import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_legal_returns_200(client):
    resp = await client.get("/legal")
    assert resp.status_code == 200
    assert "LEGAL" in resp.text


async def test_consent_page_invalid_token_returns_404(client):
    resp = await client.get("/scan/bad-token-xyz")
    assert resp.status_code == 404


async def test_consent_page_valid_token_returns_200(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-consent", 1, None, "Test", None, "ru", None)
    resp = await client.get("/scan/tok-consent")
    assert resp.status_code == 200
    assert "tok-consent" in resp.text


async def test_consent_page_already_consented_redirects(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-done", 1, None, "Test", None, "ru", None)
    await dbmod.update_consent("tok-done", "1.2.3.4", "UA", {}, {})
    resp = await client.get("/scan/tok-done", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "dashboard" in resp.headers["location"]


async def test_post_consent_sets_consent_and_redirects(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-post", 1, None, "Test", None, "ru", None)
    resp = await client.post("/scan/tok-post/consent", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].endswith("/dashboard")
    session = await dbmod.get_session("tok-post")
    assert session["consent_given"] == 1


async def test_dashboard_without_consent_redirects(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-nodash", 1, None, "Test", None, "ru", None)
    resp = await client.get("/scan/tok-nodash/dashboard", follow_redirects=False)
    assert resp.status_code in (302, 307)


async def test_dashboard_with_consent_returns_200(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-dash", 1, None, "Test", None, "ru", None)
    await dbmod.update_consent("tok-dash", "1.2.3.4", "Mozilla/5.0", {}, {})
    resp = await client.get("/scan/tok-dash/dashboard")
    assert resp.status_code == 200
    assert resp.text  # dashboard rendered successfully


async def test_client_data_endpoint_stores_data(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-client", 1, None, "Test", None, "ru", None)
    await dbmod.update_consent("tok-client", "1.2.3.4", "Mozilla", {}, {})
    resp = await client.post(
        "/scan/tok-client/client",
        json={
            "screen": {"width": 1920, "height": 1080},
            "webrtc_ips": ["10.0.0.1"],
            "fingerprint_hash": "deadbeef",
            "fingerprint_score": 0.75,
        },
    )
    assert resp.status_code == 200
    session = await dbmod.get_session("tok-client")
    assert session["fingerprint_hash"] == "deadbeef"


async def test_client_data_without_consent_returns_403(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-nocon", 1, None, "Test", None, "ru", None)
    resp = await client.post("/scan/tok-nocon/client", json={})
    assert resp.status_code == 403
