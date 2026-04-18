# Агент 3 — Frontend

**Фаза:** 2 — запускать после завершения Агента 1, параллельно с Агентом 2.

**Полный план:** `docs/superpowers/plans/2026-04-18-tgscanner.md`
**Задачи из плана:** Task 6, Task 7, Task 8, Task 9, Task 10

---

## Ответственность

Весь UI: CSS, HTML-шаблоны Jinja2, клиентский JavaScript.
Не трогает ни одного Python-файла и ни одного теста.

Файлы `web/templates/*.html` и `web/static/*` могут уже существовать как stubs от Агента 2 — перезаписывать полностью.

---

## Предусловие

Перед стартом убедиться что существуют директории:
- `web/templates/`
- `web/static/`

Если не существуют — создать: `mkdir -p web/templates web/static`

---

## Файлы, которые создаёт / перезаписывает

| Файл | Что делает |
|------|-----------|
| `web/static/style.css` | Полная киберпанк/неон тема |
| `web/templates/consent.html` | Экран согласия с boot-анимацией |
| `web/templates/dashboard.html` | Дашборд с 4 вкладками |
| `web/templates/legal.html` | Страница условий использования |
| `web/static/scanner.js` | Клиентский сбор данных |

---

## Задачи из плана (выполнять по порядку)

### Task 6 — style.css

Визуальный стиль:
- Фон: `#0a0a0f`, шрифт: `JetBrains Mono` (Google Fonts CDN)
- Основной акцент: `#00ff88` (неоновый зелёный)
- Вторичный акцент: `#ff0066` (неоновый розовый)
- Дополнительный: `#00ccff` (синий)

Обязательные эффекты:
- **Scanline overlay** — `body::after` с `repeating-linear-gradient` зелёных полос с opacity ~0.015
- **Glitch-анимация** — класс `.glitch` с псевдоэлементами `::before` (цвет `#ff0066`) и `::after` (цвет `#00ccff`), keyframes `glitch-1` и `glitch-2` с `translateX` ±3px, срабатывают раз в 3 сек
- **Typewriter** — класс `.typewriter` с `border-right: 2px solid #00ff88` и анимациями `typing` + `blink`
- **Boot-строки** — класс `.boot-line` с `opacity: 0` и анимацией `fade-in`, 5 строк с задержками 0.2s, 0.5s, 0.8s, 1.1s, 1.4s; класс `.ok::after` добавляет ` [OK]` зелёным цветом

Компоненты которые нужны:
- `.consent-screen` — flex центр на весь экран
- `.consent-box` — max-width 560px, border `1px solid #00ff88`, box-shadow с зелёным свечением
- `.btn-accept` — full-width, прозрачный фон, border `2px solid #00ff88`, hover меняет bg на `#00ff88` и цвет на `#0a0a0f`
- `.dashboard` — max-width 860px, margin auto, padding 32px
- `.tabs` — flex row, border-bottom
- `.tab-btn` — без border, `.active` получает `border-bottom: 2px solid #00ff88` и `color: #00ff88`
- `.tab-panel` — `display: none`, `.active` — `display: block`
- `.card` — bg `#0f0f1a`, border `1px solid #1e2a3a`, padding 20px
- `.card-label` — 11px, uppercase, letter-spacing 2px, цвет `#556070`
- `.card-value` — 18px, bold, цвет `#00ff88`; модификаторы `.pink` (`#ff0066`), `.blue` (`#00ccff`), `.small` (14px)
- `.grid-2` — CSS grid 2 колонки, на мобайле 1 колонка
- `.profile-header` — flex, gap 20px
- `.avatar` — 72px круг, border `2px solid #00ff88`, box-shadow зелёное свечение
- `.avatar-placeholder` — 72px круг, bg `#141428`, flex центр, font-size 28px
- `.badge` — inline-block, border `1px solid #00ff88`, цвет `#00ff88`, 10px, uppercase
- `.headers-table` — full-width, border-collapse collapse; `th` — uppercase 11px muted; `td` — padding 8px 12px, border-bottom
- `.header-key` — цвет `#00ff88`, width 35%
- `.collecting::after` — анимированные точки `...`
- `.legal-page` — max-width 720px, margin auto, padding 48px 24px
- `.back-link` — muted цвет, hover зелёный
- `h2` в `.legal-page` — border-left `3px solid #00ff88`, padding-left 12px

Commit: `feat: cyberpunk CSS theme`

---

### Task 7 — consent.html

**ОБЯЗАТЕЛЬНЫЕ элементы** (без них Агент 4 не сможет проверить функциональность):

1. `<form method="POST" action="/scan/{{ token }}/consent">` — форма с POST на consent endpoint
2. Кнопка submit внутри формы: текст `[ ПРИНЯТЬ И ПРОДОЛЖИТЬ ]`, класс `btn-accept`
3. Ссылка на legal: `<a href="/legal" target="_blank">Условиями использования</a>`
4. Текст согласия рядом со ссылкой: "Продолжая, вы соглашаетесь с..."
5. Список собираемых данных (`<ul>` или `<li>`)
6. `<link rel="stylesheet" href="/static/style.css">`

