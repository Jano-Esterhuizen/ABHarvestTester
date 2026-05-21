"""TestForge orchestration flow — deterministic Python, no LLM for routing."""

import logging
from pathlib import Path
from typing import ClassVar

from crewai.flow.flow import Flow, listen, start, router

from testforge.config import TestForgeConfig
from testforge.state import TestForgeState

logger = logging.getLogger("testforge")


def detect_existing_framework(output_dir: str) -> bool:
    """Check if the output directory already has a scaffolded framework."""
    markers = [
        "playwright.config.ts",
        "package.json",
        "tsconfig.json",
        "core/types/enums.ts",
    ]
    return all((Path(output_dir) / m).exists() for m in markers)


def discover_mcp_server(config: TestForgeConfig) -> dict | None:
    """Discover dev-provided MCP server config.

    Priority:
    1. Explicit --mcp-config CLI flag
    2. mcp-server.json in target repo root
    3. 'mcp' section in target repo's package.json
    """
    import json

    # 1. Explicit config
    if config.mcp_server_config:
        return config.mcp_server_config

    # 2. mcp-server.json in repo root
    mcp_json = Path(config.repo_path) / "mcp-server.json"
    if mcp_json.exists():
        with open(mcp_json) as f:
            return json.load(f)

    # 3. package.json 'mcp' section
    pkg_json = Path(config.repo_path) / "package.json"
    if pkg_json.exists():
        with open(pkg_json) as f:
            pkg = json.load(f)
        if "mcp" in pkg:
            return pkg["mcp"]

    return None


class TestForgeFlow(Flow[TestForgeState]):
    """Orchestrator: deterministic Python flow that coordinates all agents.

    Sequence:
    load_config → read_repository → extract_api_spec → scaffold_framework
    → plan_tests → write_tests → review_tests → (retry | complete)
    """

    _config: ClassVar[TestForgeConfig]

    @classmethod
    def create(cls, config: TestForgeConfig) -> "TestForgeFlow":
        """Factory method to create a flow with config and initial state."""
        cls._config = config
        flow = cls()
        return flow

    @start()
    def load_config(self):
        """Load config and detect output mode."""
        logger.info("Loading configuration...")
        config = self._config
        self.state.repo_path = config.repo_path
        self.state.app_url = config.app_url
        self.state.credentials = config.credentials
        self.state.output_dir = config.output_dir
        self.state.force = config.force
        self.state.mcp_server_config = config.mcp_server_config

        self.state.incremental = detect_existing_framework(self.state.output_dir)
        if self.state.incremental:
            logger.info("Existing framework detected — incremental mode")
        else:
            logger.info("No existing framework — full scaffold mode")

    @listen(load_config)
    def read_repository(self):
        """Repo Reader agent: produce context document."""
        logger.info("Agent: Repo Reader — analyzing repository...")
        from testforge.agents.repo_reader.agent import run_repo_reader

        run_repo_reader(self.state)
        logger.info(f"Context document: {len(self.state.context_document)} chars")

    @listen(read_repository)
    def extract_api_spec(self):
        """Scraper agent: produce canonical API specification."""
        logger.info("Agent: Scraper — extracting API specification...")

        # Discover MCP server
        mcp_config = discover_mcp_server(self._config)
        if mcp_config:
            self.state.mcp_server_config = mcp_config
            self.state.api_spec_source = "mcp_server"
            logger.info("MCP server found — using as authoritative API source")
        else:
            self.state.api_spec_source = "code_extraction"
            logger.info("No MCP server — extracting from code")

        from testforge.agents.scraper.agent import run_scraper

        run_scraper(self.state)
        logger.info(f"API spec source: {self.state.api_spec_source}")

    @listen(extract_api_spec)
    def scaffold_framework(self):
        """Create framework structure if needed (skipped in incremental mode)."""
        if not self.state.incremental:
            logger.info("Scaffolding test framework structure...")
            from testforge.agents.scaffold import scaffold_output

            scaffold_output(self.state)
        else:
            logger.info("Framework exists — skipping scaffold")

    @listen(scaffold_framework)
    def plan_tests(self):
        """QA Analyst: produce structured test plan."""
        logger.info("Agent: QA Analyst — planning test scenarios...")
        from testforge.agents.qa_analyst.agent import run_qa_analyst

        run_qa_analyst(self.state)
        logger.info(f"Test plan: {len(self.state.test_plan)} chars")

    @listen(plan_tests)
    def write_tests(self):
        """BE + FE + E2E Test Writers run in parallel."""
        logger.info("Agents: Test Writers — generating tests (parallel)...")
        from testforge.agents.be_test_writer.agent import run_be_writer
        from testforge.agents.fe_test_writer.agent import run_fe_writer
        from testforge.agents.e2e_test_writer.agent import run_e2e_writer

        # TODO: Run concurrently with asyncio or threading
        run_be_writer(self.state)
        run_fe_writer(self.state)
        run_e2e_writer(self.state)

        total = len(self.state.be_tests) + len(self.state.fe_tests) + len(self.state.e2e_tests)
        logger.info(f"Generated {total} test files")

    @router(write_tests)
    def review_tests(self):
        """Reviewer: run tests, check results, decide next step."""
        logger.info(f"Agent: Reviewer — iteration {self.state.iteration + 1}/{self.state.max_iterations}...")
        from testforge.agents.reviewer.agent import run_reviewer

        run_reviewer(self.state)

        if self.state.all_passing:
            logger.info("All tests passing!")
            return "complete"
        elif self.state.iteration >= self.state.max_iterations:
            logger.warning(f"Max iterations ({self.state.max_iterations}) reached. Stopping.")
            return "complete"
        else:
            failed = sum(r.get("failed", 0) for r in self.state.test_results)
            logger.info(f"{failed} test(s) failing — routing to retry")
            return "retry"

    @listen("retry")
    def fix_tests(self):
        """Send feedback to writers, regenerate failing tests."""
        self.state.iteration += 1
        logger.info(f"Retry iteration {self.state.iteration} — fixing failing tests...")

        from testforge.agents.be_test_writer.agent import run_be_writer
        from testforge.agents.fe_test_writer.agent import run_fe_writer
        from testforge.agents.e2e_test_writer.agent import run_e2e_writer

        # Re-run writers with feedback context
        run_be_writer(self.state)
        run_fe_writer(self.state)
        run_e2e_writer(self.state)

    @listen("complete")
    def deliver_results(self):
        """Output final test suite and summary report."""
        logger.info("Delivering results...")
        passed = sum(r.get("passed", 0) for r in self.state.test_results)
        failed = sum(r.get("failed", 0) for r in self.state.test_results)
        total = passed + failed

        logger.info("=" * 40)
        logger.info(f"  RESULTS: {passed}/{total} tests passing")
        logger.info(f"  Iterations used: {self.state.iteration + 1}")
        logger.info(f"  API spec source: {self.state.api_spec_source}")
        logger.info("=" * 40)
