"""Main entry point for the Error Collector MCP server."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from .services.config_service import ConfigService


def setup_logging(log_level: str) -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("error-collector-mcp.log")
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Error Collector MCP Server"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override log level from config"
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Shell integration command
    shell_parser = subparsers.add_parser(
        "install-shell-integration",
        help="Install shell integration for error collection"
    )
    shell_parser.add_argument(
        "shell",
        choices=["bash", "zsh", "fish", "auto"],
        default="auto",
        nargs="?",
        help="Shell to install integration for"
    )
    
    # Browser extension command
    extension_parser = subparsers.add_parser(
        "build-browser-extension",
        help="Build browser extension for error collection"
    )
    extension_parser.add_argument(
        "browser",
        choices=["chrome", "firefox", "all"],
        default="all",
        nargs="?",
        help="Browser to build extension for"
    )
    extension_parser.add_argument(
        "--output-dir",
        type=str,
        default="./browser-extensions",
        help="Output directory for extensions"
    )
    extension_parser.add_argument(
        "--package",
        action="store_true",
        help="Create packaged extension files"
    )
    
    # MCP server command
    server_parser = subparsers.add_parser(
        "serve",
        help="Run the MCP server"
    )
    server_parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory for storage (default: ~/.error-collector-mcp)"
    )
    
    return parser.parse_args()


async def main() -> None:
    """Main application entry point."""
    args = parse_args()
    
    # Handle shell integration command
    if args.command == "install-shell-integration":
        from .collectors.shell_wrapper import ShellWrapper
        wrapper = ShellWrapper()
        try:
            install_path = wrapper.install_shell_integration(args.shell)
            print(f"Shell integration installed to: {install_path}")
            print("Please restart your terminal or source your shell configuration file.")
            print(f"Log file location: {wrapper.log_file}")
        except Exception as e:
            print(f"Installation failed: {e}")
            sys.exit(1)
        return
    
    # Handle browser extension command
    if args.command == "build-browser-extension":
        from .collectors.browser_extension import BrowserExtensionBuilder
        builder = BrowserExtensionBuilder()
        output_dir = Path(args.output_dir)
        
        try:
            if args.browser in ["chrome", "all"]:
                chrome_dir = builder.build_chrome_extension(output_dir / "chrome")
                print(f"Chrome extension built in: {chrome_dir}")
                
                if args.package:
                    package_file = output_dir / "error-collector-mcp-chrome.zip"
                    builder.create_extension_package(chrome_dir, package_file)
                    print(f"Chrome extension packaged: {package_file}")
            
            if args.browser in ["firefox", "all"]:
                firefox_dir = builder.build_firefox_extension(output_dir / "firefox")
                print(f"Firefox extension built in: {firefox_dir}")
                
                if args.package:
                    package_file = output_dir / "error-collector-mcp-firefox.zip"
                    builder.create_extension_package(firefox_dir, package_file)
                    print(f"Firefox extension packaged: {package_file}")
            
            print("\nInstallation instructions:")
            print("Chrome: Go to chrome://extensions/, enable Developer mode, click 'Load unpacked'")
            print("Firefox: Go to about:debugging, click 'This Firefox', click 'Load Temporary Add-on'")
            
        except Exception as e:
            print(f"Extension build failed: {e}")
            sys.exit(1)
        return
    
    # Handle MCP server command
    if args.command == "serve":
        # Use the FastMCP server implementation
        from .server import main as server_main
        import os
        
        # Set environment variables for server configuration
        os.environ["ERROR_COLLECTOR_CONFIG"] = args.config
        if args.data_dir:
            os.environ["ERROR_COLLECTOR_DATA_DIR"] = args.data_dir
        
        try:
            server_main()
        except Exception as e:
            print(f"MCP server failed: {e}")
            sys.exit(1)
        return
    
    # Load configuration
    config_service = ConfigService()
    try:
        config = await config_service.load_config(args.config)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Set up logging
    log_level = args.log_level or config.server.log_level.value
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Error Collector MCP Server")
    logger.info(f"Configuration loaded from: {args.config}")
    
    # TODO: Initialize and start the MCP server
    # This will be implemented in later tasks
    logger.info("MCP server initialization not yet implemented")
    logger.info("Server would start on %s:%d", config.server.host, config.server.port)


def cli_main() -> None:
    """CLI entry point wrapper."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()