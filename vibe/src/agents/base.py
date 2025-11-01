"""
Base agent class for CTF solving agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models.base import BaseLanguageModel as LLM
else:
    try:
        from langchain_core.language_models.base import BaseLanguageModel as LLM
    except ImportError:
        # Fallback for compatibility
        LLM = object

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic

from src.models.state import CTFState, AgentType
from src.utils.logging import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)

class BaseAgent(ABC):
    """Base class for all CTF solving agents"""
    
    def __init__(self, agent_type: AgentType, model_name: str = None):
        self.agent_type = agent_type
        self.config = get_config()
        
        # Initialize LLM
        model_name = model_name or self.config.get("DEFAULT_MODEL", "gpt-4-turbo-preview")
        self.llm = self._initialize_llm(model_name)
        
    def _initialize_llm(self, model_name: str) -> LLM:
        """Initialize the LLM based on model name"""
        # Check if using Azure OpenAI
        if self.config.get("USE_AZURE_OPENAI", False):
            return AzureChatOpenAI(
                azure_endpoint=self.config.get("AZURE_OPENAI_ENDPOINT"),
                api_key=self.config.get("AZURE_OPENAI_API_KEY"),
                api_version=self.config.get("AZURE_OPENAI_API_VERSION"),
                deployment_name=self.config.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
                temperature=float(self.config.get("TEMPERATURE", 0.7)),
                max_tokens=int(self.config.get("MAX_TOKENS", 4096))
            )
        elif model_name.startswith("gpt"):
            return ChatOpenAI(
                model=model_name,
                temperature=float(self.config.get("TEMPERATURE", 0.7)),
                max_tokens=int(self.config.get("MAX_TOKENS", 4096))
            )
        elif model_name.startswith("claude"):
            return ChatAnthropic(
                model=model_name,
                temperature=float(self.config.get("TEMPERATURE", 0.7)),
                max_tokens=int(self.config.get("MAX_TOKENS", 4096))
            )
        else:
            raise ValueError(f"Unsupported model: {model_name}")
    
    @abstractmethod
    def execute(self, state: CTFState) -> CTFState:
        """
        Execute the agent's main functionality
        
        Args:
            state: Current CTF state
            
        Returns:
            Updated CTF state
        """
        pass
    
    def log_progress(self, state: CTFState, message: str, progress: float = None):
        """Log agent progress"""
        agent_state = state.agent_states[self.agent_type]
        agent_state.add_message(message)
        
        if progress is not None:
            agent_state.progress = progress
            
        logger.info(f"[{self.agent_type.value}] {message}")
    
    def log_error(self, state: CTFState, error: str):
        """Log agent error"""
        agent_state = state.agent_states[self.agent_type]
        agent_state.add_error(error)
        logger.error(f"[{self.agent_type.value}] {error}")
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        return f"""You are a specialized {self.agent_type.value} agent for solving web CTF challenges.
        
Your role is to {self._get_role_description()}.

Key guidelines:
- Be systematic and thorough in your approach
- Document all findings and actions taken
- Focus on security vulnerabilities and exploitation techniques
- Always consider the challenge context and flag format
- Prioritize high-confidence vulnerabilities
- Be creative but methodical in your exploration
"""
    
    @abstractmethod
    def _get_role_description(self) -> str:
        """Get a description of this agent's role"""
        pass