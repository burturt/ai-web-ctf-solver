"""
Threat modeling agent for identifying vulnerabilities and attack vectors
"""
from typing import Dict, Any, List
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
import json

from src.agents.base import BaseAgent
from src.models.state import CTFState, AgentType, Vulnerability
from src.utils.logging import get_logger

logger = get_logger(__name__)

class ThreatModelAgent(BaseAgent):
    """Agent responsible for threat modeling and vulnerability identification"""
    
    def __init__(self):
        super().__init__(AgentType.THREAT_MODEL)
        
    def _get_role_description(self) -> str:
        return """perform comprehensive threat modeling to identify security vulnerabilities,
        analyze attack surfaces, prioritize threats, and generate specific attack vectors for exploitation"""
    
    def execute(self, state: CTFState) -> CTFState:
        """Execute threat modeling process"""
        self.log_progress(state, "Starting threat modeling and vulnerability analysis", 0.1)
        
        try:
            # Generate threat model
            threat_model = self._generate_threat_model(state)
            self.log_progress(state, "Generated comprehensive threat model", 0.3)
            
            # Identify specific vulnerabilities
            vulnerabilities = self._identify_vulnerabilities(state, threat_model)
            for vuln in vulnerabilities:
                state.add_vulnerability(vuln)
            self.log_progress(state, f"Identified {len(vulnerabilities)} potential vulnerabilities", 0.6)
            
            # Analyze attack surface
            attack_surface = self._analyze_attack_surface(state)
            state.attack_surface = attack_surface
            self.log_progress(state, "Completed attack surface analysis", 0.8)
            
            # Generate exploitation plan
            exploitation_plan = self._generate_exploitation_plan(state)
            self._populate_fuzzing_queue(state, exploitation_plan)
            self.log_progress(state, f"Generated exploitation plan with {len(state.fuzzing_queue)} attack vectors", 0.9)
            
            self.log_progress(state, "Threat modeling completed successfully", 1.0)
            state.complete_agent(AgentType.THREAT_MODEL)
            
        except Exception as e:
            self.log_error(state, f"Threat modeling failed: {str(e)}")
        
        return state
    
    def _generate_threat_model(self, state: CTFState) -> Dict[str, Any]:
        """Generate comprehensive threat model using STRIDE methodology"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
Use STRIDE threat modeling methodology to analyze this web application:
- Spoofing: Identity verification weaknesses
- Tampering: Data integrity issues  
- Repudiation: Logging and audit trail gaps
- Information Disclosure: Data exposure risks
- Denial of Service: Availability threats
- Elevation of Privilege: Authorization bypass

Focus on web application vulnerabilities common in CTF challenges:
SQL injection, XSS, CSRF, authentication bypass, authorization flaws, 
file upload vulnerabilities, command injection, XXE, SSRF, etc."""),
            ("human", """Perform STRIDE threat modeling for this CTF web application:

Challenge: {title}
Description: {description}
URL: {url}
Flag Format: {flag_format}

Application Analysis:
{source_analysis}

Technology Stack: {technologies}
Crawled Pages: {page_count}
Forms Found: {forms_summary}

Generate a comprehensive threat model covering:
1. Asset identification (what needs protection)
2. Threat analysis using STRIDE
3. Attack surface mapping
4. Vulnerability assessment  
5. Risk prioritization
6. Specific attack scenarios for CTF exploitation

Return detailed analysis focusing on exploitable vulnerabilities.""")
        ])
        
        # Prepare forms summary
        forms_summary = []
        for page in state.crawled_pages:
            for form in page.forms:
                form_desc = f"{form['method']} {form['action']}"
                fields = [f['name'] for f in form['fields'] if f['name']]
                if fields:
                    form_desc += f" (fields: {', '.join(fields)})"
                forms_summary.append(form_desc)
        
        try:
            response = self.llm.invoke(prompt.format(
                title=state.challenge.title,
                description=state.challenge.description,
                url=state.challenge.url,
                flag_format=state.challenge.flag_format,
                source_analysis=state.source_analysis or "No source analysis available",
                technologies=", ".join(state.technology_stack) or "Unknown",
                page_count=len(state.crawled_pages),
                forms_summary="\n".join(forms_summary) or "No forms found"
            ))
            
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            return {"threat_model": content}
            
        except Exception as e:
            logger.error(f"Threat model generation failed: {e}")
            return {"threat_model": f"Threat model generation failed: {str(e)}"}
    
    def _identify_vulnerabilities(self, state: CTFState, threat_model: Dict[str, Any]) -> List[Vulnerability]:
        """Identify specific exploitable vulnerabilities"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
Based on the threat model and application analysis, identify specific, exploitable 
vulnerabilities. For each vulnerability, provide:
1. Vulnerability type (SQL injection, XSS, auth bypass, etc.)
2. Exact location (URL, parameter, form field)
3. Detailed description of the vulnerability
4. Confidence level (0.0 to 1.0)
5. Potential attack vectors
6. Suggested payloads for exploitation

Focus on vulnerabilities that are actually exploitable in this specific application."""),
            ("human", """Identify specific vulnerabilities from this analysis:

Threat Model:
{threat_model}

Application Details:
- Pages: {page_details}
- Forms: {form_details}
- Technology: {technologies}

Return a JSON array of vulnerability objects with:
- vulnerability_type: string
- location: string (URL/endpoint where vuln exists)
- description: string
- confidence: float (0.0 to 1.0)
- attack_vectors: array of strings
- payload_suggestions: array of strings

Focus on high-confidence, exploitable vulnerabilities.""")
        ])
        
        # Prepare detailed page and form information
        page_details = []
        form_details = []
        
        for page in state.crawled_pages[:10]:  # Limit for context
            page_info = f"{page.url} (Status: {page.status_code}, Title: {page.title})"
            if page.inputs:
                input_names = [inp['name'] for inp in page.inputs if inp.get('name')]
                if input_names:
                    page_info += f" - Inputs: {', '.join(input_names)}"
            page_details.append(page_info)
        
        for page in state.crawled_pages:
            for form in page.forms:
                form_info = f"{form['method']} {form['action']}"
                field_info = []
                for field in form['fields']:
                    if field['name']:
                        field_info.append(f"{field['name']} ({field['type']})")
                if field_info:
                    form_info += f" - Fields: {', '.join(field_info)}"
                form_details.append(form_info)
        
        try:
            response = self.llm.invoke(prompt.format(
                threat_model=threat_model.get("threat_model", ""),
                page_details="\n".join(page_details),
                form_details="\n".join(form_details),
                technologies=", ".join(state.technology_stack) or "Unknown"
            ))
            
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            # Parse JSON response
            try:
                # Clean the content - sometimes LLMs add markdown formatting
                clean_content = content.strip()
                if clean_content.startswith('```json'):
                    clean_content = clean_content.split('\n', 1)[1]
                if clean_content.endswith('```'):
                    clean_content = clean_content.rsplit('\n', 1)[0]
                
                vulnerabilities_data = json.loads(clean_content)
                
                # Handle case where response is not a list
                if not isinstance(vulnerabilities_data, list):
                    if isinstance(vulnerabilities_data, dict) and 'vulnerabilities' in vulnerabilities_data:
                        vulnerabilities_data = vulnerabilities_data['vulnerabilities']
                    else:
                        vulnerabilities_data = []
                        
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                logger.warning(f"Response content: {content[:200]}...")
                vulnerabilities_data = []
            
            vulnerabilities = []
            for vuln_data in vulnerabilities_data:
                vuln = Vulnerability(
                    vulnerability_type=vuln_data.get("vulnerability_type", "unknown"),
                    location=vuln_data.get("location", "unknown"),
                    description=vuln_data.get("description", ""),
                    confidence=float(vuln_data.get("confidence", 0.5)),
                    attack_vectors=vuln_data.get("attack_vectors", []),
                    payload_suggestions=vuln_data.get("payload_suggestions", [])
                )
                vulnerabilities.append(vuln)
            
            return vulnerabilities
            
        except Exception as e:
            logger.error(f"Vulnerability identification failed: {e}")
            # Return some default vulnerabilities based on common CTF patterns
            return self._get_default_vulnerabilities(state)
    
    def _get_default_vulnerabilities(self, state: CTFState) -> List[Vulnerability]:
        """Get default vulnerabilities based on common CTF patterns"""
        default_vulnerabilities = []
        
        # Check for forms (potential SQL injection)
        for page in state.crawled_pages:
            for form in page.forms:
                if any(field['name'] in ['username', 'password', 'login', 'id'] for field in form['fields']):
                    vuln = Vulnerability(
                        vulnerability_type="sql_injection",
                        location=form['action'],
                        description="Form with authentication fields - potential SQL injection",
                        confidence=0.7,
                        attack_vectors=["sql_injection_auth_bypass"],
                        payload_suggestions=["admin' OR '1'='1", "' OR 1=1 --", "admin' --"]
                    )
                    default_vulnerabilities.append(vuln)
        
        # Check for file upload functionality
        for page in state.crawled_pages:
            if any(inp.get('type') == 'file' for inp in page.inputs):
                vuln = Vulnerability(
                    vulnerability_type="file_upload",
                    location=page.url,
                    description="File upload functionality detected",
                    confidence=0.6,
                    attack_vectors=["malicious_file_upload"],
                    payload_suggestions=["shell.php", "webshell.jsp"]
                )
                default_vulnerabilities.append(vuln)
        
        return default_vulnerabilities
    
    def _analyze_attack_surface(self, state: CTFState) -> Dict[str, Any]:
        """Analyze the application's attack surface"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
Analyze the attack surface of this web application. Consider:
1. Entry points (forms, parameters, file uploads, APIs)
2. Authentication mechanisms
3. Session management
4. Input validation points
5. Output encoding
6. Access controls
7. External integrations

Provide a structured analysis of the attack surface."""),
            ("human", """Analyze the attack surface for this application:

Vulnerabilities Identified: {vuln_count}
Forms: {form_count}
Pages: {page_count}
Endpoints: {endpoints}

Application Analysis:
{source_analysis}

Return JSON with attack surface analysis including:
- entry_points: Array of potential entry points
- authentication: Analysis of auth mechanisms  
- session_management: Session handling analysis
- input_validation: Input validation assessment
- high_risk_areas: Priority areas for testing
- attack_complexity: Overall complexity assessment""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format(
                vuln_count=len(state.vulnerabilities),
                form_count=sum(len(page.forms) for page in state.crawled_pages),
                page_count=len(state.crawled_pages),
                endpoints=", ".join(state.identified_endpoints),
                source_analysis=state.source_analysis or "No analysis available"
            ))
            
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Attack surface analysis failed: {e}")
            return {
                "entry_points": ["web_forms", "url_parameters"],
                "authentication": "unknown", 
                "session_management": "unknown",
                "input_validation": "unknown",
                "high_risk_areas": ["forms"],
                "attack_complexity": "medium"
            }
    
    def _generate_exploitation_plan(self, state: CTFState) -> Dict[str, Any]:
        """Generate a structured exploitation plan"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
Generate a detailed exploitation plan for this CTF challenge. Prioritize attack vectors
by likelihood of success and potential to find the flag. Consider:

1. Vulnerability severity and exploitability
2. Common CTF patterns and techniques
3. Application-specific weaknesses
4. Payload effectiveness
5. Testing methodology

Create a systematic approach for automated exploitation."""),
            ("human", """Generate exploitation plan for this CTF challenge:

Challenge: {title}
Flag Format: {flag_format}

Identified Vulnerabilities:
{vulnerabilities}

Attack Surface:
{attack_surface}

Create a JSON exploitation plan with:
- priority_order: Array of vulnerability types in priority order
- attack_vectors: Detailed attack vector definitions
- payloads: Specific payloads mapped to vulnerabilities
- testing_sequence: Step-by-step testing approach
- success_indicators: How to identify successful exploitation
- flag_extraction: Likely flag locations and extraction methods

Focus on automated exploitation suitable for this CTF.""")
        ])
        
        # Prepare vulnerability summary
        vuln_summary = []
        for vuln in state.vulnerabilities:
            vuln_info = f"- {vuln.vulnerability_type} at {vuln.location} (confidence: {vuln.confidence})"
            vuln_info += f"\n  Vectors: {', '.join(vuln.attack_vectors)}"
            vuln_summary.append(vuln_info)
        
        try:
            response = self.llm.invoke(prompt.format(
                title=state.challenge.title,
                flag_format=state.challenge.flag_format,
                vulnerabilities="\n".join(vuln_summary),
                attack_surface=json.dumps(state.attack_surface, indent=2)
            ))
            
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Exploitation plan generation failed: {e}")
            return self._get_default_exploitation_plan(state)
    
    def _get_default_exploitation_plan(self, state: CTFState) -> Dict[str, Any]:
        """Generate a default exploitation plan"""
        return {
            "priority_order": ["sql_injection", "authentication_bypass", "file_upload", "xss"],
            "attack_vectors": {
                "sql_injection": "Test all input fields for SQL injection",
                "authentication_bypass": "Attempt to bypass authentication mechanisms",
                "file_upload": "Upload malicious files if upload functionality exists",
                "xss": "Test for cross-site scripting vulnerabilities"
            },
            "payloads": {
                "sql_injection": ["' OR '1'='1", "admin' --", "' UNION SELECT null--"],
                "auth_bypass": ["admin/admin", "admin/password", "guest/guest"]
            },
            "testing_sequence": [
                "test_sql_injection_in_forms",
                "test_authentication_bypass", 
                "test_file_upload_vulnerabilities",
                "test_xss_in_input_fields"
            ],
            "success_indicators": ["flag pattern match", "successful authentication", "file execution"],
            "flag_extraction": ["check_response_content", "check_uploaded_files", "check_database_output"]
        }
    
    def _populate_fuzzing_queue(self, state: CTFState, exploitation_plan: Dict[str, Any]):
        """Populate the fuzzing queue based on exploitation plan"""
        attack_vectors = exploitation_plan.get("attack_vectors", {})
        payloads = exploitation_plan.get("payloads", {})
        testing_sequence = exploitation_plan.get("testing_sequence", [])
        
        # Generate fuzzing tasks based on vulnerabilities and attack plan
        for vuln in state.vulnerabilities:
            for attack_vector in vuln.attack_vectors:
                for payload in vuln.payload_suggestions:
                    fuzz_task = {
                        "vulnerability_type": vuln.vulnerability_type,
                        "location": vuln.location,
                        "attack_vector": attack_vector,
                        "payload": payload,
                        "confidence": vuln.confidence,
                        "method": self._determine_http_method(vuln.location, state),
                        "parameters": self._extract_parameters(vuln.location, state)
                    }
                    state.fuzzing_queue.append(fuzz_task)
        
        # Add generic testing based on discovered forms
        for page in state.crawled_pages:
            for form in page.forms:
                for field in form['fields']:
                    if field['name']:
                        # Add SQL injection tests
                        for payload in payloads.get("sql_injection", []):
                            fuzz_task = {
                                "vulnerability_type": "sql_injection",
                                "location": form['action'],
                                "attack_vector": "form_sql_injection",
                                "payload": payload,
                                "confidence": 0.5,
                                "method": form['method'],
                                "parameters": {field['name']: payload}
                            }
                            state.fuzzing_queue.append(fuzz_task)
        
        # Sort fuzzing queue by confidence (highest first)
        state.fuzzing_queue.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    def _determine_http_method(self, location: str, state: CTFState) -> str:
        """Determine the HTTP method for a given location"""
        # Check if location matches any forms
        for page in state.crawled_pages:
            for form in page.forms:
                if form['action'] == location:
                    return form['method']
        
        return "GET"  # Default to GET
    
    def _extract_parameters(self, location: str, state: CTFState) -> Dict[str, str]:
        """Extract parameters for a given location"""
        # Check forms for parameters
        for page in state.crawled_pages:
            for form in page.forms:
                if form['action'] == location:
                    params = {}
                    for field in form['fields']:
                        if field['name']:
                            params[field['name']] = field.get('value', '')
                    return params
        
        return {}