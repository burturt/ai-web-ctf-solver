import time
import logging
import requests
from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from langchain_core.tools import tool

from core.browser import browser_manager
from core.utils import timing_decorator

logger = logging.getLogger(__name__)

@tool
@timing_decorator
def navigate_to_url(url: str) -> str:
    """Navigate to a URL and return the page source and basic info.
    
    Args:
        url: The URL to navigate to
    
    Returns:
        Page information including title, URL, and source
    """
    logger.info(f"🌐 Navigating to {url}")
    try:
        start_driver = time.time()
        driver = browser_manager.get_driver()
        logger.debug(f"⏱️ Driver retrieval took {time.time() - start_driver:.3f}s")
        
        start_nav = time.time()
        driver.get(url)
        logger.debug(f"⏱️ Page navigation took {time.time() - start_nav:.3f}s")
        
        # Wait for page to load
        logger.debug("⏳ Waiting for page to load (2s)")
        time.sleep(2)
        
        # Get basic page info
        start_info = time.time()
        title = driver.title
        current_url = driver.current_url
        page_source = driver.page_source
        cookies = driver.get_cookies()
        logger.debug(f"⏱️ Page info collection took {time.time() - start_info:.3f}s")
        
        logger.info(f"📄 Page loaded: '{title}' ({len(page_source)} chars)")
        logger.debug(f"🍪 Found {len(cookies)} cookies")
        
        result = f"""
URL: {current_url}
Title: {title}
Cookies: {cookies}
Page Source (first 100000 chars): {page_source[:100000]}
"""
        return result
        
    except Exception as e:
        logger.error(f"❌ Error navigating to URL {url}: {str(e)}")
        return f"Error navigating to URL: {str(e)}"

@tool
@timing_decorator
def find_elements(selector: str, selector_type: str = "css") -> str:
    """Find elements on the current page using CSS selector or XPath.
    
    Args:
        selector: The CSS selector or XPath to find elements
        selector_type: Type of selector ('css' or 'xpath')
    
    Returns:
        Information about found elements
    """
    logger.info(f"🔍 Finding elements with {selector_type} selector: {selector}")
    try:
        start_driver = time.time()
        driver = browser_manager.get_driver()
        logger.debug(f"⏱️ Driver retrieval took {time.time() - start_driver:.3f}s")
        
        start_find = time.time()
        if selector_type.lower() == "css":
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        elif selector_type.lower() == "xpath":
            elements = driver.find_elements(By.XPATH, selector)
        else:
            logger.error(f"❌ Invalid selector type: {selector_type}")
            return f"Invalid selector type: {selector_type}. Use 'css' or 'xpath'"
        
        logger.debug(f"⏱️ Element finding took {time.time() - start_find:.3f}s")
        
        if not elements:
            logger.info(f"🔍 No elements found with selector: {selector}")
            return f"No elements found with selector: {selector}"
        
        logger.info(f"📋 Found {len(elements)} elements")
        
        start_process = time.time()
        result = f"Found {len(elements)} elements:\n"
        for i, element in enumerate(elements[:10]):  # Limit to first 10 elements
            try:
                start_elem = time.time()
                tag = element.tag_name
                text = element.text[:200] if element.text else ""
                attrs = driver.execute_script("""
                    var items = {};
                    for (index = 0; index < arguments[0].attributes.length; ++index) {
                        items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value;
                    }
                    return items;
                """, element)
                
                result += f"\nElement {i+1}:\n"
                result += f"  Tag: {tag}\n"
                result += f"  Text: {text}\n"
                result += f"  Attributes: {attrs}\n"
                logger.debug(f"⏱️ Element {i+1} processing took {time.time() - start_elem:.3f}s")
            except Exception as e:
                logger.warning(f"⚠️ Error getting element {i+1} info: {str(e)}")
                result += f"  Error getting element info: {str(e)}\n"
        
        logger.debug(f"⏱️ Element processing took {time.time() - start_process:.3f}s")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error finding elements: {str(e)}")
        return f"Error finding elements: {str(e)}"

