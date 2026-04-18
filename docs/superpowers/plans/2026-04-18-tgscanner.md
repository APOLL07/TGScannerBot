# TGScanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that generates a personalized HTTPS scan link; when opened, the link shows the user their own Telegram profile data, IP geolocation, browser fingerprint, and WebRTC leaks on a cyberpunk-styled dashboard.

**Architecture:** aiogram 3 bot and FastAPI web server run concurrently in one process via asyncio. SQLite (aiosqlite) stores sessions and scan results. The bot creates a UUID token per `/scan` call; the web server captures IP/headers at consent POST; client-side JS collects screen/WebRTC/fingerprint data and POSTs back to the server. Deployed on Railway with auto-HTTPS.

**Tech Stack:** Python 3.11, aiogram 3.13, FastAPI 0.115, uvicorn, aiosqlite, Jinja2, httpx, ua-parser, pytest, pytest-asyncio.

---

## File Map

| File | Responsibility |
|------|---------------|
| `main.py` | Entry point — launches bot + web server via asyncio.gather |
| `db/database.py` | All SQLite operations: init, create_session, get_session, update_consent, update_client_data, get_user_sessions, count_user_sessions |
| `services/token.py` | UUID token generation |
| `services/geo.py` | IP geolocation via ip-api.com |
| `services/fingerprint.py` | User-Agent string parsing via ua-parser |
| `web/app.py` | FastAPI app factory: /legal, /scan/{token}, /scan/{token}/consent, /scan/{token}/dashboard, /scan/{token}/client |
| `bot/handlers.py` | aiogram router: /start, /help, /scan, /history + history callback |
| `bot/keyboards.py` | Inline keyboards: scan button, history pagination |
| `web/templates/consent.html` | Consent screen with boot animation and ToS link |
| `web/templates/dashboard.html` | 4-tab dashboard: ПРОФИЛЬ, СЕТЬ, УСТРОЙСТВО, ЗАГОЛОВКИ |
| `web/templates/legal.html` | Terms of Service / Disclaimer page |
| `web/static/style.css` | Cyberpunk/neon theme (JetBrains Mono, #0a0a0f bg, #00ff88 + #ff0066 accents) |
| `web/static/scanner.js` | Client-side: screen data, WebRTC leak detection, canvas/audio fingerprint, POST to /client |
| `tests/conftest.py` | Pytest fixtures: temp SQLite DB, patched DB_PATH |
| `tests/test_services.py` | Unit tests for token, fingerprint, geo |
| `tests/test_routes.py` | FastAPI route tests via httpx AsyncClient |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `db/__init__.py`, `bot/__init__.py`, `services/__init__.py`, `tests/__init__.py`
- Create: `web/templates/` and `web/static/` directories

- [ ] **Step 1: Create requirements.txt**

```
aiogram==3.13.1
fastapi==0.115.6
uvicorn[standard]==0.32.1
aiosqlite==0.20.0
jinja2==3.1.4
httpx==0.27.2
python-dotenv==1.0.1
ua-parser==0.18.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create .env.example**

```
BOT_TOKEN=your_telegram_bot_token_here
BASE_URL=https://yourapp.up.railway.app
PORT=8000
```

- [ ] **Step 3: Create .gitignore**

```
.env
__pycache__/
*.pyc
*.db
.pytest_cache/
*.egg-info/
dist/
.venv/
```

- [ ] **Step 4: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 5: Create package init files and directory structure**

```bash
mkdir -p db bot services web/templates web/static tests
touch db/__init__.py bot/__init__.py services/__init__.py tests/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore pytest.ini db/__init__.py bot/__init__.py services/__init__.py tests/__init__.py
git commit -m "chore: project scaffold"
```

---

## Task 2: Database Layer

**Files:**
- Create: `db/database.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests for database operations**

Create `tests/conftest.py`:
```python
import os
import pytest
import pytest_asyncio

@pytest.fixture(autouse=True)
def set_test_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import db.database as dbmod
    monkeypatch.setattr(dbmod, "DB_PATH", db_path)
    return db_path
```

Create `tests/test_db.py`:
```python
import pytest
from db.database import init_db, create_session, get_session, update_consent, update_client_data, get_user_sessions, count_user_sessions

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
    result = await get_session("no-such-token")
    assert result is None

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
    await update_client_data("tok3", {"width": 1920, "height": 1080}, ["10.0.0.1"], "abc123", 0.87)
    session = await get_session("tok3")
    assert session["fingerprint_hash"] == "abc123"
    assert session["fingerprint_score"] == 0.87

async def test_count_and_get_user_sessions():
    for i in range(7):
        await create_session(f"multi{i}", 200, None, "Dave", None, "en", None)
    count = await count_user_sessions(200)
    assert count == 7
    page1 = await get_user_sessions(200, limit=5, offset=0)
    assert len(page1) == 5
    page2 = await get_user_sessions(200, limit=5, offset=5)
    assert len(page2) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```
Expected: `ModuleNotFoundError: No module named 'db.database'`

- [ ] **Step 3: Implement db/database.py**

```python
import aiosqlite
import json
import os
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "sessions.db")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                tg_id INTEGER NOT NULL,
                tg_username TEXT,
                tg_first_name TEXT NOT NULL,
                tg_last_name TEXT,
                tg_lang TEXT,
                tg_photo_url TEXT,
                ip TEXT,
                user_agent TEXT,
                headers TEXT,
                geo_country TEXT,
                geo_city TEXT,
                geo_isp TEXT,
                geo_proxy INTEGER DEFAULT 0,
                screen_data TEXT,
                webrtc_ips TEXT,
                fingerprint_hash TEXT,
                fingerprint_score REAL,
                consent_given INTEGER DEFAULT 0,
                consent_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()


async def create_session(
    token: str,
    tg_id: int,
    tg_username: Optional[str],
    tg_first_name: str,
    tg_last_name: Optional[str],
    tg_lang: Optional[str],
    tg_photo_url: Optional[str],
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO sessions
               (token, tg_id, tg_username, tg_first_name, tg_last_name, tg_lang, tg_photo_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (token, tg_id, tg_username, tg_first_name, tg_last_name, tg_lang, tg_photo_url),
        )
        await db.commit()


async def get_session(token: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE token = ?", (token,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_consent(
    token: str,
    ip: str,
    user_agent: str,
    headers: dict,
    geo: dict,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE sessions SET
               ip = ?, user_agent = ?, headers = ?,
               geo_country = ?, geo_city = ?, geo_isp = ?, geo_proxy = ?,
               consent_given = 1, consent_at = datetime('now')
               WHERE token = ?""",
            (
                ip,
                user_agent,
                json.dumps(headers),
                geo.get("country"),
                geo.get("city"),
                geo.get("isp"),
                1 if geo.get("proxy") else 0,
                token,
            ),
        )
        await db.commit()


async def update_client_data(
    token: str,
    screen_data: dict,
    webrtc_ips: list,
    fingerprint_hash: str,
    fingerprint_score: float,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE sessions SET
               screen_data = ?, webrtc_ips = ?,
               fingerprint_hash = ?, fingerprint_score = ?
               WHERE token = ?""",
            (
                json.dumps(screen_data),
                json.dumps(webrtc_ips),
                fingerprint_hash,
                fingerprint_score,
                token,
            ),
        )
        await db.commit()


async def get_user_sessions(tg_id: int, limit: int = 5, offset: int = 0) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions WHERE tg_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (tg_id, limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def count_user_sessions(tg_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM sessions WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add db/database.py tests/conftest.py tests/test_db.py
git commit -m "feat: database layer with session CRUD"
```

---

## Task 3: Services (token, geo, fingerprint)

**Files:**
- Create: `services/token.py`
- Create: `services/geo.py`
- Create: `services/fingerprint.py`
- Create: `tests/test_services.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_services.py`:
```python
import re
import pytest
from unittest.mock import AsyncMock, patch
from services.token import generate_token
from services.fingerprint import parse_user_agent
from services.geo import get_ip_info

def test_generate_token_is_uuid4_format():
    token = generate_token()
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        token,
    )

def test_generate_token_is_unique():
    assert generate_token() != generate_token()

def test_parse_chrome_windows():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    result = parse_user_agent(ua)
    assert result["browser"] == "Chrome"
    assert result["browser_version"] == "124"
    assert result["os"] == "Windows"
    assert result["device_type"] == "Desktop"

def test_parse_mobile_ua():
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    result = parse_user_agent(ua)
    assert result["device_type"] == "Mobile"
    assert result["os"] == "iOS"

def test_parse_empty_ua_returns_empty_dict():
    assert parse_user_agent("") == {}

async def test_get_ip_info_localhost_returns_empty():
    result = await get_ip_info("127.0.0.1")
    assert result == {}

async def test_get_ip_info_success():
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "status": "success",
        "country": "Russia",
        "regionName": "Moscow",
        "city": "Moscow",
        "isp": "MTS",
        "org": "MTS PJSC",
        "as": "AS8359 MTS",
        "proxy": False,
        "hosting": False,
    }
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await get_ip_info("1.2.3.4")
    assert result["country"] == "Russia"
    assert result["city"] == "Moscow"
    assert result["proxy"] is False

async def test_get_ip_info_api_failure_returns_empty():
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("timeout"))
        result = await get_ip_info("1.2.3.4")
    assert result == {}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_services.py -v
```
Expected: `ModuleNotFoundError: No module named 'services.token'`

- [ ] **Step 3: Create services/token.py**

```python
import uuid


def generate_token() -> str:
    return str(uuid.uuid4())
```

- [ ] **Step 4: Create services/fingerprint.py**

```python
from ua_parser import user_agent_parser
from typing import Optional


def parse_user_agent(ua_string: str) -> dict:
    if not ua_string:
        return {}
    parsed = user_agent_parser.Parse(ua_string)
    browser = parsed["user_agent"]
    os_info = parsed["os"]
    device = parsed["device"]

    device_family = device.get("family") or "Other"
    is_mobile = device_family not in ("Other", "")

    return {
        "browser": browser.get("family") or "Unknown",
        "browser_version": browser.get("major") or "",
        "os": os_info.get("family") or "Unknown",
        "os_version": os_info.get("major") or "",
        "device_type": "Mobile" if is_mobile else "Desktop",
        "device_brand": device.get("brand") or "",
        "device_model": device.get("model") or "",
    }
```

- [ ] **Step 5: Create services/geo.py**

```python
import httpx
from typing import Optional


async def get_ip_info(ip: str) -> dict:
    if ip in ("127.0.0.1", "::1", "localhost"):
        return {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,regionName,city,isp,org,as,proxy,hosting"},
            )
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country", ""),
                    "region": data.get("regionName", ""),
                    "city": data.get("city", ""),
                    "isp": data.get("isp", ""),
                    "org": data.get("org", ""),
                    "asn": data.get("as", ""),
                    "proxy": data.get("proxy", False),
                    "hosting": data.get("hosting", False),
                }
    except Exception:
        pass
    return {}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_services.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 7: Commit**

```bash
git add services/token.py services/fingerprint.py services/geo.py tests/test_services.py
git commit -m "feat: token, geo, and fingerprint services"
```

---

## Task 4: FastAPI Routes

**Files:**
- Create: `web/app.py`
- Create: `tests/test_routes.py`
- Create: `web/templates/consent.html` (stub — "CONSENT" in body, replaced in Task 7)
- Create: `web/templates/dashboard.html` (stub — "DASHBOARD" in body, replaced in Task 8)
- Create: `web/templates/legal.html` (stub — "LEGAL" in body, replaced in Task 9)

- [ ] **Step 1: Create stub templates so routes can render**

Create `web/templates/consent.html`:
```html
<!DOCTYPE html><html><body>CONSENT {{ token }}</body></html>
```

Create `web/templates/dashboard.html`:
```html
<!DOCTYPE html><html><body>DASHBOARD {{ session.tg_id }}</body></html>
```

Create `web/templates/legal.html`:
```html
<!DOCTYPE html><html><body>LEGAL</body></html>
```

Create empty `web/static/style.css` and `web/static/scanner.js`:
```bash
touch web/static/style.css web/static/scanner.js
```

- [ ] **Step 2: Write failing route tests**

Create `tests/test_routes.py`:
```python
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
    assert resp.status_code == 307
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
    assert "DASHBOARD" in resp.text


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
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_routes.py -v
```
Expected: `ModuleNotFoundError: No module named 'web.app'`

- [ ] **Step 4: Create web/app.py**

```python
import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db.database import get_session, update_consent, update_client_data
from services.geo import get_ip_info
from services.fingerprint import parse_user_agent

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    app.mount(
        "/static",
        StaticFiles(directory=str(BASE_DIR / "static")),
        name="static",
    )

    @app.get("/legal", response_class=HTMLResponse)
    async def legal(request: Request):
        return templates.TemplateResponse("legal.html", {"request": request})

    @app.get("/scan/{token}", response_class=HTMLResponse)
    async def consent_page(request: Request, token: str):
        session = await get_session(token)
        if not session:
            return HTMLResponse("<h1>404 — Ссылка недействительна</h1>", status_code=404)
        if session["consent_given"]:
            return RedirectResponse(f"/scan/{token}/dashboard")
        return templates.TemplateResponse("consent.html", {"request": request, "token": token})

    @app.post("/scan/{token}/consent")
    async def accept_consent(request: Request, token: str):
        session = await get_session(token)
        if not session:
            return HTMLResponse("Not found", status_code=404)
        ip = get_real_ip(request)
        ua = request.headers.get("User-Agent", "")
        headers = dict(request.headers)
        geo = await get_ip_info(ip)
        await update_consent(token, ip, ua, headers, geo)
        return RedirectResponse(f"/scan/{token}/dashboard", status_code=303)

    @app.get("/scan/{token}/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request, token: str):
        session = await get_session(token)
        if not session:
            return HTMLResponse("Not found", status_code=404)
        if not session["consent_given"]:
            return RedirectResponse(f"/scan/{token}")

        ua_info = parse_user_agent(session.get("user_agent") or "")

        headers_raw = {}
        if session.get("headers"):
            try:
                headers_raw = json.loads(session["headers"])
            except Exception:
                pass

        screen = {}
        if session.get("screen_data"):
            try:
                screen = json.loads(session["screen_data"])
            except Exception:
                pass

        webrtc = []
        if session.get("webrtc_ips"):
            try:
                webrtc = json.loads(session["webrtc_ips"])
            except Exception:
                pass

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "token": token,
                "session": session,
                "ua_info": ua_info,
                "headers_raw": headers_raw,
                "screen": screen,
                "webrtc": webrtc,
            },
        )

    @app.post("/scan/{token}/client")
    async def receive_client_data(request: Request, token: str):
        session = await get_session(token)
        if not session or not session["consent_given"]:
            return JSONResponse({"error": "forbidden"}, status_code=403)
        body = await request.json()
        await update_client_data(
            token=token,
            screen_data=body.get("screen", {}),
            webrtc_ips=body.get("webrtc_ips", []),
            fingerprint_hash=body.get("fingerprint_hash", ""),
            fingerprint_score=float(body.get("fingerprint_score", 0)),
        )
        return JSONResponse({"ok": True})

    return app
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_routes.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/templates/ web/static/ tests/test_routes.py
git commit -m "feat: FastAPI routes with consent and dashboard"
```

---

## Task 5: Bot Handlers and Keyboards

**Files:**
- Create: `bot/keyboards.py`
- Create: `bot/handlers.py`

- [ ] **Step 1: Create bot/keyboards.py**

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def scan_button(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔍 ОТКРЫТЬ СКАНЕР", url=url)
    ]])


def history_nav(tg_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if page > 0:
        buttons.append(
            InlineKeyboardButton(text="← Назад", callback_data=f"history:{tg_id}:{page - 1}")
        )
    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(text="Вперёд →", callback_data=f"history:{tg_id}:{page + 1}")
        )
    if not buttons:
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(inline_keyboard=[buttons])
```

