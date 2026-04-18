# Агент 4 — Integration & Deploy

**Фаза:** 3 — запускать последним, после завершения Агентов 2 и 3.

**Полный план:** `docs/superpowers/plans/2026-04-18-tgscanner.md`
**Задачи из плана:** Task 11, Task 12

---

## Ответственность

Соединяет бота и веб-сервер в единое приложение, настраивает Railway деплой, проводит финальную проверку всего проекта.

Создаёт только 3 файла. Всё остальное уже должно существовать.

---

## Предусловие

Перед стартом убедиться что все эти файлы существуют и не пустые:

```bash
# Python
ls db/database.py services/token.py services/geo.py services/fingerprint.py
ls bot/handlers.py bot/keyboards.py web/app.py

# Шаблоны и статика (не stubs — полноценный HTML)
ls web/templates/consent.html web/templates/dashboard.html web/templates/legal.html
ls web/static/style.css web/static/scanner.js

# Тесты
ls tests/conftest.py tests/test_db.py tests/test_services.py tests/test_routes.py

# Конфиг
ls requirements.txt pytest.ini
```

Запустить тесты — все должны быть зелёными **до** начала работы:
```bash
pytest tests/ -v
```

Если тесты не зелёные — не продолжать, сообщить о проблеме.

---

## Файлы, которые создаёт

| Файл | Что делает |
|------|-----------|
| `main.py` | Точка входа — запускает бота и веб-сервер через `asyncio.gather` |
| `railway.toml` | Конфигурация деплоя Railway |
| `Procfile` | Команда запуска для Railway |

---

## Задачи из плана (выполнять по порядку)

### Task 11 — Wire main.py

**main.py:**
```python
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    import uvicorn
    from aiogram import Bot

    from bot.handlers import create_dispatcher
    from db.database import init_db
    from web.app import create_app

    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("ERROR: BOT_TOKEN environment variable is not set.")
        sys.exit(1)

    await init_db()

    bot = Bot(token=token)
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

Commit: `feat: main.py entry point — bot + web server`

---

### Локальный smoke-тест

#### Шаг 1: Установить зависимости
```bash
pip install -r requirements.txt
```

#### Шаг 2: Создать .env файл
Скопировать `.env.example` в `.env` и заполнить:
```
BOT_TOKEN=реальный_токен_от_BotFather
BASE_URL=http://localhost:8000
PORT=8000
```

#### Шаг 3: Запустить
```bash
python main.py
```

Ожидаемый вывод:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

#### Шаг 4: Проверить вручную

| Проверка | Ожидание |
|----------|---------|
| `GET http://localhost:8000/legal` | Страница условий с киберпанк стилем |
| `/scan` в боте | Сообщение с кнопкой `[🔍 ОТКРЫТЬ СКАНЕР]` |
| Нажать кнопку | Открывается `http://localhost:8000/scan/{uuid}` с экраном согласия |
| Нажать `[ ПРИНЯТЬ И ПРОДОЛЖИТЬ ]` | Редирект на дашборд с 4 вкладками |
| Вкладка ПРОФИЛЬ | Telegram ID, имя, аватар |
| Вкладка СЕТЬ | IP-адрес, геолокация, WebRTC результат (через ~4 сек) |
| Вкладка УСТРОЙСТВО | Браузер, ОС, разрешение экрана, fingerprint hash и score |
| Вкладка ЗАГОЛОВКИ | Таблица HTTP заголовков |
| `/history` в боте | Карточка последнего скана с IP и браузером |

Если что-то не работает — не деплоить на Railway.

Commit: `chore: local smoke test passed`

---

### Task 12 — Railway Deployment

#### Шаг 1: Создать railway.toml

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python main.py"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

#### Шаг 2: Создать Procfile

```
web: python main.py
```

Commit: `chore: Railway deployment config`

#### Шаг 3: Опубликовать на GitHub

```bash
git remote add origin https://github.com/ВАШ_USERNAME/TGScanner.git
git branch -M main
git push -u origin main
```

#### Шаг 4: Деплой на Railway

1. Открыть [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Выбрать репозиторий `TGScanner`
3. Railway автоматически начнёт билд

#### Шаг 5: Переменные окружения

Railway Dashboard → проект → **Variables** → добавить:

| Ключ | Значение |
|------|---------|
| `BOT_TOKEN` | токен от BotFather |
| `BASE_URL` | оставить пустым пока (заполним после шага 6) |

#### Шаг 6: Получить домен

Railway Dashboard → проект → **Settings** → **Networking** → **Generate Domain**

Скопировать URL вида `https://tgscanner-production.up.railway.app`

#### Шаг 7: Добавить BASE_URL

**Variables** → добавить:
```
BASE_URL=https://tgscanner-production.up.railway.app
```

Railway автоматически передеплоит после изменения переменных.

#### Шаг 8: Финальная проверка на проде

| Проверка | Ожидание |
|----------|---------|
| `https://ваш-домен.up.railway.app/legal` | Страница открывается, в адресной строке HTTPS с замком |
| `/scan` в боте | Кнопка ведёт на `https://ваш-домен.up.railway.app/scan/{uuid}` |
| Полный флоу: согласие → дашборд | Всё работает как на локальном тесте |

---

## Финальная проверка

```bash
pytest tests/ -v
```

Все тесты зелёные. Проект задеплоен и работает на Railway.

---

## Запрещено

- Трогать файлы в `web/`, `bot/`, `db/`, `services/`, `tests/`
- Изменять `requirements.txt`
- Деплоить если `pytest tests/ -v` выдаёт ошибки
- Деплоить если smoke-тест показал проблемы
