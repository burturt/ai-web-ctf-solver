#!/usr/bin/env python3
"""
Validate Azure OpenAI configuration for the AI Web CTF Solver
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def validate_azure_config():
    """Validate Azure OpenAI configuration"""
    print("🔍 Validating Azure OpenAI Configuration...")
    
    try:
        from src.utils.config import get_config
        from src.agents.base import BaseAgent
        from src.models.state import AgentType
        
        # Load configuration
        config = get_config()
        
        # Check if Azure OpenAI is enabled
        if not config.get("USE_AZURE_OPENAI"):
            print("❌ USE_AZURE_OPENAI is not set to true in .env file")
            return False
        
        # Check required Azure OpenAI settings
        required_settings = [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT", 
            "AZURE_OPENAI_DEPLOYMENT_NAME"
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not config.get(setting):
                missing_settings.append(setting)
        
        if missing_settings:
            print(f"❌ Missing required settings: {', '.join(missing_settings)}")
            return False
        
        print("✅ Configuration settings found")
        
        # Test LLM initialization
        print("🧪 Testing LLM initialization...")
        
        try:
            # Create a test agent to validate LLM setup
            agent = BaseAgent(AgentType.CRAWLER)
            print("✅ Azure OpenAI LLM initialized successfully")
            
            # Test a simple call
            print("🧪 Testing API call...")
            
            test_prompt = "Respond with 'Azure OpenAI test successful' if you can read this."
            response = agent.llm.invoke(test_prompt)
            
            print("✅ Azure OpenAI API call successful!")
            print(f"Response: {response.content}")
            
            return True
            
        except Exception as e:
            print(f"❌ LLM initialization failed: {str(e)}")
            print("\nTroubleshooting tips:")
            print("1. Check your API key is valid")
            print("2. Verify the endpoint URL is correct")
            print("3. Ensure the deployment name matches your Azure deployment")
            print("4. Check that your deployment is running and available")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("Make sure you've installed all dependencies: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Validation failed: {str(e)}")
        return False

def show_current_config():
    """Show current Azure OpenAI configuration (without secrets)"""
    try:
        from src.utils.config import get_config
        config = get_config()
        
        print("\n📋 Current Configuration:")
        print("=" * 30)
        print(f"USE_AZURE_OPENAI: {config.get('USE_AZURE_OPENAI')}")
        
        api_key = config.get('AZURE_OPENAI_API_KEY', '')
        if api_key:
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            print(f"AZURE_OPENAI_API_KEY: {masked_key}")
        else:
            print("AZURE_OPENAI_API_KEY: Not set")
            
        print(f"AZURE_OPENAI_ENDPOINT: {config.get('AZURE_OPENAI_ENDPOINT', 'Not set')}")
        print(f"AZURE_OPENAI_DEPLOYMENT_NAME: {config.get('AZURE_OPENAI_DEPLOYMENT_NAME', 'Not set')}")
        print(f"AZURE_OPENAI_API_VERSION: {config.get('AZURE_OPENAI_API_VERSION', 'Not set')}")
        print(f"DEFAULT_MODEL: {config.get('DEFAULT_MODEL', 'Not set')}")
        
    except Exception as e:
        print(f"❌ Failed to load configuration: {str(e)}")

if __name__ == "__main__":
    print("AI Web CTF Solver - Azure OpenAI Validation")
    print("=" * 50)
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("❌ .env file not found. Please copy .env.example to .env and configure it.")
        sys.exit(1)
    
    show_current_config()
    
    print("\n" + "=" * 50)
    
    if validate_azure_config():
        print("\n🎉 Azure OpenAI configuration is valid!")
        print("You can now start the AI Web CTF Solver with: python main.py")
    else:
        print("\n❌ Azure OpenAI configuration validation failed.")
        print("Run 'python setup_azure.py' to reconfigure Azure OpenAI settings.")
        sys.exit(1)