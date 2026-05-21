"""BE Test Writer — generates backend API test files."""

import logging

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.tools.file_tools import file_write_tool
from testforge.llm import get_llm

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
            tools=[file_write_tool],
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


def run_be_writer(state: TestForgeState) -> None:
    """Execute the BE Test Writer crew and update state."""
    # Extract BE-specific section from test plan
    feedback_context = ""
    if state.feedback:
        be_feedback = [f for f in state.feedback if "api" in f.get("test_file", "")]
        if be_feedback:
            feedback_context = "\n\nFEEDBACK FROM REVIEWER (fix these):\n"
            for fb in be_feedback:
                feedback_context += f"- {fb['test_file']}: {fb['issue']}\n  Fix: {fb['fix_suggestion']}\n"

    crew = BETestWriterCrew()
    result = crew.crew().kickoff(
        inputs={
            "output_dir": state.output_dir,
            "api_spec": state.api_spec,
            "test_plan": state.test_plan,
            "roles": [r["name"] for r in state.credentials.get("roles", [])],
            "credentials": state.credentials,
            "feedback": feedback_context,
            "app_url": state.app_url,
        }
    )

    # Track generated files
    if result:
        state.be_tests.append({"content": str(result), "status": "generated"})
