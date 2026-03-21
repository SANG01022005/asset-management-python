"""
tests/test_ip_scanner.py
Unit tests cho IPScanner — toàn bộ network calls được mock.
"""
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.domain.scanners.ip_scanner import IPScanner

GOOGLE = {
    "status": "success", "query": "8.8.8.8",
    "country": "United States", "countryCode": "US",
    "region": "VA", "regionName": "Virginia", "city": "Ashburn",
    "zip": "20149", "lat": 39.03, "lon": -77.5,
    "timezone": "America/New_York", "isp": "Google LLC",
    "org": "Google LLC", "as": "AS15169", "asname": "GOOGLE",
}

HCM = {
    "status": "success", "query": "118.69.226.234",
    "country": "Vietnam", "countryCode": "VN",
    "city": "Ho Chi Minh City", "lat": 10.8231, "lon": 106.6297,
    "timezone": "Asia/Ho_Chi_Minh", "isp": "VNPT", "org": "VNPT",
    "as": "AS45899", "asname": "VNPT-AS-VN",
}


def _mock(api_response, resolve_to=None):
    scanner = IPScanner()
    scanner._resolve      = AsyncMock(return_value=resolve_to or api_response.get("query"))
    scanner._fetch_ip_api = MagicMock(return_value=api_response)
    return scanner


class TestIPScannerHappyPath:

    @pytest.mark.asyncio
    async def test_returns_ok_status(self):
        result = await _mock(GOOGLE).scan("8.8.8.8")
        assert result["status"]  == "ok"
        assert result["scanner"] == "ip_scanner"

    @pytest.mark.asyncio
    async def test_echoes_target(self):
        assert (await _mock(GOOGLE).scan("8.8.8.8"))["target"] == "8.8.8.8"

    @pytest.mark.asyncio
    async def test_geolocation_fields(self):
        geo = (await _mock(GOOGLE).scan("8.8.8.8"))["geolocation"]
        assert geo["country"]      == "United States"
        assert geo["country_code"] == "US"
        assert geo["city"]         == "Ashburn"
        assert geo["latitude"]     == 39.03
        assert geo["longitude"]    == -77.5

    @pytest.mark.asyncio
    async def test_asn_fields(self):
        asn = (await _mock(GOOGLE).scan("8.8.8.8"))["asn"]
        assert asn["number"]       == "AS15169"
        assert asn["name"]         == "GOOGLE"
        assert asn["organisation"] == "Google LLC"

    @pytest.mark.asyncio
    async def test_vietnamese_ip(self):
        result = await _mock(HCM).scan("118.69.226.234")
        assert result["geolocation"]["country"] == "Vietnam"
        assert result["asn"]["number"]          == "AS45899"

    @pytest.mark.asyncio
    async def test_hostname_resolved(self):
        scanner = _mock(GOOGLE, resolve_to="8.8.8.8")
        await scanner.scan("dns.google")
        scanner._resolve.assert_awaited_once_with("dns.google")


class TestIPScannerErrors:

    @pytest.mark.asyncio
    async def test_unresolvable_host(self):
        scanner          = IPScanner()
        scanner._resolve = AsyncMock(return_value=None)
        result           = await scanner.scan("not-real.invalid")
        assert result["status"] == "error"
        assert "resolve" in result["error"].lower() or "valid IP" in result["error"]

    @pytest.mark.asyncio
    async def test_api_fail_status(self):
        fail = {"status": "fail", "message": "reserved range", "query": "192.168.1.1"}
        result = await _mock(fail, resolve_to="192.168.1.1").scan("192.168.1.1")
        assert result["status"] == "error"
        assert "reserved range" in result["error"]

    @pytest.mark.asyncio
    async def test_network_exception(self):
        scanner               = IPScanner()
        scanner._resolve      = AsyncMock(return_value="8.8.8.8")
        scanner._fetch_ip_api = MagicMock(side_effect=Exception("Connection refused"))
        result = await scanner.scan("8.8.8.8")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_missing_fields_graceful(self):
        sparse  = {"status": "success", "query": "1.2.3.4"}
        result  = await _mock(sparse, resolve_to="1.2.3.4").scan("1.2.3.4")
        assert result["status"] == "ok"
        assert result["geolocation"]["country"] is None
        assert result["asn"]["number"]          is None


class TestBaseContract:

    def test_scanner_name(self):
        assert IPScanner.scanner_name == "ip_scanner"

    @pytest.mark.asyncio
    async def test_ok_envelope_keys(self):
        result = await _mock(GOOGLE).scan("8.8.8.8")
        for k in ("target", "scanner", "status", "geolocation", "asn"):
            assert k in result

    @pytest.mark.asyncio
    async def test_error_envelope_keys(self):
        scanner          = IPScanner()
        scanner._resolve = AsyncMock(return_value=None)
        result           = await scanner.scan("bad")
        for k in ("target", "scanner", "status", "error"):
            assert k in result