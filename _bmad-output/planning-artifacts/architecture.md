---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/research/technical-agentic-ai-testing-orchestration-system-research-2026-05-21.md
  - _bmad-output/planning-artifacts/briefs/brief-AB.HarvestTester-2026-05-21/brief.md
workflowType: 'architecture'
project_name: 'TestForge'
user_name: 'TheBadenhorsts'
date: '2026-05-21'
---

# Architecture Decision Document: TestForge

## 1. System Overview

TestForge is a multi-agent AI system that autonomously generates and executes test suites for web applications. It takes three inputs — a repository path, a hosted application URL, and a credentials JSON file — and produces a comprehensive Playwright test suite covering both API and UI testing across multiple user roles.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TestForge System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────────────┐   │
│  │  CONFIG   │───▶│ ORCHESTRATOR │───▶│   SHARED STATE       │   │
│  │           │    │   (ORC)      │    │   (Graph State)      │   │
│  │• repo_path│    └──────┬───────┘    └──────────────────────┘   │
│  │• app_url  │           │                                       │
│  │• creds.json│          ▼                                       │
│  └──────────┘    ┌───────────────┐                               │
│                  │  REPO READER   │                               │
│                  │  (Discovery)   │                               │
│                  └───────┬────────┘                               │
│                          │ context_doc                            │
│                          ▼                                        │
│                  ┌───────────────┐                               │
│                  │   SCRAPER     │                               │
│                  │  (API Extract)│                               │
│                  └───────┬────────┘                               │
│                          │ api_spec                               │
│                          ▼                                        │
│               ┌──────────┴──────────┐                            │
│               │                     │                            │
│               ▼                     ▼                            │
│      ┌──────────────┐     ┌──────────────┐                      │
│      │ BE TEST      │     │ FE TEST      │                      │
│      │ WRITER       │     │ WRITER       │                      │
│      └──────┬───────┘     └──────┬───────┘                      │
│             │                     │                              │
│             └──────────┬──────────┘                              │
│                        ▼                                         │
│               ┌──────────────┐                                   │
│               │   REVIEWER   │──── feedback ────┐               │
│               │  (Run+Fix)   │                  │               │
│               └──────┬───────┘                  │               │
│                      │                          ▼               │
│                      │              ┌──────────────────┐        │
│                      │              │ WRITER (retry)    │        │
│                      │              └──────────────────┘        │
│                      ▼                                          │
│              ┌───────────────┐                                   │
│              │  OUTPUT: .spec.ts files                           │
│              └───────────────┘                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Input | Output | Tools |
|-------|-------|--------|-------|
| **Orchestrator (ORC)** | Config (repo, URL, creds) | Routing decisions | State management |
| **Repo Reader** | Repo path | Context document (tech stack, structure, roles, domain) | File system read |
| **Scraper** | Context doc + repo | API specification (endpoints, methods, schemas, auth) | File system read |
| **BE Test Writer** | API spec + context + creds | Backend .spec.ts files | File system write |
| **FE Test Writer** | API spec + context + creds + app URL | Frontend .spec.ts files | Playwright MCP |
| **Reviewer** | Generated tests + app URL + creds | Pass/fail results + fix instructions | Playwright MCP, test runner |

---

## 2. Technology Stack Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Language** | Python 3.11+ | Best framework support (LangGraph, CrewAI), fastest development |
| **Agent Framework** | CrewAI | Fastest to prototype; YAML-based agent config; competition timeline demands speed |
| **LLM (generation)** | Claude Sonnet 4 (via Anthropic API) | Best code generation quality |
| **LLM (routing/review)** | GPT-4o-mini (via OpenAI API) | Cheap, fast, good enough for routing |
| **Test Output** | TypeScript Playwright (.spec.ts) | Industry standard, rich ecosystem |
| **Browser Automation** | Playwright MCP (@playwright/mcp) | AI-native browser control via accessibility tree |
| **Integration Protocol** | MCP (Model Context Protocol) | Standard tool interface for agents |
| **State Management** | CrewAI Flow state / shared dict | Simple, in-process, sufficient for v1 |
| **Config Format** | JSON (credentials) + CLI args (repo, URL) | Simple, no overhead |

### Why CrewAI over LangGraph (for v1)

The research recommends LangGraph for production, but given the **competition timeline (tonight)**:
- CrewAI scaffolds faster (YAML agent/task definitions)
- Built-in sequential + hierarchical crew patterns
- Less boilerplate for the orchestrator pattern
- Can migrate to LangGraph later if this tool grows

