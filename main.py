import json
import random
import time
from pathlib import Path
from urllib.parse import urlparse
from threading import Lock

from playwright.sync_api import Error, TimeoutError, sync_playwright
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.rule import Rule


BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
PROXY_PATH = BASE_DIR / "working_proxies.txt"
USER_AGENT_PATH = BASE_DIR / "user_agents.txt"
_file_lock = Lock()

console = Console()


BANNER = r"""
  _____       ______      __ 
 |  __ \     |  ____|    / _|
 | |__) |___ | |__ _ __ | |_ 
 |  _  // _ \|  __| '_ \|  _|
 | | \ \ (_) | |  | |_) | |  
 |_|  \_\___/|_|  | .__/|_|  
                  | |
                  |_|
"""


def load_config() -> dict:
	default = {
		"url": "https://httpbin.org/ip",
		"timeout": 8,
		"retries": 3,
		"verify_ssl": True,
		"user_agent": "RefBot/1.0 (+https://example.com)",
		"cookies": {"cookie_consent": "accepted"},
	}

	if not CONFIG_PATH.exists():
		console.print(f"[bold red]Missing config file:[/bold red] {CONFIG_PATH}")
		raise SystemExit(1)

	try:
		user_cfg = json.loads(CONFIG_PATH.read_text())
	except json.JSONDecodeError as exc:
		console.print(f"[bold red]Invalid JSON in config:[/bold red] {exc}")
		raise SystemExit(1)

	merged = {**default, **user_cfg}
	if not merged.get("url"):
		console.print("[bold red]Config must include a non-empty 'url'.")
		raise SystemExit(1)

	return merged


def load_proxies() -> list[str]:
	if not PROXY_PATH.exists():
		console.print(f"[bold red]Missing proxy file:[/bold red] {PROXY_PATH}")
		raise SystemExit(1)

	proxies = [line.strip() for line in PROXY_PATH.read_text().splitlines() if line.strip()]
	if not proxies:
		console.print(f"[bold red]No proxies found in[/bold red] {PROXY_PATH}")
		raise SystemExit(1)

	random.shuffle(proxies)
	return proxies


def load_user_agents() -> list[str]:
	if not USER_AGENT_PATH.exists():
		console.print(f"[bold yellow]user_agents.txt not found. Falling back to config user_agent.[/bold yellow]")
		return []

	agents = [line.strip() for line in USER_AGENT_PATH.read_text().splitlines() if line.strip()]
	if not agents:
		console.print(f"[bold yellow]No user agents found in[/bold yellow] {USER_AGENT_PATH}. Using config user_agent.")
		return []

	return agents


def proxy_dict(proxy: str) -> dict:
	return {"http": f"http://{proxy}", "https": f"http://{proxy}"}


def drop_proxy(proxy: str) -> None:
	"""Remove a bad proxy from working_proxies.txt (thread-safe)."""
	with _file_lock:
		existing = [line.strip() for line in PROXY_PATH.read_text().splitlines() if line.strip()]
		remaining = [p for p in existing if p != proxy]
		if len(remaining) == len(existing):
			return
		PROXY_PATH.write_text("\n".join(remaining) + ("\n" if remaining else ""))


def render_config_panel(config: dict, proxy_preview: str, user_agent_label: str) -> None:
	table = Table(title="Run Settings", box=box.ROUNDED, show_header=False, pad_edge=False)
	table.add_column("Field", style="cyan", no_wrap=True)
	table.add_column("Value", style="white")
	table.add_row("Target URL", config["url"])
	table.add_row("Timeout", f"{config['timeout']}s")
	table.add_row("User-Agent", user_agent_label)
	if cookies := config.get("cookies"):
		table.add_row("Cookies", ", ".join(f"{k}={v}" for k, v in cookies.items()))
	if selector := config.get("cookie_button_selector"):
		table.add_row("Cookie Button", selector)
	if headless := config.get("headless") is not None:
		table.add_row("Headless", str(config.get("headless")))
	table.add_row("Proxy Sample", proxy_preview)
	console.print(Panel(table, title="Proxy Page Loader", border_style="green", padding=(1, 1)))
	console.print(Rule(style="dim"))


