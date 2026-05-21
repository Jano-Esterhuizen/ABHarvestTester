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
┌──────────────────────────────────────────────────────────────────────┐
│                         TestForge System                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────────────┐        │
│  │  CONFIG   │───▶│ ORCHESTRATOR │───▶│   SHARED STATE       │        │
│  │           │    │  (Flow/Py)   │    │   (Dataclass)        │        │
│  │• repo_path│    └──────┬───────┘    └──────────────────────┘        │
│  │• app_url  │           │                                            │
│  │• creds    │           ▼                                            │
│  │• mcp-cfg? │   ┌───────────────┐                                    │
│  └──────────┘    │  REPO READER   │                                    │
│                  │  (Discovery)   │                                    │
│                  └───────┬────────┘                                    │
│                          │ context_doc                                 │
│                          ▼                                             │
│                  ┌───────────────┐                                    │
│                  │   SCRAPER     │◀── optional: MCP server / Swagger  │
│                  │  (API Spec)   │                                    │
│                  └───────┬────────┘                                    │
│                          │ api_spec (canonical source of truth)        │
│                          ▼                                             │
│                  ┌───────────────┐                                    │
│                  │  QA ANALYST   │                                    │
│                  │  (Test Plan)  │                                    │
│                  └───────┬────────┘                                    │
│                          │ test_plan                                   │
│                          ▼                                             │
│         ┌────────────────┼────────────────┐                           │
│         │                │                │                           │
│         ▼                ▼                ▼                           │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐                    │
│  │ BE TEST    │   │ FE TEST    │   │ E2E TEST   │                    │
│  │ WRITER     │   │ WRITER     │   │ WRITER     │                    │
│  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘                    │
│        │                 │                │                           │
│        └─────────────────┼────────────────┘                           │
│                          ▼                                             │
│                  ┌───────────────┐                                    │
│                  │   REVIEWER    │──── feedback ────┐                │
│                  │  (Run+Fix)    │                  │                │
│                  └───────┬───────┘                  │                │
│                          │                          ▼                │
│                          │              ┌──────────────────┐         │
│                          │              │ WRITER (retry)    │         │
│                          │              └──────────────────┘         │
│                          ▼                                            │
│                  ┌───────────────┐                                    │
│                  │  OUTPUT: .spec.ts files                            │
│                  └───────────────┘                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Input | Output | Tools |
|-------|-------|--------|-------|
| **Orchestrator (Flow)** | Config (repo, URL, creds) | Sequence coordination, state management | CrewAI Flow (Python code, no LLM) |
| **Repo Reader** | Repo path | Context document (tech stack, structure, roles, domain) | File system read |
| **Scraper** | Context doc + repo (+ optional MCP server) | API specification (endpoints, methods, schemas, auth) — canonical source-of-truth document | File system read, MCP client (optional) |
| **QA Analyst** | Context doc + API spec + creds | Test plan (scenarios, edge cases, boundaries per feature) | None (pure reasoning) |
| **BE Test Writer** | Test plan + API spec + creds | Backend .spec.ts files | File system write |
| **FE Test Writer** | Test plan + context + creds + app URL | Frontend .spec.ts files | Playwright MCP |
| **E2E Test Writer** | Test plan + context + creds + app URL | End-to-end .spec.ts files (user journeys) | Playwright MCP |
| **Reviewer** | Generated tests + app URL + creds | Pass/fail results + fix instructions | Playwright MCP, test runner |

---

## 2. Technology Stack Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Language** | Python 3.11+ | Best framework support (LangGraph, CrewAI), fastest development |
| **Agent Framework** | CrewAI | Fastest to prototype; YAML-based agent config; competition timeline demands speed |
| **LLM Provider** | GitHub Models API (models.github.ai) | Single auth (GitHub token), access to multiple models, no separate API keys |
| **LLM (generation)** | OpenAI GPT-4.1 (via GitHub Models) | Best code generation + instruction following available on the platform |
| **LLM (review)** | GPT-4o-mini (via GitHub Models) | Cheap, fast, good enough for failure analysis |
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
  --output ./test-output \
  --mcp-config ./mcp-server.json   # Optional: dev-provided MCP server config
  --force                          # Optional: overwrite existing test files
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

### 3.2.1 MCP Server Configuration (Optional)

The dev team may optionally provide an MCP server that exposes Swagger/OpenAPI documentation for their application. If provided, the Scraper uses this as the **authoritative source** for the API specification instead of code-based extraction.

```json
// mcp-server.json (provided by dev team — optional)
{
  "server": {
    "command": "npx",
    "args": ["-y", "@harvest/mcp-server"],
    "transport": "stdio"
  },
  "capabilities": {
    "swagger_endpoint": "/api/docs",
    "openapi_version": "3.0"
  }
}
```

**Alternatively**, the Scraper auto-detects MCP server presence by checking for:
1. A `mcp-server.json` file in the target repo root
2. An `mcp` section in the target repo's `package.json`
3. A running MCP server config passed via `--mcp-config` CLI flag

**If MCP server is found:** The Scraper connects, pulls the Swagger/OpenAPI spec directly, and uses it as the canonical API document. This is far more accurate than code-based extraction because it's the developers' own API definition.

**If MCP server is NOT found:** The Scraper falls back to code-based extraction (reading route files, controllers, middleware) as before.

### 3.3 Output Structure — Standardized Test Framework (Clean Architecture + Three-Tier POM)

The generated test output follows a **6-Layer Architecture** with a **Three-Tier Page Object Model** pattern, based on the Agile Bridge Testing Guidelines standard. This ensures every generated test suite has identical structure regardless of the target application.

**Architecture Principle:** Separation of concerns — UI selectors, accessor logic, and business workflows are strictly separated so that UI changes only require updating one layer.

