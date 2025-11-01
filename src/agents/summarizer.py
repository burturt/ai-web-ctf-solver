"""
Summarizer agent for analyzing source code and web content
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

from src.agents.base import BaseAgent
from src.models.state import CTFState, AgentType
from src.utils.logging import get_logger

logger = get_logger(__name__)

class SummarizerAgent(BaseAgent):
    """Agent responsible for analyzing and summarizing crawled content and source code"""
    
    def __init__(self):
        super().__init__(AgentType.SUMMARIZER)
        
    def _get_role_description(self) -> str:
        return """analyze source code and web content to understand application architecture, 
        identify technology stacks, map data flows, and summarize security-relevant information for exploitation"""
    
    def execute(self, state: CTFState) -> CTFState:
        """Execute the summarization and analysis process"""
        self.log_progress(state, "Starting content analysis and summarization", 0.1)
        
        try:
            # Analyze source code if provided
            if state.challenge.source_code:
                source_analysis = self._analyze_source_code(state)
                state.source_analysis = source_analysis
                self.log_progress(state, "Source code analysis completed", 0.4)
            
            # Analyze crawled web content
            web_analysis = self._analyze_web_content(state)
            self._update_state_with_web_analysis(state, web_analysis)
            self.log_progress(state, "Web content analysis completed", 0.7)
            
            # Generate comprehensive summary
            comprehensive_summary = self._generate_comprehensive_summary(state)
            state.source_analysis = comprehensive_summary
            self.log_progress(state, "Comprehensive analysis completed", 0.9)
            
            # Extract technology stack and endpoints
            tech_analysis = self._extract_technology_info(state)
            state.technology_stack.extend(tech_analysis.get("technologies", []))
            state.identified_endpoints.extend(tech_analysis.get("endpoints", []))
            
            self.log_progress(state, "Summarization completed successfully", 1.0)
            state.complete_agent(AgentType.SUMMARIZER)
            
        except Exception as e:
            self.log_error(state, f"Summarization failed: {str(e)}")
        
        return state
    
    def _analyze_source_code(self, state: CTFState) -> str:
        """Analyze provided source code for security insights"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
You are analyzing source code for a web CTF challenge. Focus on:
1. Identifying potential vulnerabilities (SQL injection, XSS, auth bypass, etc.)
2. Understanding the application logic and data flow
3. Finding hidden functionality or debug features  
4. Identifying input validation issues
5. Understanding authentication and authorization mechanisms
6. Spotting insecure configurations or hardcoded secrets

Provide a detailed technical analysis that will help with exploitation."""),
            ("human", """Analyze this source code for security vulnerabilities and exploitation opportunities:

Challenge Description: {description}
Flag Format: {flag_format}

Source Code:
{source_code}

Provide a comprehensive analysis including:
- Key vulnerabilities identified
- Application architecture and data flow
- Potential attack vectors
- Interesting functions or endpoints
- Security mechanisms in place
- Exploitation recommendations""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format(
                description=state.challenge.description,
                flag_format=state.challenge.flag_format,
                source_code=state.challenge.source_code
            ))
            
            if isinstance(response, BaseMessage):
                return response.content
            return str(response)
            
        except Exception as e:
            logger.error(f"Source code analysis failed: {e}")
            return f"Source code analysis failed: {str(e)}"
    
    def _analyze_web_content(self, state: CTFState) -> Dict[str, Any]:
        """Analyze all crawled web content"""
        if not state.crawled_pages:
            return {"summary": "No web content to analyze"}
        
        # Prepare content summary
        content_summary = self._prepare_content_summary(state)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
Analyze crawled web application content for security testing. Focus on:
1. Form analysis and parameter identification
2. Authentication and session management
3. File upload capabilities
4. Admin or debug interfaces
5. API endpoints and AJAX calls
6. Client-side security controls
7. Information disclosure in HTML comments or JavaScript

Provide actionable intelligence for security testing."""),
            ("human", """Analyze this crawled web application:

Challenge Context: {description}
Pages Crawled: {page_count}
Forms Found: {form_count}

Content Summary:
{content_summary}

