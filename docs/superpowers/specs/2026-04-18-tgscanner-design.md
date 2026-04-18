# TGScanner — Design Spec
**Date:** 2026-04-18  
**Status:** Approved

---

## Overview

TGScanner is a Telegram bot + web application that allows a user to scan their **own** data — what Telegram exposes about their account and what any web server can learn from their browser request. The tool is a privacy-awareness instrument: users see exactly what data is visible about them. No third-party data is collected or exposed without explicit user consent.

---

## Goals

- Let users discover their own public Telegram profile data
- Let users see what a web server learns when they open a link (IP, browser, OS, etc.)
- Provide advanced privacy insights: WebRTC IP leak, browser fingerprint uniqueness
- Keep a personal history of past scans
- Comply with basic privacy law (consent screen, ToS page, no data sharing)

---

## Non-Goals

- Scanning other users' data without consent
- Storing or sharing data with third parties
- Password or private message access (impossible via Telegram Bot API)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot framework | aiogram 3 (Python) |
| Web server | FastAPI |
| Database | SQLite via aiosqlite |
| HTML templating | Jinja2 |
| Frontend JS | Vanilla JS (no framework) |
| IP geolocation | ip-api.com (free tier) |
| User-Agent parsing | `ua-parser` Python library |
| Entry point | Single `main.py` launching both bot and web via asyncio |
| Hosting | Railway (Hobby plan) |
| Domain | Railway subdomain (`*.up.railway.app`) with auto HTTPS, or custom domain via Railway |

---

## Architecture

```
┌─────────────────┐        ┌──────────────────────────────┐        ┌──────────────┐
│  Telegram Bot   │        │   FastAPI Server (Railway)    │        │   SQLite DB  │
│   (aiogram 3)   │◄──────►│  https://app.up.railway.app  │◄──────►│  sessions.db │
└─────────────────┘        └──────────────────────────────┘        └──────────────┘
         │                                │
         │ generates token+link           │ serves HTML, collects browser data
         ▼                                ▼
   /scan → UUID token          /scan/{token}
                               user's browser (HTTPS)
```

**Data flow:**
1. User sends `/scan` to the bot
2. Bot creates a UUID token, stores Telegram user data in SQLite
3. Bot replies with an inline button `[🔍 ОТКРЫТЬ СКАНЕР]` linking to `https://app.up.railway.app/scan/{token}`
4. User opens the link → sees **Consent Screen**
5. User accepts Terms of Service → FastAPI records IP, User-Agent, HTTP headers
6. JS on the page collects: screen resolution, timezone, WebRTC IPs, browser fingerprint
7. Dashboard renders with 4 tabs

---

## File Structure

```
TGScanner/
├── main.py                  # Launches bot + web server via asyncio
├── bot/
│   ├── __init__.py
│   ├── handlers.py          # /start, /scan, /history, /help
│   └── keyboards.py         # Inline buttons
├── web/
│   ├── app.py               # FastAPI routes
│   ├── templates/
│   │   ├── consent.html     # Consent screen (shown before dashboard)
│   │   ├── dashboard.html   # Main dashboard with tabs
│   │   └── legal.html       # Terms of Service / Disclaimer page
│   └── static/
│       ├── style.css        # Cyberpunk/hacker visual styles
│       └── scanner.js       # WebRTC leak, fingerprint, screen info collection
├── db/
│   ├── database.py          # SQLite connection and init
│   └── models.py            # Session and history table schemas
├── services/
│   ├── geo.py               # IP geolocation via ip-api.com
│   ├── fingerprint.py       # User-Agent parsing
│   └── token.py             # UUID token generation
├── legal/
│   └── terms.md             # Source text for Terms of Service
├── .env                     # BOT_TOKEN, BASE_URL (local dev only)
├── railway.toml             # Railway deployment config
├── Procfile                 # Process start command for Railway
└── requirements.txt
```

---

## Database Schema