- [ ] **Step 2: Create bot/handlers.py**

```python
import math
import os
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import history_nav, scan_button
from db.database import (
    count_user_sessions,
    create_session,
    get_user_sessions,
)
from services.fingerprint import parse_user_agent
from services.token import generate_token

router = Router()

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
PAGE_SIZE = 5


async def _get_photo_url(bot: Bot, user_id: int) -> Optional[str]:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count == 0:
            return None
        file_id = photos.photos[0][-1].file_id
        file = await bot.get_file(file_id)
        return f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    except Exception:
        return None


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👁 <b>TGScanner</b>\n\n"
        "Бот генерирует персональную ссылку для сканирования.\n"
        "Открой её в браузере и узнай, что о тебе видно в сети:\n\n"
        "• Telegram профиль и ID\n"
        "• IP-адрес и геолокация\n"
        "• Браузер, ОС, устройство\n"
        "• WebRTC утечки\n"
        "• Отпечаток браузера\n\n"
        "Используй /scan чтобы начать.",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Команды:</b>\n\n"
        "/scan — создать ссылку для сканирования\n"
        "/history — история твоих сканов\n"
        "/help — эта справка",
        parse_mode="HTML",
    )


@router.message(Command("scan"))
async def cmd_scan(message: Message, bot: Bot) -> None:
    token = generate_token()
    photo_url = await _get_photo_url(bot, message.from_user.id)

    await create_session(
        token=token,
        tg_id=message.from_user.id,
        tg_username=message.from_user.username,
        tg_first_name=message.from_user.first_name,
        tg_last_name=message.from_user.last_name,
        tg_lang=message.from_user.language_code,
        tg_photo_url=photo_url,
    )

    url = f"{BASE_URL}/scan/{token}"
    await message.answer(
        "🔍 <b>Ссылка для сканирования готова.</b>\n\n"
        "Открой её в браузере — увидишь всё, что о тебе известно.",
        parse_mode="HTML",
        reply_markup=scan_button(url),
    )


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    await _send_history_page(message, message.from_user.id, page=0)


@router.callback_query(F.data.startswith("history:"))
async def history_callback(callback: CallbackQuery) -> None:
    _, tg_id_str, page_str = callback.data.split(":")
    await callback.answer()
    await _send_history_page(callback.message, int(tg_id_str), int(page_str))


async def _send_history_page(message: Message, tg_id: int, page: int) -> None:
    total = await count_user_sessions(tg_id)
    if total == 0:
        await message.answer("📭 История сканов пуста. Используй /scan чтобы начать.")
        return

    total_pages = math.ceil(total / PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    sessions = await get_user_sessions(tg_id, limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    header = f"📋 <b>История сканов</b> (стр. {page + 1}/{total_pages})\n\n"
    cards = "\n\n".join(
        _format_card(s, page * PAGE_SIZE + i + 1) for i, s in enumerate(sessions)
    )

    await message.answer(
        header + cards,
        parse_mode="HTML",
        reply_markup=history_nav(tg_id, page, total_pages),
    )


def _format_card(session: dict, index: int) -> str:
    created = session.get("created_at", "")
    try:
        dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %H:%M")
    except Exception:
        dt = created or "—"

    ip = session.get("ip") or "—"
    location_parts = [session.get("geo_city"), session.get("geo_country")]
    location = ", ".join(p for p in location_parts if p) or "—"
    isp = (session.get("geo_isp") or "—")[:22]

    ua_info = parse_user_agent(session.get("user_agent") or "")
    browser = f"{ua_info.get('browser', '?')} {ua_info.get('browser_version', '')}".strip()
    os_str = f"{ua_info.get('os', '?')} {ua_info.get('os_version', '')}".strip()

    return (
        "<pre>"
        f"╔══ СКАН #{index} ══════════════════╗\n"
        f"📅 {dt}\n"
        f"🌐 IP: {ip}\n"
        f"📍 {location} • {isp}\n"
        f"💻 {browser} • {os_str}\n"
        "╚══════════════════════════════╝"
        "</pre>"
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp
```

