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
