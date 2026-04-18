import httpx

async def get_ip_info(ip: str) -> dict:
    if ip in ("127.0.0.1", "::1", "localhost"):
        return {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",  # ip-api.com requires a paid plan for HTTPS; plain HTTP is intentional
                params={"fields": "status,country,regionName,city,isp,org,as,proxy,hosting"},
            )
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country", ""),
                    "region": data.get("regionName", ""),
                    "city": data.get("city", ""),
                    "isp": data.get("isp", ""),
                    "org": data.get("org", ""),
                    "asn": data.get("as", ""),
                    "proxy": data.get("proxy", False),
                    "hosting": data.get("hosting", False),
                }
    except Exception:
        pass
    return {}