---

## 3. Configuration & Input Design

### 3.1 CLI Interface

```bash
python -m testforge \
  --repo /path/to/target/repo \
  --url https://app.example.com \
  --creds ./credentials.json \
  --output ./test-output
```

### 3.2 Credentials File Schema

```json
{
  "roles": [
    {
      "name": "user",
      "username": "testuser@example.com",
      "password": "password123",
      "description": "Standard user with basic permissions"
    },
    {
      "name": "admin",
      "username": "admin@example.com",
      "password": "adminpass",
      "description": "Administrator with elevated permissions"
    },
    {
      "name": "super_admin",
      "username": "superadmin@example.com",
      "password": "superpass",
      "description": "Super administrator with full system access"
    }
  ],
  "login": {
    "url_path": "/login",
    "username_field": "email",
    "password_field": "password",
    "submit_button": "Sign In"
  }
}
```

### 3.3 Output Structure

```
test-output/
├── config/
│   └── playwright.config.ts
├── api/
│   ├── auth.spec.ts
│   ├── endpoints/
│   │   ├── users.spec.ts
│   │   ├── projects.spec.ts
│   │   └── ...
│   └── roles/
│       ├── user-permissions.spec.ts
│       ├── admin-permissions.spec.ts
│       └── super-admin-permissions.spec.ts
├── ui/
│   ├── auth/
│   │   └── login.spec.ts
│   ├── pages/
│   │   ├── dashboard.spec.ts
│   │   ├── settings.spec.ts
│   │   └── ...
│   └── roles/
│       ├── user-access.spec.ts
│       ├── admin-access.spec.ts
│       └── super-admin-access.spec.ts
├── fixtures/
│   ├── auth.fixture.ts
│   └── test-data.ts
└── README.md
```

---

## 4. Agent Architecture Details

### 4.1 Shared State Schema

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TestForgeState:
    # Inputs
    repo_path: str = ""
    app_url: str = ""
    credentials: dict = field(default_factory=dict)
    output_dir: str = "./test-output"
    
    # Repo Reader output
    context_document: str = ""          # Full context markdown
    tech_stack: dict = field(default_factory=dict)  # {language, framework, db, etc.}
    roles_discovered: list = field(default_factory=list)  # [{name, permissions, routes}]
    
    # Scraper output
    api_spec: str = ""                  # OpenAPI/Swagger YAML or structured doc
    endpoints: list = field(default_factory=list)  # [{method, path, auth, params, response}]
    ui_routes: list = field(default_factory=list)  # [{path, component, requires_auth, role}]
    
    # Test Writer outputs
    be_tests: list = field(default_factory=list)   # [{file_path, content, status}]
    fe_tests: list = field(default_factory=list)   # [{file_path, content, status}]
    
    # Reviewer outputs
    test_results: list = field(default_factory=list)  # [{file, passed, failed, errors}]
    feedback: list = field(default_factory=list)      # [{test_file, issue, fix_suggestion}]
    iteration: int = 0
    max_iterations: int = 3
```

### 4.2 Agent Definitions (CrewAI YAML)

#### agents.yaml

```yaml
repo_reader:
  role: "Codebase Analyst"
  goal: "Understand the target repository's structure, tech stack, domain model, and role/permission system"
  backstory: >
    You are a senior software engineer who excels at quickly understanding unfamiliar codebases.
    You read source code and produce clear, structured documentation about what a system does,
    how it's organized, what roles/permissions exist, and what APIs it exposes.
  tools:
    - file_read_tool
    - directory_list_tool

scraper:
  role: "API Specification Extractor"
  goal: "Extract a complete API specification from the codebase including endpoints, methods, parameters, auth requirements, and response schemas"
  backstory: >
    You are an API documentation specialist. Given a codebase context document, you dive into
    route definitions, controllers, and middleware to produce a comprehensive API specification.
    You identify which endpoints require which roles, what parameters they accept, and what they return.
  tools:
    - file_read_tool

be_test_writer:
  role: "Backend Test Engineer"
  goal: "Generate comprehensive Playwright API tests covering all endpoints across all roles"
  backstory: >
    You are a senior QA automation engineer specializing in API testing with Playwright.
    You write TypeScript Playwright tests that cover happy paths, error cases, and permission
    boundaries. You test each endpoint with each role to verify access control.
  tools:
    - file_write_tool

