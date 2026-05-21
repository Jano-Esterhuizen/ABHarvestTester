"""QA Analyst — adversarial test planner."""

import logging

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState

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
            llm="openai/gpt-4.1",
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


def run_qa_analyst(state: TestForgeState) -> TestForgeState:
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
    return state
