# chuk_mcp/config.py
import json
import logging
from typing import Optional, Tuple

# mcp_client imports
from chuk_mcp.transports.stdio.parameters import StdioParameters


async def load_config(
    config_path: str, server_name: str
) -> Tuple[StdioParameters, Optional[float]]:
    """Load the server configuration from a JSON file.

    Returns:
        Tuple of (StdioParameters, timeout) where timeout is the per-server timeout
        in seconds, or None if not specified.
    """
    try:
        # debug
        logging.debug(f"Loading config from {config_path}")

        # Read the configuration file
        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        # Retrieve the server configuration
        server_config = config.get("mcpServers", {}).get(server_name)
        if not server_config:
            error_msg = f"Server '{server_name}' not found in configuration file."
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Construct the server parameters
        result = StdioParameters(
            command=server_config["command"],
            args=server_config.get("args", []),
            env=server_config.get("env"),
        )

        # Extract per-server timeout if specified
        server_timeout = server_config.get("timeout")
        if server_timeout is not None:
            server_timeout = float(server_timeout)

        # debug
        logging.debug(
            f"Loaded config: command='{result.command}', args={result.args}, env={result.env}, timeout={server_timeout}"
        )

        # return result with timeout
        return result, server_timeout

    except FileNotFoundError:
        # error
        error_msg = f"Configuration file not found: {config_path}"
        logging.error(error_msg)
        raise FileNotFoundError(error_msg)
    except json.JSONDecodeError as e:
        # json error
        error_msg = f"Invalid JSON in configuration file: {e.msg}"
        logging.error(error_msg)
        raise json.JSONDecodeError(error_msg, e.doc, e.pos)
    except ValueError as e:
        # error
        logging.error(str(e))
        raise