Provide analysis covering:
- Application functionality and user flows
- Security-relevant features and controls
- Potential attack surfaces
- Interesting parameters and endpoints
- Technology stack identification
- Security weaknesses observed""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format(
                description=state.challenge.description,
                page_count=len(state.crawled_pages),
                form_count=sum(len(page.forms) for page in state.crawled_pages),
                content_summary=content_summary
            ))
            
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            return {"analysis": content}
            
        except Exception as e:
            logger.error(f"Web content analysis failed: {e}")
            return {"analysis": f"Web content analysis failed: {str(e)}"}
    
    def _prepare_content_summary(self, state: CTFState) -> str:
        """Prepare a summary of crawled content for LLM analysis"""
        summary = []
        
        for page in state.crawled_pages:
            page_info = f"URL: {page.url}\n"
            page_info += f"Title: {page.title}\n"
            page_info += f"Status: {page.status_code}\n"
            
            if page.forms:
                page_info += f"Forms ({len(page.forms)}):\n"
                for form in page.forms:
                    page_info += f"  - {form['method']} {form['action']}: {len(form['fields'])} fields\n"
                    # Include interesting field names
                    field_names = [f['name'] for f in form['fields'] if f['name']]
                    if field_names:
                        page_info += f"    Fields: {', '.join(field_names)}\n"
            
            if page.inputs:
                interesting_inputs = [inp for inp in page.inputs if inp.get('name')]
                if interesting_inputs:
                    input_names = [inp['name'] for inp in interesting_inputs]
                    page_info += f"Inputs: {', '.join(input_names)}\n"
            
            # Extract interesting content snippets
            content_snippets = self._extract_interesting_content(page.content)
            if content_snippets:
                page_info += f"Interesting content: {content_snippets}\n"
            
            summary.append(page_info)
        
        return "\n---\n".join(summary)
    
    def _extract_interesting_content(self, content: str) -> str:
        """Extract interesting snippets from page content"""
        interesting_patterns = [
            "admin", "login", "password", "token", "api", "debug", 
            "flag", "secret", "key", "config", "database", "sql",
            "upload", "file", "command", "exec", "eval"
        ]
        
        lines = content.lower().split('\n')
        interesting_lines = []
        
        for line in lines:
            if any(pattern in line for pattern in interesting_patterns):
                # Limit line length and add to results
                clean_line = line.strip()[:100]
                if clean_line and clean_line not in interesting_lines:
                    interesting_lines.append(clean_line)
                    
                # Limit number of interesting lines
                if len(interesting_lines) >= 5:
                    break
        
        return "; ".join(interesting_lines)
    
    def _update_state_with_web_analysis(self, state: CTFState, analysis: Dict[str, Any]):
        """Update state with web analysis results"""
        analysis_text = analysis.get("analysis", "")
        
        # Append to existing source analysis
        if state.source_analysis:
            state.source_analysis += f"\n\n--- Web Content Analysis ---\n{analysis_text}"
        else:
            state.source_analysis = analysis_text
    
    def _generate_comprehensive_summary(self, state: CTFState) -> str:
        """Generate a comprehensive summary combining all analysis"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt() + """
            
Create a comprehensive security assessment summary that consolidates all available information
about this web application. This summary will be used by threat modeling and exploitation agents.

Focus on creating actionable intelligence for security testing."""),
            ("human", """Create a comprehensive security assessment summary:

Challenge: {title}
Description: {description}  
Flag Format: {flag_format}
URL: {url}

Source Code Analysis:
{source_analysis}

Technology Stack: {technologies}
Identified Endpoints: {endpoints}
Pages Crawled: {page_count}

Create a consolidated summary including:
1. Application overview and architecture
2. Key security-relevant functionality  
3. Potential vulnerability areas
4. Attack surface assessment
5. Recommended testing approaches
6. Priority targets for exploitation

Make this actionable for security testing.""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format(
                title=state.challenge.title,
                description=state.challenge.description,
                flag_format=state.challenge.flag_format,
                url=state.challenge.url,
                source_analysis=state.source_analysis or "None provided",
                technologies=", ".join(state.technology_stack) or "Not identified",
                endpoints=", ".join(state.identified_endpoints) or "None identified", 
                page_count=len(state.crawled_pages)
            ))
            
            if isinstance(response, BaseMessage):
                return response.content
            return str(response)
            
        except Exception as e:
            logger.error(f"Comprehensive summary generation failed: {e}")
            return f"Summary generation failed: {str(e)}"
    
    def _extract_technology_info(self, state: CTFState) -> Dict[str, List[str]]:
        """Extract structured technology and endpoint information"""
        if not state.source_analysis:
            return {"technologies": [], "endpoints": []}
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract structured information from this security analysis."),
            ("human", """From this analysis, extract:

{analysis}

Return a JSON object with:
- technologies: Array of identified technologies/frameworks
- endpoints: Array of interesting URLs/endpoints found

Focus on concrete, actionable items.""")
        ])
        
        try:
            response = self.llm.invoke(prompt.format(analysis=state.source_analysis))
            
            if isinstance(response, BaseMessage):
                content = response.content
            else:
                content = str(response)
            
            import json
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Technology extraction failed: {e}")
            return {"technologies": [], "endpoints": []}