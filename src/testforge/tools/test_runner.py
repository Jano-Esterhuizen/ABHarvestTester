"""Test runner tool — executes TypeScript compilation and Playwright tests."""

import subprocess
import logging
from pathlib import Path
from crewai.tools import tool

logger = logging.getLogger("testforge")


@tool("run_tests")
def test_runner_tool(output_dir: str, test_file: str = "") -> str:
    """Execute Playwright tests with a TypeScript compilation gate.

    First runs `tsc --noEmit` to catch compile errors cheaply.
    If compilation passes, runs `npx playwright test`.

    Args:
        output_dir: Path to the generated test output directory.
        test_file: Optional specific test file to run (empty = run all).

    Returns:
        Combined output from tsc and playwright test.
    """
    output_path = Path(output_dir)

    if not output_path.exists():
        return "ERROR: Output directory does not exist"

    # Step 1: TypeScript compilation gate
    logger.info("Running tsc --noEmit (compilation gate)...")
    tsc_result = subprocess.run(
        ["npx", "tsc", "--noEmit", "--project", "tsconfig.json"],
        cwd=output_path,
        capture_output=True,
        text=True,
        timeout=30,
        shell=True,
    )

    if tsc_result.returncode != 0:
        return (
            "COMPILE_ERROR\n"
            "TypeScript compilation failed. Fix these before running tests:\n\n"
            f"{tsc_result.stdout}\n{tsc_result.stderr}"
        )

    logger.info("Compilation passed. Running Playwright tests...")

    # Step 2: Run Playwright tests
    cmd = ["npx", "playwright", "test"]
    if test_file:
        cmd.append(test_file)
    cmd.extend(["--reporter=json"])

    pw_result = subprocess.run(
        cmd,
        cwd=output_path,
        capture_output=True,
        text=True,
        timeout=300,
        shell=True,
    )

    output = f"EXIT_CODE: {pw_result.returncode}\n\n"

    # Truncate to avoid exceeding LLM token limits (8k model)
    stdout_text = pw_result.stdout[:4000] if pw_result.stdout else ""
    output += stdout_text
    if pw_result.stderr:
        output += f"\nSTDERR:\n{pw_result.stderr[:1000]}"

    return output
