Create a system prompt that for an agent that specifically focuses on creating front-end user tests using playwright and playwright MCP server Make me a list of all the questions an agent needs to ask? Make its so that it can integrate into all other teams codes
 
✅ SYSTEM PROMPT — Playwright Front-End Testing Agent
You are a senior front-end test automation agent specializing in Playwright and Playwright MCP (Model Context Protocol) integration.
 
Your primary responsibility is to design, generate, and maintain robust, scalable, and maintainable end-to-end (E2E) and UI tests that integrate seamlessly into any team's codebase regardless of framework, architecture, or conventions.
 
## CORE OBJECTIVES
- Generate high-quality Playwright tests that are:
  - Deterministic
  - Resilient to flaky behavior
  - Readable and maintainable
  - Framework-agnostic (React, Angular, Vue, Next.js, etc.)
- Follow best practices:
  - Use locators instead of brittle selectors
  - Prefer role-based queries (getByRole, getByLabel, etc.)
  - Avoid hard waits (use auto-waiting mechanisms)
  - Isolate test cases
  - Ensure idempotency
- Integrate smoothly into existing pipelines and repositories with minimal disruption
 
## MCP INTEGRATION AWARENESS
- Use Playwright MCP Server capabilities when available to:
  - Inspect DOM structure dynamically
  - Fetch runtime metadata
  - Validate selectors against actual UI
  - Improve locator reliability
- Prefer live context over assumptions whenever MCP access is available
 
## CROSS-TEAM COMPATIBILITY RULES
- Respect existing:
  - Project structure
  - Naming conventions
  - Code style (Prettier, ESLint, etc.)
  - Test frameworks (if Playwright is layered on top)
- Do NOT introduce breaking changes
- Place tests in appropriate directories (e.g. /tests, /e2e, /specs)
- Use config-driven environments (dev, staging, prod)
- Avoid hardcoding URLs, credentials, or data
 
## TEST DESIGN PRINCIPLES
- Follow Arrange → Act → Assert pattern
- Use Page Object Model (POM) when test complexity increases
- Extract reusable helpers for:
  - Authentication
  - Navigation
  - Test data generation
- Cover:
  - Happy paths
  - Edge cases
  - Error states
  - Accessibility (where possible)
 
## OUTPUT FORMAT
- Provide:
  1. Test file(s)
  2. Optional Page Objects
  3. Helper utilities (if needed)
  4. Config adjustments (if required)
- Code must be ready to run immediately
- Include minimal but helpful comments (no over-commenting)
 
## QUALITY CHECKS BEFORE OUTPUT
- Ensure selectors are stable
- Ensure tests are not flaky
- Validate async handling
- Ensure no unnecessary waits
- Ensure readability
 
## INTERACTION MODE
Before generating tests, you MUST gather sufficient context by asking targeted questions.
If some data is missing but non-critical, proceed using best practices and clearly state assumptions.
 
You should prioritize:
- Accuracy over speed
- Reusability over quick hacks
- Compatibility over preference
 
## CONSTRAINTS
- Never expose secrets or unsafe practices
- Never assume framework unless specified
- Never generate brittle selectors (e.g. nth-child unless justified)
- Avoid overengineering
 
You are effectively a senior SDET collaborating across multiple teams.
 
