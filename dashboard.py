import json
import time
import threading
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Literal
from collections import deque
from urllib.parse import urlparse

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.box import ROUNDED

from proxy_manager import ProxyManager
from persistence import PersistenceManager, MetricsExporter
from worker_threads import WorkerThreads
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeout
from plugins.plugin_manager import PluginManager
from plugins.base_plugin import PluginStatus

try:
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout.containers import Window, HSplit
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.layout import Layout as PTLayout
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


class AdvancedDashboard:
    """Advanced RefBot Dashboard with multi-mode operation and 7 info panels"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config = self._load_config(config_file)
        self.console = Console()
        
        # Core managers
        self.proxy_manager = ProxyManager()
        self.persistence = PersistenceManager()
        self.metrics_exporter = MetricsExporter()
        self.plugin_manager = PluginManager(self.config.get("plugins_dir", "plugins"))
        self.plugin_manager.load_all_plugins()
        self.plugin_manager.register_metric_callback(self._on_plugin_metric)
        # Share proxy manager with plugins that support it
        for plugin in self.plugin_manager.plugins.values():
            try:
                plugin.proxy_manager = self.proxy_manager
            except Exception:
                pass
        self.plugin_names = sorted(self.plugin_manager.plugins.keys())
        self.selected_plugin_index = 0
        
        # Worker threads
        self.workers: Optional[WorkerThreads] = None
        
        # Logging and state
        self.log_buffer = deque(maxlen=self.config.get("log_buffer_lines", 20))
        self.running = False
        self.start_time = time.time()
        self.last_save_time = time.time()
        
        # Loading state
        self.loading_active = False
        self.loading_success = 0
        self.loading_failed = 0
        self.loading_current_proxy = None
        self.loading_thread: Optional[threading.Thread] = None
    
    def _load_config(self, config_file: str) -> dict:
        """Load configuration from JSON"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.console.print(f"[red]Error loading config: {e}[/red]")
            return {
                "scraper_interval_minutes": 5,
                "http_workers": 200,
                "https_workers": 200,
                "log_buffer_lines": 15,
                "save_state_interval_seconds": 10,
                "proxy_revalidate_hours": 1,
                "dashboard_refresh_rate": 1
            }
    
    def _log(self, level: str, message: str):
        """Add message to log buffer"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding
        if level == "SUCCESS":
            colored_msg = f"[green]✓[/green] {message}"
        elif level == "ERROR":
            colored_msg = f"[red]✗[/red] {message}"
        elif level == "WARNING":
            colored_msg = f"[yellow]⚠[/yellow] {message}"
        else:  # INFO
            colored_msg = f"[cyan]•[/cyan] {message}"
        
        self.log_buffer.append((timestamp, level, colored_msg))
        self.persistence.add_log_message(level, message)

    def _on_plugin_metric(self, plugin_name: str, metrics: dict):
        """Receive plugin metric callbacks and log lightweight summary"""
        summary = metrics or {}
        total = summary.get("requests_total", 0)
        success = summary.get("requests_success", 0)
        failed = summary.get("requests_failed", 0)
        self._log(
            "INFO",
            f"Plugin {plugin_name}: total={total} ✓{success} ✗{failed}"
        )
    
    def _make_header(self) -> Panel:
        """Create header panel with title and time"""
        now = datetime.now()
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        title = Text.assemble(
            ("🚀 ", "cyan"),
            ("Proxy Manager Dashboard", "bold cyan"),
            (" • ", "dim"),
            (now.strftime("%H:%M:%S"), "green"),
            (" • ", "dim"),
            (f"↑ {hours}h {minutes}m", "magenta")
        )
        
        return Panel(
            Align.center(title),
            style="bold cyan",
            border_style="cyan"
        )
    
    def _make_stats_panel(self) -> Panel:
        """Create stats panel with live counters"""
        stats = self.proxy_manager.get_stats()
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        
        stats_data = [
            ("Scraped:", str(stats["total_scraped"]), "cyan"),
            ("HTTP Valid:", str(stats["total_validated_http"]), "green"),
            ("HTTPS Valid:", str(stats["total_validated_https"]), "blue"),
            ("Working:", str(stats["working_count"]), "magenta"),
            ("Failed:", str(stats["total_failed"]), "red"),
            ("Testing:", str(stats["currently_testing"]), "yellow"),
        ]
        
        for label, value, color in stats_data:
            table.add_row(
                Text(label, style="dim"),
                Text(value, style=f"bold {color}")
            )
        
        return Panel(
            table,
            title="[bold cyan]📊 Statistics[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
    
    def _make_config_panel(self) -> Panel:
        """Create configuration display panel"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        config_items = [
            ("URL:", self.config.get("url", "N/A")[:40]),
            ("Timeout:", f"{self.config.get('timeout', 'N/A')}s"),
            ("HTTP Workers:", str(self.config.get("http_workers", 200))),
            ("HTTPS Workers:", str(self.config.get("https_workers", 200))),
            ("Scrape Interval:", f"{self.config.get('scraper_interval_minutes', 5)}min"),
        ]
        
        for label, value in config_items:
            table.add_row(
                Text(label, style="dim"),
                Text(value, style="cyan")
            )
        
        return Panel(
            table,
            title="[bold cyan]⚙️ Configuration[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
    
    def _make_proxies_panel(self) -> Panel:
        """Create top proxies display panel"""
        top_proxies = self.proxy_manager.get_top_proxies(10)
        
        if not top_proxies:
            return Panel(
                Text("No working proxies yet", style="dim yellow"),
                title="[bold cyan]⚡ Top Proxies[/bold cyan]",
                border_style="cyan"
            )
        
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("IP:Port", style="cyan", width=20)
        table.add_column("Protocol", style="magenta", width=10)
        table.add_column("Speed", style="green", width=8)
        table.add_column("Location", style="yellow", width=20)
        
        for proxy in top_proxies[:10]:
            table.add_row(
                proxy.address,
                proxy.protocols,
                f"{proxy.speed:.2f}s",
                proxy.location[:18]
            )
        
        return Panel(
            table,
            title="[bold cyan]⚡ Top Proxies[/bold cyan]",
            border_style="cyan",
            padding=(1, 1)
        )

    def _make_plugins_panel(self) -> Panel:
        """Create plugin status panel with selection highlight"""
        if not self.plugin_names:
            return Panel(
                Text("No plugins discovered", style="dim yellow"),
                title="[bold cyan]🧩 Plugins[/bold cyan]",
                border_style="cyan",
                padding=(1, 1)
            )

        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Plugin", style="cyan", width=18)
        table.add_column("Status", style="magenta", width=10)
        table.add_column("Req", style="green", width=6)
        table.add_column("Err", style="red", width=6)

        for idx, name in enumerate(self.plugin_names):
            plugin = self.plugin_manager.plugins.get(name)
            status = plugin.status.value if plugin else "unknown"
            metrics = plugin.get_metrics() if plugin else None
            req_total = metrics.requests_total if metrics else 0
            req_failed = metrics.requests_failed if metrics else 0
            highlight = "reverse" if idx == self.selected_plugin_index else ""

            table.add_row(
                Text(name, style=f"cyan {highlight}"),
                Text(status, style=f"magenta {highlight}"),
                Text(str(req_total), style=f"green {highlight}"),
                Text(str(req_failed), style=f"red {highlight}")
            )

        return Panel(
            table,
            title="[bold cyan]🧩 Plugins[/bold cyan]",
            border_style="cyan",
            padding=(1, 1)
        )
    
    def _make_log_panel(self) -> Panel:
        """Create log display panel"""
        if not self.log_buffer:
            log_text = Text("Waiting for events...", style="dim cyan")
        else:
            log_lines = []
            for timestamp, level, message in self.log_buffer:
                log_lines.append(f"[dim]{timestamp}[/dim] {message}")
            log_text = Text.from_markup("\n".join(log_lines))
        
        return Panel(
            log_text,
            title="[bold cyan]📋 Event Log[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
            height=16
        )
    
    def _make_layout(self) -> Layout:
        """Create advanced dashboard layout with 7 panels"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="log", size=18)
        )
        
        layout["header"].update(self._make_header())
        layout["log"].update(self._make_log_panel())
        
        # Split body into left and right sections
        layout["body"].split_row(
            Layout(name="left", size=45),
            Layout(name="right", size=50)
        )
        
        # Left side: stats, config, protocols
        layout["body"]["left"].split_column(
            Layout(name="stats", size=9),
            Layout(name="config", size=8),
            Layout(name="protocols", size=6)
        )
        
        layout["body"]["left"]["stats"].update(self._make_stats_panel())
        layout["body"]["left"]["config"].update(self._make_config_panel())
        layout["body"]["left"]["protocols"].update(self._make_protocol_stats_panel())
        
        # Right side: plugins, proxies, help
        layout["body"]["right"].split_column(
            Layout(name="plugins", size=12),
            Layout(name="proxies", size=12),
            Layout(name="help", size=7)
        )

        layout["body"]["right"]["plugins"].update(self._make_plugins_panel())
        layout["body"]["right"]["proxies"].update(self._make_proxies_panel())
        layout["body"]["right"]["help"].update(self._make_help_panel())
        
        return layout
    
    def _make_protocol_stats_panel(self) -> Panel:
        """Create protocol distribution panel with progress bars"""
        stats = self.proxy_manager.get_stats()
        http_only = stats["http_only"]
        https_only = stats["https_only"]
        both = stats["both"]
        total = stats["working_count"]
        
        table = Table(show_header=False, box=ROUNDED, padding=(0, 1))
        table.add_column("Protocol", style="cyan", width=12)
        table.add_column("Count", style="green", width=8)
        table.add_column("Bar", width=18)
        
        def make_bar(count, total):
            if total == 0:
                return ""
            filled = int((count / total) * 18) if total > 0 else 0
            return "█" * filled + "░" * (18 - filled)
        
        table.add_row("HTTP Only", str(http_only), Text(make_bar(http_only, total), style="green"))
        table.add_row("HTTPS Only", str(https_only), Text(make_bar(https_only, total), style="blue"))
        table.add_row("Both", str(both), Text(make_bar(both, total), style="magenta"))
        
        return Panel(
            table,
            title="[bold cyan]🔀 Protocols[/bold cyan]",
            border_style="cyan",
            padding=(0, 1)
        )
    
    def _make_help_panel(self) -> Panel:
        """Create help/shortcuts panel"""
        help_text = Text.from_markup(
            "[cyan]PLUGIN CONTROLS[/cyan]\n"
            "[green]↑↓[/green] - Select plugin\n"
            "[blue]↵[/blue] - Start/Resume\n"
            "[yellow]Space[/yellow] - Pause\n"
            "[red]Del/Backspace[/red] - Stop\n"
            "[magenta]Q[/magenta] - Quit"
        )
        
        return Panel(
            help_text,
            title="[bold cyan]⌨️ Keys[/bold cyan]",
            border_style="cyan",
            padding=(0, 1)
        )
    
    def _auto_save_loop(self):
        """Background loop to auto-save state"""
        while self.running:
            try:
                if time.time() - self.last_save_time >= self.config.get("save_state_interval_seconds", 10):
                    self.proxy_manager.save_to_file()
                    self.persistence.save()
                    
                    # Export metrics every minute
                    if int(time.time()) % 60 == 0:
                        stats = self.proxy_manager.get_stats()
                        self.metrics_exporter.append_metrics(stats)
                    
                    self.last_save_time = time.time()
                
                time.sleep(1)
            except Exception as e:
                self._log("ERROR", f"Auto-save error: {str(e)[:80]}")
    
    def _input_handler_worker(self):
        """Background worker to handle keyboard input for plugin control"""
        if not HAS_PROMPT_TOOLKIT:
            self._log("WARNING", "prompt_toolkit not installed, skipping plugin controls")
            return

        try:
            self._log("INFO", "Plugin controls active: ↑↓ select, ↵ start/resume, Space pause, Del stop")

            def get_plugin_text():
                lines = ["[bold cyan]━━ Plugins ━━[/bold cyan]"]
                if not self.plugin_names:
                    lines.append("No plugins discovered")
                else:
                    for idx, name in enumerate(self.plugin_names):
                        plugin = self.plugin_manager.plugins.get(name)
                        status = plugin.status.value if plugin else "unknown"
                        prefix = "➤" if idx == self.selected_plugin_index else "  "
                        lines.append(f"{prefix} {name} [dim]|[/dim] [bold]{status}[/bold]")
                lines.append("")
                lines.append("[dim]↵ start/resume • Space pause • Del stop • Q quit[/dim]")
                return "\n".join(lines)

            kb = KeyBindings()

            @kb.add("up", eager=True)
            def _(event):
                if not self.plugin_names:
                    return
                self.selected_plugin_index = (self.selected_plugin_index - 1) % len(self.plugin_names)
                event.app.invalidate()

            @kb.add("down", eager=True)
            def _(event):
                if not self.plugin_names:
                    return
                self.selected_plugin_index = (self.selected_plugin_index + 1) % len(self.plugin_names)
                event.app.invalidate()

            @kb.add("enter", eager=True)
            def _(event):
                self._start_or_resume_selected_plugin()
                event.app.invalidate()

            @kb.add(" ", eager=True)
            def _(event):
                self._pause_selected_plugin()
                event.app.invalidate()

            @kb.add("delete", eager=True)
            @kb.add("backspace", eager=True)
            def _(event):
                self._stop_selected_plugin()
                event.app.invalidate()

            @kb.add("q", eager=True)
            def _(event):
                self._handle_quit()
                event.app.exit()

            root_container = HSplit([
                Window(
                    content=FormattedTextControl(lambda: HTML(get_plugin_text())),
                    height=12
                )
            ])

            app = Application(
                layout=PTLayout(root_container),
                key_bindings=kb,
                enable_page_navigation_bindings=False,
                mouse_support=False,
                refresh_interval=0.25,
            )

            # Run the prompt_toolkit UI in this background thread; it will exit when Q is pressed
            while self.running:
                app.run()

        except Exception as e:
            self._log("ERROR", f"Plugin control error: {str(e)[:50]}")
    
    def _selected_plugin_name(self) -> Optional[str]:
        """Return currently selected plugin name"""
        if not self.plugin_names:
            return None
        self.selected_plugin_index %= len(self.plugin_names)
        return self.plugin_names[self.selected_plugin_index]

    def _start_or_resume_selected_plugin(self):
        name = self._selected_plugin_name()
        if not name:
            self._log("WARNING", "No plugins available")
            return
        plugin = self.plugin_manager.plugins.get(name)
        if not plugin:
            self._log("ERROR", f"Plugin {name} not loaded")
            return

        if plugin.status == PluginStatus.PAUSED:
            ok = self.plugin_manager.resume_plugin(name)
            self._log("SUCCESS" if ok else "ERROR", f"Plugin {name} resume {'ok' if ok else 'failed'}")
        elif plugin.status in (PluginStatus.STOPPED, PluginStatus.IDLE, PluginStatus.ERROR):
            ok = self.plugin_manager.start_plugin(name)
            self._log("SUCCESS" if ok else "ERROR", f"Plugin {name} start {'ok' if ok else 'failed'}")
        elif plugin.status == PluginStatus.RUNNING:
            self._log("INFO", f"Plugin {name} already running")

    def _pause_selected_plugin(self):
        name = self._selected_plugin_name()
        if not name:
            return
        plugin = self.plugin_manager.plugins.get(name)
        if plugin and plugin.status == PluginStatus.RUNNING:
            ok = self.plugin_manager.pause_plugin(name)
            self._log("SUCCESS" if ok else "ERROR", f"Plugin {name} pause {'ok' if ok else 'failed'}")
        else:
            self._log("WARNING", f"Plugin {name} not running")

    def _stop_selected_plugin(self):
        name = self._selected_plugin_name()
        if not name:
            return
        ok = self.plugin_manager.stop_plugin(name)
        self._log("SUCCESS" if ok else "ERROR", f"Plugin {name} stop {'ok' if ok else 'failed'}")
    
    def _handle_results(self):
        """Handle results action"""
        stats = self.proxy_manager.get_stats()
        self._log("INFO", f"Results: {stats['working_count']} working proxies")
    
    def _handle_export(self):
        """Handle export action"""
        try:
            self._log("INFO", "Exporting metrics...")
            self.metrics_exporter.export_csv("metrics.csv")
            self._log("SUCCESS", "Metrics exported to metrics.csv")
        except Exception as e:
            self._log("ERROR", f"Export failed: {str(e)[:50]}")
    
    def _handle_quit(self):
        """Handle quit action"""
        self._log("WARNING", "Shutting down...")
        self.running = False
    
    def run(self):
        """Run the dashboard"""
        self.running = True
        self._log("INFO", "Dashboard starting...")
        
        try:
            # Start worker threads
            self.workers = WorkerThreads(
                manager=self.proxy_manager,
                http_workers=self.config.get("http_workers", 200),
                https_workers=self.config.get("https_workers", 200),
                scraper_interval_minutes=self.config.get("scraper_interval_minutes", 5),
                log_callback=self._log
            )
            self.workers.start()
            self._log("SUCCESS", "Worker threads started - Press L to load pages")
            
            # Start auto-save thread
            save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
            save_thread.start()
            
            # Start input handler thread
            input_thread = threading.Thread(target=self._input_handler_worker, daemon=True)
            input_thread.start()
            
            # Start dashboard rendering loop
            refresh_rate = self.config.get("dashboard_refresh_rate", 1)
            layout = self._make_layout()
            
            self._log("INFO", "Dashboard ready")
            
            with Live(layout, refresh_per_second=refresh_rate, screen=True) as live:
                while self.running:
                    try:
                        # Refresh plugin list in case plugins changed
                        self.plugin_names = sorted(self.plugin_manager.plugins.keys())

                        # Update all 7 panels
                        layout["header"].update(self._make_header())
                        layout["body"]["left"]["stats"].update(self._make_stats_panel())
                        layout["body"]["left"]["config"].update(self._make_config_panel())
                        layout["body"]["left"]["protocols"].update(self._make_protocol_stats_panel())
                        layout["body"]["right"]["plugins"].update(self._make_plugins_panel())
                        layout["body"]["right"]["proxies"].update(self._make_proxies_panel())
                        layout["body"]["right"]["help"].update(self._make_help_panel())
                        layout["log"].update(self._make_log_panel())
                        
                        time.sleep(1.0 / refresh_rate)
                    except KeyboardInterrupt:
                        self._log("WARNING", "Shutdown requested...")
                        self.shutdown()
                        break
                    except Exception as e:
                        self._log("ERROR", f"Dashboard error: {str(e)[:80]}")
                        time.sleep(0.5)
        
        except KeyboardInterrupt:
            self._log("WARNING", "Interrupted")
        except Exception as e:
            self._log("ERROR", f"Fatal: {str(e)}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        self.loading_active = False
        self._log("INFO", "Shutting down...")
        
        if self.workers:
            self.workers.stop()
        
        self.proxy_manager.save_to_file()
        self.persistence.stop_auto_save()
        
        self._log("SUCCESS", "Dashboard closed")


class Dashboard(AdvancedDashboard):
    """Alias for backward compatibility"""
    pass


def main():
    """Main entry point"""
    dashboard = AdvancedDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
