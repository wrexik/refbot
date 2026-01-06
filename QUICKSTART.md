# RefBot Quick Start Guide

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers
```bash
playwright install chromium
```

## Running the System

### Option 1: Dashboard (Recommended)
```bash
python main.py
```
Then navigate with arrow keys and press Enter to control plugins.

### Option 2: CLI
```bash
# List all plugins
python -m cli.cli_commands plugin list

# Start a plugin
python -m cli.cli_commands plugin start registration_plugin

# Show metrics
python -m cli.cli_commands metrics show

# Start API server
python -m cli.cli_commands api start --port 8000
```

### Option 3: REST API
```bash
# Start the server
python -m cli.cli_commands api start --port 8000

# Then use curl or requests to control
curl http://localhost:8000/api/plugins
curl -X POST http://localhost:8000/api/plugins/registration_plugin/start
```

### Option 4: Python Script
```python
from plugins.plugin_manager import PluginManager

# Create and load plugins
pm = PluginManager("plugins")
pm.load_all_plugins()

# Start all plugins
pm.start_all_plugins()

# Let them run for a while
import time
time.sleep(300)

# Stop and cleanup
pm.stop_all_plugins()
```

## Configuration

### Main Config (config.json)
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

### Registration Plugin Config
Edit `plugins/registration_plugin/plugin_config.json`:
```json
{
  "url": "https://example.com/register",
  "first_name_selector": "input[name='firstName']",
  "email_selector": "input[name='email']",
  "submit_selector": "button[type='submit']",
  "headless": false,
  "batch_size": 5,
  "delay_between_submissions_ms": 2000,
  "proxy_url": "http://proxy.example.com:8080"
}
```

## Dashboard Controls

Navigate with **arrow keys**:
- **UP/DOWN** - Select plugin
- **ENTER** - Start/Resume
- **SPACE** - Pause
- **DELETE/BACKSPACE** - Stop
- **Q/ESC** - Quit

View in dashboard:
- Plugin status (running, paused, stopped, error)
- Current metrics (requests, success rate, response time)
- Active proxies and their health
- Live logs from all plugins

## Monitoring

### View Metrics
```bash
python -m cli.cli_commands metrics show --hours 24
```

### Export Metrics
```bash
# CSV export
python -m cli.cli_commands metrics export --format csv --output results.csv

# JSON export
python -m cli.cli_commands metrics export --format json --output results.json
```

### Check Proxy Health
```bash
python -m cli.cli_commands proxies health
python -m cli.cli_commands proxies score --top 20
```

### View API Documentation
Start the API server and open: http://localhost:8000/docs

## Creating Custom Plugins

### Step 1: Create Plugin Directory
```bash
mkdir plugins/my_plugin
```

### Step 2: Create Plugin Class
File: `plugins/my_plugin/my_plugin.py`
```python
from plugins.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def execute(self):
        # Your plugin logic here
        return {
            "response_time_ms": 100,
            "items_processed": 10
        }
```

### Step 3: Create Configuration
File: `plugins/my_plugin/plugin_config.json`
```json
{
  "enabled": true,
  "name": "My Plugin",
  "description": "Plugin description",
  "class": "my_plugin.MyPlugin",
  "version": "1.0.0"
}
```

### Step 4: Load and Run
```python
from plugins.plugin_manager import PluginManager

pm = PluginManager()
pm.load_plugin("my_plugin")
pm.start_plugin("my_plugin")
```

## Troubleshooting

### Playwright Not Found
```bash
pip install playwright
playwright install chromium
```

### Port Already in Use
```bash
# Use different port
python -m cli.cli_commands api start --port 8001
```

### Plugin Not Loading
- Check plugin_config.json exists in plugin directory
- Verify "class" field points to correct class name
- Check plugin_config.json is valid JSON
- Look at logs for detailed error messages

### Proxy Connection Issues
- Verify proxy URL format: `http://host:port`
- Test proxy separately: `curl -x http://proxy:port http://example.com`
- Check proxy is accessible from your network
- Add timeout configuration in plugin config

### Low Success Rate
- Increase delay between submissions
- Reduce batch size
- Add proxy rotation
- Check target website restrictions
- Verify form selectors are correct

## Performance Tuning

### For High-Volume Registrations
```json
{
  "batch_size": 20,
  "delay_between_submissions_ms": 500,
  "headless": true
}
```

### For Reliable Registrations
```json
{
  "batch_size": 1,
  "delay_between_submissions_ms": 3000,
  "headless": false
}
```

### Proxy Scoring
The system automatically scores proxies based on:
- Success rate (40% weight)
- Response time (30% weight)
- Reliability (30% weight)

Best proxies are selected automatically via `WEIGHTED` load balancing strategy.

## Environment Variables

```bash
# API Configuration
export REFBOT_API_URL="http://localhost:8000"
export REFBOT_API_TOKEN="your-token"

# Logging
export REFBOT_LOG_LEVEL="INFO"

# Database
export REFBOT_DB_PATH="./data/metrics.db"
```

## API Endpoints

### Health & Status
- `GET /api/health` - System health
- `GET /api/plugins` - List plugins

### Plugin Control
- `POST /api/plugins/{name}/start` - Start plugin
- `POST /api/plugins/{name}/stop` - Stop plugin

### Metrics
- `GET /api/metrics` - Current metrics
- `GET /api/metrics/export?format=csv|json` - Export

### Proxies
- `GET /api/proxies?sort=score|response_time|success_rate` - Proxy list

### Documentation
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation

## Support

For issues and feature requests:
1. Check ARCHITECTURE.md for detailed component information
2. Review logs in dashboard or CLI output
3. Test API endpoints at http://localhost:8000/docs
4. Create plugin-specific issue with reproduction steps

## Next Steps

1. **Customize Registration Plugin**
   - Update selectors for your target website
   - Configure proxy and batch settings
   - Test with small batch first

2. **Create Custom Plugin**
   - Extend BasePlugin class
   - Implement execute() method
   - Add plugin_config.json

3. **Set Up Monitoring**
   - Export metrics regularly
   - Monitor success rates
   - Track proxy health

4. **Production Deployment**
   - Use systemd for auto-start
   - Configure log rotation
   - Set up metrics backup
   - Enable API authentication

---
**Version**: 1.0.0
**Last Updated**: 2024
