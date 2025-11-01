"""
LangGraph workflow definition for the CTF solver multi-agent system
"""
from typing import Dict, Any, List
try:
    from langgraph.graph import StateGraph, END, START
    LANGGRAPH_AVAILABLE = True
    
    # Try to import SqliteSaver, create fallback if not available
    try:
        checkpoint_module = __import__('langgraph.checkpoint.sqlite', fromlist=['SqliteSaver'])
        SqliteSaver = checkpoint_module.SqliteSaver
    except ImportError:
        class SqliteSaver:
            @classmethod
            def from_conn_string(cls, conn_string):
                return cls()
except ImportError:
    # Fallback implementations
    LANGGRAPH_AVAILABLE = False
    
    class StateGraph:
        def __init__(self, state_class):
            self.state_class = state_class
            self.nodes = {}
            self.edges = {}
        
        def add_node(self, name, func):
            self.nodes[name] = func
        
        def add_edge(self, from_node, to_node):
            if from_node not in self.edges:
                self.edges[from_node] = []
            self.edges[from_node].append(to_node)
        
        def add_conditional_edges(self, from_node, condition, mapping):
            pass
        
        def set_entry_point(self, node):
            self.entry_point = node
        
        def compile(self, **kwargs):
            return MockCompiledGraph()
    
    END = "END"
    START = "START"
    
    class SqliteSaver:
        @classmethod
        def from_conn_string(cls, conn_string):
            return cls()
    
    class MockCompiledGraph:
        async def astream(self, state, config=None):
            yield state

from src.models.state import CTFState, AgentType, WorkflowStatus
from src.agents.crawler import CrawlerAgent
from src.agents.summarizer import SummarizerAgent  
from src.agents.threat_model import ThreatModelAgent
from src.agents.fuzzer import FuzzerAgent
from src.utils.logging import get_logger

logger = get_logger(__name__)

