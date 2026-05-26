"""E2E Test Writer — generates end-to-end user journey test files."""

import logging
import os
import re

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.llm import get_llm
from testforge.tools.file_tools import file_read_tool

logger = logging.getLogger("testforge")
SINGLE_CASE_MODE = True


@CrewBase
class E2ETestWriterCrew:
    """Crew that generates end-to-end journey .spec.ts files."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    _playwright_tools: list = []

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


def _split_journey_cases(journey_text: str) -> list[tuple[str, str]]:
    """Split an E2E journey chunk into case-sized units."""
    case_start = re.compile(
        r"^\s*(?:[-*]\s*)?(?:E2E\d+|TC\d+|Test\s*Case\s*\d+|Scenario\s*\d+|Step\s*\d+)\s*[:\-].*",
        re.IGNORECASE,
    )

    cases: list[tuple[str, str]] = []
    current_name = "e2e-case"
    current_lines: list[str] = []

    for line in journey_text.split("\n"):
        if case_start.match(line):
            if current_lines:
                cases.append((current_name, "\n".join(current_lines).strip()))
            current_name = re.sub(r"[^a-z0-9]+", "-", line.lower()).strip("-")[:60] or "e2e-case"
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)

    if current_lines:
        cases.append((current_name, "\n".join(current_lines).strip()))

    if not cases and journey_text:
        cases = [("e2e-case-1", journey_text[:800])]

    return cases


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
        f"{r['name']}:username={r.get('username', r.get('email', ''))},password={r.get('password', '')}"
        for r in state.credentials.get("roles", [])
    )
    login_cfg = state.credentials.get("login", {}) if isinstance(state.credentials, dict) else {}
    login_url_path = login_cfg.get("url_path", "/login")
    login_username_field = login_cfg.get("username_field", "username")
    login_password_field = login_cfg.get("password_field", "password")
    login_submit_button = login_cfg.get("submit_button", "Sign In")

    chunks = _extract_e2e_journeys(state.test_plan or "")

    output_dir = os.path.join(state.output_dir, "tests", "e2e")
    os.makedirs(output_dir, exist_ok=True)

    for journey_name, e2e_chunk in chunks:
        case_items = _split_journey_cases(e2e_chunk) if SINGLE_CASE_MODE else [("all-e2e-cases", e2e_chunk[:2500])]

        for case_idx, (case_name, case_text) in enumerate(case_items, start=1):
            plan_chunk = case_text[:1200] if case_text else e2e_chunk[:1200]

            logger.info(
                f"Generating E2E tests for journey '{journey_name}', case {case_idx}/{len(case_items)}: {case_name}"
            )

            # Start/stop Playwright MCP per case to ensure a clean writer process state.
            playwright_mcp = None
            playwright_tools = []
            try:
                from testforge.tools.playwright_mcp import create_playwright_mcp

                playwright_mcp = create_playwright_mcp(state.app_url)
                playwright_tools = playwright_mcp.tools
                logger.info("Playwright MCP started for E2E Writer case")
            except Exception as e:
                logger.warning(f"Playwright MCP unavailable: {e} -- proceeding without browser tools")

            try:
                E2ETestWriterCrew._playwright_tools = playwright_tools
                # Fresh crew each case to avoid cross-case memory bleed.
                crew = E2ETestWriterCrew()
                result = crew.crew().kickoff(
                    inputs={
                        "e2e_chunk": plan_chunk,
                        "plan_chunk": plan_chunk,
                        "roles": roles,
                        "credentials": creds_summary,
                        "login_url_path": login_url_path,
                        "login_username_field": login_username_field,
                        "login_password_field": login_password_field,
                        "login_submit_button": login_submit_button,
                        "feedback": feedback_context,
                        "app_url": state.app_url,
                    }
                )
            finally:
                if playwright_mcp:
                    try:
                        playwright_mcp.stop()
                    except Exception:
                        pass
                logger.info("Playwright MCP stopped for E2E Writer case")

            code = str(result)
            slug_base = f"{journey_name}-{case_name}"
            slug = re.sub(r"[^a-z0-9]", "-", slug_base.lower()).strip("-") or "journey"
            filepath = os.path.join(output_dir, f"{slug}.e2e.spec.ts")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            state.e2e_tests.append({"file": filepath, "journey": journey_name, "status": "generated"})
            logger.info(f"Wrote E2E test: {filepath}")
