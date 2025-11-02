import requests
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import logging
from datetime import datetime
from functools import wraps
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level for all libraries
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ctf_solver.log'),
        logging.StreamHandler()
    ]
)

# Get our main logger and set it to DEBUG level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set specific library loggers to INFO level to reduce noise
logging.getLogger('openai').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('selenium').setLevel(logging.INFO)
logging.getLogger('selenium.webdriver').setLevel(logging.INFO)
logging.getLogger('selenium.webdriver.remote').setLevel(logging.INFO)
logging.getLogger('selenium.webdriver.common').setLevel(logging.INFO)
logging.getLogger('requests').setLevel(logging.INFO)
logging.getLogger('webdriver_manager').setLevel(logging.INFO)
logging.getLogger('langchain').setLevel(logging.INFO)
logging.getLogger('langchain_openai').setLevel(logging.INFO)
logging.getLogger('langchain_core').setLevel(logging.INFO)
logging.getLogger('langgraph').setLevel(logging.INFO)

def timing_decorator(func):
    """Decorator to add timing and logging to functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        logger.info(f"🚀 Starting {func_name}")
        logger.debug(f"📋 {func_name} args: {args[1:] if args else 'None'}, kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"✅ {func_name} completed in {duration:.3f}s")
            logger.debug(f"📤 {func_name} result length: {len(str(result)) if result else 0} chars")
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error(f"❌ {func_name} failed after {duration:.3f}s: {str(e)}")
            raise
    return wrapper

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

# Create the LLM with tools
llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",  # Replace with your deployment name
    api_version="2024-12-01-preview"
)
# Define all available browser tools
browser_tools = [
    navigate_to_url,
    find_elements,
    click_element,
    fill_form_field,
    execute_javascript,
    get_page_info,
    fetch_contents,
    get_console_logs
]
llm_with_tools = llm.bind_tools(browser_tools)

# Define the prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert CTF (Capture The Flag) solver. Your goal is to analyze the given challenge and solve it completely.

    When given a CTF challenge:
    1. First, navigate to the target URL to explore the challenge
    2. Analyze the page for clues, hints, or vulnerabilities
    3. Look for common CTF patterns like:
       - Hidden directories or files
       - Source code comments
       - HTTP headers with clues
       - Form parameters to exploit
       - Encoding/decoding challenges
       - SQL injection opportunities
       - XSS vulnerabilities
       - Authentication bypasses
    4. Use browser tools to interact with the page as needed in order to solve the challenge. Follow instructions on the HTML page if provided.
    5. Continue investigating until you find the flag (usually in format: flag{{...}} or similar)
    
    Available browser tools:
    - navigate_to_url: Navigate to any URL
    - find_elements: Find page elements using CSS selectors or XPath
    - click_element: Click on buttons, links, or other clickable elements
    - fill_form_field: Fill in form inputs and textareas
    - execute_javascript: Run JavaScript code in the browser
    - get_page_info: Get comprehensive page information
    - fetch_contents: Fetch raw contents of a URL using HTTP requests (useful for APIs, raw HTML, headers)
    - get_console_logs: Get JavaScript console logs and error messages
    
    CRITICAL RULES:
    1. USE ONLY ONE TOOL AT A TIME - Never call multiple tools simultaneously
    2. Wait for each tool's response before deciding on the next action
    3. After any action that changes the page state (clicking, filling forms, executing JavaScript), 
       ALWAYS immediately use get_page_info to check what the current page looks like
    4. This is crucial for detecting:
       - New content that appears after interactions
       - Redirects to new pages
       - Hidden elements that become visible
       - Error messages or success messages
       - Flags that only appear after specific actions
    
    Keep exploring until you solve the challenge completely. Say "CHALLENGE SOLVED" when you find the flag."""),
    ("human", "CTF Challenge: {input_data}")
])

def agent_node(state: MessagesState):
    """Main agent node that processes input and decides on actions."""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: MessagesState):
    """Determine if the agent should continue working or end."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Continue if there are tool calls to make
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Check if challenge is solved
    if hasattr(last_message, 'content') and last_message.content:
        content = last_message.content.upper()
        if "CHALLENGE SOLVED" in content or "FLAG{" in content or "CTF{" in content:
            return "__end__"
    
    # Stop after reasonable number of attempts (prevent infinite loops)
    if len(messages) > 15:  # Reduced limit
        return "__end__"
    
    # If no tools called and challenge not solved, END instead of continuing
    return "__end__"

# Create the graph
workflow = StateGraph(MessagesState)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(browser_tools))

# Set entry point
workflow.set_entry_point("agent")

# Simplified edges - remove the problematic "continue" node
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "__end__": "__end__"}
)

# Add edge from tools back to agent
workflow.add_edge("tools", "agent")

# Compile the graph
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

@timing_decorator
def run_ctf_solver(input_data: str):
    """Run the CTF solver with the given input data."""
    logger.info(f"🚀 Starting CTF solver for: {input_data}")
    
    start_format = time.time()
    messages = prompt.format_messages(input_data=input_data)
    logger.debug(f"⏱️ Message formatting took {time.time() - start_format:.3f}s")
    
    config = {
        "configurable": {"thread_id": "1"},
        "recursion_limit": 999999  # Set to effectively infinite
    }
    
    logger.info("🤖 AI Agent is working on the challenge...")
    logger.info("=" * 50)
    
    try:
        start_invoke = time.time()
        result = app.invoke({"messages": messages}, config)
        logger.info(f"⏱️ Graph execution completed in {time.time() - start_invoke:.3f}s")
        
        # Log message statistics
        message_count = len(result["messages"])
        total_chars = sum(len(str(msg.content)) if hasattr(msg, 'content') and msg.content else 0 
                         for msg in result["messages"])
        logger.info(f"📊 Total messages: {message_count}, Total characters: {total_chars}")
        
        # Print all messages for debugging
        for i, msg in enumerate(result["messages"]):
            if hasattr(msg, 'content') and msg.content:
                logger.debug(f"--- Step {i+1} ---")
                logger.debug(f"Message length: {len(msg.content)} chars")
                if len(msg.content) > 1000:
                    logger.debug(f"Message preview: {msg.content[:500]}...{msg.content[-500:]}")
                else:
                    logger.debug(f"Message: {msg.content}")
        
        final_content = result["messages"][-1].content
        logger.info(f"🏁 Final result length: {len(final_content)} chars")
        return final_content
    
    except Exception as e:
        logger.error(f"❌ CTF solver failed: {str(e)}")
        raise
    
    finally:
        # Always close the browser when done
        browser_manager.close()
        logger.info("🔒 Browser closed successfully")

if __name__ == "__main__":
    # Example usage
    sample_input = "https://i-spy.acmcyber.com/"
    
    logger.info("🚩 CTF Solver Starting...")
    logger.info(f"🎯 Target: {sample_input}")
    logger.info("Let the AI solve this challenge...")
    
    try:
        result = run_ctf_solver(sample_input)
        logger.info(f"🏁 Final Result: {result}")
    except Exception as e:
        logger.error(f"❌ CTF Solver failed with error: {e}")
        raise
