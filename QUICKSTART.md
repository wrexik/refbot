# RefBot Quick Start Guide

Get RefBot up and running in minutes with this streamlined guide.

## Prerequisites

- Python 3.8+ installed
- pip package manager
- Internet connection
- Terminal/Command Prompt access

## Installation

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including:
- requests (HTTP client)
- rich (terminal UI)
- playwright (browser automation)
- fastapi (REST API)
- click (CLI framework)
- apscheduler (job scheduling)

### Step 2: Install Playwright Browsers

```bash
playwright install chromium
```

This downloads the Chromium browser for automation plugins. Required for:
- Registration plugin
- Browsing plugin
- Any custom plugins using browser automation

## Running RefBot

### Option 1: Dashboard (Recommended)

The interactive terminal dashboard provides real-time monitoring and control:

```bash
python main.py
```

**What you'll see**:
- 7 information panels (header, stats, config, protocols, proxies, loading, logs)
- Real-time proxy validation progress
- Live event log with color-coded messages
- Top performing proxies
- Plugin status

**Keyboard shortcuts**:
- `L` - Load page through proxy
- `R` - Show results
- `E` - Export proxies to file
- `Q` - Quit application

**Wait time**: First scrape cycle takes ~5 minutes. After that, proxies are continuously validated.

### Option 2: CLI Commands

Control RefBot from the command line:

```bash
# List all plugins
python -m cli.cli_commands plugin list

# Start a plugin
python -m cli.cli_commands plugin start registration_plugin

# View current metrics
python -m cli.cli_commands metrics show

# Export metrics to CSV
python -m cli.cli_commands metrics export --format csv

# Start the API server
python -m cli.cli_commands api start --port 8000
```

### Option 3: REST API

Start the API server for remote control:

```bash
python -m cli.cli_commands api start --port 8000
```

Then access endpoints:

```bash
# Check system health
curl http://localhost:8000/api/health

# List all plugins
curl http://localhost:8000/api/plugins

# Start a plugin
curl -X POST http://localhost:8000/api/plugins/registration_plugin/start

# Get current metrics
curl http://localhost:8000/api/metrics

# View API documentation
# Open browser to: http://localhost:8000/docs
```

### Option 4: Python Script

Use RefBot programmatically in your own scripts:

```python
from plugins.plugin_manager import PluginManager
from main import get_proxies, get_stats
import time

# Initialize plugin manager
pm = PluginManager("plugins")
pm.load_all_plugins()

# Start all plugins
pm.start_all_plugins()

# Get working HTTPS proxies
proxies = get_proxies("HTTPS")
print(f"Found {len(proxies)} working HTTPS proxies")

# Get system statistics
stats = get_stats()
print(f"Total working: {stats['working_count']}")
print(f"Average speed: {stats['average_speed']:.2f}s")

# Let plugins run for 5 minutes
time.sleep(300)

# Stop all plugins
pm.stop_all_plugins()
```

## Basic Configuration

### Main Configuration (config.json)

The main configuration file controls system behavior:

```json
{
  "mode": "dashboard",
  "url": "https://httpbin.org/ip",
  "timeout": 8,
  "scraper_interval_minutes": 20,
  "http_workers": 200,
  "https_workers": 200,
  "dashboard_refresh_rate": 1,
  "plugins_dir": "plugins",
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "enable": true
  }
}
```

**Key settings to adjust**:
- `timeout`: Increase if proxies are timing out (default: 8 seconds)
- `http_workers` / `https_workers`: Reduce if CPU usage too high (default: 200 each)
- `scraper_interval_minutes`: How often to re-scrape sources (default: 20 minutes)
- `api.port`: Change if port 8000 is already in use

### Plugin Configuration

Each plugin has its own configuration file in `plugins/{plugin_name}/plugin_config.json`.

**Example - Registration Plugin** (`plugins/registration_plugin/plugin_config.json`):

```json
{
  "enabled": true,
  "name": "Registration Plugin",
  "description": "Automated form registration",
  "class": "registration_plugin.RegistrationPlugin",
  "version": "1.0.0",
  "url": "https://example.com/register",
  "first_name_selector": "input[name='firstName']",
  "email_selector": "input[name='email']",
  "submit_selector": "button[type='submit']",
  "headless": false,
  "batch_size": 5,
  "delay_between_submissions_ms": 2000,
  "proxy_url": null
}
```

