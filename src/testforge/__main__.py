"""TestForge CLI entry point."""

import click
import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

from testforge.config import TestForgeConfig, validate_config
from testforge.flow import TestForgeFlow

# Load .env file from project root
load_dotenv()


def preflight_check() -> list[str]:
    """Validate environment before spending tokens. Returns list of errors."""
    errors = []

    # Node.js / npx required for Playwright
    if not shutil.which("node"):
        errors.append("Node.js not found — install from https://nodejs.org")
    if not shutil.which("npx"):
        errors.append("npx not found — comes with Node.js")

    # Required Python packages
    required_packages = [
        ("crewai", "crewai[tools]"),
        ("click", "click"),
        ("yaml", "pyyaml"),
        ("mcp", "mcp"),
        ("mcpadapt", "mcpadapt"),
    ]
    for module, pip_name in required_packages:
        try:
            __import__(module)
        except ImportError:
            errors.append(f"Python package '{pip_name}' not installed — run: pip install {pip_name}")

    # Check Playwright config exists in output (if incremental) or npx is available
    if not shutil.which("npx"):
        errors.append("npx not found — Playwright tests won't run. Install Node.js")

    return errors


@click.command()
@click.option("--repo", required=True, type=click.Path(exists=True), help="Path to target repository")
@click.option("--url", required=True, help="URL of the running application")
@click.option("--creds", required=True, type=click.Path(exists=True), help="Path to credentials JSON file")
@click.option("--output", default="./test-output", help="Output directory for generated tests")
@click.option("--mcp-config", default=None, type=click.Path(exists=True), help="Optional: dev-provided MCP server config")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing test files")
@click.option("--demo", is_flag=True, default=False, help="Demo mode: limit to 3 tests per agent (FE + BE only)")
def cli(repo: str, url: str, creds: str, output: str, mcp_config: str | None, force: bool, demo: bool):
    """TestForge — Generate comprehensive Playwright test suites using AI agents."""

    # Load credentials
    creds_path = Path(creds)
    with open(creds_path) as f:
        credentials = json.load(f)

    # Load optional MCP server config
    mcp_server_config = None
    if mcp_config:
        with open(mcp_config) as f:
            mcp_server_config = json.load(f)

    # Validate environment
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        click.echo("ERROR: GITHUB_TOKEN environment variable is required.", err=True)
        click.echo("Set it in your .env file or export it.", err=True)
        sys.exit(1)

    # Preflight: check all dependencies before wasting tokens
    click.echo("Preflight check...")
    preflight_errors = preflight_check()
    if preflight_errors:
        click.echo("=" * 60, err=True)
        click.echo("  PREFLIGHT FAILED -- fix these before running:", err=True)
        click.echo("=" * 60, err=True)
        for err in preflight_errors:
            click.echo(f"  X {err}", err=True)
        click.echo("\n  Run: .\\setup-env.ps1  to fix automatically", err=True)
        sys.exit(1)
    click.echo("Preflight OK")

    # Build config
    config = TestForgeConfig(
        repo_path=str(Path(repo).resolve()),
        app_url=url.rstrip("/"),
        credentials=credentials,
        output_dir=str(Path(output).resolve()),
        mcp_config_path=mcp_config,
        mcp_server_config=mcp_server_config,
        force=force,
        demo=demo,
        github_token=github_token,
    )

    # Validate
    errors = validate_config(config)
    if errors:
        for err in errors:
            click.echo(f"ERROR: {err}", err=True)
        sys.exit(1)

    click.echo("=" * 60)
    click.echo("  TestForge — Agentic AI Test Orchestration")
    click.echo("=" * 60)
    click.echo(f"  Repo:    {config.repo_path}")
    click.echo(f"  App URL: {config.app_url}")
    click.echo(f"  Output:  {config.output_dir}")
    click.echo(f"  Roles:   {', '.join(r['name'] for r in credentials['roles'])}")
    if mcp_server_config:
        click.echo(f"  MCP:     Provided (authoritative API source)")
    click.echo(f"  Force:   {config.force}")
    if config.demo:
        click.echo("  Mode:    DEMO (3 tests per agent, FE + BE only)")
    click.echo("=" * 60)

    # Configure LLM environment for CrewAI (LiteLLM under the hood)
    os.environ["OPENAI_API_KEY"] = github_token
    os.environ["OPENAI_API_BASE"] = os.environ.get(
        "GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference"
    )

    # Run the flow
    flow = TestForgeFlow.create(config=config)
    flow.kickoff()

    click.echo("\n✓ TestForge complete. Output at: " + config.output_dir)


if __name__ == "__main__":
    cli()