- [ ] **Step 3: Run existing tests to confirm nothing broken**

```bash
pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add bot/keyboards.py bot/handlers.py
git commit -m "feat: bot handlers — /start /help /scan /history"
```

---

## Task 6: CSS — Cyberpunk Theme

**Files:**
- Modify: `web/static/style.css`

- [ ] **Step 1: Write web/static/style.css**

```css
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0a0a0f;
  --bg2: #0f0f1a;
  --bg3: #141428;
  --green: #00ff88;
  --pink: #ff0066;
  --blue: #00ccff;
  --text: #c8d3e0;
  --muted: #556070;
  --border: #1e2a3a;
}

html, body {
  background: var(--bg);
  color: var(--text);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 14px;
  min-height: 100vh;
  overflow-x: hidden;
}

/* Scanline overlay */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,255,136,0.015) 2px,
    rgba(0,255,136,0.015) 4px
  );
  pointer-events: none;
  z-index: 9999;
}

/* ── Glitch effect ── */
.glitch {
  position: relative;
  color: var(--green);
  text-shadow: 0 0 10px rgba(0,255,136,0.6);
}
.glitch::before,
.glitch::after {
  content: attr(data-text);
  position: absolute;
  inset: 0;
}
.glitch::before {
  color: var(--pink);
  animation: glitch-1 3s infinite;
  clip-path: polygon(0 0, 100% 0, 100% 35%, 0 35%);
}
.glitch::after {
  color: var(--blue);
  animation: glitch-2 3s infinite;
  clip-path: polygon(0 65%, 100% 65%, 100% 100%, 0 100%);
}
@keyframes glitch-1 {
  0%, 90%, 100% { transform: none; opacity: 0; }
  92% { transform: translateX(-3px); opacity: 0.8; }
  94% { transform: translateX(3px); opacity: 0.8; }
  96% { transform: none; opacity: 0; }
}
@keyframes glitch-2 {
  0%, 88%, 100% { transform: none; opacity: 0; }
  90% { transform: translateX(3px); opacity: 0.8; }
  92% { transform: translateX(-3px); opacity: 0.8; }
  94% { transform: none; opacity: 0; }
}

/* ── Typewriter ── */
.typewriter { overflow: hidden; white-space: nowrap; border-right: 2px solid var(--green); animation: typing 2s steps(40) forwards, blink 0.75s step-end infinite; }
@keyframes typing { from { width: 0 } to { width: 100% } }
@keyframes blink { 50% { border-color: transparent } }

/* ── Consent Screen ── */
.consent-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}
.consent-box {
  width: 100%;
  max-width: 560px;
  border: 1px solid var(--green);
  padding: 40px;
  background: var(--bg2);
  box-shadow: 0 0 40px rgba(0,255,136,0.08), inset 0 0 40px rgba(0,0,0,0.4);
}
.consent-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 28px;
}
.boot-lines { margin-bottom: 28px; }
.boot-line {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 4px;
  opacity: 0;
  animation: fade-in 0.3s forwards;
}
.boot-line.ok::after { content: ' [OK]'; color: var(--green); }
.boot-line:nth-child(1) { animation-delay: 0.2s; }
.boot-line:nth-child(2) { animation-delay: 0.5s; }
.boot-line:nth-child(3) { animation-delay: 0.8s; }
.boot-line:nth-child(4) { animation-delay: 1.1s; }
.boot-line:nth-child(5) { animation-delay: 1.4s; }
@keyframes fade-in { to { opacity: 1 } }

.data-list { margin-bottom: 28px; padding-left: 0; list-style: none; }
.data-list li { padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.data-list li::before { content: '> '; color: var(--green); }

.consent-tos {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 20px;
  line-height: 1.6;
}
.consent-tos a { color: var(--green); text-decoration: none; border-bottom: 1px solid rgba(0,255,136,0.3); }
.consent-tos a:hover { color: #fff; border-color: #fff; }

.btn-accept {
  display: block;
  width: 100%;
  padding: 14px;
  background: transparent;
  border: 2px solid var(--green);
  color: var(--green);
  font-family: inherit;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-accept:hover {
  background: var(--green);
  color: var(--bg);
  box-shadow: 0 0 30px rgba(0,255,136,0.4);
}

/* ── Dashboard ── */
.dashboard { max-width: 860px; margin: 0 auto; padding: 32px 24px; }

.dash-header { margin-bottom: 32px; }
.dash-title { font-size: 20px; font-weight: 700; letter-spacing: 4px; text-transform: uppercase; }
.dash-subtitle { color: var(--muted); font-size: 12px; margin-top: 6px; }

/* Tabs */
.tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 28px; overflow-x: auto; }
.tab-btn {
  padding: 12px 24px;
  background: none;
  border: none;
  color: var(--muted);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 2px;
  text-transform: uppercase;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active {
  color: var(--green);
  border-bottom-color: var(--green);
  text-shadow: 0 0 8px rgba(0,255,136,0.5);
}

.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* Cards */
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  padding: 20px 24px;
  margin-bottom: 16px;
}
.card-label {
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}
.card-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--green);
  word-break: break-all;
}
.card-value.pink { color: var(--pink); }
.card-value.blue { color: var(--blue); }
.card-value.small { font-size: 14px; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 600px) { .grid-2 { grid-template-columns: 1fr; } }

/* Profile */
.profile-header { display: flex; align-items: center; gap: 20px; margin-bottom: 24px; }
.avatar {
  width: 72px; height: 72px;
  border-radius: 50%;
  border: 2px solid var(--green);
  box-shadow: 0 0 20px rgba(0,255,136,0.3);
  object-fit: cover;
}
.avatar-placeholder {
  width: 72px; height: 72px;
  border-radius: 50%;
  border: 2px solid var(--green);
  background: var(--bg3);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
  box-shadow: 0 0 20px rgba(0,255,136,0.2);
}
.profile-name { font-size: 20px; font-weight: 700; }
.badge {
  display: inline-block;
  padding: 3px 10px;
  border: 1px solid var(--green);
  color: var(--green);
  font-size: 10px;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-top: 6px;
}

/* Headers table */
.headers-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.headers-table th { text-align: left; color: var(--muted); padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 11px; letter-spacing: 1px; text-transform: uppercase; }
.headers-table td { padding: 8px 12px; border-bottom: 1px solid var(--border); word-break: break-all; }
.headers-table tr:hover td { background: var(--bg3); }
.header-key { color: var(--green); width: 35%; }

/* Status indicators */
.status-ok { color: var(--green); }
.status-warn { color: var(--pink); }
.status-info { color: var(--blue); }

/* Collecting animation */
.collecting { color: var(--muted); font-size: 12px; }
.collecting::after { content: '...'; animation: dots 1.5s infinite; }
@keyframes dots { 0%,100%{content:'.'} 33%{content:'..'} 66%{content:'...'} }

/* Legal page */
.legal-page { max-width: 720px; margin: 0 auto; padding: 48px 24px; }
.legal-page h1 { color: var(--green); font-size: 20px; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 8px; }
.legal-page .updated { color: var(--muted); font-size: 12px; margin-bottom: 36px; }
.legal-page h2 { color: var(--text); font-size: 14px; letter-spacing: 2px; text-transform: uppercase; margin: 28px 0 12px; border-left: 3px solid var(--green); padding-left: 12px; }
.legal-page p { color: var(--muted); line-height: 1.8; margin-bottom: 12px; font-size: 13px; }
.legal-page a { color: var(--green); }
.back-link { display: inline-block; margin-bottom: 32px; color: var(--muted); text-decoration: none; font-size: 12px; }
.back-link:hover { color: var(--green); }
```