QUESTION SET — What the Agent MUST Ask
These questions ensure the agent generates correct, reusable, and team-compatible tests.
🧩 1. Application Context
What is the application type?
(SPA, SSR, microfrontend, static site, etc.)
What framework is used?
(React, Angular, Vue, Next.js, etc.)
What is the base URL for testing?
Which environments exist?
(dev, QA, staging, prod)
🔐 2. Authentication & Access
Does the app require authentication?
What type?
(UI login, API login, SSO, OAuth)
Should authentication be mocked, reused, or executed per test?
Are test credentials available or should fixtures be used?
🎯 3. Test Scope Definition
What features or flows need testing?
Priority level?
(critical path, regression, smoke, exploratory)
What user roles exist (admin, user, guest)?
Must tests include negative/error scenarios?
🧪 4. Test Data Strategy
Should test data be:
Static
Seeded
Generated dynamically
Are APIs available for setup/teardown?
Should data cleanup be implemented?
🧰 5. Existing Codebase Integration
Where should tests live?
(/tests, /e2e, etc.)
Is there an existing Playwright setup?
Are there existing:
Page Object Models?
Helpers/utilities?
What naming conventions should be followed?
What linting rules must be respected?
⚙️ 6. Playwright Configuration
Is there an existing playwright.config.ts?
What browsers should be tested?
(Chromium, Firefox, WebKit)
Is parallel execution enabled?
What timeout/retry strategy is used?
🌐 7. UI Stability & Selectors
Are test IDs available?
(data-testid, data-cy)
Should accessibility selectors be preferred?
Are dynamic elements expected?
🔄 8. CI/CD Integration
Which CI system is used?
(GitHub Actions, Azure DevOps, Jenkins)
Should tests run on:
PRs?
nightly builds?
Are artifacts required?
(videos, screenshots, traces)
📊 9. Reporting & Debugging
What reporting tools are used?
(Playwright report, Allure, custom dashboard)
Should traces/videos/screenshots always be captured?
🧱 10. Architectural Patterns
Should Page Object Model be enforced?
Are there shared component libraries?
Should tests be:
Fully isolated
Or reusable chained flows?
🚀 11. Performance & Reliability
Are flaky tests currently an issue?
Should retries be implemented?
Any performance constraints?
🔍 12. MCP Server Usage
Is Playwright MCP server available?
Should DOM be dynamically inspected before test generation?
Should agent verify selectors live?
🧭 13. Coding Standards
TypeScript or JavaScript?
Preferred import style?
Formatting rules (Prettier config)?
🧠 14. Constraints & Preferences
Any forbidden approaches?
Required libraries/tools?
Special security or compliance requirements?
🔗 Why This Works Across Teams
This setup ensures:
✅ Zero hard dependency on a specific framework

✅ Configurable patterns (POM, helpers, test data)

✅ Flexible CI/CD compatibility

✅ Respect for existing architecture

✅ Scalable test design
 
starter Playwright + MCP template repo
 
Here’s a production-ready starter Playwright + MCP template repository you can drop into any team’s codebase. It’s designed to be:
✅ Framework-agnostic
✅ CI/CD friendly
✅ MCP-aware
✅ Scalable (multi-team use)
✅ Clean and opinionated without being restrictive
📁 Repository Structure
 
playwright-mcp-template.txt
 
Sue Padayachee comes in first place, now, lets see who is next
 
⚙️ 1. package.json
{
  "name": "playwright-mcp-template",
  "version": "1.0.0",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "report": "playwright show-report"
  },
  "devDependencies": {
    "@playwright/test": "^1.45.0",
    "dotenv": "^16.0.0",
    "typescript": "^5.0.0"
  }
}
 
⚙️ 2. playwright.config.ts
import { defineConfig } from '@playwright/test';
import dotenv from 'dotenv';
 
dotenv.config();
 
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30 * 1000,
 
  retries: process.env.CI ? 2 : 0,
 
  reporter: [
    ['html'],
    ['list']
  ],
 
  use: {
    baseURL: process.env.BASE_URL,
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
 
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' }
    },
    {
      name: 'firefox',
      use: { browserName: 'firefox' }
    }
  ]
});
``
 
🔐 3. .env.example
BASE_URL=https://example.com 
USERNAME=testuser 
PASSWORD=password123
 
🧪 4. Example Test (tests/e2e/example.spec.ts)
import { test, expect } from '@playwright/test';
import { HomePage } from '../pages/home.page';
 
test('homepage loads correctly', async ({ page }) => {
  const home = new HomePage(page);
 
  await home.goto();
  await home.assertLoaded();
});
 
🧱 5. Page Object (tests/pages/home.page.ts)
import { Page, expect } from '@playwright/test';
 
export class HomePage {
  constructor(private page: Page) {}
 
  async goto() {
    await this.page.goto('/');
  }
 
  async assertLoaded() {
    await expect(this.page.getByRole('heading')).toBeVisible();
  }
}
 
🔁 6. Fixtures (Reusable Setup)
import { test as base } from '@playwright/test';
 
export const test = base.extend({
  // Add shared fixtures here
});
 
export { expect } from '@playwright/test';
 
🔑 7. Auth Helper (tests/utils/auth.ts)
import { Page } from '@playwright/test';
 
export async function login(page: Page) {
  await page.goto('/login');
 
  await page.getByLabel('Username').fill(process.env.USERNAME!);
  await page.getByLabel('Password').fill(process.env.PASSWORD!);
 
  await page.getByRole('button', { name: 'Login' }).click();
}
 
🧠 8. MCP Client (tests/mcp/mcp-client.ts)
This is a minimal abstraction to integrate Playwright with an MCP server.
export class MCPClient {
  async getDomSnapshot() {
    // placeholder — replace with real MCP call
    return {};
  }
 
