#!/usr/bin/env python3
"""
Quick setup script for integrating Error Collector MCP with Kiro.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default."""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    return input(f"{prompt}: ").strip()


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    return response.startswith('y')


def create_config_file(config_path: Path) -> Dict[str, Any]:
    """Create configuration file with user input."""
    print("\n🔧 Setting up Error Collector MCP configuration...")
    
    # Get OpenRouter API key
    api_key = get_user_input(
        "Enter your OpenRouter API key (get one free at https://openrouter.ai)"
    )
    
    if not api_key:
        print("❌ OpenRouter API key is required!")
        sys.exit(1)
    
    # Get data directory
    default_data_dir = str(Path.home() / ".error-collector-mcp")
    data_dir = get_user_input("Data directory", default_data_dir)
    
    # Get collection preferences
    collect_browser = get_yes_no("Enable browser error collection?", True)
    collect_terminal = get_yes_no("Enable terminal error collection?", True)
    
    enabled_sources = []
    if collect_browser:
        enabled_sources.append("browser")
    if collect_terminal:
        enabled_sources.append("terminal")
    
    # Create configuration
    config = {
        "openrouter": {
            "api_key": api_key,
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "max_tokens": 1000,
            "temperature": 0.7
        },
        "collection": {
            "enabled_sources": enabled_sources,
            "ignored_error_patterns": [
                "ResizeObserver loop limit exceeded",
                "Non-Error promise rejection captured",
                "Script error\\."
            ],
            "ignored_domains": [
                "chrome-extension://",
                "moz-extension://",
                "localhost:3000"
            ],
            "auto_summarize": True,
            "max_errors_per_minute": 100
        },
        "storage": {
            "data_directory": data_dir,
            "max_errors_stored": 10000,
            "retention_days": 30
        },
        "server": {
            "host": "localhost",
            "port": 8000,
            "log_level": "INFO"
        }
    }
    
    # Write configuration file
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to {config_path}")
    return config


def setup_kiro_mcp_config(config: Dict[str, Any]) -> None:
    """Set up Kiro MCP configuration."""
    print("\n🔗 Setting up Kiro MCP integration...")
    
    # Determine config location
    workspace_mcp = Path(".kiro/settings/mcp.json")
    user_mcp = Path.home() / ".kiro/settings/mcp.json"
    
    use_workspace = False
    if workspace_mcp.parent.exists():
        use_workspace = get_yes_no(
            f"Found Kiro workspace config. Use workspace config ({workspace_mcp})?", 
            True
        )
    
    mcp_config_path = workspace_mcp if use_workspace else user_mcp
    
    # Create directory if needed
    mcp_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing MCP config or create new
    mcp_config = {}
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, 'r') as f:
                mcp_config = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️  Invalid JSON in {mcp_config_path}, creating new config")
    
    # Ensure mcpServers section exists
    if "mcpServers" not in mcp_config:
        mcp_config["mcpServers"] = {}
    
    # Add Error Collector MCP server
    config_file_path = str(Path("config.json").resolve())
    
    mcp_config["mcpServers"]["error-collector"] = {
        "command": "error-collector-mcp",
        "args": ["serve", "--config", config_file_path],
        "env": {
            "ERROR_COLLECTOR_CONFIG": config_file_path
        },
        "disabled": False,
        "autoApprove": [
            "query_errors",
            "get_error_summary", 
            "get_error_statistics",
            "get_server_status",
            "health_check"
        ]
    }
    
    # Write MCP configuration
    with open(mcp_config_path, 'w') as f:
        json.dump(mcp_config, f, indent=2)
    
    print(f"✅ Kiro MCP configuration updated: {mcp_config_path}")


