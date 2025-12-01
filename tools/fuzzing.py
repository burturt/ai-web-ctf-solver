import subprocess
import logging
from langchain_core.tools import tool
from core.browser import browser_manager
from core.utils import timing_decorator

logger = logging.getLogger(__name__)

@tool
@timing_decorator
def run_ffuf(target_url: str, wordlist: str, options: str = "") -> str:
    """
    Runs ffuf for content discovery on a URL using the current browser session.
    - target_url: The full URL to scan. Use 'FUZZ' to indicate the fuzzing point.
    - wordlist: The path to the wordlist file.
    - options: Optional additional ffuf command-line arguments.
    """
    logger.info(f"Running ffuf on {target_url} with wordlist {wordlist}")
    try:
        # Get cookies from the browser session
        cookies = browser_manager.get_driver().get_cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        command = f"ffuf -w {wordlist} -u {target_url} -b \"{cookie_str}\" {options} -ac"

        logger.info(f"Executing ffuf command: {command}")

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
        logger.error(f"An unexpected error occurred while running ffuf: {e}")
        return f"An unexpected error occurred: {str(e)}"

@tool
@timing_decorator
def run_sqlmap(target_url: str, options: str = "--batch --level=1 --risk=1") -> str:
    """
    Runs sqlmap on a target URL to check for SQL injection vulnerabilities.
    - target_url: The full URL to test, including parameters.
    - options: Optional additional sqlmap command-line arguments. Defaults to non-interactive mode.
    """
    logger.info(f"Running sqlmap on {target_url}")
    try:
        # Get cookies and format them for sqlmap
        cookies = browser_manager.get_driver().get_cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        command = f"sqlmap -u \"{target_url}\" --cookie=\"{cookie_str}\" {options}"
        
        logger.info(f"Executing sqlmap command: {command}")
        
        process = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=600)

        if "is vulnerable" in process.stdout:
            return f"sqlmap found a potential vulnerability at {target_url}. Full output is in the logs. Key findings:\n" + process.stdout
        else:
            return "sqlmap scan completed. No obvious vulnerabilities found with the given options. Output:" + process.stdout

    except FileNotFoundError:
        return "Error: `sqlmap` command not found. Please ensure it is installed and in your system's PATH."
    except subprocess.TimeoutExpired:
        return "Error: sqlmap scan timed out after 10 minutes."
    except Exception as e:
        logger.error(f"An unexpected error occurred while running sqlmap: {e}")
        return f"An unexpected error occurred: {str(e)}"
