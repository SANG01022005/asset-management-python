"""
app/domain/scanners/ip_scanner.py
Geolocation + ASN lookup dùng ip-api.com (free, no key required).
"""
import asyncio
import ipaddress
import socket
from typing import Any, Dict

import httpx

from app.domain.scanners.base_scanner import BaseScanner

_IP_API_URL = (
    "http://ip-api.com/json/{ip}"
    "?fields=status,message,country,countryCode,region,regionName,"
    "city,zip,lat,lon,timezone,isp,org,as,asname,query"
)


class IPScanner(BaseScanner):
    scanner_name = "ip_scanner"

    async def scan(self, target: str) -> Dict[str, Any]:
        # 1. Resolve hostname → IP
        ip = await self._resolve(target)
        if ip is None:
            return self._error(target, f"Could not resolve '{target}' to a valid IP address.")

        # 2. Fetch metadata
        try:
            data = await asyncio.to_thread(self._fetch_ip_api, ip)
        except Exception as exc:
            return self._error(target, f"ip-api.com request failed: {exc}")

        if data.get("status") != "success":
            return self._error(target, data.get("message", "ip-api.com returned non-success status."))

        # 3. Shape response
        return self._ok(
            target,
            ip=data.get("query", ip),
            geolocation={
                "country":      data.get("country"),
                "country_code": data.get("countryCode"),
                "region":       data.get("region"),
                "region_name":  data.get("regionName"),
                "city":         data.get("city"),
                "zip":          data.get("zip"),
                "latitude":     data.get("lat"),
                "longitude":    data.get("lon"),
                "timezone":     data.get("timezone"),
            },
            asn={
                "number":       data.get("as"),
                "name":         data.get("asname"),
                "organisation": data.get("org"),
                "isp":          data.get("isp"),
            },
        )

    async def _resolve(self, target: str):
        """Return canonical IP string, or None on failure."""
        try:
            ipaddress.ip_address(target)
            return target
        except ValueError:
            pass
        try:
            resolved = await asyncio.to_thread(socket.gethostbyname, target)
            ipaddress.ip_address(resolved)
            return resolved
        except (socket.gaierror, ValueError):
            return None

    @staticmethod
    def _fetch_ip_api(ip: str) -> Dict[str, Any]:
        url = _IP_API_URL.format(ip=ip)
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()