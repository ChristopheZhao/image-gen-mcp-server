"""
Unified entry point for MCP Image Generation Server.

This module provides a single entry point that supports both stdio and HTTP transports
based on configuration, ensuring backward compatibility while enabling remote access.
"""

import sys
from .config import load_config


def main():
    """
    Main entry point for MCP Image Generation Server.

    Supports both stdio (for local IDE integration) and HTTP (for remote access)
    transports based on MCP_TRANSPORT environment variable.
    """
    try:
        # Load configuration
        config = load_config()

        print(f"Starting MCP Image Generation Server...", file=sys.stderr)
        print(f"Transport mode: {config.transport}", file=sys.stderr)

        if config.is_stdio_transport():
            # Use existing FastMCP stdio implementation for backward compatibility
            print("Using stdio transport (FastMCP)", file=sys.stderr)
            from .transports.stdio import main as stdio_main
            stdio_main()

        elif config.is_http_transport():
            # Use new HTTP implementation
            print(f"Using HTTP transport: {config.host}:{config.port}", file=sys.stderr)
            from .transports.http_server import run_http_server
            run_http_server(config)

        else:
            print(
                f"ERROR: Unknown transport mode: {config.transport}",
                file=sys.stderr
            )
            print("Supported transports: stdio, http", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nServer interrupted by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Failed to start server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
