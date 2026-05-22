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
        f"{r['name']}:{r.get('username', r.get('email', ''))}" for r in state.credentials.get("roles", [])
    )

    # Split API spec into resource chunks
    chunks = _split_api_by_resource(state.api_spec)
    if not chunks:
        chunks = [("all", state.api_spec[:3000])]

    output_dir = os.path.join(state.output_dir, "tests", "api")
    os.makedirs(output_dir, exist_ok=True)

    for resource_name, api_chunk in chunks:
        # Truncate each chunk to fit within token budget
        api_chunk_trimmed = api_chunk[:2500]
        plan_chunk = state.test_plan[:2000] if state.test_plan else "No test plan available"

        logger.info(f"Generating BE tests for resource: {resource_name}")

        crew = BETestWriterCrew()
        result = crew.crew().kickoff(
            inputs={
                "api_chunk": api_chunk_trimmed,
                "plan_chunk": plan_chunk,
                "roles": roles,
                "credentials": creds_summary,
                "feedback": feedback_context,
                "app_url": state.app_url,
            }
        )

        # Write output to file
        code = str(result)
        filename = re.sub(r"[^a-z0-9]", "-", resource_name.lower()).strip("-") + ".api.spec.ts"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        state.be_tests.append({"file": filepath, "resource": resource_name, "status": "generated"})
        logger.info(f"Wrote BE test: {filepath}")
