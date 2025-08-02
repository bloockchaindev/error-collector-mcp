#!/usr/bin/env python3
"""
Error Collector MCP - Quick Setup Script
Interactive setup script to get you up and running in under 2 minutes.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import json

# ANSI color codes for pretty output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header():
    """Print the setup header."""
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           🚀 Error Collector MCP - Quick Setup              ║
║                                                              ║
║     Get up and running with AI-powered error collection     ║
║                    in under 2 minutes!                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.BOLD}What this script will do:{Colors.END}
✅ Check system requirements
✅ Install dependencies (if needed)
✅ Set up environment variables
✅ Configure OpenRouter API
✅ Test the installation
✅ Start the MCP server

{Colors.YELLOW}Let's get started!{Colors.END}
""")

def check_python_version() -> bool:
    """Check if Python version is compatible."""
    print(f"{Colors.BLUE}🔍 Checking Python version...{Colors.END}")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"{Colors.GREEN}✅ Python {version.major}.{version.minor}.{version.micro} - Compatible!{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.9+{Colors.END}")
        print(f"{Colors.YELLOW}Please upgrade Python and try again.{Colors.END}")
        return False

def check_pip() -> bool:
    """Check if pip is available."""
    print(f"{Colors.BLUE}🔍 Checking pip...{Colors.END}")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print(f"{Colors.GREEN}✅ pip is available{Colors.END}")
        return True
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}❌ pip not found{Colors.END}")
        return False

