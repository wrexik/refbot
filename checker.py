"""
Proxy checker - validates HTTP and HTTPS support for proxies
Returns detailed validation results with speed metrics
"""

import requests
import time
from typing import Dict, Optional


HTTP_TEST_URL = "http://httpbin.org/ip"
HTTPS_TEST_URL = "https://httpbin.org/ip"


def validate_http_proxy(ip: str, port: int, timeout: int = 8) -> Dict:
    """
    Validate if proxy supports HTTP requests
    
    Args:
        ip: Proxy IP address
        port: Proxy port
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with keys:
        - success: bool - Whether validation passed
        - speed: float - Response time in seconds (0 if failed)
        - location: str - Approximate location from response
        - error: str - Error message if failed
    """
    proxy_addr = f"http://{ip}:{port}"
    proxies = {"http": proxy_addr, "https": proxy_addr}
    
    try:
        start = time.perf_counter()
        response = requests.get(
            HTTP_TEST_URL,
            proxies=proxies,
            timeout=timeout,
            verify=False,
        )
        elapsed = time.perf_counter() - start
        
        if response.status_code == 200:
            try:
                data = response.json()
                location = data.get("origin", "Unknown")
            except:
                location = "Unknown"
            
            return {
                "success": True,
                "speed": elapsed,
                "location": location,
                "error": None,
            }
        else:
            return {
                "success": False,
                "speed": 0,
                "location": None,
                "error": f"HTTP {response.status_code}",
            }
    
    except requests.Timeout:
        return {
            "success": False,
            "speed": 0,
            "location": None,
            "error": "Timeout",
        }
    except requests.ConnectionError:
        return {
            "success": False,
            "speed": 0,
            "location": None,
            "error": "Connection failed",
        }
    except Exception as exc:
        return {
            "success": False,
            "speed": 0,
            "location": None,
            "error": str(exc)[:50],
        }


def validate_https_proxy(ip: str, port: int, timeout: int = 8) -> Dict:
    """
    Validate if proxy supports HTTPS requests
    
    Args:
        ip: Proxy IP address
        port: Proxy port
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with keys:
        - success: bool - Whether validation passed
        - speed: float - Response time in seconds (0 if failed)
        - location: str - Approximate location from response
        - error: str - Error message if failed
    """
    proxy_addr = f"http://{ip}:{port}"
    proxies = {"http": proxy_addr, "https": proxy_addr}
    
    try:
        start = time.perf_counter()
        response = requests.get(
            HTTPS_TEST_URL,
            proxies=proxies,
            timeout=timeout,
            verify=False,
        )
        elapsed = time.perf_counter() - start
        
        if response.status_code == 200:
            try:
                data = response.json()
                location = data.get("origin", "Unknown")
            except:
                location = "Unknown"
            
            return {
                "success": True,
                "speed": elapsed,
                "location": location,
                "error": None,
            }
        else:
            return {
                "success": False,
                "speed": 0,
                "location": None,
                "error": f"HTTP {response.status_code}",
            }
    
    except requests.Timeout:
        return {
            "success": False,
            "speed": 0,
            "location": None,
            "error": "Timeout",
        }
    except requests.ConnectionError:
        return {
            "success": False,
            "speed": 0,
            "location": None,
            "error": "Connection failed",
        }
    except Exception as exc:
        return {
            "success": False,
            "speed": 0,
            "location": None,
            "error": str(exc)[:50],
        }


if __name__ == "__main__":
    print("Proxy Checker - Testing with sample proxies\n")
    
    # Test with a known working proxy (example)
    test_proxies = [
        ("1.1.1.1", 8080),
        ("8.8.8.8", 8080),
    ]
    
    for ip, port in test_proxies:
        print(f"Testing {ip}:{port}")
        
        http_result = validate_http_proxy(ip, port)
        print(f"  HTTP: {http_result}")
        
        https_result = validate_https_proxy(ip, port)
        print(f"  HTTPS: {https_result}\n")