```
test-output/
├── playwright.config.ts              # Playwright configuration
├── package.json                       # Dependencies (playwright, etc.)
├── tsconfig.json                      # TypeScript config
│
├── core/                              # LAYER 1: Core (Foundation)
│   ├── types/
│   │   ├── test-case.types.ts        # Base test interfaces
│   │   └── enums.ts                  # TestStatus, UserRole enums
│   ├── constants/
│   │   └── app.constants.ts          # App-wide constants (URLs, timeouts)
│   └── interfaces/
│       └── page-contract.ts          # Shared interface contracts
│
├── data/                              # LAYER 2: Data Layer
│   ├── credentials/
│   │   └── accounts.ts               # Role-based account data (from creds.json)
│   ├── generators/
│   │   └── test-data.generator.ts    # Dynamic test data generation
│   └── models/
│       └── api-response.model.ts     # Expected response structures
│
├── utils/                             # LAYER 3: Utility Layer
│   ├── actions/
│   │   ├── click.actions.ts          # Click action factory
│   │   ├── form.actions.ts           # Form interaction factory
│   │   └── navigation.actions.ts     # Navigation helpers
│   ├── wait/
│   │   └── wait.helper.ts            # Smart waiting utilities
│   └── logger/
│       └── test.logger.ts            # Structured logging
│
├── ui/                                # LAYER 4: UI Layer (Three-Tier POM)
│   ├── pages/                         #   Sub-Layer 1: PAGES (selectors ONLY)
│   │   ├── login/
│   │   │   └── login.page.ts         #     Pure selectors, no methods
│   │   ├── dashboard/
│   │   │   └── dashboard.page.ts
│   │   └── [feature]/
│   │       └── [feature].page.ts
│   │
│   ├── objects/                        #   Sub-Layer 2: OBJECTS (accessors + data)
│   │   ├── login/
│   │   │   └── login.object.ts        #     Accessor methods, test data payloads
│   │   ├── dashboard/
│   │   │   └── dashboard.object.ts
│   │   └── [feature]/
│   │       └── [feature].object.ts
│   │
│   └── models/                         #   Sub-Layer 3: MODELS (business logic)
│       ├── login/
│       │   └── login.model.ts          #     Workflows, orchestration, assertions
│       ├── dashboard/
│       │   └── dashboard.model.ts
│       └── [feature]/
│           └── [feature].model.ts
│
├── business/                           # LAYER 5: Business Logic Layer
│   ├── workflows/
│   │   ├── authentication.workflow.ts  # Login/logout sequences
│   │   └── [feature].workflow.ts       # Multi-page business flows
│   └── validators/
│       └── response.validator.ts       # API response validation logic
│
├── tests/                              # LAYER 6: Test Layer (top)
│   ├── api/
│   │   ├── auth/
│   │   │   └── auth.api.spec.ts
│   │   ├── endpoints/
│   │   │   └── [resource].api.spec.ts
│   │   └── roles/
│   │       ├── user-permissions.spec.ts
│   │       ├── admin-permissions.spec.ts
│   │       └── super-admin-permissions.spec.ts
│   ├── ui/
│   │   ├── auth/
│   │   │   └── login.ui.spec.ts
│   │   ├── pages/
│   │   │   └── [page].ui.spec.ts
│   │   └── roles/
│   │       ├── user-access.ui.spec.ts
│   │       ├── admin-access.ui.spec.ts
│   │       └── super-admin-access.ui.spec.ts
│   └── e2e/
│       └── [workflow].e2e.spec.ts       # Cross-page business flows
│
├── fixtures/
│   ├── auth.fixture.ts                 # Authentication fixture (per role)
│   └── base.fixture.ts                 # Base test fixture with shared setup
│
└── README.md                           # Generated docs: what was discovered, coverage
```

### 3.4 Three-Tier POM Implementation Standard (TypeScript)

Every page/feature the agents discover MUST follow this exact structure:

#### Sub-Layer 1: Pages (Selectors Only)

```typescript
// ui/pages/login/login.page.ts
// LAYER 4.1: PAGES — Pure HTML codification. NO methods, NO logic.

export const loginPage = {
  usernameInputField: "#Username",
  passwordInputField: "#Password",
  loginButton: "#LoginButton",
  errorMessage: ".alert-danger",
  forgotPasswordLink: "a[href='/forgot-password']"
};
```

#### Sub-Layer 2: Objects (Accessor Methods + Data)

```typescript
// ui/objects/login/login.object.ts
// LAYER 4.2: OBJECTS — Accessor methods returning selectors. NO business logic.

import { Page, Locator } from '@playwright/test';
import { loginPage } from '../pages/login/login.page';

export class LoginObject {
  constructor(private page: Page) {}

  getUsernameField(): Locator {
    return this.page.locator(loginPage.usernameInputField);
  }

  getPasswordField(): Locator {
    return this.page.locator(loginPage.passwordInputField);
  }

  getLoginButton(): Locator {
    return this.page.locator(loginPage.loginButton);
  }

  getErrorMessage(): Locator {
    return this.page.locator(loginPage.errorMessage);
  }
}
```

#### Sub-Layer 3: Models (Business Logic & Workflows)