**Структура:**
```
body
└── .consent-screen
    └── .consent-box
        ├── .consent-title.glitch  (data-text="// TGSCANNER //")
        ├── .boot-lines
        │   ├── .boot-line.ok  "Инициализация сканирования"
        │   ├── .boot-line.ok  "Модуль сбора данных загружен"
        │   ├── .boot-line.ok  "Соединение с Telegram API"
        │   ├── .boot-line.ok  "Анализ сетевых параметров"
        │   └── .boot-line     "Ожидание подтверждения пользователя"
        ├── <p>  "Будут собраны следующие данные:"
        ├── .data-list
        │   ├── <li> Telegram ID, имя, @username, аватар
        │   ├── <li> IP-адрес и геолокация
        │   ├── <li> Браузер, операционная система, устройство
        │   ├── <li> HTTP-заголовки запроса
        │   ├── <li> Разрешение экрана и временная зона
        │   ├── <li> Отпечаток браузера (Canvas + Audio API)
        │   └── <li> WebRTC утечки IP-адресов
        ├── <p class="consent-tos">  "Нажимая кнопку ниже, вы ... [Условиями использования]"
        └── <form method="POST" action="/scan/{{ token }}/consent">
            └── <button type="submit" class="btn-accept">[ ПРИНЯТЬ И ПРОДОЛЖИТЬ ]</button>
```

Commit: `feat: consent screen template`

---

### Task 8 — dashboard.html

**КРИТИЧЕСКИ ВАЖНЫЕ элементы** — без них scanner.js не будет работать:

| id элемента | Вкладка | Что отображает |
|-------------|---------|---------------|
| `webrtc-result` | СЕТЬ | WebRTC утечки (заполняет JS) |
| `screen-res` | УСТРОЙСТВО | Разрешение экрана (заполняет JS) |
| `timezone` | УСТРОЙСТВО | Временная зона (заполняет JS) |
| `color-depth` | УСТРОЙСТВО | Глубина цвета (заполняет JS) |
| `fp-hash` | УСТРОЙСТВО | Хэш отпечатка браузера (заполняет JS) |
| `fp-score` | УСТРОЙСТВО | Уникальность отпечатка % (заполняет JS) |

**КРИТИЧЕСКИ ВАЖНЫЕ JS-переменная и скрипт:**
```html
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
```
Оба тега `<script>` должны быть перед `</body>`.

**Jinja2 переменные из контекста** (все передаются из `web/app.py`):

```
token           — строка UUID
session         — dict с ключами: tg_id, tg_username, tg_first_name, tg_last_name,
                  tg_lang, tg_photo_url, ip, geo_country, geo_city, geo_isp, geo_proxy,
                  consent_at, created_at
ua_info         — dict с ключами: browser, browser_version, os, os_version, device_type
headers_raw     — dict HTTP заголовков
screen          — dict или {} (если JS ещё не отправил)
webrtc          — list или [] (если JS ещё не отправил)
```

**Структура вкладок:**

```
[ ПРОФИЛЬ ] [ СЕТЬ ] [ УСТРОЙСТВО ] [ ЗАГОЛОВКИ ]

Вкладка ПРОФИЛЬ:
- Аватар: <img> если session.tg_photo_url, иначе .avatar-placeholder с "👤"
- Имя: session.tg_first_name + session.tg_last_name
- @username (если есть)
- Бейдж "✓ VERIFIED SCAN"
- Карточки: Telegram ID, Username, Язык, Дата скана

Вкладка СЕТЬ:
- Большая карточка: IP-адрес (session.ip) — цвет pink
- Сетка 2x2: Страна, Город, Провайдер, VPN/Proxy индикатор
- Карточка: WebRTC утечка — id="webrtc-result", начальный текст класс .collecting

Вкладка УСТРОЙСТВО:
- Карточки: Браузер (ua_info), ОС (ua_info), Тип устройства (ua_info)
- Карточки с id для JS: screen-res, timezone, color-depth — начальный текст класс .collecting
- Карточка: Отпечаток браузера — id="fp-hash", класс .collecting
- Карточка: Уникальность — id="fp-score", класс .collecting

Вкладка ЗАГОЛОВКИ:
- .headers-table со всеми headers_raw.items()
- Если пусто: "Заголовки не получены"
```

**id вкладок** (нужны для switchTab):
- `tab-profile` (активная по умолчанию)
- `tab-network`
- `tab-device`
- `tab-headers`

**onclick кнопок:**
```html
<button class="tab-btn active" onclick="switchTab('profile')">[ ПРОФИЛЬ ]</button>
<button class="tab-btn" onclick="switchTab('network')">[ СЕТЬ ]</button>
<button class="tab-btn" onclick="switchTab('device')">[ УСТРОЙСТВО ]</button>
<button class="tab-btn" onclick="switchTab('headers')">[ ЗАГОЛОВКИ ]</button>
```

Commit: `feat: dashboard template with 4 tabs`

---

### Task 9 — legal.html

