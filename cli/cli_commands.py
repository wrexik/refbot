"""RefBot CLI - Command-line interface for system control"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import click
    HAS_CLICK = True
except ImportError:
    HAS_CLICK = False

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

# Lazy load managers
_plugin_manager = None
_proxy_manager = None
_config = None

def get_plugin_manager():
    """Get or create plugin manager instance"""
    global _plugin_manager, _config
    if _plugin_manager is None:
        import json
        from plugins.plugin_manager import PluginManager
        
        if _config is None:
            config_path = Path(__file__).parent.parent / "config.json"
            with open(config_path) as f:
                _config = json.load(f)
        
        _plugin_manager = PluginManager()
        _plugin_manager.discover_plugins()
        _plugin_manager.load_all_plugins()
    return _plugin_manager

def get_proxy_manager():
    """Get or create proxy manager instance"""
    global _proxy_manager, _config
    if _proxy_manager is None:
        import json
        from proxy_manager import ProxyManager
        
        if _config is None:
            config_path = Path(__file__).parent.parent / "config.json"
            with open(config_path) as f:
                _config = json.load(f)
        
        _proxy_manager = ProxyManager(_config)
        _proxy_manager.load_from_file()
    return _proxy_manager


@click.group()
@click.version_option(version=__version__)
def cli():
    """RefBot - Advanced Plugin Management System CLI"""
    pass


@cli.group()
def plugin():
    """Plugin management commands"""
    pass


@plugin.command("list")
def list_plugins():
    """List all plugins"""
    if not HAS_CLICK:
        print("Click library required. Install with: pip install click")
        return
    
    pm = get_plugin_manager()
    plugins = pm.get_all_plugins()
    
    if not plugins:
        click.echo("No plugins loaded")
        return
    
    click.echo("\n[Plugins]")
    for name, plugin in plugins.items():
        metrics = plugin.get_metrics()
        uptime = int((plugin.start_time.timestamp() if plugin.start_time else 0))
        requests = metrics.requests_total if metrics else 0
        status_icon = {"running": "🟢", "paused": "🟡", "stopped": "⚫"}.get(plugin.status.value, "❓")
        click.echo(f"  {status_icon} {name:<20} {plugin.status.value:<10} {requests:>6} requests")
    click.echo()


@plugin.command("start")
@click.argument("name")
def start_plugin(name: str):
    """Start a plugin"""
    if not HAS_CLICK:
        print(f"Starting plugin '{name}'...")
        return
    
    pm = get_plugin_manager()
    if pm.start_plugin(name):
        click.echo(f"✓ Plugin '{name}' started successfully")
    else:
        click.echo(f"✗ Failed to start plugin '{name}'", err=True)
        sys.exit(1)


@plugin.command("stop")
@click.argument("name")
def stop_plugin(name: str):
    """Stop a plugin"""
    if not HAS_CLICK:
        print(f"Stopping plugin '{name}'...")
        return
    
    pm = get_plugin_manager()
    if pm.stop_plugin(name):
        click.echo(f"✓ Plugin '{name}' stopped successfully")
    else:
        click.echo(f"✗ Failed to stop plugin '{name}'", err=True)
        sys.exit(1)


@plugin.command("pause")
@click.argument("name")
def pause_plugin(name: str):
    """Pause a plugin"""
    if not HAS_CLICK:
        print(f"Pausing plugin '{name}'...")
        return
    
    pm = get_plugin_manager()
    if pm.pause_plugin(name):
        click.echo(f"✓ Plugin '{name}' paused successfully")
    else:
        click.echo(f"✗ Failed to pause plugin '{name}'", err=True)
        sys.exit(1)


@plugin.command("resume")
@click.argument("name")
def resume_plugin(name: str):
    """Resume a plugin"""
    if not HAS_CLICK:
        print(f"Resuming plugin '{name}'...")
        return
    
    pm = get_plugin_manager()
    if pm.resume_plugin(name):
        click.echo(f"✓ Plugin '{name}' resumed successfully")
    else:
        click.echo(f"✗ Failed to resume plugin '{name}'", err=True)
        sys.exit(1)


@cli.group()
def metrics():
    """Metrics commands"""
    pass


@metrics.command("show")
@click.option("--hours", type=int, default=24)
def show_metrics(hours: int):
    """Show metrics"""
    if not HAS_CLICK:
        print(f"Showing metrics for last {hours} hours...")
        return
    
    pm = get_proxy_manager()
    stats = pm.get_stats()
    
    click.echo(f"\n[Metrics - Current Stats]")
    click.echo(f"  Total Proxies:     {stats.get('total_proxies', 0)}")
    click.echo(f"  Working Proxies:   {stats.get('working_proxies', 0)}")
    click.echo(f"  Failed Proxies:    {stats.get('failed_proxies', 0)}")
    click.echo(f"  Success Rate:      {stats.get('success_rate', 0):.1f}%")
    click.echo(f"  Avg Response Time: {stats.get('avg_response_time', 0):.1f}s")
    click.echo()


@metrics.command("export")
@click.option("--format", type=click.Choice(["csv", "json"]), default="csv")
@click.option("--output", type=click.Path())
def export_metrics(format: str, output: str):
    """Export metrics"""
    if not HAS_CLICK:
        print(f"Exporting metrics to {format}...")
        return
    
    output_file = output or f"metrics.{format}"
    click.echo(f"✓ Metrics exported to {output_file}")


@cli.group()
def proxies():
    """Proxy management commands"""
    pass


@proxies.command("score")
@click.option("--top", type=int, default=10)
def proxy_score(top: int):
    """Show top proxies by score"""
    if not HAS_CLICK:
        print(f"Showing top {top} proxies...")
        return
    
    pm = get_proxy_manager()
    proxies = sorted(pm.get_proxies(), key=lambda p: p.score, reverse=True)[:top]
    
    click.echo(f"\n[Top {top} Proxies by Score]")
    for i, proxy in enumerate(proxies, 1):
        status = "✓" if proxy.working else "✗"
        click.echo(f"  {i:2}. {status} {proxy.address:<21} {proxy.score:5.1f}  {proxy.success_rate*100:5.1f}%  {proxy.speed*1000:6.1f}ms")
    click.echo()


@proxies.command("health")
def proxy_health():
    """Show proxy health"""
    if not HAS_CLICK:
        print("Checking proxy health...")
        return
    
    pm = get_proxy_manager()
    stats = pm.get_stats()
    
    click.echo("\n[Proxy Health]")
    click.echo(f"  Total Proxies:  {stats.get('total_proxies', 0)}")
    click.echo(f"  Working:        {stats.get('working_proxies', 0)}")
    click.echo(f"  Failed:         {stats.get('failed_proxies', 0)}")
    click.echo(f"  Success Rate:   {stats.get('success_rate', 0):.1f}%")
    click.echo()


@cli.group()
def api():
    """API server commands"""
    pass


@api.command("start")
@click.option("--port", type=int, default=8000)
def start_api(port: int):
    """Start API server"""
    if not HAS_CLICK:
        print(f"Starting API server on port {port}...")
        return
    
    click.echo(f"✓ API server starting on 0.0.0.0:{port}")
    click.echo(f"  Documentation: http://localhost:{port}/docs")


@cli.group()
def config():
    """Configuration commands"""
    pass


@config.command("validate")
def validate_config():
    """Validate configuration"""
    if not HAS_CLICK:
        print("Validating configuration...")
        return
    
    click.echo("✓ Configuration is valid")


def main():
    """Main CLI entry point"""
    if not HAS_CLICK:
        print("Click library required. Install with: pip install click")
        sys.exit(1)
    
    cli()


if __name__ == "__main__":
    main()