class CTFSolverGraph:
    """
    LangGraph-based workflow for CTF solving using multiple specialized agents.
    
    The workflow follows this sequence:
    1. START -> Crawler Agent (map the web application)
    2. Crawler -> Summarizer Agent (analyze content and source code)  
    3. Summarizer -> Threat Model Agent (identify vulnerabilities)
    4. Threat Model -> Fuzzer Agent (exploit vulnerabilities)
    5. Fuzzer -> END (when flag found or max attempts reached)
    
    Each agent can loop back to itself for iterative processing.
    """
    
    def __init__(self):
        self.graph = None
        # Try to initialize checkpointer, fall back to None if it fails
        try:
            checkpointer_candidate = SqliteSaver.from_conn_string(":memory:")
            # Check if the checkpointer has the required methods
            if hasattr(checkpointer_candidate, 'get_next_version'):
                self.checkpointer = checkpointer_candidate
                logger.info("SqliteSaver checkpointer initialized successfully")
            else:
                logger.warning("SqliteSaver missing required methods - incompatible version")
                logger.info("Continuing without checkpointer - workflow state will not be persisted")
                self.checkpointer = None
        except Exception as e:
            logger.warning(f"Failed to initialize SqliteSaver checkpointer: {e}")
            logger.info("Continuing without checkpointer - workflow state will not be persisted")
            self.checkpointer = None
        
        self.agents = {
            AgentType.CRAWLER: CrawlerAgent(),
            AgentType.SUMMARIZER: SummarizerAgent(),
            AgentType.THREAT_MODEL: ThreatModelAgent(), 
            AgentType.FUZZER: FuzzerAgent()
        }
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        # Create the state graph
        workflow = StateGraph(CTFState)
        
        # Add nodes for each agent
        workflow.add_node("crawler", self._crawler_node)
        workflow.add_node("summarizer", self._summarizer_node)  
        workflow.add_node("threat_model", self._threat_model_node)
        workflow.add_node("fuzzer", self._fuzzer_node)
        workflow.add_node("coordinator", self._coordinator_node)
        
        # Define the workflow edges
        workflow.set_entry_point("crawler")
        
        # Crawler can go to summarizer or loop back to itself
        workflow.add_conditional_edges(
            "crawler",
            self._should_continue_crawling,
            {
                "continue": "crawler",
                "analyze": "summarizer"
            }
        )
        
        # Summarizer goes to threat modeling
        workflow.add_edge("summarizer", "threat_model")
        
        # Threat model can loop back to itself or go to fuzzer
        workflow.add_conditional_edges(
            "threat_model", 
            self._should_continue_threat_modeling,
            {
                "continue": "threat_model",
                "fuzz": "fuzzer"
            }
        )
        
        # Fuzzer can loop back or end
        workflow.add_conditional_edges(
            "fuzzer",
            self._should_continue_fuzzing,
            {
                "continue": "fuzzer", 
                "coordinate": "coordinator",
                "end": END
            }
        )
        
        # Coordinator decides next steps or ends
        workflow.add_conditional_edges(
            "coordinator",
            self._coordinator_decision,
            {
                "crawler": "crawler",
                "threat_model": "threat_model", 
                "fuzzer": "fuzzer",
                "end": END
            }
        )
        
        # Compile the graph
        if self.checkpointer:
            self.graph = workflow.compile(checkpointer=self.checkpointer)
        else:
            self.graph = workflow.compile()
            logger.info("Graph compiled without checkpointer")
        
    def _crawler_node(self, state: CTFState) -> CTFState:
        """Execute crawler agent"""
        logger.info(f"Executing crawler agent for challenge {state.challenge.id}")
        state.set_current_agent(AgentType.CRAWLER)
        state.workflow_status = WorkflowStatus.CRAWLING
        
        try:
            # Execute crawler agent
            updated_state = self.agents[AgentType.CRAWLER].execute(state)
            updated_state.agent_states[AgentType.CRAWLER].add_message("Crawling completed successfully")
            return updated_state
            
        except Exception as e:
            logger.error(f"Crawler agent failed: {str(e)}")
            state.agent_states[AgentType.CRAWLER].add_error(f"Crawler failed: {str(e)}")
            return state
    
    def _summarizer_node(self, state: CTFState) -> CTFState:
        """Execute summarizer agent"""
        logger.info(f"Executing summarizer agent for challenge {state.challenge.id}")
        state.set_current_agent(AgentType.SUMMARIZER)
        state.workflow_status = WorkflowStatus.ANALYZING
        
        try:
            updated_state = self.agents[AgentType.SUMMARIZER].execute(state)
            updated_state.agent_states[AgentType.SUMMARIZER].add_message("Analysis completed successfully")
            return updated_state
            
        except Exception as e:
            logger.error(f"Summarizer agent failed: {str(e)}")
            state.agent_states[AgentType.SUMMARIZER].add_error(f"Analysis failed: {str(e)}")
            return state
    
    def _threat_model_node(self, state: CTFState) -> CTFState:
        """Execute threat modeling agent"""
        logger.info(f"Executing threat model agent for challenge {state.challenge.id}")
        state.set_current_agent(AgentType.THREAT_MODEL)
        state.workflow_status = WorkflowStatus.MODELING_THREATS
        
        try:
            updated_state = self.agents[AgentType.THREAT_MODEL].execute(state)
            updated_state.agent_states[AgentType.THREAT_MODEL].add_message("Threat modeling completed successfully")
            return updated_state
            
        except Exception as e:
            logger.error(f"Threat model agent failed: {str(e)}")
            state.agent_states[AgentType.THREAT_MODEL].add_error(f"Threat modeling failed: {str(e)}")
            return state
    
    def _fuzzer_node(self, state: CTFState) -> CTFState:
        """Execute fuzzer agent"""
        logger.info(f"Executing fuzzer agent for challenge {state.challenge.id}")
        state.set_current_agent(AgentType.FUZZER)
        state.workflow_status = WorkflowStatus.FUZZING
        
        try:
            updated_state = self.agents[AgentType.FUZZER].execute(state)
            updated_state.agent_states[AgentType.FUZZER].add_message("Fuzzing iteration completed")
            return updated_state
            
        except Exception as e:
            logger.error(f"Fuzzer agent failed: {str(e)}")
            state.agent_states[AgentType.FUZZER].add_error(f"Fuzzing failed: {str(e)}")
            return state
    
    def _coordinator_node(self, state: CTFState) -> CTFState:
        """Coordinate next actions based on current state"""
        logger.info(f"Coordinator evaluating next steps for challenge {state.challenge.id}")
        
        # Mark coordinator as active
        state.set_current_agent(AgentType.COORDINATOR)
        
        # Add coordination logic here
        state.agent_states[AgentType.COORDINATOR].add_message("Evaluating next steps...")
        
        return state
    
    def _should_continue_crawling(self, state: CTFState) -> str:
        """Decide if crawler should continue or move to analysis"""
        crawler_state = state.agent_states[AgentType.CRAWLER]
        
        # Continue crawling if:
        # 1. Haven't reached max pages
        # 2. Found new links to explore
        # 3. Haven't found enough coverage
        
        max_pages = 50  # TODO: Make configurable
        if (len(state.crawled_pages) < max_pages and 
            crawler_state.progress < 1.0):
            return "continue"
        
        return "analyze"
    
    def _should_continue_threat_modeling(self, state: CTFState) -> str:
        """Decide if threat modeling should continue or move to fuzzing"""
        threat_state = state.agent_states[AgentType.THREAT_MODEL]
        
        # Continue if we haven't found enough vulnerabilities or
        # haven't analyzed all crawled content
        if (len(state.vulnerabilities) == 0 or 
            threat_state.progress < 1.0):
            return "continue"
        
        return "fuzz"
    
    def _should_continue_fuzzing(self, state: CTFState) -> str:
        """Decide if fuzzing should continue, coordinate, or end"""
        fuzzer_state = state.agent_states[AgentType.FUZZER]
        
        # End if flag found
        if state.flags_found:
            state.workflow_status = WorkflowStatus.COMPLETED
            return "end"
        
        # Continue fuzzing if we have more payloads to try
        max_attempts = 100  # TODO: Make configurable
        if (len(state.submission.exploit_attempts) < max_attempts and
            len(state.fuzzing_queue) > 0):
            return "continue"
            
        # If we've exhausted current fuzzing queue, coordinate
        if len(state.fuzzing_queue) == 0:
            return "coordinate"
        
        # Otherwise end (max attempts reached)
        state.workflow_status = WorkflowStatus.FAILED
        return "end"
    
    def _coordinator_decision(self, state: CTFState) -> str:
        """Coordinator decides next action"""
        
        # If we found flags, we're done
        if state.flags_found:
            state.workflow_status = WorkflowStatus.COMPLETED
            return "end"
        
        # If we haven't crawled enough, go back to crawling
        if len(state.crawled_pages) < 10:  # TODO: Make configurable
            return "crawler"
        
        # If we need more vulnerabilities, go back to threat modeling
        if len(state.vulnerabilities) < 3:  # TODO: Make configurable
            return "threat_model"
            
        # If we have vulnerabilities but empty fuzzing queue, go to fuzzer
        if len(state.vulnerabilities) > 0 and len(state.fuzzing_queue) == 0:
            return "fuzzer"
        
        # Otherwise we're done
        state.workflow_status = WorkflowStatus.FAILED
        return "end"
    
    async def solve_ctf(self, state: CTFState, thread_id: str = "default") -> CTFState:
        """
        Execute the complete CTF solving workflow
        
        Args:
            state: Initial CTF state with challenge information
            thread_id: Unique identifier for this workflow execution
            
        Returns:
            Final state after workflow completion
        """
        logger.info(f"Starting CTF solving workflow for challenge {state.challenge.id}")
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # Execute the workflow
            final_state = None
            async for event in self.graph.astream(state, config=config):
                logger.debug(f"Workflow event: {event}")
                final_state = event
                
            logger.info(f"CTF solving workflow completed for challenge {state.challenge.id}")
            return final_state
            
        except Exception as e:
            logger.error(f"CTF solving workflow failed: {str(e)}")
            state.workflow_status = WorkflowStatus.FAILED
            return state
    
    def get_workflow_visualization(self) -> str:
        """Get a visual representation of the workflow graph"""
        if not LANGGRAPH_AVAILABLE:
            return "LangGraph not available - install with: pip install langgraph"
        
        try:
            # Dynamic import to avoid linter issues
            visualization = __import__('langgraph.graph.visualization', fromlist=['draw_png'])
            return visualization.draw_png(self.graph)
        except (ImportError, AttributeError):
            return "Visualization requires additional dependencies (pygraphviz and langgraph[visualization])"