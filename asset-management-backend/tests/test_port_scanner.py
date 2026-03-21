"""
tests/test_port_scanner.py
Unit tests cho PortScanner — không có real TCP connections.
"""
import ipaddress
from unittest.mock import AsyncMock, patch

import pytest
from app.domain.scanners.port_scanner import PortScanner

FAKE_PORTS = [
    {"port": 22,  "service": "ssh"},
    {"port": 80,  "service": "http"},
    {"port": 443, "service": "https"},
]


class TestIsLocalIp:

    @pytest.mark.parametrize("ip_str", [
        "127.0.0.1", "127.255.255.255",
        "10.0.0.1", "10.255.255.254",
        "172.16.0.1", "172.31.255.254",
        "192.168.0.1", "192.168.255.254",
        "::1",
    ])
    def test_local_allowed(self, ip_str):
        assert PortScanner.is_local_ip(ipaddress.ip_address(ip_str)) is True

    @pytest.mark.parametrize("ip_str", [
        "8.8.8.8", "1.1.1.1", "93.184.216.34",
        "172.15.255.255", "172.32.0.0", "192.169.0.1", "11.0.0.1",
    ])
    def test_public_blocked(self, ip_str):
        assert PortScanner.is_local_ip(ipaddress.ip_address(ip_str)) is False

    @pytest.mark.parametrize("ip_str, expected", [
        ("10.0.0.0", True), ("10.255.255.255", True),
        ("172.16.0.0", True), ("172.31.255.255", True),
        ("192.168.0.0", True), ("192.168.255.255", True),
        ("127.0.0.0", True), ("127.255.255.255", True),
    ])
    def test_boundary_addresses(self, ip_str, expected):
        assert PortScanner.is_local_ip(ipaddress.ip_address(ip_str)) is expected


class TestPortScannerScan:

    @pytest.mark.asyncio
    async def test_local_ip_ok(self):
        scanner = PortScanner(ports=[22, 80, 443])
        with patch.object(scanner, "_sweep", new=AsyncMock(return_value=FAKE_PORTS)):
            result = await scanner.scan("192.168.1.1")
        assert result["status"]        == "ok"
        assert result["open_ports"]    == FAKE_PORTS
        assert result["scanned_ports"] == 3

    @pytest.mark.asyncio
    async def test_public_ip_rejected(self):
        scanner    = PortScanner()
        sweep_mock = AsyncMock()
        with patch.object(scanner, "_sweep", new=sweep_mock):
            result = await scanner.scan("8.8.8.8")
        assert result["status"] == "error"
        assert "Security policy violation" in result["error"]
        sweep_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_hostname_rejected(self):
        result = await PortScanner().scan("example.com")
        assert result["status"] == "error"
        assert "not a valid IP" in result["error"]

    @pytest.mark.asyncio
    async def test_loopback(self):
        scanner = PortScanner(ports=[80])
        with patch.object(scanner, "_sweep", new=AsyncMock(return_value=[])):
            result = await scanner.scan("127.0.0.1")
        assert result["status"]     == "ok"
        assert result["open_ports"] == []

    @pytest.mark.asyncio
    async def test_custom_ports(self):
        scanner = PortScanner(ports=[22, 443, 8080])
        with patch.object(scanner, "_sweep", new=AsyncMock(return_value=[])):
            result = await scanner.scan("10.0.0.1")
        assert result["scanned_ports"] == 3

    @pytest.mark.asyncio
    async def test_ports_sorted(self):
        scanner  = PortScanner(ports=[443, 22, 80])
        unsorted = [{"port": 443, "service": "https"}, {"port": 22, "service": "ssh"}, {"port": 80, "service": "http"}]
        with patch.object(scanner, "_sweep", new=AsyncMock(return_value=sorted(unsorted, key=lambda x: x["port"]))):
            result = await scanner.scan("192.168.0.1")
        ports = [p["port"] for p in result["open_ports"]]
        assert ports == sorted(ports)


class TestServiceName:

    @pytest.mark.parametrize("port, service", [
        (22, "ssh"), (80, "http"), (443, "https"),
        (3306, "mysql"), (5432, "postgresql"), (6379, "redis"),
        (27017, "mongodb"), (9999, "unknown"),
    ])
    def test_service_lookup(self, port, service):
        assert PortScanner._service_name(port) == service