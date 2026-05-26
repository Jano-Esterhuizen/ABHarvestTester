"""BE Test Writer — generates backend API test files."""

import logging
import os
import re

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.llm import get_llm
from testforge.tools.file_tools import file_read_tool, directory_list_tool

logger = logging.getLogger("testforge")
SINGLE_CASE_MODE = True


@CrewBase
class BETestWriterCrew:
    """Crew that generates backend API .spec.ts files."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def be_test_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["be_test_writer"],
            tools=[file_read_tool, directory_list_tool],
            llm=get_llm(),
            verbose=True,
        )

    @task
    def write_be_tests(self) -> Task:
        return Task(config=self.tasks_config["write_be_tests"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def _split_api_by_resource(api_spec: str) -> list[tuple[str, str]]:
    """Split API spec into chunks by resource heading. Returns [(resource_name, chunk)]."""
    chunks = []
    current_name = "general"
    current_lines = []

    for line in api_spec.split("\n"):
        if line.startswith("## ") or line.startswith("### "):
            if current_lines:
                chunks.append((current_name, "\n".join(current_lines)))
            current_name = re.sub(r"[#\s]+", "", line).strip() or "general"
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        chunks.append((current_name, "\n".join(current_lines)))

    return chunks


def _extract_api_cases(test_plan: str) -> list[tuple[str, str]]:
    """Extract API test cases from the test plan (one case per item)."""
    case_start = re.compile(
        r"^\s*(?:[-*]\s*)?(?:API\d+|TC\d+|Test\s*Case\s*\d+|Scenario\s*\d+)\s*[:\-].*",
        re.IGNORECASE,
    )

    cases: list[tuple[str, str]] = []
    current_name = "api-case"
    current_lines: list[str] = []
    in_api_section = False

    for line in test_plan.split("\n"):
        lower = line.lower()
        if "api" in lower or "backend" in lower or "endpoint" in lower:
            in_api_section = True

        if not in_api_section:
            continue

        if line.startswith("## ") and "api" not in lower and current_lines:
            break

        if case_start.match(line):
            if current_lines:
                cases.append((current_name, "\n".join(current_lines).strip()))
            current_name = re.sub(r"[^a-z0-9]+", "-", line.lower()).strip("-")[:60] or "api-case"
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)

    if current_lines:
        cases.append((current_name, "\n".join(current_lines).strip()))

    # Fallback for plans without explicit API case labels.
    if not cases and test_plan:
        cases = [("api-case-1", test_plan[:600])]

    return cases


def run_be_writer(state: TestForgeState) -> None:
    """Execute the BE Test Writer crew per resource chunk and write files."""
    feedback_context = ""
    if state.feedback:
        be_feedback = [f for f in state.feedback if "api" in f.get("test_file", "")]
        if be_feedback:
            feedback_context = "\nFEEDBACK:\n"
            for fb in be_feedback:
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

    # Split API spec into resource chunks
    chunks = _split_api_by_resource(state.api_spec)
    if not chunks:
        chunks = [("all", state.api_spec[:3000])]

    api_cases = _extract_api_cases(state.test_plan or "")
    if SINGLE_CASE_MODE and not api_cases:
        api_cases = [("api-case-1", state.test_plan[:600] if state.test_plan else "No test plan available")]

    # Demo mode: limit to 3 chunks
    if state.demo:
        chunks = chunks[:3]
        logger.info("DEMO MODE: limiting BE tests to 3 resources")

    output_dir = os.path.join(state.output_dir, "tests", "api")
    os.makedirs(output_dir, exist_ok=True)

    for resource_name, api_chunk in chunks:
        # Truncate each chunk to fit within token budget
        api_chunk_trimmed = api_chunk[:2500]

        if SINGLE_CASE_MODE:
            case_items = api_cases
        else:
            case_items = [("all-api-cases", state.test_plan[:2000] if state.test_plan else "No test plan available")]

        for case_idx, (case_name, case_text) in enumerate(case_items, start=1):
            plan_chunk = case_text[:1200] if case_text else "No test plan available"
            logger.info(
                f"Generating BE tests for resource '{resource_name}', case {case_idx}/{len(case_items)}: {case_name}"
            )

            # Fresh crew each case to avoid cross-case memory bleed.
            crew = BETestWriterCrew()
            result = crew.crew().kickoff(
                inputs={
                    "api_chunk": api_chunk_trimmed,
                    "plan_chunk": plan_chunk,
                    "roles": roles,
                    "credentials": creds_summary,
                    "login_url_path": login_url_path,
                    "login_username_field": login_username_field,
                    "login_password_field": login_password_field,
                    "feedback": feedback_context,
                    "app_url": state.app_url,
                }
            )

            # Write output to file
            code = str(result)
            resource_slug = re.sub(r"[^a-z0-9]", "-", resource_name.lower()).strip("-")
            case_slug = re.sub(r"[^a-z0-9]", "-", case_name.lower()).strip("-") or f"case-{case_idx}"
            filename = f"{resource_slug}-{case_slug}.api.spec.ts"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)

            state.be_tests.append({"file": filepath, "resource": resource_name, "status": "generated"})
            logger.info(f"Wrote BE test: {filepath}")
