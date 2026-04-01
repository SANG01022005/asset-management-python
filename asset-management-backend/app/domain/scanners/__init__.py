# app/domain/scanners/__init__.py
from app.domain.scanners.base_scanner import BaseScanner
from app.domain.scanners.ip_scanner import IPScanner
from app.domain.scanners.port_scanner import PortScanner

# Conditional imports for optional scanners
try:
    from app.domain.scanners.ssl_scanner import SSLScanner
except ImportError:
    SSLScanner = None
    import logging
    logging.getLogger(__name__).warning("SSLScanner not available - pyOpenSSL not installed")

try:
    from app.domain.scanners.tech_scanner import TechScanner
except ImportError:
    TechScanner = None
    import logging
    logging.getLogger(__name__).warning("TechScanner not available - dependencies missing")

__all__ = [
    "BaseScanner",
    "IPScanner",
    "PortScanner",
    "SSLScanner",
    "TechScanner",
]