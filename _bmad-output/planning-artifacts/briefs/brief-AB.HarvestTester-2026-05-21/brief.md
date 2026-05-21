---
title: "TestForge — Agentic AI Test Orchestration System"
status: draft
created: 2026-05-21
updated: 2026-05-21
---

# Product Brief: TestForge

## Executive Summary

TestForge is a project-agnostic, multi-agent AI system that autonomously discovers a codebase, extracts its API surface, generates comprehensive front-end and back-end tests, executes them, and self-corrects through feedback loops — all without human intervention beyond pointing it at a repository.

It exists because QA teams are bottlenecked: developers ship faster than testers can write coverage. TestForge collapses the time from "new project exists" to "comprehensive test suite running" from weeks to hours. Any team at Drawbridge can point it at their repo and get executable Playwright tests — no test-writing required.

This is a competition entry built to win, but designed to outlive the competition as a real tool QA teams adopt daily.

## The Problem

QA teams face a recurring pattern: a new project appears (or an existing one has no tests), and the team must manually read the codebase, understand the API surface, write tests, run them, debug failures, and iterate. For smaller projects this takes days. For each new project, the cycle repeats from scratch.

The cost: teams ship without adequate test coverage, bugs reach production, and QA becomes the bottleneck rather than the enabler. Developers move fast; QA can't keep up with manual test authoring.

## The Solution

TestForge is a team of AI agents that replicate what a senior QA engineer does — but autonomously and in minutes:

1. **Reads the repo** — understands the codebase structure, tech stack, domain, and role/permission model
2. **Extracts the API surface** — discovers endpoints, contracts, UI components, and which roles can access what
3. **Writes tests** — generates API contract tests and UI tests using Playwright, testing each role (user, admin, super-admin) against appropriate scenarios
4. **Runs and reviews** — executes tests against the live hosted URL, diagnoses failures, feeds corrections back to the writers
5. **Delivers** — outputs a ready-to-run test suite with proper structure and tagging

The system is project-agnostic with minimal configuration:
- **Repo path** — local path or git URL to the codebase
- **Hosted URL** — where the running application is accessible (for Playwright to interact with)
- **Credentials file** — a JSON config providing login details for each role (e.g. user, admin, super-admin) so the system can test across permission boundaries

That's it. The Repo Reader agent handles discovery of roles, rights, and application structure automatically.

## What Makes This Different

- **Zero-config discovery** — No manual Swagger authoring or test plan writing. It reads the code directly.
- **Self-correcting** — Tests that fail get diagnosed and rewritten automatically (up to 3 iterations).
- **Project-agnostic** — Not built for one app. Works on any smaller web project with an API layer and/or UI.
- **Full stack** — Covers both API contract testing AND UI testing in one pass.
- **Immediate value** — Point at repo, get tests. No ramp-up time per project.

The honest moat: execution speed and the feedback loop. The individual pieces (LLM code generation, Playwright) exist — the value is orchestrating them into a seamless pipeline that actually works end-to-end.

## Who This Serves

**Primary: QA Engineers at Agile Bridge**
- Need test coverage for projects they're assigned to
- Don't have time to write everything from scratch
- Want a starting test suite they can review, trust, and extend
- Working on smaller/medium-complexity web projects

**Secondary: Development Teams**
- Want basic test coverage without waiting for QA
- Can run TestForge themselves to validate their work before handoff

## Success Criteria

| Signal | Measure |
|--------|---------|
| Generates valid, executable tests | >80% of generated tests compile and run without error |
| Finds real issues | Detects at least 3 genuine bugs/gaps in the target Harvest replica |
| Works without hand-holding | Runs end-to-end with only a repo URL as input |
| Fast enough to matter | Full pipeline completes in <1 hour for a small project |
| Impresses judges | Clear demo showing autonomous discovery → test generation → execution → results |
| Reusable beyond competition | Works on at least 2 different repos without code changes |

## Scope

### In (v1 — competition demo)

- Single repo input (local path or git URL) + hosted app URL
- Credentials JSON config for multi-role testing (user, admin, super-admin)
- Codebase analysis and context generation (including role/permission discovery)
- API endpoint discovery and contract extraction
- Playwright test generation (API + UI) across all configured roles
- Role-based test scenarios (same action tested with different permission levels)
- Automated test execution with failure diagnosis
- One feedback loop iteration (write → run → fix → run)
- Structured output: organized .spec.ts files

### Out (v1)

- Multi-repo orchestration
- CI/CD integration
- Historical test tracking or regression detection
- Performance/load testing
- Security testing
- Support for massive/enterprise-scale codebases
- Complex OAuth/SSO integration (credentials are provided via config, not discovered)

## Vision

If TestForge wins and works: it becomes the default first step when any QA team at Drawbridge picks up a new project. "Run TestForge, review what it found, extend from there." Over time it grows to handle larger projects, learns from past test suites, and integrates into CI/CD — new code gets tested by AI before it reaches a human reviewer.

The 6-month picture: every new project at Drawbridge has test coverage within its first day of existence, generated autonomously and maintained through change detection.

## Technical Approach (Summary)

- **Architecture**: 5 specialized AI agents + 1 orchestrator (graph-based workflow)
- **Framework**: LangGraph or CrewAI (Python)
- **Test Output**: Playwright TypeScript (.spec.ts)
- **Integration**: MCP protocol for tool access
- **LLMs**: Claude Sonnet (generation) + GPT-4o-mini (routing)
- **Key Pattern**: Orchestrator-Worker with Evaluator-Optimizer feedback loop

*Full technical research available in: `_bmad-output/planning-artifacts/research/`*

## Competition Strategy

**Demo flow for maximum impact:**
1. Show an empty test folder
2. Point TestForge at the Harvest replica repo (live)
3. Watch agents discover, extract, write, execute
4. Show the resulting test suite — organized, tagged, passing
5. Show a failing test that found a real bug in the dev team's code
6. "This took X minutes. A human would take Y days."

**The punchline**: "We didn't write tests. We wrote the thing that writes tests."
