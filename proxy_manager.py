import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Proxy:
    """Represents a single proxy with metadata"""
    ip: str
    port: int
    http: bool = False
    https: bool = False
    speed: float = 0.0
    location: str = "Unknown"
    last_checked: float = 0.0
    source: str = "unknown"
    failed_count: int = 0
    
    def __hash__(self):
        return hash(f"{self.ip}:{self.port}")
    
    def __eq__(self, other):
        if isinstance(other, Proxy):
            return self.ip == other.ip and self.port == other.port
        return False
    
    @property
    def address(self) -> str:
        """Return IP:Port string"""
        return f"{self.ip}:{self.port}"
    
    @property
    def is_working(self) -> bool:
        """Return True if proxy works with HTTP or HTTPS"""
        return self.http or self.https
    
    @property
    def protocols(self) -> str:
        """Return protocol string (HTTP/HTTPS/BOTH)"""
        if self.http and self.https:
            return "BOTH"
        elif self.http:
            return "HTTP"
        elif self.https:
            return "HTTPS"
        return "NONE"


class ProxyManager:
    """Thread-safe proxy storage and management"""
    
    def __init__(self, state_file: str = "working_proxies.json"):
        self.state_file = Path(state_file)
        self.proxies: Dict[str, Proxy] = {}  # key: "ip:port"
        self.lock = threading.RLock()
        
        # Stats
        self.total_scraped = 0
        self.total_validated_http = 0
        self.total_validated_https = 0
        self.total_failed = 0
        self.currently_testing = 0
        
        # Timing
        self.start_time = time.time()
        self.last_full_scrape = 0.0
        
        # Load existing state
        self.load_from_file()
    
    def load_from_file(self):
        """Load proxies from JSON state file"""
        with self.lock:
            if self.state_file.exists():
                try:
                    with open(self.state_file, 'r') as f:
                        data = json.load(f)
                    
                    if isinstance(data, dict):
                        for key, proxy_dict in data.items():
                            proxy = Proxy(**proxy_dict)
                            self.proxies[key] = proxy
                except Exception:
                    pass
    
    def save_to_file(self):
        """Save proxies to JSON state file"""
        with self.lock:
            try:
                data = {addr: asdict(proxy) for addr, proxy in self.proxies.items()}
                with open(self.state_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
    
    def add_proxy(self, ip: str, port: int, source: str = "unknown") -> Proxy:
        """Add or update a proxy in the manager"""
        with self.lock:
            addr = f"{ip}:{port}"
            if addr in self.proxies:
                # Update existing
                self.proxies[addr].source = source
            else:
                # Add new
                proxy = Proxy(ip=ip, port=port, source=source, last_checked=time.time())
                self.proxies[addr] = proxy
                self.total_scraped += 1
            return self.proxies[addr]
    
    def validate_http(self, ip: str, port: int, speed: float, location: str = "Unknown"):
        """Mark proxy as validated for HTTP"""
        with self.lock:
            addr = f"{ip}:{port}"
            if addr in self.proxies:
                self.proxies[addr].http = True
                self.proxies[addr].speed = speed
                self.proxies[addr].location = location
                self.proxies[addr].last_checked = time.time()
                self.proxies[addr].failed_count = 0
                self.total_validated_http += 1
    
    def validate_https(self, ip: str, port: int, speed: float, location: str = "Unknown"):
        """Mark proxy as validated for HTTPS"""
        with self.lock:
            addr = f"{ip}:{port}"
            if addr in self.proxies:
                self.proxies[addr].https = True
                self.proxies[addr].speed = speed
                self.proxies[addr].location = location
                self.proxies[addr].last_checked = time.time()
                self.proxies[addr].failed_count = 0
                self.total_validated_https += 1
    
    def mark_failed(self, ip: str, port: int):
        """Mark proxy as failed and increment fail count"""
        with self.lock:
            addr = f"{ip}:{port}"
            if addr in self.proxies:
                self.proxies[addr].failed_count += 1
                if self.proxies[addr].failed_count >= 3:
                    # Remove after 3 consecutive failures
                    del self.proxies[addr]
                self.total_failed += 1
    
    def remove_proxy(self, ip: str, port: int):
        """Remove a proxy from manager"""
        with self.lock:
            addr = f"{ip}:{port}"
            if addr in self.proxies:
                del self.proxies[addr]
    
    def get_working(self, protocol: str = "ANY") -> List[Proxy]:
        """Get all working proxies, optionally filtered by protocol"""
        with self.lock:
            result = []
            for proxy in self.proxies.values():
                if protocol == "ANY" and proxy.is_working:
                    result.append(proxy)
                elif protocol == "HTTP" and proxy.http:
                    result.append(proxy)
                elif protocol == "HTTPS" and proxy.https:
                    result.append(proxy)
                elif protocol == "BOTH" and proxy.http and proxy.https:
                    result.append(proxy)
            
            # Sort by speed (fastest first)
            return sorted(result, key=lambda p: p.speed)
    
    def get_top_proxies(self, count: int = 10) -> List[Proxy]:
        """Get top N working proxies by speed"""
        working = self.get_working("ANY")
        return working[:count]
    
    def get_proxy(self, ip: str, port: int) -> Optional[Proxy]:
        """Get a specific proxy"""
        with self.lock:
            addr = f"{ip}:{port}"
            return self.proxies.get(addr)
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        with self.lock:
            working_count = len([p for p in self.proxies.values() if p.is_working])
            http_only = len([p for p in self.proxies.values() if p.http and not p.https])
            https_only = len([p for p in self.proxies.values() if p.https and not p.http])
            both = len([p for p in self.proxies.values() if p.http and p.https])
            
            uptime = time.time() - self.start_time
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            
            return {
                "total_scraped": self.total_scraped,
                "total_validated_http": self.total_validated_http,
                "total_validated_https": self.total_validated_https,
                "total_failed": self.total_failed,
                "working_count": working_count,
                "http_only": http_only,
                "https_only": https_only,
                "both": both,
                "currently_testing": self.currently_testing,
                "total_proxies": len(self.proxies),
                "uptime_hours": hours,
                "uptime_minutes": minutes,
                "uptime_total_seconds": int(uptime),
                "last_full_scrape": self.last_full_scrape,
                "avg_speed": sum(p.speed for p in self.proxies.values() if p.speed > 0) / max(1, len([p for p in self.proxies.values() if p.speed > 0])),
            }
    
    def set_testing_count(self, count: int):
        """Set currently testing count"""
        with self.lock:
            self.currently_testing = count
    
    def set_last_scrape_time(self):
        """Update last full scrape timestamp"""
        with self.lock:
            self.last_full_scrape = time.time()
    
    def get_all_proxies(self) -> List[Proxy]:
        """Get all proxies"""
        with self.lock:
            return list(self.proxies.values())
    
    def clear_all(self):
        """Clear all proxies (for testing)"""
        with self.lock:
            self.proxies.clear()
