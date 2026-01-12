# RefBot Deployment Guide

This guide covers deploying RefBot in development, staging, and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Configuration Management](#configuration-management)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 4+ GB |
| Disk Space | 1 GB | 5+ GB |
| OS | Windows/Linux/macOS | Linux (Ubuntu 20.04+) |
| Python | 3.8+ | 3.10+ |
| Network | 10 Mbps | 50+ Mbps |

### Software Dependencies

- Python 3.8 or higher
- pip (Python package manager)
- Git (for version control)
- Chromium browser (for Playwright)
- Optional: Docker, Docker Compose
- Optional: systemd (Linux) or Windows Service

## Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/refbot.git
cd refbot
```

### Step 2: Create Virtual Environment

**Windows**:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### Step 4: Configure Application

Copy and edit the configuration:

```bash
cp config.json config.local.json
# Edit config.local.json with your settings
```

### Step 5: Run Application

```bash
# Dashboard mode
python main.py

# API mode
python -m cli.cli_commands api start --port 8000

# CLI mode
python -m cli.cli_commands plugin list
```

## Production Deployment

### Option 1: Systemd Service (Linux)

#### Create Service File

Create `/etc/systemd/system/refbot.service`:

```ini
[Unit]
Description=RefBot Proxy Management System
After=network.target

[Service]
Type=simple
User=refbot
Group=refbot
WorkingDirectory=/opt/refbot
Environment="PATH=/opt/refbot/.venv/bin"
ExecStart=/opt/refbot/.venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/refbot/refbot.log
StandardError=append:/var/log/refbot/refbot-error.log

[Install]
WantedBy=multi-user.target
```

#### Deploy Application

```bash
# Create user
sudo useradd -r -s /bin/false refbot

# Create directories
sudo mkdir -p /opt/refbot
sudo mkdir -p /var/log/refbot
sudo chown -R refbot:refbot /opt/refbot /var/log/refbot

# Copy application files
sudo cp -r . /opt/refbot/
cd /opt/refbot

# Install dependencies
sudo -u refbot python3 -m venv .venv
sudo -u refbot .venv/bin/pip install -r requirements.txt
sudo -u refbot .venv/bin/playwright install chromium

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable refbot
sudo systemctl start refbot

# Check status
sudo systemctl status refbot
```

#### Manage Service

```bash
# Start service
sudo systemctl start refbot

# Stop service
sudo systemctl stop refbot

# Restart service
sudo systemctl restart refbot

# View logs
sudo journalctl -u refbot -f

# View status
sudo systemctl status refbot
```

### Option 2: Windows Service

#### Using NSSM (Non-Sucking Service Manager)

1. **Download NSSM**:
   - Download from https://nssm.cc/download
   - Extract to `C:\nssm`

2. **Install Service**:

```powershell
# Open Command Prompt as Administrator
cd C:\nssm\win64

# Install service
nssm install RefBot "C:\refbot\.venv\Scripts\python.exe" "C:\refbot\main.py"

# Configure service
nssm set RefBot AppDirectory "C:\refbot"
nssm set RefBot DisplayName "RefBot Proxy Management"
nssm set RefBot Description "Enterprise proxy management and automation system"
nssm set RefBot Start SERVICE_AUTO_START

# Set output logs
nssm set RefBot AppStdout "C:\refbot\logs\refbot.log"
nssm set RefBot AppStderr "C:\refbot\logs\refbot-error.log"

# Start service
nssm start RefBot
```

3. **Manage Service**:

```powershell
# Start service
nssm start RefBot

# Stop service
nssm stop RefBot

# Restart service
nssm restart RefBot

# Remove service
nssm remove RefBot confirm
```

## Docker Deployment

### Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application files
COPY . .

# Create non-root user
RUN useradd -m -u 1000 refbot && \
    chown -R refbot:refbot /app

USER refbot

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# Run application
CMD ["python", "main.py"]
```

### Create Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  refbot:
    build: .
    container_name: refbot
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./config.json:/app/config.json:ro
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - REFBOT_MODE=api
      - REFBOT_API_HOST=0.0.0.0
      - REFBOT_API_PORT=8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - refbot-network

networks:
  refbot-network:
    driver: bridge
```

### Deploy with Docker

```bash
# Build image
docker build -t refbot:latest .

# Run container
docker run -d \
  --name refbot \
  -p 8000:8000 \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  refbot:latest

# Or use Docker Compose
docker-compose up -d

# View logs
docker logs -f refbot

# Stop container
docker-compose down
```

### Docker Management

```bash
# View logs
docker logs -f refbot

# Execute command in container
docker exec -it refbot python -m cli.cli_commands plugin list

# Restart container
docker restart refbot

# Update and restart
docker-compose pull
docker-compose up -d

# View resource usage
docker stats refbot
```

## Configuration Management

### Environment-Specific Configurations

Create separate configuration files for each environment:

```bash
config.local.json      # Local development
config.staging.json    # Staging environment
config.production.json # Production environment
```

### Using Environment Variables

Override configuration with environment variables:

```bash
# API Configuration
export REFBOT_MODE="api"
export REFBOT_API_HOST="0.0.0.0"
export REFBOT_API_PORT="8000"
export REFBOT_API_TOKEN="your-secret-token"

# Worker Configuration
export REFBOT_HTTP_WORKERS="200"
export REFBOT_HTTPS_WORKERS="200"
export REFBOT_SCRAPER_INTERVAL="20"

# Paths
export REFBOT_PLUGINS_DIR="/opt/refbot/plugins"
export REFBOT_CONFIG_PATH="/opt/refbot/config.json"
export REFBOT_METRICS_FILE="/var/log/refbot/metrics.csv"

# Logging
export REFBOT_LOG_LEVEL="INFO"
export REFBOT_LOG_FILE="/var/log/refbot/refbot.log"
```

### Configuration Validation

Validate configuration before deployment:

```bash
python -m cli.cli_commands config validate
```

### Secrets Management

**Never commit secrets to version control!**

Use environment variables or secret management tools:

```bash
# Using environment variables
export REFBOT_API_TOKEN=$(cat /run/secrets/refbot_token)

# Using AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id refbot/api-token

# Using HashiCorp Vault
vault kv get secret/refbot/api-token
```

## Monitoring and Maintenance

### Health Checks

#### HTTP Health Check

```bash
curl -f http://localhost:8000/api/health || exit 1
```

#### Python Health Check

```python
import requests

try:
    response = requests.get("http://localhost:8000/api/health", timeout=5)
    response.raise_for_status()
    print("✓ Service is healthy")
except Exception as e:
    print(f"✗ Service is unhealthy: {e}")
    exit(1)
```

### Metrics Collection

#### Export Metrics Regularly

Set up cron job (Linux):

```bash
# Add to crontab
0 * * * * /opt/refbot/.venv/bin/python -m cli.cli_commands metrics export --format csv --output /var/log/refbot/metrics-$(date +\%Y\%m\%d-\%H).csv
```

#### Monitor Key Metrics

```python
from main import get_stats

stats = get_stats()

# Alert if metrics fall below thresholds
if stats['working_count'] < 50:
    send_alert("Low proxy count")

if stats['average_speed'] > 5.0:
    send_alert("High average response time")
```

### Log Management

#### Log Rotation (Linux)

Create `/etc/logrotate.d/refbot`:

```
/var/log/refbot/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 refbot refbot
    sharedscripts
    postrotate
        systemctl reload refbot
    endscript
}
```

#### Log Aggregation

Forward logs to centralized logging:

```bash
# Using rsyslog
echo "*.* @@logserver:514" >> /etc/rsyslog.conf

