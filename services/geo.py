import httpx

async def get_ip_info(ip: str) -> dict:
    if ip in ("127.0.0.1", "::1", "localhost"):
        return {}
    try:
        # ip-api.com: free, accurate, supports proxy/hosting detection
        # fields: status,country,regionName,city,isp,org,proxy,hosting
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,regionName,city,isp,org,proxy,hosting"},
            )
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country", ""),
                    "region": data.get("regionName", ""),
                    "city": data.get("city", ""),
                    "isp": data.get("isp", "") or data.get("org", ""),
                    "org": data.get("org", ""),
                    "proxy": bool(data.get("proxy") or data.get("hosting")),
                    "hosting": bool(data.get("hosting")),
                }
    except Exception:
        pass
    return {}