- [ ] **Step 2: Commit**

```bash
git add web/static/style.css
git commit -m "feat: cyberpunk CSS theme"
```

---

## Task 7: Consent Screen Template

**Files:**
- Modify: `web/templates/consent.html`

- [ ] **Step 1: Replace stub with full consent.html**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TGScanner — Авторизация</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="consent-screen">
  <div class="consent-box">
    <div class="consent-title glitch" data-text="// TGSCANNER //">// TGSCANNER //</div>

    <div class="boot-lines">
      <div class="boot-line ok">Инициализация сканирования</div>
      <div class="boot-line ok">Модуль сбора данных загружен</div>
      <div class="boot-line ok">Соединение с Telegram API</div>
      <div class="boot-line ok">Анализ сетевых параметров</div>
      <div class="boot-line">Ожидание подтверждения пользователя</div>
    </div>

    <p style="font-size:12px;color:var(--muted);margin-bottom:12px;letter-spacing:1px;text-transform:uppercase;">Будут собраны следующие данные:</p>
    <ul class="data-list">
      <li>Telegram ID, имя, @username, аватар</li>
      <li>IP-адрес и геолокация</li>
      <li>Браузер, операционная система, устройство</li>
      <li>HTTP-заголовки запроса</li>
      <li>Разрешение экрана и временная зона</li>
      <li>Отпечаток браузера (Canvas + Audio API)</li>
      <li>WebRTC утечки IP-адресов</li>
    </ul>

    <p class="consent-tos">
      Нажимая кнопку ниже, вы подтверждаете, что ознакомились и соглашаетесь
      с <a href="/legal" target="_blank">Условиями использования</a>.
      Данные видны только вам и не передаются третьим лицам.
    </p>

    <form method="POST" action="/scan/{{ token }}/consent">
      <button type="submit" class="btn-accept">[ ПРИНЯТЬ И ПРОДОЛЖИТЬ ]</button>
    </form>
  </div>
