"""Reviewer — runs tests via subprocess, uses LLM only to analyze failures."""

import json
import logging
import os
import subprocess

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.tools.file_tools import file_read_tool
from testforge.tools.test_runner import test_runner_tool
from testforge.llm import get_llm

logger = logging.getLogger("testforge")


@CrewBase
class ReviewerCrew:
    """Crew that analyzes test failures and provides fix suggestions."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["reviewer"],
            tools=[file_read_tool, test_runner_tool],
            llm=get_llm(),
            verbose=True,
        )

    @task
    def review_tests(self) -> Task:
        return Task(config=self.tasks_config["review_tests"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def _run_tests(output_dir: str) -> tuple[str, list[dict]]:
    """Run Playwright tests via subprocess, return (raw_output, results)."""
    test_dir = os.path.join(output_dir, "tests")
    if not os.path.isdir(test_dir):
        return "No tests directory found", []

    try:
        result = subprocess.run(
            "npx playwright test --reporter=json",
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
            env={**os.environ, "BASE_URL": os.environ.get("BASE_URL", "http://localhost:3000")},
        )
        raw = result.stdout + result.stderr

        # Try to parse JSON reporter output
        results = []
        try:
            report = json.loads(result.stdout)
            for suite in report.get("suites", []):
                for spec in suite.get("specs", []):
                    for test in spec.get("tests", []):
                        status = test.get("status", "unknown")
                        results.append({
                            "title": spec.get("title", ""),
                            "status": status,
                            "error": test.get("results", [{}])[0].get("error", {}).get("message", "")
                            if status != "passed" else "",
                        })
        except (json.JSONDecodeError, KeyError):
            # Fallback: just record exit code
            results.append({
                "title": "all",
                "status": "passed" if result.returncode == 0 else "failed",
                "error": raw[:500] if result.returncode != 0 else "",
            })

        return raw[:3000], results
    except subprocess.TimeoutExpired:
        return "Tests timed out after 120s", [{"title": "all", "status": "timeout", "error": "timeout"}]
    except FileNotFoundError:
        return "npx not found — Node.js required", [{"title": "all", "status": "error", "error": "npx not found"}]


def run_reviewer(state: TestForgeState) -> None:
    """Run tests, then use LLM only if there are failures to analyze."""
    raw_output, results = _run_tests(state.output_dir)
    state.test_results = results

    failures = [r for r in results if r["status"] != "passed"]
    if not failures:
        logger.info("All tests passed — no reviewer analysis needed")
        state.feedback = []
        return

    # Truncate failure info for 8k token budget
    failures_text = "\n".join(
        f"- {f['title']}: {f['error'][:200]}" for f in failures[:10]
    )

    logger.info(f"Analyzing {len(failures)} failures via LLM")

    crew = ReviewerCrew()
    result = crew.crew().kickoff(
        inputs={
            "output_dir": state.output_dir,
            "test_plan": state.test_plan,
            "test_results": raw_output[:1500],
            "failures": failures_text[:2000],
        }
    )

    state.feedback = _parse_feedback(str(result))


def _parse_feedback(output: str) -> list[dict]:
    """Parse reviewer analysis into structured feedback for writers."""
    feedback = []
    lines = output.split("\n")
    for line in lines:
        if "TEST_BUG:" in line:
            parts = line.split("|")
            if len(parts) >= 3:
                feedback.append({
                    "test_file": parts[1].strip(),
                    "issue": parts[2].strip(),
                    "fix_suggestion": parts[3].strip() if len(parts) > 3 else "",
                })
    # Fallback: treat entire output as one feedback item if no structured format
    if not feedback and output.strip():
        feedback.append({
            "test_file": "general",
            "issue": output[:500],
            "fix_suggestion": output[500:1000] if len(output) > 500 else "",
        })
    return feedback
