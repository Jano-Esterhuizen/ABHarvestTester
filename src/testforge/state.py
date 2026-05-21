"""TestForge shared state — passed between all agents in the flow."""

from typing import Optional

from crewai.flow.flow import FlowState
from pydantic import Field


class TestForgeState(FlowState):
    """Shared state that flows between agents via the orchestrator."""

    # Inputs
    repo_path: str = ""
    app_url: str = ""
    credentials: dict = Field(default_factory=dict)
    output_dir: str = "./test-output"
    incremental: bool = False
    force: bool = False
    mcp_server_config: Optional[dict] = None

    # Repo Reader output
    context_document: str = ""
    tech_stack: dict = Field(default_factory=dict)
    roles_discovered: list = Field(default_factory=list)

    # Scraper output
    api_spec: str = ""
    api_spec_source: str = ""  # "mcp_server" | "code_extraction"
    endpoints: list = Field(default_factory=list)
    ui_routes: list = Field(default_factory=list)

    # QA Analyst output
    test_plan: str = ""

    # Test Writer outputs
    be_tests: list = Field(default_factory=list)
    fe_tests: list = Field(default_factory=list)
    e2e_tests: list = Field(default_factory=list)

    # Reviewer outputs
    test_results: list = Field(default_factory=list)
    feedback: list = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3

    @property
    def all_passing(self) -> bool:
        """True if all tests passed in the last review."""
        if not self.test_results:
            return False
        return all(r.get("failed", 0) == 0 for r in self.test_results)
