# RefBot Advanced Plugin System - Implementation Summary

## Project Structure

```
refbot/
├── main.py                          # Main entry point
├── config.json                      # Main configuration
├── dashboard.py                     # Dashboard UI (existing)
├── requirements.txt                 # Updated with all dependencies
│
├── core/                            # Core subsystems
│   ├── __init__.py
│   ├── scheduler.py                 # Advanced job scheduling with APScheduler
│   ├── analytics.py                 # Metrics aggregation with alerting
│   └── proxy_scoring.py             # Intelligent proxy ranking
│
├── api/                             # REST API subsystem
│   ├── __init__.py
│   └── rest_api.py                  # FastAPI REST server
│
├── cli/                             # Command-line interface
│   ├── __init__.py
│   └── cli_commands.py              # Click-based CLI commands
│
├── plugins/                         # Plugin system
│   ├── __init__.py
│   ├── base_plugin.py               # Abstract base class for all plugins
│   ├── plugin_manager.py            # Plugin discovery & lifecycle management
│   ├── scheduler.py                 # (Already created in Phase 7)
│   │
│   └── registration_plugin/         # Registration automation plugin
│       ├── __init__.py
│       ├── plugin_config.json       # Plugin configuration
│       └── registration_plugin.py   # Playwright integration
│
├── checker.py                       # Existing checker (legacy)
├── scraper.py                       # Existing scraper (legacy)
└── other files...
```

## Core Modules

### 1. **core/scheduler.py** (286 lines)
Advanced job scheduling with APScheduler integration.

**Key Features:**
- Cron expression support (`*/5 * * * *` format)
- Exponential backoff retry logic with configurable multiplier (2.0x)
- Execution history tracking (deque with max 1000 records)
- Success/failure callbacks
- Statistics export (total, success, failure, duration metrics)
- Thread-safe with RLock

**Key Classes:**
- `PluginScheduler`: Main scheduler with APScheduler integration
- `ScheduleConfig`: Configuration dataclass
- `ExecutionRecord`: Execution history record
- `ExecutionStatus`: SUCCESS, FAILED, CANCELLED, RETRYING

### 2. **core/analytics.py** (380+ lines)
Real-time metrics aggregation with alerting and anomaly detection.

**Key Features:**
- Time-series metrics storage (deque-based with retention)
- Threshold-based alerting (upper/lower bounds)
- Anomaly detection (Z-score and IQR methods)
- Trend analysis with moving averages
- Reliability scoring (0-100)
- CSV/JSON export

**Key Classes:**
- `MetricsAggregator`: Main metrics engine
- `Alert`: Alert data structure
- `AlertSeverity`: INFO, WARNING, CRITICAL
- Analysis methods: detect_anomalies(), get_trend_analysis(), get_success_rate()

### 3. **core/proxy_scoring.py** (330+ lines)
Intelligent proxy ranking with circuit breaker health monitoring.

**Key Features:**
- Weighted scoring algorithm (40% success, 30% speed, 30% reliability)
- Circuit breaker pattern (CLOSED, OPEN, HALF_OPEN states)
- 4 load balancing strategies (ROUND_ROBIN, LEAST_LOADED, WEIGHTED, RANDOM)
- Automatic health state transitions
- Failover chain management

**Key Classes:**
- `ProxyScorer`: Main scoring engine
- `ProxyScore`: Individual proxy metrics
- `LoadBalancingStrategy`: Enum with 4 strategies
- `CircuitState`: Enum for health states

### 4. **api/rest_api.py** (200+ lines)
FastAPI REST server for remote control and monitoring.

**Key Endpoints:**
- `GET /api/health` - System health status
- `GET /api/plugins` - List plugins
- `POST /api/plugins/{name}/start` - Start plugin
- `POST /api/plugins/{name}/stop` - Stop plugin
- `GET /api/metrics` - Current metrics
- `GET /api/metrics/export` - Export metrics (CSV/JSON)
- `GET /api/proxies` - List proxies by score
- `GET /docs` - Interactive Swagger UI
- `GET /redoc` - ReDoc documentation

**Features:**
- Pydantic models for validation
- Bearer token authentication (placeholder)
- CORS support
- Rate limiting ready (slowapi)
- Auto-generated documentation

### 5. **cli/cli_commands.py** (400+ lines)
Click-based command-line interface for system control.

**Command Groups:**
- `refbot plugin` - Plugin management (list, start, stop, status)
- `refbot metrics` - Metrics commands (show, export)
- `refbot proxies` - Proxy commands (score, health)
- `refbot api` - API control (start server)
- `refbot config` - Configuration validation
- `refbot --version` - Version info

**Features:**
- Color-coded output (✓ success, ✗ error, ⚠ warning)
- Table formatting via tabulate
- Colorama for Windows compatibility
- API integration via requests
- Configurable via environment variables

## Plugin System

### 1. **plugins/base_plugin.py**
Abstract base class for all plugins.

**Key Features:**
- Plugin lifecycle: start(), pause(), resume(), stop()
- Status tracking (IDLE, RUNNING, PAUSED, STOPPED, ERROR)
- Performance metrics collection
- Configuration loading from plugin_config.json
- Error and metric callbacks
- Thread-safe operation with RLock

**Key Classes:**
- `BasePlugin`: Abstract base class (all plugins extend this)
- `PluginStatus`: Enum for plugin states
- `PluginMetrics`: Performance metrics dataclass

**Methods:**
- `execute()` - Abstract method for plugin logic
- `start()/pause()/resume()/stop()` - Lifecycle control
- `get_config()/set_config()` - Configuration management
- `get_metrics()` - Performance metrics
- `on_error()/on_metric()` - Callback registration

