agent: 'E2E Test Writer'
parent_document: 'TestForge Architecture Decision Document'
owner: 'Agile Bridge'
date: '2026-05-21'
status: 'Design — pre-implementation'

# E2E Test Writer Agent — Detailed Design

Companion document to the TestForge architecture. This document is the full specification for the E2E Test Writer agent: responsible for generating cross-page user journey tests that verify the system works as a whole from login to completion.

## 1. Purpose & Position in the Flow

The E2E Test Writer is the third and final Writer agent. It generates tests that simulate real users performing complete business workflows across multiple pages. These tests are the highest-confidence validation — if an E2E test passes, the business workflow works end-to-end.

```
QA ANALYST ──▶ ┌───────────────────┐
               │  E2E TEST WRITER   │ ──▶ tests/e2e/*.e2e.spec.ts
               │   (this agent)     │
               └───────────────────┘
                        │
                        ├── Uses: file_write_tool (to write spec files)
                        ├── Uses: Playwright MCP (optional, for exploration)
                        └── Reads: test-plan.md §4, api-spec, credentials
```

### Contract with the rest of the system

| Concern | Commitment |
|---------|-----------|
| Inputs accepted | test-plan.md §4 (E2E test cases) + api-specification.md + context-document.md + credentials |
| Output location | `{output_dir}/tests/e2e/` |
| File naming | `{workflow-name}.e2e.spec.ts` — one file per business journey |
| Test framework | Playwright Test (TypeScript) |
| Side effects | Writes .spec.ts files only — never runs them |
| Failure mode | Produce compilable tests even if uncertain; use TODO comments for unresolvable ambiguity |

## 2. Inputs

### 2.1 Test Plan §4 — E2E Journey Test Cases

Each journey from the QA Analyst's plan includes:
- Journey name and description
- Roles involved
- Step sequence (login → navigate → interact → verify)
- Assertions at each step
- Data setup requirements
- Priority (P0 or P1 — E2E tests are never P2/P3)

### 2.2 API Specification

Used for:
- Data setup via `request` fixture (POST to create test data before UI interaction)
- Data cleanup in afterAll (DELETE created resources)
- Understanding what the UI should display (expected values from API responses)

### 2.3 Context Document