fe_test_writer:
  role: "Frontend Test Engineer"
  goal: "Generate comprehensive Playwright UI tests covering all pages and interactions across all roles"
  backstory: >
    You are a senior QA automation engineer specializing in UI testing with Playwright.
    You write TypeScript Playwright tests that navigate pages, fill forms, click buttons,
    and verify UI behavior. You test role-based access to pages and features.
  tools:
    - file_write_tool
    - playwright_mcp_tool

reviewer:
  role: "Test Quality Reviewer"
  goal: "Execute generated tests, analyze failures, and provide actionable fix instructions"
  backstory: >
    You are a senior QA lead who runs test suites, diagnoses why tests fail, and provides
    clear, specific instructions on how to fix them. You distinguish between test bugs
    (wrong selector, wrong assertion) and application bugs (genuine defects to report).
  tools:
    - test_runner_tool
    - playwright_mcp_tool
    - file_read_tool
```

### 4.3 Orchestration Flow (CrewAI Flow)

```python
from crewai.flow.flow import Flow, listen, start, router

class TestForgeFlow(Flow):
    
    @start()
    def load_config(self):
        """Load repo path, app URL, and credentials from CLI args"""
        # Parse config, validate inputs exist
        return self.state
    
    @listen(load_config)
    def read_repository(self):
        """Repo Reader agent: produce context document"""
        # Run repo_reader crew
        return self.state
    
    @listen(read_repository)
    def extract_api_spec(self):
        """Scraper agent: produce API specification"""
        # Run scraper crew
        return self.state
    
    @listen(extract_api_spec)
    def write_tests(self):
        """BE + FE Test Writers run in parallel"""
        # Run both test writer crews concurrently
        return self.state
    
    @listen(write_tests)
    @router()
    def review_tests(self):
        """Reviewer: run tests, check results, decide next step"""
        # Run reviewer crew
        if self.state.all_passing or self.state.iteration >= self.state.max_iterations:
            return "complete"
        else:
            return "retry"
    
    @listen("retry")
    def fix_tests(self):
        """Send feedback to writers, regenerate failing tests"""
        self.state.iteration += 1
        # Re-run writers with feedback context
        return self.state  # Routes back to review_tests
    
    @listen("complete")
    def deliver_results(self):
        """Output final test suite and summary report"""
        # Write results, generate README
        return self.state
```

---

## 5. Integration Architecture

### 5.1 Playwright MCP Integration

The FE Test Writer and Reviewer agents use Playwright MCP for browser interaction:

```
┌─────────────┐     MCP (stdio)     ┌──────────────────┐
│  FE Writer  │◀───────────────────▶│  @playwright/mcp │
│  Agent      │                      │  Server          │
└─────────────┘                      └────────┬─────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │  Chromium Browser │
                                     │  (target app)    │
                                     └──────────────────┘
```

**Playwright MCP capabilities used:**
- `playwright_navigate` — navigate to app pages
- `playwright_click` — interact with UI elements
- `playwright_fill` — enter form data (login, etc.)
- `playwright_get_visible_text` — read page content for assertions
- `playwright_screenshot` — capture state for debugging

### 5.2 File System Tools

Custom MCP tools for repo reading and test file writing:

| Tool | Purpose |
|------|---------|
| `file_read_tool` | Read source files from target repo |
| `directory_list_tool` | List directory contents recursively |
| `file_write_tool` | Write generated .spec.ts files to output dir |
| `test_runner_tool` | Execute `npx playwright test` and capture results |

### 5.3 LLM Provider Configuration

```python
# Environment variables required
ANTHROPIC_API_KEY=sk-ant-...     # For Claude Sonnet (test generation)
OPENAI_API_KEY=sk-...            # For GPT-4o-mini (routing, review)
```

Agent-to-model mapping:
| Agent | Model | Reason |
|-------|-------|--------|
| Repo Reader | Claude Sonnet 4 | Complex code comprehension |
| Scraper | Claude Sonnet 4 | Structured extraction from code |
| BE Test Writer | Claude Sonnet 4 | Code generation quality |
| FE Test Writer | Claude Sonnet 4 | Code generation quality |
| Reviewer | GPT-4o-mini | Pattern matching, cheaper for iteration |
| Orchestrator | GPT-4o-mini | Routing decisions only |

---

## 6. Implementation Patterns & Conventions

### 6.1 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python modules | snake_case | `repo_reader.py` |
| Python classes | PascalCase | `TestForgeFlow` |
| Agent YAML files | kebab-case | `agents.yaml`, `tasks.yaml` |
| Output test files | kebab-case.spec.ts | `user-permissions.spec.ts` |
| Config keys | snake_case | `repo_path`, `app_url` |

### 6.2 Error Handling

| Scenario | Handling |
|----------|----------|
| Repo path doesn't exist | Fail fast with clear error message |
| App URL unreachable | Fail fast — can't test what's not running |
| LLM API error | Retry 2x with exponential backoff, then fail |
| Test generation produces invalid TS | Reviewer catches via compile check, feeds back |
| Playwright can't find element | Reviewer reports as test bug, writer adjusts selector strategy |
| Max iterations reached | Stop, output what works, report what doesn't |

### 6.3 Logging & Observability

```python
# Structured logging for every agent action
import logging

