import os
import importlib
import logging
import time
import re
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import trim_messages
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from google.api_core.exceptions import ResourceExhausted

from core.browser import browser_manager
from core.utils import timing_decorator

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
logging.getLogger('google.generativeai').setLevel(logging.INFO)
logging.getLogger('google.ai').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('selenium').setLevel(logging.INFO)
logging.getLogger('selenium.webdriver').setLevel(logging.INFO)
logging.getLogger('selenium.webdriver.remote').setLevel(logging.INFO)
logging.getLogger('selenium.webdriver.common').setLevel(logging.INFO)
logging.getLogger('requests').setLevel(logging.INFO)
logging.getLogger('webdriver_manager').setLevel(logging.INFO)
logging.getLogger('langchain').setLevel(logging.INFO)
logging.getLogger('langchain_google_genai').setLevel(logging.INFO)
logging.getLogger('langchain_core').setLevel(logging.INFO)
logging.getLogger('langgraph').setLevel(logging.INFO)


def load_tools(tool_dir="tools") -> list[BaseTool]:
    """
    Dynamically loads all tools decorated with @tool from modules in a given directory.
    """
    tool_list = []
    if not os.path.exists(tool_dir):
        logger.warning(f"Tool directory '{tool_dir}' does not exist.")
        return tool_list

    for filename in os.listdir(tool_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{tool_dir}.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, BaseTool):
                        tool_list.append(attr)
                        logger.info(f"Loaded tool: {attr.name} from {module_name}")
            except Exception as e:
                logger.error(f"Error loading tool from {module_name}: {e}")
    return tool_list

# Create the LLM
llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0,
    max_retries=2
)

