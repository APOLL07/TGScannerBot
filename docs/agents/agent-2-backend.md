# Агент 2 — Backend

**Фаза:** 2 — запускать после завершения Агента 1, параллельно с Агентом 3.

**Полный план:** `docs/superpowers/plans/2026-04-18-tgscanner.md`
**Задачи из плана:** Task 4, Task 5

---

## Ответственность

Вся Python-логика бэкенда: FastAPI роуты и Telegram бот.
Создаёт stub-шаблоны (однострочный HTML) — Агент 3 заменит их на полноценные.
Создаёт пустые static-файлы — Агент 3 заполнит их.

---

## Предусловие

Перед стартом убедиться что существуют:
- `db/database.py` с функциями `init_db`, `create_session`, `get_session`, `update_consent`, `update_client_data`, `get_user_sessions`, `count_user_sessions`
- `services/token.py` с `generate_token()`
- `services/geo.py` с `get_ip_info()`
- `services/fingerprint.py` с `parse_user_agent()`
- `tests/conftest.py` с фикстурой `set_test_db`

---

## Файлы, которые создаёт

| Файл | Что делает |
|------|-----------|
| `web/app.py` | FastAPI app factory со всеми роутами |
| `web/templates/consent.html` | **Stub** — заменит Агент 3 |
| `web/templates/dashboard.html` | **Stub** — заменит Агент 3 |
| `web/templates/legal.html` | **Stub** — заменит Агент 3 |
| `web/static/style.css` | **Пустой файл** — заполнит Агент 3 |
| `web/static/scanner.js` | **Пустой файл** — заполнит Агент 3 |
| `bot/keyboards.py` | `scan_button(url)`, `history_nav(tg_id, page, total_pages)` |
| `bot/handlers.py` | Router: /start /help /scan /history + callback, `create_dispatcher()` |
| `tests/test_routes.py` | Тесты всех FastAPI роутов |

---

## Задачи из плана (выполнять по порядку)

### Task 4 — FastAPI Routes

#### Шаг 1: Создать stub-шаблоны и пустые static-файлы

`web/templates/consent.html`:
```html
<!DOCTYPE html><html><body>CONSENT {{ token }}</body></html>
```

`web/templates/dashboard.html`:
```html
<!DOCTYPE html><html><body>DASHBOARD {{ session.tg_id }}</body></html>
```

`web/templates/legal.html`:
```html
<!DOCTYPE html><html><body>LEGAL</body></html>
```

```bash
touch web/static/style.css web/static/scanner.js
```

#### Шаг 2: Написать тесты (до реализации)

`tests/test_routes.py`:
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


async def test_client_data_without_consent_returns_403(client, set_test_db):
    import db.database as dbmod
    await dbmod.create_session("tok-nocon", 1, None, "Test", None, "ru", None)
    resp = await client.post("/scan/tok-nocon/client", json={})
    assert resp.status_code == 403
```

Запустить — убедиться что падают (`ModuleNotFoundError: No module named 'web.app'`).

#### Шаг 3: Реализовать web/app.py

```python
import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db.database import get_session, update_consent, update_client_data
from services.fingerprint import parse_user_agent
from services.geo import get_ip_info

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

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

Запустить: `pytest tests/test_routes.py -v` — все тесты зелёные.

Commit: `feat: FastAPI routes with consent and dashboard`

---

### Task 5 — Bot Handlers and Keyboards

#### Шаг 1: Создать bot/keyboards.py

```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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

#### Шаг 2: Создать bot/handlers.py

```python
import math
import os
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import history_nav, scan_button
from db.database import count_user_sessions, create_session, get_user_sessions
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

Запустить все тесты: `pytest tests/ -v` — все зелёные.

Commit: `feat: bot handlers — /start /help /scan /history`

---

## Финальная проверка

```bash
pytest tests/ -v
```

Все тесты зелёные. После этого Агент 4 может стартовать (вместе с завершением Агента 3).

---

## Запрещено

- Записывать реальный HTML/CSS/JS в `web/templates/` или `web/static/` — только stubs и пустые файлы
- Создавать `main.py`
- Изменять `db/database.py` или любой файл из `services/`
- Изменять `tests/conftest.py`
