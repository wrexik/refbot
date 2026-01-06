#!/usr/bin/env python
"""
RefBot System Verification Script
Checks all components are installed, importable, and functional
"""

import sys
import json
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python {version.major}.{version.minor} - requires 3.10+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check all required packages are installed"""
    required = {
        'requests': 'HTTP library',
        'rich': 'Terminal UI',
        'playwright': 'Browser automation',
        'urllib3': 'HTTP utilities',
    }
    
    all_ok = True
    for module, desc in required.items():
        try:
            __import__(module)
            print(f"✅ {module:15} - {desc}")
        except ImportError:
            print(f"❌ {module:15} - {desc} [MISSING]")
            all_ok = False
    
    return all_ok

def check_files():
    """Check all required files exist"""
    required_files = [
        'dashboard.py',
        'proxy_manager.py',
        'worker_threads.py',
        'persistence.py',
        'scraper.py',
        'checker.py',
        'main.py',
        'config.json',
        'requirements.txt',
    ]
    
    all_ok = True
    for filename in required_files:
        path = Path(filename)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {filename:25} ({size:6} bytes)")
        else:
            print(f"❌ {filename:25} [MISSING]")
            all_ok = False
    
    return all_ok

def check_imports():
    """Check all modules can be imported"""
    modules = [
        ('dashboard', 'AdvancedDashboard'),
        ('proxy_manager', 'ProxyManager'),
        ('worker_threads', 'WorkerThreads'),
        ('persistence', 'PersistenceManager'),
        ('persistence', 'MetricsExporter'),
        ('scraper', 'fetch_proxies_stream'),
        ('checker', 'validate_http_proxy'),
        ('checker', 'validate_https_proxy'),
        ('main', 'get_proxies'),
    ]
    
    all_ok = True
    for module_name, class_name in modules:
        try:
            module = __import__(module_name)
            if hasattr(module, class_name):
                print(f"✅ {module_name:20} → {class_name}")
            else:
                print(f"❌ {module_name:20} → {class_name} [NOT FOUND]")
                all_ok = False
        except Exception as e:
            print(f"❌ {module_name:20} → {class_name} [{str(e)[:30]}]")
            all_ok = False
    
    return all_ok

def check_config():
    """Check configuration file"""
    try:
        with open('config.json') as f:
            config = json.load(f)
        
        required_keys = [
            'url', 'timeout', 'scraper_interval_minutes',
            'http_workers', 'https_workers',
        ]
        
        all_ok = True
        for key in required_keys:
            if key in config:
                print(f"✅ config['{key}'] = {config[key]}")
            else:
                print(f"❌ config['{key}'] [MISSING]")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"❌ config.json - {str(e)}")
        return False

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("RefBot System Verification")
    print("="*60 + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Files", check_files),
        ("Module Imports", check_imports),
        ("Configuration", check_config),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n[{name}]")
        print("-" * 60)
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    all_ok = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
        if not result:
            all_ok = False
    
    print("="*60)
    
    if all_ok:
        print("\n🎉 All checks passed!")
        print("\nYou're ready to run:")
        print("  python dashboard.py")
        print("\nThe dashboard will:")
        print("  • Scrape proxies from 38 sources")
        print("  • Validate with 200 HTTP/HTTPS workers each")
        print("  • Display a 7-panel Rich dashboard")
        print("  • Auto-save state every 10 seconds")
        print("\nPress Ctrl+C to stop.")
        return 0
    else:
        print("\n⚠️  Some checks failed!")
        print("\nTo fix:")
        print("  pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
