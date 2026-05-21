"""Reviewer — executes tests, analyzes failures, provides fix instructions."""

import logging

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.tools.file_tools import file_read_tool
from testforge.tools.test_runner import test_runner_tool
from testforge.tools.playwright_mcp import create_playwright_mcp

logger = logging.getLogger("testforge")


@CrewBase
class ReviewerCrew:
    """Crew that runs tests and provides feedback."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, playwright_tools: list = None):
        super().__init__()
        self._playwright_tools = playwright_tools or []

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            tools=[test_runner_tool, file_read_tool] + self._playwright_tools,
            llm="openai/gpt-4o-mini",
            verbose=True,
        )

    @task
    def review_tests(self) -> Task:
        return Task(config=self.tasks_config["review_tests"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def run_reviewer(state: TestForgeState) -> TestForgeState:
    """Execute the Reviewer crew and update state."""
    # Start Playwright MCP for optional manual verification (screenshot, inspect)
    pw_mcp = create_playwright_mcp(state.app_url)
    try:
        pw_mcp.start()
        pw_tools = pw_mcp.tools
        logger.info(f"Playwright MCP started — {len(pw_tools)} tools available for Reviewer")

        crew = ReviewerCrew(playwright_tools=pw_tools)
        result = crew.crew().kickoff(
            inputs={
                "output_dir": state.output_dir,
                "app_url": state.app_url,
                "roles": [r["name"] for r in state.credentials.get("roles", [])],
            }
        )

        # Parse reviewer output into structured feedback
        result_str = str(result)
        state.test_results = _parse_results(result_str)
        state.feedback = _parse_feedback(result_str)
    finally:
        pw_mcp.stop()
        logger.info("Playwright MCP stopped for Reviewer")

    return state


def _parse_results(output: str) -> list[dict]:
    """Parse test runner output into structured results."""
    # Simple parsing — in production this would parse the JSON reporter output
    results = []
    if "COMPILE_ERROR" in output:
        results.append({"file": "all", "passed": 0, "failed": 1, "errors": ["Compilation failed"]})
    elif "EXIT_CODE: 0" in output:
        results.append({"file": "all", "passed": 1, "failed": 0, "errors": []})
    else:
        results.append({"file": "all", "passed": 0, "failed": 1, "errors": [output[:500]]})
    return results


def _parse_feedback(output: str) -> list[dict]:
    """Parse reviewer analysis into structured feedback for writers."""
    feedback = []
    # The reviewer agent will structure its output; this parses it
    if "TEST_BUG:" in output:
        lines = output.split("\n")
        for line in lines:
            if line.startswith("TEST_BUG:"):
                parts = line.split("|")
                if len(parts) >= 3:
                    feedback.append({
                        "test_file": parts[1].strip(),
                        "issue": parts[2].strip(),
                        "fix_suggestion": parts[3].strip() if len(parts) > 3 else "",
                    })
    return feedback
