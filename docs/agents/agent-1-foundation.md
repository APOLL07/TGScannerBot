# Агент 1 — Foundation

**Фаза:** 1 — запускать первым, до всех остальных агентов.

**Полный план:** `docs/superpowers/plans/2026-04-18-tgscanner.md`
**Задачи из плана:** Task 1, Task 2, Task 3

---

## Ответственность

Создаёт всю основу проекта: файловую структуру, зависимости, базу данных и сервисы.
Все остальные агенты зависят от результатов этого агента и не могут стартовать до его завершения.

---

## Файлы, которые создаёт

| Файл | Что делает |
|------|-----------|
| `requirements.txt` | Все зависимости проекта |
| `.env.example` | Шаблон переменных окружения |
| `.gitignore` | Исключения git |
| `pytest.ini` | `asyncio_mode = auto` |
| `db/__init__.py` | Пустой, объявляет пакет |
| `db/database.py` | Все функции работы с SQLite |
| `bot/__init__.py` | Пустой, объявляет пакет |
| `services/__init__.py` | Пустой, объявляет пакет |
| `web/__init__.py` | Пустой, объявляет пакет |
| `tests/__init__.py` | Пустой, объявляет пакет |
| `tests/conftest.py` | Pytest fixture: temp SQLite DB, monkeypatch DB_PATH |
| `tests/test_db.py` | Тесты всех функций базы данных |
| `services/token.py` | `generate_token() -> str` |
| `services/geo.py` | `get_ip_info(ip: str) -> dict` |
| `services/fingerprint.py` | `parse_user_agent(ua: str) -> dict` |
| `tests/test_services.py` | Тесты token, geo, fingerprint |

---

## Задачи из плана (выполнять по порядку)

### Task 1 — Project Scaffold

Создать структуру директорий и конфигурационные файлы.

**requirements.txt:**
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

**.env.example:**
```
BOT_TOKEN=your_telegram_bot_token_here
BASE_URL=https://yourapp.up.railway.app
PORT=8000
```

**.gitignore:**
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

**pytest.ini:**
```ini
[pytest]
asyncio_mode = auto
```

Создать директории и пустые `__init__.py`:
```bash
mkdir -p db bot services tests web/templates web/static
touch db/__init__.py bot/__init__.py services/__init__.py tests/__init__.py web/__init__.py
touch web/static/.gitkeep
```

Commit: `chore: project scaffold`

---

### Task 2 — Database Layer

**tests/conftest.py:**
```python
import pytest

@pytest.fixture(autouse=True)
def set_test_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import db.database as dbmod
    monkeypatch.setattr(dbmod, "DB_PATH", db_path)
    return db_path
```

**tests/test_db.py:**
```python
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
```

Запустить тесты — убедиться что падают (`ModuleNotFoundError`).

**db/database.py:**
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
    token: str, ip: str, user_agent: str, headers: dict, geo: dict,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE sessions SET
               ip = ?, user_agent = ?, headers = ?,
               geo_country = ?, geo_city = ?, geo_isp = ?, geo_proxy = ?,
               consent_given = 1, consent_at = datetime('now')
               WHERE token = ?""",
            (
                ip, user_agent, json.dumps(headers),
                geo.get("country"), geo.get("city"), geo.get("isp"),
                1 if geo.get("proxy") else 0,
                token,
            ),
        )
        await db.commit()


async def update_client_data(
    token: str, screen_data: dict, webrtc_ips: list,
    fingerprint_hash: str, fingerprint_score: float,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE sessions SET
               screen_data = ?, webrtc_ips = ?,
               fingerprint_hash = ?, fingerprint_score = ?
               WHERE token = ?""",
            (
                json.dumps(screen_data), json.dumps(webrtc_ips),
                fingerprint_hash, fingerprint_score, token,
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
            return [dict(row) for row in await cursor.fetchall()]


async def count_user_sessions(tg_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM sessions WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
```

Запустить: `pytest tests/test_db.py -v` — все тесты зелёные.

Commit: `feat: database layer with session CRUD`

---

### Task 3 — Services

**tests/test_services.py:**
```python
import re
import pytest
from unittest.mock import AsyncMock, patch
from services.token import generate_token
from services.fingerprint import parse_user_agent
from services.geo import get_ip_info

def test_generate_token_is_uuid4():
    token = generate_token()
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", token
    )

def test_generate_token_unique():
    assert generate_token() != generate_token()

def test_parse_chrome_windows():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    result = parse_user_agent(ua)
    assert result["browser"] == "Chrome"
    assert result["browser_version"] == "124"
    assert result["os"] == "Windows"
    assert result["device_type"] == "Desktop"

def test_parse_mobile_ua():
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
    result = parse_user_agent(ua)
    assert result["device_type"] == "Mobile"

def test_parse_empty_ua():
    assert parse_user_agent("") == {}

async def test_get_ip_info_localhost_returns_empty():
    assert await get_ip_info("127.0.0.1") == {}

async def test_get_ip_info_success():
    mock_resp = AsyncMock()
    mock_resp.json.return_value = {
        "status": "success", "country": "Russia", "regionName": "Moscow",
        "city": "Moscow", "isp": "MTS", "org": "MTS PJSC",
        "as": "AS8359", "proxy": False, "hosting": False,
    }
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        result = await get_ip_info("1.2.3.4")
    assert result["country"] == "Russia"
    assert result["proxy"] is False

async def test_get_ip_info_exception_returns_empty():
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("timeout"))
        result = await get_ip_info("1.2.3.4")
    assert result == {}
```

Запустить тесты — убедиться что падают.

**services/token.py:**
```python
import uuid

def generate_token() -> str:
    return str(uuid.uuid4())
```

**services/fingerprint.py:**
```python
from ua_parser import user_agent_parser

def parse_user_agent(ua_string: str) -> dict:
    if not ua_string:
        return {}
    parsed = user_agent_parser.Parse(ua_string)
    browser = parsed["user_agent"]
    os_info = parsed["os"]
    device = parsed["device"]
    device_family = device.get("family") or "Other"
    return {
        "browser": browser.get("family") or "Unknown",
        "browser_version": browser.get("major") or "",
        "os": os_info.get("family") or "Unknown",
        "os_version": os_info.get("major") or "",
        "device_type": "Mobile" if device_family not in ("Other", "") else "Desktop",
        "device_brand": device.get("brand") or "",
        "device_model": device.get("model") or "",
    }
```

**services/geo.py:**
```python
import httpx

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

Запустить: `pytest tests/test_services.py -v` — все тесты зелёные.

Commit: `feat: token, geo, and fingerprint services`

---

## Финальная проверка

```bash
pytest tests/test_db.py tests/test_services.py -v
```

Все тесты должны быть зелёными. После этого Агенты 2 и 3 могут стартовать.

---

## Запрещено

- Создавать `main.py`
- Создавать файлы в `web/templates/` или `web/static/`
- Создавать `bot/handlers.py` или `bot/keyboards.py`
- Изменять схему базы данных после коммита
