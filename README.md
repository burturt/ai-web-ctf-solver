# AI Web CTF Solver

An automated tool that uses **Google Gemini** (via LangChain) and **Selenium** to autonomously solve Web Capture The Flag (CTF) challenges. It combines an LLM-based agent with browser automation and security tools to investigate, exploit, and retrieve flags.

## 🚀 Features

*   **AI Agent:** Powered by Google Gemini, capable of reasoning, planning, and executing complex multi-step attacks.
*   **Browser Automation:** Uses Selenium (Chrome) to interact with web pages (click, fill forms, execute JS, inspect DOM).
*   **Tool Integration:**
    *   **Fuzzing:** Integrates with `ffuf` for directory and file discovery.
    *   **SQL Injection:** Integrates with `sqlmap` for detecting and exploiting SQLi.
    *   **Web Inspection:** Custom tools to fetch headers, view source, and analyze console logs.
*   **Rate Limit Handling:** Intelligent handling of Gemini API rate limits with automatic retries.
*   **User Interface:** Includes a Streamlit-based web UI for easy interaction and file uploads.

## 🛠️ Prerequisites

Before running the project, ensure you have the following installed:

1.  **Python 3.9+**
2.  **Google Chrome** (for Selenium automation)
3.  **Security Tools** (optional but recommended for full functionality):
    *   [`ffuf`](https://github.com/ffuf/ffuf) (Fuzz Faster U Fool)
    *   [`sqlmap`](https://github.com/sqlmapproject/sqlmap)

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd ai-web-ctf-solver
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Setup:**
    Create a `.env` file in the root directory and add your Google Gemini API key:
    ```bash
    GEMINI_API_KEY=your_api_key_here
    GEMINI_MODEL=gemini-2.5-flash # Optional, defaults to gemini-2.5-flash
    ```

## 🖥️ Usage

### Web Interface (Recommended)
The easiest way to use the solver is via the Streamlit UI:

```bash
streamlit run app.py
```
This will open a web page (usually http://localhost:8501) where you can:
*   Enter the target URL.
*   Provide additional hints or context.
*   Upload challenge files (source code, pcap, etc.).
*   View the agent's live progress and logs.

### Command Line Interface
You can also run the solver directly from the terminal. 
*Note: currently `main.py` has a hardcoded example in the `__main__` block. You may need to edit it to change the target.*

```bash
python main.py
```

## 📂 Project Structure

*   `app.py`: Streamlit frontend application.
*   `main.py`: Core logic, agent definition, and entry point.
*   `core/`: Core functionality.
    *   `browser.py`: Selenium browser management.
    *   `utils.py`: Utility functions (e.g., timing decorators).
*   `tools/`: Tool definitions for the LLM.
    *   `fuzzing.py`: Wrappers for `ffuf` and `sqlmap`.
    *   `web_navigation.py`: (Implied) Browser interaction tools.
*   `files/`: Directory where uploaded challenge files are stored.

## 🛡️ Disclaimer
This tool is intended for educational purposes and authorized security testing (CTFs) only. **Do not use this tool on any system you do not own or have explicit permission to test.**