def install_package() -> bool:
    """Install the error-collector-mcp package."""
    print(f"{Colors.BLUE}📦 Installing Error Collector MCP...{Colors.END}")
    
    # Check if already installed
    try:
        import error_collector_mcp
        print(f"{Colors.GREEN}✅ Package already installed{Colors.END}")
        return True
    except ImportError:
        pass
    
    try:
        # Check if we're in the source directory
        if Path("pyproject.toml").exists() and Path("error_collector_mcp").exists():
            print(f"{Colors.CYAN}📁 Installing from source directory...{Colors.END}")
            # Set environment variable to prevent recursive setup calls
            env = os.environ.copy()
            env['SKIP_SETUP_SCRIPT'] = '1'
            result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                                  capture_output=True, text=True, env=env)
        else:
            print(f"{Colors.CYAN}🌐 Installing from PyPI...{Colors.END}")
            result = subprocess.run([sys.executable, "-m", "pip", "install", "error-collector-mcp"], 
                                  capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Installation successful!{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ Installation failed:{Colors.END}")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ Installation error: {e}{Colors.END}")
        return False

def get_openrouter_api_key() -> Optional[str]:
    """Get OpenRouter API key from user."""
    print(f"\n{Colors.BLUE}🔑 OpenRouter API Key Setup{Colors.END}")
    print(f"{Colors.CYAN}You need a free OpenRouter API key for AI-powered error summarization.{Colors.END}")
    print(f"{Colors.YELLOW}📖 Get your free key at: https://openrouter.ai/{Colors.END}")
    
    # Check if already set in environment
    existing_key = os.getenv('OPENROUTER_API_KEY')
    if existing_key:
        print(f"{Colors.GREEN}✅ Found existing API key in environment{Colors.END}")
        use_existing = input(f"{Colors.CYAN}Use existing key? (y/n): {Colors.END}").lower().strip()
        if use_existing in ['y', 'yes', '']:
            return existing_key
    
    while True:
        api_key = input(f"{Colors.CYAN}Enter your OpenRouter API key: {Colors.END}").strip()
        
        if not api_key:
            print(f"{Colors.YELLOW}⚠️  API key is required for AI summarization{Colors.END}")
            skip = input(f"{Colors.CYAN}Skip for now? (y/n): {Colors.END}").lower().strip()
            if skip in ['y', 'yes']:
                return None
            continue
        
        if api_key.startswith('sk-or-v1-') and len(api_key) > 20:
            print(f"{Colors.GREEN}✅ API key looks valid{Colors.END}")
            return api_key
        else:
            print(f"{Colors.YELLOW}⚠️  API key should start with 'sk-or-v1-' and be longer{Colors.END}")
            continue

def create_env_file(api_key: Optional[str]) -> bool:
    """Create .env file with configuration."""
    print(f"{Colors.BLUE}📝 Creating environment configuration...{Colors.END}")
    
    env_content = f"""# Error Collector MCP - Environment Variables
# Generated by setup script on {os.popen('date').read().strip()}

# OpenRouter API Key (REQUIRED for AI summarization)
OPENROUTER_API_KEY={api_key or 'your-api-key-here'}

# Optional: Customize data directory
# ERROR_COLLECTOR_DATA_DIR=/custom/data/path

# Optional: Change log level (DEBUG, INFO, WARNING, ERROR)
# ERROR_COLLECTOR_SERVER__LOG_LEVEL=INFO

# Optional: Change server port
# ERROR_COLLECTOR_SERVER__PORT=8000
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print(f"{Colors.GREEN}✅ Environment file created: .env{Colors.END}")
        
        if not api_key:
            print(f"{Colors.YELLOW}⚠️  Remember to add your API key to .env later{Colors.END}")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ Failed to create .env file: {e}{Colors.END}")
        return False

def test_installation() -> bool:
    """Test that the installation works."""
    print(f"{Colors.BLUE}🧪 Testing installation...{Colors.END}")
    
    try:
        # Test import
        result = subprocess.run([
            sys.executable, "-c", 
            "from error_collector_mcp.services.config_service import ConfigService; print('✅ Import successful')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Package import successful{Colors.END}")
        else:
            print(f"{Colors.RED}❌ Package import failed:{Colors.END}")
            print(result.stderr)
            return False
        
        # Test CLI command
        result = subprocess.run([
            sys.executable, "-m", "error_collector_mcp.main", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ CLI command available{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ CLI command failed:{Colors.END}")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}❌ Test timed out{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Test error: {e}{Colors.END}")
        return False

def setup_integrations() -> Dict[str, bool]:
    """Set up optional integrations."""
    print(f"\n{Colors.BLUE}🔌 Optional Integrations{Colors.END}")
    
    integrations = {}
    
    # Kiro integration
    print(f"{Colors.CYAN}📝 Kiro IDE Integration{Colors.END}")
    setup_kiro = input(f"{Colors.CYAN}Set up Kiro MCP integration? (y/n): {Colors.END}").lower().strip()
    
    if setup_kiro in ['y', 'yes']:
        integrations['kiro'] = setup_kiro_integration()
    else:
        integrations['kiro'] = False
    
    # Browser extension
    print(f"{Colors.CYAN}🌐 Browser Extension{Colors.END}")
    setup_browser = input(f"{Colors.CYAN}Build browser extension for error collection? (y/n): {Colors.END}").lower().strip()
    
    if setup_browser in ['y', 'yes']:
        integrations['browser'] = build_browser_extension()
    else:
        integrations['browser'] = False
    
    # Terminal integration
    print(f"{Colors.CYAN}💻 Terminal Integration{Colors.END}")
    setup_terminal = input(f"{Colors.CYAN}Install shell integration for terminal errors? (y/n): {Colors.END}").lower().strip()
    
    if setup_terminal in ['y', 'yes']:
        integrations['terminal'] = install_shell_integration()
    else:
        integrations['terminal'] = False
    
    return integrations

def setup_kiro_integration() -> bool:
    """Set up Kiro MCP integration."""
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
        
        print(f"{Colors.GREEN}✅ Kiro integration configured: {mcp_file}{Colors.END}")
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ Kiro integration failed: {e}{Colors.END}")
        return False

def build_browser_extension() -> bool:
    """Build browser extension."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "error_collector_mcp.main", 
            "build-browser-extension", "chrome", "--package"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Browser extension built successfully{Colors.END}")
            print(f"{Colors.CYAN}📁 Extension location: browser-extensions/chrome/{Colors.END}")
            print(f"{Colors.YELLOW}📖 Install: Go to chrome://extensions/, enable Developer mode, click 'Load unpacked'{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ Browser extension build failed:{Colors.END}")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}❌ Browser extension build timed out{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Browser extension error: {e}{Colors.END}")
        return False

def install_shell_integration() -> bool:
    """Install shell integration."""
    try:
        # Detect shell
        shell = os.getenv('SHELL', '').split('/')[-1]
        if not shell:
            shell = 'bash'  # default
        
        result = subprocess.run([
            sys.executable, "-m", "error_collector_mcp.main", 
            "install-shell-integration", shell
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Shell integration installed for {shell}{Colors.END}")
            print(f"{Colors.YELLOW}🔄 Please restart your terminal or run: source ~/.{shell}rc{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ Shell integration failed:{Colors.END}")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"{Colors.RED}❌ Shell integration timed out{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Shell integration error: {e}{Colors.END}")
        return False

def start_server() -> bool:
    """Start the MCP server."""
    print(f"\n{Colors.BLUE}🚀 Starting Error Collector MCP Server...{Colors.END}")
    
    start_now = input(f"{Colors.CYAN}Start the server now? (y/n): {Colors.END}").lower().strip()
    
    if start_now not in ['y', 'yes']:
        print(f"{Colors.YELLOW}📝 To start later, run: error-collector-mcp serve{Colors.END}")
        return True
    
    try:
        print(f"{Colors.CYAN}🔄 Starting server... (Press Ctrl+C to stop){Colors.END}")
        
        # Start server in background for testing
        process = subprocess.Popen([
            sys.executable, "-m", "error_collector_mcp.server"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment to see if it starts successfully
        import time
        time.sleep(3)
        
        if process.poll() is None:
            print(f"{Colors.GREEN}✅ Server started successfully!{Colors.END}")
            print(f"{Colors.CYAN}🌐 Server running on http://localhost:8000{Colors.END}")
            
            # Ask if user wants to keep it running
            keep_running = input(f"{Colors.CYAN}Keep server running in background? (y/n): {Colors.END}").lower().strip()
            
            if keep_running not in ['y', 'yes']:
                process.terminate()
                process.wait()
                print(f"{Colors.YELLOW}🛑 Server stopped{Colors.END}")
            else:
                print(f"{Colors.GREEN}🎉 Server running in background (PID: {process.pid}){Colors.END}")
                print(f"{Colors.YELLOW}💡 To stop: kill {process.pid}{Colors.END}")
            
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"{Colors.RED}❌ Server failed to start:{Colors.END}")
            if stderr:
                print(stderr.decode())
            return False
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Server startup cancelled{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}❌ Server startup error: {e}{Colors.END}")
        return False

def print_success_summary(integrations: Dict[str, bool]):
    """Print setup success summary."""
    print(f"""
{Colors.GREEN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║            🎉 Setup Complete! You're ready to go!           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.BOLD}✅ What's been set up:{Colors.END}
• Error Collector MCP package installed
• Environment variables configured (.env)
• Configuration validated
""")
    
    if integrations.get('kiro'):
        print("• Kiro IDE integration configured")
    if integrations.get('browser'):
        print("• Browser extension built")
    if integrations.get('terminal'):
        print("• Terminal integration installed")
    
    print(f"""
{Colors.BOLD}🚀 Quick Commands:{Colors.END}
• Start server: {Colors.CYAN}error-collector-mcp serve{Colors.END}
• Check status: {Colors.CYAN}curl http://localhost:8000/health{Colors.END}
• View logs: {Colors.CYAN}tail -f ~/.error-collector-mcp/logs/server.log{Colors.END}

{Colors.BOLD}📚 Next Steps:{Colors.END}
• Read the docs: {Colors.CYAN}README.md{Colors.END}
• Configure advanced settings: {Colors.CYAN}config.json{Colors.END}
• Set up more integrations: {Colors.CYAN}SETUP.md{Colors.END}

{Colors.BOLD}🆘 Need Help?{Colors.END}
• Documentation: https://error-collector-mcp.readthedocs.io/
• Issues: https://github.com/error-collector-mcp/error-collector-mcp/issues

{Colors.GREEN}Happy error collecting! 🐛➡️🤖{Colors.END}
""")

def main():
    """Main setup function."""
    # Prevent recursive execution during pip install
    if os.getenv('SKIP_SETUP_SCRIPT'):
        print("Skipping setup script (running from pip install)")
        return
    
    try:
        print_header()
        
        # System checks
        if not check_python_version():
            sys.exit(1)
        
        if not check_pip():
            sys.exit(1)
        
        # Installation
        if not install_package():
            sys.exit(1)
        
        # Configuration
        api_key = get_openrouter_api_key()
        
        if not create_env_file(api_key):
            sys.exit(1)
        
        # Testing
        if not test_installation():
            print(f"{Colors.YELLOW}⚠️  Installation test failed, but you can try running manually{Colors.END}")
        
        # Optional integrations
        integrations = setup_integrations()
        
        # Start server
        start_server()
        
        # Success summary
        print_success_summary(integrations)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Setup cancelled by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Setup failed: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()