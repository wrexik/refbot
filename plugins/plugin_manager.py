"""Plugin Manager - Discover and manage plugins"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from importlib import import_module
from inspect import isclass

from .base_plugin import BasePlugin, PluginStatus


logger = logging.getLogger(__name__)


class PluginManager:
    """Manage plugin discovery, loading, and lifecycle"""
    
    def __init__(self, plugins_dir: str = None):
        """
        Initialize plugin manager
        
        Args:
            plugins_dir: Directory containing plugins
        """
        self.plugins_dir = Path(plugins_dir or "plugins")
        self.plugins: Dict[str, BasePlugin] = {}
        self._callbacks: List[Callable] = []
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
    
    def discover_plugins(self) -> List[str]:
        """
        Auto-discover plugins in plugins directory
        
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue
            
            config_file = plugin_dir / "plugin_config.json"
            if config_file.exists():
                discovered.append(plugin_dir.name)
                logger.info(f"Discovered plugin: {plugin_dir.name}")
        
        return discovered
    
    def load_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Load a plugin
        
        Args:
            plugin_name: Name of plugin to load
        
        Returns:
            Plugin instance or None if failed
        """
        if plugin_name in self.plugins:
            logger.warning(f"Plugin already loaded: {plugin_name}")
            return self.plugins[plugin_name]
        
        plugin_dir = self.plugins_dir / plugin_name
        config_file = plugin_dir / "plugin_config.json"
        
        if not plugin_dir.exists():
            logger.error(f"Plugin directory not found: {plugin_dir}")
            return None
        
        if not config_file.exists():
            logger.error(f"Config file not found: {config_file}")
            return None
        
        try:
            # Load config to get plugin class
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            plugin_class = config.get("class", f"{plugin_name}.RegistrationPlugin")
            
            # Import and instantiate plugin
            module_name, class_name = plugin_class.rsplit(".", 1)
            
            # Add plugin dir to path if needed
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))
            
            module = import_module(module_name)
            plugin_cls = getattr(module, class_name)
            
            if not isclass(plugin_cls) or not issubclass(plugin_cls, BasePlugin):
                logger.error(f"Invalid plugin class: {plugin_class}")
                return None
            
            # Create instance
            plugin = plugin_cls(plugin_name, str(config_file))
            
            # Register callbacks
            for callback in self._callbacks:
                plugin.on_metric(callback)
            
            self.plugins[plugin_name] = plugin
            logger.info(f"Loaded plugin: {plugin_name}")
            return plugin
        
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            return None
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin
        
        Args:
            plugin_name: Name of plugin to unload
        
        Returns:
            True if successful
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin not loaded: {plugin_name}")
            return False
        
        plugin = self.plugins[plugin_name]
        
        if plugin.status in (PluginStatus.RUNNING, PluginStatus.PAUSED):
            plugin.stop()
        
        del self.plugins[plugin_name]
        logger.info(f"Unloaded plugin: {plugin_name}")
        return True
    
    def start_plugin(self, plugin_name: str) -> bool:
        """
        Start a plugin
        
        Args:
            plugin_name: Name of plugin to start
        
        Returns:
            True if successful
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not loaded: {plugin_name}")
            return False
        
        return self.plugins[plugin_name].start()
    
    def pause_plugin(self, plugin_name: str) -> bool:
        """
        Pause a plugin
        
        Args:
            plugin_name: Name of plugin to pause
        
        Returns:
            True if successful
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not loaded: {plugin_name}")
            return False
        
        return self.plugins[plugin_name].pause()
    
    def resume_plugin(self, plugin_name: str) -> bool:
        """
        Resume a plugin
        
        Args:
            plugin_name: Name of plugin to resume
        
        Returns:
            True if successful
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not loaded: {plugin_name}")
            return False
        
        return self.plugins[plugin_name].resume()
    
    def stop_plugin(self, plugin_name: str) -> bool:
        """
        Stop a plugin
        
        Args:
            plugin_name: Name of plugin to stop
        
        Returns:
            True if successful
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not loaded: {plugin_name}")
            return False
        
        return self.plugins[plugin_name].stop()
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Get a plugin instance
        
        Args:
            plugin_name: Name of plugin
        
        Returns:
            Plugin instance or None
        """
        return self.plugins.get(plugin_name)
    
    def get_plugins(self) -> List[BasePlugin]:
        """
        Get all loaded plugins
        
        Returns:
            List of plugin instances
        """
        return list(self.plugins.values())
    
    def get_plugin_status(self, plugin_name: str = None) -> Dict[str, Any]:
        """
        Get plugin status
        
        Args:
            plugin_name: Specific plugin or None for all
        
        Returns:
            Status dictionary
        """
        if plugin_name:
            if plugin_name not in self.plugins:
                return {}
            return self.plugins[plugin_name].get_status()
        
        return {
            name: plugin.get_status()
            for name, plugin in self.plugins.items()
        }
    
    def get_plugins_summary(self) -> Dict[str, Any]:
        """
        Get summary of all plugins
        
        Returns:
            Summary with counts and status
        """
        plugins = list(self.plugins.values())
        
        return {
            "total_plugins": len(plugins),
            "running": sum(1 for p in plugins if p.status == PluginStatus.RUNNING),
            "paused": sum(1 for p in plugins if p.status == PluginStatus.PAUSED),
            "stopped": sum(1 for p in plugins if p.status == PluginStatus.STOPPED),
            "error": sum(1 for p in plugins if p.status == PluginStatus.ERROR),
            "plugins": [p.get_status() for p in plugins]
        }
    
    def register_metric_callback(self, callback: Callable) -> None:
        """
        Register callback for all plugin metrics
        
        Args:
            callback: Callback function(plugin_name, metrics)
        """
        self._callbacks.append(callback)
        
        # Register with already loaded plugins
        for plugin in self.plugins.values():
            plugin.on_metric(callback)
    
    def load_all_plugins(self) -> int:
        """
        Load all discovered plugins
        
        Returns:
            Number of successfully loaded plugins
        """
        discovered = self.discover_plugins()
        loaded = 0
        
        for plugin_name in discovered:
            if self.load_plugin(plugin_name):
                loaded += 1
        
        logger.info(f"Loaded {loaded}/{len(discovered)} plugins")
        return loaded
    
    def start_all_plugins(self) -> int:
        """
        Start all loaded plugins
        
        Returns:
            Number of started plugins
        """
        started = 0
        
        for plugin in self.plugins.values():
            if plugin.start():
                started += 1
        
        return started
    
    def stop_all_plugins(self) -> int:
        """
        Stop all loaded plugins
        
        Returns:
            Number of stopped plugins
        """
        stopped = 0
        
        for plugin in self.plugins.values():
            if plugin.stop():
                stopped += 1
        
        return stopped
    
    def pause_all_plugins(self) -> int:
        """
        Pause all running plugins
        
        Returns:
            Number of paused plugins
        """
        paused = 0
        
        for plugin in self.plugins.values():
            if plugin.status == PluginStatus.RUNNING:
                if plugin.pause():
                    paused += 1
        
        return paused
    
    def resume_all_plugins(self) -> int:
        """
        Resume all paused plugins
        
        Returns:
            Number of resumed plugins
        """
        resumed = 0
        
        for plugin in self.plugins.values():
            if plugin.status == PluginStatus.PAUSED:
                if plugin.resume():
                    resumed += 1
        
        return resumed
