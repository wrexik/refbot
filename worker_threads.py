import threading
import time
import queue
from typing import Optional, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from proxy_manager import ProxyManager
from scraper import fetch_proxies_stream
from checker import validate_http_proxy, validate_https_proxy


class WorkerThreads:
    """Manages three concurrent worker threads: scraper, HTTP validator, HTTPS validator"""
    
    def __init__(self, 
                 manager: ProxyManager,
                 http_workers: int = 200,
                 https_workers: int = 200,
                 scraper_interval_minutes: int = 5,
                 log_callback: Optional[Callable[[str, str], None]] = None):
        """
        Initialize worker threads.
        
        Args:
            manager: ProxyManager instance
            http_workers: Number of HTTP validation workers
            https_workers: Number of HTTPS validation workers
            scraper_interval_minutes: Minutes between full scrape cycles
            log_callback: Callable(level: str, message: str) for logging
        """
        self.manager = manager
        self.http_workers = http_workers
        self.https_workers = https_workers
        self.scraper_interval_minutes = scraper_interval_minutes
        self.log_callback = log_callback or self._default_log
        
        # Thread control
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Work queues
        self.proxy_queue = queue.Queue()  # New proxies from scraper
        self.http_validate_queue = queue.Queue()  # Proxies to validate HTTP
        self.https_validate_queue = queue.Queue()  # Proxies to validate HTTPS
        
        # Threads
        self.scraper_thread: Optional[threading.Thread] = None
        self.http_validator_thread: Optional[threading.Thread] = None
        self.https_validator_thread: Optional[threading.Thread] = None
        
        # Stats
        self.scraped_this_cycle = 0
        self.http_validated_this_cycle = 0
        self.https_validated_this_cycle = 0
    
    def _default_log(self, level: str, message: str):
        """Default logging function"""
        print(f"[{level}] {message}")
    
    def start(self):
        """Start all worker threads"""
        if self.running:
            return
        
        self.running = True
        self.shutdown_event.clear()
        
        # Start scraper thread
        self.scraper_thread = threading.Thread(target=self._scraper_worker, daemon=False)
        self.scraper_thread.start()
        
        # Start HTTP validator thread
        self.http_validator_thread = threading.Thread(target=self._http_validator_worker, daemon=False)
        self.http_validator_thread.start()
        
        # Start HTTPS validator thread
        self.https_validator_thread = threading.Thread(target=self._https_validator_worker, daemon=False)
        self.https_validator_thread.start()
        
        self.log_callback("INFO", "All worker threads started")
    
    def stop(self):
        """Stop all worker threads gracefully"""
        if not self.running:
            return
        
        self.log_callback("INFO", "Shutting down worker threads...")
        self.running = False
        self.shutdown_event.set()
        
        # Wait for threads to finish (with timeout)
        if self.scraper_thread:
            self.scraper_thread.join(timeout=5)
        if self.http_validator_thread:
            self.http_validator_thread.join(timeout=5)
        if self.https_validator_thread:
            self.https_validator_thread.join(timeout=5)
        
        # Save final state
        self.manager.save_to_file()
        self.log_callback("INFO", "All worker threads stopped")
    
    def _scraper_worker(self):
        """Worker thread: fetch proxies from sources"""
        self.log_callback("INFO", "Scraper worker started")
        
        while not self.shutdown_event.is_set():
            try:
                self.scraped_this_cycle = 0
                self.log_callback("INFO", "Starting proxy scrape cycle...")
                self.manager.set_last_scrape_time()
                
                def scrape_callback(source_url: str, status: str):
                    self.log_callback("INFO", f"{source_url[:50]}... → {status}")
                
                # Stream proxies directly into manager
                for ip, port, source, protocol_hint in fetch_proxies_stream(scrape_callback):
                    if self.shutdown_event.is_set():
                        break
                    
                    proxy = self.manager.add_proxy(ip, port, source)
                    self.scraped_this_cycle += 1
                    
                    # Queue for HTTP validation
                    self.http_validate_queue.put((ip, port))
                
                self.log_callback("SUCCESS", f"Scrape cycle complete: {self.scraped_this_cycle} new proxies")
                
                # Wait for next cycle
                wait_time = self.scraper_interval_minutes * 60
                self.log_callback("INFO", f"Next scrape in {self.scraper_interval_minutes} minutes")
                self.shutdown_event.wait(wait_time)
                
            except Exception as e:
                self.log_callback("ERROR", f"Scraper worker error: {str(e)[:100]}")
                time.sleep(10)
    
    def _http_validator_worker(self):
        """Worker thread: validate HTTP proxies"""
        self.log_callback("INFO", "HTTP validator worker started")
        
        with ThreadPoolExecutor(max_workers=self.http_workers) as executor:
            futures = {}
            
            while not self.shutdown_event.is_set() or not self.http_validate_queue.empty():
                try:
                    # Add new tasks if queue has items and we have capacity
                    while len(futures) < self.http_workers and not self.http_validate_queue.empty():
                        try:
                            ip, port = self.http_validate_queue.get(timeout=0.1)
                            future = executor.submit(validate_http_proxy, ip, port)
                            futures[(ip, port)] = future
                        except queue.Empty:
                            break
                    
                    # Check completed futures
                    completed = [(key, futures[key]) for key in list(futures.keys()) 
                                if futures[key].done()]
                    
                    for (ip, port), future in completed:
                        try:
                            result = future.result(timeout=1)
                            del futures[(ip, port)]
                            
                            if result["success"]:
                                self.manager.validate_http(ip, port, result["speed"], result["location"])
                                self.http_validated_this_cycle += 1
                                self.log_callback("SUCCESS", f"HTTP valid: {ip}:{port} → {result['location']} ({result['speed']:.2f}s)")
                                
                                # Queue for HTTPS validation
                                self.https_validate_queue.put((ip, port))
                            else:
                                self.log_callback("WARNING", f"HTTP fail: {ip}:{port} → {result['error']}")
                        except Exception as e:
                            self.log_callback("ERROR", f"HTTP validation error: {str(e)[:100]}")
                            if (ip, port) in futures:
                                del futures[(ip, port)]
                    
                    # Update testing count
                    self.manager.set_testing_count(len(futures) + self.http_validate_queue.qsize())
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.log_callback("ERROR", f"HTTP validator worker error: {str(e)[:100]}")
                    time.sleep(1)
    
    def _https_validator_worker(self):
        """Worker thread: validate HTTPS proxies"""
        self.log_callback("INFO", "HTTPS validator worker started")
        
        with ThreadPoolExecutor(max_workers=self.https_workers) as executor:
            futures = {}
            
            while not self.shutdown_event.is_set() or not self.https_validate_queue.empty():
                try:
                    # Add new tasks if queue has items and we have capacity
                    while len(futures) < self.https_workers and not self.https_validate_queue.empty():
                        try:
                            ip, port = self.https_validate_queue.get(timeout=0.1)
                            future = executor.submit(validate_https_proxy, ip, port)
                            futures[(ip, port)] = future
                        except queue.Empty:
                            break
                    
                    # Check completed futures
                    completed = [(key, futures[key]) for key in list(futures.keys()) 
                                if futures[key].done()]
                    
                    for (ip, port), future in completed:
                        try:
                            result = future.result(timeout=1)
                            del futures[(ip, port)]
                            
                            if result["success"]:
                                self.manager.validate_https(ip, port, result["speed"], result["location"])
                                self.https_validated_this_cycle += 1
                                self.log_callback("SUCCESS", f"HTTPS valid: {ip}:{port} → {result['location']} ({result['speed']:.2f}s)")
                            else:
                                self.log_callback("WARNING", f"HTTPS fail: {ip}:{port} → {result['error']}")
                        except Exception as e:
                            self.log_callback("ERROR", f"HTTPS validation error: {str(e)[:100]}")
                            if (ip, port) in futures:
                                del futures[(ip, port)]
                    
                    # Update testing count
                    self.manager.set_testing_count(len(futures) + self.https_validate_queue.qsize())
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.log_callback("ERROR", f"HTTPS validator worker error: {str(e)[:100]}")
                    time.sleep(1)
    
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue sizes"""
        return {
            "http_validate": self.http_validate_queue.qsize(),
            "https_validate": self.https_validate_queue.qsize(),
            "scraped_this_cycle": self.scraped_this_cycle,
            "http_validated_this_cycle": self.http_validated_this_cycle,
            "https_validated_this_cycle": self.https_validated_this_cycle,
        }
