"""RefBot Main - unified entrypoint for dashboard + API + utilities"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict

from proxy_manager import ProxyManager
from dashboard import AdvancedDashboard
from api.rest_api import run_server as run_api_server

logger = logging.getLogger(__name__)


# ---- Utility functions (backward compatible) --------------------------------

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

    with open(filename, "w") as f:
        for proxy in proxies:
            f.write(f"{proxy.address}\n")

    return len(proxies)


# ---- Entrypoint helpers ------------------------------------------------------

def _load_config(config_path: str = "config.json") -> Dict[str, Any]:
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not load config.json, using defaults: %s", exc)
        return {}


def _start_api_if_enabled(config: Dict[str, Any]) -> threading.Thread | None:
    api_cfg = config.get("api", {}) or {}
    if not api_cfg.get("enable", False):
        return None

    host = api_cfg.get("host", "0.0.0.0")
    port = int(api_cfg.get("port", 8000))
    reload = bool(api_cfg.get("reload", False))

    def _run_api():
        run_api_server(host=host, port=port, reload=reload)

    thread = threading.Thread(target=_run_api, daemon=True)
    thread.start()
    logger.info("API server starting on %s:%s (reload=%s)", host, port, reload)
    return thread


def run():
    """Start dashboard (and API if enabled in config.json)"""
    config = _load_config()
    _start_api_if_enabled(config)

    dashboard = AdvancedDashboard(config_file="config.json")
    dashboard.run()


if __name__ == "__main__":
    run()

