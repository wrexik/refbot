"""RefBot REST API - FastAPI server for remote control and monitoring"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

# Add parent directory to path to import RefBot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Query
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    HAS_FASTAPI = True
    
    # Models (must be inside try block since they use BaseModel)
    class HealthStatus(BaseModel):
        """System health status"""
        status: str
        uptime_seconds: int
        plugins_active: int
        proxies_active: int
        last_check: str


    class PluginStatus(BaseModel):
        """Plugin status"""
        name: str
        status: str
        uptime_seconds: int
        requests_count: int
        last_error: Optional[str] = None


    class MetricsSummary(BaseModel):
        """Metrics summary"""
        total_requests: int
        successful_requests: int
        failed_requests: int
        average_response_time: float
        active_proxies: int
        timestamp: str


    class ProxyScore(BaseModel):
        """Proxy score"""
        ip: str
        port: int
        score: float
        success_rate: float
        response_time_ms: float
        active: bool
        
except ImportError:
    HAS_FASTAPI = False
    # Provide dummy classes when FastAPI not installed
    class HealthStatus: pass
    class PluginStatus: pass
    class MetricsSummary: pass
    class ProxyScore: pass

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


def create_app(plugin_manager=None, proxy_manager=None, config=None) -> "FastAPI":
    """Create FastAPI application with system integration"""
    if not HAS_FASTAPI:
        logger.error("FastAPI not installed")
        return None
    
    # Import RefBot components
    if plugin_manager is None:
        from plugins.plugin_manager import PluginManager
        plugin_manager = PluginManager()
        plugin_manager.discover_plugins()
        plugin_manager.load_all_plugins()
    
    if proxy_manager is None:
        from proxy_manager import ProxyManager
        import json
        config_data = json.load(open("config.json")) if config is None else config
        state_file = config_data.get("proxy_state_file", "working_proxies.json")
        proxy_manager = ProxyManager(state_file=state_file)
        proxy_manager.load_from_file()
    
    app = FastAPI(
        title="RefBot API",
        description="Advanced REST API for RefBot proxy and plugin management",
        version=__version__,
        docs_url="/docs",
        openapi_url="/openapi.json"
    )
    
    # Store managers in app state
    app.state.plugin_manager = plugin_manager
    app.state.proxy_manager = proxy_manager
    app.state.start_time = datetime.now()
    
    # ==================== Health ====================
    @app.get("/api/health", response_model=HealthStatus)
    async def get_health():
        """Get system health status"""
        uptime = (datetime.now() - app.state.start_time).total_seconds()
        status_info = app.state.plugin_manager.get_status()
        stats = app.state.proxy_manager.get_stats()
        
        return HealthStatus(
            status="healthy",
            uptime_seconds=int(uptime),
            plugins_active=status_info.get("running", 0),
            proxies_active=stats.get("working_proxies", 0),
            last_check=datetime.now().isoformat()
        )
    
    # ==================== Plugins ====================
    @app.get("/api/plugins", response_model=List[PluginStatus])
    async def list_plugins():
        """List all plugins"""
        plugins = []
        for name, plugin in app.state.plugin_manager.get_all_plugins().items():
            metrics = plugin.get_metrics()
            uptime = (datetime.now() - plugin.start_time).total_seconds() if plugin.start_time else 0
            
            plugins.append(PluginStatus(
                name=name,
                status=plugin.status.value,
                uptime_seconds=int(uptime),
                requests_count=metrics.requests_total if metrics else 0,
                last_error=metrics.last_error if metrics else None
            ))
        return plugins
    
    @app.get("/api/plugins/{name}/status", response_model=PluginStatus)
    async def get_plugin_status(name: str):
        """Get status of a specific plugin"""
        plugin = app.state.plugin_manager.get_plugin(name)
        if not plugin:
            raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
        
        metrics = plugin.get_metrics()
        uptime = (datetime.now() - plugin.start_time).total_seconds() if plugin.start_time else 0
        
        return PluginStatus(
            name=name,
            status=plugin.status.value,
            uptime_seconds=int(uptime),
            requests_count=metrics.requests_total if metrics else 0,
            last_error=metrics.last_error if metrics else None
        )
    
    @app.post("/api/plugins/{name}/start")
    async def start_plugin(name: str):
        """Start a plugin"""
        success = app.state.plugin_manager.start_plugin(name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to start plugin '{name}'")
        return {"status": "started", "message": f"Plugin '{name}' started successfully"}
    
    @app.post("/api/plugins/{name}/stop")
    async def stop_plugin(name: str):
        """Stop a plugin"""
        success = app.state.plugin_manager.stop_plugin(name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to stop plugin '{name}'")
        return {"status": "stopped", "message": f"Plugin '{name}' stopped successfully"}
    
    @app.post("/api/plugins/{name}/pause")
    async def pause_plugin(name: str):
        """Pause a plugin"""
        success = app.state.plugin_manager.pause_plugin(name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to pause plugin '{name}'")
        return {"status": "paused", "message": f"Plugin '{name}' paused successfully"}
    
    @app.post("/api/plugins/{name}/resume")
    async def resume_plugin(name: str):
        """Resume a plugin"""
        success = app.state.plugin_manager.resume_plugin(name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to resume plugin '{name}'")
        return {"status": "resumed", "message": f"Plugin '{name}' resumed successfully"}
    
    @app.post("/api/plugins/start-all")
    async def start_all_plugins():
        """Start all plugins"""
        results = app.state.plugin_manager.start_all_plugins()
        return {"status": "started", "message": "All plugins started", "results": results}
    
    @app.post("/api/plugins/stop-all")
    async def stop_all_plugins():
        """Stop all plugins"""
        results = app.state.plugin_manager.stop_all_plugins()
        return {"status": "stopped", "message": "All plugins stopped", "results": results}
    
    @app.post("/api/plugins/pause-all")
    async def pause_all_plugins():
        """Pause all plugins"""
        results = app.state.plugin_manager.pause_all_plugins()
        return {"status": "paused", "message": "All plugins paused", "results": results}
    
    @app.post("/api/plugins/resume-all")
    async def resume_all_plugins():
        """Resume all plugins"""
        results = app.state.plugin_manager.resume_all_plugins()
        return {"status": "resumed", "message": "All plugins resumed", "results": results}
    
    # ==================== Metrics ====================
    @app.get("/api/metrics", response_model=MetricsSummary)
    async def get_metrics():
        """Get current metrics"""
        stats = app.state.proxy_manager.get_stats()
        
        return MetricsSummary(
            total_requests=stats.get("total_checks", 0),
            successful_requests=stats.get("working_proxies", 0),
            failed_requests=stats.get("failed_proxies", 0),
            average_response_time=stats.get("avg_response_time", 0.0),
            active_proxies=stats.get("working_proxies", 0),
            timestamp=datetime.now().isoformat()
        )
    
    @app.get("/api/metrics/export")
    async def export_metrics(format: str = "json"):
        """Export metrics"""
        stats = app.state.proxy_manager.get_stats()
        if format == "csv":
            return {"status": "exported", "format": "csv", "data": stats}
        return {"status": "exported", "format": "json", "data": stats}
    
    # ==================== Proxies ====================
    @app.get("/api/proxies", response_model=List[ProxyScore])
    async def list_proxies(sort: str = "score", limit: int = 50):
        """List proxies"""
        proxies = app.state.proxy_manager.get_proxies()
        
        # Sort by score
        if sort == "score":
            proxies = sorted(proxies, key=lambda p: p.score, reverse=True)
        elif sort == "speed":
            proxies = sorted(proxies, key=lambda p: p.speed)
        
        # Convert to API model
        result = []
        for proxy in proxies[:limit]:
            result.append(ProxyScore(
                ip=proxy.address.split(':')[0],
                port=int(proxy.address.split(':')[1]),
                score=proxy.score,
                success_rate=proxy.success_rate * 100,
                response_time_ms=proxy.speed * 1000,
                active=proxy.working
            ))
        
        return result
    
    # ==================== Root ====================
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "RefBot API",
            "version": __version__,
            "status": "active",
            "documentation": "/docs"
        }
    
    return app


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the API server"""
    if not HAS_FASTAPI:
        logger.error("FastAPI not installed. Install with: pip install fastapi uvicorn")
        return
    
    try:
        import uvicorn
        app = create_app()
        
        logger.info(f"Starting API server on {host}:{port}")
        logger.info(f"Documentation: http://{host}:{port}/docs")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to run API server: {e}")


if __name__ == "__main__":
    run_server()
