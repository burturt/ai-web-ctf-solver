"""
State management for the LangGraph CTF solver workflow
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from enum import Enum

from src.models.challenge import Challenge, ExploitAttempt, CTFSubmission

class AgentType(Enum):
    """Types of agents in the workflow"""
    CRAWLER = "crawler"
    SUMMARIZER = "summarizer" 
    THREAT_MODEL = "threat_model"
    FUZZER = "fuzzer"
    COORDINATOR = "coordinator"

class WorkflowStatus(Enum):
    """Overall workflow status"""
    INITIALIZING = "initializing"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    MODELING_THREATS = "modeling_threats"
    FUZZING = "fuzzing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class CrawledPage:
    """Information about a crawled web page"""
    url: str
    title: str = ""
    content: str = ""
    forms: List[Dict[str, Any]] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    status_code: int = 200
    response_time: float = 0.0

@dataclass
class Vulnerability:
    """Identified vulnerability information"""
    vulnerability_type: str
    location: str
    description: str
    confidence: float  # 0.0 to 1.0
    attack_vectors: List[str] = field(default_factory=list)
    payload_suggestions: List[str] = field(default_factory=list)
    
@dataclass
class AgentState:
    """State for individual agents"""
    agent_type: AgentType
    status: str = "ready"
    current_task: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: str):
        """Add a status message"""
        self.messages.append(f"[{datetime.now().isoformat()}] {message}")
        self.last_updated = datetime.now()
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")
        self.last_updated = datetime.now()

@dataclass
class CTFState:
    """
    Complete state for the CTF solving workflow.
    This is the main state object that gets passed between LangGraph nodes.
    """
    # Core challenge information
    challenge: Challenge
    submission: CTFSubmission
    
    # Workflow management
    workflow_status: WorkflowStatus = WorkflowStatus.INITIALIZING
    current_agent: Optional[AgentType] = None
    completed_agents: Set[AgentType] = field(default_factory=set)
    
    # Agent states
    agent_states: Dict[AgentType, AgentState] = field(default_factory=dict)
    
    # Crawling results
    crawled_pages: List[CrawledPage] = field(default_factory=list)
    site_map: Dict[str, List[str]] = field(default_factory=dict)  # URL -> linked URLs
    
    # Analysis results
    source_analysis: Optional[str] = None
    technology_stack: List[str] = field(default_factory=list)
    identified_endpoints: List[str] = field(default_factory=list)
    
    # Threat modeling results
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    attack_surface: Dict[str, Any] = field(default_factory=dict)
    
    # Fuzzing state
    fuzzing_queue: List[Dict[str, Any]] = field(default_factory=list)
    attempted_payloads: Set[str] = field(default_factory=set)
    
    # Results
    flags_found: List[str] = field(default_factory=list)
    successful_exploits: List[ExploitAttempt] = field(default_factory=list)
    
    # Metadata
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize agent states if not provided"""
        if not self.agent_states:
            for agent_type in AgentType:
                self.agent_states[agent_type] = AgentState(agent_type=agent_type)
        
        # Initialize submission if not provided
        if not hasattr(self, 'submission') or self.submission is None:
            self.submission = CTFSubmission(challenge=self.challenge)
    
    def set_current_agent(self, agent_type: AgentType):
        """Set the currently active agent"""
        self.current_agent = agent_type
        self.agent_states[agent_type].status = "active"
        self.agent_states[agent_type].last_updated = datetime.now()
    
    def complete_agent(self, agent_type: AgentType):
        """Mark an agent as completed"""
        self.completed_agents.add(agent_type)
        self.agent_states[agent_type].status = "completed"
        self.agent_states[agent_type].progress = 1.0
        self.agent_states[agent_type].last_updated = datetime.now()
    
    def add_crawled_page(self, page: CrawledPage):
        """Add a crawled page to the state"""
        self.crawled_pages.append(page)
        # Update site map
        if page.url not in self.site_map:
            self.site_map[page.url] = page.links
    
    def add_vulnerability(self, vulnerability: Vulnerability):
        """Add an identified vulnerability"""
        self.vulnerabilities.append(vulnerability)
    
    def add_exploit_attempt(self, attempt: ExploitAttempt):
        """Add an exploitation attempt"""
        self.submission.add_exploit_attempt(attempt)
        if attempt.flag_found:
            self.flags_found.append(attempt.flag_found)
            self.successful_exploits.append(attempt)
    
    def is_complete(self) -> bool:
        """Check if the workflow is complete"""
        return (self.workflow_status == WorkflowStatus.COMPLETED or 
                self.workflow_status == WorkflowStatus.FAILED or
                len(self.flags_found) > 0)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state"""
        return {
            "challenge_id": self.challenge.id,
            "challenge_url": self.challenge.url,
            "workflow_status": self.workflow_status.value,
            "current_agent": self.current_agent.value if self.current_agent else None,
            "completed_agents": [agent.value for agent in self.completed_agents],
            "pages_crawled": len(self.crawled_pages),
            "vulnerabilities_found": len(self.vulnerabilities),
            "exploit_attempts": len(self.submission.exploit_attempts),
            "flags_found": len(self.flags_found),
            "success": self.submission.success,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds()
        }