```typescript
// ui/models/login/login.model.ts
// LAYER 4.3: MODELS — All business logic, workflows, orchestration, assertions.

import { Page, expect } from '@playwright/test';
import { LoginObject } from '../../objects/login/login.object';
import { createFormActions } from '../../../utils/actions/form.actions';
import { createClickActions } from '../../../utils/actions/click.actions';

export class LoginModel {
  private loginObject: LoginObject;
  private formActions: ReturnType<typeof createFormActions>;
  private clickActions: ReturnType<typeof createClickActions>;

  constructor(private page: Page) {
    this.loginObject = new LoginObject(page);
    this.formActions = createFormActions(page);
    this.clickActions = createClickActions(page);
  }

  async signIn(username: string, password: string): Promise<void> {
    await this.formActions.fillField(this.loginObject.getUsernameField(), username);
    await this.formActions.fillField(this.loginObject.getPasswordField(), password);
    await this.clickActions.click(this.loginObject.getLoginButton());
  }

  async verifyLoginSuccess(expectedTitle: string): Promise<void> {
    await expect(this.page).toHaveTitle(expectedTitle);
  }

  async verifyLoginFailure(expectedError: string): Promise<void> {
    await expect(this.loginObject.getErrorMessage()).toContainText(expectedError);
  }
}
```

#### Test Layer Usage

```typescript
// tests/ui/auth/login.ui.spec.ts
import { test, expect } from '@playwright/test';
import { LoginModel } from '../../../ui/models/login/login.model';
import { getAccountByRole } from '../../../data/credentials/accounts';

test.describe('Login Feature', () => {
  let loginModel: LoginModel;

  test.beforeEach(async ({ page }) => {
    loginModel = new LoginModel(page);
    await page.goto('/login');
  });

  test('standard user can log in successfully', async ({ page }) => {
    const account = getAccountByRole('user');
    await loginModel.signIn(account.username, account.password);
    await loginModel.verifyLoginSuccess('Dashboard');
  });

  test('admin can log in and access admin panel', async ({ page }) => {
    const account = getAccountByRole('admin');
    await loginModel.signIn(account.username, account.password);
    await loginModel.verifyLoginSuccess('Admin Dashboard');
  });

  test('invalid credentials show error message', async ({ page }) => {
    await loginModel.signIn('invalid@test.com', 'wrongpassword');
    await loginModel.verifyLoginFailure('Invalid credentials');
  });
});
```

### 3.5 Dependency Hierarchy (Strict)

```
Tests Layer (6) ─── imports from ──▶ Business (5), UI Models (4.3), Data (2)
    │
Business Layer (5) ─── imports from ──▶ UI Models (4.3), Data (2), Utils (3)
    │
UI Models (4.3) ─── imports from ──▶ UI Objects (4.2), Utils (3), Data (2)
    │
UI Objects (4.2) ─── imports from ──▶ UI Pages (4.1), Core (1)
    │
UI Pages (4.1) ─── imports from ──▶ Core (1) only
    │
Utils (3) ─── imports from ──▶ Core (1), Data (2)
    │
Data (2) ─── imports from ──▶ Core (1) only
    │
Core (1) ─── imports from ──▶ NOTHING (foundation)
```

**RULE: Higher layers CAN import lower layers. Lower layers NEVER import higher layers.**

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
    incremental: bool = False              # True if framework already exists in output_dir
    mcp_server_config: Optional[dict] = None  # Dev-provided MCP server config (if exists)
    
    # Repo Reader output
    context_document: str = ""          # Full context markdown (budget: ≤4000 tokens)
    tech_stack: dict = field(default_factory=dict)  # {language, framework, db, etc.}
    roles_discovered: list = field(default_factory=list)  # [{name, permissions, routes}]
    
    # Scraper output
    api_spec: str = ""                  # OpenAPI/Swagger YAML or structured doc (SOURCE OF TRUTH)
    api_spec_source: str = ""           # "mcp_server" | "code_extraction" — how the spec was obtained
    endpoints: list = field(default_factory=list)  # [{method, path, auth, params, response}]
    ui_routes: list = field(default_factory=list)  # [{path, component, requires_auth, role}]
    
    # QA Analyst output
    test_plan: str = ""                 # Structured test plan (scenarios, edge cases, boundaries)
    
    # Test Writer outputs
    be_tests: list = field(default_factory=list)   # [{file_path, content, status}]
    fe_tests: list = field(default_factory=list)   # [{file_path, content, status}]
    e2e_tests: list = field(default_factory=list)  # [{file_path, content, status}]
    
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
  goal: "Understand the target repository's structure, tech stack, domain model, and role/permission system. Output MUST stay within the context budget (≤4000 tokens)."
  backstory: >
    You are a senior software engineer who excels at quickly understanding unfamiliar codebases.
    You read source code and produce clear, structured documentation about what a system does,
    how it's organized, what roles/permissions exist, and what APIs it exposes.
    CRITICAL: Your output is consumed by every downstream agent. Keep it concise and structured.
    Use bullet points, not prose. Summarize patterns, don't enumerate every file.
  tools:
    - file_read_tool
    - directory_list_tool

scraper:
  role: "API Specification Extractor"
  goal: "Produce the canonical API specification document — the single source of truth for all downstream agents. Prefer the dev-provided MCP server/Swagger endpoint if available; fall back to code-based extraction if not."
  backstory: >
    You are an API documentation specialist. Your FIRST action is always to check whether the
    dev team has provided an MCP server or Swagger endpoint. If they have, connect to it and
    pull the OpenAPI/Swagger spec directly — this is the most authoritative source because
    the developers defined it themselves.
    
    If no MCP server is available, you fall back to code-based extraction: reading route
    definitions, controllers, and middleware to produce a comprehensive API specification.
    
    Either way, you produce the SAME structured output: a canonical API document listing all
    endpoints, methods, parameters, auth requirements, roles, and response schemas. This
    document becomes the source of truth for the QA Analyst and all Test Writers downstream.
  tools:
    - file_read_tool
    - mcp_client_tool

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