  async validateSelector(selector: string) {
    // Hook into MCP server for validation
    return true;
  }
}
``
✅ Extend this to:
Fetch DOM snapshots
Auto-generate selectors
Validate flaky locators
🧪 9. Global Setup (scripts/global-setup.ts)
import { chromium } from '@playwright/test';
 
export default async function globalSetup() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
 
  // Optional: pre-auth
  // save storage state
 
  await browser. Close();
}
 
🚀 10. GitHub Actions CI (.github/workflows/playwright.yml)
name: Playwright Tests
 
on:
  pull_request:
  push:
    branches: [main]
 
jobs:
  test:
    runs-on: ubuntu-latest
 
    steps:
      - uses: actions/checkout@v4
 
      - uses: actions/setup-node@v4
        with:
          node-version: 20
 
      - run: npm ci
      - run: npx playwright install --with-deps
 
      - run: npm test
 
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
 
📘 README.md (short version)
# Playwright MCP Template
 
✅ Key Design Decisions
🔹 MCP Ready
mcp-client.ts acts as a plug-in layer
No hard dependency → works even if MCP unavailable
🔹 Team-Friendly
Clear separation:
tests
pages
utils
Easy to extend
🔹 Scalable
Supports:
multiple environments
CI pipelines
test data strategies
 
## Setup
npm install
npx playwright install
 
## Run tests
npm test
 
## Features
- Playwright E2E testing
- MCP-ready structure
- Page Object Model
- CI/CD ready
- Multi-browser support
 
 
 
🚀 If You Want Next Level
I can extend this into:
✅ Auto-generating tests using MCP + AI

✅ Self-healing selectors

✅ Visual regression testing

✅ Component testing setup

✅ Multi-tenant test orchestration
 
 
Example Domain
 
Create a smart agent workflow (decision tree) 
 
Here’s a smart agent workflow decision tree tailored for a Playwright + MCP testing agent that works across teams, environments, and architectures.
This is structured so you can:
Plug it into an AI agent
Use it as a reasoning framework
Turn it into code later
🧠 SMART AGENT WORKFLOW (DECISION TREE)
START
   ↓ 
Gather Context → Validate Inputs → Evaluate Environment
   ↓ 
Define Test Scope → Determine Strategy → Select Architecture
   ↓
 Generate Tests → Validate → Integrate → Output
   ↓ 
END
 
🔍 1. CONTEXT GATHERING NODE
IF required context is missing
     → Ask questions 
ELSE
     → Proceed
 
Required Inputs:
App type
Base URL
Framework (if known)
Auth requirements
Test scope
⚙️ 2. ENVIRONMENT DETECTION NODE
IF Playwright already exists
    → Adapt to existing setup
ELSE
    → Generate minimal config scaffold
IF MCP server available
    → Enable DOM inspection + selector validation
ELSE
    → Use best-practice selectors
🔐 3. AUTH STRATEGY NODE
IF authentication required
    IF reusable session possible
        → Use storageState strategy
    ELSE IF API login available
        → Prefer API auth setup
    ELSE
        → Perform UI login in setup
ELSE
    → Skip auth
🎯 4. TEST SCOPE CLASSIFICATION NODE
IF user specifies flows
    → Use provided flows
ELSE
    → Infer from app type:
        - Landing page
        - Navigation
        - Core feature
IF critical path
    → Prioritize reliability, minimal dependencies
IF regression suite
    → Expand coverage
IF exploratory
    → Generate broader scenarios
🧱 5. TEST ARCHITECTURE DECISION
IF tests are simple
    → Inline test structure
ELSE
    → Use Page Object Model (POM)
IF multiple tests share logic
    → Extract helpers
IF multi-role system
    → Separate fixtures per role
🔎 6. SELECTOR STRATEGY NODE
IF MCP available
    → Validate selectors via MCP
    → Prefer stable attributes dynamically
ELSE
    → Use fallback priority:
        1. getByRole
        2. getByLabel
        3. data-testid
        4. text
        5. CSS (last resort)
IF selector is brittle
    → Refactor before proceeding
🧪 7. TEST DATA STRATEGY NODE
IF test data API available
    → Seed via API
ELSE IF static acceptable
    → Use fixed data
ELSE
    → Generate dynamic data
IF data persists between tests
    → Add cleanup step
🔄 8. EXECUTION STRATEGY NODE
IF CI environment
    → Enable retries & artifacts
ELSE
    → Keep minimal retries
IF flaky areas detected
    → Add stability improvements:
        - better locators
        - assertions before actions
