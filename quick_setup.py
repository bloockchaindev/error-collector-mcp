#!/usr/bin/env python3
"""
Error Collector MCP - Quick Setup Script (Simplified)
Simple setup script for users who already have the package installed.
"""

import os
import sys
import json
from pathlib import Path

def print_banner():
    print("""
🚀 Error Collector MCP - Quick Setup

This script will help you configure Error Collector MCP in 2 minutes!
""")

def setup_environment():
    """Set up environment variables."""
    print("📝 Setting up environment variables...")
    
    # Check if .env already exists
    if Path('.env').exists():
        print("✅ .env file already exists")
        use_existing = input("Use existing .env file? (y/n): ").lower().strip()
        if use_existing in ['y', 'yes', '']:
            return True
    
    # Get API key
    print("\n🔑 OpenRouter API Key Setup")
    print("Get your free API key at: https://openrouter.ai/")
    
    api_key = input("Enter your OpenRouter API key: ").strip()
    
    if not api_key:
        print("⚠️  Skipping API key setup - you can add it later to .env")
        api_key = "your-api-key-here"
    
    # Create .env file
    env_content = f"""# Error Collector MCP Environment Variables
OPENROUTER_API_KEY={api_key}

# Optional customizations:
# ERROR_COLLECTOR_DATA_DIR=/custom/data/path
# ERROR_COLLECTOR_SERVER__LOG_LEVEL=INFO
# ERROR_COLLECTOR_SERVER__PORT=8000
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Environment file created: .env")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env: {e}")
        return False

def setup_kiro_integration():
    """Set up Kiro MCP integration."""
    print("\n🔌 Kiro Integration Setup")
    setup = input("Set up Kiro MCP integration? (y/n): ").lower().strip()
    
    if setup not in ['y', 'yes']:
        return False
    
    try:
        kiro_dir = Path('.kiro/settings')
        kiro_dir.mkdir(parents=True, exist_ok=True)
        
        mcp_config = {
            "mcpServers": {
                "error-collector": {
                    "command": "error-collector-mcp",
                    "args": ["serve"],
                    "autoApprove": [
                        "get_server_status",
                        "health_check",
                        "query_errors",
                        "get_error_statistics"
                    ]
                }
            }
        }
        
        mcp_file = kiro_dir / 'mcp.json'
        with open(mcp_file, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        print(f"✅ Kiro integration configured: {mcp_file}")
        return True
        
    except Exception as e:
        print(f"❌ Kiro integration failed: {e}")
        return False

def test_configuration():
    """Test the configuration."""
    print("\n🧪 Testing configuration...")
    
    try:
        # Test import
        from error_collector_mcp.services.config_service import ConfigService
        print("✅ Package import successful")
        
        # Test config loading
        import asyncio
        
        async def test_config():
            config_service = ConfigService()
            config = await config_service.load_config('config.json')
            return config
        
        config = asyncio.run(test_config())
        print("✅ Configuration loaded successfully")
        print(f"   Model: {config.openrouter.model}")
        print(f"   Data directory: {config.storage.data_directory}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def print_next_steps():
    """Print next steps for the user."""
    print("""
🎉 Setup Complete!

Next steps:
1. Start the server:
   error-collector-mcp serve

2. Test the server:
   curl http://localhost:8000/health

3. Optional integrations:
   • Browser extension: error-collector-mcp build-browser-extension chrome
   • Terminal integration: error-collector-mcp install-shell-integration

4. Documentation:
   • README.md - Overview and features
   • SETUP.md - Detailed setup guide
   • DEPLOYMENT.md - Production deployment

Happy error collecting! 🐛➡️🤖
""")

def main():
    """Main setup function."""
    try:
        print_banner()
        
        # Setup environment
        if not setup_environment():
            print("❌ Environment setup failed")
            return False
        
        # Setup Kiro integration
        setup_kiro_integration()
        
        # Test configuration
        if not test_configuration():
            print("⚠️  Configuration test failed, but you can try running manually")
        
        # Print next steps
        print_next_steps()
        
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)