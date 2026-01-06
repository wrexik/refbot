"""Base Plugin Class - Abstract base for all plugins"""

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path


class PluginStatus(Enum):
    """Plugin execution status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginMetrics:
    """Plugin performance metrics"""
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    uptime_seconds: float = 0.0
    start_time: Optional[str] = None
    last_error: Optional[str] = None
    avg_response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return asdict(self)


class BasePlugin(ABC):
    """Abstract base class for all plugins"""
    
    def __init__(self, name: str, config_path: str):
        """
        Initialize plugin
        
        Args:
            name: Plugin name
            config_path: Path to plugin_config.json
        """
        self.name = name
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(f"plugins.{name}")
        
        # Status tracking
        self.status = PluginStatus.IDLE
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        
        # Metrics
        self.metrics = PluginMetrics()
        self.metrics.start_time = datetime.now().isoformat()
        
        # Configuration
        self.config: Dict[str, Any] = {}
        self._load_config()
        
        # Callbacks
        self._on_error_callbacks: List[Callable] = []
        self._on_metric_callbacks: List[Callable] = []
        
    def _load_config(self) -> None:
        """Load configuration from plugin_config.json"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.logger.info(f"Loaded config from {self.config_path}")
            else:
                self.logger.warning(f"Config file not found: {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self.config = {}
    
    def _save_config(self) -> None:
        """Save configuration to plugin_config.json"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Saved config to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Execute plugin logic (must be implemented by subclasses)
        
        Returns:
            Dictionary with execution results
        """
        pass
    
    def start(self) -> bool:
        """Start plugin execution"""
        with self._lock:
            if self.status in (PluginStatus.RUNNING, PluginStatus.PAUSED):
                self.logger.warning(f"Plugin already {self.status.value}")
                return False
            
            self.status = PluginStatus.RUNNING
            self.metrics.start_time = datetime.now().isoformat()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self.logger.info("Plugin started")
            return True
    
    def pause(self) -> bool:
        """Pause plugin execution"""
        with self._lock:
            if self.status != PluginStatus.RUNNING:
                return False
            
            self.status = PluginStatus.PAUSED
            self.logger.info("Plugin paused")
            return True
    
    def resume(self) -> bool:
        """Resume plugin execution"""
        with self._lock:
            if self.status != PluginStatus.PAUSED:
                return False
            
            self.status = PluginStatus.RUNNING
            self.logger.info("Plugin resumed")
            return True
    
    def stop(self) -> bool:
        """Stop plugin execution"""
        with self._lock:
            if self.status == PluginStatus.STOPPED:
                return False
            
            self.status = PluginStatus.STOPPED
            self.logger.info("Plugin stopped")
            return True
    
    def _run(self) -> None:
        """Main execution loop"""
        try:
            while self.status != PluginStatus.STOPPED:
                if self.status == PluginStatus.RUNNING:
                    try:
                        result = self.execute()
                        self._record_success(result)
                    except Exception as e:
                        self._record_error(str(e))
                        self._trigger_error_callbacks(e)
                
                # Update uptime
                if self.metrics.start_time:
                    start = datetime.fromisoformat(self.metrics.start_time)
                    self.metrics.uptime_seconds = (datetime.now() - start).total_seconds()
                
                time.sleep(0.1)  # Prevent busy waiting
        
        except Exception as e:
            self.logger.error(f"Plugin execution failed: {e}")
            self.status = PluginStatus.ERROR
            self.metrics.last_error = str(e)
    
    def _record_success(self, result: Dict[str, Any]) -> None:
        """Record successful execution"""
        with self._lock:
            self.metrics.requests_total += 1
            self.metrics.requests_success += 1
            
            if "response_time_ms" in result:
                # Update average response time
                total = self.metrics.requests_success
                current_avg = self.metrics.avg_response_time_ms
                new_time = result["response_time_ms"]
                self.metrics.avg_response_time_ms = (
                    (current_avg * (total - 1) + new_time) / total
                )
            
            self._trigger_metric_callbacks()
    
    def _record_error(self, error: str) -> None:
        """Record failed execution"""
        with self._lock:
            self.metrics.requests_total += 1
            self.metrics.requests_failed += 1
            self.metrics.last_error = error
            self._trigger_metric_callbacks()
    
    def _trigger_error_callbacks(self, error: Exception) -> None:
        """Trigger error callbacks"""
        for callback in self._on_error_callbacks:
            try:
                callback(self.name, error)
            except Exception as e:
                self.logger.warning(f"Error callback failed: {e}")
    
    def _trigger_metric_callbacks(self) -> None:
        """Trigger metric callbacks"""
        for callback in self._on_metric_callbacks:
            try:
                callback(self.name, self.metrics.to_dict())
            except Exception as e:
                self.logger.warning(f"Metric callback failed: {e}")
    
    def on_error(self, callback: Callable) -> None:
        """Register error callback"""
        self._on_error_callbacks.append(callback)
    
    def on_metric(self, callback: Callable) -> None:
        """Register metric callback"""
        self._on_metric_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get plugin status"""
        with self._lock:
            return {
                "name": self.name,
                "status": self.status.value,
                "metrics": self.metrics.to_dict(),
                "config_loaded": bool(self.config)
            }
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
        self._save_config()
    
    def get_metrics(self) -> PluginMetrics:
        """Get current metrics"""
        with self._lock:
            return self.metrics
    
    def log(self, level: str, message: str) -> None:
        """Log message"""
        if level.upper() == "DEBUG":
            self.logger.debug(message)
        elif level.upper() == "INFO":
            self.logger.info(message)
        elif level.upper() == "WARNING":
            self.logger.warning(message)
        elif level.upper() == "ERROR":
            self.logger.error(message)
        elif level.upper() == "CRITICAL":
            self.logger.critical(message)
