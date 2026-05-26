"""Playwright MCP server integration for FE/E2E Writer exploration.

Uses crewai_tools.MCPServerAdapter to expose Playwright browser tools
(navigate, click, fill, screenshot, get_visible_text, etc.) as CrewAI tools.

Architecture:
- FE Writer & E2E Writer use this for UI exploration (understanding pages, selectors)
- Reviewer does NOT use this — it runs `npx playwright test` as a subprocess
- Each agent gets an isolated instance; no shared browser sessions
"""

import logging
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter

logger = logging.getLogger("testforge")

# Only expose a useful subset of tools to avoid bloating the LLM prompt
USEFUL_TOOLS = {
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_fill_form",
    "browser_take_screenshot",
    "browser_press_key",
}


def create_playwright_mcp(app_url: str) -> MCPServerAdapter:
    """Create an MCPServerAdapter connected to the Playwright MCP server.

    The returned adapter must be used as a context manager or manually stopped:
        with create_playwright_mcp(url) as tools:
            agent = Agent(tools=tools, ...)

    Args:
        app_url: The target application URL to navigate to (passed to agents for navigation).

    Returns:
        MCPServerAdapter instance (call .tools after starting).
    """
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@playwright/mcp@latest", "--headless"],
    )
    return MCPServerAdapter(server_params, connect_timeout=60)
