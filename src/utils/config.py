"""
Configuration management for the CTF solver
"""
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration management class"""
    
    def __init__(self):
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            # API Keys
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            
            # Azure OpenAI Configuration
            "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            "AZURE_OPENAI_DEPLOYMENT_NAME": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            "USE_AZURE_OPENAI": os.getenv("USE_AZURE_OPENAI", "false").lower() == "true",
            
            # Database
            "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///./ctf_solver.db"),
            "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
            
            # Crawler settings
            "CRAWLER_MAX_DEPTH": int(os.getenv("CRAWLER_MAX_DEPTH", "5")),
            "CRAWLER_MAX_PAGES": int(os.getenv("CRAWLER_MAX_PAGES", "50")),
            "CRAWLER_TIMEOUT": int(os.getenv("CRAWLER_TIMEOUT", "30")),
            "USER_AGENT": os.getenv("USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"),
            
            # LLM settings
            "DEFAULT_MODEL": os.getenv("DEFAULT_MODEL", "gpt-4-turbo-preview"),
            "BACKUP_MODEL": os.getenv("BACKUP_MODEL", "claude-3-opus-20240229"),
            "MAX_TOKENS": int(os.getenv("MAX_TOKENS", "4096")),
            "TEMPERATURE": float(os.getenv("TEMPERATURE", "0.7")),
            
            # Security settings
            "MAX_FUZZING_ATTEMPTS": int(os.getenv("MAX_FUZZING_ATTEMPTS", "100")),
            "FUZZING_TIMEOUT": int(os.getenv("FUZZING_TIMEOUT", "300")),
            "EXPLOIT_TIMEOUT": int(os.getenv("EXPLOIT_TIMEOUT", "60")),
            
            # Web interface
            "HOST": os.getenv("HOST", "0.0.0.0"),
            "PORT": int(os.getenv("PORT", "8000")),
            "DEBUG": os.getenv("DEBUG", "True").lower() == "true",
            
            # Logging
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "LOG_FILE": os.getenv("LOG_FILE", "logs/ctf_solver.log")
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self._config.copy()

# Global config instance
_config = None

def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config

def initialize_config(config_file: str = None):
    """Initialize configuration from file"""
    global _config
    if config_file and Path(config_file).exists():
        load_dotenv(config_file)
    _config = Config()