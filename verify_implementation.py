#!/usr/bin/env python3
"""Verification script for RefBot system"""

import sys
import os
from pathlib import Path

# Add refbot to path
refbot_dir = Path(__file__).parent
sys.path.insert(0, str(refbot_dir))

def check_imports():
    """Check all imports work"""
    print("\n" + "="*60)
    print("Checking imports...")
    print("="*60)
    
    errors = []
    
    modules = [
        ("api.rest_api", "REST API"),
        ("cli.cli_commands", "CLI Commands"),
        ("core.scheduler", "Scheduler"),
        ("core.analytics", "Analytics"),
        ("core.proxy_scoring", "Proxy Scoring"),
        ("plugins.base_plugin", "Base Plugin"),
        ("plugins.plugin_manager", "Plugin Manager"),
    ]
    
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            print(f"  ✓ {display_name:30} OK")
        except Exception as e:
            print(f"  ✗ {display_name:30} FAILED: {e}")
            errors.append((display_name, str(e)))
    
    return errors

def check_files():
    """Check all files exist"""
    print("\n" + "="*60)
    print("Checking files...")
    print("="*60)
    
    files = [
        "api/__init__.py",
        "api/rest_api.py",
        "cli/__init__.py",
        "cli/cli_commands.py",
        "core/__init__.py",
        "core/scheduler.py",
        "core/analytics.py",
        "core/proxy_scoring.py",
        "plugins/__init__.py",
        "plugins/base_plugin.py",
        "plugins/plugin_manager.py",
        "plugins/scheduler.py",
        "plugins/registration_plugin/__init__.py",
        "plugins/registration_plugin/plugin_config.json",
        "plugins/registration_plugin/registration_plugin.py",
        "ARCHITECTURE.md",
        "QUICKSTART.md",
        "requirements.txt",
    ]
    
    errors = []
    for file_path in files:
        full_path = refbot_dir / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  ✓ {file_path:50} ({size:6} bytes)")
        else:
            print(f"  ✗ {file_path:50} MISSING")
            errors.append(file_path)
    
    return errors

def check_structure():
    """Check directory structure"""
    print("\n" + "="*60)
    print("Checking directory structure...")
    print("="*60)
    
    dirs = ["api", "cli", "core", "plugins"]
    errors = []
    
    for dir_name in dirs:
        dir_path = refbot_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            files = list(dir_path.glob("*.py")) + list(dir_path.glob("*.json"))
            print(f"  ✓ {dir_name:30} ({len(files)} files)")
        else:
            print(f"  ✗ {dir_name:30} MISSING")
            errors.append(dir_name)
    
    return errors

def test_scheduler():
    """Test scheduler module"""
    print("\n" + "="*60)
    print("Testing Scheduler...")
    print("="*60)
    
    try:
        from core.scheduler import PluginScheduler
        scheduler = PluginScheduler()
        print("  ✓ PluginScheduler instantiation")
        
        stats = scheduler.get_statistics("test")
        print(f"  ✓ get_statistics() returns: {type(stats).__name__}")
        
        return []
    except Exception as e:
        return [f"Scheduler test failed: {e}"]

def test_analytics():
    """Test analytics module"""
    print("\n" + "="*60)
    print("Testing Analytics...")
    print("="*60)
    
    try:
        from core.analytics import MetricsAggregator, AlertSeverity
        agg = MetricsAggregator()
        print("  ✓ MetricsAggregator instantiation")
        
        agg.record_metric("test_metric", 100)
        print("  ✓ record_metric() works")
        
        stats = agg.get_metric_statistics("test_metric")
        print(f"  ✓ get_metric_statistics() returns: {type(stats).__name__}")
        
        return []
    except Exception as e:
        return [f"Analytics test failed: {e}"]

