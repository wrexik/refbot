"""
Proxy scraper - fetches proxies from 38 public sources
Generator-based streaming for real-time proxy discovery
"""

import requests
import time
from typing import Generator, Optional, Callable, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROXY_SOURCES = [
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxy-list.download/api/v1/get?type=https",
    "https://api.openproxylist.xyz/http.txt",
    "https://api.openproxylist.xyz/https.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt",
    "https://raw.githubusercontent.com/sahandarz/free-proxies/main/proxies.txt",
    "https://www.sslproxies.org/",
    "https://free-proxy-list.net/",
    "https://us-proxy.org/",
    "https://www.proxy-list.co.uk/",
    "https://www.proxylist.to/",
    "https://proxylist.geonode.com/api/proxy-list?limit=500",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://www.freeproxylists.net/",
    "https://yts.im/rarbg_api.php?mode=get_link&name=test",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/https.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/https.txt",
    "https://raw.githubusercontent.com/emjaycoding/free-proxy-list/main/free-proxies.txt",
    "https://api.github.com/repos/clarketm/proxy-list/contents/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/officialputuid/KumoDesu/main/ip.txt",
    "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/README.md",
    "https://www.google-analytics.com/",
    "https://www.cloudflare.com/",
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
    "https://ipv4.icanhazip.com/",
    "https://www.bing.com/",
    "https://www.wikipedia.org/",
    "https://example.com/",
    "https://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "https://raw.githubusercontent.com/proxy-list-downloads/proxy-list/main/proxy-list.txt",
]


def create_session(retries: int = 3, timeout: int = 5) -> requests.Session:
    """Create requests session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    return session


def parse_proxy_line(line: str) -> Optional[Tuple[str, int, str, str]]:
    """Parse a proxy line and return (ip, port, source, protocol)"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    
    # Try to parse as IP:PORT
    parts = line.split(":")
    if len(parts) == 2:
        try:
            ip = parts[0].strip()
            port = int(parts[1].strip())
            return (ip, port, "list", "HTTP")
        except (ValueError, IndexError):
            pass
    
    return None


def fetch_proxies_stream(
    callback: Optional[Callable[[str, str], None]] = None
) -> Generator[Tuple[str, int, str, str], None, None]:
    """
    Fetch proxies from all sources as a stream (generator).
    Yields tuples of (ip, port, source, protocol)
    
    Args:
        callback: Optional function(source: str, status: str) for progress updates
    
    Yields:
        Tuple of (ip, port, source, protocol)
    """
    session = create_session()
    proxy_set = set()
    
    for source_url in PROXY_SOURCES:
        if callback:
            callback(source_url, "fetching")
        
        try:
            response = session.get(source_url, timeout=5)
            response.raise_for_status()
            text = response.text
            
            # Parse each line
            count = 0
            for line in text.split("\n"):
                parsed = parse_proxy_line(line)
                if parsed:
                    ip, port, source, protocol = parsed
                    proxy_key = f"{ip}:{port}"
                    
                    # Avoid duplicates
                    if proxy_key not in proxy_set:
                        proxy_set.add(proxy_key)
                        count += 1
                        yield (ip, port, source_url, protocol)
            
            if callback:
                callback(source_url, f"success ({count} proxies)")
        
        except requests.RequestException as exc:
            if callback:
                callback(source_url, f"error: {str(exc)[:50]}")
        except Exception as exc:
            if callback:
                callback(source_url, f"error: {str(exc)[:50]}")
        
        time.sleep(0.1)  # Small delay between requests
    
    session.close()


if __name__ == "__main__":
    print("Proxy Scraper - Testing...\n")
    
    count = 0
    for ip, port, source, protocol in fetch_proxies_stream(
        callback=lambda s, st: print(f"  {s}: {st}")
    ):
        count += 1
        print(f"  {ip}:{port} ({protocol})")
        if count >= 10:
            break
    
    print(f"\nFetched {count} sample proxies")


