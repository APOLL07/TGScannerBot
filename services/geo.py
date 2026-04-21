import httpx

async def get_ip_info(ip: str) -> dict:
    if ip in ("127.0.0.1", "::1", "localhost"):
        return {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"https://ipapi.co/{ip}/json/",
                headers={"User-Agent": "TGScanner/1.0"},
            )
            data = resp.json()
            if not data.get("error"):
                return {
                    "country": data.get("country_name", ""),
                    "region": data.get("region", ""),
                    "city": data.get("city", ""),
                    "isp": data.get("org", ""),
                    "org": data.get("org", ""),
                    "asn": data.get("asn", ""),
                    "proxy": False,   # ipapi.co free tier does not provide proxy detection
                    "hosting": False,
                }
    except Exception:
        pass
    return {}
