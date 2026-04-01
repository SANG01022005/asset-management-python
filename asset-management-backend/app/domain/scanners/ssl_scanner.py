# app/domain/scanners/ssl_scanner.py
"""
app/domain/scanners/ssl_scanner.py

SSL/TLS Certificate Scanner
"""
import ssl
import socket
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, Optional, List

# Try to import OpenSSL, handle if not available
try:
    import OpenSSL.crypto as crypto
    OPENSSL_AVAILABLE = True
except ImportError:
    OPENSSL_AVAILABLE = False
    crypto = None

from app.domain.scanners.base_scanner import BaseScanner


class SSLScanner(BaseScanner):
    """SSL/TLS certificate scanner for domains"""
    
    scanner_name = "ssl_scanner"
    
    def __init__(self):
        super().__init__()
        if not OPENSSL_AVAILABLE:
            import logging
            logging.getLogger(__name__).warning("OpenSSL not available, SSLScanner functionality limited")
    
    async def scan(self, target: str) -> Dict[str, Any]:
        """Scan SSL certificate for a domain"""
        if not OPENSSL_AVAILABLE:
            return self._error(target, "OpenSSL library not available. Please install pyOpenSSL.")
        
        try:
            # Run blocking SSL operations in thread pool
            result = await asyncio.to_thread(self._scan_sync, target)
            return result
        except Exception as exc:
            return self._error(target, f"SSL scan failed: {str(exc)}")
    
    def _scan_sync(self, target: str) -> Dict[str, Any]:
        """Synchronous SSL scan - runs in thread pool"""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Connect to the target
            with socket.create_connection((target, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=target) as ssock:
                    cert = ssock.getpeercert()
                    der_cert = ssock.getpeercert(binary_form=True)
                    
                    # Parse certificate if OpenSSL available
                    if OPENSSL_AVAILABLE and crypto:
                        x509 = crypto.load_certificate(crypto.FILETYPE_ASN1, der_cert)
                        grade = self._calculate_grade(x509)
                        issues = self._check_issues(x509)
                        is_self_signed = self._check_self_signed(x509)
                    else:
                        grade = "Unknown"
                        issues = []
                        is_self_signed = False
                    
                    return self._ok(
                        target,
                        certificate=self._parse_certificate(cert, is_self_signed),
                        connection=self._parse_connection(ssock),
                        grade=grade,
                        issues=issues,
                    )
        except ssl.SSLError as e:
            return self._error(target, f"SSL error: {str(e)}")
        except socket.timeout:
            return self._error(target, "Connection timeout")
        except Exception as e:
            return self._error(target, f"Connection failed: {str(e)}")
    
    def _parse_certificate(self, cert: Dict, is_self_signed: bool = False) -> Dict:
        """Parse certificate information"""
        not_after = cert.get("notAfter", "")
        return {
            "subject": self._get_subject(cert),
            "issuer": self._get_issuer(cert),
            "serial_number": cert.get("serialNumber", ""),
            "valid_from": cert.get("notBefore", ""),
            "valid_until": not_after,
            "days_until_expiry": self._calculate_days_until_expiry(not_after),
            "is_expired": self._check_is_expired(not_after),
            "is_self_signed": is_self_signed,
            "san": self._get_san(cert),
        }
    
    def _get_subject(self, cert: Dict) -> str:
        """Extract subject from certificate"""
        subject = cert.get("subject", [])
        if subject and len(subject) > 0:
            for item in subject[0]:
                if item[0] == "commonName":
                    return item[1]
        return "Unknown"
    
    def _get_issuer(self, cert: Dict) -> str:
        """Extract issuer from certificate"""
        issuer = cert.get("issuer", [])
        if issuer and len(issuer) > 0:
            for item in issuer[0]:
                if item[0] == "commonName":
                    return item[1]
        return "Unknown"
    
    def _get_san(self, cert: Dict) -> List[str]:
        """Extract Subject Alternative Names"""
        san = cert.get("subjectAltName", [])
        return [item[1] for item in san if item[0] == "DNS"]
    
    def _calculate_days_until_expiry(self, not_after: str) -> int:
        """Calculate days until certificate expires"""
        if not not_after or not isinstance(not_after, str):
            return 0
        try:
            # Handle different date formats
            # Format: "Jan  1 00:00:00 2025 GMT" or "Jan 1 00:00:00 2025 GMT"
            cleaned = re.sub(r'\s+', ' ', not_after.strip())
            expiry_date = datetime.strptime(cleaned, "%b %d %H:%M:%S %Y %Z")
            days = (expiry_date - datetime.now()).days
            return max(0, days)
        except (ValueError, TypeError):
            # Try alternative format without double spaces
            try:
                cleaned = ' '.join(not_after.split())
                expiry_date = datetime.strptime(cleaned, "%b %d %H:%M:%S %Y %Z")
                days = (expiry_date - datetime.now()).days
                return max(0, days)
            except:
                return 0
    
    def _check_is_expired(self, not_after: str) -> bool:
        """Check if certificate is expired"""
        if not not_after or not isinstance(not_after, str):
            return True
        try:
            cleaned = re.sub(r'\s+', ' ', not_after.strip())
            expiry_date = datetime.strptime(cleaned, "%b %d %H:%M:%S %Y %Z")
            return expiry_date < datetime.now()
        except (ValueError, TypeError):
            try:
                cleaned = ' '.join(not_after.split())
                expiry_date = datetime.strptime(cleaned, "%b %d %H:%M:%S %Y %Z")
                return expiry_date < datetime.now()
            except:
                return True
    
    def _check_self_signed(self, x509) -> bool:
        """Check if certificate is self-signed"""
        if not OPENSSL_AVAILABLE or not crypto:
            return False
        try:
            return x509.get_issuer() == x509.get_subject()
        except:
            return False
    
    def _parse_connection(self, ssock) -> Dict:
        """Parse connection information"""
        cipher = ssock.cipher()
        return {
            "tls_version": self._get_tls_version(ssock.version()),
            "cipher_suite": cipher[0] if cipher else "Unknown",
            "key_exchange": cipher[1] if cipher else "Unknown"
        }
    
    def _get_tls_version(self, version_str: str) -> str:
        """Map TLS version string"""
        version_map = {
            "TLSv1": "TLS 1.0",
            "TLSv1.1": "TLS 1.1",
            "TLSv1.2": "TLS 1.2",
            "TLSv1.3": "TLS 1.3"
        }
        return version_map.get(version_str, version_str)
    
    def _calculate_grade(self, x509) -> str:
        """Calculate security grade based on certificate properties"""
        if not OPENSSL_AVAILABLE or not crypto:
            return "Unknown"
        
        if self._check_self_signed(x509):
            return "F"
        
        # Check expiry
        try:
            not_after = x509.get_notAfter().decode() if hasattr(x509, 'get_notAfter') else ""
            expiry_days = self._calculate_days_until_expiry(not_after)
        except:
            expiry_days = 365
        
        if expiry_days < 30:
            return "D"
        elif expiry_days < 90:
            return "C"
        elif self._check_weak_cipher(x509):
            return "B"
        else:
            return "A"
    
    def _check_weak_cipher(self, x509) -> bool:
        """Check if certificate uses weak cipher"""
        if not OPENSSL_AVAILABLE or not crypto:
            return False
        try:
            pubkey = x509.get_pubkey()
            bits = pubkey.bits() if hasattr(pubkey, 'bits') else 2048
            return bits < 2048
        except:
            return False
    
    def _check_issues(self, x509) -> List[str]:
        """Check for security issues"""
        issues = []
        
        if not OPENSSL_AVAILABLE or not crypto:
            return issues
        
        if self._check_self_signed(x509):
            issues.append("Self-signed certificate")
        
        try:
            not_after = x509.get_notAfter().decode() if hasattr(x509, 'get_notAfter') else ""
            if self._calculate_days_until_expiry(not_after) < 30:
                issues.append("Certificate expires soon")
        except:
            pass
        
        return issues