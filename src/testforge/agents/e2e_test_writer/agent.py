"""E2E Test Writer — generates end-to-end user journey test files."""

import logging
import os
import re

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.llm import get_llm
from testforge.tools.file_tools import file_read_tool
from testforge.tools.playwright_mcp import create_playwright_mcp

logger = logging.getLogger("testforge")


@CrewBase
class E2ETestWriterCrew:
    """Crew that generates end-to-end journey .spec.ts files."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, playwright_tools: list | None = None):
        super().__init__()
        self._playwright_tools = playwright_tools or []

    @agent
    def e2e_test_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["e2e_test_writer"],
            tools=[file_read_tool] + self._playwright_tools,
            llm=get_llm(),
            verbose=True,
        )

    @task
    def write_e2e_tests(self) -> Task:
        return Task(config=self.tasks_config["write_e2e_tests"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def _extract_e2e_journeys(test_plan: str) -> list[tuple[str, str]]:
    """Extract E2E journey sections from test plan."""
    chunks = []
    current_name = "journey"
    current_lines = []
    in_e2e = False

    for line in test_plan.split("\n"):
        lower = line.lower()
        if "e2e" in lower or "journey" in lower or "end-to-end" in lower:
            in_e2e = True
        if in_e2e:
            if line.startswith("### "):
                if current_lines:
                    chunks.append((current_name, "\n".join(current_lines)))
                current_name = line.strip("# ").strip()
                current_lines = [line]
            else:
                current_lines.append(line)

    if current_lines:
        chunks.append((current_name, "\n".join(current_lines)))

    if not chunks:
        chunks = [("journeys", test_plan[:2500])]

    return chunks


def run_e2e_writer(state: TestForgeState) -> None:
    """Execute the E2E Test Writer crew per journey and write files."""
    feedback_context = ""
    if state.feedback:
        e2e_feedback = [f for f in state.feedback if "e2e" in f.get("test_file", "")]
        if e2e_feedback:
            feedback_context = "\nFEEDBACK:\n"
            for fb in e2e_feedback:
                feedback_context += f"- {fb['test_file']}: {fb['fix_suggestion']}\n"

    roles = ", ".join(r["name"] for r in state.credentials.get("roles", []))
    creds_summary = "; ".join(
        f"{r['name']}:{r.get('username', r.get('email', ''))}" for r in state.credentials.get("roles", [])
    )

    chunks = _extract_e2e_journeys(state.test_plan or "")

    output_dir = os.path.join(state.output_dir, "tests", "e2e")
    os.makedirs(output_dir, exist_ok=True)

    # Start Playwright MCP for UI exploration
    playwright_mcp = create_playwright_mcp(state.app_url)
    try:
        playwright_tools = playwright_mcp.tools
        logger.info("Playwright MCP started for E2E Writer")
    except Exception as e:
        logger.warning(f"Playwright MCP unavailable: {e} — proceeding without browser tools")
        playwright_tools = []

    try:
        for journey_name, e2e_chunk in chunks:
            plan_chunk = e2e_chunk[:2500]

            logger.info(f"Generating E2E tests for journey: {journey_name}")

            crew = E2ETestWriterCrew(playwright_tools=playwright_tools)
            result = crew.crew().kickoff(
                inputs={
                    "e2e_chunk": plan_chunk,
                    "plan_chunk": plan_chunk,
                    "roles": roles,
                    "credentials": creds_summary,
                    "feedback": feedback_context,
                    "app_url": state.app_url,
                }
            )

            code = str(result)
            slug = re.sub(r"[^a-z0-9]", "-", journey_name.lower()).strip("-") or "journey"
            filepath = os.path.join(output_dir, f"{slug}.e2e.spec.ts")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            state.e2e_tests.append({"file": filepath, "journey": journey_name, "status": "generated"})
            logger.info(f"Wrote E2E test: {filepath}")
    finally:
        try:
            playwright_mcp.stop()
        except Exception:
            pass
        logger.info("Playwright MCP stopped for E2E Writer")
