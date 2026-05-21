"""TestForge shared state — passed between all agents in the flow."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TestForgeState:
    """Shared state that flows between agents via the orchestrator."""

    # Inputs
    repo_path: str = ""
    app_url: str = ""
    credentials: dict = field(default_factory=dict)
    output_dir: str = "./test-output"
    incremental: bool = False
    force: bool = False
    mcp_server_config: Optional[dict] = None

    # Repo Reader output
    context_document: str = ""
    tech_stack: dict = field(default_factory=dict)
    roles_discovered: list = field(default_factory=list)

    # Scraper output
    api_spec: str = ""
    api_spec_source: str = ""  # "mcp_server" | "code_extraction"
    endpoints: list = field(default_factory=list)
    ui_routes: list = field(default_factory=list)

    # QA Analyst output
    test_plan: str = ""

    # Test Writer outputs
    be_tests: list = field(default_factory=list)
    fe_tests: list = field(default_factory=list)
    e2e_tests: list = field(default_factory=list)

    # Reviewer outputs
    test_results: list = field(default_factory=list)
    feedback: list = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3

    @property
    def all_passing(self) -> bool:
        """True if all tests passed in the last review."""
        if not self.test_results:
            return False
        return all(r.get("failed", 0) == 0 for r in self.test_results)