logger = logging.getLogger("testforge")

# Log levels:
# INFO  - Agent started, completed, produced output
# DEBUG - LLM prompts, intermediate state
# WARN  - Retries, fallbacks
# ERROR - Failures that stop execution
```

### 6.4 Test Output Standards

All generated tests MUST follow these patterns:

```typescript
// Standard imports
import { test, expect } from '@playwright/test';

// Fixture-based auth (generated in fixtures/auth.fixture.ts)
import { test as authTest } from '../fixtures/auth.fixture';

// Test structure: describe blocks by feature, test blocks by scenario
test.describe('Feature: [feature name]', () => {
  test('[role] can [action]', async ({ page }) => {
    // Arrange - Navigate, set up state
    // Act - Perform the action
    // Assert - Verify the outcome
  });

  test('[role] cannot [action] (permission denied)', async ({ page }) => {
    // Negative test for role boundaries
  });
});
```

---

## 7. Project Structure

```
testforge/
├── pyproject.toml                 # Project metadata, dependencies
├── README.md                      # Setup + usage instructions
├── .env.example                   # Required environment variables
├── credentials.example.json       # Example credentials file
│
├── src/
│   └── testforge/
│       ├── __init__.py
│       ├── __main__.py            # CLI entry point
│       ├── config.py              # Config loading + validation
│       ├── state.py               # TestForgeState dataclass
│       ├── flow.py                # TestForgeFlow (orchestrator)
│       │
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── repo_reader/
│       │   │   ├── __init__.py
│       │   │   ├── agent.py       # Crew definition
│       │   │   └── config/
│       │   │       ├── agents.yaml
│       │   │       └── tasks.yaml
│       │   ├── scraper/
│       │   │   ├── __init__.py
│       │   │   ├── agent.py
│       │   │   └── config/
│       │   │       ├── agents.yaml
│       │   │       └── tasks.yaml
│       │   ├── be_test_writer/
│       │   │   ├── __init__.py
│       │   │   ├── agent.py
│       │   │   └── config/
│       │   │       ├── agents.yaml
│       │   │       └── tasks.yaml
│       │   ├── fe_test_writer/
│       │   │   ├── __init__.py
│       │   │   ├── agent.py
│       │   │   └── config/
│       │   │       ├── agents.yaml
│       │   │       └── tasks.yaml
│       │   └── reviewer/
│       │       ├── __init__.py
│       │       ├── agent.py
│       │       └── config/
│       │           ├── agents.yaml
│       │           └── tasks.yaml
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── file_tools.py      # Read/write/list files
│       │   ├── test_runner.py     # Execute playwright tests
│       │   └── playwright_mcp.py  # MCP client wrapper
│       │
│       └── templates/
│           ├── playwright.config.template.ts
│           ├── auth.fixture.template.ts
│           └── base.spec.template.ts
│
├── tests/                         # Tests for TestForge itself
│   ├── unit/
│   │   ├── test_config.py
│   │   └── test_state.py
│   └── integration/
│       └── test_flow.py
│
└── docs/
    └── architecture.md            # This document (symlinked)
```

---

## 8. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Credentials in config file | `.gitignore` the creds file; document in README |
| LLM API keys in env | `.env` file, never committed; `.env.example` as template |
| Repo read access | Only reads, never writes to target repo |
| Generated tests contain creds | Auth fixture uses env vars, not hardcoded passwords |
| Playwright browser sessions | Isolated per run; browser closed on completion |
| Target app access | Tests run against provided URL only; no network scanning |

---

## 9. Deployment & Execution

### 9.1 Local Development (Competition Demo)

```bash
# 1. Clone and install
git clone <repo>
cd testforge
pip install -e .