def extract_retry_delay(error_message: str) -> float:
    """Extract retry delay from Gemini API error message.

    Args:
        error_message: The error message string

    Returns:
        Retry delay in seconds, defaults to 60 if not found
    """
    # Look for "Please retry in X.Xs" or "retry_delay { seconds: X }"
    patterns = [
        r'Please retry in ([\d.]+)s',
        r'retry_delay\s*{\s*seconds:\s*(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            delay = float(match.group(1))
            logger.info(f"⏰ Extracted retry delay: {delay}s from error message")
            return delay

    # Default to 60 seconds if we can't parse the delay
    logger.warning("⚠️ Could not extract retry delay from error, using default 60s")
    return 60.0

def invoke_llm_with_rate_limit_handling(llm_instance, messages, max_attempts=5):
    """Invoke LLM with automatic rate limit handling.

    Args:
        llm_instance: The LLM instance to invoke
        messages: Messages to send to the LLM
        max_attempts: Maximum number of retry attempts

    Returns:
        The LLM response

    Raises:
        Exception: If all retry attempts fail
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            logger.debug(f"🔄 LLM invocation attempt {attempt + 1}/{max_attempts}")
            return llm_instance.invoke(messages)
        except ResourceExhausted as e:
            attempt += 1
            error_msg = str(e)

            if attempt >= max_attempts:
                logger.error(f"❌ Max retry attempts ({max_attempts}) reached")
                raise

            # Extract retry delay from error message
            retry_delay = extract_retry_delay(error_msg)

            logger.warning(f"⚠️ Rate limit hit (429 error). Waiting {retry_delay}s before retry {attempt}/{max_attempts}")
            logger.info(f"💤 Sleeping for {retry_delay}s...")

            time.sleep(retry_delay)

            logger.info(f"🔄 Retrying after rate limit delay...")
        except Exception as e:
            # For non-rate-limit errors, log details and raise
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"❌ Non-rate-limit error occurred: {error_type}: {error_msg}")

            # If it's a message ordering error, provide helpful context
            if "400" in error_msg and ("function call turn" in error_msg.lower() or "tool" in error_msg.lower()):
                logger.error("💡 This appears to be a message ordering issue.")
                logger.error("💡 Check that tool_calls are followed by tool responses.")
                logger.error("💡 Message sequence validation should have caught this.")

            raise

    raise Exception(f"Failed to invoke LLM after {max_attempts} attempts")

def validate_message_sequence(messages):
    """Validate message sequence follows Gemini's ordering requirements.

    Gemini's Requirements (from error message):
    - Function call turn (AI message with tool_calls) must come immediately after:
      * A user/human turn, OR
      * A function/tool response turn
    - Tool messages must be followed by either another tool message OR an AI message
    - Tool messages must be preceded by an AI message with tool_calls

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

    for i, msg in enumerate(messages):
        # Check AI messages with tool_calls (function call turn)
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Must come after a user turn OR a function response turn
            if i == 0:
                return False, f"AI message with tool_calls at position {i} cannot be first (must follow user or tool message)"

            prev_msg = messages[i - 1]
            # Previous message must be Human or Tool
            if not (isinstance(prev_msg, (HumanMessage, ToolMessage))):
                msg_type = type(prev_msg).__name__
                return False, f"AI message with tool_calls at position {i} must come after HumanMessage or ToolMessage (found {msg_type})"

            # Next message(s) must be tool responses
            if i + 1 >= len(messages):
                return False, f"AI message with tool_calls at position {i} has no following tool messages"

            next_msg = messages[i + 1]
            if not isinstance(next_msg, ToolMessage):
                msg_type = type(next_msg).__name__
                return False, f"AI message with tool_calls at position {i} not followed by ToolMessage (found {msg_type})"

        # Check tool messages
        if isinstance(msg, ToolMessage):
            # Previous message must be AI message with tool_calls OR another tool message
            if i == 0:
                return False, f"ToolMessage at position {i} cannot be first"

            prev_msg = messages[i - 1]
            # Allow consecutive tool messages (multiple tool responses)
            if isinstance(prev_msg, ToolMessage):
                continue

            if not (isinstance(prev_msg, AIMessage) and hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls):
                msg_type = type(prev_msg).__name__
                return False, f"ToolMessage at position {i} not preceded by AI message with tool_calls (found {msg_type})"

    return True, "Valid"

def custom_token_counter(messages):
    """Token counter using Google Gemini's native tokenizer."""
    try:
        # Use the LLM's built-in token counting
        total_tokens = llm.get_num_tokens_from_messages(messages)
        logger.debug(f"🔢 Token count: {total_tokens}")
        return total_tokens
    except Exception as e:
        logger.warning(f"⚠️ Token counting failed: {e}, using character-based estimate")
        # Fallback to character-based estimation (roughly 4 chars per token)
        total_chars = 0
        for message in messages:
            if hasattr(message, 'content') and message.content:
                total_chars += len(str(message.content))
            elif isinstance(message, str):
                total_chars += len(message)
        return total_chars // 4

# Load tools dynamically
tools = load_tools()
if not tools:
    logger.error("❌ No tools loaded! Check the 'tools' directory.")
else:
    logger.info(f"🔧 Loaded {len(tools)} tools")

llm_with_tools = llm.bind_tools(tools)

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
    
    You also have access to the following specialized security tools:

    - `run_ffuf(target_url: str, wordlist: str, options: str = "")`:
      Use this tool for stateful content discovery (finding hidden files or directories).
      It automatically uses your current browser session cookies.
      You MUST provide a `target_url` with 'FUZZ' at the fuzzing location (e.g., 'https://example.com/FUZZ').
      You MUST provide a valid `wordlist` path (e.g., '/usr/share/wordlists/dirb/common.txt').
      Example: After logging in, you could scan for admin panels with `run_ffuf(target_url='https://current-site.com/FUZZ', wordlist='path/to/wordlist.txt')`.

    - `run_sqlmap(target_url: str, options: str = "--batch --level=1 --risk=1")`:
      Use this tool to test for SQL injection vulnerabilities on a URL with parameters.
      It automatically uses your browser session cookies.
      The `target_url` must be the full, specific URL you want to test (e.g., 'https://example.com/items.php?id=123').
      Only use this when you have identified a specific URL with parameters that looks suspicious.

    Always analyze the output of these tools to guide your next steps. If a tool returns an error, do not try it again immediately. Analyze the error and try to solve the problem (e.g., by providing a correct wordlist path).
    
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

    logger.debug(f"📊 Processing {len(messages)} messages before trimming")

    # Use LangChain's built-in trim_messages function with progressive trimming
    # This properly handles tool call/response chains and message ordering
    TOKEN_LIMIT = 200000

    # Try trimming with progressively lower token limits until we get a valid sequence
    trimmed_messages = None
    token_limits_to_try = [TOKEN_LIMIT]

    # Generate progressive token limits (90%, 80%, 70%, ... of original)
    for percentage in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]:
        token_limits_to_try.append(int(TOKEN_LIMIT * percentage))

    for attempt, current_limit in enumerate(token_limits_to_try):
        try:
            candidate_messages = trim_messages(
                messages=messages,
                max_tokens=current_limit,
                token_counter=custom_token_counter,
                strategy="last",  # Keep most recent messages
                allow_partial=False,  # Don't break message sequences
                include_system=True  # Always keep system messages
            )

            # Validate the trimmed messages
            is_valid, validation_msg = validate_message_sequence(candidate_messages)

            if is_valid:
                trimmed_messages = candidate_messages
                if len(trimmed_messages) < len(messages):
                    logger.debug(f"✂️ Trimmed from {len(messages)} to {len(trimmed_messages)} messages (limit: {current_limit} tokens)")
                break
            else:
                if attempt == 0:
                    logger.debug(f"⚠️ Trimming with {current_limit} tokens creates invalid sequence: {validation_msg}")
                    logger.debug(f"🔄 Trying with lower token limit...")
        except Exception as e:
            logger.debug(f"⚠️ Trimming with {current_limit} tokens failed: {e}")
            continue

    # If no valid trimming found, use all messages
    if trimmed_messages is None:
        logger.warning(f"⚠️ Could not find valid trimming, using all {len(messages)} messages")
        trimmed_messages = messages

        # Final validation
        is_valid, validation_msg = validate_message_sequence(trimmed_messages)
        if not is_valid:
            logger.error(f"❌ Even untrimmed messages are invalid: {validation_msg}")
            logger.error("📋 Message sequence:")
            for i, msg in enumerate(trimmed_messages):
                msg_type = type(msg).__name__
                has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
                logger.error(f"  [{i}] {msg_type}{' (with tool_calls)' if has_tool_calls else ''}")
            raise ValueError(f"Invalid message sequence for Gemini API: {validation_msg}")

    # Log the message sequence for debugging
    logger.debug("📋 Message sequence being sent to Gemini:")
    for i, msg in enumerate(trimmed_messages):
        msg_type = type(msg).__name__
        has_tool_calls = hasattr(msg, 'tool_calls') and msg.tool_calls
        logger.debug(f"  [{i}] {msg_type}{' (with tool_calls)' if has_tool_calls else ''}")

    # Count tokens in final messages
    token_count = custom_token_counter(trimmed_messages)
    logger.debug(f"📊 Final: {len(trimmed_messages)} messages, ~{token_count} tokens")

    response = invoke_llm_with_rate_limit_handling(llm_with_tools, trimmed_messages)
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
        # Handle both string and list content
        if isinstance(last_message.content, str):
            content = last_message.content.upper()
        elif isinstance(last_message.content, list):
            # Join list items into a single string
            content = " ".join(str(item) for item in last_message.content).upper()
        else:
            content = str(last_message.content).upper()

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
workflow.add_node("tools", ToolNode(tools))

# Set entry point
workflow.set_entry_point("agent")

# Simplified edges
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