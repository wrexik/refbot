"""RefBot Main - unified entrypoint for dashboard + API + utilities"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict

from proxy_manager import ProxyManager
from plugins.plugin_manager import PluginManager
from dashboard import AdvancedDashboard

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


def _start_api_if_enabled(config: Dict[str, Any], plugin_manager=None, proxy_manager=None) -> threading.Thread | None:
    """Start API server if enabled in config"""
    api_cfg = config.get("api", {}) or {}
    
    # Always enable API by default if not specified
    if not api_cfg.get("enable", True):
        return None

    try:
        from api.rest_api import create_app
        import uvicorn
    except ImportError:
        logger.warning("FastAPI/uvicorn not installed. API server disabled. Install with: pip install fastapi uvicorn")
        return None

    host = api_cfg.get("host", "127.0.0.1")
    port = int(api_cfg.get("port", 8000))
    reload = bool(api_cfg.get("reload", False))

    def _run_api():
        try:
            app = create_app(plugin_manager=plugin_manager, proxy_manager=proxy_manager, config=config)
            logger.info(f"🌐 API server starting on {host}:{port}")
            logger.info(f"📚 API docs available at http://{host}:{port}/docs")
            uvicorn.run(
                app,
                host=host,
                port=port,
                reload=reload,
                log_level="warning"
            )
        except Exception as e:
            logger.error(f"API server error: {e}")

    thread = threading.Thread(target=_run_api, daemon=True)
    thread.start()
    
    # Give the API server time to start
    time.sleep(1)
    
    return thread


def run():
    """Start dashboard (and API if enabled in config.json)"""
    config = _load_config()
    
    # Initialize managers
    plugin_manager = PluginManager()
    plugin_manager.discover_plugins()
    plugin_manager.load_all_plugins()
    
    state_file = config.get("proxy_state_file", "working_proxies.json")
    proxy_manager = ProxyManager(state_file=state_file)
    proxy_manager.load_from_file()
    
    # Start API with shared managers
    _start_api_if_enabled(config, plugin_manager=plugin_manager, proxy_manager=proxy_manager)

    # Start dashboard with shared managers
    dashboard = AdvancedDashboard(config_file="config.json")
    dashboard.plugin_manager = plugin_manager
    dashboard.proxy_manager = proxy_manager
    dashboard.run()


if __name__ == "__main__":
    run()

