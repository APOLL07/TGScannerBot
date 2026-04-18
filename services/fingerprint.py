from ua_parser import user_agent_parser

def parse_user_agent(ua_string: str) -> dict:
    if not ua_string:
        return {}
    parsed = user_agent_parser.Parse(ua_string)
    browser = parsed["user_agent"]
    os_info = parsed["os"]
    device = parsed["device"]
    device_family = device.get("family") or "Other"
    return {
        "browser": browser.get("family") or "Unknown",
        "browser_version": browser.get("major") or "",
        "os": os_info.get("family") or "Unknown",
        "os_version": os_info.get("major") or "",
        "device_type": "Mobile" if device_family not in ("Other", "") else "Desktop",  # tablets also classified as Mobile per spec
        "device_brand": device.get("brand") or "",
        "device_model": device.get("model") or "",
    }
