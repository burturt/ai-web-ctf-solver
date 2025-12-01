# Plan for Integrating Stateful Fuzzing into the AI Web CTF Solver

## 1. Introduction & Goals

This document outlines a detailed plan to integrate stateful web application fuzzing capabilities into the existing AI-powered CTF solver framework. 

The primary goals of this refactoring and implementation are:

1.  **Modularity**: To create a framework where tools are isolated into self-contained modules. This allows for adding, removing, or disabling features without impacting the core application logic.
2.  **Debuggability**: To ensure that each component, especially the external tool integrations, has robust logging and clear error handling, making it easier to diagnose issues.
3.  **Resilience**: To build a system where the failure of a single tool or component (e.g., a missing executable or a bug in a tool's logic) does not crash the entire agent, but instead provides a useful error message that the agent can act upon.

## 2. Core Architectural Change: A Modular Tool System

To achieve our goals, we will move away from defining tools directly in `main.py` and create a dedicated, plug-and-play tool system.

### 2.1. New Directory Structure

We will introduce a `tools/` directory to house all agent-callable tools, and a `core/` directory for shared components like the `BrowserManager`.

```
/
├── main.py
├── PLAN.md
├── core/
│   ├── __init__.py
│   └── browser.py      # Move BrowserManager here
└── tools/
    ├── __init__.py
    ├── web_navigation.py # Move existing browser tools here
    └── fuzzing.py        # New fuzzing tools will live here
```

### 2.2. Dynamic Tool Loading

In `main.py`, we will implement a function, `load_tools`, that dynamically imports all modules from the `tools/` directory and registers any function decorated with LangChain's `@tool`.

This means that to add a new tool, one only needs to create a function with the `@tool` decorator in any file within the `tools/` directory. To disable a tool or a set of tools, you can simply rename the file (e.g., `fuzzing.py` to `fuzzing.py.disabled`) or comment out the `@tool` decorator.

## 3. Step-by-Step Implementation Plan

### Step 3.1: Refactor Existing Codebase

1.  **Create `core/` directory:**
    *   Create a new file `core/browser.py`.
    *   Move the `BrowserManager` class from `main.py` into `core/browser.py`.
    *   Instantiate a single, global instance of the browser manager in this file: `browser_manager = BrowserManager()`.
    *   In `main.py`, remove the `BrowserManager` class definition and instead import the instance: `from core.browser import browser_manager`.

2.  **Create `tools/` directory:**
    *   Create a new file `tools/web_navigation.py`.
    *   Move all the existing web-interaction tool functions (`navigate_to_url`, `click_element`, `enter_text`, `get_page_source`, `fetch_contents`) from `main.py` into `tools/web_navigation.py`.
    *   Add the necessary imports to this file, including `@tool` and `from core.browser import browser_manager`.

### Step 3.2: Implement Dynamic Tool Loader in `main.py`

1.  **Add imports** for `os` and `importlib` to `main.py`.
2.  **Create the `load_tools` function:**

    ```python
    import os
    import importlib
    from langchain_core.tools import BaseTool

    def load_tools(tool_dir="tools") -> list[BaseTool]:
        """
        Dynamically loads all tools decorated with @tool from modules in a given directory.
        """
        tool_list = []
        for filename in os.listdir(tool_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"{tool_dir}.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, BaseTool):
                            tool_list.append(attr)
                except Exception as e:
                    print(f"Error loading tool from {module_name}: {e}")
        return tool_list
    ```
3.  **Update Agent Initialization:** In `main.py`, replace the static `tools = [...]` list with a call to this new function: `tools = load_tools()`.

### Step 3.3: Implement the Fuzzing Tools

1.  **Create `tools/fuzzing.py`**.
2.  **Add Imports:** This file will need `subprocess`, `logging`, `@tool`, and `from core.browser import browser_manager`.
3.  **Implement `run_ffuf`:**

    ```python
    import subprocess
    import logging
    from langchain_core.tools import tool
    from core.browser import browser_manager

    @tool
    def run_ffuf(target_url: str, wordlist: str, options: str = "") -> str:
        """
        Runs ffuf for content discovery on a URL using the current browser session.
        - target_url: The full URL to scan. Use 'FUZZ' to indicate the fuzzing point.
        - wordlist: The path to the wordlist file.
        - options: Optional additional ffuf command-line arguments.
        """
        logging.info(f"Running ffuf on {target_url} with wordlist {wordlist}")
        try:
            # Get cookies from the browser session
            cookies = browser_manager.get_driver().get_cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            command = f"ffuf -w {wordlist} -u {target_url} -b \"{cookie_str}\" {options} -ac"

            logging.info(f"Executing ffuf command: {command}")

            # Execute the command
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300 # 5-minute timeout
            )

            if process.returncode != 0 and "Wordlist file not found" in process.stderr:
                return f"Error: Wordlist file not found at path: {wordlist}. Please provide a valid path."

            # Return the captured output, sanitized for the agent
            output = process.stdout
            if not output:
                return "ffuf completed with no output. This may mean nothing was found or an error occurred."
            
            # Simple summary: return a fixed number of lines
            summary = "\n".join(output.strip().split("\n")[:20])
            return f"ffuf scan completed. Output summary:\n{summary}"

        except FileNotFoundError:
            return "Error: `ffuf` command not found. Please ensure it is installed and in your system's PATH."
        except subprocess.TimeoutExpired:
            return "Error: ffuf scan timed out after 5 minutes."
        except Exception as e:
            logging.error(f"An unexpected error occurred while running ffuf: {e}")
            return f"An unexpected error occurred: {str(e)}"

    ```
4.  **Implement `run_sqlmap` (in `tools/fuzzing.py`):**
    This implementation will be very similar, following the same pattern of getting cookies, building a command, executing it with `subprocess`, and handling errors gracefully.

    ```python
    @tool
    def run_sqlmap(target_url: str, options: str = "--batch --level=1 --risk=1") -> str:
        """
        Runs sqlmap on a target URL to check for SQL injection vulnerabilities.
        - target_url: The full URL to test, including parameters.
        - options: Optional additional sqlmap command-line arguments. Defaults to non-interactive mode.
        """
        logging.info(f"Running sqlmap on {target_url}")
        try:
            # Get cookies and format them for sqlmap
            cookies = browser_manager.get_driver().get_cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            command = f"sqlmap -u \"{target_url}\" --cookie=\"{cookie_str}\" {options}"
            
            logging.info(f"Executing sqlmap command: {command}")
            
            process = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=600)

            if "is vulnerable" in process.stdout:
                return f"sqlmap found a potential vulnerability at {target_url}. Full output is in the logs. Key findings:\n" + process.stdout
            else:
                return "sqlmap scan completed. No obvious vulnerabilities found with the given options."

        except FileNotFoundError:
            return "Error: `sqlmap` command not found. Please ensure it is installed and in your system's PATH."
        except subprocess.TimeoutExpired:
            return "Error: sqlmap scan timed out after 10 minutes."
        except Exception as e:
            logging.error(f"An unexpected error occurred while running sqlmap: {e}")
            return f"An unexpected error occurred: {str(e)}"
    ```

### Step 3.4: Update Agent's System Prompt

The final, crucial step is to make the agent aware of its new tools. We will update the `system_prompt` variable in `main.py`.

**Add the following tool descriptions to the prompt:**

```
... existing prompt ...

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
```

## 4. Phase 2: LLM-Generated Fuzzing

After the core framework is stable, we can implement the LLM-powered payload generation as a new tool in `tools/fuzzing.py`.

- **Tool Name:** `generate_contextual_payloads(field_description: str) -> list[str]`
- **Implementation:** This tool would not use `subprocess`. Instead, it would make a separate, specific call to an LLM (e.g., using the `ChatOpenAI` object from `main.py`) with a prompt like: "You are a security expert. Generate a list of 10 creative fuzzing payloads for a form field described as: '{field_description}'. Return only a Python list of strings."
- **Agent Workflow:** The main agent would first identify a form field, then call this tool to get payloads, and finally loop through them using the `enter_text` and `click_element` tools from `tools/web_navigation.py`.

```
```