### Table: `sessions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `token` | TEXT UNIQUE | UUID scan token |
| `tg_id` | INTEGER | Telegram user ID |
| `tg_username` | TEXT | @username (nullable) |
| `tg_first_name` | TEXT | First name |
| `tg_last_name` | TEXT | Last name (nullable) |
| `tg_lang` | TEXT | Telegram language code |
| `tg_photo_url` | TEXT | Profile photo URL (nullable) |
| `ip` | TEXT | IP address at link open time |
| `user_agent` | TEXT | Raw User-Agent string |
| `headers` | TEXT | JSON-encoded HTTP headers |
| `screen_data` | TEXT | JSON: resolution, colorDepth, timezone |
| `webrtc_ips` | TEXT | JSON: detected WebRTC IPs |
| `fingerprint_hash` | TEXT | Browser fingerprint hash |
| `fingerprint_score` | REAL | Uniqueness score 0.0–1.0 |
| `consent_given` | INTEGER | Boolean (0/1) |
| `consent_at` | TEXT | ISO timestamp of consent |
| `created_at` | TEXT | ISO timestamp of token creation |

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message explaining what the bot does |
| `/scan` | Generates a unique scan link, sends as inline button |
| `/history` | Shows paginated cards of past scans |
| `/help` | Lists all commands with short descriptions |

### `/scan` response format
Message text + inline keyboard:
```
🔍 Твоя ссылка для сканирования готова.
Открой её в браузере — увидишь всё что о тебе известно.

[🔍 ОТКРЫТЬ СКАНЕР]   ← URL button
```

### `/history` card format (monospace via `<pre>`)
```
╔══ СКАН #3 ══════════════════╗
📅 18 апр 2026, 14:32
🌐 IP: 91.234.xx.xx
📍 Москва, Россия • МТС
💻 Chrome 124 • Windows 11
🔗 /scan_abc123
╚══════════════════════════════╝
```
Pagination via inline buttons: `← Назад` / `Вперёд →` (5 scans per page).

---

## Web Interface

### Consent Screen
Shown before the dashboard. Cannot be bypassed.

- Animated terminal boot text: "ИНИЦИАЛИЗАЦИЯ СКАНИРОВАНИЯ..."
- List of data that will be collected (IP, browser, Telegram profile)
- Text: "Продолжая, вы соглашаетесь с [Условиями использования]" — hyperlink to `/legal`
- Button: `[ПРИНЯТЬ И ПРОДОЛЖИТЬ]`
- On accept: sets `consent_given=true` in DB, redirects to dashboard

### Dashboard — 4 Tabs

**[ПРОФИЛЬ]**
- Avatar with neon border
- Telegram ID, username, full name, language
- "VERIFIED SCAN" badge

**[СЕТЬ]**
- IP address
- Country, city, ISP (from ip-api.com)
- Basic VPN/proxy indicator (by ASN)
- WebRTC leak result: real IP if VPN is leaking, or "Утечек не обнаружено ✓"

**[УСТРОЙСТВО]**
- OS, browser, version (parsed from User-Agent)
- Device type: Mobile / Desktop
- Screen resolution, color depth (from JS)
- Browser timezone
- Browser fingerprint hash + uniqueness score ("Уникальность: 94.7%")

**[ЗАГОЛОВКИ]**
- Full HTTP headers table (raw, for technically curious users)

### Legal Page (`/legal`)
Separate static page with:
- Disclaimer: the service collects data only with explicit user consent
- No responsibility clause for how users interpret results
- Data is not shared with third parties
- Data storage duration
- Contact information

---

## Visual Style

| Property | Value |
|----------|-------|
| Background | `#0a0a0f` |
| Primary accent | `#00ff88` (neon green) |
| Secondary accent | `#ff0066` (neon pink/red) |
| Font | `JetBrains Mono` (Google Fonts) |
| Effects | Glitch effect on headings, scanline CSS overlay, typewriter text animation |
| Tab active state | Neon underline glow |

---

## Bonus Features

### 1. WebRTC IP Leak Detection
JavaScript uses RTCPeerConnection to detect IPs exposed by the browser — including real IP behind a VPN. Results shown in the [СЕТЬ] tab.

### 2. Browser Fingerprint Score
JS collects: canvas fingerprint, installed fonts (via JS probing), audio API fingerprint, plugin list, screen metrics. Combined into a hash. Uniqueness score estimated from entropy of collected attributes. Shown in [УСТРОЙСТВО] tab.

### 3. Scan History with Pagination
Every opened scan link is logged. `/history` in the bot shows formatted cards with pagination. Allows the user to track their own scans over time (different devices, locations, IPs).

---

## Environment Variables

Set in Railway dashboard (production) and `.env` file (local dev):

```
BOT_TOKEN=your_telegram_bot_token
BASE_URL=https://yourapp.up.railway.app
PORT=8000
```

Railway injects `PORT` automatically. `BASE_URL` is set manually in Railway environment variables after first deploy.

---

## Out of Scope (v1)

- Authentication / multi-user isolation beyond token UUID
- Email notifications
- Dark/light theme toggle
- Export to PDF/PNG
