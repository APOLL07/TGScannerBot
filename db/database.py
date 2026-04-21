import asyncpg
import json
import os
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool


async def init_db() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGSERIAL PRIMARY KEY,
                token TEXT UNIQUE NOT NULL,
                tg_id BIGINT NOT NULL,
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
                fingerprint_score DOUBLE PRECISION,
                os_hint TEXT,
                browser_hint TEXT,
                consent_given INTEGER DEFAULT 0,
                consent_at TEXT,
                created_at TEXT DEFAULT (to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
        # Permanent consent table — one row per Telegram user
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_consents (
                tg_id BIGINT PRIMARY KEY,
                consented_at TEXT NOT NULL
            )
        """)


async def create_session(
    token: str,
    tg_id: int,
    tg_username: Optional[str],
    tg_first_name: str,
    tg_last_name: Optional[str],
    tg_lang: Optional[str],
    tg_photo_url: Optional[str],
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """INSERT INTO sessions
                   (token, tg_id, tg_username, tg_first_name, tg_last_name, tg_lang, tg_photo_url)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                token, tg_id, tg_username, tg_first_name, tg_last_name, tg_lang, tg_photo_url,
            )
        except asyncpg.UniqueViolationError as e:
            raise ValueError(f"Session with token '{token}' already exists") from e


async def get_session(token: str) -> Optional[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE token = $1", token)
        return dict(row) if row else None


async def has_user_consented(tg_id: int) -> bool:
    """Returns True if this Telegram user has ever accepted the consent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM user_consents WHERE tg_id = $1", tg_id
        )
        return row is not None


async def grant_user_consent(tg_id: int) -> None:
    """Record permanent consent for a Telegram user (upsert)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO user_consents (tg_id, consented_at)
               VALUES ($1, to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS'))
               ON CONFLICT (tg_id) DO NOTHING""",
            tg_id,
        )


async def update_consent(
    token: str, ip: str, user_agent: str, headers: dict, geo: dict,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE sessions SET
               ip = $1, user_agent = $2, headers = $3,
               geo_country = $4, geo_city = $5, geo_isp = $6, geo_proxy = $7,
               consent_given = 1, consent_at = to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
               WHERE token = $8""",
            ip, user_agent, json.dumps(headers),
            geo.get("country"), geo.get("city"), geo.get("isp"),
            1 if geo.get("proxy") else 0,
            token,
        )
        if result == "UPDATE 0":
            raise ValueError(f"No session found for token: {token}")


async def update_client_data(
    token: str, screen_data: dict, webrtc_ips: list,
    fingerprint_hash: str, fingerprint_score: float,
    os_hint: str = "", browser_hint: str = "",
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Add columns if they don't exist yet (for existing deployments)
        await conn.execute(
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS os_hint TEXT"
        )
        await conn.execute(
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS browser_hint TEXT"
        )
        result = await conn.execute(
            """UPDATE sessions SET
               screen_data = $1, webrtc_ips = $2,
               fingerprint_hash = $3, fingerprint_score = $4,
               os_hint = $5, browser_hint = $6
               WHERE token = $7""",
            json.dumps(screen_data), json.dumps(webrtc_ips),
            fingerprint_hash, fingerprint_score,
            os_hint or None, browser_hint or None, token,
        )
        if result == "UPDATE 0":
            raise ValueError(f"No session found for token: {token}")


async def get_user_sessions(tg_id: int, limit: int = 5, offset: int = 0) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM sessions WHERE tg_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            tg_id, limit, offset,
        )
        return [dict(row) for row in rows]


async def count_user_sessions(tg_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) FROM sessions WHERE tg_id = $1", tg_id
        )
        return row[0] if row else 0
