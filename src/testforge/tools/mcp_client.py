"""MCP client for connecting to dev-provided MCP servers (Swagger/API spec pull).

Uses crewai_tools.MCPServerAdapter to expose the dev team's MCP server tools
as CrewAI tools the Scraper agent can call.

Architecture:
- The Scraper agent uses this when a dev-provided MCP server is discovered
- Discovery priority: --mcp-config flag > mcp-server.json in repo > package.json 'mcp' section
- If no MCP server is found, the Scraper falls back to code-based extraction
"""

import logging
from typing import Optional

from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter

logger = logging.getLogger("testforge")


def create_dev_mcp(mcp_config: dict) -> Optional[MCPServerAdapter]:
    """Create an MCPServerAdapter connected to a dev-provided MCP server.

    The returned adapter must be used as a context manager or manually stopped:
        with create_dev_mcp(config) as tools:
            agent = Agent(tools=tools, ...)

    Args:
        mcp_config: MCP server configuration dict. Supports two formats:
            Stdio: {"server": {"command": "npx", "args": [...]}, "capabilities": {...}}
            SSE:   {"url": "http://localhost:8000/sse"}

    Returns:
        MCPServerAdapter instance, or None if config is invalid.
    """
    if not mcp_config:
        logger.warning("No MCP config provided")
        return None

    # SSE transport: {"url": "..."}
    if "url" in mcp_config:
        logger.info(f"Connecting to dev MCP server via SSE: {mcp_config['url']}")
        return MCPServerAdapter({"url": mcp_config["url"]})

    # Stdio transport: {"server": {"command": ..., "args": [...]}}
    server = mcp_config.get("server", {})
    command = server.get("command")
    args = server.get("args", [])

    if not command:
        logger.error("MCP config missing 'server.command' — cannot connect")
        return None

    logger.info(f"Connecting to dev MCP server via stdio: {command} {' '.join(args)}")
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=server.get("env"),
    )
    return MCPServerAdapter(server_params)
