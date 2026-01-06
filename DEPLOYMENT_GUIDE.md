# RefBot - Deployment & Usage Guide

## ✅ System Status: READY FOR DEPLOYMENT

All components verified and operational. The system is production-ready.

## 🚀 Start Using RefBot

### Step 1: Run the Dashboard
```bash
python dashboard.py
```

### Step 2: Wait for Proxies
- First scrape cycle: ~5 minutes
- Dashboard updates every 1 second
- Stats panel shows progress
- Logs panel shows activity

### Step 3: Monitor
Watch the 7-panel dashboard:
1. **Header** - Current time and uptime
2. **Stats** - Scraped, validated, working counts
3. **Config** - Active settings
4. **Protocols** - HTTP/HTTPS distribution
5. **Top Proxies** - Fastest 8 proxies
6. **Loading** - Page loader status
7. **Help** - Keyboard shortcuts
8. **Logs** - Color-coded activity

### Step 4: Get Proxies

**Option A: While Dashboard Running**
```python
from main import get_proxies

proxies = get_proxies("HTTPS")  # "HTTP", "HTTPS", or "ANY"
for p in proxies[:5]:
    print(f"{p.ip}:{p.port} - {p.response_time:.2f}s")
```

**Option B: Export to File**
Press `E` in dashboard to export to file.

Or from Python:
```python
from main import export_proxies
count = export_proxies("working_proxies.txt")
print(f"Exported {count} proxies")
```

**Option C: Get Statistics**
```python
from main import get_stats
stats = get_stats()
print(f"Working: {stats['working_count']}")
print(f"Testing: {stats['testing_count']}")
print(f"Average Speed: {stats['average_speed']:.2f}s")
```

## 📊 What Each Panel Shows

### Header Panel
```
Time: 14:32:15 | Uptime: 00:05:23 | Mode: Scraping
```
- Current server time
- How long dashboard has been running
- Current operational mode

### Stats Panel
```
Scraped:      342    (proxies found from sources)
HTTP Valid:    89    (working with HTTP)
HTTPS Valid:   84    (working with HTTPS)
Working:      127    (total valid proxies)
Testing:       45    (currently being validated)
Failed:        67    (failed to validate)
Avg Speed:  0.42s   (average response time)
Total:       239    (total unique proxies seen)
```

### Config Panel
```
URL:        https://httpbin.org/ip
Timeout:    8 seconds
Workers:    200 HTTP + 200 HTTPS
Interval:   20 minutes between scrapes
Log Lines:  20 buffer size
Refresh:    1 Hz (per second)
Save:       Every 10 seconds
```

### Protocol Distribution
```
HTTP:   ██████████████░░ 45%
HTTPS:  █████████░░░░░░░ 35%
BOTH:   ██░░░░░░░░░░░░░░ 20%
```
Shows which proxies support which protocols.

### Top Proxies
```
45.76.12.34:8080      0.32s (HTTPS)
102.23.44.55:3128     0.38s (HTTP)
178.34.12.67:8888     0.45s (BOTH)
... (5 more)
```
Fastest working proxies by response time.

### Loading Status
```
Active:      No
Success:     12
Failed:       3
Current:     idle
```
Shows page loader statistics if using integrated browser automation.

### Event Log
```
14:32:15 ✓ Validated 12.34.56.78:8080 (HTTPS, 0.42s)
14:32:14 ✓ Added proxy 45.32.44.23:3128 from source
14:32:13 ✗ Failed to validate 123.45.67.89:9999
```
Color-coded log with latest 20 events:
- 🟢 Green = success
- 🟡 Yellow = info
- 🔴 Red = error/failure

## 🎯 Use Cases

### Use Case 1: Get HTTPS Proxies
```python
from main import get_proxies
import requests

# Get HTTPS-only proxies
proxies = get_proxies("HTTPS")

if proxies:
    proxy = proxies[0]  # Get first (fastest)
    proxy_addr = f"http://{proxy.ip}:{proxy.port}"
    
    response = requests.get(
        "https://example.com",
        proxies={"https": proxy_addr},
        timeout=5
    )
    print(response.status_code)
```

### Use Case 2: Monitor Proxy Quality
```python
from main import get_stats

while True:
    stats = get_stats()
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
