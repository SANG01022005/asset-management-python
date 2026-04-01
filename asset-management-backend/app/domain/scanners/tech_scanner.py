# app/domain/scanners/tech_scanner.py
"""
app/domain/scanners/tech_scanner.py

Technology Detection Scanner
"""
import asyncio
import re
from typing import Any, Dict, List

import httpx

from app.domain.scanners.base_scanner import BaseScanner


class TechScanner(BaseScanner):
    """Technology detection scanner for web applications"""
    
    scanner_name = "tech_scanner"
    
    # Common technology patterns
    TECH_PATTERNS = {
        "nginx": {
            "pattern": r"nginx[/\s]*([\d.]+)?",
            "category": "Web Server",
            "header": "server"
        },
        "apache": {
            "pattern": r"Apache[/\s]*([\d.]+)?",
            "category": "Web Server",
            "header": "server"
        },
        "cloudflare": {
            "pattern": r"cloudflare",
            "category": "CDN",
            "header": "server"
        },
        "react": {
            "pattern": r"react",
            "category": "JavaScript Framework",
            "meta": "generator"
        },
        "vue": {
            "pattern": r"vue",
            "category": "JavaScript Framework",
            "meta": "generator"
        },
        "angular": {
            "pattern": r"angular",
            "category": "JavaScript Framework",
            "meta": "generator"
        },
        "express": {
            "pattern": r"express",
            "category": "Web Framework",
            "header": "x-powered-by"
        },
        "django": {
            "pattern": r"django",
            "category": "Web Framework",
            "header": "server"
        },
        "rails": {
            "pattern": r"rails",
            "category": "Web Framework",
            "header": "server"
        },
        "wordpress": {
            "pattern": r"wordpress",
            "category": "CMS",
            "meta": "generator"
        }
    }
    
    async def scan(self, target: str) -> Dict[str, Any]:
        """Detect technologies used by a web application"""
        try:
            # Try HTTPS first, then HTTP
            for protocol in ["https", "http"]:
                url = f"{protocol}://{target}"
                try:
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                        response = await client.get(url)
                        technologies = await asyncio.to_thread(
                            self._detect_technologies, response.headers, response.text
                        )
                        
                        return self._ok(
                            target,
                            domain=target,
                            technologies=technologies,
                            headers=dict(response.headers),
                            meta_tags=self._extract_meta_tags(response.text),
                        )
                except (httpx.ConnectError, httpx.TimeoutException):
                    continue
                except Exception:
                    continue
            
            return self._error(target, "No web server responded")
            
        except Exception as exc:
            return self._error(target, f"Technology detection failed: {str(exc)}")
    
    def _detect_technologies(self, headers: Dict, body: str) -> List[Dict]:
        """Detect technologies from headers and body"""
        technologies = []
        
        for tech_name, tech_info in self.TECH_PATTERNS.items():
            confidence = 0
            version = None
            
            # Check headers (highest confidence)
            if "header" in tech_info:
                header_name = tech_info["header"]
                if header_name in headers:
                    header_value = headers[header_name].lower()
                    match = re.search(tech_info["pattern"], header_value, re.IGNORECASE)
                    if match:
                        confidence = 100
                        version = match.group(1) if match.groups() else None
            
            # Check meta tags (medium confidence)
            if confidence == 0 and "meta" in tech_info:
                meta_pattern = tech_info["pattern"]
                if re.search(meta_pattern, body, re.IGNORECASE):
                    confidence = 80
            
            # Check body (lowest confidence)
            if confidence == 0:
                if re.search(tech_info["pattern"], body, re.IGNORECASE):
                    confidence = 60
            
            if confidence > 0:
                technologies.append({
                    "name": tech_name,
                    "category": tech_info["category"],
                    "version": version,
                    "confidence": confidence
                })
        
        # Deduplicate and sort by confidence
        unique_techs = {}
        for tech in technologies:
            if tech["name"] not in unique_techs or tech["confidence"] > unique_techs[tech["name"]]["confidence"]:
                unique_techs[tech["name"]] = tech
        
        return sorted(unique_techs.values(), key=lambda x: x["confidence"], reverse=True)
    
    def _extract_meta_tags(self, html: str) -> Dict:
        """Extract meta tags from HTML"""
        meta_tags = {}
        
        # Extract generator meta tag
        gen_match = re.search(r'<meta\s+name="generator"\s+content="([^"]+)"', html, re.IGNORECASE)
        if gen_match:
            meta_tags["generator"] = gen_match.group(1)
        
        # Extract viewport
        vp_match = re.search(r'<meta\s+name="viewport"\s+content="([^"]+)"', html, re.IGNORECASE)
        if vp_match:
            meta_tags["viewport"] = vp_match.group(1)
        
        return meta_tags