import json
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class PersistenceManager:
    """Handles auto-save and state persistence for dashboard"""
    
    def __init__(self, 
                 state_file: str = "dashboard_state.json",
                 save_interval: int = 10):
        self.state_file = Path(state_file)
        self.save_interval = save_interval
        self.state: Dict[str, Any] = {}
        self.lock = threading.RLock()
        self.running = False
        self.save_thread: Optional[threading.Thread] = None
        
        # Load existing state
        self.load()
    
    def load(self):
        """Load state from file"""
        with self.lock:
            if self.state_file.exists():
                try:
                    with open(self.state_file, 'r') as f:
                        self.state = json.load(f)
                except Exception:
                    self.state = {}
            else:
                self.state = {}
            
            # Initialize default state if empty
            if not self.state:
                self.state = {
                    "session_start": time.time(),
                    "last_save": time.time(),
                    "last_scrape": 0,
                    "pause_scrapers": False,
                    "pause_validators": False,
                    "selected_filter": "ANY",  # ANY, HTTP, HTTPS, BOTH
                    "log_messages": []
                }
    
    def save(self):
        """Save state to file"""
        with self.lock:
            try:
                self.state["last_save"] = time.time()
                with open(self.state_file, 'w') as f:
                    json.dump(self.state, f, indent=2)
            except Exception:
                pass
    
    def update(self, key: str, value: Any):
        """Update a state value"""
        with self.lock:
            self.state[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a state value"""
        with self.lock:
            return self.state.get(key, default)
    
    def start_auto_save(self):
        """Start background auto-save thread"""
        if self.running:
            return
        
        self.running = True
        self.save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self.save_thread.start()
    
    def stop_auto_save(self):
        """Stop background auto-save thread"""
        self.running = False
        if self.save_thread:
            self.save_thread.join(timeout=2)
        self.save()  # Final save
    
    def _auto_save_loop(self):
        """Background loop that saves every interval"""
        while self.running:
            time.sleep(self.save_interval)
            self.save()
    
    def add_log_message(self, level: str, message: str, max_logs: int = 1000):
        """Add a log message to state"""
        with self.lock:
            if "log_messages" not in self.state:
                self.state["log_messages"] = []
            
            log_entry = {
                "timestamp": time.time(),
                "level": level,  # INFO, SUCCESS, WARNING, ERROR
                "message": message
            }
            self.state["log_messages"].append(log_entry)
            
            # Keep only last N logs
            if len(self.state["log_messages"]) > max_logs:
                self.state["log_messages"] = self.state["log_messages"][-max_logs:]
    
    def get_log_messages(self, limit: int = 100) -> list:
        """Get recent log messages"""
        with self.lock:
            logs = self.state.get("log_messages", [])
            return logs[-limit:]
    
    def clear_logs(self):
        """Clear all logs"""
        with self.lock:
            self.state["log_messages"] = []


class MetricsExporter:
    """Export metrics to CSV for analysis"""
    
    def __init__(self, metrics_file: str = "metrics.csv"):
        self.metrics_file = Path(metrics_file)
        self.lock = threading.RLock()
        
        # Initialize CSV with headers
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV file with headers"""
        if not self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'w') as f:
                    f.write("timestamp,total_scraped,http_valid,https_valid,working_count,"
                           "avg_speed,top_countries,failed_count\n")
            except Exception:
                pass
    
    def append_metrics(self, stats: Dict[str, Any]):
        """Append current metrics to CSV"""
        with self.lock:
            try:
                timestamp = datetime.now().isoformat()
                row = (
                    f"{timestamp},"
                    f"{stats.get('total_scraped', 0)},"
                    f"{stats.get('total_validated_http', 0)},"
                    f"{stats.get('total_validated_https', 0)},"
                    f"{stats.get('working_count', 0)},"
                    f"{stats.get('avg_speed', 0.0):.2f},"
                    f"\"data\","
                    f"{stats.get('total_failed', 0)}\n"
                )
                with open(self.metrics_file, 'a') as f:
                    f.write(row)
            except Exception:
                pass
    
    def export_csv(self, filename: str = None):
        """Export current metrics to CSV file (or copy existing file)"""
        with self.lock:
            try:
                target = Path(filename) if filename else self.metrics_file
                if self.metrics_file.exists():
                    with open(self.metrics_file, 'r') as src:
                        with open(target, 'w') as dst:
                            dst.write(src.read())
            except Exception as e:
                print(f"Warning: Failed to export metrics: {e}")
