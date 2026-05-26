"""FE Test Writer — generates frontend UI test files."""

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
class FETestWriterCrew:
    """Crew that generates frontend UI .spec.ts files."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    _playwright_tools: list = []

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
            max_execution_time=300,  # 5 min timeout per chunk to avoid hanging
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


def _extract_ui_cases(test_plan: str) -> list[tuple[str, str]]:
    """Extract UI test cases from the test plan (one case per item)."""
    case_start = re.compile(
        r"^\s*(?:[-*]\s*)?(?:UI\d+|TC\d+|Test\s*Case\s*\d+|Scenario\s*\d+)\s*[:\-].*",
        re.IGNORECASE,
    )

    cases: list[tuple[str, str]] = []
    current_name = "ui-case"
    current_lines: list[str] = []
    in_ui_section = False

    for line in test_plan.split("\n"):
        lower = line.lower()
        if "ui" in lower or "frontend" in lower or "page" in lower:
            in_ui_section = True

        if not in_ui_section:
            continue

        if line.startswith("## ") and "ui" not in lower and "page" not in lower and current_lines:
            break

        if case_start.match(line):
            if current_lines:
                cases.append((current_name, "\n".join(current_lines).strip()))
            current_name = re.sub(r"[^a-z0-9]+", "-", line.lower()).strip("-")[:60] or "ui-case"
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)

    if current_lines:
        cases.append((current_name, "\n".join(current_lines).strip()))

    if not cases and test_plan:
        cases = [("ui-case-1", test_plan[:600])]

    return cases


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
        f"{r['name']}:username={r.get('username', r.get('email', ''))},password={r.get('password', '')}"
        for r in state.credentials.get("roles", [])
    )
    login_cfg = state.credentials.get("login", {}) if isinstance(state.credentials, dict) else {}
    login_url_path = login_cfg.get("url_path", "/login")
    login_username_field = login_cfg.get("username_field", "username")
    login_password_field = login_cfg.get("password_field", "password")
    login_submit_button = login_cfg.get("submit_button", "Sign In")

    chunks = _split_ui_routes(state.context_document)
    ui_cases = _extract_ui_cases(state.test_plan or "")
    if SINGLE_CASE_MODE and not ui_cases:
        ui_cases = [("ui-case-1", state.test_plan[:600] if state.test_plan else "No test plan")]

    # Demo mode: limit to 3 chunks
    if state.demo:
        chunks = chunks[:3]
        logger.info("DEMO MODE: limiting FE tests to 3 pages")

    output_dir = os.path.join(state.output_dir, "tests", "ui")
    pom_dir = os.path.join(state.output_dir, "tests", "ui", "pages")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(pom_dir, exist_ok=True)

    for page_name, ui_chunk in chunks:
        if SINGLE_CASE_MODE:
            case_items = ui_cases
        else:
            case_items = [("all-ui-cases", state.test_plan[:2000] if state.test_plan else "No test plan")]

        for case_idx, (case_name, case_text) in enumerate(case_items, start=1):
            plan_chunk = case_text[:1200] if case_text else "No test plan"

            logger.info(
                f"Generating FE tests for page '{page_name}', case {case_idx}/{len(case_items)}: {case_name}"
            )

            # Start/stop Playwright MCP per case to ensure a clean writer process state.
            playwright_mcp = None
            playwright_tools = []
            try:
                from testforge.tools.playwright_mcp import create_playwright_mcp, USEFUL_TOOLS

                playwright_mcp = create_playwright_mcp(state.app_url)
                all_tools = list(playwright_mcp.tools)
                playwright_tools = [t for t in all_tools if t.name in USEFUL_TOOLS]
                print(
                    f"[TestForge] Playwright MCP started — {len(playwright_tools)} tools available "
                    f"(filtered from {len(all_tools)})"
                )
                logger.info("Playwright MCP started for FE Writer case")
            except Exception as e:
                print(f"[TestForge] Playwright MCP FAILED: {e}")
                logger.warning(f"Playwright MCP unavailable: {e} -- proceeding without browser tools")

            try:
                FETestWriterCrew._playwright_tools = playwright_tools
                # Fresh crew each case to avoid cross-case memory bleed.
                crew = FETestWriterCrew()
                result = crew.crew().kickoff(
                    inputs={
                        "ui_chunk": ui_chunk[:2500],
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
                logger.info("Playwright MCP stopped for FE Writer case")

            code = str(result)

            # Split POM and spec if file break marker present
            parts = [p.strip() for p in code.split("// --- FILE BREAK ---") if p.strip()]
            if len(parts) == 2:
                # Simple case: one POM + one spec
                pom_code, spec_code = parts
                slug = re.sub(r"[^a-z0-9]", "-", f"{page_name}-{case_name}".lower()).strip("-")
                pom_path = os.path.join(pom_dir, f"{slug}.page.ts")
                spec_path = os.path.join(output_dir, f"{slug}.ui.spec.ts")
                with open(pom_path, "w", encoding="utf-8") as f:
                    f.write(pom_code.strip())
                with open(spec_path, "w", encoding="utf-8") as f:
                    f.write(spec_code.strip())
            elif len(parts) > 2:
                # Multiple POM/spec pairs (LLM generated multiple pages)
                # Pattern: parts alternate POM, spec, POM, spec...
                pair_idx = 0
                for i in range(0, len(parts) - 1, 2):
                    pom_code = parts[i]
                    spec_code = parts[i + 1]
                    # Try to extract class name for slug
                    class_match = re.search(r"class\s+(\w+)", pom_code)
                    if class_match:
                        slug = re.sub(r"([A-Z])", r"-\1", class_match.group(1)).lower().strip("-")
                        slug = re.sub(r"-page$", "", slug)
                    else:
                        slug = f"{page_name}-{case_name}-{pair_idx}"
                    slug = re.sub(r"[^a-z0-9-]", "", slug).strip("-") or f"page-{pair_idx}"
                    pom_path = os.path.join(pom_dir, f"{slug}.page.ts")
                    spec_path = os.path.join(output_dir, f"{slug}.ui.spec.ts")
                    with open(pom_path, "w", encoding="utf-8") as f:
                        f.write(pom_code.strip())
                    with open(spec_path, "w", encoding="utf-8") as f:
                        f.write(spec_code.strip())
                    state.fe_tests.append({"file": spec_path, "page": f"{page_name}-{slug}", "status": "generated"})
                    pair_idx += 1
                # Handle odd trailing part (POM without matching spec)
                if len(parts) % 2 == 1:
                    trailing = parts[-1]
                    slug = re.sub(r"[^a-z0-9]", "-", f"{page_name}-{case_name}".lower()).strip("-")
                    path = os.path.join(output_dir, f"{slug}-extra.ui.spec.ts")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(trailing.strip())
                logger.info(f"Split FE output into {pair_idx} page pairs for: {page_name}")
                continue  # Skip the append below since we already added to fe_tests
            else:
                slug = re.sub(r"[^a-z0-9]", "-", f"{page_name}-{case_name}".lower()).strip("-")
                spec_path = os.path.join(output_dir, f"{slug}.ui.spec.ts")
                with open(spec_path, "w", encoding="utf-8") as f:
                    f.write(code)

            state.fe_tests.append({"file": spec_path, "page": page_name, "status": "generated"})
            logger.info(f"Wrote FE test: {spec_path}")
