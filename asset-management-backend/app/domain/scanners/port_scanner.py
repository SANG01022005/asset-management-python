"""
app/domain/scanners/port_scanner.py
TCP port scanner — CHỈ private/loopback IPs (security policy).
"""
import asyncio
import ipaddress
from typing import Any, Dict, List, Optional, Tuple

from app.domain.scanners.base_scanner import BaseScanner

_DEFAULT_PORTS: Tuple[int, ...] = (
    21, 22, 23, 25, 53, 80, 110, 143,
    443, 445, 3306, 5432, 6379, 8080, 8443, 27017,
)
_CONCURRENCY    = 100
_CONNECT_TIMEOUT = 1.0

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

_WELL_KNOWN: Dict[int, str] = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb",
    3306: "mysql", 5432: "postgresql", 6379: "redis",
    8080: "http-alt", 8443: "https-alt", 27017: "mongodb",
}


class PortScanner(BaseScanner):
    scanner_name = "port_scanner"

    def __init__(self, ports: Optional[List[int]] = None, timeout: float = _CONNECT_TIMEOUT):
        self._ports   = list(ports) if ports else list(_DEFAULT_PORTS)
        self._timeout = timeout

    async def scan(self, target: str) -> Dict[str, Any]:
        try:
            addr = ipaddress.ip_address(target)
        except ValueError:
            return self._error(target, f"'{target}' is not a valid IP address.")

        if not self.is_local_ip(addr):
            return self._error(
                target,
                f"Security policy violation: '{target}' is a public IP address. "
                "PortScanner only operates on private/loopback ranges.",
            )

        open_ports = await self._sweep(str(addr))
        return self._ok(target, ip=str(addr), scanned_ports=len(self._ports), open_ports=open_ports)

    @staticmethod
    def is_local_ip(addr) -> bool:
        if addr.is_loopback or addr.is_private:
            return True
        if isinstance(addr, ipaddress.IPv4Address):
            return any(addr in net for net in _PRIVATE_NETWORKS)
        return False

    async def _sweep(self, ip: str) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def probe(port: int) -> Optional[Dict[str, Any]]:
            async with semaphore:
                try:
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port), timeout=self._timeout)
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
                    return {"port": port, "service": self._service_name(port)}
                except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                    return None

        results    = await asyncio.gather(*[probe(p) for p in self._ports])
        open_ports = [r for r in results if r is not None]
        open_ports.sort(key=lambda r: r["port"])
        return open_ports

    @classmethod
    def _service_name(cls, port: int) -> str:
        return _WELL_KNOWN.get(port, "unknown")