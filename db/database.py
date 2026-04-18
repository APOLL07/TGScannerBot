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