**Key settings**:
- `enabled`: Set to `false` to disable plugin
- `url`: Target website URL
- `headless`: Set to `true` for invisible browser mode
- `batch_size`: Number of submissions per batch
- `delay_between_submissions_ms`: Delay between submissions (milliseconds)
- `proxy_url`: Optional proxy to use for requests

## Dashboard Guide

### Understanding the Panels

**1. Header Panel**
```
Time: 14:32:15 | Uptime: 00:05:23 | Mode: Scraping
```
- Current system time
- How long RefBot has been running
- Current operational mode

**2. Statistics Panel**
```
Scraped:      342    Total proxies found
HTTP Valid:    89    Working with HTTP
HTTPS Valid:   84    Working with HTTPS
Working:      127    Total valid proxies
Testing:       45    Currently being validated
Failed:        67    Failed validation
Avg Speed:  0.42s    Average response time
```

**3. Protocol Distribution Panel**
```
HTTP:   ██████████████░░ 45%
HTTPS:  █████████░░░░░░░ 35%
BOTH:   ██░░░░░░░░░░░░░░ 20%
```
Visual breakdown of proxy protocol support.

**4. Top Proxies Panel**
```
1. 192.168.1.100:8080  0.23s  HTTP
2. 10.0.0.50:3128      0.31s  HTTPS
...
```
Fastest working proxies sorted by response time.

**5. Event Log Panel**
```
[INFO]    Scraper started
[SUCCESS] Proxy validated: 1.2.3.4:8080
[WARNING] Slow proxy: 5.6.7.8:3128 (8.2s)
[ERROR]   Proxy failed: 9.10.11.12:8000
```
Color-coded activity stream showing what's happening.

### Keyboard Controls

| Key | Action |
|-----|--------|
| `L` | Load a page through a random working proxy |
| `R` | Show detailed results/statistics |
| `E` | Export working proxies to `exported_proxies.txt` |
| `↑` / `↓` | Navigate plugins (future feature) |
| `Enter` | Start/resume selected plugin (future feature) |
| `Space` | Pause selected plugin (future feature) |
| `Q` | Quit application |

## Common Tasks

### Get Working Proxies

**From Dashboard**: Press `E` to export to file.

**From Python**:
```python
from main import get_proxies

# Get all working proxies
all_proxies = get_proxies("ANY")

# Get only HTTPS proxies
https_proxies = get_proxies("HTTPS")

# Get only HTTP proxies
http_proxies = get_proxies("HTTP")

# Print proxy addresses
for proxy in https_proxies[:10]:
    print(f"{proxy.ip}:{proxy.port} - {proxy.response_time:.2f}s")
```

### View Metrics

**From CLI**:
```bash
python -m cli.cli_commands metrics show
```

**From API**:
```bash
curl http://localhost:8000/api/metrics
```

**From Python**:
```python
from main import get_stats

stats = get_stats()
print(f"Working: {stats['working_count']}")
print(f"Testing: {stats['testing_count']}")
print(f"Failed: {stats['failed_count']}")
print(f"Average Speed: {stats['average_speed']:.2f}s")
```

### Export Metrics

**To CSV**:
```bash
python -m cli.cli_commands metrics export --format csv --output metrics.csv
```

**To JSON**:
```bash
python -m cli.cli_commands metrics export --format json --output metrics.json
```

**Via API**:
```bash
curl "http://localhost:8000/api/metrics/export?format=csv" > metrics.csv
```

### Manage Plugins

**List all plugins**:
```bash
python -m cli.cli_commands plugin list
```

**Start a plugin**:
```bash
python -m cli.cli_commands plugin start registration_plugin
```

**Stop a plugin**:
```bash
python -m cli.cli_commands plugin stop registration_plugin
```

**Check plugin status**:
```bash
python -m cli.cli_commands plugin status registration_plugin
```

## Creating a Custom Plugin

### Step 1: Create Plugin Directory

```bash
mkdir -p plugins/my_plugin
touch plugins/my_plugin/__init__.py
touch plugins/my_plugin/my_plugin.py
touch plugins/my_plugin/plugin_config.json
```

