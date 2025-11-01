"""
Main entry point for the AI Web CTF Solver
"""
import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.config import initialize_config
from src.utils.logging import setup_logging, get_logger
from src.web.app import run_server

def main():
    """Main application entry point"""
    try:
        # Initialize configuration
        initialize_config()
        
        # Setup logging
        setup_logging(log_level="INFO", log_file="logs/ctf_solver.log")
        logger = get_logger(__name__)
        
        logger.info("Starting AI Web CTF Solver...")
        logger.info("LangGraph Multi-Agent System - Team PBR")
        
        # Run the web server
        run_server()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()