</div>
</body>
</html>
```

- [ ] **Step 2: Run route tests to confirm consent page still works**

```bash
pytest tests/test_routes.py::test_consent_page_valid_token_returns_200 -v
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/templates/consent.html
git commit -m "feat: consent screen template"
```

---

## Task 8: Dashboard Template

**Files:**
- Modify: `web/templates/dashboard.html`

- [ ] **Step 1: Replace stub with full dashboard.html**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TGScanner — Результаты</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="dashboard">

  <div class="dash-header">
    <div class="dash-title glitch" data-text="// SCAN COMPLETE //">// SCAN COMPLETE //</div>
    <div class="dash-subtitle">Токен: {{ token[:8] }}... &nbsp;|&nbsp; {{ session.created_at }}</div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('profile')">[ ПРОФИЛЬ ]</button>
    <button class="tab-btn" onclick="switchTab('network')">[ СЕТЬ ]</button>
    <button class="tab-btn" onclick="switchTab('device')">[ УСТРОЙСТВО ]</button>
    <button class="tab-btn" onclick="switchTab('headers')">[ ЗАГОЛОВКИ ]</button>
  </div>

  <!-- ПРОФИЛЬ -->
  <div id="tab-profile" class="tab-panel active">
    <div class="profile-header">
      {% if session.tg_photo_url %}
        <img class="avatar" src="{{ session.tg_photo_url }}" alt="avatar">
      {% else %}
        <div class="avatar-placeholder">👤</div>
      {% endif %}
      <div>
        <div class="profile-name">{{ session.tg_first_name }} {{ session.tg_last_name or '' }}</div>
        {% if session.tg_username %}
          <div style="color:var(--muted);font-size:13px;margin-top:4px;">@{{ session.tg_username }}</div>
        {% endif %}
        <div class="badge">✓ VERIFIED SCAN</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-label">Telegram ID</div>
        <div class="card-value">{{ session.tg_id }}</div>
      </div>
      <div class="card">
        <div class="card-label">Username</div>
        <div class="card-value">{{ '@' + session.tg_username if session.tg_username else '—' }}</div>
      </div>
      <div class="card">
        <div class="card-label">Язык интерфейса</div>
        <div class="card-value">{{ session.tg_lang or '—' }}</div>
      </div>
      <div class="card">
        <div class="card-label">Скан выполнен</div>
        <div class="card-value small">{{ session.consent_at or '—' }}</div>
      </div>
    </div>
  </div>

  <!-- СЕТЬ -->
  <div id="tab-network" class="tab-panel">
    <div class="card">
      <div class="card-label">IP-адрес</div>
      <div class="card-value pink">{{ session.ip or '—' }}</div>
    </div>
    <div class="grid-2">
      <div class="card">
        <div class="card-label">Страна</div>
        <div class="card-value small">{{ session.geo_country or '—' }}</div>
      </div>
      <div class="card">
        <div class="card-label">Город</div>
        <div class="card-value small">{{ session.geo_city or '—' }}</div>
      </div>
      <div class="card">
        <div class="card-label">Провайдер (ISP)</div>
        <div class="card-value small">{{ session.geo_isp or '—' }}</div>
      </div>
      <div class="card">
        <div class="card-label">VPN / Proxy</div>
        <div class="card-value {% if session.geo_proxy %}pink{% else %}status-ok{% endif %}">
          {{ 'ОБНАРУЖЕН ⚠' if session.geo_proxy else 'НЕ ОБНАРУЖЕН ✓' }}
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-label">WebRTC утечка IP</div>
      <div id="webrtc-result" class="card-value collecting">Сбор данных</div>
    </div>
  </div>

  <!-- УСТРОЙСТВО -->
  <div id="tab-device" class="tab-panel">
    <div class="grid-2">
      <div class="card">
        <div class="card-label">Браузер</div>
        <div class="card-value small">{{ ua_info.browser or '—' }} {{ ua_info.browser_version or '' }}</div>
      </div>
      <div class="card">
        <div class="card-label">Операционная система</div>
        <div class="card-value small">{{ ua_info.os or '—' }} {{ ua_info.os_version or '' }}</div>
      </div>
      <div class="card">
        <div class="card-label">Тип устройства</div>
        <div class="card-value small">{{ ua_info.device_type or '—' }}</div>
      </div>
      <div class="card">
        <div class="card-label">Разрешение экрана</div>
        <div id="screen-res" class="card-value small collecting">Сбор данных</div>
      </div>
      <div class="card">
        <div class="card-label">Временная зона</div>
        <div id="timezone" class="card-value small collecting">Сбор данных</div>
      </div>
      <div class="card">
        <div class="card-label">Глубина цвета</div>
        <div id="color-depth" class="card-value small collecting">Сбор данных</div>
      </div>
    </div>
    <div class="card">
      <div class="card-label">Отпечаток браузера</div>
      <div id="fp-hash" class="card-value blue collecting">Вычисление</div>
    </div>
    <div class="card">
      <div class="card-label">Уникальность отпечатка</div>
      <div id="fp-score" class="card-value collecting">Вычисление</div>
    </div>
  </div>

  <!-- ЗАГОЛОВКИ -->
  <div id="tab-headers" class="tab-panel">
    <div class="card" style="padding:0;overflow:hidden;">
      <table class="headers-table">
        <thead>
          <tr><th>Заголовок</th><th>Значение</th></tr>
        </thead>
        <tbody>
          {% for key, value in headers_raw.items() %}
          <tr>
            <td class="header-key">{{ key }}</td>
            <td>{{ value }}</td>
          </tr>
          {% else %}
          <tr><td colspan="2" style="color:var(--muted);padding:16px;">Заголовки не получены</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

</div>

<script>
  const SCAN_TOKEN = "{{ token }}";

  function switchTab(name) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    event.currentTarget.classList.add('active');
  }
</script>
<script src="/static/scanner.js"></script>
</body>
</html>
```

