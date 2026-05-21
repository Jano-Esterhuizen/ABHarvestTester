# TestForge

> **"We didn't write tests. We wrote the thing that writes tests."**

A project-agnostic, multi-agent AI system that autonomously reads a codebase, plans a test strategy, generates comprehensive Playwright test suites, executes them, and self-corrects through feedback loops — with no human intervention beyond three inputs.

Built for Agile Bridge using [CrewAI](https://crewai.com) + [GitHub Models](https://github.com/marketplace/models) + [Playwright](https://playwright.dev).

---

## Three Inputs. Full Test Suite.

```bash
testforge \
  --repo  ./path/to/your/project \
  --url   https://your-app.example.com \
  --creds credentials.json
```

That's all TestForge needs. Everything else is discovered automatically.

---

## Agent Pipeline

TestForge runs **7 specialised AI agents** in a fixed, gated pipeline. Each agent has one responsibility and passes its output to the next.

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                        YOU PROVIDE                                  │
  │   --repo path/to/project   --url https://app.com   --creds creds.json│
  └────────────────────────────┬────────────────────────────────────────┘
                               │
                               ▼
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║  PHASE 1 — DISCOVERY                                                 ║
  ║                                                                       ║
  ║  ┌─────────────────┐                                                 ║
  ║  │  REPO READER    │  Reads your codebase. Discovers:                ║
  ║  │                 │  • Tech stack and framework                     ║
  ║  │  Model: GPT-4.1 │  • Folder structure and module boundaries       ║
  ║  │  Tools: read,   │  • Role and permission model                    ║
  ║  │         list    │  • Auth mechanism (JWT, session, API key)       ║
  ║  └────────┬────────┘                                                 ║
  ║           │  Outputs → context-document.md (≤4000 tokens)           ║
  ╚═══════════╪═══════════════════════════════════════════════════════════╝
              │
              ▼
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║  PHASE 2 — API EXTRACTION                                            ║
  ║                                                                       ║
  ║  ┌─────────────────┐                                                 ║
  ║  │    SCRAPER      │  Extracts the full API surface:                 ║
  ║  │                 │  • Every endpoint (method, path, params)        ║
  ║  │  Model: GPT-4.1 │  • Request and response schemas                ║
  ║  │  Tools: read,   │  • Auth requirements per endpoint               ║
  ║  │         MCP*    │  • Which roles can access what                  ║
  ║  └────────┬────────┘                                                 ║
  ║           │  * Uses dev-provided MCP server if available,           ║
  ║           │    otherwise reads source code directly                  ║
  ║           │  Outputs → api-spec.md                                   ║
  ╚═══════════╪═══════════════════════════════════════════════════════════╝
              │
              ▼
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║  PHASE 3 — FRAMEWORK SCAFFOLD                                        ║
  ║                                                                       ║
  ║  ┌─────────────────┐                                                 ║
  ║  │    SCAFFOLD     │  Creates the output directory structure:        ║
  ║  │   (no LLM)      │  • playwright.config.ts (with your app URL)    ║
  ║  │                 │  • package.json + tsconfig.json                 ║
  ║  │  Pure Python    │  • core/types/enums.ts (your roles as enums)   ║
  ║  │                 │  • data/credentials/accounts.ts                 ║
  ║  │                 │  • fixtures/auth.fixture.ts                     ║
  ║  └────────┬────────┘  • reports/, tests/, ui/ directories           ║
  ║           │  Skipped automatically if framework already exists       ║
  ║           │  (incremental mode — adds tests without overwriting)     ║
  ╚═══════════╪═══════════════════════════════════════════════════════════╝
              │
              ▼
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║  PHASE 4 — TEST PLANNING                                             ║
  ║                                                                       ║
  ║  ┌─────────────────┐                                                 ║
  ║  │   QA ANALYST    │  Thinks adversarially. Produces a structured   ║
  ║  │                 │  Gherkin test plan covering all three layers:   ║
  ║  │  Model: GPT-4.1 │                                                 ║
  ║  │  Tools: none    │  @api scenarios  → for BE Test Writer          ║
  ║  │  (pure thought) │  @ui scenarios   → for FE Test Writer          ║
  ║  │                 │  @e2e scenarios  → for E2E Test Writer          ║
  ║  └────────┬────────┘                                                 ║
  ║           │  Outputs → test-plan.md (human-readable Gherkin)        ║
  ║           │  Visible on disk immediately — review before writers run ║
  ╚═══════════╪═══════════════════════════════════════════════════════════╝
              │
              ▼
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║  PHASE 5 — TEST GENERATION                                           ║
  ║                                                                       ║
  ║  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ║
  ║  │  BE TEST WRITER │   │  FE TEST WRITER │   │ E2E TEST WRITER │   ║
  ║  │                 │   │                 │   │                 │   ║
  ║  │ Reads:          │   │ Reads:          │   │ Reads:          │   ║
  ║  │ test-plan.md    │   │ test-plan.md    │   │ test-plan.md    │   ║
  ║  │ (@api only)     │   │ (@ui only)      │   │ (@e2e only)     │   ║
  ║  │                 │   │                 │   │                 │   ║
  ║  │ Writes:         │   │ Writes:         │   │ Writes:         │   ║
  ║  │ tests/api/      │   │ ui/pages/       │   │ tests/e2e/      │   ║
  ║  │ *.api.spec.ts   │   │ ui/objects/     │   │ *.e2e.spec.ts   │   ║
  ║  │                 │   │ ui/models/      │   │                 │   ║
  ║  │ Tools: read,    │   │ tests/ui/       │   │ Tools: read,    │   ║
  ║  │        write    │   │ *.ui.spec.ts    │   │        write,   │   ║
  ║  │                 │   │                 │   │        MCP      │   ║
  ║  │                 │   │ Tools: read,    │   │                 │   ║
  ║  │                 │   │        write,   │   │                 │   ║
  ║  │                 │   │        MCP      │   │                 │   ║
  ║  └────────┬────────┘   └────────┬────────┘   └────────┬────────┘   ║
  ║           │                     │                     │             ║
  ║           │  Also writes:       │  Also writes:       │             ║
  ║           │  reports/           │  reports/           │             ║
  ║           │  be-test-coverage   │  fe-test-coverage   │             ║
  ║           │  .md                │  .md                │             ║
  ╚═══════════╪═════════════════════╪═════════════════════╪═════════════╝
              └──────────┬──────────┘                     │
                         └──────────────┬─────────────────┘
                                        │
                                        ▼
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║  PHASE 6 — REVIEW LOOP  (up to 3 iterations)                        ║
  ║                                                                       ║
  ║  ┌─────────────────────────────────────────────────────────────┐    ║
  ║  │                       REVIEWER                              │    ║
  ║  │                                                             │    ║
  ║  │  Model: GPT-4o-mini   Tools: test_runner, read, Playwright  │    ║
  ║  │                                                             │    ║
  ║  │  Step 1 — Compilation gate:  npx tsc --noEmit              │    ║
  ║  │  Step 2 — Test execution:    npx playwright test           │    ║
  ║  │  Step 3 — Categorise every failure:                        │    ║
  ║  │                                                             │    ║
  ║  │  TEST_BUG      wrong selector, bad assertion  → fix it     │    ║
  ║  │  APP_BUG       genuine defect in the app      → report it  │    ║
  ║  │  DATA_DEPENDENT missing test data             → report it  │    ║
  ║  │  FLAKY         intermittent timing issue       → add retry  │    ║
  ║  │  ENVIRONMENT   app unreachable                → STOP       │    ║
  ║  └──────────────────────────┬──────────────────────────────────┘    ║
  ║                             │                                        ║
  ║         ┌───────────────────┴──────────────────┐                    ║
  ║         │                                      │                    ║
  ║         ▼                                      ▼                    ║
  ║   TEST_BUGs found                    All passing  OR                ║
  ║   AND iteration < 3                  Max iterations reached          ║
  ║         │                            OR only APP_BUG remain         ║
  ║         ▼                                      │                    ║
  ║   Writers re-run with                          │                    ║
  ║   fix instructions                             ▼                    ║
  ║   (loop back to Phase 5)               ┌───────────────┐           ║
  ║                                         │   COMPLETE    │           ║
  ╚═════════════════════════════════════════╪═══════════════╪═══════════╝
                                            │               │
                                            ▼               ▼
                                     test-output/      Terminal
                                     README.md         summary
```

---

## What Each Agent Produces

| Agent | Reads | Writes to disk | Terminal output |
|-------|-------|----------------|-----------------|
| **Repo Reader** | Source files from `--repo` | *(in memory)* | Agent reasoning |
| **Scraper** | Repo files + MCP server | *(in memory)* | Agent reasoning |
| **Scaffold** | State config | Full framework skeleton | Progress logs |
| **QA Analyst** | context-doc + api-spec | `test-plan.md` | Agent reasoning |
| **BE Test Writer** | `test-plan.md` + api-spec | `tests/api/*.api.spec.ts` + `reports/be-test-coverage.md` | 🧪 file written per spec file |
| **FE Test Writer** | `test-plan.md` + context | `ui/**` POM files + `tests/ui/*.ui.spec.ts` + `reports/fe-test-coverage.md` | 🧪 file written per file |
| **E2E Test Writer** | `test-plan.md` + api-spec | `tests/e2e/*.e2e.spec.ts` | 🧪 file written per spec file |
| **Reviewer** | All generated tests | `results.json` | Pass/fail counts per iteration |

---

## Output Directory Structure

```
test-output/
│
├── test-plan.md                    ← QA Analyst's Gherkin test plan (review this first)
│
├── reports/
│   ├── be-test-coverage.md         ← Which @api scenarios were implemented / skipped
│   └── fe-test-coverage.md         ← Which @ui scenarios were implemented / skipped
│
├── playwright.config.ts            ← Pre-configured with your app URL
├── package.json                    ← @playwright/test dependency
├── tsconfig.json                   ← TypeScript config with path aliases
│
├── core/
│   ├── types/enums.ts              ← Your roles as a TypeScript enum
│   └── constants/app.constants.ts  ← BASE_URL and timeout constants
│
├── data/
│   └── credentials/accounts.ts    ← Role → credentials mapping (uses env vars)
│
├── fixtures/
│   └── auth.fixture.ts             ← Reusable authenticated page fixture
│
├── ui/                             ← Three-tier Page Object Model (FE Writer)
│   ├── pages/[feature]/            ← Selector constants only
│   ├── objects/[feature]/          ← Locator accessors only
│   └── models/[feature]/           ← Business logic and workflows
│
├── tests/
│   ├── api/                        ← BE Writer output
│   │   ├── auth.api.spec.ts
│   │   ├── projects.api.spec.ts
│   │   └── roles/
│   │       ├── director-permissions.spec.ts
│   │       └── analyst-permissions.spec.ts
│   │
│   ├── ui/                         ← FE Writer output
│   │   ├── login/login.ui.spec.ts
│   │   └── dashboard/dashboard.ui.spec.ts
│   │
│   └── e2e/                        ← E2E Writer output
│       └── project-lifecycle.e2e.spec.ts
│
└── results.json                    ← Playwright JSON reporter output (after Reviewer runs)
```

---

## The Test Plan Format (Gherkin)

The QA Analyst produces `test-plan.md` in [Gherkin](https://cucumber.io/docs/gherkin/) syntax — the same format used by BDD frameworks like Cucumber. It is intentionally human-readable so non-technical stakeholders can review it before any code is written.

```gherkin
Feature: Projects

  @P0 @api @director
  Scenario: director can create a project with valid data
    Given a director user is authenticated with a valid token
    When they send POST to /api/projects with a valid name and description
    Then the response status should be 201
    And the response body should contain an id field

  @P0 @api @analyst
  Scenario: analyst is denied project creation
    Given an analyst user is authenticated
    When they send POST to /api/projects
    Then the response status should be 403
    And the response body should contain an error message
```

**Tags and what they mean:**

| Tag | Meaning |
|-----|---------|
| `@P0` | Critical — blocks release if failing |
| `@P1` | High — must be tested |
| `@P2` | Medium — should be tested |
| `@P3` | Low — nice to have |
| `@api` | Implemented by the BE Test Writer |
| `@ui` | Implemented by the FE Test Writer |
| `@e2e` | Implemented by the E2E Test Writer |
| `@director` | Test runs authenticated as the director role |
| `@pm` | Test runs authenticated as the pm role |
| `@analyst` | Test runs authenticated as the analyst role |

---

## The Coverage Reports

After generating tests, each writer produces a coverage report showing exactly which Gherkin scenarios from the test plan were implemented and which were skipped.

**`reports/be-test-coverage.md`** example:

```markdown
# BE Test Coverage Report

## Summary
| Total @api Scenarios | Implemented | Skipped |
|----------------------|-------------|---------|
| 24                   | 22          | 2       |

## Scenario Coverage

### Feature: Authentication
| Scenario | Priority | Role | Status | File |
|----------|----------|------|--------|------|
| director can log in | P0 | director | ✅ Implemented | tests/api/auth.api.spec.ts |
| invalid password rejected | P0 | all | ✅ Implemented | tests/api/auth.api.spec.ts |
| unauthenticated request blocked | P0 | — | ✅ Implemented | tests/api/auth.api.spec.ts |
```

---

## The Feedback Loop

The Reviewer runs up to **3 times**. On each pass it distinguishes between test problems and application problems:

```
Iteration 1:  Reviewer runs → 5 TEST_BUGs found → Writers fix them → loop
Iteration 2:  Reviewer runs → 2 new TEST_BUGs + 1 APP_BUG → Writers fix 2 → loop
Iteration 3:  Reviewer runs → 1 TEST_BUG still failing → STOP (max iterations)
              Remaining failures documented in results — app bugs reported as findings
```

**Only `TEST_BUG` failures go back to writers.** `APP_BUG` failures are reported as genuine defects found in the target application — the test is correct, the app is wrong.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Playwright test execution)
- A GitHub Token with [GitHub Models](https://github.com/marketplace/models) access

### Installation

```bash
# Clone and install
git clone <repo>
cd ABHarvestTester
pip install -e .

# Install Playwright browsers
npx playwright install chromium
```

### Configuration

```bash
# 1. Set up your GitHub token
cp .env.example .env
# Edit .env — set GITHUB_TOKEN=ghp_your_token_here

# 2. Set up target app credentials
cp credentials.example.json credentials.json
# Edit credentials.json with your test account logins
```

**`credentials.json` format:**
```json
{
  "roles": [
    {
      "name": "director",
      "username": "director@example.com",
      "password": "TestPass123",
      "description": "Director with highest permissions"
    },
    {
      "name": "analyst",
      "username": "analyst@example.com",
      "password": "TestPass123",
      "description": "Analyst with basic permissions"
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

### Run

```bash
# Basic
testforge --repo ./path/to/project --url https://app.example.com --creds credentials.json

# With optional MCP server (authoritative API spec from the dev team)
testforge --repo ./project --url https://app.example.com --creds creds.json --mcp-config mcp.json

# Custom output directory
testforge --repo ./project --url https://app.example.com --creds creds.json --output ./my-tests

# Force overwrite existing output
testforge --repo ./project --url https://app.example.com --creds creds.json --force
```

### After the run

```bash
cd test-output

# Install test dependencies
npm install

# Run the generated test suite
npx playwright test

# Open the HTML report
npx playwright show-report
```

---

## CLI Reference

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--repo` | ✅ | — | Path to the target repository |
| `--url` | ✅ | — | Live URL of the running application |
| `--creds` | ✅ | — | Path to credentials JSON file |
| `--output` | ❌ | `./test-output` | Where to write the generated test suite |
| `--mcp-config` | ❌ | — | Dev-provided MCP server config (authoritative API source) |
| `--force` | ❌ | `false` | Overwrite existing output directory |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | ✅ | GitHub personal access token with Models API access |
| `GITHUB_MODELS_ENDPOINT` | ❌ | Override the GitHub Models API URL (default: `https://models.github.ai/inference`) |

---

## Architecture Notes

**Why CrewAI Flow?** The pipeline is deterministic Python — routing decisions are coded `if/else`, not LLM calls. The LLMs handle understanding and generation; the orchestrator handles sequencing.

**Why GitHub Models?** Single token, no separate Anthropic/OpenAI accounts needed. The `gpt-4.1` model handles complex generation (repo reading, test writing). `gpt-4o-mini` handles the Reviewer's pattern-matching work cheaply.

**Why Gherkin?** The QA Analyst outputs Gherkin so the test plan is readable by non-technical stakeholders before a single line of test code is written. Writers map each `Scenario` to exactly one `test()` block, creating a traceable link from business intent to automation.

**Why Three-Tier POM for FE tests?** Pages (selectors) → Objects (locators) → Models (logic) keeps UI tests maintainable. When a selector changes, you update one line in the page file. When a workflow changes, you update one method in the model. Tests themselves never change.

---

## License

MIT