# Using Fluentd
<source>
  @type tail
  path /var/log/refbot/refbot.log
  pos_file /var/log/td-agent/refbot.pos
  tag refbot.log
  format json
</source>
```

### Automated Backups

#### Database Backup Script

Create `backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backup/refbot"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration
cp /opt/refbot/config.json $BACKUP_DIR/config_$DATE.json

# Backup database files
cp /opt/refbot/data/*.json $BACKUP_DIR/

# Backup metrics
cp /var/log/refbot/metrics.csv $BACKUP_DIR/metrics_$DATE.csv

# Compress
tar -czf $BACKUP_DIR/refbot_$DATE.tar.gz $BACKUP_DIR/*.json $BACKUP_DIR/*.csv

# Remove old backups (keep 30 days)
find $BACKUP_DIR -name "refbot_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/refbot_$DATE.tar.gz"
```

Schedule with cron:

```bash
# Daily at 2 AM
0 2 * * * /opt/refbot/backup.sh
```

### Alerting

#### Email Alerts

```python
import smtplib
from email.message import EmailMessage

def send_alert(subject, message):
    msg = EmailMessage()
    msg['Subject'] = f"[RefBot] {subject}"
    msg['From'] = "refbot@example.com"
    msg['To'] = "admin@example.com"
    msg.set_content(message)
    
    with smtplib.SMTP('localhost') as s:
        s.send_message(msg)
```

#### Slack Alerts

```python
import requests

def send_slack_alert(message):
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    payload = {
        "text": f"🚨 RefBot Alert: {message}",
        "username": "RefBot",
        "icon_emoji": ":robot_face:"
    }
    requests.post(webhook_url, json=payload)
```

### Performance Monitoring

#### System Resources

```bash
# CPU and Memory usage
ps aux | grep python

# Disk usage
df -h /opt/refbot

# Network connections
netstat -an | grep 8000
```

#### Application Metrics

```bash
# View metrics via CLI
python -m cli.cli_commands metrics show

# Export for analysis
python -m cli.cli_commands metrics export --format json | jq '.'
```

## Security Best Practices

### API Security

#### Enable Authentication

Update config.json:

```json
{
  "api": {
    "enable": true,
    "host": "0.0.0.0",
    "port": 8000,
    "auth_token": "use-environment-variable",
    "require_auth": true
  }
}
```

Set token via environment:

```bash
export REFBOT_API_TOKEN="$(openssl rand -hex 32)"
```

#### Use HTTPS

Put RefBot behind reverse proxy (nginx, Caddy):

```nginx
server {
    listen 443 ssl http2;
    server_name refbot.example.com;
    
    ssl_certificate /etc/letsencrypt/live/refbot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/refbot.example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Network Security

#### Firewall Rules (Linux)

```bash
# Allow only specific IPs to access API
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Block all other access
sudo ufw deny 8000
```

#### Rate Limiting

Enable rate limiting in config:

```json
{
  "api": {
    "rate_limit": {
      "enabled": true,
      "requests_per_minute": 60
    }
  }
}
```

### File Permissions

Set appropriate permissions:

```bash
# Application files
chmod 750 /opt/refbot
chmod 640 /opt/refbot/config.json

# Log files
chmod 640 /var/log/refbot/*.log
chown refbot:refbot /var/log/refbot/*.log

# Data files
chmod 600 /opt/refbot/data/*.json
```

### Regular Updates

Keep dependencies updated:

```bash
# Update Python packages
pip list --outdated
pip install --upgrade -r requirements.txt

# Update Playwright browsers
playwright install chromium

# Check for security vulnerabilities
pip-audit
```

## Troubleshooting

### Common Issues

#### Service Won't Start

**Check logs**:
```bash
sudo journalctl -u refbot -n 50
```

**Check configuration**:
```bash
python -m cli.cli_commands config validate
```

**Check permissions**:
```bash
ls -la /opt/refbot
ls -la /var/log/refbot
```

#### High CPU Usage

**Reduce worker counts**:
```json
{
  "http_workers": 100,
  "https_workers": 100
}
```

**Check for stuck processes**:
```bash
ps aux | grep python
htop
```

#### High Memory Usage

**Reduce log buffer**:
```json
{
  "log_buffer_lines": 10
}
```

**Check for memory leaks**:
```bash
# Monitor memory over time
watch -n 5 'ps aux | grep python'
```

#### API Not Responding

**Check if running**:
```bash
curl http://localhost:8000/api/health
```

**Check port availability**:
```bash
netstat -tulpn | grep 8000
```

**Check firewall**:
```bash
sudo ufw status
```

#### Plugin Errors

**Check plugin configuration**:
```bash
python -m cli.cli_commands plugin list
python -m cli.cli_commands plugin status plugin_name
```

**View plugin logs**:
```bash
grep "plugin_name" /var/log/refbot/refbot.log
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or via environment:

```bash
export REFBOT_LOG_LEVEL="DEBUG"
```

### Performance Tuning

#### For High Throughput

```json
{
  "http_workers": 400,
  "https_workers": 400,
  "scraper_interval_minutes": 10,
  "timeout": 5
}
```

#### For Stability

```json
{
  "http_workers": 100,
  "https_workers": 100,
  "timeout": 15,
  "retries": 5
}
```

#### For Low Resources

```json
{
  "http_workers": 50,
  "https_workers": 50,
  "dashboard_refresh_rate": 0.5,
  "log_buffer_lines": 10
}
```

## Maintenance Checklist

### Daily

- [ ] Check service status
- [ ] Review error logs
- [ ] Monitor resource usage (CPU, memory, disk)
- [ ] Verify proxy counts are healthy

### Weekly

- [ ] Review metrics and trends
- [ ] Check for plugin errors
- [ ] Verify backups are running
- [ ] Review security logs

### Monthly

- [ ] Update dependencies
- [ ] Review and update configuration
- [ ] Test disaster recovery procedures
- [ ] Review and clean old logs
- [ ] Check disk space usage

### Quarterly

- [ ] Security audit
- [ ] Performance optimization review
- [ ] Update documentation
- [ ] Review and update backup retention
- [ ] Capacity planning

## Scaling Strategies

### Vertical Scaling

Increase resources on single server:

```json
{
  "http_workers": 500,
  "https_workers": 500
}
```

### Horizontal Scaling

Deploy multiple instances behind load balancer:

```
┌─────────────┐
│Load Balancer│
└──────┬──────┘
       │
   ┌───┴────┬────────┬────────┐
   │        │        │        │
┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│RefBot│ │RefBot│ │RefBot│ │RefBot│
│  #1  │ │  #2  │ │  #3  │ │  #4  │
└──────┘ └──────┘ └──────┘ └──────┘
```

**Load balancer configuration** (nginx):

```nginx
upstream refbot_backend {
    least_conn;
    server 10.0.1.10:8000;
    server 10.0.1.11:8000;
    server 10.0.1.12:8000;
    server 10.0.1.13:8000;
}

server {
    listen 80;
    server_name refbot.example.com;
    
    location / {
        proxy_pass http://refbot_backend;
    }
}
```

### Database Sharding

For very large deployments, shard proxy database by region or protocol.

---

**RefBot Deployment Guide**

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Status**: Production Ready
    print(f"Working proxies: {stats['working_count']}")
    print(f"Average speed: {stats['average_speed']:.2f}s")
    
    import time
    time.sleep(60)  # Check every minute
```

### Use Case 3: Rotate Proxies
```python
from main import get_proxies
import random

proxies = get_proxies("ANY")

if proxies:
    # Get random proxy
    proxy = random.choice(proxies)
    proxy_addr = f"http://{proxy.ip}:{proxy.port}"
    
    # Use it...
    print(f"Using: {proxy_addr}")
```

### Use Case 4: Export for Selenium
```python
from main import export_proxies

# Export all working proxies
count = export_proxies("selenium_proxies.txt")
print(f"Exported {count} proxies for Selenium")

# In your Selenium code:
with open("selenium_proxies.txt") as f:
    proxies = f.read().strip().split("\n")

# Use with Selenium...
```

## ⚙️ Configuration Options

Edit `config.json` to customize:

```json
{
  "url": "https://httpbin.org/ip",              // Target URL for page loading
  "timeout": 8,                                  // Request timeout (seconds)
  "retries": 3,                                  // Retry count for failed requests
  "verify_ssl": true,                            // Verify SSL certificates
  "scraper_interval_minutes": 20,                // How often to re-scrape (minutes)
  "http_workers": 200,                           // HTTP validation workers
  "https_workers": 200,                          // HTTPS validation workers
  "log_buffer_lines": 20,                        // Event log buffer size
  "save_state_interval_seconds": 10,             // State save interval (seconds)
  "proxy_revalidate_hours": 1,                   // Re-validate old proxies (hours)
  "dashboard_refresh_rate": 1,                   // Dashboard refresh rate (Hz)
  "cookies": {                                   // Optional cookies for requests
    "cookie_consent": "accepted"
  }
}
```

### Recommended Settings

**For Maximum Proxies (Gathering Mode):**
```json
{
  "scraper_interval_minutes": 5,
  "http_workers": 400,
  "https_workers": 400,
  "timeout": 5
}
```

**For Quality Over Quantity (Testing Mode):**
```json
{
  "scraper_interval_minutes": 60,
  "http_workers": 100,
  "https_workers": 100,
  "timeout": 15
}
```

**For Low Resource Usage (Minimal Mode):**
```json
{
  "scraper_interval_minutes": 120,
  "http_workers": 50,
  "https_workers": 50,
  "timeout": 10
}
```

## 📈 Performance Tuning

### If Dashboard Runs Slow:
1. Reduce `http_workers` and `https_workers`
2. Increase `timeout` for less frequent retries
3. Increase `scraper_interval_minutes`

### If Memory Usage is High:
1. Reduce `log_buffer_lines` (default 20)
2. Reduce `http_workers` and `https_workers`
3. Close other applications

### If Getting Few Proxies:
1. Reduce `timeout` to accept faster proxies
2. Increase `http_workers` and `https_workers`
3. Reduce `scraper_interval_minutes` (scrape more often)

### If Want Fastest Proxies:
1. Increase `timeout` (be more selective)
2. Increase validation worker count
3. Let it run longer (more validation = better filtering)

## 🔍 Monitoring & Debugging

### Check Working Proxies
```python
from main import get_proxies

proxies = get_proxies("ANY")
print(f"Total working: {len(proxies)}")
for p in proxies:
    print(f"  {p.ip}:{p.port} - {p.response_time:.2f}s - {p.protocol}")
```

### Check Metrics
```python
from main import get_stats

stats = get_stats()
print(f"Scraped:     {stats['scraped_count']}")
print(f"Valid HTTP:  {stats['http_valid_count']}")
print(f"Valid HTTPS: {stats['https_valid_count']}")
print(f"Working:     {stats['working_count']}")
print(f"Testing:     {stats['testing_count']}")
print(f"Failed:      {stats['failed_count']}")
print(f"Avg Speed:   {stats['average_speed']:.2f}s")
```

### View Metrics File
```bash
# CSV format - open in spreadsheet app
cat metrics.csv

# Or from Python
import pandas as pd
df = pd.read_csv("metrics.csv")
print(df)
```

### View Logs
```bash
# JSON format
cat working_proxies.json | python -m json.tool | head -20
```

## 🚨 Troubleshooting

### Issue: "No working proxies" after 5 minutes
**Solution:**
1. Check internet connection
2. Verify proxy sources are accessible
3. Try reducing timeout in config.json
4. Check logs for error patterns

### Issue: Dashboard crashes
**Solution:**
1. Make terminal wider (100+ columns)
2. Use modern terminal app (Windows Terminal, iTerm2, etc.)
3. Reduce log buffer size in config.json
4. Check Python version is 3.10+

### Issue: Very few proxies found
**Solution:**
1. Wait longer (first scrape is 5+ minutes)
2. Reduce timeout value
3. Increase worker counts
4. Check proxy sources are working

### Issue: High CPU/Memory usage
**Solution:**
1. Reduce `http_workers` and `https_workers`
2. Reduce `log_buffer_lines`
3. Increase `scraper_interval_minutes`
4. Close other applications

### Issue: Dashboard shows outdated proxies
**Solution:**
1. Check `dashboard_state.json` file
2. Delete state files to reset:
   ```bash
   rm working_proxies.json dashboard_state.json
   ```
3. Restart dashboard
4. Wait for new proxies to validate

## 📁 Important Files

| File | Purpose |
|------|---------|
| `dashboard.py` | Main entry point - run this! |
| `working_proxies.json` | Your proxy database |
| `metrics.csv` | Historical validation data |
| `config.json` | Settings (editable) |
| `dashboard_state.json` | Dashboard backup state |
| `verify_system.py` | System verification |

## 🔐 Security Notes

1. **Proxy Privacy**: Your proxies are stored locally
2. **No External Tracking**: No data sent anywhere
3. **SSL Verification**: Enabled by default
4. **Timeout Protection**: Defaults to 8 seconds
5. **Error Handling**: Failed requests logged locally

## 📚 Additional Resources

- **Full Docs**: See `README_NEW.md`
- **Quick Reference**: See `QUICKSTART_NEW.md`
- **Version Info**: See `CHANGELOG.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`

## 🎯 Summary

1. **Run**: `python dashboard.py`
2. **Wait**: ~5 minutes for first proxies
3. **Get**: Use `get_proxies()` or export
4. **Use**: Pass to your applications
5. **Monitor**: Watch dashboard for stats

That's it! RefBot handles everything else automatically.

---

**Status**: ✅ READY TO USE

Questions? Check the documentation files or review configuration options above.