qa_analyst:
  role: "QA Analyst & Test Planner"
  goal: "Think like a user AND an adversary. Produce a structured test plan identifying all scenarios developers would miss — edge cases, boundary conditions, negative paths, race conditions, permission gaps."
  backstory: >
    You are a senior QA analyst with a hacker's mindset. Given an API specification and
    application context, you don't just list happy paths — you find the gaps. What happens
    with empty strings? Null values? Expired tokens? Concurrent edits? Users accessing
    other users' data? You produce a comprehensive test plan that the test writers follow,
    ensuring coverage goes far beyond what a developer would think to test.
    Your output is a structured test plan, NOT code.
  tools: []

e2e_test_writer:
  role: "End-to-End Test Engineer"
  goal: "Generate cross-page user-journey tests that verify the full system works together from login to completion"
  backstory: >
    You are a senior QA automation engineer specializing in end-to-end workflows.
    You write TypeScript Playwright tests that simulate real user journeys spanning
    multiple pages — login, navigate, create, verify, clean up. You test that the
    system works as a whole, not just individual pages. Each journey maps to a real
    business workflow a user would perform.
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
    """Orchestrator: knows its team through CrewAI's YAML convention.
    
    Each agent lives in src/testforge/agents/<name>/config/agents.yaml + tasks.yaml.
    The Flow imports each agent's Crew class and invokes them in sequence.
    No LLM needed for orchestration — the sequence is deterministic Python code.
    
    Team knowledge mechanism:
    - Agent definitions: YAML files (CrewAI convention) in each agent's config/ folder
    - Task definitions: YAML files defining what each agent does
    - Sequence: Hardcoded in this Flow via @listen decorators
    - State: Shared TestForgeState dataclass passed between steps
    """
    
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
        """Scraper agent: produce canonical API specification (source of truth).
        
        Discovery priority:
        1. Check --mcp-config CLI flag (explicit dev-provided server)
        2. Check target repo for mcp-server.json at root
        3. Check target repo package.json for 'mcp' section
        4. If any found → connect to MCP server, pull Swagger/OpenAPI spec
        5. If none found → fall back to code-based extraction
        
        Either path produces the same canonical api_spec document.
        """
        # Detect MCP server availability
        mcp_config = self._discover_mcp_server()
        if mcp_config:
            self.state.mcp_server_config = mcp_config
            self.state.api_spec_source = "mcp_server"
            # Scraper crew runs with MCP client tool → pulls Swagger directly
        else:
            self.state.api_spec_source = "code_extraction"
            # Scraper crew runs with file_read_tool → extracts from source code
        # Run scraper crew (agent adapts strategy based on api_spec_source)
        return self.state
    
    @listen(extract_api_spec)
    def scaffold_framework(self):
        """Create framework structure if needed (skipped in incremental mode)"""
        if not self.state.incremental:
            # Write playwright.config.ts, package.json, tsconfig.json
            # Create core/, utils/, fixtures/ from templates
            pass
        else:
            logger.info("Framework exists — incremental mode, skipping scaffold")
        return self.state
    
    @listen(scaffold_framework)
    def plan_tests(self):
        """QA Analyst: produce structured test plan with scenarios + edge cases"""
        # Run qa_analyst crew — outputs test_plan to state
        return self.state
    
    @listen(plan_tests)
    def write_tests(self):
        """BE + FE + E2E Test Writers run in parallel, following the test plan"""
        # Run all three test writer crews concurrently
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

### 4.4 Incremental Output (Idempotent Runs)

**Problem:** If TestForge is run twice against the same target app, should it recreate the entire framework structure or only add new tests?

**Answer:** Detect whether the framework already exists. If it does, skip scaffolding and only generate/update test-related files.

**Detection mechanism:**

```python
def detect_existing_framework(output_dir: str) -> bool:
    """Check if the output directory already has a scaffolded framework."""
    markers = [
        "playwright.config.ts",
        "package.json",
        "tsconfig.json",
        "core/types/enums.ts",
    ]
    return all((Path(output_dir) / m).exists() for m in markers)
```

**Two modes:**

| Mode | Triggered when | What happens |
|------|---------------|-------------|
| **Full scaffold** | `output_dir` is empty or missing framework markers | Create entire 6-layer structure: config files, folders, fixtures, core types, utils, AND generate tests |
| **Incremental** | Framework markers exist | Skip scaffolding. Only generate/update files in `ui/`, `tests/`, `business/`, and `data/generators/` |

**What gets created vs. what gets skipped on incremental run:**

