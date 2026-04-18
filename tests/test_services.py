import re
from unittest.mock import AsyncMock, MagicMock, patch
from services.token import generate_token
from services.fingerprint import parse_user_agent
from services.geo import get_ip_info

def test_generate_token_is_uuid4():
    token = generate_token()
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", token
    )

def test_generate_token_unique():
    assert generate_token() != generate_token()

def test_parse_chrome_windows():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    result = parse_user_agent(ua)
    assert result["browser"] == "Chrome"
    assert result["browser_version"] == "124"
    assert result["os"] == "Windows"
    assert result["device_type"] == "Desktop"

def test_parse_mobile_ua():
    ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
    result = parse_user_agent(ua)
    assert result["device_type"] == "Mobile"

def test_parse_empty_ua():
    assert parse_user_agent("") == {}

async def test_get_ip_info_localhost_returns_empty():
    assert await get_ip_info("127.0.0.1") == {}

async def test_get_ip_info_success():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "status": "success", "country": "Russia", "regionName": "Moscow",
        "city": "Moscow", "isp": "MTS", "org": "MTS PJSC",
        "as": "AS8359", "proxy": False, "hosting": False,
    }
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        result = await get_ip_info("1.2.3.4")
    assert result["country"] == "Russia"
    assert result["proxy"] is False

async def test_get_ip_info_exception_returns_empty():
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("timeout"))
        result = await get_ip_info("1.2.3.4")
    assert result == {}

async def test_get_ip_info_fail_status_returns_empty():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "fail", "message": "invalid query"}
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        result = await get_ip_info("999.999.999.999")
    assert result == {}

async def test_get_ip_info_ipv6_loopback_returns_empty():
    assert await get_ip_info("::1") == {}