# 2. Set up environment
cp .env.example .env
# Edit .env with API keys

# 3. Prepare credentials
cp credentials.example.json credentials.json
# Edit with target app credentials

# 4. Run TestForge
python -m testforge \
  --repo /path/to/harvest-replica \
  --url http://localhost:3000 \
  --creds ./credentials.json \
  --output ./generated-tests

# 5. Review and run generated tests
cd generated-tests
npx playwright test
```

### 9.2 Dependencies

```toml
[project]
name = "testforge"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "crewai[tools]>=0.121.0",
    "anthropic>=0.52.0",
    "openai>=1.82.0",
    "pyyaml>=6.0",
    "click>=8.1.0",
]
```

### 9.3 Prerequisites on Target Machine

- Python 3.11+
- Node.js 18+ (for Playwright test execution)
- `npx playwright install` (browser binaries)
- API keys for Claude + OpenAI

---

## 10. Bounded Iteration & Convergence

The feedback loop (write → run → review → fix) is bounded to prevent cost runaway:

```
Iteration 1: Generate all tests → run → review
Iteration 2: Fix failing tests → run → review  
Iteration 3: Final fix attempt → run → report

After iteration 3: STOP. Report results as-is.
```

**Convergence criteria (stop early if met):**
- All tests pass
- No new fixes possible (same failures repeated)
- Only application bugs remain (not test bugs)

**Failure categorization by Reviewer:**

| Category | Action |
|----------|--------|
| **Test bug** (wrong selector, bad assertion) | Feed back to Writer for fix |
| **App bug** (genuine defect found) | Report as finding — do NOT fix the test |
| **Flaky** (passes sometimes) | Add retry annotation, report as warning |
| **Environment** (app not running, timeout) | Report as blocked — stop iteration |

---

## 11. Data Flow Diagram

```
CONFIG ──▶ ORC ──▶ REPO READER ──▶ SCRAPER ──▶ WRITERS ──▶ REVIEWER ──▶ OUTPUT
                       │                │           │            │
                       ▼                ▼           ▼            ▼
                  context.md      api-spec.md   *.spec.ts   results.json
                  (roles,         (endpoints,   (tests per   (pass/fail,
                   stack,          schemas,      role per     feedback)
                   domain)         auth reqs)    endpoint)
```

---

## 12. Competition Demo Strategy (Architectural Support)

The architecture directly supports the demo flow:

1. **Show config** — 3 simple inputs (repo, URL, creds JSON)
2. **Show agents starting** — Verbose logging shows each agent activating
3. **Show discovery** — Repo Reader's context document appears in real-time
4. **Show generation** — Test files appearing in output directory
5. **Show execution** — Playwright running tests, green/red results
6. **Show the bug** — A failing test that found a real issue in the dev team's code
7. **Show the report** — Summary of coverage, findings, role-based test matrix

**Key architectural decision for demo impact:** All output is written to files as it's produced (not buffered until the end). This lets the demo show progress in real-time.

---

## Architectural Decisions Summary (ADR Log)

| # | Decision | Choice | Status |
|---|----------|--------|--------|
| ADR-001 | Agent framework | CrewAI (speed to prototype) | Accepted |
| ADR-002 | Primary LLM | Claude Sonnet 4 via Anthropic API | Accepted |
| ADR-003 | Routing LLM | GPT-4o-mini via OpenAI API | Accepted |
| ADR-004 | Test framework output | Playwright (TypeScript) | Accepted |
| ADR-005 | Browser control | Playwright MCP server | Accepted |
| ADR-006 | Configuration model | CLI args + JSON creds file | Accepted |
| ADR-007 | State management | In-process shared state (dataclass) | Accepted |
| ADR-008 | Iteration bound | Max 3 review cycles | Accepted |
| ADR-009 | Parallel execution | BE + FE writers run concurrently | Accepted |
| ADR-010 | Output format | Files written incrementally (demo-friendly) | Accepted |
| ADR-011 | Role-based testing | Creds JSON defines roles; Reader discovers permissions | Accepted |
| ADR-012 | Project agnostic | No hardcoded app assumptions; all from discovery | Accepted |