### Step 2: Write Plugin Configuration

`plugins/my_plugin/plugin_config.json`:
```json
{
  "enabled": true,
  "name": "My Custom Plugin",
  "description": "Does something useful",
  "class": "my_plugin.MyPlugin",
  "version": "1.0.0",
  "schedule": {
    "type": "cron",
    "expression": "*/10 * * * *",
    "enabled": true
  },
  "custom_setting": "value"
}
```

### Step 3: Implement Plugin Class

`plugins/my_plugin/my_plugin.py`:
```python
from plugins.base_plugin import BasePlugin
import logging

class MyPlugin(BasePlugin):
    def __init__(self, config: dict):
        super().__init__(config)
        self.custom_setting = config.get("custom_setting", "default")
        self.logger.info(f"Initialized with setting: {self.custom_setting}")
    
    def execute(self):
        """Main plugin logic - runs on schedule or when started"""
        self.logger.info("Executing my custom plugin")
        
        # Get working HTTPS proxies
        proxies = self.proxy_manager.get_working("HTTPS")
        self.logger.info(f"Found {len(proxies)} working proxies")
        
        # Do something with proxies
        for proxy in proxies[:5]:
            try:
                result = self.use_proxy(proxy)
                self.increment_metric("successful_operations", 1)
            except Exception as e:
                self.logger.error(f"Error using proxy {proxy.address}: {e}")
                self.on_error_callback(self.name, e)
    
    def use_proxy(self, proxy):
        """Your custom logic here"""
        import requests
        proxy_url = f"http://{proxy.ip}:{proxy.port}"
        response = requests.get(
            "https://httpbin.org/ip",
            proxies={"https": proxy_url},
            timeout=5
        )
        return response.json()
```

### Step 4: Load and Run Plugin

```python
from plugins.plugin_manager import PluginManager

pm = PluginManager("plugins")
pm.load_plugin("my_plugin")
pm.start_plugin("my_plugin")
```

Or via CLI:
```bash
python -m cli.cli_commands plugin start my_plugin
```
## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Playwright not found | Run `pip install playwright && playwright install chromium` |
| Port already in use | Change port in config.json or use `--port` flag |
| Plugin not loading | Check plugin_config.json syntax and class path |
| No proxies found | Wait 5+ minutes for first scrape cycle |
| High failure rate | Reduce workers or increase timeout in config |
| Memory usage high | Reduce log_buffer_lines and worker counts |
| API not responding | Check API is enabled in config and port is available |

### Debugging Tips

**Enable verbose logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check plugin status**:
```bash
python -m cli.cli_commands plugin status
```

**View API logs**:
```bash
# API logs are printed to console when running
python -m cli.cli_commands api start --port 8000
```

**Test proxy manually**:
```bash
curl -x http://proxy:port https://httpbin.org/ip
```

## Performance Optimization

### High-Volume Processing

For maximum throughput:
```json
{
  "batch_size": 50,
  "delay_between_submissions_ms": 100,
  "headless": true,
  "http_workers": 300,
  "https_workers": 300
}
```

### Reliable Processing

For maximum reliability:
```json
{
  "batch_size": 1,
  "delay_between_submissions_ms": 5000,
  "headless": false,
  "timeout": 15,
  "retries": 5
}
```

### Resource Optimization

For limited resources:
```json
{
  "http_workers": 50,
  "https_workers": 50,
  "log_buffer_lines": 10,
  "dashboard_refresh_rate": 0.5
}
```

## Best Practices

### Plugin Development

1. **Always call super().__init__(config)** in your plugin constructor
2. **Use self.logger** for all logging instead of print()
3. **Track metrics** with increment_metric() and set_metric()
4. **Handle exceptions** gracefully and call on_error_callback()
5. **Test independently** before integrating with dashboard

### Configuration Management

1. **Store secrets** in environment variables, not config files
2. **Validate configurations** before deployment
3. **Document custom settings** in plugin_config.json comments
4. **Use version control** for configuration files
5. **Keep backups** of working configurations

### Proxy Management

