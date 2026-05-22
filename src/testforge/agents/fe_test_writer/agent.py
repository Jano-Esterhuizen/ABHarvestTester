"""FE Test Writer — generates frontend UI test files."""

import logging
import os
import re

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.llm import get_llm
from testforge.tools.file_tools import file_read_tool, directory_list_tool
from testforge.tools.playwright_mcp import create_playwright_mcp

logger = logging.getLogger("testforge")


@CrewBase
class FETestWriterCrew:
    """Crew that generates frontend UI .spec.ts files."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, playwright_tools: list | None = None):
        super().__init__()
        self._playwright_tools = playwright_tools or []

    @agent
    def fe_test_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["fe_test_writer"],
            tools=[file_read_tool, directory_list_tool] + self._playwright_tools,
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


def _split_ui_routes(context_document: str) -> list[tuple[str, str]]:
    """Extract UI route sections from context document."""
    chunks = []
    in_ui_section = False
    current_lines = []
    current_name = "pages"

    for line in context_document.split("\n"):
        if "UI Routes" in line or "Pages" in line:
            in_ui_section = True
            continue
        if in_ui_section:
            if line.startswith("## ") and "UI" not in line and "Page" not in line:
                break
            if line.startswith("- /") or line.startswith("  /"):
                if current_lines and len("\n".join(current_lines)) > 500:
                    chunks.append((current_name, "\n".join(current_lines)))
                    current_lines = []
                route = line.strip("- ").split(" ")[0]
                current_name = route.strip("/").replace("/", "-") or "home"
            current_lines.append(line)

    if current_lines:
        chunks.append((current_name, "\n".join(current_lines)))

    # Fallback: just pass the whole context truncated
    if not chunks:
        chunks = [("pages", context_document[:2500])]

    return chunks


def run_fe_writer(state: TestForgeState) -> None:
    """Execute the FE Test Writer crew per page chunk and write files."""
    feedback_context = ""
    if state.feedback:
        fe_feedback = [f for f in state.feedback if "ui" in f.get("test_file", "")]
        if fe_feedback:
            feedback_context = "\nFEEDBACK:\n"
            for fb in fe_feedback:
                feedback_context += f"- {fb['test_file']}: {fb['fix_suggestion']}\n"

    roles = ", ".join(r["name"] for r in state.credentials.get("roles", []))
    creds_summary = "; ".join(
        f"{r['name']}:{r.get('username', r.get('email', ''))}" for r in state.credentials.get("roles", [])
    )

    chunks = _split_ui_routes(state.context_document)

    # Demo mode: limit to 3 chunks
    if state.demo:
        chunks = chunks[:3]
        logger.info("DEMO MODE: limiting FE tests to 3 pages")

    output_dir = os.path.join(state.output_dir, "tests", "ui")
    pom_dir = os.path.join(state.output_dir, "tests", "ui", "pages")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pom_dir, exist_ok=True)

    # Start Playwright MCP for UI exploration
    playwright_mcp = create_playwright_mcp(state.app_url)
    try:
        playwright_tools = playwright_mcp.tools
        logger.info("Playwright MCP started for FE Writer")
    except Exception as e:
        logger.warning(f"Playwright MCP unavailable: {e} — proceeding without browser tools")
        playwright_tools = []

    try:
        for page_name, ui_chunk in chunks:
            plan_chunk = state.test_plan[:2000] if state.test_plan else "No test plan"

            logger.info(f"Generating FE tests for page: {page_name}")

            crew = FETestWriterCrew(playwright_tools=playwright_tools)
            result = crew.crew().kickoff(
                inputs={
                    "ui_chunk": ui_chunk[:2500],
                    "plan_chunk": plan_chunk,
                    "roles": roles,
                    "credentials": creds_summary,
                    "feedback": feedback_context,
                    "app_url": state.app_url,
                }
            )

            code = str(result)

            # Split POM and spec if file break marker present
            parts = code.split("// --- FILE BREAK ---")
            if len(parts) == 2:
                pom_code, spec_code = parts
                slug = re.sub(r"[^a-z0-9]", "-", page_name.lower()).strip("-")
                pom_path = os.path.join(pom_dir, f"{slug}.page.ts")
                spec_path = os.path.join(output_dir, f"{slug}.ui.spec.ts")
                with open(pom_path, "w", encoding="utf-8") as f:
                    f.write(pom_code.strip())
                with open(spec_path, "w", encoding="utf-8") as f:
                    f.write(spec_code.strip())
            else:
                slug = re.sub(r"[^a-z0-9]", "-", page_name.lower()).strip("-")
                spec_path = os.path.join(output_dir, f"{slug}.ui.spec.ts")
                with open(spec_path, "w", encoding="utf-8") as f:
                    f.write(code)

            state.fe_tests.append({"file": spec_path, "page": page_name, "status": "generated"})
            logger.info(f"Wrote FE test: {spec_path}")
    finally:
        try:
            playwright_mcp.stop()
        except Exception:
            pass
        logger.info("Playwright MCP stopped for FE Writer")
