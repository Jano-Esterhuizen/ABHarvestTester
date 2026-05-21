"""Scraper — extracts canonical API specification from code or MCP server."""

import logging

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.tools.file_tools import file_read_tool
from testforge.tools.mcp_client import create_dev_mcp

logger = logging.getLogger("testforge")


@CrewBase
class ScraperCrew:
    """Crew that produces the canonical API specification document."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, mcp_tools: list = None):
        super().__init__()
        self._mcp_tools = mcp_tools or []

    @agent
    def scraper(self) -> Agent:
        return Agent(
            config=self.agents_config["scraper"],
            tools=[file_read_tool] + self._mcp_tools,
            llm="openai/gpt-4.1",
            verbose=True,
        )

    @task
    def extract_api_spec(self) -> Task:
        return Task(config=self.tasks_config["extract_api_spec"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def run_scraper(state: TestForgeState) -> TestForgeState:
    """Execute the Scraper crew and update state."""
    mcp_tools = []
    dev_mcp = None

    # If dev-provided MCP server config exists, connect to it
    if state.mcp_server_config:
        dev_mcp = create_dev_mcp(state.mcp_server_config)
        if dev_mcp:
            try:
                dev_mcp.start()
                mcp_tools = dev_mcp.tools
                logger.info(f"Dev MCP server started — {len(mcp_tools)} tools available for Scraper")
            except Exception as e:
                logger.warning(f"Failed to connect to dev MCP server: {e}")
                logger.info("Falling back to code-based extraction")
                state.api_spec_source = "code_extraction"
                dev_mcp = None

    try:
        crew = ScraperCrew(mcp_tools=mcp_tools)
        result = crew.crew().kickoff(
            inputs={
                "repo_path": state.repo_path,
                "context_document": state.context_document,
                "api_spec_source": state.api_spec_source,
                "mcp_server_config": state.mcp_server_config or {},
            }
        )

        state.api_spec = str(result)
    finally:
        if dev_mcp:
            dev_mcp.stop()
            logger.info("Dev MCP server stopped for Scraper")

    return state
