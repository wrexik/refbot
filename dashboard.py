import json
import time
import threading
import random
import shutil
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
    
    # ═══════════════════════════════════════════════════════════════
    # STYLING CONSTANTS - Centralized theme configuration
    # ═══════════════════════════════════════════════════════════════
    
    # Color Scheme
    COLOR_PRIMARY = "cyan"
    COLOR_SUCCESS = "green"
    COLOR_ERROR = "red"
    COLOR_WARNING = "yellow"
    COLOR_INFO = "blue"
    COLOR_ACCENT = "magenta"
    COLOR_DIM = "dim"
    
    # Layout Sizes (proportional)
    SIZE_HEADER = 4
    SIZE_LOG = 18
    SIZE_LEFT_COL = 50
    SIZE_RIGHT_COL = 50
    SIZE_STATS = 9
    SIZE_CONFIG = 8
    SIZE_PROTOCOLS = 6
    SIZE_PLUGINS = 12
    SIZE_PROXIES = 12
    SIZE_HELP = 7
    
    # Spacing Configuration
    PADDING_PANEL_TEXT = (1, 2)
    PADDING_PANEL_TABLE = (1, 1)
    PADDING_PANEL_MINIMAL = (0, 1)
    PADDING_TABLE_NO_HEADER = (0, 2)
    PADDING_TABLE_WITH_HEADER = (0, 1)
    
    # Terminal Size Requirements
    MIN_TERMINAL_WIDTH = 80
    MIN_TERMINAL_HEIGHT = 45
    
    def __init__(self, config_file: str = "config.json"):
        self.config = self._load_config(config_file)
        self.console = Console()
        
        # Terminal size tracking for responsive design
        self.terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        
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
        
        # Color coding with constants
        if level == "SUCCESS":
            colored_msg = f"[{self.COLOR_SUCCESS}]✓[/{self.COLOR_SUCCESS}] {message}"
        elif level == "ERROR":
            colored_msg = f"[{self.COLOR_ERROR}]✗[/{self.COLOR_ERROR}] {message}"
        elif level == "WARNING":
            colored_msg = f"[{self.COLOR_WARNING}]⚠[/{self.COLOR_WARNING}] {message}"
        else:  # INFO
            colored_msg = f"[{self.COLOR_PRIMARY}]•[/{self.COLOR_PRIMARY}] {message}"
        
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
        
        # Check if API is available
        api_status = "🌐 API Ready" if self._check_api_available() else "⚠️ API Off"
        
        title = Text.assemble(
            ("🚀 ", self.COLOR_PRIMARY),
            ("Proxy Manager Dashboard", f"bold {self.COLOR_PRIMARY}"),
            (" • ", self.COLOR_DIM),
            (now.strftime("%H:%M:%S"), self.COLOR_SUCCESS),
            (" • ", self.COLOR_DIM),
            (f"↑ {hours}h {minutes}m", self.COLOR_ACCENT),
            (" • ", self.COLOR_DIM),
            (api_status, self.COLOR_INFO if "Ready" in api_status else self.COLOR_WARNING)
        )
        
        return Panel(
            Align.center(title),
            border_style=self.COLOR_PRIMARY
        )
    
    def _check_api_available(self) -> bool:
        """Check if API server is available"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex(('127.0.0.1', 8000))
            sock.close()
            return result == 0
        except:
            return False
    
    def _make_stats_panel(self) -> Panel:
        """Create stats panel with live counters"""
        stats = self.proxy_manager.get_stats()
        
        table = Table(show_header=False, box=None, padding=self.PADDING_TABLE_NO_HEADER)
        
        # Format numbers with thousands separator for large values
        stats_data = [
            ("Scraped:", f"{stats['total_scraped']:,}", self.COLOR_PRIMARY),
            ("HTTP Valid:", f"{stats['total_validated_http']:,}", self.COLOR_SUCCESS),
            ("HTTPS Valid:", f"{stats['total_validated_https']:,}", self.COLOR_INFO),
            ("Working:", f"{stats['working_count']:,}", self.COLOR_ACCENT),
            ("Failed:", f"{stats['total_failed']:,}", self.COLOR_ERROR),
            ("Testing:", f"{stats['currently_testing']:,}", self.COLOR_WARNING),
        ]
        
        for label, value, color in stats_data:
            table.add_row(
                Text(label, style=self.COLOR_DIM),
                Text(value, style=f"bold {color}")
            )
        
        return Panel(
            table,
            title=f"[bold {self.COLOR_PRIMARY}]📊 Statistics[/bold {self.COLOR_PRIMARY}]",
            border_style=self.COLOR_PRIMARY,
            padding=self.PADDING_PANEL_TEXT
        )
    
    def _make_config_panel(self) -> Panel:
        """Create configuration display panel"""
        self.terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        table = Table(show_header=False, box=None, padding=self.PADDING_TABLE_NO_HEADER)
        
        # Dynamic URL truncation based on terminal width
        url_max_len = max(25, self.terminal_size.columns // 3)
        url = self.config.get("url", "N/A")
        truncated_url = url if len(url) <= url_max_len else url[:url_max_len-3] + "..."
        
        config_items = [
            ("URL:", truncated_url),
            ("Timeout:", f"{self.config.get('timeout', 'N/A')}s"),
            ("HTTP Workers:", f"{self.config.get('http_workers', 200):,}"),
            ("HTTPS Workers:", f"{self.config.get('https_workers', 200):,}"),
            ("Scrape Interval:", f"{self.config.get('scraper_interval_minutes', 5)}min"),
        ]
        
        for label, value in config_items:
            table.add_row(
                Text(label, style=self.COLOR_DIM),
                Text(value, style=self.COLOR_PRIMARY)
            )
        
        return Panel(
            table,
            title=f"[bold {self.COLOR_PRIMARY}]⚙️ Configuration[/bold {self.COLOR_PRIMARY}]",
            border_style=self.COLOR_PRIMARY,
            padding=self.PADDING_PANEL_TEXT
        )
    
    def _make_proxies_panel(self) -> Panel:
        """Create top proxies display panel"""
        self.terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        top_proxies = self.proxy_manager.get_top_proxies(10)
        
        if not top_proxies:
            return Panel(
                Text("No working proxies yet", style=f"{self.COLOR_DIM} {self.COLOR_WARNING}"),
                title=f"[bold {self.COLOR_PRIMARY}]⚡ Top Proxies[/bold {self.COLOR_PRIMARY}]",
                border_style=self.COLOR_PRIMARY,
                padding=self.PADDING_PANEL_TABLE
            )
        
        # Responsive column widths (percentage-based)
        available_width = max(60, self.terminal_size.columns // 2 - 10)
        width_ip = max(18, int(available_width * 0.35))
        width_proto = max(8, int(available_width * 0.18))
        width_speed = max(7, int(available_width * 0.15))
        width_loc = max(15, int(available_width * 0.32))
        
        table = Table(show_header=True, box=None, padding=self.PADDING_TABLE_WITH_HEADER)
        table.add_column("IP:Port", style=self.COLOR_PRIMARY, width=width_ip)
        table.add_column("Protocol", style=self.COLOR_ACCENT, width=width_proto)
        table.add_column("Speed", style=self.COLOR_SUCCESS, width=width_speed)
        table.add_column("Location", style=self.COLOR_WARNING, width=width_loc)
        
        for proxy in top_proxies[:10]:
            # Dynamic truncation based on column width
            location = proxy.location if len(proxy.location) <= width_loc else proxy.location[:width_loc-3] + "..."
            table.add_row(
                proxy.address,
                proxy.protocols,
                f"{proxy.speed:.2f}s",
                location
            )
        
        return Panel(
            table,
            title=f"[bold {self.COLOR_PRIMARY}]⚡ Top Proxies[/bold {self.COLOR_PRIMARY}]",
            border_style=self.COLOR_PRIMARY,
            padding=self.PADDING_PANEL_TABLE
        )

    def _make_plugins_panel(self) -> Panel:
        self.terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        """Create plugin status panel with selection highlight"""
        if not self.plugin_names:
            return Panel(
                Text("No plugins discovered", style=f"{self.COLOR_DIM} {self.COLOR_WARNING}"),
                title=f"[bold {self.COLOR_PRIMARY}]🧩 Plugins[/bold {self.COLOR_PRIMARY}]",
                border_style=self.COLOR_PRIMARY,
                padding=self.PADDING_PANEL_TABLE
            )

        # Responsive column widths
        available_width = max(40, self.terminal_size.columns // 2 - 10)
        width_name = max(14, int(available_width * 0.45))
        width_status = max(8, int(available_width * 0.25))
        width_req = max(5, int(available_width * 0.15))
        width_err = max(5, int(available_width * 0.15))

        table = Table(show_header=True, box=None, padding=self.PADDING_TABLE_WITH_HEADER)
        table.add_column("Plugin", style=self.COLOR_PRIMARY, width=width_name)
        table.add_column("Status", style=self.COLOR_ACCENT, width=width_status)
        table.add_column("Req", style=self.COLOR_SUCCESS, width=width_req, justify="right")
        table.add_column("Err", style=self.COLOR_ERROR, width=width_err, justify="right")

        for idx, name in enumerate(self.plugin_names):
            plugin = self.plugin_manager.plugins.get(name)
            status = plugin.status.value if plugin else "unknown"
            metrics = plugin.get_metrics() if plugin else None
            req_total = metrics.requests_total if metrics else 0
            req_failed = metrics.requests_failed if metrics else 0
            highlight = "reverse" if idx == self.selected_plugin_index else ""
            
            # Status badge with emoji
            status_badges = {
                "running": "🟢 running",
                "paused": "🟡 paused",
                "stopped": "⚫ stopped",
                "error": "🔴 error"
            }
            status_display = status_badges.get(status, f"❓ {status}")

            # Truncate name if needed
            display_name = name if len(name) <= width_name else name[:width_name-3] + "..."

            table.add_row(
                Text(display_name, style=f"{self.COLOR_PRIMARY} {highlight}"),
                Text(status_display, style=f"{self.COLOR_ACCENT} {highlight}"),
                Text(f"{req_total:,}", style=f"{self.COLOR_SUCCESS} {highlight}"),
                Text(f"{req_failed:,}", style=f"{self.COLOR_ERROR} {highlight}")
            )

        return Panel(
            table,
            title=f"[bold {self.COLOR_PRIMARY}]🧩 Plugins[/bold {self.COLOR_PRIMARY}]",
            border_style=self.COLOR_PRIMARY,
            padding=self.PADDING_PANEL_TABLE
        )
    
    def _make_log_panel(self) -> Panel:
        """Create log display panel"""
        if not self.log_buffer:
            log_text = Text("Waiting for events...", style=f"{self.COLOR_DIM} {self.COLOR_PRIMARY}")
        else:
            log_lines = []
            for timestamp, level, message in self.log_buffer:
                log_lines.append(f"[{self.COLOR_DIM}]{timestamp}[/{self.COLOR_DIM}] {message}")
            log_text = Text.from_markup("\n".join(log_lines))
        
        return Panel(
            log_text,
            title=f"[bold {self.COLOR_PRIMARY}]📋 Event Log[/bold {self.COLOR_PRIMARY}]",
            border_style=self.COLOR_PRIMARY,
            padding=self.PADDING_PANEL_TEXT,
            height=self.SIZE_LOG
        )
    
    def _make_layout(self) -> Layout:
        """Create advanced dashboard layout with 7 panels"""
        # Update terminal size for responsive design
        self.terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=self.SIZE_HEADER),
            Layout(name="body"),
            Layout(name="log", size=self.SIZE_LOG)
        )
        
        # Check if terminal is too small and show warning
        if self.terminal_size.columns < self.MIN_TERMINAL_WIDTH or self.terminal_size.lines < self.MIN_TERMINAL_HEIGHT:
            warning_text = Text.from_markup(
                f"[bold {self.COLOR_WARNING}]⚠ Terminal Too Small[/bold {self.COLOR_WARNING}]\n\n"
                f"Current: {self.terminal_size.columns}×{self.terminal_size.lines}\n"
                f"Minimum: {self.MIN_TERMINAL_WIDTH}×{self.MIN_TERMINAL_HEIGHT}\n\n"
                f"[{self.COLOR_DIM}]Please resize your terminal for optimal display.[/{self.COLOR_DIM}]"
            )
            layout["header"].update(Panel(
                Align.center(warning_text),
                border_style=self.COLOR_WARNING,
                style=f"bold {self.COLOR_WARNING}"
            ))
        else:
            layout["header"].update(self._make_header())
        
        layout["log"].update(self._make_log_panel())
        
        # Split body into left and right sections (balanced 50:50)
        layout["body"].split_row(
            Layout(name="left", size=self.SIZE_LEFT_COL),
            Layout(name="right", size=self.SIZE_RIGHT_COL)
        )
        
        # Left side: stats, config, protocols
        layout["body"]["left"].split_column(
            Layout(name="stats", size=self.SIZE_STATS),
            Layout(name="config", size=self.SIZE_CONFIG),
            Layout(name="protocols", size=self.SIZE_PROTOCOLS)
        )
        
        layout["body"]["left"]["stats"].update(self._make_stats_panel())
        layout["body"]["left"]["config"].update(self._make_config_panel())
        layout["body"]["left"]["protocols"].update(self._make_protocol_stats_panel())
        
        # Right side: plugins, proxies, help
        layout["body"]["right"].split_column(
            Layout(name="plugins", size=self.SIZE_PLUGINS),
            Layout(name="proxies", size=self.SIZE_PROXIES),
            Layout(name="help", size=self.SIZE_HELP)
        )

        layout["body"]["right"]["plugins"].update(self._make_plugins_panel())
        layout["body"]["right"]["proxies"].update(self._make_proxies_panel())
        layout["body"]["right"]["help"].update(self._make_help_panel())
        
        return layout
    
    def _make_protocol_stats_panel(self) -> Panel:
        """Create protocol distribution panel with progress bars"""
        self.terminal_size = shutil.get_terminal_size(fallback=(80, 24))
        stats = self.proxy_manager.get_stats()
        http_only = stats["http_only"]
        https_only = stats["https_only"]
        both = stats["both"]
        total = stats["working_count"]
        
        # Responsive bar width
        bar_width = max(12, min(24, self.terminal_size.columns // 6))
        
        table = Table(show_header=False, box=None, padding=self.PADDING_TABLE_NO_HEADER)
        table.add_column("Protocol", style=self.COLOR_PRIMARY, width=12)
        table.add_column("Count", style=self.COLOR_SUCCESS, width=8, justify="right")
        table.add_column("Bar", width=bar_width)
        
        def make_bar(count, total, color):
            """Create enhanced progress bar with percentage"""
            if total == 0:
                return Text("░" * bar_width, style=self.COLOR_DIM)
            
            percentage = count / total
            filled = int(percentage * bar_width)
            
            # Gradient effect: use different characters for visual interest
            bar_chars = "█" * filled + "░" * (bar_width - filled)
            pct_text = f" {percentage*100:.0f}%" if bar_width > 15 else ""
            
            return Text(bar_chars + pct_text, style=color)
        
        table.add_row("HTTP Only", f"{http_only:,}", make_bar(http_only, total, self.COLOR_SUCCESS))
        table.add_row("HTTPS Only", f"{https_only:,}", make_bar(https_only, total, self.COLOR_INFO))
        table.add_row("Both", f"{both:,}", make_bar(both, total, self.COLOR_ACCENT))
        
        return Panel(
            table,
            title=f"[bold {self.COLOR_PRIMARY}]🔀 Protocols[/bold {self.COLOR_PRIMARY}]",
            border_style=self.COLOR_PRIMARY,
            padding=self.PADDING_PANEL_MINIMAL
        )
    
    def _make_help_panel(self) -> Panel:
        """Create help/shortcuts panel"""
        help_text = Text.from_markup(
            f"[bold {self.COLOR_PRIMARY}]PLUGIN CONTROLS[/bold {self.COLOR_PRIMARY}]\n"
            f"[{self.COLOR_SUCCESS}]\u2191\u2193 / K J[/{self.COLOR_SUCCESS}] - Select plugin\n"
            f"[{self.COLOR_INFO}]Enter[/{self.COLOR_INFO}] - Start/Resume\n"
            f"[{self.COLOR_WARNING}]Space[/{self.COLOR_WARNING}] - Pause\n"
            f"[{self.COLOR_ERROR}]Delete[/{self.COLOR_ERROR}] - Stop\n"
            f"[{self.COLOR_ACCENT}]Q[/{self.COLOR_ACCENT}] - Quit"
        )
        
        return Panel(
            help_text,
            title=f"[bold {self.COLOR_PRIMARY}]⌨️ Keys[/bold {self.COLOR_PRIMARY}]",
            border_style=self.COLOR_PRIMARY,
            padding=self.PADDING_PANEL_MINIMAL
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
        """Background worker to handle keyboard input without blocking Live context"""
        try:
            import sys
            import os
            
            # Try Unix approach first
            if sys.platform != "win32":
                self._input_handler_unix()
            else:
                self._input_handler_windows()
                
        except Exception as e:
            self._log("WARNING", f"Keyboard input handler error: {str(e)[:40]}")
    
    def _input_handler_unix(self):
        """Non-blocking keyboard input for Unix/Linux/Mac"""
        try:
            import select
            import sys
            
            self._log("INFO", "Keyboard ready: ↑↓/KJ select, ↵ start, Space pause, Del stop, Q quit")
            
            while self.running:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)
                    self._handle_input_char(ch)
                
        except Exception as e:
            self._log("WARNING", f"Unix input handler: {str(e)[:40]}")
    
    def _input_handler_windows(self):
        """Keyboard input for Windows"""
        try:
            import msvcrt
            import time
            
            self._log("INFO", "Keyboard ready: ↑↓/KJ select, Enter start, Space pause, Delete stop, Q quit")
            
            while self.running:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch == b'\xe0':  # Arrow key prefix
                        next_ch = msvcrt.getch()
                        if next_ch == b'H':  # Up arrow
                            if self.plugin_names:
                                self.selected_plugin_index = (self.selected_plugin_index - 1) % len(self.plugin_names)
                                self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
                        elif next_ch == b'P':  # Down arrow
                            if self.plugin_names:
                                self.selected_plugin_index = (self.selected_plugin_index + 1) % len(self.plugin_names)
                                self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
                        elif next_ch == b'S':  # Delete key
                            self._stop_selected_plugin()
                    else:
                        # Decode and handle regular keys
                        try:
                            char = ch.decode('utf-8', errors='ignore')
                            if char.lower() == 'q':
                                self._log("WARNING", "Shutdown requested...")
                                self.running = False
                            elif char == '\r':  # Enter
                                self._start_or_resume_selected_plugin()
                            elif char == ' ':  # Space
                                self._pause_selected_plugin()
                            elif char == 'k':  # Vim up
                                if self.plugin_names:
                                    self.selected_plugin_index = (self.selected_plugin_index - 1) % len(self.plugin_names)
                                    self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
                            elif char == 'j':  # Vim down
                                if self.plugin_names:
                                    self.selected_plugin_index = (self.selected_plugin_index + 1) % len(self.plugin_names)
                                    self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
                        except:
                            pass
                time.sleep(0.05)
                    
        except Exception as e:
            self._log("WARNING", f"Windows input handler: {str(e)[:40]}")
    
    def _handle_input_char(self, ch: str):
        """Handle a single character input"""
        if ch.lower() == 'q':
            self._log("WARNING", "Shutdown requested...")
            self.running = False
        elif ch == '\x1b':  # ESC sequence (arrows)
            import sys
            next_ch = sys.stdin.read(1)
            if next_ch == '[':
                arrow = sys.stdin.read(1)
                if arrow == 'A':  # Up
                    if self.plugin_names:
                        self.selected_plugin_index = (self.selected_plugin_index - 1) % len(self.plugin_names)
                        self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
                elif arrow == 'B':  # Down
                    if self.plugin_names:
                        self.selected_plugin_index = (self.selected_plugin_index + 1) % len(self.plugin_names)
                        self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
        elif ch == '\r':  # Enter
            self._start_or_resume_selected_plugin()
        elif ch == ' ':  # Space
            self._pause_selected_plugin()
        elif ch in ('\x08', '\x7f', '\x04'):  # Backspace, Delete, Ctrl+D
            self._stop_selected_plugin()
        elif ch == 'k':  # Vim up
            if self.plugin_names:
                self.selected_plugin_index = (self.selected_plugin_index - 1) % len(self.plugin_names)
                self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
        elif ch == 'j':  # Vim down
            if self.plugin_names:
                self.selected_plugin_index = (self.selected_plugin_index + 1) % len(self.plugin_names)
                self._log("INFO", f"Selected: {self.plugin_names[self.selected_plugin_index]}")
    
    def _selected_plugin_name(self) -> Optional[str]:
        """Return currently selected plugin name"""
        if not self.plugin_names:
            return None
        self.selected_plugin_index %= len(self.plugin_names)
        return self.plugin_names[self.selected_plugin_index]

    def _start_or_resume_selected_plugin(self):
        name = self._selected_plugin_name()
        if not name:
            self._log("WARNING", "⚠️ No plugins available to start")
            return
        plugin = self.plugin_manager.plugins.get(name)
        if not plugin:
            self._log("ERROR", f"❌ Plugin '{name}' not loaded")
            return

        if plugin.status == PluginStatus.PAUSED:
            ok = self.plugin_manager.resume_plugin(name)
            self._log("SUCCESS" if ok else "ERROR", f"{'▶️ Resumed' if ok else '❌ Failed to resume'} plugin '{name}'")
        elif plugin.status in (PluginStatus.STOPPED, PluginStatus.IDLE, PluginStatus.ERROR):
            ok = self.plugin_manager.start_plugin(name)
            self._log("SUCCESS" if ok else "ERROR", f"{'🚀 Started' if ok else '❌ Failed to start'} plugin '{name}'")
        elif plugin.status == PluginStatus.RUNNING:
            self._log("INFO", f"✓ Plugin '{name}' is already running")

    def _pause_selected_plugin(self):
        name = self._selected_plugin_name()
        if not name:
            self._log("WARNING", "⚠️ No plugins available to pause")
            return
        plugin = self.plugin_manager.plugins.get(name)
        if not plugin:
            self._log("ERROR", f"❌ Plugin '{name}' not found")
            return
        if plugin.status == PluginStatus.RUNNING:
            ok = self.plugin_manager.pause_plugin(name)
            self._log("SUCCESS" if ok else "ERROR", f"{'⏸️ Paused' if ok else '❌ Failed to pause'} plugin '{name}'")
        elif plugin.status == PluginStatus.PAUSED:
            self._log("INFO", f"⏸️ Plugin '{name}' is already paused")
        else:
            self._log("WARNING", f"⚠️ Plugin '{name}' is not running (status: {plugin.status.value})")

    def _stop_selected_plugin(self):
        name = self._selected_plugin_name()
        if not name:
            self._log("WARNING", "⚠️ No plugins available to stop")
            return
        plugin = self.plugin_manager.plugins.get(name)
        if not plugin:
            self._log("ERROR", f"❌ Plugin '{name}' not found")
            return
        ok = self.plugin_manager.stop_plugin(name)
        self._log("SUCCESS" if ok else "ERROR", f"{'⏹️ Stopped' if ok else '❌ Failed to stop'} plugin '{name}'")
    
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