- [ ] **Step 2: Run route tests to confirm dashboard renders**

```bash
pytest tests/test_routes.py::test_dashboard_with_consent_returns_200 -v
```
Expected: PASS (response contains "SCAN COMPLETE")

- [ ] **Step 3: Commit**

```bash
git add web/templates/dashboard.html
git commit -m "feat: dashboard template with 4 tabs"
```

---

## Task 9: Legal Page Template

**Files:**
- Modify: `web/templates/legal.html`

- [ ] **Step 1: Replace stub with full legal.html**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TGScanner — Условия использования</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="legal-page">

  <a href="javascript:history.back()" class="back-link">← Вернуться назад</a>

  <h1>Условия использования</h1>
  <div class="updated">Последнее обновление: апрель 2026</div>

  <h2>1. Назначение сервиса</h2>
  <p>TGScanner — инструмент для самодиагностики приватности. Сервис позволяет пользователю узнать, какие данные о нём доступны через браузерный запрос и Telegram API. Все собираемые данные принадлежат самому пользователю.</p>

  <h2>2. Согласие на сбор данных</h2>
  <p>Любой сбор данных происходит исключительно после явного согласия пользователя путём нажатия кнопки «Принять и продолжить». Без явного согласия данные не фиксируются и не сохраняются.</p>

  <h2>3. Какие данные собираются</h2>
  <p>После подтверждения согласия сервис собирает: публичные данные профиля Telegram (ID, имя, @username, аватар, язык); IP-адрес и данные геолокации, полученные через публичный API; User-Agent строку браузера; HTTP-заголовки запроса; характеристики устройства, собранные через JavaScript (разрешение экрана, временная зона, отпечаток браузера); IP-адреса, раскрываемые через WebRTC.</p>

  <h2>4. Ограничение ответственности</h2>
  <p>Сервис предоставляется «как есть». Авторы не несут ответственности за интерпретацию результатов сканирования, точность геолокационных данных (они предоставляются третьей стороной — ip-api.com), а также за любые действия пользователя на основании полученных данных.</p>
  <p>Точность данных о VPN/Proxy является приблизительной и не гарантируется. Отпечаток браузера и показатель уникальности носят информационный характер.</p>

  <h2>5. Передача данных третьим лицам</h2>
  <p>Собранные данные не передаются, не продаются и не раскрываются третьим лицам. Для получения геолокации по IP используется публичный API ip-api.com — IP-адрес пользователя передаётся на их серверы в рамках стандартного запроса.</p>

  <h2>6. Хранение данных</h2>
  <p>Данные хранятся в базе данных сервиса. Пользователь может запросить удаление своих данных, обратившись по контактному адресу ниже.</p>

  <h2>7. Ограничения использования</h2>
  <p>Запрещается использовать сервис для сбора данных о третьих лицах без их согласия. Каждая ссылка предназначена исключительно для самодиагностики владельца ссылки.</p>

  <h2>8. Контакт</h2>
  <p>По вопросам, связанным с данными: <a href="mailto:apolonov.osi1@gmail.com">apolonov.osi1@gmail.com</a></p>

