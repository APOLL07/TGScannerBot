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
