# RefBot Architecture

This document provides a comprehensive overview of RefBot's system architecture, including core modules, plugin system, API design, and integration patterns.

## Table of Contents

- [System Overview](#system-overview)
- [Core Modules](#core-modules)
- [Plugin System](#plugin-system)
- [API Design](#api-design)
- [CLI Interface](#cli-interface)
- [Data Flow](#data-flow)
- [Configuration](#configuration)
- [Integration Patterns](#integration-patterns)

## System Overview

RefBot is built on a modular, extensible architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │   REST API   │  │  CLI Interface│      │
│  │  (Rich UI)   │  │  (FastAPI)   │  │   (Click)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                  Orchestration Layer                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Plugin Manager                             │   │
│  │  (Lifecycle, Discovery, Scheduling)                   │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     Core Services                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Proxy   │ │ Worker   │ │Scheduler │ │Analytics │       │
│  │ Manager  │ │ Threads  │ │          │ │          │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │  Proxy   │ │Persisten-│ │ Scraper  │                    │
│  │  Scorer  │ │   ce     │ │          │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules
### proxy_manager.py

**Purpose**: Thread-safe proxy storage and management.

**Key Components**:
- `ProxyManager`: Centralized proxy database with RLock protection
- `Proxy`: Dataclass representing proxy metadata (IP, port, protocol, response time, status)

**Responsibilities**:
- Store and retrieve proxy instances
- Filter proxies by protocol (HTTP/HTTPS/BOTH)
- Track proxy status (testing, working, failed)
- Calculate aggregate statistics
- Provide top-performing proxies

**Thread Safety**: All operations protected by threading.RLock.

### worker_threads.py

**Purpose**: Concurrent proxy scraping and validation.

**Key Components**:
- `WorkerThreads`: Orchestrates multiple background workers
- Scraper thread: Fetches proxies from 38 sources
- HTTP validator thread: Validates HTTP protocol support (200 workers)
- HTTPS validator thread: Validates HTTPS protocol support (200 workers)
- Auto-save thread: Persists state every 10 seconds

**Concurrency Model**:
- ThreadPoolExecutor for validation workers
- Generator-based streaming for memory efficiency
- Queue-based communication between threads

### checker.py

**Purpose**: Proxy validation logic.

**Key Functions**:
- `validate_http_proxy()`: Tests HTTP protocol support
- `validate_https_proxy()`: Tests HTTPS protocol support
- `check_proxy_health()`: Comprehensive health check

**Validation Process**:
1. Attempt connection to target URL
2. Measure response time
3. Verify successful response (200 status)
4. Update proxy status and metadata

**Timeout Handling**: Configurable timeouts with retry logic.

### scraper.py

**Purpose**: Multi-source proxy aggregation.

**Key Features**:
- 38+ proxy sources (public lists, APIs)
- Generator-based streaming (memory efficient)
- Concurrent fetching with ThreadPoolExecutor
- Duplicate detection and filtering

**Source Types**:
- Static proxy lists
- Dynamic APIs
- Rotating proxy services
- Community-maintained sources

### persistence.py

**Purpose**: State management and metrics export.

**Key Components**:
- `PersistenceManager`: JSON-based state persistence
- `MetricsExporter`: CSV metrics export

**Persisted Data**:
- Proxy inventory with metadata
- Validation history
- Performance metrics
- Configuration snapshots

**Export Formats**: JSON (state), CSV (metrics)

### dashboard.py

**Purpose**: Interactive Rich-based terminal UI.

**Key Features**:
- 7 information panels (header, stats, config, protocols, proxies, loading, logs)
- 1 Hz refresh rate (configurable)
- Keyboard navigation and controls
- Color-coded event logging
- Live metrics visualization

**Panels**:
1. **Header**: Time, uptime, operational mode
2. **Statistics**: Proxy counts and averages
3. **Configuration**: Active settings
4. **Protocol Distribution**: HTTP/HTTPS/BOTH breakdown with progress bars
5. **Top Proxies**: Fastest 8 proxies with response times
6. **Loading Status**: Page loader state
7. **Event Log**: 20-line scrolling activity stream

### core/scheduler.py

**Purpose**: Advanced job scheduling with APScheduler.

**Key Features**:
- Cron expression support (`*/5 * * * *` format)
- Exponential backoff retry logic (configurable multiplier)
- Execution history tracking (max 1000 records)
- Success/failure callbacks
- Thread-safe with RLock

**Key Classes**:
- `PluginScheduler`: Main scheduler
- `ScheduleConfig`: Schedule configuration dataclass
- `ExecutionRecord`: Execution history record
- `ExecutionStatus`: Enum (SUCCESS, FAILED, CANCELLED, RETRYING)

### core/analytics.py

**Purpose**: Real-time metrics aggregation with alerting.

**Key Features**:
- Time-series metrics storage with retention
- Threshold-based alerting (upper/lower bounds)
- Anomaly detection (Z-score and IQR methods)
- Trend analysis with moving averages
- Reliability scoring (0-100)
- CSV/JSON export

**Key Classes**:
- `MetricsAggregator`: Main metrics engine
- `Alert`: Alert data structure
- `AlertSeverity`: Enum (INFO, WARNING, CRITICAL)

**Analysis Methods**:
- `detect_anomalies()`: Statistical anomaly detection
- `get_trend_analysis()`: Moving average trends
- `get_success_rate()`: Success rate calculation

### core/proxy_scoring.py

**Purpose**: Intelligent proxy ranking and health monitoring.

**Key Features**:
- Weighted scoring algorithm (40% success, 30% speed, 30% reliability)
- Circuit breaker pattern (CLOSED, OPEN, HALF_OPEN states)
- 4 load balancing strategies
- Automatic health state transitions
- Failover chain management

**Key Classes**:
- `ProxyScorer`: Main scoring engine
- `ProxyScore`: Individual proxy metrics
- `LoadBalancingStrategy`: Enum (ROUND_ROBIN, LEAST_LOADED, WEIGHTED, RANDOM)
- `CircuitState`: Enum (CLOSED, OPEN, HALF_OPEN)

**Scoring Algorithm**:
```
score = (success_rate * 0.4) + (speed_score * 0.3) + (reliability * 0.3)
```

### plugins/base_plugin.py

**Purpose**: Abstract base class for all plugins.

**Key Features**:
- Plugin lifecycle methods: `start()`, `pause()`, `resume()`, `stop()`
- Status tracking (IDLE, RUNNING, PAUSED, STOPPED, ERROR)
- Performance metrics collection
- Configuration loading from `plugin_config.json`
- Error and metric callbacks
- Thread-safe operation with RLock

**Key Classes**:
- `BasePlugin`: Abstract base class (all plugins extend this)
- `PluginStatus`: Enum for plugin states
- `PluginMetrics`: Performance metrics dataclass

**Abstract Methods**:
```python
def execute(self):
    """Main plugin logic - must be implemented by subclasses"""
    pass
```

**Lifecycle Methods**:
- `start()`: Initialize and start plugin execution
- `pause()`: Temporarily pause execution
- `resume()`: Resume from paused state
- `stop()`: Stop and cleanup resources

### plugins/plugin_manager.py

**Purpose**: Plugin discovery, loading, and lifecycle orchestration.

**Key Features**:
- Auto-discovery of plugins in `plugins/` directory
- Dynamic plugin loading from configuration
- Lifecycle management for all plugins
- Callback registration for metrics aggregation
- Plugin status tracking and reporting
- Batch operations (start_all, stop_all, etc.)

**Key Methods**:
```python
discover_plugins()          # Find all available plugins
load_plugin(name)           # Load specific plugin
load_all_plugins()          # Load all discovered plugins
start_plugin(name)          # Start specific plugin
stop_plugin(name)           # Stop specific plugin
get_plugin_status(name)     # Get status of plugin(s)
get_plugins_summary()       # Get overview with counts
register_metric_callback()  # Register global metric callbacks
```

**Plugin Discovery Process**:
1. Scan `plugins/` directory for subdirectories
2. Look for `plugin_config.json` in each subdirectory
3. Load configuration and validate structure
4. Dynamically import plugin class
5. Instantiate plugin with configuration

### plugins/registration_plugin/

**Purpose**: Automated form registration with browser automation.

**Key Features**:
- Real browser automation via Playwright
- Configurable form field selectors
- Cookie acceptance handling
- Proxy rotation support
- Batch processing with delays
- Random data generation (names, emails)
- Headless or visible browser mode

**Configuration**:
```json
{
  "enabled": true,
  "name": "Registration Plugin",
  "class": "registration_plugin.RegistrationPlugin",
  "url": "https://example.com/register",
  "first_name_selector": "input[name='firstName']",
  "email_selector": "input[name='email']",
  "submit_selector": "button[type='submit']",
  "headless": false,
  "batch_size": 1,
  "delay_between_submissions_ms": 1000,
  "proxy_url": null
}
```

### REST API (api/rest_api.py)

**Framework**: FastAPI with Pydantic validation.

**Base URL**: `http://localhost:8000`

**Endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health status |
| GET | `/api/plugins` | List all plugins with status |
| POST | `/api/plugins/{name}/start` | Start specific plugin |
| POST | `/api/plugins/{name}/stop` | Stop specific plugin |
| POST | `/api/plugins/{name}/pause` | Pause specific plugin |
| POST | `/api/plugins/{name}/resume` | Resume specific plugin |
| GET | `/api/metrics` | Current system metrics |
| GET | `/api/metrics/export` | Export metrics (CSV/JSON) |
| GET | `/api/proxies` | List proxies by score |
| GET | `/api/proxies/{id}` | Get specific proxy details |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/redoc` | ReDoc documentation |

**Request/Response Models** (Pydantic):
```python
class PluginStatusResponse(BaseModel):
    name: str
    status: str
    metrics: Dict[str, Any]

class MetricsResponse(BaseModel):
    timestamp: str
    proxies: Dict[str, int]
    plugins: Dict[str, Any]
```

**Authentication**: Bearer token (configurable).

**Features**:
- Auto-generated OpenAPI documentation
- CORS support for web clients
- Rate limiting (via slowapi)
- Request validation with Pydantic
- Structured error responses

### CLI Interface (cli/cli_commands.py)

**Framework**: Click with colored output (colorama).

**Command Groups**:

```bash
refbot plugin           # Plugin management
  ├── list             # List all plugins
  ├── start <name>     # Start plugin
  ├── stop <name>      # Stop plugin
  ├── pause <name>     # Pause plugin
  ├── resume <name>    # Resume plugin
  └── status [name]    # Get plugin status

refbot metrics          # Metrics management
  ├── show             # Display current metrics
  └── export           # Export metrics to file

refbot proxies          # Proxy management
  ├── list             # List all proxies
  ├── score            # Show proxy scores
  └── health           # Check proxy health

refbot api              # API server control
  ├── start            # Start API server
  └── stop             # Stop API server

refbot config           # Configuration
  └── validate         # Validate configuration

refbot --version        # Show version info
```

**Output Formatting**:
- Color-coded status (✓ green, ✗ red, ⚠ yellow)
- Table formatting via tabulate
- Progress bars for long operations
- JSON output mode for scripting

## Data Flow

### Proxy Validation Flow

```
┌──────────────┐
│   Scraper    │ Fetches from 38 sources
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ ProxyManager │ Stores as "testing"
└──────┬───────┘
       │
       ├─────────────┬─────────────┐
       ▼             ▼             ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│HTTP Worker│ │HTTP Worker│ │HTTP Worker│ 200 workers
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │
      └──────────┬──┴─────────────┘
                 ▼
          ┌────────────┐
          │  Checker   │ Validates proxy
          └──────┬─────┘
                 │
                 ▼
          ┌────────────┐
          │ProxyManager│ Updates status → "working" or "failed"
          └──────┬─────┘
                 │
                 ▼
          ┌────────────┐
          │Persistence │ Saves to JSON/CSV
          └────────────┘
```

### Plugin Execution Flow

```
┌──────────────┐
│ User/API/CLI │ Triggers plugin start
└──────┬───────┘
       │
       ▼
┌──────────────┐
│PluginManager │ Loads and initializes
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Scheduler  │ Schedules execution (optional)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ BasePlugin   │ execute() method runs
└──────┬───────┘
       │
       ├────────────────┐
       ▼                ▼
┌──────────────┐ ┌───────────┐
│ ProxyManager │ │ Analytics │ Accesses services
└──────────────┘ └───────────┘
       │
       ▼
┌──────────────┐
│   Callbacks  │ Metrics/errors propagated
└──────────────┘
```

### Metrics Aggregation Flow

```
┌──────────────┐
│   Workers    │ Generate events
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ProxyManager  │ Tracks proxy metrics
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Analytics   │ Aggregates and analyzes
└──────┬───────┘
       │
       ├─────────────────┬─────────────┐
       ▼                 ▼             ▼
┌───────────┐    ┌───────────┐ ┌──────────┐
│  Alerts   │    │   Trends  │ │ Anomalies│
└───────────┘    └───────────┘ └──────────┘
       │                 │             │
       └────────┬────────┴─────────────┘
                ▼
         ┌─────────────┐
         │  Dashboard  │ Displays
         │  API/CLI    │ Exposes
         └─────────────┘
```

## Configuration

### Main Configuration (config.json)

```json
{
  "mode": "dashboard",
  "url": "https://httpbin.org/ip",
  "timeout": 8,
  "retries": 3,
  "verify_ssl": true,
  "scraper_interval_minutes": 20,
  "http_workers": 200,
  "https_workers": 200,
  "log_buffer_lines": 20,
  "save_state_interval_seconds": 10,
  "proxy_revalidate_hours": 1,
  "dashboard_refresh_rate": 1,
  "plugins_dir": "plugins",
  "metrics_file": "metrics.csv",
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "enable": true,
    "auth_token": "your-secret-token"
  },
  "analytics": {
    "retention_hours": 24,
    "alert_thresholds": {
      "success_rate": 0.7,
      "response_time": 5.0
    }
  }
}
```

### Plugin Configuration Template

**Location**: `plugins/{plugin_name}/plugin_config.json`

```json
{
  "enabled": true,
  "name": "Plugin Display Name",
  "description": "Plugin description",
  "class": "module_name.PluginClassName",
  "version": "1.0.0",
  "schedule": {
    "type": "cron",
    "expression": "*/5 * * * *",
    "enabled": true
  },
  "retry": {
    "max_attempts": 3,
    "backoff_multiplier": 2.0
  },
  "custom_settings": {
    // Plugin-specific configuration
  }
}
```

## Integration Patterns

### Dashboard Integration

```python
from plugins.plugin_manager import PluginManager

class AdvancedDashboard:
    def __init__(self):
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_all_plugins()
        self.plugin_manager.register_metric_callback(self.on_plugin_metric)
    
    def on_plugin_metric(self, plugin_name: str, metrics: dict):
        """Handle plugin metrics updates"""
        self.update_plugin_panel(plugin_name, metrics)
    
    def start_selected_plugin(self):
        """Start plugin selected in UI"""
        plugin_name = self.get_selected_plugin()
        self.plugin_manager.start_plugin(plugin_name)
```

### API Integration

```python
from fastapi import FastAPI
from plugins.plugin_manager import PluginManager

app = FastAPI()
plugin_manager = PluginManager()

@app.post("/api/plugins/{name}/start")
async def start_plugin(name: str):
    try:
        plugin_manager.start_plugin(name)
        return {"status": "success", "message": f"Plugin {name} started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Custom Plugin Development

```python
from plugins.base_plugin import BasePlugin

class MyCustomPlugin(BasePlugin):
    def __init__(self, config: dict):
        super().__init__(config)
        self.custom_setting = config.get("custom_setting", "default")
    
    def execute(self):
        """Main plugin logic"""
        self.logger.info("Executing custom plugin")
        
        # Access proxy manager
        proxies = self.proxy_manager.get_working("HTTPS")
        
        # Your custom logic here
        for proxy in proxies[:10]:
            result = self.process_proxy(proxy)
            self.increment_metric("processed", 1)
        
        # Handle errors
        if error_occurred:
            self.on_error_callback(self.name, error)
    
    def process_proxy(self, proxy):
        """Custom processing logic"""
        # Implementation here
        pass
```

## Performance Characteristics

| Component | Throughput | Latency | Resource Usage |
|-----------|------------|---------|----------------|
| Scraper | 5-10 proxies/sec | N/A | <5% CPU |
| HTTP Validator | 50 checks/sec | <2s | 10-15% CPU |
| HTTPS Validator | 50 checks/sec | <2s | 10-15% CPU |
| Dashboard | 1 Hz refresh | 1s | <5% CPU, 50MB RAM |
| API Server | 100+ req/sec | <50ms | <10% CPU |
| Plugin Manager | 10 plugins | ~100ms startup | <5% CPU per plugin |
| Analytics | 1000 metrics/sec | <10ms | 100MB RAM |

## Security Considerations

1. **API Authentication**: Bearer token required for sensitive endpoints
2. **Input Validation**: Pydantic models validate all API inputs
3. **Proxy Security**: SSL verification configurable per proxy
4. **Rate Limiting**: Slowapi integration prevents abuse
5. **Error Handling**: Sensitive information not exposed in error messages
6. **Configuration**: Secrets should be environment variables, not config files

## Deployment Architecture

### Standalone Deployment

```
┌─────────────────────────┐
│     Single Server       │
│                         │
│  ┌──────────────────┐   │
│  │   RefBot App     │   │
│  │  (main.py)       │   │
│  └──────────────────┘   │
│           │             │
│  ┌────────▼─────────┐   │
│  │   Persistence    │   │
│  │ (JSON/CSV files) │   │
│  └──────────────────┘   │
└─────────────────────────┘
```

### Distributed Deployment

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Worker 1   │      │   Worker 2   │      │   Worker N   │
│  (Validator) │      │  (Validator) │      │  (Validator) │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       └───────────┬─────────┴─────────┬───────────┘
                   │                   │
            ┌──────▼───────────────────▼───────┐
            │     Centralized Storage         │
            │  (Shared Database/Redis)        │
            └──────▲───────────────────▲───────┘
                   │                   │
       ┌───────────┴─────────┬─────────┴───────────┐
       │                     │                     │
┌──────▼───────┐      ┌──────▼───────┐      ┌──────▼───────┐
│   API 1      │      │   API 2      │      │  Dashboard   │
│ (Load Bal.)  │      │ (Load Bal.)  │      │  (Monitor)   │
└──────────────┘      └──────────────┘      └──────────────┘
```

## Extension Points

RefBot is designed for extensibility:

1. **Custom Plugins**: Extend `BasePlugin` for new automation tasks
2. **Custom Scrapers**: Add new proxy sources to `scraper.py`
3. **Custom Validators**: Implement additional validation logic in `checker.py`
4. **Custom Scorers**: Add scoring algorithms to `proxy_scoring.py`
5. **Custom API Endpoints**: Extend FastAPI routes in `rest_api.py`
6. **Custom CLI Commands**: Add Click commands to `cli_commands.py`
7. **Custom Dashboard Panels**: Extend Rich UI in `dashboard.py`
8. **Custom Alerts**: Add alert rules to `analytics.py`

## Best Practices

1. **Plugin Development**:
   - Always call `super().__init__(config)` in plugin constructors
   - Use `self.logger` for all logging
   - Track metrics with `increment_metric()` and `set_metric()`
   - Handle exceptions and call `on_error_callback()` when needed

2. **Configuration**:
   - Store secrets in environment variables
   - Use JSON Schema to validate configurations
   - Document all configuration options
   - Provide sensible defaults

3. **Performance**:
   - Use ThreadPoolExecutor for I/O-bound tasks
   - Use ProcessPoolExecutor for CPU-bound tasks
   - Implement backpressure for queue-based systems
   - Monitor memory usage with metrics

4. **Error Handling**:
   - Catch specific exceptions, not generic `Exception`
   - Log errors with context (proxy IP, plugin name, etc.)
   - Implement retry logic with exponential backoff
   - Fail gracefully and maintain system stability

---

**Architecture Version**: 1.0.0
**Last Updated**: January 2026
**Status**: Production Ready
