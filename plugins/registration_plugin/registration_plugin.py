"""Registration Plugin - Automated form registration with Playwright"""

import random
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

from plugins.base_plugin import BasePlugin, PluginStatus


logger = logging.getLogger(__name__)


@dataclass
class RegistrationConfig:
    """Registration form configuration"""
    url: str = ""
    first_name_selector: str = "input[name='firstName']"
    email_selector: str = "input[name='email']"
    submit_selector: str = "button[type='submit']"
    accept_cookies_selector: Optional[str] = None
    headless: bool = True
    batch_size: int = 1
    delay_between_submissions_ms: int = 1000
    proxy_url: Optional[str] = None


class RegistrationPlugin(BasePlugin):
    """Plugin for automated registration form submission"""
    
    def __init__(self, name: str, config_path: str):
        """Initialize registration plugin"""
        super().__init__(name, config_path)
        
        if not HAS_PLAYWRIGHT:
            self.logger.error("Playwright not installed. Install with: pip install playwright")
        
        self.reg_config = self._load_registration_config()
        self.first_names = self._load_first_names()
        self.domains = ["gmail.com", "yahoo.com", "outlook.com"]
        self.playwright = None
        self.browser = None
        self.context = None
        self.registered_emails = set()
    
    def _load_registration_config(self) -> RegistrationConfig:
        """Load registration-specific configuration"""
        config = RegistrationConfig()
        
        # Override with values from plugin_config.json
        config.url = self.config.get("url", config.url)
        config.first_name_selector = self.config.get("first_name_selector", config.first_name_selector)
        config.email_selector = self.config.get("email_selector", config.email_selector)
        config.submit_selector = self.config.get("submit_selector", config.submit_selector)
        config.accept_cookies_selector = self.config.get("accept_cookies_selector", config.accept_cookies_selector)
        config.headless = self.config.get("headless", config.headless)
        config.batch_size = max(1, self.config.get("batch_size", config.batch_size))
        config.delay_between_submissions_ms = max(0, self.config.get("delay_between_submissions_ms", config.delay_between_submissions_ms))
        config.proxy_url = self.config.get("proxy_url", config.proxy_url)
        
        # Validate required fields
        if not config.url:
            self.logger.error("No URL configured in plugin_config.json")
        if not config.first_name_selector:
            self.logger.warning("No first_name_selector configured")
        if not config.email_selector:
            self.logger.warning("No email_selector configured")
        if not config.submit_selector:
            self.logger.warning("No submit_selector configured")
        
        return config
    
    def _load_first_names(self) -> list:
        """Load first names from file or use defaults"""
        names = [
            "John", "Jane", "Michael", "Sarah", "David", "Emily",
            "Robert", "Jessica", "James", "Mary", "William", "Patricia",
            "Richard", "Jennifer", "Joseph", "Linda", "Thomas", "Barbara",
            "Charles", "Susan", "Christopher", "Jessica", "Daniel", "Sarah",
            "Matthew", "Karen", "Anthony", "Nancy", "Donald", "Lisa",
            "Steven", "Betty", "Paul", "Margaret", "Andrew", "Sandra",
            "Joshua", "Ashley", "Kenneth", "Kimberly", "Kevin", "Donna"
        ]
        
        # Try to load from user_agents.txt file (if exists with names)
        try:
            name_file = Path(__file__).parent.parent.parent / "first_names.txt"
            if name_file.exists():
                with open(name_file, 'r') as f:
                    file_names = [line.strip() for line in f if line.strip()]
                    if file_names:
                        return file_names
        except Exception as e:
            self.logger.debug(f"Could not load names from file: {e}")
        
        return names
    
    def _generate_email(self) -> str:
        """Generate random email"""
        first_name = random.choice(self.first_names)
        timestamp = int(time.time() * 1000) % 1000000
        domain = random.choice(self.domains)
        email = f"{first_name.lower()}{timestamp}@{domain}"
        return email
    
    def _get_random_proxy(self) -> Optional[str]:
        """Get a random proxy from proxy_manager or config"""
        # If explicit proxy in config, use that
        if self.reg_config.proxy_url:
            return self.reg_config.proxy_url
        
        # Try to get random proxy from shared proxy_manager
        if hasattr(self, "proxy_manager") and self.proxy_manager:
            try:
                working = self.proxy_manager.get_working("ANY")
                if working:
                    choice = random.choice(working)
                    proxy_url = f"http://{choice.address}"
                    self.logger.info(f"Selected random proxy: {proxy_url}")
                    return proxy_url
            except Exception as e:
                self.logger.debug(f"Could not get proxy from manager: {e}")
        
        return None
    
    def _setup_browser(self, proxy_url: Optional[str] = None) -> bool:
        """Setup Playwright browser with optional proxy"""
        try:
            if not HAS_PLAYWRIGHT:
                self.logger.error("Playwright not available")
                return False
            
            self.playwright = sync_playwright().start()
            
            browser_args = {}
            if proxy_url:
                if proxy_url.startswith("http"):
                    proxy_host = proxy_url.split("://", 1)[1]
                else:
                    proxy_host = proxy_url
                    proxy_url = f"http://{proxy_url}"
                browser_args["proxy"] = {"server": proxy_url}
                self.logger.info(f"Using proxy: {proxy_url}")
            
            self.browser = self.playwright.chromium.launch(
                headless=self.reg_config.headless,
                **browser_args
            )
            
            self.context = self.browser.new_context()
            self.logger.info("Browser setup successful")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to setup browser: {e}")
            return False
    
    def _teardown_browser(self) -> None:
        """Close browser and cleanup Playwright"""
        try:
            if hasattr(self, 'context') and self.context:
                self.context.close()
                self.context = None
        except Exception as e:
            self.logger.debug(f"Error closing context: {e}")
        
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
                self.browser = None
        except Exception as e:
            self.logger.debug(f"Error closing browser: {e}")
        
        try:
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
                self.playwright = None
        except Exception as e:
            self.logger.debug(f"Error stopping playwright: {e}")
    
    def _accept_cookies(self, page: Page) -> bool:
        """Accept cookies if selector provided"""
        if not self.reg_config.accept_cookies_selector:
            return True
        
        try:
            page.wait_for_selector(self.reg_config.accept_cookies_selector, timeout=2000)
            page.click(self.reg_config.accept_cookies_selector)
            self.logger.debug("Cookies accepted")
            return True
        except Exception as e:
            self.logger.debug(f"Could not accept cookies: {e}")
            return True  # Continue anyway
    
    def _fill_form(self, page: Page, first_name: str, email: str) -> bool:
        """Fill and submit registration form"""
        try:
            # Navigate to URL
            page.goto(self.reg_config.url, wait_until="domcontentloaded", timeout=10000)
            self.logger.debug(f"Loaded page: {self.reg_config.url}")
            
            # Accept cookies
            self._accept_cookies(page)
            
            # Wait for form to be ready
            page.wait_for_selector(self.reg_config.first_name_selector, timeout=5000)
            
            # Fill first name
            page.fill(self.reg_config.first_name_selector, first_name)
            self.logger.debug(f"Filled first name: {first_name}")
            
            # Fill email
            page.fill(self.reg_config.email_selector, email)
            self.logger.debug(f"Filled email: {email}")
            
            # Wait before submitting
            time.sleep(self.reg_config.delay_between_submissions_ms / 1000)
            
            # Submit form
            page.click(self.reg_config.submit_selector)
            self.logger.debug("Form submitted")
            
            # Wait for response
            page.wait_for_load_state("networkidle", timeout=5000)
            
            # Check for success (simple heuristic)
            if "success" in page.url.lower() or "thank" in page.content().lower():
                self.registered_emails.add(email)
                self.logger.info(f"Registration successful: {email}")
                return True
            else:
                self.logger.warning(f"Registration may have failed: {email}")
                return True  # Assume success if form submitted
        
        except Exception as e:
            self.logger.error(f"Form filling failed: {e}")
            return False
    
    def _register_batch(self) -> Dict[str, Any]:
        """Register a batch of users"""
        results = {
            "submitted": 0,
            "successful": 0,
            "failed": 0,
            "emails": []
        }
        
        try:
            # Get a random proxy for this batch
            proxy_url = self._get_random_proxy()
            
            # Always teardown and setup new browser to use different proxy each run
            self._teardown_browser()
            if not self._setup_browser(proxy_url):
                raise Exception("Browser setup failed")
            
            for i in range(self.reg_config.batch_size):
                if self.status != PluginStatus.RUNNING:
                    break
                
                first_name = random.choice(self.first_names)
                email = self._generate_email()
                
                page = self.context.new_page()
                
                try:
                    if self._fill_form(page, first_name, email):
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                    
                    results["submitted"] += 1
                    results["emails"].append(email)
                    
                except Exception as e:
                    self.logger.error(f"Registration error: {e}")
                    results["failed"] += 1
                
                finally:
                    page.close()
        
        except Exception as e:
            self.logger.error(f"Batch registration failed: {e}")
            results["failed"] += 1
        
        return results
    
    def execute(self) -> Dict[str, Any]:
        """Execute registration"""
        if not HAS_PLAYWRIGHT:
            self.logger.error("Playwright not installed")
            return {"error": "Playwright not installed", "response_time_ms": 0, "submitted": 0, "successful": 0, "failed": 1}
        
        if not self.reg_config.url:
            self.logger.error("No URL configured")
            return {"error": "No URL configured", "response_time_ms": 0, "submitted": 0, "successful": 0, "failed": 1}
        
        start_time = time.time()
        
        try:
            results = self._register_batch()
            response_time = (time.time() - start_time) * 1000
            
            return {
                "response_time_ms": response_time,
                "submitted": results["submitted"],
                "successful": results["successful"],
                "failed": results["failed"],
                "total_registered": len(self.registered_emails)
            }
        
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            response_time = (time.time() - start_time) * 1000
            return {"error": str(e), "response_time_ms": response_time, "submitted": 0, "successful": 0, "failed": 1}
    
    def stop(self) -> bool:
        """Stop plugin and cleanup"""
        result = super().stop()
        self._teardown_browser()
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get plugin status with registration details"""
        status = super().get_status()
        status["total_registered"] = len(self.registered_emails)
        status["proxy_url"] = self.reg_config.proxy_url
        status["target_url"] = self.reg_config.url
        return status
