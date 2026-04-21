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
railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
default_url = f"https://{railway_domain}" if railway_domain else "http://localhost:8000"
BASE_URL = os.environ.get("BASE_URL", default_url)
PAGE_SIZE = 5


async def _get_photo_url(bot: Bot, user_id: int) -> Optional[str]:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count == 0:
            return None
        file_id = photos.photos[0][-1].file_id
        file = await bot.get_file(file_id)
        return file.file_path
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