Страница с классом `.legal-page`. Обязательные разделы `<h2>`:
1. Назначение сервиса
2. Согласие на сбор данных
3. Какие данные собираются (перечислить все 7 типов из consent.html)
4. Ограничение ответственности
5. Передача данных третьим лицам (упомянуть ip-api.com)
6. Хранение данных
7. Ограничения использования
8. Контакт: `<a href="mailto:apolonov.osi1@gmail.com">apolonov.osi1@gmail.com</a>`

Кнопка/ссылка "← Вернуться назад": `<a href="javascript:history.back()" class="back-link">`

Commit: `feat: legal / terms of service page`

---

### Task 10 — scanner.js

**Назначение:** собирает данные на стороне клиента, обновляет DOM, отправляет данные на сервер.

**Точка входа:** читает `window.SCAN_TOKEN` (задан в dashboard.html как `const SCAN_TOKEN`).
Запускается через `DOMContentLoaded` или немедленно если документ уже загружен.

**Функции которые нужно реализовать:**

#### 1. `collectScreen() -> object`
Возвращает объект:
```js
{
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
}
```

#### 2. `canvasFingerprint() -> string`
- Создать `<canvas>` 200x40
- Нарисовать текст с шрифтом "JetBrains Mono, monospace", цвет `#00ff88`
- Нарисовать прямоугольник цвет `#ff0066`
- Вернуть `canvas.toDataURL().slice(-80)`
- При ошибке: вернуть `'unavailable'`

#### 3. `audioFingerprint() -> Promise<string>`
- Создать `AudioContext` → `OscillatorNode` (type: 'triangle', freq: 10000) → `AnalyserNode` → `GainNode` (gain 0)
- Подождать 100ms, взять Float32Array из analyser, суммировать abs значений
- Вернуть результат как строку с 4 знаками
- При ошибке: вернуть `'unavailable'`

#### 4. `detectWebRTCLeaks() -> Promise<string[]>`
- `new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] })`
- `createDataChannel('')` + `createOffer()` + `setLocalDescription()`
- Слушать `onicecandidate`, извлекать IP regex `(\d{1,3}(\.\d{1,3}){3})`
- Таймаут 4000ms — resolve с найденными IP
- При ошибке: resolve с `[]`

#### 5. `djb2(str) -> string`
Хэш-функция для fingerprint:
```js
function djb2(str) {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i);
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}
```

#### 6. `calculateScore(screen, canvasHash, audioHash) -> number`
Возвращает 0–100. Логика начисления очков (примерная, max=10):
- Нестандартное разрешение (не из топ-5 популярных) → +2
- Canvas hash доступен → +3
- Audio hash доступен → +2
- Timezone offset ≠ 0 → +1
- Язык не `en*` → +1
- hardwareConcurrency > 4 → +1

Итого: `Math.round((score / 10) * 100)`

#### 7. Обновление DOM

```js
function setEl(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}
```

После сбора данных:
```js
// screen
setEl('screen-res', `${screen.width} × ${screen.height} (×${screen.pixelRatio})`);
setEl('timezone', screen.timezone || '—');
setEl('color-depth', `${screen.colorDepth}-bit`);

// webrtc
if (ips.length === 0) {
  setEl('webrtc-result', '<span class="status-ok">Утечек не обнаружено ✓</span>');
} else {
  setEl('webrtc-result', `<span class="status-warn">⚠ Обнаружены IP: ${ips.join(', ')}</span>`);
}

// fingerprint
setEl('fp-hash', `<span style="font-size:12px;word-break:break-all;">${fpHash}</span>`);
const color = score >= 70 ? 'var(--pink)' : score >= 40 ? 'var(--blue)' : 'var(--green)';
setEl('fp-score', `<span style="color:${color}">${score}%</span> <span style="font-size:11px;color:var(--muted);">(оценка уникальности)</span>`);
```

#### 8. POST на сервер

```js
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
```

Ошибку fetch поглощать (try/catch без rethrow) — не ломать UI при сетевой проблеме.

**Порядок выполнения в `run()`:**
1. `collectScreen()` → обновить DOM screen сразу
2. `Promise.all([canvasFingerprint(), audioFingerprint(), detectWebRTCLeaks()])` — параллельно
3. Обновить DOM webrtc + fingerprint
4. POST на сервер

Commit: `feat: client-side scanner (WebRTC, fingerprint, screen)`

---

## Финальная проверка

Открыть `web/templates/dashboard.html` и убедиться что присутствуют все 6 id:
```bash
grep -E 'id="(webrtc-result|screen-res|timezone|color-depth|fp-hash|fp-score)"' web/templates/dashboard.html
```
Должны найтись все 6 совпадений.

Убедиться что `SCAN_TOKEN` и `scanner.js` подключены:
```bash
grep "SCAN_TOKEN" web/templates/dashboard.html
grep "scanner.js" web/templates/dashboard.html
```

---

## Запрещено

- Трогать любые `.py` файлы
- Трогать `tests/`
- Трогать `requirements.txt`
- Создавать `main.py`
- Изменять схему базы данных