| Layer | Full Scaffold | Incremental |
|-------|:---:|:---:|
| `playwright.config.ts`, `package.json`, `tsconfig.json` | ✅ Create | ⏭️ Skip |
| `core/` (types, constants, interfaces) | ✅ Create | ⏭️ Skip |
| `utils/` (actions, wait helpers, logger) | ✅ Create | ⏭️ Skip |
| `fixtures/auth.fixture.ts`, `base.fixture.ts` | ✅ Create | ⏭️ Skip (unless new roles discovered) |
| `data/credentials/accounts.ts` | ✅ Create | 🔄 Regenerate (creds may have changed) |
| `data/generators/` | ✅ Create | 🔄 Update with new entity generators |
| `ui/pages/`, `ui/objects/`, `ui/models/` | ✅ Create | ➕ Add new features only (don't overwrite existing) |
| `business/workflows/` | ✅ Create | ➕ Add new workflows only |
| `tests/` (api, ui, e2e) | ✅ Create | ➕ Add new test files; overwrite only if `--force` flag |

**File conflict rules (incremental mode):**

| Scenario | Behavior |
|----------|----------|
| New feature discovered (e.g., `/projects` page) | Create new `projects.page.ts`, `projects.object.ts`, `projects.model.ts`, `projects.ui.spec.ts` |
| Existing feature (e.g., `/login` page already has POM) | **Skip** — don't overwrite. User may have hand-edited selectors. |
| Existing test file | **Skip** — unless `--force` is passed on CLI |
| New role in credentials | Add new role-based test files, update `auth.fixture.ts` |

**Flow integration:**

```python
@start()
def load_config(self):
    """Load config and detect output mode"""
    self.state.incremental = detect_existing_framework(self.state.output_dir)
    return self.state

@listen(extract_api_spec)
def scaffold_framework(self):
    """Create framework structure if needed (skipped in incremental mode)"""
    if not self.state.incremental:
        # Write playwright.config.ts, package.json, tsconfig.json
        # Create core/, utils/, fixtures/ from templates
        pass
    else:
        logger.info("Framework exists — incremental mode, skipping scaffold")
    return self.state

@listen(scaffold_framework)
def write_tests(self):
    """Writers generate tests (aware of what already exists)"""
    # Pass existing file list to writers so they skip existing features
    return self.state
```

**Writer awareness:** In incremental mode, the test writers receive a list of already-existing POM/test files. Their task prompt includes: "Do NOT regenerate tests for features that already have files. Only create tests for NEW features discovered in the API spec / UI routes that don't have corresponding test files yet."

### 4.5 Context Budget & Downstream Propagation

**Problem:** The Repo Reader's context document is consumed by *every* downstream agent (Scraper, BE Writer, FE Writer). If the target repo is large (100+ files), an unbounded context doc bloats each agent's prompt, silently degrading output quality — no crash, just progressively worse test generation as the LLM struggles with token overload.

**Solution: Hard budget + structured format + selective propagation**

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Context document max size | ≤4000 tokens (~3000 words) | Leaves room for agent instructions + generated output in a 128k window |
| API spec max size | ≤6000 tokens | Larger because it's more structured (endpoint lists) |
| Per-agent context injection | Only what that agent needs | Scraper gets full context; Writers get summary + API spec |

**Context document structure (Repo Reader must follow this template):**

```markdown
# Target Application Context

## Stack
- Language: [e.g., TypeScript]
- Framework: [e.g., Next.js 14]
- Database: [e.g., PostgreSQL via Prisma]
- Auth: [e.g., NextAuth.js, JWT sessions]

## Roles & Permissions
| Role | Routes | Capabilities |
|------|--------|-------------|
| user | /dashboard, /profile | View own data, edit profile |
| admin | /admin/*, /users | Manage users, view reports |

## Key Entities
- User (id, name, email, role)
- Project (id, name, ownerId, status)
- TimeEntry (id, userId, projectId, hours, date)

## UI Routes (discovered)
- /login — public
- /dashboard — user, admin
- /admin/users — admin only

## Conventions & Patterns
- API routes under /api/[resource]
- Auth middleware on all /api/* except /api/auth
- Response format: { data: T, error?: string }
```

**Selective propagation (what each agent receives):**

| Agent | Receives |
|-------|----------|
| Scraper | Full context document (needs to know where to look for APIs) |
| QA Analyst | Full context + full API spec + credentials (roles) — needs everything to think adversarially |
| BE Test Writer | Test plan (BE section) + API spec + Roles |
| FE Test Writer | Test plan (FE section) + UI Routes + Roles |
| E2E Test Writer | Test plan (E2E section) + UI Routes + API spec summary + Roles |
| Reviewer | Roles + test files + execution output (minimal context) |

**Implementation:** The `read_repository` step in the Flow validates output length. If the context document exceeds 4000 tokens, it re-prompts the Repo Reader with: "Your output exceeds the budget. Summarize: remove file listings, collapse similar routes, use bullet points not prose."

**Token counting:** Use `tiktoken` (cl100k_base encoding) for accurate measurement before injecting into downstream prompts.

### 4.6 QA Analyst Test Plan Output Template

The QA Analyst MUST produce output in this structured format so the Writers can parse it predictably:

```markdown
# Test Plan: [Application Name]

## API Tests (BE Writer)

### [Feature/Resource]
| Scenario | Method | Endpoint | Roles | Type | Priority |
|----------|--------|----------|-------|------|----------|
| [description] | GET/POST/etc. | /api/... | user,admin | happy/negative/boundary | P1/P2/P3 |

#### Edge Cases
- [specific edge case: empty body, null field, expired token, etc.]
- [boundary: max length, zero value, special characters]

### [Next Feature/Resource]
...

## UI Tests (FE Writer)

### [Page/Feature]
| Scenario | Page | Role | Type | Priority |
|----------|------|------|------|----------|
| [description] | /path | user,admin | happy/negative/access | P1/P2/P3 |

#### Edge Cases
- [specific UI edge case: empty state, long text overflow, rapid clicks]

### [Next Page/Feature]
...

## E2E Tests (E2E Writer)

### [User Journey Name]
| Step | Action | Expected | Roles |
|------|--------|----------|-------|
| 1 | [action] | [expected result] | user |
| 2 | [action] | [expected result] | user |

#### Failure Paths
- [what happens if step N fails mid-journey]
- [what if session expires during workflow]

### [Next Journey]
...

## Cross-Cutting Concerns
- Permission boundaries: [specific gaps to test between roles]
- Data dependencies: [what data each test needs, and how to create it]
- Race conditions: [concurrent operations that could conflict]
```

**Rules for the QA Analyst:**
- Group scenarios by Writer responsibility (BE / FE / E2E sections)
- Include priority (P1 = must test, P2 = should test, P3 = nice to have)
- Edge cases must be *specific* — not generic ("test invalid input") but concrete ("empty string in name field", "999999999 as quantity")
- Each scenario should map to exactly one test function in the output

---

## 5. Integration Architecture

### 5.1 Playwright MCP Integration & Session Isolation

The FE Test Writer and Reviewer both interact with the target app's browser, but they MUST NOT share a session. **Each gets its own isolated Playwright instance.**

**Session isolation strategy:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PLAYWRIGHT SESSION MANAGEMENT                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FE WRITER (Discovery Phase)          REVIEWER (Execution Phase)    │
│  ┌─────────────┐                      ┌─────────────┐              │
│  │  FE Writer  │                      │  Reviewer   │              │
│  │  Agent      │                      │  Agent      │              │
│  └──────┬──────┘                      └──────┬──────┘              │
│         │ MCP (stdio)                        │ subprocess            │
│         ▼                                    ▼                      │
│  ┌──────────────┐                     ┌──────────────┐             │
│  │ PW MCP #1    │                     │ npx playwright│             │
│  │ (exploration)│                     │ test          │             │
│  └──────┬───────┘                     └──────┬───────┘             │
│         ▼                                    ▼                      │
│  ┌──────────────┐                     ┌──────────────┐             │
│  │ Browser Ctx A│                     │ Browser Ctx B│             │
│  │ (isolated)   │                     │ (isolated)   │             │
│  └──────────────┘                     └──────────────┘             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this prevents race conditions:**

| Concern | Solution |
|---------|----------|
| FE Writer and Reviewer running simultaneously | They DON'T — flow is sequential (write → then review). Never concurrent. |
| Retry loop: Writer regenerating while Reviewer active | Flow enforces: Reviewer completes → feedback → Writer starts. No overlap. |
| Shared browser state (cookies, localStorage) | Each gets a fresh browser context. No shared state between phases. |
| MCP server reuse across agents | FE Writer spawns its own MCP server instance; Reviewer uses `npx playwright test` (entirely separate process). |
| Stale session after login | FE Writer's MCP session is destroyed after exploration. Reviewer's test runner creates fresh contexts per test file. |

**Implementation rules:**
1. **FE Writer** uses a Playwright MCP server (spawned via stdio) for **exploration only** — understanding what pages exist, what elements are visible, what the UI looks like. This session is terminated when the FE Writer finishes.
2. **Reviewer** does NOT use MCP for test execution. It runs `npx playwright test` as a subprocess, which spawns its own browser instances with proper test isolation (Playwright Test's built-in context-per-test).
3. **If Reviewer needs manual verification** (e.g., screenshot comparison), it spawns a separate MCP instance that is destroyed after use.
4. **No two agents ever hold a browser session simultaneously.**

**Playwright MCP capabilities used (FE Writer exploration only):**
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
| `mcp_client_tool` | Connect to dev-provided MCP server to pull Swagger/OpenAPI spec (optional) |

### 5.3 LLM Provider Configuration (GitHub Copilot)

All LLM access goes through GitHub's Models API using a GitHub Personal Access Token (PAT). This provides access to multiple models (Claude, GPT-4o, etc.) through a single authentication mechanism.

```python
# Environment variables required
GITHUB_TOKEN=ghp_...             # GitHub PAT with Copilot access
# Base URL for GitHub Models API
GITHUB_MODELS_ENDPOINT=https://models.github.ai/inference
```

**CrewAI LLM configuration:**
```python
# Uses LiteLLM under the hood — configure via environment
import os
os.environ["OPENAI_API_KEY"] = os.environ["GITHUB_TOKEN"]
os.environ["OPENAI_API_BASE"] = "https://models.github.ai/inference"

# In CrewAI agent definitions, reference models as:
# llm: "openai/gpt-4.1"                    (generation agents)
# llm: "openai/gpt-4o-mini"               (reviewer only)
```

Agent-to-model mapping:
| Agent | Model (via GitHub Models) | Reason |
|-------|---------------------------|--------|
| Repo Reader | gpt-4.1 | Best instruction following + long context for code comprehension |
| Scraper | gpt-4.1 | Structured extraction from code |
| QA Analyst | gpt-4.1 | Adversarial reasoning needs strongest model |
| BE Test Writer | gpt-4.1 | Best code generation quality available on GitHub Models |
| FE Test Writer | gpt-4.1 | Best code generation quality available on GitHub Models |
| E2E Test Writer | gpt-4.1 | Complex multi-page flows need strong code gen |
| Reviewer | gpt-4o-mini | Pattern matching, cheaper for iteration loops |
| Orchestrator | — (no LLM) | Pure Python Flow code; routing is if/else, not inference |

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

All generated tests MUST follow the **6-Layer Architecture with Three-Tier POM** standard (see Section 3.3-3.5). Key rules for the AI agents:

**Pages Layer rules:**
- Export a single `const` object with all selectors
- NO methods, NO classes, NO Playwright API calls
- Only CSS selectors, data-testid attributes, or XPath
- File naming: `[feature].page.ts`

**Objects Layer rules:**
- One class per page, receives `Page` in constructor
- Methods return `Locator` objects (from Playwright)
- NO business logic, NO assertions, NO waits
- File naming: `[feature].object.ts`

**Models Layer rules:**
- One class per page, receives `Page` in constructor
- ALL business logic lives here: workflows, waits, assertions
- Uses Objects layer for element access (never accesses Pages directly)
- File naming: `[feature].model.ts`

**Test Layer rules:**
- Uses Models for all interactions (never Objects or Pages directly)
- Follows AAA pattern (Arrange-Act-Assert)
- One `test.describe` per feature/page
- Tags: `@smoke`, `@negative`, `@boundary`, `@roles`
- File naming: `[feature].[type].spec.ts` (type = ui | api | e2e)

```typescript
// Standard test structure
import { test, expect } from '@playwright/test';
import { LoginModel } from '../../../ui/models/login/login.model';
import { getAccountByRole } from '../../../data/credentials/accounts';

test.describe('Feature: [feature name]', () => {
  test('[role] can [action]', async ({ page }) => {
    // Arrange — set up models and data
    const model = new LoginModel(page);
    const account = getAccountByRole('user');
    
    // Act — perform the action
    await model.signIn(account.username, account.password);
    
    // Assert — verify the outcome
    await model.verifyLoginSuccess('Dashboard');
  });

  test('[role] cannot [action] (permission denied)', async ({ page }) => {
    // Negative test for role boundaries
  });
});
```

**Future language support (v2+):** The Three-Tier POM architecture is language-agnostic. The same structure applies in C# (NUnit + Playwright) and Python (pytest + Playwright). A config flag will select the output language.

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
│       │   ├── qa_analyst/
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
│       │   ├── e2e_test_writer/
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
│       │   ├── playwright_mcp.py  # Playwright MCP client (FE exploration)
│       │   └── mcp_client.py     # Dev-provided MCP server client (Swagger pull)
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
| GitHub token in env | `.env` file with `GITHUB_TOKEN`, never committed; `.env.example` as template |
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
# Edit .env with your GitHub PAT (needs Copilot access)

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
    "openai>=1.82.0",
    "pyyaml>=6.0",
    "click>=8.1.0",
    "tiktoken>=0.7.0",
]
```

### 9.3 Prerequisites on Target Machine

- Python 3.11+
- Node.js 18+ (for Playwright test execution)
- `npx playwright install` (browser binaries)
- GitHub PAT with Copilot/Models access

---

## 10. Bounded Iteration & Convergence

The feedback loop (write → run → review → fix) is bounded to prevent cost runaway:

```
Iteration 1: Generate all tests → COMPILE → run → review
Iteration 2: Fix failing tests → COMPILE → run → review  
Iteration 3: Final fix attempt → COMPILE → run → report

After iteration 3: STOP. Report results as-is.
```

### 10.2 TypeScript Compilation Gate

Before every test execution, the Reviewer MUST run a compilation check:

```bash
npx tsc --noEmit --project tsconfig.json
```

**Why:** A syntax error in generated TypeScript wastes an entire Playwright test cycle. The test runner produces confusing runtime errors ("Cannot find module", "Unexpected token") that obscure the real issue. A clean compiler error is far more actionable for the feedback loop.

**Flow:**
```
Writer produces .spec.ts files
  → Reviewer runs tsc --noEmit
    ├── Compile errors → Feed compiler output to Writer (skip test execution entirely)
    └── Clean compile → Proceed to npx playwright test
```

**Failure handling:**

| Compile result | Action |
|----------------|--------|
| Type errors (e.g., wrong import path) | Feed back to Writer with exact error + file + line |
| Syntax errors (e.g., missing bracket) | Feed back to Writer — trivial fix |
| Missing module (e.g., Playwright not installed) | Environment issue — report and stop |
| Clean (exit code 0) | Proceed to test execution |

**Cost savings:** Compilation takes <2s vs. a full Playwright run (30-120s). Catching a bad import before launching browsers saves both time and tokens on the review analysis.

**Implementation:** The `test_runner_tool` always runs `tsc --noEmit` first. Only on success does it proceed to `npx playwright test`.

**Convergence criteria (stop early if met):**
- All tests pass
- No new fixes possible (same failures repeated)
- Only application bugs remain (not test bugs)

**Failure categorization by Reviewer:**

| Category | Action |
|----------|--------|
| **Test bug** (wrong selector, bad assertion) | Feed back to Writer for fix |
| **App bug** (genuine defect found) | Report as finding — do NOT fix the test |
| **Data-dependent** (missing data, empty state) | Report as data issue — do NOT feed back to Writer (see §10.1) |
| **Flaky** (passes sometimes) | Add retry annotation, report as warning |
| **Environment** (app not running, timeout) | Report as blocked — stop iteration |

### 10.1 Data-Dependent Failure Handling

A critical failure mode: a test fails not because the test is wrong or the app has a bug, but because **expected data doesn't exist** in the application. If the Reviewer incorrectly categorizes this as a "test bug" and sends it to the Writer, we enter a wasteful loop where tokens are burned rewriting a test that can never pass without data.

**The problem:**
```
Test: "Admin can see list of users on /users page"
Result: FAIL — expected table with rows, got empty table
Is it: wrong selector? app bug? or just... no users exist yet?
```

**Solution: Three-pronged approach**

#### Strategy 1: Self-Sufficient Tests (Arrange step creates data via API)

Generated tests MUST follow the pattern: **create what you need before you assert on it.**

```typescript
test('admin can see users in user list', async ({ page, request }) => {
  // ARRANGE — Create test data via API first
  const response = await request.post('/api/users', {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: { name: 'Test User', email: 'testuser@test.com', role: 'user' }
  });
  expect(response.ok()).toBeTruthy();
  
  // ACT — Navigate and interact
  await page.goto('/users');
  
  // ASSERT — Now we know data exists
  await expect(page.locator('table tbody tr')).toHaveCount(1);
});
```

**Rule for Test Writers:** Every test that asserts on *dynamic data* (lists, tables, dashboards) MUST create that data in its Arrange step via API calls. Tests that assert on *static UI* (buttons exist, navigation works, form fields present) do not need this.

#### Strategy 2: Reviewer Heuristic — Distinguish Data Issues from Test Bugs

The Reviewer uses this decision tree:

```
Test failed →
  ├── Error: "Element not found" on navigation/form element → TEST BUG (wrong selector)
  ├── Error: "Element not found" on data-display element → SUSPECT DATA ISSUE
  │     └── Check: Does the page load? Are structural elements present?
  │           ├── Yes (page works, just no data) → DATA-DEPENDENT failure
  │           └── No (page itself broken) → APP BUG or TEST BUG
  ├── Error: "Expected 5, got 0" on count/list → DATA-DEPENDENT
  ├── Error: "Timeout waiting for..." on data element → DATA-DEPENDENT
  └── Error: assertion mismatch on known values → TEST BUG (wrong assertion)
```

**Key signals of data-dependent failure:**
- Empty tables/lists where content was expected
- Count assertions returning 0
- "No results found" messages visible
- Page loads fine but specific data fields are empty

#### Strategy 3: Data Precondition Check (Pre-flight)

Before the Reviewer runs the full suite, it runs a quick **data smoke check**:

```typescript
// fixtures/data-precondition.fixture.ts
test.describe('Data Preconditions', () => {
  test('API is reachable and returns data', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.ok()).toBeTruthy();
  });

  test('At least one user exists', async ({ request }) => {
    const response = await request.get('/api/users', {
      headers: { Authorization: `Bearer ${adminToken}` }
    });
    const data = await response.json();
    // If this fails, it's a DATA issue, not a test issue
    expect(data.length).toBeGreaterThan(0);
  });
});
```

If precondition tests fail → Reviewer logs "DATA PRECONDITION FAILED" and does NOT send feedback to Writers. Instead reports: "Tests require seed data that doesn't exist. Recommend seeding the app or adding API-based data creation in Arrange steps."

**Token waste prevention:**

| Scenario | Without this fix | With this fix |
|----------|-----------------|---------------|
| Empty user table | 3 iterations × rewrite = ~$0.60 wasted | 0 rewrites, reported as data issue |
| Missing entity | Writer adds waits, retries selectors (never works) | Reviewer skips, reports precondition |
| App has no seed data | Entire feedback loop fails | Caught in pre-flight, stops early |

---

## 11. Data Flow Diagram

```
CONFIG ──▶ ORC ──▶ REPO READER ──▶ SCRAPER ──▶ QA ANALYST ──▶ WRITERS ──▶ REVIEWER ──▶ OUTPUT
                       │                │            │             │            │
                       ▼                ▼            ▼             ▼            ▼
                  context.md      api-spec.md   test-plan.md   *.spec.ts   results.json
                  (roles,         (endpoints,   (scenarios,    (tests per   (pass/fail,
                   stack,          schemas,      edge cases,    role per     feedback)
                   domain)         auth reqs)    boundaries)    endpoint)
                                       ▲
                                       │
                              MCP server (if available)
                              OR code extraction (fallback)
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
| ADR-002 | LLM Provider | GitHub Models API (models.github.ai) — single token, multiple models. NOTE: Anthropic/Claude NOT available on this platform. | Accepted |
| ADR-003 | Primary LLM | OpenAI GPT-4.1 via GitHub Models (best code gen + instruction following available) | Accepted |
| ADR-004a | Routing LLM | GPT-4o-mini for Reviewer only. Orchestrator is pure Python (no LLM). | Accepted |
| ADR-004b | Test framework output | Playwright (TypeScript) | Accepted |
| ADR-005 | Browser control | Playwright MCP server | Accepted |
| ADR-006 | Configuration model | CLI args + JSON creds file | Accepted |
| ADR-007 | State management | In-process shared state (dataclass) | Accepted |
| ADR-008 | Iteration bound | Max 3 review cycles | Accepted |
| ADR-009 | Parallel execution | BE + FE + E2E writers run concurrently (after QA Analyst planning step) | Accepted |
| ADR-010 | Output format | Files written incrementally (demo-friendly) | Accepted |
| ADR-011 | Role-based testing | Creds JSON defines roles; Reader discovers permissions | Accepted |
| ADR-012 | Project agnostic | No hardcoded app assumptions; all from discovery | Accepted |
| ADR-013 | Test framework pattern | 6-Layer Architecture + Three-Tier POM (Clean Architecture) | Accepted |
| ADR-014 | Output language (v1) | TypeScript (Playwright Test). C#/Python planned for v2 | Accepted |
| ADR-015 | POM standard | Based on Agile Bridge Testing Guidelines (ADSE) | Accepted |
| ADR-016 | Playwright session isolation | FE Writer uses MCP for exploration only; Reviewer uses `npx playwright test` (separate process). No shared sessions. | Accepted |
| ADR-017 | Data-dependent failure handling | Self-sufficient tests (Arrange creates data via API); Reviewer heuristics distinguish data issues from test bugs; pre-flight data checks prevent wasteful feedback loops | Accepted |
| ADR-018 | TypeScript compilation gate | `tsc --noEmit` before every test execution. Compile errors fed directly to Writer without running tests. | Accepted |
| ADR-019 | Context budget | Repo Reader output capped at ≤4000 tokens. Selective propagation: each agent gets only what it needs. Prevents silent quality degradation on large repos. | Accepted |
| ADR-020 | Orchestrator is code, not LLM | Flow routing is deterministic if/else in Python. No LLM call for routing decisions. | Accepted |
| ADR-021 | Scraper/Reader overlap | Accepted for v1. Two LLM passes read similar files. v2: merge into single "Discovery" agent or pass read cache. | Accepted |
| ADR-022 | No state checkpointing | Accepted for v1. Crash = restart. Demo is controlled. v2: checkpoint files between phases. | Accepted |
| ADR-023 | Incremental output | Detect existing framework via marker files. If present, skip scaffolding and only add new features/tests. Existing files never overwritten unless `--force`. | Accepted |
| ADR-024 | QA Analyst agent | Dedicated planning agent between Scraper and Writers. Thinks adversarially — produces structured test plan with edge cases, boundaries, negative paths. Writers follow the plan instead of improvising. | Accepted |
| ADR-025 | E2E Test Writer agent | Separate from FE Writer. Owns cross-page user-journey tests (`tests/e2e/`). Simulates real business workflows end-to-end. | Accepted |
| ADR-026 | Dev-provided MCP server | Scraper checks for an optional MCP server from the dev team. If found, pulls Swagger/OpenAPI spec directly (authoritative source). If not found, falls back to code-based extraction. Canonical API doc produced either way. | Accepted |
