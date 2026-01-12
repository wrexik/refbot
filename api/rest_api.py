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
        try:
            from plugins.plugin_manager import PluginManager
            plugin_manager = PluginManager()
            plugin_manager.discover_plugins()
            plugin_manager.load_all_plugins()
        except Exception as e:
            logger.warning(f"Failed to initialize plugin manager: {e}")
            # Create empty plugin manager
            class EmptyPluginManager:
                def get_all_plugins(self): return {}
                def get_plugin(self, name): return None
                def start_plugin(self, name): return False
                def stop_plugin(self, name): return False
                def pause_plugin(self, name): return False
                def resume_plugin(self, name): return False
                def start_all_plugins(self): return {}
                def stop_all_plugins(self): return {}
                def pause_all_plugins(self): return {}
                def resume_all_plugins(self): return {}
            plugin_manager = EmptyPluginManager()
    
    if proxy_manager is None:
        try:
            from proxy_manager import ProxyManager
            import json
            
            # Try to load config
            config_file = Path("config.json")
            if config_file.exists():
                config_data = json.load(open(config_file))
            else:
                config_data = {}
            
            state_file = config_data.get("proxy_state_file", "working_proxies.json")
            proxy_manager = ProxyManager(state_file=state_file)
            
            # Try to load from file
            if Path(state_file).exists():
                proxy_manager.load_from_file()
        except Exception as e:
            logger.warning(f"Failed to initialize proxy manager: {e}")
            # Create minimal proxy manager
            class EmptyProxyManager:
                def get_stats(self): 
                    return {"working_count": 0, "testing_count": 0, "failed_count": 0, "average_speed": 0.0}
                def get_working(self, protocol="ANY"): 
                    return []
            proxy_manager = EmptyProxyManager()
    
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
        try:
            uptime = (datetime.now() - app.state.start_time).total_seconds()
            
            # Get plugin status
            plugins_active = 0
            try:
                all_plugins = app.state.plugin_manager.get_all_plugins()
                plugins_active = sum(1 for p in all_plugins.values() if p.status == PluginStatus.RUNNING)
            except Exception as e:
                logger.warning(f"Error getting plugin status: {e}")
            
            # Get proxy stats
            proxies_active = 0
            try:
                stats = app.state.proxy_manager.get_stats()
                proxies_active = stats.get("working_count", 0)
            except Exception as e:
                logger.warning(f"Error getting proxy stats: {e}")
            
            return HealthStatus(
                status="healthy",
                uptime_seconds=int(uptime),
                plugins_active=plugins_active,
                proxies_active=proxies_active,
                last_check=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Health check error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== Plugins ====================
    @app.get("/api/plugins", response_model=List[PluginStatus])
    async def list_plugins():
        """List all plugins"""
        try:
            plugins = []
            all_plugins = app.state.plugin_manager.get_all_plugins()
            
            for name, plugin in all_plugins.items():
                try:
                    metrics = plugin.get_metrics() if hasattr(plugin, 'get_metrics') else None
                    uptime = (datetime.now() - plugin.start_time).total_seconds() if hasattr(plugin, 'start_time') and plugin.start_time else 0
                    
                    plugins.append(PluginStatus(
                        name=name,
                        status=plugin.status.value if hasattr(plugin.status, 'value') else str(plugin.status),
                        uptime_seconds=int(uptime),
                        requests_count=metrics.requests_total if metrics and hasattr(metrics, 'requests_total') else 0,
                        last_error=metrics.last_error if metrics and hasattr(metrics, 'last_error') else None
                    ))
                except Exception as e:
                    logger.warning(f"Error getting plugin {name} status: {e}")
                    
            return plugins
        except Exception as e:
            logger.error(f"List plugins error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/plugins/{name}/status", response_model=PluginStatus)
    async def get_plugin_status(name: str):
        """Get status of a specific plugin"""
        try:
            plugin = app.state.plugin_manager.get_plugin(name)
            if not plugin:
                raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
            
            metrics = plugin.get_metrics() if hasattr(plugin, 'get_metrics') else None
            uptime = (datetime.now() - plugin.start_time).total_seconds() if hasattr(plugin, 'start_time') and plugin.start_time else 0
            
            return PluginStatus(
                name=name,
                status=plugin.status.value if hasattr(plugin.status, 'value') else str(plugin.status),
                uptime_seconds=int(uptime),
                requests_count=metrics.requests_total if metrics and hasattr(metrics, 'requests_total') else 0,
                last_error=metrics.last_error if metrics and hasattr(metrics, 'last_error') else None
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get plugin status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/{name}/start")
    async def start_plugin(name: str):
        """Start a plugin"""
        try:
            success = app.state.plugin_manager.start_plugin(name)
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to start plugin '{name}'")
            return {"status": "started", "message": f"Plugin '{name}' started successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Start plugin error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/{name}/stop")
    async def stop_plugin(name: str):
        """Stop a plugin"""
        try:
            success = app.state.plugin_manager.stop_plugin(name)
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to stop plugin '{name}'")
            return {"status": "stopped", "message": f"Plugin '{name}' stopped successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Stop plugin error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/{name}/pause")
    async def pause_plugin(name: str):
        """Pause a plugin"""
        try:
            success = app.state.plugin_manager.pause_plugin(name)
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to pause plugin '{name}'")
            return {"status": "paused", "message": f"Plugin '{name}' paused successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Pause plugin error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/{name}/resume")
    async def resume_plugin(name: str):
        """Resume a plugin"""
        try:
            success = app.state.plugin_manager.resume_plugin(name)
            if not success:
                raise HTTPException(status_code=400, detail=f"Failed to resume plugin '{name}'")
            return {"status": "resumed", "message": f"Plugin '{name}' resumed successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Resume plugin error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/start-all")
    async def start_all_plugins():
        """Start all plugins"""
        try:
            results = app.state.plugin_manager.start_all_plugins()
            return {"status": "started", "message": "All plugins started", "results": results}
        except Exception as e:
            logger.error(f"Start all plugins error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/stop-all")
    async def stop_all_plugins():
        """Stop all plugins"""
        try:
            results = app.state.plugin_manager.stop_all_plugins()
            return {"status": "stopped", "message": "All plugins stopped", "results": results}
        except Exception as e:
            logger.error(f"Stop all plugins error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/pause-all")
    async def pause_all_plugins():
        """Pause all plugins"""
        try:
            results = app.state.plugin_manager.pause_all_plugins()
            return {"status": "paused", "message": "All plugins paused", "results": results}
        except Exception as e:
            logger.error(f"Pause all plugins error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/plugins/resume-all")
    async def resume_all_plugins():
        """Resume all plugins"""
        try:
            results = app.state.plugin_manager.resume_all_plugins()
            return {"status": "resumed", "message": "All plugins resumed", "results": results}
        except Exception as e:
            logger.error(f"Resume all plugins error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== Metrics ====================
    @app.get("/api/metrics", response_model=MetricsSummary)
    async def get_metrics():
        """Get current metrics"""
        try:
            stats = app.state.proxy_manager.get_stats()
            
            return MetricsSummary(
                total_requests=stats.get("testing_count", 0) + stats.get("working_count", 0) + stats.get("failed_count", 0),
                successful_requests=stats.get("working_count", 0),
                failed_requests=stats.get("failed_count", 0),
                average_response_time=stats.get("average_speed", 0.0),
                active_proxies=stats.get("working_count", 0),
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Get metrics error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/metrics/export")
    async def export_metrics(format: str = "json"):
        """Export metrics"""
        stats = app.state.proxy_manager.get_stats()
        if format == "csv":
            return {"status": "exported", "format": "csv", "data": stats}
        return {"status": "exported", "format": "json", "data": stats}
    
    # ==================== Proxies ====================
    @app.get("/api/proxies", response_model=List[ProxyScore])
    async def list_proxies(sort: str = "speed", limit: int = 50):
        """List proxies"""
        try:
            # Get working proxies
            proxies = app.state.proxy_manager.get_working()
            
            # Sort proxies
            if sort == "speed":
                proxies = sorted(proxies, key=lambda p: p.speed if p.speed > 0 else 999)
            elif sort == "score":
                # Calculate simple score based on speed
                proxies = sorted(proxies, key=lambda p: p.speed if p.speed > 0 else 999)
            
            # Convert to API model
            result = []
            for proxy in proxies[:limit]:
                try:
                    # Calculate success rate based on failed count
                    success_rate = max(0, 100 - (proxy.failed_count * 10))
                    
                    # Calculate score (lower speed is better)
                    score = max(0, 100 - (proxy.speed * 10))
                    
                    result.append(ProxyScore(
                        ip=proxy.ip,
                        port=proxy.port,
                        score=score,
                        success_rate=success_rate,
                        response_time_ms=proxy.speed * 1000,
                        active=proxy.is_working
                    ))
                except Exception as e:
                    logger.warning(f"Error converting proxy {proxy.address}: {e}")
            
            return result
        except Exception as e:
            logger.error(f"List proxies error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
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
        
        logger.info(f"Starting API server on {host}:{port}")
        logger.info(f"Documentation: http://{host}:{port}/docs")
        
        # Use the factory function to create app
        uvicorn.run(
            "api.rest_api:create_app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            factory=True
        )
    except Exception as e:
        logger.error(f"Failed to run API server: {e}")
        import traceback
        traceback.print_exc()


# Create app instance for direct uvicorn usage
app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()

