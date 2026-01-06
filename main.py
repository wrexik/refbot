"""
RefBot Main - Utilities for accessing proxy data
The complete system runs via 'python dashboard.py'
This module provides access to ProxyManager for external use.
"""

from proxy_manager import ProxyManager
import json
from pathlib import Path


def get_proxies(protocol: str = "ANY"):
    """Get working proxies for external use"""
    manager = ProxyManager()
    return manager.get_working(protocol)


def get_stats():
    """Get current statistics"""
    manager = ProxyManager()
    return manager.get_stats()


def get_top_proxies(count: int = 10):
    """Get top fastest proxies"""
    manager = ProxyManager()
    return manager.get_top_proxies(count)


def export_proxies(filename: str = "exported_proxies.txt"):
    """Export all working proxies to file"""
    manager = ProxyManager()
    proxies = manager.get_working("ANY")
    
    with open(filename, 'w') as f:
        for proxy in proxies:
            f.write(f"{proxy.address}\n")
    
    return len(proxies)


if __name__ == "__main__":
    # Just show usage - the dashboard handles everything
    print("""
╔════════════════════════════════════════════════════════════════╗
║                  RefBot - Advanced Proxy Manager               ║
╚════════════════════════════════════════════════════════════════╝

To run the complete system with scraping, validation, and loading:

    python dashboard.py

The dashboard provides:
  ✓ Real-time proxy scraping from 38 sources
  ✓ HTTP & HTTPS validation with 200 concurrent workers
  ✓ 7 information panels with live stats
  ✓ Page loading integration
  ✓ Auto-save and metrics export
  ✓ Professional Rich UI

This module (main.py) provides utility functions for external access:
  - get_proxies(protocol) - Get working proxies
  - get_stats() - Get current statistics
  - get_top_proxies(count) - Get fastest proxies
  - export_proxies(filename) - Export to file

Example usage in Python:
  from main import get_proxies, get_stats
  proxies = get_proxies("HTTPS")  # Get HTTPS-only proxies
  stats = get_stats()
  print(f"Working proxies: {stats['working_count']}")
    """)

