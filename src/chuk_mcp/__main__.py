# chuk_mcp/__main__.py
"""
Chuk MCP Command Line Interface

A development and testing utility for working with MCP servers. This CLI provides
quick connectivity testing, protocol exploration, and debugging capabilities.

Usage:
    python -m chuk_mcp                    # Test default server
    python -m chuk_mcp --config path.json # Use custom config
    python -m chuk_mcp --server name      # Test specific server
    python -m chuk_mcp --list-servers     # Show available servers
    python -m chuk_mcp --verbose          # Enable detailed logging
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import anyio

# Import from our package - updated to use new structure
from chuk_mcp.config import load_config
from chuk_mcp.transports.stdio import stdio_client
from chuk_mcp.protocol.messages import (
    send_initialize,
    send_ping,
    send_tools_list,
    send_resources_list,
    send_prompts_list,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        if verbose
        else "%(levelname)s: %(message)s"
    )

    logging.basicConfig(level=level, format=format_str, stream=sys.stderr)

    # Reduce noise from anyio in non-verbose mode
    if not verbose:
        logging.getLogger("anyio").setLevel(logging.WARNING)


def find_default_config() -> Optional[str]:
    """Find a default configuration file in common locations."""
    possible_paths = [
        "server_config.json",
        "mcp_config.json",
        "config.json",
        Path.home() / ".config" / "mcp" / "config.json",
        Path.home() / ".mcp_config.json",
    ]

    for path in possible_paths:
        if Path(str(path)).exists():
            return str(path)
    return None


def list_servers(config_path: str) -> None:
    """List all available servers in the configuration."""
    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        servers = config.get("mcpServers", {})
        if not servers:
            print("No servers found in configuration.")
            return

        print(f"Available servers in {config_path}:")
        for name, details in servers.items():
            command = details.get("command", "unknown")
            args = details.get("args", [])
            print(f"  • {name}: {command} {' '.join(args)}")

    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading configuration: {e}")
        sys.exit(1)


async def test_server(
    config_path: str, server_name: str, verbose: bool = False
) -> bool:
    """Test connectivity and basic functionality with an MCP server."""
    logger = logging.getLogger(__name__)

    try:
        # Load server configuration
        logger.info(f"Loading configuration for server '{server_name}'")
        server_params, _ = await load_config(config_path, server_name)

        logger.info(
            f"Connecting to server: {server_params.command} {' '.join(server_params.args)}"
        )

        # Connect to server
        async with stdio_client(server_params) as (read_stream, write_stream):
            # Initialize connection
            logger.info("Initializing MCP connection...")
            init_result = await send_initialize(read_stream, write_stream)

            if not init_result:
                print("❌ Server initialization failed")
                return False

            print(
                f"✅ Connected to {init_result.serverInfo.name} v{init_result.serverInfo.version}"
            )
            print(f"   Protocol version: {init_result.protocolVersion}")

            if verbose and init_result.instructions:
                print(f"   Instructions: {init_result.instructions}")

            # Test basic connectivity
            logger.info("Testing ping...")
            ping_result = await send_ping(read_stream, write_stream)
            status = "✅ Ping successful" if ping_result else "❌ Ping failed"
            print(f"   {status}")

            # Discover capabilities
            capabilities = init_result.capabilities

            # Test tools if available
            if capabilities.tools:
                try:
                    logger.info("Discovering tools...")
                    tools_result = await send_tools_list(read_stream, write_stream)
                    tools = tools_result.tools
                    print(f"   🔧 Tools available: {len(tools)}")

                    if verbose and tools:
                        for tool in tools[:3]:  # Show first 3 tools
                            name = tool.name
                            desc = tool.description or "No description"
                            print(f"      • {name}: {desc}")
                        if len(tools) > 3:
                            print(f"      ... and {len(tools) - 3} more")

                except Exception as e:
                    logger.warning(f"Error listing tools: {e}")
                    print("   ⚠️  Tools feature available but listing failed")

            # Test resources if available
            if capabilities.resources:
                try:
                    logger.info("Discovering resources...")
                    resources_result = await send_resources_list(
                        read_stream, write_stream
                    )
                    resources = resources_result.resources
                    print(f"   📄 Resources available: {len(resources)}")

                    if verbose and resources:
                        for resource in resources[:3]:  # Show first 3 resources
                            name = resource.name
                            desc = resource.description or "No description"
                            print(f"      • {name}: {desc}")
                        if len(resources) > 3:
                            print(f"      ... and {len(resources) - 3} more")

                except Exception as e:
                    logger.warning(f"Error listing resources: {e}")
                    print("   ⚠️  Resources feature available but listing failed")

            # Test prompts if available
            if capabilities.prompts:
                try:
                    logger.info("Discovering prompts...")
                    prompts_result = await send_prompts_list(read_stream, write_stream)
                    prompts = prompts_result.prompts
                    print(f"   💬 Prompts available: {len(prompts)}")

                    if verbose and prompts:
                        for prompt in prompts[:3]:  # Show first 3 prompts
                            name = prompt.name
                            desc = prompt.description or "No description"
                            print(f"      • {name}: {desc}")
                        if len(prompts) > 3:
                            print(f"      ... and {len(prompts) - 3} more")

                except Exception as e:
                    logger.warning(f"Error listing prompts: {e}")
                    print("   ⚠️  Prompts feature available but listing failed")

            print("🎉 Server test completed successfully!")
            return True

    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path}")
        return False
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=verbose)
        print(f"❌ Connection failed: {e}")
        return False


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Chuk MCP - Test and explore MCP server connections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Test default server with default config
  %(prog)s --server sqlite           # Test specific server
  %(prog)s --config custom.json     # Use custom configuration file
  %(prog)s --list-servers            # Show all available servers
  %(prog)s --verbose --server mydb   # Detailed output for debugging
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to configuration file (default: search common locations)",
    )

    parser.add_argument(
        "--server",
        "-s",
        default="sqlite",
        help="Name of server to test (default: sqlite)",
    )

    parser.add_argument(
        "--list-servers",
        "-l",
        action="store_true",
        help="List all available servers and exit",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging and detailed output",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Find configuration file
    config_path = args.config
    if not config_path:
        config_path = find_default_config()
        if not config_path:
            print(
                "❌ No configuration file found. Please specify --config or create server_config.json"
            )
            sys.exit(1)

    # Handle list servers command
    if args.list_servers:
        list_servers(config_path)
        return

    # Test the server
    print(f"Testing MCP server '{args.server}' using config: {config_path}")
    print("=" * 60)

    try:
        success = anyio.run(test_server, config_path, args.server, args.verbose)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)


def run():
    """Entry point for console script."""
    main()


if __name__ == "__main__":
    main()
