"""QA Analyst — adversarial test planner."""

import logging
from pathlib import Path

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.llm import get_llm

logger = logging.getLogger("testforge")


@CrewBase
class QAAnalystCrew:
    """Crew that produces a structured test plan."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def qa_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["qa_analyst"],
            tools=[],
            llm=get_llm(),
            verbose=True,
        )

    @task
    def plan_tests(self) -> Task:
        return Task(config=self.tasks_config["plan_tests"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def run_qa_analyst(state: TestForgeState) -> None:
    """Execute the QA Analyst crew and update state."""
    crew = QAAnalystCrew()
    result = crew.crew().kickoff(
        inputs={
            "context_document": state.context_document,
            "api_spec": state.api_spec,
            "roles": [r["name"] for r in state.credentials.get("roles", [])],
            "credentials_summary": str(state.credentials.get("roles", [])),
        }
    )

    state.test_plan = str(result)

    # Write test plan to disk — visibility, persistence, and human review opportunity
    plan_path = Path(state.output_dir) / "test-plan.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(state.test_plan, encoding="utf-8")
    logger.info(f"Test plan written to: {plan_path}")