</div>
</body>
</html>
```

- [ ] **Step 2: Verify legal page test still passes**

```bash
pytest tests/test_routes.py::test_legal_returns_200 -v
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/templates/legal.html
git commit -m "feat: legal / terms of service page"
```

---

## Task 10: scanner.js — Client-Side Data Collection

**Files:**
- Modify: `web/static/scanner.js`

- [ ] **Step 1: Write web/static/scanner.js**

```javascript
(function () {
  'use strict';

  // ── Utilities ──────────────────────────────────────────────────────────────

  function djb2(str) {
    let hash = 5381;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) + hash) + str.charCodeAt(i);
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16).padStart(8, '0');
  }

  function setEl(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  // ── Screen data ────────────────────────────────────────────────────────────

  function collectScreen() {
    return {
      width: window.screen.width,
      height: window.screen.height,
      availWidth: window.screen.availWidth,
      availHeight: window.screen.availHeight,
      colorDepth: window.screen.colorDepth,
      pixelRatio: window.devicePixelRatio || 1,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timezoneOffset: new Date().getTimezoneOffset(),
      language: navigator.language,
      languages: (navigator.languages || []).join(','),
      platform: navigator.platform,
      hardwareConcurrency: navigator.hardwareConcurrency || 0,
      maxTouchPoints: navigator.maxTouchPoints || 0,
      cookieEnabled: navigator.cookieEnabled,
      doNotTrack: navigator.doNotTrack,
    };
  }

  // ── Canvas fingerprint ─────────────────────────────────────────────────────

  function canvasFingerprint() {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = 200;
      canvas.height = 40;
      const ctx = canvas.getContext('2d');
      ctx.textBaseline = 'alphabetic';
      ctx.fillStyle = '#00ff88';
      ctx.font = '14px JetBrains Mono, monospace';
      ctx.fillText('TGScanner \u2639 \u{1F50D}', 4, 28);
      ctx.strokeStyle = '#ff0066';
      ctx.lineWidth = 1;
      ctx.strokeRect(1, 1, 198, 38);
      ctx.fillStyle = 'rgba(0,204,255,0.3)';
      ctx.fillRect(60, 5, 80, 12);
      return canvas.toDataURL().slice(-80);
    } catch (_) {
      return 'unavailable';
    }
  }

  // ── Audio fingerprint ──────────────────────────────────────────────────────

  async function audioFingerprint() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
      const oscillator = ctx.createOscillator();
      const analyser = ctx.createAnalyser();
      const gain = ctx.createGain();
      gain.gain.value = 0;
      oscillator.type = 'triangle';
      oscillator.frequency.value = 10000;
      oscillator.connect(analyser);
      analyser.connect(gain);
      gain.connect(ctx.destination);
      oscillator.start(0);
      await new Promise(resolve => setTimeout(resolve, 100));
      const data = new Float32Array(analyser.frequencyBinCount);
      analyser.getFloatFrequencyData(data);
      oscillator.stop();
      await ctx.close();
      return data.slice(0, 30).reduce((a, b) => a + Math.abs(b), 0).toFixed(4);
    } catch (_) {
      return 'unavailable';
    }
  }

  // ── WebRTC leak detection ──────────────────────────────────────────────────

  async function detectWebRTCLeaks() {
    return new Promise(resolve => {
      const ips = new Set();
      let pc;
      try {
        pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
        pc.createDataChannel('');
        pc.createOffer()
          .then(offer => pc.setLocalDescription(offer))
          .catch(() => resolve([]));

        pc.onicecandidate = event => {
          if (!event || !event.candidate) {
            pc.close();
            resolve(Array.from(ips));
            return;
          }
          const matches = event.candidate.candidate.match(/(\d{1,3}(\.\d{1,3}){3})/g);
          if (matches) matches.forEach(ip => ips.add(ip));
        };
      } catch (_) {
        resolve([]);
        return;
      }
      setTimeout(() => {
        try { pc.close(); } catch (_) {}
        resolve(Array.from(ips));
      }, 4000);
    });
  }

  // ── Fingerprint score (entropy estimate) ──────────────────────────────────

  function calculateScore(screen, canvasHash, audioHash) {
    let score = 0;
    const max = 10;

    const commonRes = ['1920x1080', '1366x768', '1440x900', '1280x720', '1536x864'];
    if (!commonRes.includes(`${screen.width}x${screen.height}`)) score += 2;

    if (canvasHash && canvasHash !== 'unavailable') score += 3;

    if (audioHash && audioHash !== 'unavailable') score += 2;

    if (screen.timezoneOffset !== 0) score += 1;

    if (screen.language && !screen.language.startsWith('en')) score += 1;

    if (screen.hardwareConcurrency > 4) score += 1;

    return Math.round((score / max) * 100);
  }

  // ── Update DOM ─────────────────────────────────────────────────────────────

  function updateScreenDOM(screen) {
    setEl('screen-res', `${screen.width} × ${screen.height} (×${screen.pixelRatio})`);
    setEl('timezone', screen.timezone || '—');
    setEl('color-depth', `${screen.colorDepth}-bit`);
  }

  function updateWebRTCDOM(ips) {
    if (!ips || ips.length === 0) {
      setEl('webrtc-result', '<span class="status-ok">Утечек не обнаружено ✓</span>');
    } else {
      setEl('webrtc-result', `<span class="status-warn">⚠ Обнаружены IP: ${ips.join(', ')}</span>`);
    }
  }

  function updateFingerprintDOM(hash, score) {
    setEl('fp-hash', `<span style="font-size:12px;word-break:break-all;">${hash}</span>`);
    const color = score >= 70 ? 'var(--pink)' : score >= 40 ? 'var(--blue)' : 'var(--green)';
    setEl('fp-score', `<span style="color:${color}">${score}%</span> <span style="font-size:11px;color:var(--muted);">(оценка уникальности)</span>`);
  }

  // ── Main ───────────────────────────────────────────────────────────────────

  async function run() {
    const token = window.SCAN_TOKEN;
    if (!token) return;

    const screen = collectScreen();
    updateScreenDOM(screen);

    const [canvasHash, audioHash, webrtcIPs] = await Promise.all([
      Promise.resolve(canvasFingerprint()),
      audioFingerprint(),
      detectWebRTCLeaks(),
    ]);

    updateWebRTCDOM(webrtcIPs);

    const fpRaw = `${canvasHash}|${audioHash}|${screen.width}x${screen.height}|${screen.timezone}|${screen.language}|${screen.hardwareConcurrency}`;
    const fpHash = djb2(fpRaw);
    const fpScore = calculateScore(screen, canvasHash, audioHash);

    updateFingerprintDOM(fpHash, fpScore);

    try {
      await fetch(`/scan/${token}/client`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          screen,
          webrtc_ips: webrtcIPs,
          fingerprint_hash: fpHash,
          fingerprint_score: fpScore / 100,
        }),
      });
    } catch (_) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
