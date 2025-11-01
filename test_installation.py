#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Web CTF Solver - Installation Test Script
Tests all dependencies and configurations
"""

def test_imports():
    """Test all required imports"""
    print("🧪 Testing Python imports...")
    
    failed_imports = []
    
    # Test core dependencies
    try:
        import langchain
        print("✅ langchain")
    except ImportError as e:
        failed_imports.append(f"langchain: {e}")
        print("❌ langchain")
    
    try:
        import langchain_openai
        print("✅ langchain_openai")
    except ImportError as e:
        failed_imports.append(f"langchain_openai: {e}")
        print("❌ langchain_openai")
    
    try:
        import langgraph
        print("✅ langgraph")
    except ImportError as e:
        failed_imports.append(f"langgraph: {e}")
        print("❌ langgraph")
    
    try:
        import fastapi
        print("✅ fastapi")
    except ImportError as e:
        failed_imports.append(f"fastapi: {e}")
        print("❌ fastapi")
    
    try:
        import requests
        print("✅ requests")
    except ImportError as e:
        failed_imports.append(f"requests: {e}")
        print("❌ requests")
    
    try:
        import pydantic
        print("✅ pydantic")
    except ImportError as e:
        failed_imports.append(f"pydantic: {e}")
        print("❌ pydantic")
    
    # Optional imports
    try:
        import selenium
        print("✅ selenium (optional)")
    except ImportError:
        print("⚠️  selenium (optional - not installed)")
    
    try:
        import bs4
        print("✅ beautifulsoup4 (as bs4)")
    except ImportError as e:
        failed_imports.append(f"beautifulsoup4: {e}")
        print("❌ beautifulsoup4")
    
    return failed_imports

def test_langchain_compatibility():
    """Test LangChain compatibility"""
    print("\n🔗 Testing LangChain compatibility...")
    
    try:
        # Test new import structure
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.messages import HumanMessage
        print("✅ LangChain core imports (new structure)")
        return True
    except ImportError:
        try:
            # Test old import structure (dynamic import to avoid linter errors)
            langchain_prompts = __import__('langchain.prompts', fromlist=['ChatPromptTemplate'])
            langchain_schema = __import__('langchain.schema', fromlist=['HumanMessage'])
            print("✅ LangChain imports (legacy structure)")
            return True
        except ImportError as e:
            print(f"❌ LangChain imports failed: {e}")
            return False

def test_azure_openai_support():
    """Test Azure OpenAI support"""
    print("\n☁️  Testing Azure OpenAI support...")
    
    try:
        from langchain_openai import AzureChatOpenAI
        print("✅ Azure OpenAI support available")
        return True
    except ImportError as e:
        print(f"❌ Azure OpenAI support not available: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\n⚙️  Testing configuration...")
    
    try:
        import sys
        from pathlib import Path
        
        # Add src to path
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root / "src"))
        
        from src.utils.config import get_config
        config = get_config()
        print("✅ Configuration module loaded")
        
        # Check for .env file
        env_file = project_root / ".env"
        if env_file.exists():
            print("✅ .env file found")
        else:
            print("⚠️  .env file not found (copy from .env.example)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    """Run all tests"""
    print("AI Web CTF Solver - Installation Test")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    failed_imports = test_imports()
    if failed_imports:
        all_passed = False
        print(f"\n❌ {len(failed_imports)} import failures:")
        for failure in failed_imports:
            print(f"   • {failure}")
    
    # Test LangChain compatibility
    if not test_langchain_compatibility():
        all_passed = False
    
    # Test Azure OpenAI support
    test_azure_openai_support()  # Non-critical
    
    # Test configuration
    if not test_configuration():
        all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All core tests passed!")
        print("You can now run the AI Web CTF Solver with: python main.py")
    else:
        print("❌ Some tests failed. Please install missing dependencies:")
        print("   pip install --upgrade pip setuptools wheel")
        print("   pip install -r requirements-minimal.txt")
    
    print("\n💡 Troubleshooting:")
    print("   • If imports fail: pip install -r requirements-minimal.txt")
    print("   • For Azure OpenAI: python setup_azure.py")
    print("   • For full features: pip install -r requirements.txt")

if __name__ == "__main__":
    main()