Used for:
- Frontend route paths (where to navigate)
- Component structure (what Models are available from the FE Test Writer's output)
- Auth flow details (how login works)
- Domain glossary (naming tests meaningfully)

### 2.4 Credentials

Used for:
- Knowing which roles to test with
- Login credentials per role
- Login URL and form selectors

### 2.5 Feedback from Reviewer (retry iterations)

On retry, receives structured feedback:
- Which test files failed
- What the error was
- Suggested fix (from Reviewer's categorisation)
- Only TEST_BUG feedback is actionable — APP_BUG and DATA_DEPENDENT are ignored

## 3. Output Structure

### 3.1 File Organization

```
tests/e2e/
├── project-lifecycle.e2e.spec.ts     # Full CRUD journey for projects
├── user-management.e2e.spec.ts       # Admin manages users
├── billing-workflow.e2e.spec.ts      # Create time entries → generate invoice
└── onboarding-flow.e2e.spec.ts       # New user signup → first action
```

### 3.2 File Template

```typescript
import { test, expect } from '@playwright/test';
import { LoginModel } from '../../ui/models/login/login.model';
import { DashboardModel } from '../../ui/models/dashboard/dashboard.model';
import { ProjectModel } from '../../ui/models/projects/project.model';
import { getAccountByRole } from '../../data/credentials/accounts';

test.describe('Journey: Project Lifecycle', () => {
  const account = getAccountByRole('user');
  let projectId: string;

  test.beforeAll(async ({ request }) => {
    // Data setup via API if needed BEFORE the journey starts
    // Only for preconditions the journey doesn't create itself
  });

  test.afterAll(async ({ request }) => {
    // Cleanup any data created during the journey
    if (projectId) {
      await request.delete(`/api/projects/${projectId}`);
    }
  });

  test('User creates a project, adds time entry, and views report', async ({ page, request }) => {
    // === STEP 1: Login ===
    const loginModel = new LoginModel(page);
    await loginModel.navigate();
    await loginModel.signIn(account.username, account.password);
    await expect(page).toHaveURL(/dashboard/);

    // === STEP 2: Navigate to Projects ===
    const dashboardModel = new DashboardModel(page);
    await dashboardModel.navigateToProjects();

    // === STEP 3: Create Project ===
    const projectModel = new ProjectModel(page);
    await projectModel.createProject({
      name: `E2E Test Project ${Date.now()}`,
      description: 'Created by E2E test'
    });
    await expect(projectModel.successMessage).toBeVisible();
    
    // Capture ID for cleanup
    const url = page.url();
    projectId = url.split('/').pop()!;

    // === STEP 4: Add Time Entry ===
    await projectModel.addTimeEntry({
      hours: 2,
      description: 'E2E test time entry'
    });
    await expect(projectModel.timeEntryRow).toContainText('2');

    // === STEP 5: View Report ===
    await dashboardModel.navigateToReports();
    await expect(page.locator('[data-testid="total-hours"]')).toContainText('2');
  });

  test('User cannot access admin project settings', async ({ page }) => {
    // Negative E2E: verify permission boundary in context of a journey
    const loginModel = new LoginModel(page);
    await loginModel.navigate();
    await loginModel.signIn(account.username, account.password);

    await page.goto('/admin/projects/settings');
    await expect(page).toHaveURL(/dashboard|forbidden|unauthorized/);
  });
});
```

## 4. Writing Rules

### 4.1 Journey Structure

Every E2E test follows this pattern:
1. **Arrange** — Set up precondition data via API (if needed)
2. **Login** — Authenticate as the journey's role
3. **Navigate** — Go to the starting page
4. **Act** — Perform the multi-step workflow
5. **Assert** — Verify the outcome at each significant transition
6. **Cleanup** — Remove created data (afterAll or afterEach)

### 4.2 Self-Sufficiency

E2E tests must be fully self-sufficient:
- Create their own test data (via API in beforeAll or within the test)
- Never depend on tests in other files having run first
- Always clean up (even if the test fails — use fixtures/hooks)
- Use unique identifiers (timestamps, UUIDs) to avoid collisions with parallel runs

### 4.3 Model Reuse

E2E tests MUST reuse Page Object Models from the FE Test Writer:
```typescript
import { LoginModel } from '../../ui/models/login/login.model';
import { ProjectModel } from '../../ui/models/projects/project.model';
```

If a Model doesn't exist yet (FE Writer hasn't created it), the E2E Writer:
- Creates a minimal inline model within the test file
- Adds a TODO comment: `// TODO: Replace with shared model when available`

### 4.4 API for Setup, UI for Verification

The golden rule of E2E testing:
- **Use API to set up data** — faster, more reliable than clicking through UI
- **Use UI to verify the workflow** — that's what we're actually testing
- **Use API to clean up** — guaranteed to work even if UI is broken

```typescript
// GOOD: Setup via API
test.beforeAll(async ({ request }) => {
  const response = await request.post('/api/projects', {
    data: { name: 'Test Project', description: 'For E2E test' }
  });
  projectId = (await response.json()).id;
});

// GOOD: Test the UI workflow
test('user can edit project name', async ({ page }) => {
  await page.goto(`/projects/${projectId}`);
  // ... UI interactions ...
});

// GOOD: Cleanup via API
test.afterAll(async ({ request }) => {
  await request.delete(`/api/projects/${projectId}`);
});
```

### 4.5 Assertion Strategy

- Assert at every significant step transition (not just the end)
- Use `expect(page).toHaveURL()` after navigation to confirm the right page loaded
- Use `expect(locator).toBeVisible()` for elements that should appear
- Use `expect(locator).toContainText()` for content verification
- Avoid `expect(locator).toHaveCount()` for dynamic data — use `toBeVisible()` instead
- Never use `page.waitForTimeout()` — use auto-waiting or `waitForResponse()`

### 4.6 Handling Dynamic Data

```typescript
// GOOD: Use unique data to avoid test collisions
const projectName = `E2E Project ${Date.now()}`;

// GOOD: Wait for specific API responses
const [response] = await Promise.all([
  page.waitForResponse(resp => resp.url().includes('/api/projects') && resp.status() === 201),
  projectModel.clickCreate()
]);
const { id } = await response.json();

// GOOD: Capture dynamic IDs for later assertions/cleanup
projectId = id;
```

### 4.7 Multi-Role Journeys

Some journeys involve multiple roles (e.g., admin creates user, user logs in):
```typescript
test('Admin creates user who can then login', async ({ browser, request }) => {
  // Admin context
  const adminContext = await browser.newContext();
  const adminPage = await adminContext.newPage();
  // ... admin creates user via UI ...
  await adminContext.close();

  // New user context
  const userContext = await browser.newContext();
  const userPage = await userContext.newPage();
  // ... new user logs in and verifies access ...
  await userContext.close();
});
```

## 5. What E2E Tests Should NOT Do

- **Don't test API validation** — that's the BE Test Writer's job
- **Don't test individual page elements in isolation** — that's the FE Test Writer's job
- **Don't test every permutation** — E2E tests are expensive; test the critical path + one edge case
- **Don't skip login** — every E2E test starts from an unauthenticated state (proves the full flow)
- **Don't use `storageState`** — E2E tests exercise the login flow as part of the journey
- **Don't hardcode selectors** — use Models; if Models aren't available, use role/label locators
- **Don't create more than 5-7 E2E tests total** — they should be high-value only

## 6. CrewAI Agent Definition

### 6.1 agents.yaml

```yaml
e2e_test_writer:
  role: "End-to-End Journey Test Engineer"
  goal: >
    Generate cross-page user journey tests that verify complete business workflows
    from login to completion. Each test simulates a real user performing a real task.
    Tests must be self-sufficient (create own data via API), use Page Object Models,
    and clean up after themselves.
  backstory: >
    You are a senior QA automation engineer who thinks in user stories, not endpoints.
    You write tests that answer: "Can a real user accomplish this business goal?"
    You know that E2E tests are expensive to maintain, so you write only the most
    valuable journeys — the critical paths that, if broken, mean the business is blocked.
    You use the API for data setup because it's faster and more reliable than clicking
    through UI forms. You use the UI for verification because that's what you're actually
    testing. You always clean up because flaky leftover data is the #1 cause of flaky tests.
    You reuse Page Object Models from the FE Test Writer whenever possible.
  tools:
    - file_write_tool
  llm: openai/gpt-4.1
  max_iter: 4
  memory: true
  verbose: true
```

### 6.2 tasks.yaml

```yaml
write_e2e_tests:
  description: >
    Generate end-to-end user journey test files based on the test plan §4.
    
    For each journey in the plan:
    1. Create a .e2e.spec.ts file named after the workflow
    2. Implement the full step sequence from the plan
    3. Use API (request fixture) for data setup in beforeAll
    4. Use Page Object Models for UI interactions
    5. Assert at every step transition
    6. Clean up created data in afterAll
    
    AVAILABLE ROLES: {roles}
    CREDENTIALS: {credentials}
    APP URL: {app_url}
    OUTPUT DIR: {output_dir}/tests/e2e/
    
    TEST PLAN (E2E section):
    {test_plan}
    
    API SPECIFICATION (for data setup endpoints):
    {api_spec}
    
    CONTEXT (for page routes and domain understanding):
    {context_document}
    {feedback}
    
    RULES:
    - One file per business journey
    - Each test must be independently runnable
    - Use unique data (timestamps/UUIDs) for test isolation
    - Import Models from ../../ui/models/ when available
    - Exercise the login flow in every test (no storageState shortcuts)
    - Maximum 5-7 E2E test files total — quality over quantity
    - Capture resource IDs from API responses for cleanup
    - Use waitForResponse() over waitForTimeout()
  expected_output: >
    Multiple .e2e.spec.ts files written to tests/e2e/ covering the critical
    user journey workflows defined in the test plan.
  agent: e2e_test_writer
```

## 7. Playwright MCP Usage (Optional)

When the Playwright MCP tool is available, the E2E Writer may use it for:
- **Exploration**: Navigate the app to discover exact URLs, selectors, and page transitions
- **Selector validation**: Confirm that locators work on the live page before writing them into tests
- **Flow discovery**: Walk through a journey manually to understand the exact steps

**Rules for MCP usage:**
- MCP is for exploration ONLY — the generated .spec.ts files use standard Playwright, not MCP
- Do not spend more than 2-3 MCP interactions per journey — it's expensive
- Prefer locators from Models over MCP-discovered selectors
- If MCP shows the app is unreachable, proceed using context doc and API spec (best effort)

## 8. Handling Reviewer Feedback

On retry iterations, the E2E Writer receives feedback from the Reviewer:

```
FEEDBACK FROM REVIEWER (fix these):
- project-lifecycle.e2e.spec.ts: Selector '.create-btn' not found
  Fix: Use getByRole('button', { name: 'Create' }) instead
- billing-workflow.e2e.spec.ts: Timeout waiting for /api/invoices response
  Fix: Increase timeout or add explicit waitForResponse before assertion
```

**Response strategy:**
1. Only fix TEST_BUG feedback — ignore APP_BUG and DATA_DEPENDENT
2. Apply the suggested fix exactly if it's specific
3. If the fix is vague, use the Playwright MCP (if available) to investigate
4. Rewrite the entire file with fixes applied — don't patch
5. If the same test fails 3 times, mark it as `test.skip()` with a comment explaining why

## 9. Failure Modes & Handling

| Scenario | Handling |
|----------|---------|
| No E2E test cases in the plan | Skip — write nothing; log that E2E section was empty |
| Page Object Models not yet created by FE Writer | Create minimal inline models with TODO comments |
| API spec missing for data setup endpoints | Use UI for setup (slower but works); add note |
| Unknown page URLs | Use paths from context-document.md §4.2; add comments if uncertain |
| App requires complex setup (feature flags, external services) | Note in test file; use test.skip() with explanation |
| Too many journeys in the plan (>7) | Implement P0 journeys only; note P1 as "planned but deferred" |

## 10. Definition of Done

The E2E Test Writer's task is complete when:

1. One .e2e.spec.ts file exists per journey in the test plan §4 (up to 7 max)
2. Each test file compiles (valid TypeScript, correct imports)
3. Each test has: describe block, beforeAll/afterAll for data, explicit assertions
4. Data setup uses API, verification uses UI, cleanup uses API
5. No hardcoded credentials — all from `getAccountByRole()`
6. No `waitForTimeout()` — uses auto-waiting or `waitForResponse()`
7. Files written to `{output_dir}/tests/e2e/`

## 11. Performance Characteristics

| Metric | Target |
|--------|--------|
| Files generated | 3-7 per run |
| LLM calls | 1-2 per file (generation + self-review) |
| Token usage | ~15K input / ~3K output per file |
| Time per file | ~30-60 seconds (LLM generation) |
| Total agent runtime | 2-5 minutes |