```

- [ ] **Step 2: Commit**

```bash
git add web/static/scanner.js
git commit -m "feat: client-side scanner (WebRTC, fingerprint, screen)"
```

---

## Task 11: Wire main.py

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    import uvicorn
    from aiogram import Bot

    from bot.handlers import create_dispatcher
    from db.database import init_db
    from web.app import create_app

    await init_db()

    bot = Bot(token=os.environ["BOT_TOKEN"])
    dp = create_dispatcher()
    app = create_app()

    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=["message", "callback_query"]),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run all tests to confirm everything still passes**

```bash
pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 3: Install dependencies and do a local smoke test**

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in a real `BOT_TOKEN`. Set `BASE_URL=http://localhost:8000`.

```bash
python main.py
```

Expected output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Open `http://localhost:8000/legal` — legal page should render with cyberpunk styling.

Send `/scan` to your bot — should receive a message with an inline button.
Click the button — consent screen should appear.
Click accept — dashboard should load with your Telegram profile and then fill in device/WebRTC data.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: main.py entry point — bot + web server"
```

---

## Task 12: Railway Deployment

**Files:**
- Create: `railway.toml`
- Create: `Procfile`

- [ ] **Step 1: Create railway.toml**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python main.py"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

- [ ] **Step 2: Create Procfile**

```
web: python main.py
```

- [ ] **Step 3: Commit**

```bash
git add railway.toml Procfile
git commit -m "chore: Railway deployment config"
```

- [ ] **Step 4: Deploy to Railway**

1. Go to railway.app → New Project → Deploy from GitHub repo (push this repo to GitHub first)
2. Railway will auto-detect Python and build
3. Go to project Settings → Variables → Add:
   - `BOT_TOKEN` = your Telegram bot token
   - `BASE_URL` = (leave empty for now — set after step 5)
4. Go to Settings → Networking → Generate Domain → copy the `*.up.railway.app` URL
5. Add `BASE_URL` = `https://your-app.up.railway.app` in Variables
6. Redeploy (Railway auto-redeploys on variable changes)

- [ ] **Step 5: Verify production deployment**

Send `/scan` to your bot. Click the button — should open `https://your-app.up.railway.app/scan/{token}` with a valid SSL certificate. Complete the scan. Verify all 4 tabs display data correctly.

---

## Self-Review Checklist

**Spec coverage:**
- [x] Telegram bot /start, /scan, /history, /help → Tasks 5, 11
- [x] UUID token generation → Task 3
- [x] SQLite session storage → Task 2
- [x] Consent screen with ToS hyperlink → Tasks 4, 7, 9
- [x] IP capture at consent POST → Task 4 (web/app.py `accept_consent`)
- [x] IP geolocation via ip-api.com → Task 3 (geo.py)
- [x] User-Agent parsing → Task 3 (fingerprint.py)
- [x] Dashboard with 4 tabs → Task 8
- [x] WebRTC leak detection → Task 10 (scanner.js)
- [x] Browser fingerprint hash + score → Task 10 (scanner.js)
- [x] Client-side data POST to /client endpoint → Tasks 4, 10
- [x] /history with card formatting and pagination → Task 5
- [x] Cyberpunk CSS theme → Task 6
- [x] Legal page → Task 9
- [x] Railway deployment → Task 12
- [x] Inline scan button in Telegram → Task 5 (keyboards.py)
- [x] Screen resolution, timezone from JS → Task 10

**No placeholders:** Verified — all steps contain complete code.

**Type consistency:** `create_session`, `get_session`, `update_consent`, `update_client_data`, `get_user_sessions`, `count_user_sessions` are defined in Task 2 and used consistently in Tasks 4 and 5. `parse_user_agent` defined in Task 3, used in Tasks 4 and 5. `generate_token` defined in Task 3, used in Task 5.