@tool
@timing_decorator
def click_element(selector: str, selector_type: str = "css") -> str:
    """Click on an element found by CSS selector or XPath.
    
    Args:
        selector: The CSS selector or XPath to find the element to click
        selector_type: Type of selector ('css' or 'xpath')
    
    Returns:
        Result of the click action
    """
    logger.info(f"🖱️ Clicking element with {selector_type} selector: {selector}")
    try:
        start_driver = time.time()
        driver = browser_manager.get_driver()
        logger.debug(f"⏱️ Driver retrieval took {time.time() - start_driver:.3f}s")
        
        start_wait = time.time()
        if selector_type.lower() == "css":
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
        elif selector_type.lower() == "xpath":
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
        else:
            logger.error(f"❌ Invalid selector type: {selector_type}")
            return f"Invalid selector type: {selector_type}. Use 'css' or 'xpath'"
        
        logger.debug(f"⏱️ Element wait took {time.time() - start_wait:.3f}s")
        
        start_click = time.time()
        element.click()
        logger.debug(f"⏱️ Click action took {time.time() - start_click:.3f}s")
        
        logger.debug("⏳ Waiting for page changes (1s)")
        time.sleep(1)  # Wait for any page changes
        
        new_url = driver.current_url
        logger.info(f"✅ Element clicked successfully. New URL: {new_url}")
        return f"Successfully clicked element. Current URL: {new_url}"
        
    except TimeoutException:
        logger.error(f"⏰ Timeout: Element not found or not clickable: {selector}")
        return f"Element not found or not clickable: {selector}"
    except Exception as e:
        logger.error(f"❌ Error clicking element: {str(e)}")
        return f"Error clicking element: {str(e)}"

@tool
@timing_decorator
def fill_form_field(selector: str, value: str, selector_type: str = "css") -> str:
    """Fill a form field (input, textarea) with a value.
    
    Args:
        selector: The CSS selector or XPath to find the form field
        value: The value to enter in the field
        selector_type: Type of selector ('css' or 'xpath')
    
    Returns:
        Result of the form filling action
    """
    logger.info(f"📝 Filling form field {selector} with value: {value}")
    try:
        start_driver = time.time()
        driver = browser_manager.get_driver()
        logger.debug(f"⏱️ Driver retrieval took {time.time() - start_driver:.3f}s")
        
        start_wait = time.time()
        if selector_type.lower() == "css":
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        elif selector_type.lower() == "xpath":
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
        else:
            logger.error(f"❌ Invalid selector type: {selector_type}")
            return f"Invalid selector type: {selector_type}. Use 'css' or 'xpath'"
        
        logger.debug(f"⏱️ Element wait took {time.time() - start_wait:.3f}s")
        
        start_fill = time.time()
        element.clear()
        element.send_keys(value)
        logger.debug(f"⏱️ Form filling took {time.time() - start_fill:.3f}s")
        
        logger.info(f"✅ Successfully filled form field with {len(value)} characters")
        return f"Successfully filled form field with value: {value}"
        
    except TimeoutException:
        logger.error(f"⏰ Timeout: Form field not found: {selector}")
        return f"Form field not found: {selector}"
    except Exception as e:
        logger.error(f"❌ Error filling form field: {str(e)}")
        return f"Error filling form field: {str(e)}"

@tool
@timing_decorator
def execute_javascript(script: str) -> str:
    """Execute JavaScript code in the browser and return the result.
    
    Args:
        script: JavaScript code to execute
    
    Returns:
        Result of the JavaScript execution
    """
    logger.info(f"🔧 Executing JavaScript ({len(script)} chars)")
    logger.debug(f"📜 JavaScript code: {script[:500]}{'...' if len(script) > 500 else ''}")
    try:
        start_driver = time.time()
        driver = browser_manager.get_driver()
        logger.debug(f"⏱️ Driver retrieval took {time.time() - start_driver:.3f}s")
        
        start_exec = time.time()
        result = driver.execute_script(script)
        logger.debug(f"⏱️ JavaScript execution took {time.time() - start_exec:.3f}s")
        
        logger.info(f"✅ JavaScript executed successfully. Result type: {type(result).__name__}")
        logger.debug(f"📤 JavaScript result: {str(result)[:200]}{'...' if len(str(result)) > 200 else ''}")
        return f"JavaScript executed successfully. Result: {str(result)}"
        
    except Exception as e:
        logger.error(f"❌ Error executing JavaScript: {str(e)}")
        return f"Error executing JavaScript: {str(e)}"