def browse_with_proxy(proxy: str, config: dict, ua: str, cookies: dict, cookie_selector: str) -> tuple[bool, dict]:
	"""Use Playwright to load the page via a proxy, accept cookies, and return status/body preview."""
	start = time.perf_counter()
	headless = bool(config.get("headless", True))
	timeout_ms = int(config.get("timeout", 10) * 1000)
	target_url = config["url"]
	warmup_url = config.get("warmup_url", target_url)

	try:
		with sync_playwright() as pw:
			browser = pw.chromium.launch(headless=headless, proxy={"server": f"http://{proxy}"})
			context = browser.new_context(
				user_agent=ua,
				ignore_https_errors=not config.get("verify_ssl", True),
				viewport={"width": 1280, "height": 720},
			)
			host = urlparse(target_url).hostname
			if cookies and host:
				context.add_cookies([
					{"name": k, "value": str(v), "domain": host, "path": "/"}
					for k, v in cookies.items()
				])

			page = context.new_page()

			# Warm-up to set early cookies if needed
			try:
				page.goto(warmup_url, wait_until="domcontentloaded", timeout=timeout_ms)
			except (TimeoutError, Error):
				pass

			response = page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)

			cookie_clicked = False
			if cookie_selector:
				try:
					btn = page.wait_for_selector(cookie_selector, timeout=3000)
					btn.click(force=True)
					cookie_clicked = True
				except TimeoutError:
					cookie_clicked = False
				except Error as exc:
					return False, {"error": f"Cookie click failed: {exc}", "proxy": proxy}

			page.wait_for_timeout(500)
			body_html = page.content()
			elapsed = time.perf_counter() - start

			status_code = response.status if response else 0
			ok = status_code and 200 <= status_code < 400
			context.close()
			browser.close()

			return ok, {
				"status": status_code,
				"elapsed": elapsed,
				"proxy": proxy,
				"body": body_html[:400].replace("\n", " "),
				"cookie_clicked": cookie_clicked,
			}
	except Error as exc:
		return False, {"error": str(exc), "proxy": proxy}


def main() -> None:
	config = load_config()
	proxies = load_proxies()
	user_agents = load_user_agents()
	cookies = config.get("cookies", {}) if isinstance(config.get("cookies", {}), dict) else {}
	cookie_selector = config.get("cookie_button_selector", "#cookie-accept-all")

	console.print(Panel(BANNER, border_style="magenta", title="RefBot", subtitle="Proxy Page Loader"))

	ua_label = f"Random from file ({len(user_agents)} entries)" if user_agents else config["user_agent"]

	render_config_panel(config, proxy_preview=proxies[0], user_agent_label=ua_label)

	attempts = len(proxies)  # run through all proxies
	selected = proxies
	successes: list[Panel] = []
	success_count = 0
	fail_count = 0

	def attempt_proxy(proxy: str) -> tuple[bool, dict, str]:
		ua_to_use = random.choice(user_agents) if user_agents else config.get("user_agent", "")
		success, info = browse_with_proxy(
			proxy=proxy,
			config=config,
			ua=ua_to_use,
			cookies=cookies,
			cookie_selector=cookie_selector,
		)
		info["user_agent"] = ua_to_use
		info.setdefault("stage", "browse")
		if not success:
			drop_proxy(proxy)
		return success, info, ua_to_use

	with Progress(
		SpinnerColumn(style="yellow"),
		TextColumn("{task.description}"),
		TimeElapsedColumn(),
		console=console,
	) as progress:
		task = progress.add_task("Browsing proxies...", total=len(selected))
		for proxy in selected:
			success, info, ua_used = attempt_proxy(proxy)
			progress.update(task, description=f"Checked {proxy}")
			progress.advance(task)

			if success:
				success_count += 1
				body_preview = info.get("body", "")
				success_panel = Panel(
					Text(
						f"Status: {info['status']}\n"
						f"Elapsed: {info['elapsed']:.2f}s\n"
						f"Proxy: {info['proxy']}\n"
						f"User-Agent: {ua_used}\n"
						f"Cookies clicked: {info.get('cookie_clicked', False)}\n\n"
						f"Body preview:\n{body_preview}",
						style="green",
					),
					title=f"Success #{success_count}",
					border_style="green",
				)
				successes.append(success_panel)
				console.print(success_panel)
			else:
				fail_count += 1
				stage = info.get("stage", "browse")
				error_msg = info.get("error", "Unknown error")
				console.print(f"[bold red]Failed ({stage}) via {proxy}:[/bold red] {error_msg} — removed from list")

	if not successes:
		console.print(Panel("All attempts failed. Try more retries or refresh the proxy list.", title="No Success", border_style="red"))

	console.print(
		Panel(
			f"Processed {len(selected)} proxies. Success: {success_count}, Failed: {fail_count}.",
			title="Summary",
			border_style="cyan",
		)
	)


if __name__ == "__main__":
	main()
