#!/usr/bin/env python3
"""
Azure OpenAI Configuration Helper
Run this script to configure Azure OpenAI settings for the AI Web CTF Solver
"""

import os
from pathlib import Path

def setup_azure_openai():
    """Interactive setup for Azure OpenAI configuration"""
    print("🔧 Azure OpenAI Configuration Setup")
    print("=" * 50)
    
    env_file = Path(".env")
    
    # Check if .env exists, if not copy from example
    if not env_file.exists():
        example_file = Path(".env.example")
        if example_file.exists():
            import shutil
            shutil.copy(example_file, env_file)
            print("✅ Created .env file from .env.example")
        else:
            print("❌ .env.example not found. Please create it first.")
            return
    
    print("\nPlease provide your Azure OpenAI configuration:")
    
    # Collect Azure OpenAI settings
    azure_settings = {}
    
    azure_settings['AZURE_OPENAI_API_KEY'] = input("Azure OpenAI API Key: ").strip()
    azure_settings['AZURE_OPENAI_ENDPOINT'] = input("Azure OpenAI Endpoint (e.g., https://your-resource.openai.azure.com/): ").strip()
    azure_settings['AZURE_OPENAI_DEPLOYMENT_NAME'] = input("Deployment Name (e.g., gpt-4): ").strip()
    
    api_version = input("API Version (press Enter for default 2024-02-15-preview): ").strip()
    if not api_version:
        api_version = "2024-02-15-preview"
    azure_settings['AZURE_OPENAI_API_VERSION'] = api_version
    
    # Validate inputs
    required_fields = ['AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_DEPLOYMENT_NAME']
    for field in required_fields:
        if not azure_settings[field]:
            print(f"❌ {field} is required!")
            return
    
    # Update .env file
    update_env_file(env_file, azure_settings)
    
    print("\n✅ Azure OpenAI configuration completed!")
    print("📝 Updated .env file with Azure OpenAI settings")
    print("\nTo use Azure OpenAI, make sure USE_AZURE_OPENAI=true in your .env file")
    
    # Test configuration
    test_config = input("\nWould you like to test the configuration? (y/n): ").strip().lower()
    if test_config == 'y':
        test_azure_openai_config(azure_settings)

def update_env_file(env_file: Path, azure_settings: dict):
    """Update .env file with Azure OpenAI settings"""
    
    # Read existing .env content
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add Azure OpenAI settings
    updated_lines = []
    azure_keys = set(azure_settings.keys())
    found_keys = set()
    
    for line in lines:
        line = line.strip()
        if '=' in line:
            key = line.split('=')[0]
            if key in azure_keys:
                # Update existing key
                updated_lines.append(f"{key}={azure_settings[key]}\n")
                found_keys.add(key)
            elif key == 'USE_AZURE_OPENAI':
                # Enable Azure OpenAI
                updated_lines.append("USE_AZURE_OPENAI=true\n")
            else:
                # Keep existing line
                updated_lines.append(line + "\n")
        else:
            # Keep comments and empty lines
            updated_lines.append(line + "\n")
    
    # Add missing Azure OpenAI keys
    missing_keys = azure_keys - found_keys
    if missing_keys:
        updated_lines.append("\n# Azure OpenAI Configuration (added by setup script)\n")
        for key in missing_keys:
            updated_lines.append(f"{key}={azure_settings[key]}\n")
    
    # Add USE_AZURE_OPENAI if not found
    if not any('USE_AZURE_OPENAI' in line for line in updated_lines):
        updated_lines.append("USE_AZURE_OPENAI=true\n")
    
    # Write updated content
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)

def test_azure_openai_config(azure_settings: dict):
    """Test Azure OpenAI configuration"""
    print("\n🧪 Testing Azure OpenAI configuration...")
    
    try:
        from langchain_openai import AzureChatOpenAI
        
        # Create Azure OpenAI client
        llm = AzureChatOpenAI(
            azure_endpoint=azure_settings['AZURE_OPENAI_ENDPOINT'],
            api_key=azure_settings['AZURE_OPENAI_API_KEY'],
            api_version=azure_settings['AZURE_OPENAI_API_VERSION'],
            deployment_name=azure_settings['AZURE_OPENAI_DEPLOYMENT_NAME'],
            temperature=0.7,
            max_tokens=100
        )
        
        # Test with a simple prompt - use simple string instead of HumanMessage for compatibility
        test_prompt = "Hello! Please respond with 'Azure OpenAI connection successful'."
        
        response = llm.invoke(test_prompt)
        
        print("✅ Azure OpenAI connection successful!")
        print(f"Response: {response.content}")
        
    except ImportError:
        print("⚠️  langchain-openai not installed. Run: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Azure OpenAI connection failed: {str(e)}")
        print("\nPlease check your configuration:")
        print("1. Verify your API key is correct")
        print("2. Ensure the endpoint URL is correct") 
        print("3. Check that the deployment name matches your Azure deployment")
        print("4. Verify the API version is supported")

def show_config_example():
    """Show example configuration"""
    print("\n📋 Example Azure OpenAI Configuration:")
    print("=" * 40)
    print("AZURE_OPENAI_API_KEY=your-32-character-api-key-here")
    print("AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/")
    print("AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4")
    print("AZURE_OPENAI_API_VERSION=2024-02-15-preview")
    print("USE_AZURE_OPENAI=true")
    print("\n💡 Tips:")
    print("- Get your API key from Azure Portal > Cognitive Services > Your OpenAI Resource")
    print("- Endpoint should end with .openai.azure.com/")
    print("- Deployment name is what you named your model deployment in Azure")

if __name__ == "__main__":
    print("AI Web CTF Solver - Azure OpenAI Setup")
    print("Choose an option:")
    print("1. Configure Azure OpenAI (interactive)")
    print("2. Show configuration example")
    print("3. Test existing configuration")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        setup_azure_openai()
    elif choice == "2":
        show_config_example()
    elif choice == "3":
        # Load existing config and test
        from dotenv import load_dotenv
        load_dotenv()
        
        azure_settings = {
            'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY'),
            'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'AZURE_OPENAI_DEPLOYMENT_NAME': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            'AZURE_OPENAI_API_VERSION': os.getenv('AZURE_OPENAI_API_VERSION')
        }
        
        if all(azure_settings.values()):
            test_azure_openai_config(azure_settings)
        else:
            print("❌ Azure OpenAI configuration not found in .env file")
            print("Run option 1 to configure Azure OpenAI")
    else:
        print("Invalid choice. Exiting.")