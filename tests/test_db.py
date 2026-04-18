import pytest
from db.database import (
    init_db, create_session, get_session,
    update_consent, update_client_data,
    get_user_sessions, count_user_sessions,
)

@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()

async def test_create_and_get_session():
    await create_session("tok1", 100, "alice", "Alice", "Smith", "en", None)
    session = await get_session("tok1")
    assert session is not None
    assert session["tg_id"] == 100
    assert session["tg_first_name"] == "Alice"
    assert session["consent_given"] == 0

async def test_get_session_nonexistent_returns_none():
    assert await get_session("no-such-token") is None

async def test_update_consent():
    await create_session("tok2", 101, None, "Bob", None, "ru", None)
    geo = {"country": "Russia", "city": "Moscow", "isp": "MTS", "proxy": False}
    await update_consent("tok2", "1.2.3.4", "Mozilla/5.0", {"accept": "*/*"}, geo)
    session = await get_session("tok2")
    assert session["consent_given"] == 1
    assert session["ip"] == "1.2.3.4"
    assert session["geo_country"] == "Russia"
    assert session["geo_proxy"] == 0

async def test_update_client_data():
    await create_session("tok3", 102, None, "Carol", None, "en", None)
    await update_client_data("tok3", {"width": 1920}, ["10.0.0.1"], "abc123", 0.87)
    session = await get_session("tok3")
    assert session["fingerprint_hash"] == "abc123"
    assert session["fingerprint_score"] == 0.87

async def test_count_and_paginate_sessions():
    for i in range(7):
        await create_session(f"multi{i}", 200, None, "Dave", None, "en", None)
    assert await count_user_sessions(200) == 7
    assert len(await get_user_sessions(200, limit=5, offset=0)) == 5
    assert len(await get_user_sessions(200, limit=5, offset=5)) == 2

async def test_create_session_duplicate_token_raises():
    await create_session("dup", 300, None, "Eve", None, "en", None)
    with pytest.raises(ValueError, match="already exists"):
        await create_session("dup", 300, None, "Eve", None, "en", None)

async def test_update_consent_unknown_token_raises():
    with pytest.raises(ValueError, match="No session found for token"):
        await update_consent("ghost", "1.2.3.4", "ua", {}, {})

async def test_update_client_data_unknown_token_raises():
    with pytest.raises(ValueError, match="No session found for token"):
        await update_client_data("ghost", {}, [], "h", 0.0)
