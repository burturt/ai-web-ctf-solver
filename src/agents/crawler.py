"""
Web crawler agent for mapping and exploring web applications
"""
import asyncio
from typing import List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.messages import BaseMessage
except ImportError:
    # Fallback - create simple replacements
    class ChatPromptTemplate:
        @classmethod
        def from_messages(cls, messages):
            return cls()
        def format(self, **kwargs):
            return "Default prompt"
    
    class BaseMessage:
        def __init__(self, content=""):
            self.content = content

from src.agents.base import BaseAgent
from src.models.state import CTFState, AgentType, CrawledPage
from src.utils.logging import get_logger

logger = get_logger(__name__)

class CrawlerAgent(BaseAgent):
    """Agent responsible for crawling and mapping web applications"""
    
    def __init__(self):
        super().__init__(AgentType.CRAWLER)
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        self.driver = None
        
    def _get_role_description(self) -> str:
        return """systematically crawl and map web applications to understand their structure, 
        identify all endpoints, forms, parameters, and potential entry points for security testing"""
    
    def _setup_selenium_driver(self):
        """Setup headless Chrome driver for JavaScript-heavy sites"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(f"--user-agent={self.config.get('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')}")
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(30)
            except Exception as e:
                logger.error(f"Failed to setup Selenium driver: {e}")
                self.driver = None
    
    def execute(self, state: CTFState) -> CTFState:
        """Execute the crawling process"""
        self.log_progress(state, "Starting web application crawling", 0.1)
        
        try:
            # Setup selenium if needed
            self._setup_selenium_driver()
            
            # Get initial crawling strategy from LLM
            crawl_plan = self._get_crawling_plan(state)
            self.log_progress(state, f"Generated crawling plan: {crawl_plan['strategy']}", 0.2)
            
            # Start crawling from the main URL
            base_url = state.challenge.url
            self._crawl_url(base_url, state, depth=0)
            
            # Perform intelligent crawling based on discovered content
            self._intelligent_crawl(state, crawl_plan)
            
            # Analyze crawled content with LLM
            analysis = self._analyze_crawled_content(state)
            state.source_analysis = analysis.get("summary", "")
            state.technology_stack = analysis.get("technologies", [])
            state.identified_endpoints = analysis.get("endpoints", [])
            
            self.log_progress(state, f"Crawling completed. Found {len(state.crawled_pages)} pages", 1.0)
            state.complete_agent(AgentType.CRAWLER)
            
        except Exception as e:
            self.log_error(state, f"Crawling failed: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return state
    
    def _get_crawling_plan(self, state: CTFState) -> Dict[str, Any]:
        """Use LLM to generate an intelligent crawling strategy"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", """Analyze this CTF challenge and create a crawling strategy:
            
Challenge URL: {url}
Challenge Description: {description}
Source Code: {source_code}
Flag Format: {flag_format}

Create a strategic crawling plan that identifies:
1. Key areas to focus on
2. Potential hidden endpoints to discover  
3. Forms and parameters to examine
4. Technology stack to identify
5. Common CTF vulnerability patterns to look for

Return a JSON object with strategy, focus_areas, and discovery_techniques.""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format(
                url=state.challenge.url,
                description=state.challenge.description,
                source_code=state.challenge.source_code or "Not provided",
                flag_format=state.challenge.flag_format
            ))
            
            # Parse LLM response into structured plan
            import json
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback to default plan
                return {
                    "strategy": "comprehensive_crawl",
                    "focus_areas": ["forms", "admin_panels", "file_uploads"],
                    "discovery_techniques": ["directory_bruteforce", "parameter_discovery", "js_analysis"]
                }
                
        except Exception as e:
            logger.error(f"Failed to generate crawling plan: {e}")
            return {
                "strategy": "basic_crawl", 
                "focus_areas": ["main_pages"],
                "discovery_techniques": ["follow_links"]
            }
    
    def _crawl_url(self, url: str, state: CTFState, depth: int = 0, max_depth: int = 3) -> CrawledPage:
        """Crawl a single URL and extract information"""
        if url in self.visited_urls or depth > max_depth:
            return None
            
        self.visited_urls.add(url)
        self.log_progress(state, f"Crawling: {url}", 0.3 + (depth * 0.1))
        
        try:
            # Try requests first for speed
            response = self.session.get(url, timeout=30, allow_redirects=True)
            content = response.text
            status_code = response.status_code
            headers = dict(response.headers)
            
            # If page seems to require JavaScript, use Selenium
            if self._needs_javascript(content) and self.driver:
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                content = self.driver.page_source
                
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {e}")
            return None
        
        # Parse content with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract page information
        page = CrawledPage(
            url=url,
            title=soup.title.string if soup.title else "",
            content=content,
            status_code=status_code,
            headers=headers
        )
        
        # Extract forms
        page.forms = self._extract_forms(soup, url)
        
        # Extract links
        page.links = self._extract_links(soup, url)
        
        # Extract input fields
        page.inputs = self._extract_inputs(soup)
        
        # Extract cookies
        if hasattr(self.session, 'cookies'):
            page.cookies = dict(self.session.cookies)
        
        # Add to state
        state.add_crawled_page(page)
        
        return page
    
    def _needs_javascript(self, content: str) -> bool:
        """Determine if a page likely needs JavaScript rendering"""
        js_indicators = [
            "React", "Angular", "Vue", "document.createElement", 
            "fetch(", "XMLHttpRequest", "spa", "single-page"
        ]
        return any(indicator in content for indicator in js_indicators)
    
    def _extract_forms(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract all forms from the page"""
        forms = []
        
        for form in soup.find_all('form'):
            form_data = {
                'action': urljoin(base_url, form.get('action', '')),
                'method': form.get('method', 'GET').upper(),
                'fields': []
            }
            
            # Extract input fields
            for input_field in form.find_all(['input', 'textarea', 'select']):
                field = {
                    'name': input_field.get('name', ''),
                    'type': input_field.get('type', 'text'),
                    'value': input_field.get('value', ''),
                    'required': input_field.has_attr('required')
                }
                form_data['fields'].append(field)
                
            forms.append(form_data)
            
        return forms
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from the page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            full_url = urljoin(base_url, link['href'])
            
            # Only include HTTP(S) links from same domain
            parsed = urlparse(full_url)
            base_parsed = urlparse(base_url)
            
            if (parsed.scheme in ['http', 'https'] and 
                parsed.netloc == base_parsed.netloc):
                links.append(full_url)
                
        return list(set(links))  # Remove duplicates
    
    def _extract_inputs(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract all input fields from the page"""
        inputs = []
        
        for input_field in soup.find_all(['input', 'textarea', 'select']):
            field = {
                'name': input_field.get('name', ''),
                'type': input_field.get('type', 'text'),
                'id': input_field.get('id', ''),
                'class': input_field.get('class', []),
                'placeholder': input_field.get('placeholder', ''),
                'value': input_field.get('value', '')
            }
            inputs.append(field)
            
        return inputs
    
    def _intelligent_crawl(self, state: CTFState, crawl_plan: Dict[str, Any]):
        """Perform intelligent crawling based on the plan"""
        discovery_techniques = crawl_plan.get('discovery_techniques', [])
        
        # Directory discovery
        if 'directory_bruteforce' in discovery_techniques:
            self._discover_directories(state)
        
        # Parameter discovery
        if 'parameter_discovery' in discovery_techniques:
            self._discover_parameters(state)
            
        # JavaScript analysis  
        if 'js_analysis' in discovery_techniques:
            self._analyze_javascript(state)
    
    def _discover_directories(self, state: CTFState):
        """Try to discover hidden directories"""
        base_url = state.challenge.url
        common_dirs = [
            '/admin', '/administrator', '/login', '/dashboard', '/panel',
            '/api', '/uploads', '/files', '/backup', '/config',
            '/test', '/dev', '/staging', '/debug', '/robots.txt',
            '/sitemap.xml', '/.git', '/.env', '/backup.sql'
        ]
        
        for directory in common_dirs:
            test_url = urljoin(base_url, directory)
            if test_url not in self.visited_urls:
                self._crawl_url(test_url, state, depth=1)
    
    def _discover_parameters(self, state: CTFState):
        """Try to discover hidden parameters"""
        # Analyze existing forms for parameter patterns
        common_params = ['id', 'user', 'file', 'path', 'url', 'cmd', 'page', 'debug']
        
        for page in state.crawled_pages:
            base_url = page.url
            
            # Test common parameters
            for param in common_params:
                test_url = f"{base_url}?{param}=test"
                if test_url not in self.visited_urls:
                    self._crawl_url(test_url, state, depth=1)
    
    def _analyze_javascript(self, state: CTFState):
        """Analyze JavaScript for API endpoints and functionality"""
        if not self.driver:
            return
            
        for page in state.crawled_pages:
            try:
                self.driver.get(page.url)
                
                # Extract JavaScript files
                scripts = self.driver.find_elements(By.TAG_NAME, "script")
                for script in scripts:
                    src = script.get_attribute("src")
                    if src and src not in self.visited_urls:
                        self._crawl_url(src, state, depth=1)
                        
            except Exception as e:
                logger.error(f"JavaScript analysis failed for {page.url}: {e}")
    
    def _analyze_crawled_content(self, state: CTFState) -> Dict[str, Any]:
        """Use LLM to analyze all crawled content"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
Analyze all crawled web content to identify:
1. Technology stack and frameworks used
2. Key endpoints and functionality  
3. Potential security issues or interesting findings
4. Attack surface areas
5. Data flow and application architecture

Focus on security-relevant information for CTF exploitation."""),
            ("human", """Analyze this crawled web application data:

Total pages crawled: {page_count}
Challenge context: {description}

Pages found:
{pages_summary}

Forms discovered:
{forms_summary}

Return a JSON analysis with:
- summary: Overall application analysis
- technologies: List of identified technologies
- endpoints: List of interesting endpoints
- security_notes: Potential security observations
- attack_surface: Key areas for security testing""")
        ])
        
        # Prepare summary data
        pages_summary = ""
        forms_summary = ""
        
        for i, page in enumerate(state.crawled_pages[:10]):  # Limit for context
            pages_summary += f"- {page.url}: {page.title} (Status: {page.status_code})\n"
            
        for page in state.crawled_pages:
            for form in page.forms:
                forms_summary += f"- {form['method']} {form['action']}: {len(form['fields'])} fields\n"
        
        try:
            response = self.llm.invoke(prompt.format(
                page_count=len(state.crawled_pages),
                description=state.challenge.description,
                pages_summary=pages_summary,
                forms_summary=forms_summary
            ))
            
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            import json
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Failed to analyze crawled content: {e}")
            return {
                "summary": f"Crawled {len(state.crawled_pages)} pages",
                "technologies": [],
                "endpoints": [],
                "security_notes": [],
                "attack_surface": []
            }