"""BrowsingPlugin - simple page loader with proxy and UA rotation"""

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins.base_plugin import BasePlugin, PluginStatus

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


@dataclass
class BrowsingConfig:
    url: str = "https://example.com"
    headless: bool = True
    timeout_seconds: int = 12
    wait_selector: Optional[str] = None
    success_keyword: Optional[str] = None
    delay_after_load_ms: int = 500
    proxy_list: List[str] = None
    proxy_list_file: Optional[str] = None
    user_agents_file: Optional[str] = "user_agents.txt"
    use_stealth: bool = False
    max_retries_per_run: int = 1
    batch_size: int = 1
    sleep_between_runs_ms: int = 5000


class BrowsingPlugin(BasePlugin):
    def __init__(self, name: str, config_path: str):
        super().__init__(name, config_path)
        self.bconf = self._load_browsing_config()
        self.user_agents = self._load_user_agents()
        self.proxies = self._load_proxies()
        self.proxy_index = 0
        self.total_success = 0
        self.total_fail = 0

    def _load_browsing_config(self) -> BrowsingConfig:
        cfg = BrowsingConfig()
        cfg.url = self.config.get("url", cfg.url)
        cfg.headless = self.config.get("headless", cfg.headless)
        cfg.timeout_seconds = int(self.config.get("timeout_seconds", cfg.timeout_seconds))
        cfg.wait_selector = self.config.get("wait_selector", cfg.wait_selector)
        cfg.success_keyword = self.config.get("success_keyword", cfg.success_keyword)
        cfg.delay_after_load_ms = int(self.config.get("delay_after_load_ms", cfg.delay_after_load_ms))
        cfg.proxy_list = self.config.get("proxy_list", []) or []
        cfg.proxy_list_file = self.config.get("proxy_list_file", None)
        cfg.user_agents_file = self.config.get("user_agents_file", cfg.user_agents_file)
        cfg.use_stealth = bool(self.config.get("use_stealth", cfg.use_stealth))
        cfg.max_retries_per_run = int(self.config.get("max_retries_per_run", cfg.max_retries_per_run))
        cfg.batch_size = int(self.config.get("batch_size", cfg.batch_size))
        cfg.sleep_between_runs_ms = int(self.config.get("sleep_between_runs_ms", cfg.sleep_between_runs_ms))
        return cfg

    def _load_user_agents(self) -> List[str]:
        if not self.bconf.user_agents_file:
            return []
        return _read_lines(Path(self.bconf.user_agents_file))

    def _load_proxies(self) -> List[str]:
        proxies = list(self.bconf.proxy_list)
        if self.bconf.proxy_list_file:
            proxies.extend(_read_lines(Path(self.bconf.proxy_list_file)))
        return proxies

    def _next_proxy(self) -> Optional[str]:
        # Prefer shared proxy_manager if injected by dashboard
        if hasattr(self, "proxy_manager") and self.proxy_manager:
            for _ in range(10):  # wait up to ~5s for a working proxy
                try:
                    working = self.proxy_manager.get_working("ANY")
                    if working:
                        choice = random.choice(working)
                        return f"http://{choice.address}"
                except Exception:
                    pass
                time.sleep(0.5)

        if not self.proxies:
            return None
        proxy = self.proxies[self.proxy_index % len(self.proxies)]
        self.proxy_index += 1
        # Normalize to include scheme for Playwright
        if not proxy.startswith("http"):
            proxy = f"http://{proxy}"
        return proxy

    def _choose_user_agent(self) -> Optional[str]:
        return random.choice(self.user_agents) if self.user_agents else None

    def _load_once(self, proxy: Optional[str]) -> Dict[str, Any]:
        if not HAS_PLAYWRIGHT:
            return {"error": "playwright not installed"}

        start = time.time()
        ua = self._choose_user_agent()
        result: Dict[str, Any] = {
            "proxy": proxy,
            "user_agent": ua,
            "status": "unknown",
            "response_time_ms": 0.0,
        }

        with sync_playwright() as pw:
            launch_args: Dict[str, Any] = {"headless": self.bconf.headless}
            if proxy:
                launch_args["proxy"] = {"server": proxy}

            browser = pw.chromium.launch(**launch_args)
            context = browser.new_context(user_agent=ua) if ua else browser.new_context()
            page = context.new_page()
            try:
                resp = page.goto(self.bconf.url, wait_until="domcontentloaded", timeout=self.bconf.timeout_seconds * 1000)
                if self.bconf.wait_selector:
                    page.wait_for_selector(self.bconf.wait_selector, timeout=self.bconf.timeout_seconds * 1000)
                if self.bconf.delay_after_load_ms:
                    time.sleep(self.bconf.delay_after_load_ms / 1000)

                content_ok = True
                if self.bconf.success_keyword:
                    content = page.content().lower()
                    content_ok = self.bconf.success_keyword.lower() in content

                status_ok = resp.status is None or 200 <= resp.status < 400
                ok = status_ok and content_ok
                result["status"] = "success" if ok else "failed"
                return result
            except Exception as exc:
                result["error"] = str(exc)
                result["status"] = "error"
                return result
            finally:
                result["response_time_ms"] = (time.time() - start) * 1000
                context.close()
                browser.close()

    def execute(self) -> Dict[str, Any]:
        proxy = self._next_proxy()
        attempts = 0
        max_attempts = max(1, self.bconf.max_retries_per_run)
        last_result: Dict[str, Any] = {}
        for _ in range(max_attempts):
            attempts += 1
            last_result = self._load_once(proxy)
            if last_result.get("status") == "success":
                self.total_success += 1
                break
        else:
            self.total_fail += 1

        last_result.update({
            "attempts": attempts,
            "total_success": self.total_success,
            "total_fail": self.total_fail,
        })
        if self.bconf.sleep_between_runs_ms:
            time.sleep(self.bconf.sleep_between_runs_ms / 1000)
        return last_result
