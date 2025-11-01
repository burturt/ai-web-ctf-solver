# AI Web CTF Solver

A LangGraph-powered multi-agent AI system for automatically solving web CTF challenges.

## Overview

This project implements **Stateful-LLM-Fuzz**, a hybrid framework that uses agentic LLMs to solve web CTF challenges through intelligent crawling, analysis, threat modeling, and exploitation.

### Architecture

The system consists of four specialized AI agents orchestrated by LangGraph:

1. **Web Crawler Agent** - Maps and explores web applications
2. **Summarizer Agent** - Analyzes source code and web content  
3. **Threat Model Agent** - Identifies vulnerabilities and attack vectors
4. **Fuzzing Agent** - Exploits vulnerabilities using AI-controlled automation

## Features

- 🤖 **Multi-Agent AI System** - Specialized agents for different security testing phases
- 🕸️ **Intelligent Web Crawling** - AI-guided exploration of web applications
- 🔍 **Source Code Analysis** - Automated analysis of provided source code
- 🎯 **Threat Modeling** - STRIDE-based vulnerability identification
- ⚡ **Smart Exploitation** - Adaptive fuzzing with AI-generated payloads
- 🌐 **Web Interface** - Real-time monitoring and challenge submission
- 📊 **Live Dashboard** - Progress tracking and result visualization

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/burturt/ai-web-ctf-solver.git
   cd ai-web-ctf-solver
   ```

2. **Install Python dependencies**
   
   **Option A: Full installation (recommended)**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```
   
   **Option B: Minimal installation (if full install fails)**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements-minimal.txt
   ```
   
   **Option C: Step-by-step installation**
   ```bash
   # Install build tools first
   pip install --upgrade pip setuptools wheel
   
   # Install core LangChain dependencies
   pip install langchain langchain-openai langgraph
   
   # Install web framework
   pip install fastapi uvicorn jinja2
   
   # Install utilities
   pip install requests beautifulsoup4 python-dotenv pydantic loguru
   ```

5. **Test your installation**
   ```bash
   python test_installation.py
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

   **For Azure OpenAI users:**
   ```bash
   python setup_azure.py
   # Follow the interactive setup to configure Azure OpenAI
   ```

4. **Install additional tools (optional)**
   ```bash
   # Install Chrome/Chromium for Selenium
   # On macOS: brew install --cask google-chrome
   # On Ubuntu: apt-get install chromium-browser
   ```

## Configuration

Edit the `.env` file with your settings:

```env
# API Keys (required - choose one)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Azure OpenAI (alternative to OpenAI)
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
USE_AZURE_OPENAI=true

# LLM Configuration
DEFAULT_MODEL=gpt-4-turbo-preview
TEMPERATURE=0.7
MAX_TOKENS=4096

# Crawler Settings
CRAWLER_MAX_PAGES=50
CRAWLER_TIMEOUT=30

# Security Settings  
MAX_FUZZING_ATTEMPTS=100
FUZZING_TIMEOUT=300

# Web Interface
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### Azure OpenAI Setup

If you're using Azure OpenAI instead of OpenAI directly:

1. **Run the interactive setup script:**
   ```bash
   python setup_azure.py
   ```

2. **Or manually configure your `.env` file:**
   ```env
   USE_AZURE_OPENAI=true
   AZURE_OPENAI_API_KEY=your-azure-api-key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=your-gpt-4-deployment-name
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   ```

3. **Required Azure Resources:**
   - Azure OpenAI Service resource
   - GPT-4 or GPT-3.5-turbo model deployment
   - API key with appropriate permissions

4. **Test your configuration:**
   ```bash
   python setup_azure.py
   # Choose option 3 to test existing configuration
   ```

## Usage

### Starting the Application

```bash
python main.py
```

The web interface will be available at `http://localhost:8000`

### Submitting a CTF Challenge

1. Navigate to the home page
2. Fill in the challenge details:
   - **Challenge URL** (required)
   - **Title** (optional)
   - **Description** (optional)  
   - **Source Code** (optional)
   - **Flag Format** (optional, e.g., "CTF{...}")
   - **Hint** (optional)

3. Click "Start Solving" to begin the automated solving process

### Monitoring Progress

The system provides real-time monitoring through:

- **Live agent status** - See which agent is currently active
- **Progress tracking** - Overall completion percentage
- **Live logs** - Real-time agent messages and actions
- **Vulnerability detection** - Identified security issues
- **Statistics** - Pages crawled, exploits attempted, etc.
- **Flag results** - Automatically detected flags

## Architecture Details

### LangGraph Workflow