🧠 9. MCP ENHANCED INTELLIGENCE NODE
(only if MCP enabled)
→ Fetch DOM snapshot
→ Validate UI structure
→ Detect dynamic elements
→ Improve selector choices
IF mismatch between expected & actual UI
    → Adapt test dynamically
🧩 10. CODE GENERATION NODE
Generate:
- Test specs
- Page Objects (if needed)
- Utilities
- Fixtures
Rules:
Follow project conventions
Avoid breaking changes
Keep modular
✅ 11. VALIDATION NODE
Check:
✔ selectors stable
✔ no hard waits
✔ async handled
✔ tests isolated
✔ reusable structures
IF issues detected
    → Refactor before output
🔗 12. INTEGRATION NODE
IF existing repo structure
    → Place files accordingly
ELSE
    → Use standard structure
IF CI exists
    → Ensure compatibility
📤 13. OUTPUT NODE
Return:
Test files
Supporting files
Minimal explanation
Assumptions made
🔁 SELF-IMPROVEMENT LOOP (ADVANCED)
AFTER test execution:
IF failures occur
    → Analyze:
        - selector failure
        - timing issue
        - env issue
    IF MCP enabled
        → revalidate selectors
    → Auto-fix test
⚡ CONDENSED DECISION TREE (FAST VIEW)
Start
 ├── Context complete?
 │     ├── No → Ask questions
 │     └── Yes
 │
 ├── Playwright मौजूद?
 │     ├── Yes → Extend
 │     └── No → Scaffold
 │
 ├── MCP available?
 │     ├── Yes → Enable smart selectors
 │     └── No → Use best practices
 │
 ├── Auth needed?
 │     ├── Yes → (Storage | API | UI)
 │     └── No
 │
 ├── Scope defined?
 │     ├── Yes → Use it
 │     └── No → Infer basics
 │
 ├── Complexity?
 │     ├── Low → Inline tests
 │     └── High → POM + helpers
 │
 ├── Data strategy?
 │     ├── API | Static | Dynamic
 │
 ├── Generate tests
 │
 ├── Validate quality
 │
 ├── Integrate into repo
 │
 └── Output
🚀 Why This Works
This workflow:
✅ Adapts dynamically to any codebase

✅ Uses MCP when available but doesn’t depend on it

✅ Prevents flaky tests

✅ Scales from small apps → enterprise systems

✅ Mimics how a senior SDET actually thinks
✅ If You Want Next
I can convert this into:
✅ Executable agent logic (JSON / YAML / LangGraph)
✅ VSCode extension agent
✅ Self-healing Playwright bot
✅ Multi-agent system (QA + Dev + Reviewer agents)
 OR build a self-adaptive test generator agent
 
🤖 SELF-ADAPTIVE TEST GENERATOR AGENT
This is a next-gen QA agent that:
✅ Generates Playwright tests
✅ Adapts based on runtime failures
✅ Self-heals selectors
✅ Learns UI changes using MCP
✅ Works across teams and repos
🧠 1. CORE AGENT ARCHITECTURE
 
Plain Text
                ┌──────────────────────┐
                │  Input / Instructions│
                └─────────┬────────────┘
                          ↓
                ┌──────────────────────┐
                │ Context Analyzer      │
                └─────────┬────────────┘
                          ↓
                ┌──────────────────────┐
                │ Test Strategy Engine  │
                └─────────┬────────────┘
                          ↓
                ┌──────────────────────┐
                │ Test Generator        │
                └─────────┬────────────┘
                          ↓
                ┌──────────────────────┐
                │ Execution Engine      │
                └─────────┬────────────┘
                          ↓
                ┌──────────────────────┐
                │ Failure Analyzer      │
                └─────────┬────────────┘
                          ↓
                ┌──────────────────────┐
                │ Self-Healing Engine   │
                └─────────┬────────────┘
                          ↓
                ┌──────────────────────┐
                │ Learning Memory       │
                └──────────────────────┘
 
⚙️ 2. AGENT MODULES (DETAILED)
🔍 A. Context Analyzer
Purpose
Understands:
App type
Environment
Existing repo structure
Test scope
Output
 
{
  "framework": "React",
  "auth": "UI login",
  "mcp": true,
  "testPriority": "critical",
  "structure": "existing"
}
 
🧠 B. Test Strategy Engine
Decides:
Scenario	Action
Simple flow	Inline test
Complex UI	Page Object Model
Multi-role	Fixtures
Flaky app	Add guards & retries
MCP available	Enable DOM learning
🧪 C. Test Generator
Generates:
✅ Playwright test files
✅ Page Objects
✅ Fixtures
✅ Helper utilities
Example Output:
test('user can checkout', async ({ page }) => {
  await page.goto('/shop');
 
  await page.getByRole('button', { name: 'Add to cart' }).click();
  await page.getByRole('link', { name: 'Cart' }).click();
 
  await expect(page.getByText('Total')).toBeVisible();
});
 
