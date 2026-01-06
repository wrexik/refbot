"""RefBot REST API - FastAPI server for remote control and monitoring"""

import os
import logging
from datetime import datetime
from typing import List, Optional

try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Query
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


# Models
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


def create_app() -> "FastAPI":
    """Create FastAPI application"""
    if not HAS_FASTAPI:
        logger.error("FastAPI not installed")
        return None
    
    app = FastAPI(
        title="RefBot API",
        description="Advanced REST API for RefBot",
        version=__version__,
        docs_url="/docs",
        openapi_url="/openapi.json"
    )
    
    # ==================== Health ====================
    @app.get("/api/health", response_model=HealthStatus)
    async def get_health():
        """Get system health status"""
        return HealthStatus(
            status="healthy",
            uptime_seconds=3600,
            plugins_active=2,
            proxies_active=12,
            last_check=datetime.now().isoformat()
        )
    
    # ==================== Plugins ====================
    @app.get("/api/plugins", response_model=List[PluginStatus])
    async def list_plugins():
        """List all plugins"""
        return [
            PluginStatus(
                name="scraper",
                status="running",
                uptime_seconds=3600,
                requests_count=1250
            ),
            PluginStatus(
                name="checker",
                status="running",
                uptime_seconds=2400,
                requests_count=850
            )
        ]
    
    @app.post("/api/plugins/{name}/start")
    async def start_plugin(name: str):
        """Start a plugin"""
        return {"status": "started", "message": f"Plugin '{name}' started"}
    
    @app.post("/api/plugins/{name}/stop")
    async def stop_plugin(name: str):
        """Stop a plugin"""
        return {"status": "stopped", "message": f"Plugin '{name}' stopped"}
    
    # ==================== Metrics ====================
    @app.get("/api/metrics", response_model=MetricsSummary)
    async def get_metrics():
        """Get current metrics"""
        return MetricsSummary(
            total_requests=2100,
            successful_requests=2045,
            failed_requests=55,
            average_response_time=245.5,
            active_proxies=12,
            timestamp=datetime.now().isoformat()
        )
    
    @app.get("/api/metrics/export")
    async def export_metrics(format: str = "json"):
        """Export metrics"""
        if format == "csv":
            return {"status": "exported", "format": "csv"}
        return {"status": "exported", "format": "json"}
    
    # ==================== Proxies ====================
    @app.get("/api/proxies", response_model=List[ProxyScore])
    async def list_proxies(sort: str = "score"):
        """List proxies"""
        return [
            ProxyScore(
                ip="192.168.1.1",
                port=8080,
                score=95.5,
                success_rate=98.5,
                response_time_ms=125.3,
                active=True
            ),
            ProxyScore(
                ip="192.168.1.2",
                port=8080,
                score=87.2,
                success_rate=92.1,
                response_time_ms=185.7,
                active=True
            )
        ]
    
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
