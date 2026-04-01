"""
app/domain/scanners/base_scanner.py
Abstract base class cho tất cả scanners.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseScanner(ABC):
    scanner_name: str = "base"

    @abstractmethod
    async def scan(self, target: str) -> Dict[str, Any]:
        """Perform scan and return structured result dict."""

    def _ok(self, target: str, **extra: Any) -> Dict[str, Any]:
        return {"target": target, "scanner": self.scanner_name, "status": "ok", **extra}

    def _error(self, target: str, message: str) -> Dict[str, Any]:
        return {
            "target":  target,
            "scanner": self.scanner_name,
            "status":  "error",
            "error":   message,
        }