import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from core.utils import timing_decorator

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.driver = None
        logger.info("🌐 BrowserManager initialized")
    
    @timing_decorator
    def get_driver(self):
        """Initialize and return a Chrome WebDriver instance."""
        if self.driver is None:
            logger.info("🔧 Initializing Chrome WebDriver...")
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Enable logging capabilities
            options.add_argument('--enable-logging')
            options.add_argument('--log-level=0')
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            
            # Set logging preferences to capture browser logs
            options.set_capability('goog:loggingPrefs', {
                'browser': 'ALL',
                'driver': 'ALL',
                'performance': 'ALL'
            })
            
            try:
                logger.debug("🔨 Creating Chrome WebDriver instance...")
                self.driver = webdriver.Chrome(options=options)
                self.driver.implicitly_wait(10)
                logger.info("✅ Chrome WebDriver initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Chrome driver: {e}")
                raise Exception(f"Failed to initialize Chrome driver: {e}")
        else:
            logger.debug("♻️ Reusing existing Chrome WebDriver instance")
        
        return self.driver
    
    @timing_decorator
    def close(self):
        """Close the browser."""
        if self.driver:
            logger.info("🔒 Closing Chrome WebDriver...")
            self.driver.quit()
            self.driver = None
            logger.info("✅ Chrome WebDriver closed successfully")
        else:
            logger.debug("ℹ️ No WebDriver to close")

# Global browser manager instance
browser_manager = BrowserManager()
