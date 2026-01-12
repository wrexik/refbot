# RefBot

**Enterprise-grade proxy management system with plugin architecture, automated validation, and real-time monitoring.**

RefBot is a production-ready Python application designed for high-performance proxy scraping, validation, and utilization. It features a modular plugin system, REST API, CLI interface, and an interactive terminal dashboard powered by Rich.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for automation plugins)
playwright install chromium

# Run the dashboard
python main.py
```

The system will automatically:
- Scrape proxies from multiple sources
- Validate proxies concurrently (HTTP/HTTPS)
- Display real-time metrics and status
- Persist state and metrics to disk
- Enable plugin-based automation tasks

## Features

### Core Capabilities
- **Multi-Source Scraping**: Aggregate proxies from 38+ public sources
- **Concurrent Validation**: 200 HTTP + 200 HTTPS workers with sub-2s response times
- **Plugin Architecture**: Extensible system for custom automation workflows
- **REST API**: Full remote control and monitoring via FastAPI
- **CLI Interface**: Complete command-line management with Click
- **Rich Dashboard**: Interactive 7-panel terminal UI with live updates
- **State Persistence**: Automatic JSON and CSV exports every 10 seconds
- **Thread-Safe Design**: RLock protection for concurrent operations
- **Advanced Scheduling**: Cron-based job scheduling with retry logic
- **Metrics & Analytics**: Real-time aggregation with alerting and anomaly detection
- **Intelligent Scoring**: Weighted proxy ranking with circuit breaker health monitoring

### Plugin System
- **Base Plugin Framework**: Abstract class for creating custom plugins
- **Plugin Manager**: Auto-discovery, lifecycle management, and orchestration
- **Registration Plugin**: Automated form submission with Playwright browser automation
- **Browsing Plugin**: Proxy-aware web browsing and interaction

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Application                         │
│                      (main.py)                               │
├─────────────────────────────────────────────────────────────┤
│  Dashboard UI          │  REST API        │  CLI Commands   │
│  (dashboard.py)        │  (api/rest_api)  │  (cli/)         │
├────────────────────────┴──────────────────┴─────────────────┤
│                     Plugin Manager                           │
│                  (plugins/plugin_manager.py)                 │
├─────────────────────────────────────────────────────────────┤
│  Core Services:                                              │
│  • ProxyManager (thread-safe proxy storage)                  │
│  • WorkerThreads (scraper + validators + auto-save)          │
│  • Scheduler (job scheduling with APScheduler)               │
│  • Analytics (metrics aggregation + alerting)                │
│  • ProxyScorer (intelligent ranking + circuit breaker)       │
│  • Persistence (JSON + CSV state management)                 │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
refbot/
├── main.py                    # Main entry point
├── dashboard.py               # Rich terminal UI
├── config.json                # Configuration
├── proxy_manager.py           # Thread-safe proxy storage
├── worker_threads.py          # Concurrent workers
├── persistence.py             # State persistence
├── scraper.py                 # Multi-source proxy scraper
├── checker.py                 # HTTP/HTTPS validation
│
├── core/                      # Core subsystems
│   ├── scheduler.py           # Job scheduling with APScheduler
│   ├── analytics.py           # Metrics aggregation + alerting
│   └── proxy_scoring.py       # Intelligent proxy ranking
│
├── api/                       # REST API
│   └── rest_api.py            # FastAPI server
│
├── cli/                       # Command-line interface
│   └── cli_commands.py        # Click-based commands
│
├── plugins/                   # Plugin system
│   ├── base_plugin.py         # Abstract base class
│   ├── plugin_manager.py      # Plugin lifecycle management
│   ├── registration_plugin/   # Form automation plugin
│   └── browsing_plugin/       # Web browsing plugin
│
└── requirements.txt           # Python dependencies
```

## Usage

### Dashboard Interface

Run the interactive dashboard:

```bash
python main.py
```

The dashboard displays 7 information panels:

1. **Header**: Current time, uptime, operational mode
2. **Statistics**: Proxy counts (scraped, validated, working, failed)
3. **Configuration**: Active settings and parameters
4. **Protocol Distribution**: HTTP/HTTPS/BOTH support breakdown
5. **Top Proxies**: Fastest working proxies with response times
6. **Loading Status**: Page loader state and metrics
7. **Event Log**: Color-coded activity stream

### Python API

Use RefBot programmatically in your applications:

```python
from main import get_proxies, get_stats, export_proxies

# Get working HTTPS proxies
proxies = get_proxies("HTTPS")  # Options: "HTTP", "HTTPS", "ANY"
for proxy in proxies[:5]:
    print(f"{proxy.ip}:{proxy.port} - {proxy.response_time:.2f}s")

# Get system statistics
stats = get_stats()
print(f"Working: {stats['working_count']}")
print(f"Average Speed: {stats['average_speed']:.2f}s")

# Export proxies to file
count = export_proxies("working_proxies.txt")
print(f"Exported {count} proxies")
```

### REST API

Start the API server:

```bash
python -m cli.cli_commands api start --port 8000
```

Available endpoints:

- `GET /api/health` - System health status
- `GET /api/plugins` - List all plugins
- `POST /api/plugins/{name}/start` - Start a plugin
- `POST /api/plugins/{name}/stop` - Stop a plugin
- `GET /api/metrics` - Get current metrics
- `GET /api/proxies` - List proxies by score
- `GET /docs` - Interactive Swagger documentation