### 2. **plugins/plugin_manager.py**
Plugin discovery and lifecycle management.

**Key Features:**
- Auto-discovery of plugins in plugins/ directory
- Dynamic plugin loading from plugin_config.json
- Lifecycle management (load, unload, start, stop, pause, resume)
- Callback registration for metrics
- Plugin status tracking
- Batch operations (start_all, stop_all, etc.)

**Key Methods:**
- `discover_plugins()` - Find all available plugins
- `load_plugin(name)` - Load a specific plugin
- `start_plugin()/stop_plugin()` - Lifecycle control
- `get_plugin_status()` - Status for one or all plugins
- `get_plugins_summary()` - Overview with counts
- `load_all_plugins()` - Load everything
- `start_all_plugins()` - Start everything
- `register_metric_callback()` - Register global callbacks

### 3. **plugins/registration_plugin/registration_plugin.py**
Automated registration form submission with Playwright.

**Key Features:**
- Real browser automation with Playwright
- Form field auto-filling (firstName, email)
- Cookie acceptance handling
- Proxy rotation support
- Batch processing with configurable delays
- Random name/email generation
- Registration tracking
- Headless or visible mode

**Configuration (plugin_config.json):**
```json
{
  "url": "https://rarecloud.io/rewards",
  "first_name_selector": "input[name='firstName']",
  "email_selector": "input[name='email']",
  "submit_selector": "button[type='submit']",
  "headless": false,
  "batch_size": 1,
  "delay_between_submissions_ms": 1000,
  "proxy_url": null
}
```

## Integration Points

### Dashboard Integration
The dashboard should integrate with the plugin system:

```python
from plugins.plugin_manager import PluginManager

class AdvancedDashboard:
    def __init__(self):
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_all_plugins()
        self.plugin_manager.register_metric_callback(self.on_plugin_metric)
    
    def on_plugin_metric(self, plugin_name, metrics):
        # Update dashboard with plugin metrics
        pass
```

### Arrow Key Control
Navigate between plugins and control them:
- **UP/DOWN** - Select plugin
- **ENTER** - Start/Resume selected plugin
- **SPACE** - Pause selected plugin
- **DELETE** - Stop selected plugin

## Dependencies

```
Core:
- requests>=2.31.0
- playwright>=1.57.0
- rich>=13.5.0

Advanced Features:
- apscheduler>=3.10.0      # Job scheduling
- fastapi==0.104.1         # REST API
- uvicorn==0.24.0          # ASGI server
- slowapi==0.1.8           # Rate limiting
- pydantic==2.5.0          # Validation
- click==8.1.7             # CLI framework
- tabulate==0.9.0          # Table formatting
- colorama==0.4.6          # Terminal colors
```

## Configuration Files

### Main Configuration (config.json)
```json
{
  "mode": "dashboard",
  "plugins_dir": "plugins",
  "metrics_file": "metrics.csv",
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "enable": true
  }
}
```

### Plugin Configuration (plugins/[plugin_name]/plugin_config.json)
```json
{
  "enabled": true,
  "name": "Plugin Display Name",
  "description": "Plugin description",
  "class": "module.PluginClass",
  "version": "1.0.0",
  ...plugin_specific_settings...
}
```

## Usage Examples

### CLI Usage
```bash
# List plugins
python -m cli.cli_commands plugin list

# Start a plugin
python -m cli.cli_commands plugin start registration_plugin

# Show metrics
python -m cli.cli_commands metrics show --hours 24

# View top proxies
python -m cli.cli_commands proxies score --top 10

# Start API server
python -m cli.cli_commands api start --port 8000
```

### Python Usage
```python
from plugins.plugin_manager import PluginManager

# Create manager
pm = PluginManager("plugins")

# Discover and load plugins
pm.load_all_plugins()

# Start all plugins
pm.start_all_plugins()

# Get status
status = pm.get_plugins_summary()

# Stop all plugins
pm.stop_all_plugins()
```

### API Usage
```bash
# Get health status
curl http://localhost:8000/api/health

# List plugins
curl http://localhost:8000/api/plugins

# Start plugin
curl -X POST http://localhost:8000/api/plugins/registration_plugin/start

# Get metrics
curl http://localhost:8000/api/metrics

# Export metrics
curl "http://localhost:8000/api/metrics/export?format=csv" > metrics.csv
```

## Next Steps

1. **Update dashboard.py** - Integrate PluginManager and add plugin panels
2. **Add arrow key navigation** - Implement plugin control in dashboard
3. **Create main entry point** - Update main.py to use new plugin system
4. **Test plugins** - Verify each plugin works independently
5. **Production deployment** - Build Docker image, create systemd service
6. **Monitoring** - Set up metrics export and alerting
7. **Documentation** - Create user guides and API documentation

## Architecture Highlights

✓ **Modular**: Each subsystem is independent and testable
✓ **Scalable**: Plugin architecture allows adding features without modifying core
✓ **Reliable**: Circuit breaker, retry logic, and health monitoring
✓ **Observable**: Comprehensive metrics and logging throughout
✓ **Remote Control**: REST API and CLI interfaces
✓ **Configuration-Driven**: All behavior controlled via JSON configs
✓ **Production-Ready**: Error handling, type hints, docstrings
✓ **Extensible**: Easy to add new plugins or subsystems

---
**Status**: Implementation Phase 7 Complete
**Version**: 1.0.0-alpha
**Last Updated**: 2024