@tool
@timing_decorator
def get_page_info() -> str:
    """Get current page information including URL, title, cookies, and full HTML source.
    
    Returns:
        Complete page information including full HTML source
    """
    logger.info("📊 Getting current page state with full HTML")
    try:
        start_driver = time.time()
        driver = browser_manager.get_driver()
        logger.debug(f"⏱️ Driver retrieval took {time.time() - start_driver:.3f}s")
        
        start_basic = time.time()
        current_url = driver.current_url
        title = driver.title
        cookies = driver.get_cookies()
        page_source = driver.page_source
        logger.debug(f"⏱️ Basic page info collection took {time.time() - start_basic:.3f}s")
        
        start_elements = time.time()
        # Get some useful page elements
        logger.debug(f"⏱️ Element collection took {time.time() - start_elements:.3f}s")
        
        logger.info(f"📄 Page: '{title}' ({len(page_source)} chars HTML)")
        
        start_build = time.time()
        result = f"""
Current URL: {current_url}
Title: {title}
Cookies: {cookies}
"""
        result += f"\n\nFULL HTML SOURCE:\n{'-'*50}\n{page_source}\n{'-'*50}\n"
        logger.debug(f"⏱️ Result building took {time.time() - start_build:.3f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error getting page info: {str(e)}")
        return f"Error getting page info: {str(e)}"

@tool
@timing_decorator
def fetch_contents(url: str, method: str = "GET", headers: Dict[str, str] = None, data: str = None) -> str:
    """Fetch the raw contents of a URL using HTTP requests with the browser's current cookies.
    
    This maintains the same session state as the browser, including:
    - Authentication cookies
    - Session tokens
    - CSRF tokens
    - Any other browser cookies
    
    This is useful for:
    - Getting raw HTML source while authenticated
    - Accessing API endpoints with session data
    - Checking HTTP headers and responses
    - Making requests with custom headers
    - Testing different HTTP methods with browser session
    
    Args:
        url: The URL to fetch
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional headers as a dictionary
        data: Optional data to send with the request
    
    Returns:
        Response information including status, headers, and content
    """
    logger.info(f"🌐 Fetching contents from {url} using {method}")
    try:
        # Get current browser cookies if browser is active
        cookies = {}
        start_cookies = time.time()
        try:
            driver = browser_manager.get_driver()
            browser_cookies = driver.get_cookies()
            
            # Convert Selenium cookies to requests format
            for cookie in browser_cookies:
                cookies[cookie['name']] = cookie['value']
                
            logger.debug(f"🍪 Using {len(cookies)} cookies from browser session")
            logger.debug(f"⏱️ Cookie retrieval took {time.time() - start_cookies:.3f}s")
            
        except Exception as cookie_error:
            logger.warning(f"⚠️ Could not get browser cookies: {cookie_error}")
            logger.info("🔄 Proceeding without cookies...")
        
        # Prepare headers
        request_headers = headers or {}
        
        # Add common headers if not provided
        if 'User-Agent' not in request_headers:
            request_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        logger.debug(f"📋 Request headers: {request_headers}")
        logger.debug(f"📦 Request data length: {len(data) if data else 0}")
        
        start_request = time.time()
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=request_headers,
            cookies=cookies,
            data=data,
            timeout=10
        )
        logger.debug(f"⏱️ HTTP request took {time.time() - start_request:.3f}s")
        
        # Get response cookies for future reference
        response_cookies = dict(response.cookies)
        
        logger.info(f"📥 Response: {response.status_code} ({len(response.text)} chars)")
        logger.debug(f"🍪 Response cookies: {len(response_cookies)} received")
        
        result = f"""
Status Code: {response.status_code}
URL: {response.url}
Request Cookies Used: {cookies}
Response Cookies: {response_cookies}
Response Headers: {dict(response.headers)}

Content (first 10000 characters):
{response.text[:10000]}
"""
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error fetching contents: {str(e)}")
        return f"Error fetching contents: {str(e)}"

