"""Repo Reader — analyzes target repository and produces context document."""

import logging
from pathlib import Path

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.tools.file_tools import file_read_tool, directory_list_tool
from testforge.llm import get_llm

logger = logging.getLogger("testforge")

CONTEXT_BUDGET_TOKENS = 4000


@CrewBase
class RepoReaderCrew:
    """Crew that reads a target repo and produces a context document."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def repo_reader(self) -> Agent:
        return Agent(
            config=self.agents_config["repo_reader"],
            tools=[file_read_tool, directory_list_tool],
            llm=get_llm(),
            verbose=True,
        )

    @task
    def analyze_repository(self) -> Task:
        return Task(config=self.tasks_config["analyze_repository"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def run_repo_reader(state: TestForgeState) -> None:
    """Execute the Repo Reader crew and update state."""
    crew = RepoReaderCrew()
    result = crew.crew().kickoff(
        inputs={
            "repo_path": state.repo_path,
            "roles": [r["name"] for r in state.credentials.get("roles", [])],
        }
    )

    state.context_document = str(result)

    # Validate token budget
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        token_count = len(enc.encode(state.context_document))
        if token_count > CONTEXT_BUDGET_TOKENS:
            logger.warning(
                f"Context document exceeds budget: {token_count}/{CONTEXT_BUDGET_TOKENS} tokens"
            )
    except ImportError:
        logger.warning("tiktoken not available — skipping budget check")
