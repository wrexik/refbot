# RefBot Quick Start Guide

Get RefBot running in 2 minutes.

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python dashboard.py
```

## That's It!

The dashboard will:
1. Start scraping proxies from 38 sources
2. Validate them with 200 concurrent HTTP/HTTPS workers
3. Display a 7-panel Rich dashboard
4. Auto-save state every 10 seconds
5. Update every 1 second

## Dashboard Layout

```
┌─────────────────────────────────┐
│ Header (Time, Uptime, Mode)     │
├──────────────┬──────────────────┤
│ Stats Panel  │  Top Proxies     │
├──────────────┤  Loading Status  │
│ Config Panel │  Help & Shortcuts│
├──────────────┤──────────────────┤
│ Protocol Bar │  (7 panels total)│
└──────────────┴──────────────────┘
         Event Log (20 lines)
```

## Key Panels

| Panel | Shows |
|-------|-------|
| **Stats** | Scraped, Validated, Working, Failed, Avg Speed |
| **Config** | Current settings from config.json |
| **Protocols** | HTTP/HTTPS/BOTH distribution |
| **Top Proxies** | 8 fastest working proxies |
| **Loading** | Page loader status & success/fail counts |
| **Help** | Keyboard shortcuts |
| **Log** | Color-coded activity (20 lines) |

## Common Tasks

### Get Proxies After Dashboard Starts

Wait ~5 minutes, then in another terminal:

```python
from main import get_proxies
proxies = get_proxies("HTTPS")  # or "HTTP", "ANY"
print(f"Found {len(proxies)} working proxies")
for p in proxies[:5]:
    print(f"  {p.ip}:{p.port} - {p.response_time:.2f}s")
```

### Change Configuration

Edit `config.json`:

```json
{
  "scraper_interval_minutes": 20,
  "http_workers": 200,
  "https_workers": 200,
  "timeout": 8
}
```

Then restart dashboard: `python dashboard.py`

### Export Proxies

While dashboard running, press `E` key to export.

Or in Python:

```python
from main import export_proxies
count = export_proxies("my_proxies.txt")
print(f"Exported {count} proxies")
```

### Get Statistics

```python
from main import get_stats
stats = get_stats()
print(f"Working: {stats['working_count']}")
print(f"Testing: {stats['testing_count']}")
print(f"Failed: {stats['failed_count']}")
print(f"Avg Speed: {stats['average_speed']:.2f}s")
```

## Dashboard Features

| Feature | How to Use |
|---------|-----------|
| **Auto-Scrape** | Starts automatically, runs every 20 minutes |
| **Auto-Validate** | 400 concurrent workers (200 HTTP, 200 HTTPS) |
| **Auto-Save** | State saved to JSON every 10 seconds |
| **Live Stats** | Refreshes every 1 second |
| **Color Logs** | Green=success, Yellow=info, Red=errors |
| **Top Proxies** | Shows 8 fastest with response times |
| **Metrics Export** | CSV export to metrics.csv |

## Troubleshooting

### Dashboard shows "No working proxies"
- **Solution**: Wait 5 minutes for first scrape cycle
- Check that your internet is working
- Verify proxy sources are accessible

### Validation is slow
- **Solution**: Reduce worker count in config.json
- Increase timeout value
- Check network connectivity

### Terminal display is messed up
- **Solution**: Make terminal wider (100+ columns)
- Use Windows Terminal or modern terminal app
- Try in different terminal

## File Locations

| File | Purpose |
|------|---------|
| `working_proxies.json` | Persistent proxy database |
| `metrics.csv` | Validation statistics |
| `dashboard_state.json` | Dashboard backup |
| `config.json` | Configuration (editable) |

## Performance

- **First Scrape**: 5 minutes to gather 50+ proxies
- **Validation**: 1-2 seconds per proxy
- **Dashboard Update**: 1 second
- **Memory**: 2-5 MB for 100 proxies

## Next Steps

1. ✅ Run `python dashboard.py`
2. ✅ Wait for proxies to validate (~5 min)
3. ✅ Export with E key or `export_proxies()`
4. ✅ Use in your code with `get_proxies()`
5. ✅ Check metrics in `metrics.csv`

## For More Details

See [README.md](README.md) for complete documentation.