@tool
@timing_decorator
def get_console_logs() -> str:
    """Get JavaScript console logs from the browser.
    
    This captures console messages including:
    - console.log() messages
    - console.error() messages  
    - console.warn() messages
    - JavaScript errors and exceptions
    - Network errors
    - Other browser console output
    
    Returns:
        All console log entries with their levels and messages
    """
    logger.info("📝 Getting JavaScript console logs")
    try:
        start_driver = time.time()
        driver = browser_manager.get_driver()
        logger.debug(f"⏱️ Driver retrieval took {time.time() - start_driver:.3f}s")
        
        # Get console logs
        start_logs = time.time()
        logs = driver.get_log('browser')
        logger.debug(f"⏱️ Log retrieval took {time.time() - start_logs:.3f}s")
        logger.debug(f"🔍 Raw browser logs: {logs}")
        
        if not logs:
            logger.info("📝 No console logs found via browser API")
            return "No console logs found."
        
        logger.info(f"📝 Found {len(logs)} console log entries")
        
        start_process = time.time()
        result = f"Found {len(logs)} console log entries:\n\n"
        
        for i, log_entry in enumerate(logs):
            timestamp = log_entry.get('timestamp', 'Unknown')
            level = log_entry.get('level', 'Unknown')
            message = log_entry.get('message', 'No message')
            source = log_entry.get('source', 'Unknown')
            
            result += f"Entry {i+1}:\n"
            result += f"  Level: {level}\n"
            result += f"  Source: {source}\n"
            result += f"  Timestamp: {timestamp}\n"
            result += f"  Message: {message}\n\n"
        
        logger.debug(f"⏱️ Log processing took {time.time() - start_process:.3f}s")
        logger.debug(f"📤 Console logs result: {result[:200]}{'...' if len(result) > 200 else ''}")
        return result
        
    except Exception as e:
        logger.warning(f"⚠️ Browser logs API failed: {str(e)}, trying JavaScript fallback")
        # If browser logs aren't available, try to get them via JavaScript
        try:
            start_fallback = time.time()
            driver = browser_manager.get_driver()
            
            # Inject JavaScript to capture console logs
            console_script = """
            if (!window.consoleCapture) {
                window.consoleCapture = [];
                const originalLog = console.log;
                const originalError = console.error;
                const originalWarn = console.warn;
                const originalInfo = console.info;
                
                console.log = function(...args) {
                    window.consoleCapture.push({level: 'LOG', message: args.join(' '), timestamp: Date.now()});
                    originalLog.apply(console, args);
                };
                console.error = function(...args) {
                    window.consoleCapture.push({level: 'ERROR', message: args.join(' '), timestamp: Date.now()});
                    originalError.apply(console, args);
                };
                console.warn = function(...args) {
                    window.consoleCapture.push({level: 'WARN', message: args.join(' '), timestamp: Date.now()});
                    originalWarn.apply(console, args);
                };
                console.info = function(...args) {
                    window.consoleCapture.push({level: 'INFO', message: args.join(' '), timestamp: Date.now()});
                    originalInfo.apply(console, args);
                };
            }
            return window.consoleCapture || [];
            """
            
            captured_logs = driver.execute_script(console_script)
            logger.debug(f"⏱️ JavaScript fallback took {time.time() - start_fallback:.3f}s")
            
            if not captured_logs:
                logger.info("📝 No captured console logs available, logging enabled for future")
                return f"No console logs available. Console logging has been enabled for future messages. Error accessing browser logs: {str(e)}"
            
            logger.info(f"📝 Found {len(captured_logs)} captured console messages via JavaScript")
            result = f"Found {len(captured_logs)} captured console messages:\n\n"
            for i, log in enumerate(captured_logs):
                result += f"Entry {i+1}:\n"
                result += f"  Level: {log.get('level', 'Unknown')}\n"
                result += f"  Message: {log.get('message', 'No message')}\n"
                result += f"  Timestamp: {log.get('timestamp', 'Unknown')}\n\n"
            
            return result
            
        except Exception as inner_e:
            logger.error(f"❌ JavaScript fallback also failed: {str(inner_e)}")
            return f"Error getting console logs: {str(e)}. Fallback error: {str(inner_e)}"