```
START → Crawler → Summarizer → Threat Model → Fuzzer → END
  ↑        ↓          ↓            ↓          ↓
  └─── Coordinator ←──┴────────────┴──────────┘
```

### Agent Responsibilities

#### 1. Web Crawler Agent
- Systematically maps web application structure
- Discovers hidden endpoints and parameters
- Extracts forms, links, and input fields
- Identifies technology stack
- Uses both HTTP requests and Selenium for JS-heavy sites

#### 2. Summarizer Agent  
- Analyzes provided source code for vulnerabilities
- Processes crawled web content
- Identifies application architecture and data flow
- Extracts security-relevant information
- Generates comprehensive security assessment

#### 3. Threat Model Agent
- Performs STRIDE threat modeling
- Identifies specific exploitable vulnerabilities  
- Analyzes attack surface
- Prioritizes threats by exploitability
- Generates detailed exploitation plan

#### 4. Fuzzing Agent
- Executes targeted exploitation attempts
- Tests SQL injection, XSS, auth bypass, file upload, etc.
- Adapts payloads based on response analysis
- Automatically extracts flags from responses
- Uses both HTTP requests and browser automation

### State Management

The system uses a comprehensive state object (`CTFState`) that tracks:
- Challenge information
- Crawling results (pages, forms, links)
- Analysis findings
- Identified vulnerabilities  
- Fuzzing queue and results
- Agent progress and messages
- Found flags and successful exploits

## API Endpoints

### Challenge Management
- `POST /api/challenges/submit` - Submit new challenge
- `GET /api/challenges/{id}/status` - Get challenge status
- `GET /api/challenges/{id}/details` - Get detailed information
- `POST /api/challenges/{id}/stop` - Stop running challenge
- `DELETE /api/challenges/{id}` - Delete challenge

### System Information  
- `GET /api/challenges` - List all challenges
- `GET /api/stats` - System statistics
- `GET /health` - Health check

## Supported Vulnerability Types

The system can identify and exploit:

- **SQL Injection** - Various injection techniques
- **Cross-Site Scripting (XSS)** - Reflected and stored
- **Authentication Bypass** - Logic flaws and injection
- **Authorization Issues** - Access control vulnerabilities
- **File Upload** - Malicious file upload attacks
- **Command Injection** - OS command execution
- **XXE** - XML external entity attacks
- **SSRF** - Server-side request forgery
- **Deserialization** - Object deserialization flaws

## Development

### Project Structure

```
ai-web-ctf-solver/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment configuration template
├── src/
│   ├── models/            # Data models
│   │   ├── challenge.py   # Challenge and exploit models
│   │   └── state.py       # State management models
│   ├── agents/            # AI agents
│   │   ├── base.py        # Base agent class
│   │   ├── crawler.py     # Web crawler agent
│   │   ├── summarizer.py  # Content analysis agent
│   │   ├── threat_model.py # Threat modeling agent
│   │   └── fuzzer.py      # Exploitation agent
│   ├── graph/             # LangGraph workflow
│   │   └── workflow.py    # Main workflow definition
│   ├── web/               # Web interface
│   │   ├── app.py         # FastAPI application
│   │   └── templates/     # HTML templates
│   └── utils/             # Utility modules
│       ├── config.py      # Configuration management
│       └── logging.py     # Logging setup
└── tests/                 # Test files
```

### Running Tests

```bash
python -m pytest tests/
```

### Adding New Vulnerability Types

1. Add the vulnerability type to `ChallengeType` enum in `models/challenge.py`
2. Implement detection logic in `ThreatModelAgent`
3. Add exploitation method in `FuzzerAgent`
4. Update payload generation in threat modeling

## Security Considerations

⚠️ **Important**: This tool is designed for educational purposes and authorized security testing only.

- Only test applications you own or have explicit permission to test
- The tool performs active exploitation attempts
- Some payloads may cause service disruption
- Review all generated requests before execution in production environments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Team

**Team PBR** - ECE M117 Fall 2025
- Casey
- Roshni  
- Alec
- Lena
- Paramee

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for multi-agent orchestration
- Uses [LangChain](https://github.com/langchain-ai/langchain) for LLM integration
- Web interface powered by [FastAPI](https://fastapi.tiangolo.com/)
- Automation via [Selenium](https://selenium.dev/) and [Requests](https://requests.readthedocs.io/)

## Citation

```bibtex
@misc{ai-web-ctf-solver-2025,
  title={AI Web CTF Solver: LangGraph-Powered Multi-Agent Security Testing},
  author={Team PBR},
  year={2025},
  url={https://github.com/burturt/ai-web-ctf-solver}
}
```