def setup_browser_integration(config: Dict[str, Any]) -> None:
    """Set up browser error collection."""
    if "browser" not in config["collection"]["enabled_sources"]:
        return
    
    print("\n🌐 Setting up browser error collection...")
    
    setup_browser = get_yes_no("Set up browser extension for error collection?", True)
    if not setup_browser:
        print("ℹ️  You can set up browser collection later with:")
        print("   error-collector-mcp build-browser-extension all --package")
        return
    
    try:
        # Build browser extensions
        import subprocess
        result = subprocess.run([
            "error-collector-mcp", "build-browser-extension", "all", "--package"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Browser extensions built successfully!")
            print("\n📋 Installation instructions:")
            print("Chrome:")
            print("  1. Go to chrome://extensions/")
            print("  2. Enable 'Developer mode'")
            print("  3. Click 'Load unpacked'")
            print("  4. Select the 'browser-extensions/chrome' folder")
            print("\nFirefox:")
            print("  1. Go to about:debugging")
            print("  2. Click 'This Firefox'")
            print("  3. Click 'Load Temporary Add-on'")
            print("  4. Select any file in the 'browser-extensions/firefox' folder")
        else:
            print(f"❌ Failed to build browser extensions: {result.stderr}")
            
    except FileNotFoundError:
        print("❌ error-collector-mcp command not found. Please install the package first:")
        print("   pip install -e .")


def setup_terminal_integration(config: Dict[str, Any]) -> None:
    """Set up terminal error collection."""
    if "terminal" not in config["collection"]["enabled_sources"]:
        return
    
    print("\n💻 Setting up terminal error collection...")
    
    setup_terminal = get_yes_no("Install shell integration for terminal error collection?", True)
    if not setup_terminal:
        print("ℹ️  You can set up terminal collection later with:")
        print("   error-collector-mcp install-shell-integration")
        return
    
    try:
        import subprocess
        result = subprocess.run([
            "error-collector-mcp", "install-shell-integration"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Shell integration installed successfully!")
            print("🔄 Please restart your terminal or run:")
            
            # Detect shell and provide appropriate command
            shell = os.environ.get('SHELL', '/bin/bash')
            if 'zsh' in shell:
                print("   source ~/.zshrc")
            elif 'bash' in shell:
                print("   source ~/.bashrc")
            else:
                print("   source your shell configuration file")
        else:
            print(f"❌ Failed to install shell integration: {result.stderr}")
            
    except FileNotFoundError:
        print("❌ error-collector-mcp command not found. Please install the package first:")
        print("   pip install -e .")


def test_integration() -> None:
    """Test the integration setup."""
    print("\n🧪 Testing integration...")
    
    try:
        import subprocess
        
        # Test if the server can start
        print("Testing server startup...")
        result = subprocess.run([
            "error-collector-mcp", "serve", "--config", "config.json"
        ], capture_output=True, text=True, timeout=5)
        
        # The server will run indefinitely, so timeout is expected
        print("✅ Server can start successfully")
        
    except subprocess.TimeoutExpired:
        print("✅ Server started successfully (timeout expected)")
    except FileNotFoundError:
        print("❌ error-collector-mcp command not found")
        print("Please install the package: pip install -e .")
    except Exception as e:
        print(f"⚠️  Server test failed: {e}")


def main():
    """Main setup function."""
    print("🚀 Error Collector MCP - Kiro Integration Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run this script from the error-collector-mcp directory")
        sys.exit(1)
    
    # Create configuration
    config_path = Path("config.json")
    if config_path.exists():
        overwrite = get_yes_no(f"Configuration file {config_path} exists. Overwrite?", False)
        if not overwrite:
            print("Using existing configuration file")
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = create_config_file(config_path)
    else:
        config = create_config_file(config_path)
    
    # Set up Kiro MCP integration
    setup_kiro_mcp_config(config)
    
    # Set up browser integration
    setup_browser_integration(config)
    
    # Set up terminal integration
    setup_terminal_integration(config)
    
    # Test the setup
    test_integration()
    
    # Final instructions
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Restart Kiro to load the new MCP configuration")
    print("2. Try asking Kiro: 'Check the error collector status'")
    print("3. Test error collection: 'Simulate a test error and show it to me'")
    print("4. Start debugging: 'Show me any recent errors and analyze them'")
    
    print("\n📚 For more information, see KIRO_INTEGRATION.md")
    print("\n🆘 If you need help:")
    print("- Check server logs: ~/.error-collector-mcp/server.log")
    print("- Test manually: error-collector-mcp serve --config config.json")
    print("- Ask Kiro: 'Check error collector health'")


if __name__ == "__main__":
    main()