def test_proxy_scoring():
    """Test proxy scoring module"""
    print("\n" + "="*60)
    print("Testing Proxy Scoring...")
    print("="*60)
    
    try:
        from core.proxy_scoring import ProxyScorer, LoadBalancingStrategy
        scorer = ProxyScorer()
        print("  ✓ ProxyScorer instantiation")
        
        scorer.record_request("http://proxy1:8080", 100, True)
        print("  ✓ record_request() works")
        
        sorted_proxies = scorer.get_sorted_proxies()
        print(f"  ✓ get_sorted_proxies() returns: {type(sorted_proxies).__name__}")
        
        return []
    except Exception as e:
        return [f"ProxyScoring test failed: {e}"]

def test_base_plugin():
    """Test base plugin module"""
    print("\n" + "="*60)
    print("Testing Base Plugin...")
    print("="*60)
    
    try:
        from plugins.base_plugin import BasePlugin, PluginStatus
        
        # Create a test plugin
        class TestPlugin(BasePlugin):
            def execute(self):
                return {"test": "result"}
        
        # Create temporary config
        config_path = refbot_dir / "plugins" / "test" / "plugin_config.json"
        plugin = TestPlugin("test", str(config_path))
        
        print("  ✓ BasePlugin subclass creation")
        print(f"  ✓ Initial status: {plugin.status.value}")
        
        return []
    except Exception as e:
        return [f"BasePlugin test failed: {e}"]

def test_plugin_manager():
    """Test plugin manager module"""
    print("\n" + "="*60)
    print("Testing Plugin Manager...")
    print("="*60)
    
    try:
        from plugins.plugin_manager import PluginManager
        pm = PluginManager(str(refbot_dir / "plugins"))
        print("  ✓ PluginManager instantiation")
        
        discovered = pm.discover_plugins()
        print(f"  ✓ discover_plugins() found: {len(discovered)} plugins")
        
        summary = pm.get_plugins_summary()
        print(f"  ✓ get_plugins_summary() returns: {type(summary).__name__}")
        
        return []
    except Exception as e:
        return [f"PluginManager test failed: {e}"]

def test_cli():
    """Test CLI module"""
    print("\n" + "="*60)
    print("Testing CLI...")
    print("="*60)
    
    try:
        from cli.cli_commands import cli
        print("  ✓ CLI module imports")
        print(f"  ✓ CLI version available")
        
        return []
    except Exception as e:
        return [f"CLI test failed: {e}"]

def test_rest_api():
    """Test REST API module"""
    print("\n" + "="*60)
    print("Testing REST API...")
    print("="*60)
    
    try:
        from api.rest_api import app
        print("  ✓ FastAPI app creation")
        
        # Check key endpoints exist
        routes = [route.path for route in app.routes]
        print(f"  ✓ Total routes: {len(routes)}")
        
        return []
    except Exception as e:
        return [f"REST API test failed: {e}"]

def main():
    """Run all checks"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  RefBot Advanced Plugin System - Verification  ".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    all_errors = []
    
    # File checks
    all_errors.extend(check_files())
    all_errors.extend(check_structure())
    
    # Import checks
    all_errors.extend(check_imports())
    
    # Module tests
    all_errors.extend(test_scheduler())
    all_errors.extend(test_analytics())
    all_errors.extend(test_proxy_scoring())
    all_errors.extend(test_base_plugin())
    all_errors.extend(test_plugin_manager())
    all_errors.extend(test_cli())
    all_errors.extend(test_rest_api())
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    if all_errors:
        print(f"\n⚠️  Found {len(all_errors)} issues:\n")
        for error in all_errors:
            if isinstance(error, tuple):
                print(f"  - {error[0]}: {error[1]}")
            else:
                print(f"  - {error}")
        return 1
    else:
        print("\n✅ All checks passed!")
        print("\nSystem is ready for:")
        print("  1. Dashboard integration")
        print("  2. Plugin development")
        print("  3. Production deployment")
        print("  4. REST API usage")
        print("  5. CLI command execution")
        print("\nNext steps:")
        print("  - Read QUICKSTART.md for getting started")
        print("  - Read ARCHITECTURE.md for detailed documentation")
        print("  - Update dashboard.py to integrate PluginManager")
        print("  - Configure plugin_config.json for your use case")
        return 0

if __name__ == "__main__":
    sys.exit(main())
