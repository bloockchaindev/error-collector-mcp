#!/usr/bin/env python3
"""
Repository setup script for Error Collector MCP.

This script helps initialize the repository for development or deployment.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        print(f"✅ {' '.join(cmd)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {' '.join(cmd)}")
        print(f"   Error: {e.stderr.strip()}")
        return False


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def setup_development_environment() -> bool:
    """Set up the development environment."""
    print("\n🔧 Setting up development environment...")
    
    # Install package in development mode
    if not run_command([sys.executable, "-m", "pip", "install", "-e", ".[dev]"]):
        return False
    
    # Install pre-commit hooks
    if not run_command(["pre-commit", "install"]):
        print("⚠️  Pre-commit hooks installation failed (optional)")
    
    return True


def create_configuration(api_key: Optional[str] = None) -> bool:
    """Create initial configuration files."""
    print("\n⚙️  Creating configuration...")
    
    config_path = Path("config.json")
    if config_path.exists():
        print(f"⚠️  {config_path} already exists, skipping")
        return True
    
    # Use minimal config as base
    minimal_config_path = Path("config.minimal.json")
    if not minimal_config_path.exists():
        print(f"❌ {minimal_config_path} not found")
        return False
    
    with open(minimal_config_path) as f:
        config = json.load(f)
    
    # Set API key if provided
    if api_key:
        config["openrouter"]["api_key"] = api_key
        print("✅ OpenRouter API key configured")
    else:
        print("⚠️  No OpenRouter API key provided - you'll need to set it manually")
    
    # Write configuration
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Created {config_path}")
    return True


def run_tests() -> bool:
    """Run the test suite."""
    print("\n🧪 Running tests...")
    return run_command([sys.executable, "-m", "pytest", "-v"])


def check_code_quality() -> bool:
    """Check code quality with linting tools."""
    print("\n🔍 Checking code quality...")
    
    success = True
    
    # Check formatting
    if not run_command(["black", "--check", "."]):
        print("   Run 'black .' to fix formatting")
        success = False
    
    # Check import sorting
    if not run_command(["isort", "--check-only", "."]):
        print("   Run 'isort .' to fix import sorting")
        success = False
    
    # Type checking
    if not run_command(["mypy", "error_collector_mcp/"]):
        success = False
    
    return success


def setup_git_hooks() -> bool:
    """Set up git hooks for development."""
    print("\n🪝 Setting up git hooks...")
    
    # Check if we're in a git repository
    if not Path(".git").exists():
        print("⚠️  Not in a git repository, skipping git hooks")
        return True
    
    # Install pre-commit hooks
    return run_command(["pre-commit", "install"])


def validate_installation() -> bool:
    """Validate that the installation is working."""
    print("\n✅ Validating installation...")
    
    # Check if the CLI is available
    if not run_command(["error-collector-mcp", "--help"]):
        return False
    
    # Check if we can import the package
    try:
        import error_collector_mcp
        print("✅ Package import successful")
    except ImportError as e:
        print(f"❌ Package import failed: {e}")
        return False
    
    return True


def setup_kiro_integration() -> bool:
    """Set up Kiro integration if requested."""
    print("\n🎯 Setting up Kiro integration...")
    
    kiro_setup_script = Path("setup_kiro_integration.py")
    if not kiro_setup_script.exists():
        print(f"❌ {kiro_setup_script} not found")
        return False
    
    return run_command([sys.executable, str(kiro_setup_script)])


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(
        description="Set up Error Collector MCP repository"
    )
    parser.add_argument(
        "--dev", action="store_true", help="Set up development environment"
    )
    parser.add_argument(
        "--api-key", help="OpenRouter API key for configuration"
    )
    parser.add_argument(
        "--kiro", action="store_true", help="Set up Kiro integration"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run tests after setup"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check code quality"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all setup steps"
    )
    
    args = parser.parse_args()
    
    print("🚀 Error Collector MCP Repository Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    success = True
    
    # Development setup
    if args.dev or args.all:
        success &= setup_development_environment()
        success &= setup_git_hooks()
    
    # Configuration
    if args.api_key or args.all:
        success &= create_configuration(args.api_key)
    
    # Kiro integration
    if args.kiro or args.all:
        success &= setup_kiro_integration()
    
    # Validation
    if args.dev or args.all:
        success &= validate_installation()
    
    # Testing
    if args.test or args.all:
        success &= run_tests()
    
    # Code quality
    if args.check or args.all:
        success &= check_code_quality()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        if not args.api_key and not args.all:
            print("1. Set your OpenRouter API key in config.json")
        print("2. Start the server: error-collector-mcp serve")
        print("3. Check the QUICK_START.md for usage instructions")
    else:
        print("❌ Setup completed with errors")
        print("Please check the error messages above and try again")
        sys.exit(1)


if __name__ == "__main__":
    main()