1. **Monitor success rates** and adjust validation parameters
2. **Rotate proxies** regularly to avoid bans
3. **Use proxy scoring** to select best performing proxies
4. **Implement circuit breakers** for failing proxies
5. **Track proxy health** over time

### Production Deployment

1. **Use virtual environments** for dependency isolation
2. **Set up log rotation** to manage disk space
3. **Monitor resource usage** (CPU, memory, network)
4. **Implement health checks** for critical components
5. **Schedule regular backups** of metrics and state

## Advanced Usage

### Custom Metrics

Track custom metrics in your plugin:

```python
def execute(self):
    start_time = time.time()
    
    # Your logic here
    items_processed = self.process_items()
    
    # Track custom metrics
    self.set_metric("items_processed", items_processed)
    self.increment_metric("total_runs", 1)
    self.set_metric("last_run_duration", time.time() - start_time)
```

### Scheduling Plugins

Use cron expressions for scheduled execution:

```json
{
  "schedule": {
    "type": "cron",
    "expression": "*/15 * * * *",
    "enabled": true
  }
}
```

**Common cron patterns**:
- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour
- `0 0 * * *` - Daily at midnight
- `0 9-17 * * *` - Every hour from 9 AM to 5 PM

### Circuit Breaker Pattern

Implement failover with circuit breakers:

```python
from core.proxy_scoring import ProxyScorer, CircuitState

scorer = ProxyScorer()

# Get proxy with circuit breaker
proxy = scorer.get_next_proxy(strategy="WEIGHTED")

if scorer.get_proxy_health(proxy.id) == CircuitState.OPEN:
    # Proxy is failing, use fallback
    proxy = scorer.get_failover_proxy()
```

### Analytics and Alerting

Set up custom alerts:

```python
from core.analytics import MetricsAggregator, AlertSeverity

aggregator = MetricsAggregator()

# Add alert for low success rate
aggregator.add_alert(
    "success_rate",
    lower_threshold=0.7,
    severity=AlertSeverity.CRITICAL,
    message="Success rate below 70%"
)

# Check for alerts
alerts = aggregator.get_active_alerts()
for alert in alerts:
    print(f"[{alert.severity}] {alert.message}")
```

## Environment Variables

Configure RefBot with environment variables:

```bash
# API Configuration
export REFBOT_API_HOST="0.0.0.0"
export REFBOT_API_PORT="8000"
export REFBOT_API_TOKEN="your-secret-token"

# Paths
export REFBOT_PLUGINS_DIR="./plugins"
export REFBOT_CONFIG_PATH="./config.json"
export REFBOT_METRICS_FILE="./metrics.csv"

# Logging
export REFBOT_LOG_LEVEL="INFO"
export REFBOT_LOG_FILE="./refbot.log"

# Performance
export REFBOT_HTTP_WORKERS="200"
export REFBOT_HTTPS_WORKERS="200"
```

## Next Steps

### For New Users

1. ✅ Run the dashboard and observe proxy scraping
2. ✅ Export working proxies and test them
3. ✅ Explore the CLI commands
4. ✅ Try the REST API with Swagger UI
5. ✅ Review the configuration options

### For Developers

1. 📖 Read ARCHITECTURE.md for system design
2. 🔧 Create a simple custom plugin
3. 🧪 Test plugin with CLI commands
4. 🌐 Integrate plugin with REST API
5. 📊 Set up metrics collection and monitoring

### For Production Use

1. 🐳 Set up Docker containerization
2. 🔐 Configure API authentication
3. 📈 Set up metrics export pipeline
4. 🚨 Configure alerting for critical issues
5. 💾 Implement automated backups
6. 📝 Document custom configurations
7. 🧪 Create integration tests

## Additional Resources

- **ARCHITECTURE.md** - Detailed system architecture and design
- **DEPLOYMENT_GUIDE.md** - Production deployment instructions
- **IMPLEMENTATION_MANIFEST.md** - Implementation details and status
- **README.md** - Project overview and features
- API Documentation at `http://localhost:8000/docs`

## Support and Community

For questions, issues, or contributions:
- Open an issue on GitHub
- Review existing documentation
- Check API documentation at /docs
- Test with CLI commands before filing bugs

---

**RefBot** - Proxy management and automation made simple.

**Version**: 1.0.0  
**Last Updated**: January 2026