Example usage:

```bash
# Get health status
curl http://localhost:8000/api/health

# Start a plugin
curl -X POST http://localhost:8000/api/plugins/registration_plugin/start

# Export metrics
curl "http://localhost:8000/api/metrics/export?format=csv" > metrics.csv
```

### CLI Commands

Complete command-line interface:

```bash
# Plugin management
python -m cli.cli_commands plugin list
python -m cli.cli_commands plugin start registration_plugin
python -m cli.cli_commands plugin stop registration_plugin
python -m cli.cli_commands plugin status

# Metrics
python -m cli.cli_commands metrics show --hours 24
python -m cli.cli_commands metrics export --format csv

# Proxy management
python -m cli.cli_commands proxies score --top 10
python -m cli.cli_commands proxies health

# Configuration
python -m cli.cli_commands config validate
```
## Configuration

Edit `config.json` to customize system behavior:

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
    "enable": true
  }
}
```

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mode` | Operating mode (dashboard/api/cli) | `"dashboard"` |
| `url` | Target URL for proxy validation | `"https://httpbin.org/ip"` |
| `timeout` | Request timeout in seconds | `8` |
| `scraper_interval_minutes` | Interval between scraping cycles | `20` |
| `http_workers` | Concurrent HTTP validation workers | `200` |
| `https_workers` | Concurrent HTTPS validation workers | `200` |
| `save_state_interval_seconds` | State persistence interval | `10` |
| `dashboard_refresh_rate` | UI update frequency (Hz) | `1` |
| `plugins_dir` | Plugin directory path | `"plugins"` |

## Plugin Development

### Creating a Custom Plugin

1. Create a plugin directory under `plugins/`:

```
plugins/
└── my_plugin/
    ├── __init__.py
    ├── plugin_config.json
    └── my_plugin.py
```

2. Define plugin configuration (`plugin_config.json`):

```json
{
  "enabled": true,
  "name": "My Custom Plugin",
  "description": "Custom automation plugin",
  "class": "my_plugin.MyPlugin",
  "version": "1.0.0",
  "schedule": {
    "type": "cron",
    "expression": "*/5 * * * *"
  }
}
```

3. Implement the plugin class (`my_plugin.py`):

```python
from plugins.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def __init__(self, config: dict):
        super().__init__(config)
    
    def execute(self):
        """Main plugin logic"""
        self.logger.info("Executing custom plugin")
        
        # Get working proxies
        proxies = self.proxy_manager.get_working("HTTPS")
        
        # Your automation logic here
        for proxy in proxies[:5]:
            # Do something with each proxy
            pass
        
        # Track metrics
        self.increment_metric("tasks_completed", 1)
```

4. Load and run the plugin:

```python
from plugins.plugin_manager import PluginManager

pm = PluginManager("plugins")
pm.load_all_plugins()
pm.start_plugin("my_plugin")
```
## Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Scraping Speed | 5-10 proxies/sec | Concurrent fetching from 38 sources |
| Validation Rate | 50-100 proxies/sec | 400 concurrent workers (200 HTTP + 200 HTTPS) |
| Memory Usage | 2-5 MB | Per 100 working proxies |
| CPU Usage | <10% idle, <30% load | Efficient thread pooling |
| Dashboard Refresh | 1 Hz | Configurable update rate |
| State Persistence | 10 sec interval | Automatic JSON/CSV export |
| Response Time | <2 sec | Typical proxy validation time |

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Internet connection for proxy scraping

### Setup

1. **Clone or download the repository**:

```bash
git clone https://github.com/yourusername/refbot.git
cd refbot
```

2. **Create a virtual environment** (recommended):

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers** (for automation plugins):

```bash
playwright install chromium
```

5. **Configure the system**:

Edit `config.json` to match your requirements (optional).

6. **Run RefBot**:

```bash
python main.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No proxies found | Wait 5+ minutes for first scrape cycle to complete |
| Validation too slow | Reduce worker counts in config or increase timeout |
| Dashboard text overlaps | Increase terminal width (minimum 100 columns recommended) |
| High memory usage | Reduce `log_buffer_lines` in configuration |
| Page loading fails | Ensure Playwright is installed: `playwright install chromium` |
| Plugin errors | Check plugin_config.json syntax and required dependencies |
| API not responding | Verify API is enabled in config and port is not in use |

## Dependencies

Core dependencies:

```
requests>=2.31.0          # HTTP client
rich>=13.0.0              # Terminal UI
playwright>=1.40.0        # Browser automation
urllib3>=2.0.0            # HTTP utilities
apscheduler>=3.10.0       # Job scheduling
fastapi>=0.104.0          # REST API framework
uvicorn>=0.24.0           # ASGI server
click>=8.1.0              # CLI framework
tabulate>=0.9.0           # Table formatting
colorama>=0.4.6           # Terminal colors
pydantic>=2.5.0           # Data validation
```

See `requirements.txt` for complete dependency list.

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation in the `docs/` directory
- Review the ARCHITECTURE.md for technical details

## Roadmap

- [ ] Docker containerization
- [ ] Web-based UI alternative to terminal dashboard
- [ ] Additional proxy sources
- [ ] Machine learning-based proxy quality prediction
- [ ] Distributed proxy validation across multiple nodes
- [ ] Enhanced authentication support
- [ ] Proxy rotation strategies
- [ ] Integration with popular web scraping frameworks

---

**RefBot** - Professional proxy management made simple.