🚀 D. Execution Engine
Runs tests and captures:
Errors
Screenshots
Traces
DOM snapshots (via MCP)
❌ E. Failure Analyzer
Detects failure type:
Plain Text
IF "element not found" → Selector issue
IF "timeout" → Timing issue
IF "navigation failed" → Env issue
IF "assertion failed" → Logic issue


🔧 F. Self-Healing Engine
Core intelligence layer
🔹 Selector Healing
Plain Text
IF selector fails:
    → Query MCP DOM snapshot
    → Find closest match:
        - same role
        - similar text
        - nearby structure
    → Replace selector
Example:
 
 
// Old

page.getByText('Submit')


// New (auto-fixed)

page.getByRole('button', { name: 'Submit Order' })


Show more lines
 
🔹 Timing Fixes
Plain Text
IF timeout:
    → Add wait condition:
        await expect(locator).toBeVisible()


🔹 Flow Repair
Plain Text
IF navigation step missing:
    → Insert prerequisite steps


🔹 Assertion Correction
Plain Text
IF UI changed:
    → Update expected text dynamically (via MCP)


🧠 G. Learning Memory (CRITICAL)
Stores patterns like:
JSON
 
{

  "selectors": {

    "loginButton": {

      "old": "text=Login",

      "new": "role=button[name='Sign in']"

    }

  },

  "flakyPaths": ["/checkout"],

  "preferredSelectors": ["getByRole"]

}

``

Show more lines
 
🔁 3. SELF-ADAPTATION LOOP
Plain Text
Generate → Run → Fail → Analyze → Fix → Re-run → Learn


Example Loop:
Test fails ❌
Detect: selector broken
MCP finds new selector ✅
Test updated
Re-run passes ✅
Memory updated
🧬 4. DECISION LOGIC (SIMPLIFIED)
Plain Text
IF failure:
    SWITCH type:
        selector → heal
        timeout → stabilize
        assertion → update expected
        navigation → repair flow


🔗 5. MCP INTEGRATION LAYER
Capabilities used:
DOM inspection
Selector validation
UI diffing
Accessibility tree
Example:
 
 
 
 
TypeScript
 
const dom = await mcp.getDomSnapshot();

const selector = mcp.findBestSelector("Submit button");

``

Show more lines
 
🧱 6. CODE STRUCTURE
Plain Text
/agent
 ├── context-analyzer.ts
 ├── strategy-engine.ts
 ├── generator.ts
 ├── executor.ts
 ├── failure-analyzer.ts
 ├── self-healer.ts
 ├── memory-store.ts
 └── mcp-adapter.ts


🔥 7. PSEUDO IMPLEMENTATION (CORE LOOP)
 
 
 
 
TypeScript
 
while (true) {

  const tests = generateTests(context);


  const results = await runTests(tests);


  if (results.passed) break;


  const failure = analyze(results);


  const fix = selfHeal(failure, context);


  applyFix(tests, fix);


  updateMemory(fix);

}


Show more lines
 
🧩 8. ADVANCED FEATURES
✅ Auto Test Expansion
Plain Text
IF feature stable:
    → Generate edge cases automatically


✅ Flaky Test Detection
Plain Text
IF intermittent failures:
    → mark as flaky
    → apply retry + stabilization


✅ Multi-Team Adaptation
Plain Text
Detect:
- naming conventions
- folder structure
- frameworks
→ adapt automatically


✅ Risk-Based Testing
Plain Text
Prioritize:
- checkout
- login
- payments


🚀 9. OPTIONAL ADD-ONS
You can extend this into:
🔹 Visual Testing
screenshot diffing
🔹 API + UI hybrid testing
🔹 AI-generated test scenarios
🔹 Multi-agent system:
Generator agent
Reviewer agent
Fixer agent
✅ 10. WHAT MAKES THIS "SELF-ADAPTIVE"
Unlike basic automation, this agent:
✅ Fixes itself after failures
✅ Learns UI changes over time
✅ Gets smarter per run
✅ Reduces maintenance cost drastically
✅ Works across any team’s code
⚡ If You Want Next
I can build:
✅ Full working TypeScript implementation
✅ Plug-and-play CLI tool
✅ GitHub bot that auto-fixes failing tests
✅ Visual architecture diagram (interactive)
 