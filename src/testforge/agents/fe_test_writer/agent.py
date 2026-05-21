"""FE Test Writer — generates frontend UI test files."""

import logging

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.tools.file_tools import file_write_tool
from testforge.tools.playwright_mcp import create_playwright_mcp
from testforge.llm import get_llm

logger = logging.getLogger("testforge")


@CrewBase
class FETestWriterCrew:
    """Crew that generates frontend UI .spec.ts files."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    _playwright_tools: list = []

    @agent
    def fe_test_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["fe_test_writer"],
            tools=[file_write_tool] + self._playwright_tools,
            llm=get_llm(),
            verbose=True,
        )

    @task
    def write_fe_tests(self) -> Task:
        return Task(config=self.tasks_config["write_fe_tests"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def run_fe_writer(state: TestForgeState) -> None:
    """Execute the FE Test Writer crew and update state."""
    feedback_context = ""
    if state.feedback:
        fe_feedback = [f for f in state.feedback if "ui" in f.get("test_file", "")]
        if fe_feedback:
            feedback_context = "\n\nFEEDBACK FROM REVIEWER (fix these):\n"
            for fb in fe_feedback:
                feedback_context += f"- {fb['test_file']}: {fb['issue']}\n  Fix: {fb['fix_suggestion']}\n"

    # Start Playwright MCP server for UI exploration
    pw_mcp = create_playwright_mcp(state.app_url)
    try:
        pw_mcp.start()
        pw_tools = pw_mcp.tools
        logger.info(f"Playwright MCP started — {len(pw_tools)} tools available for FE Writer")

        crew = FETestWriterCrew()
        crew._playwright_tools = pw_tools
        result = crew.crew().kickoff(
            inputs={
                "output_dir": state.output_dir,
                "context_document": state.context_document,
                "test_plan": state.test_plan,
                "roles": [r["name"] for r in state.credentials.get("roles", [])],
                "credentials": state.credentials,
                "feedback": feedback_context,
                "app_url": state.app_url,
            }
        )

        if result:
            state.fe_tests.append({"content": str(result), "status": "generated"})
    finally:
        pw_mcp.stop()
        logger.info("Playwright MCP stopped for FE Writer")
