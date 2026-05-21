agent: 'Reviewer'
parent_document: 'TestForge Architecture Decision Document'
owner: 'Agile Bridge'
date: '2026-05-21'
status: 'Design — pre-implementation'

# Reviewer Agent — Detailed Design

Companion document to the TestForge architecture. This document is the full specification for the Reviewer agent: the quality gate that executes generated tests, diagnoses failures, and routes actionable feedback back to the Writers for iterative improvement.

## 1. Purpose & Position in the Flow

The Reviewer is the final agent before delivery. It closes the feedback loop: Writers produce code → Reviewer runs it → if it fails, Reviewer diagnoses → Writers fix → repeat (up to 3 iterations). Without the Reviewer, TestForge would produce tests that might not compile, let alone pass.

```
BE WRITER ──┐
FE WRITER ──┼──▶ ┌─────────────────┐ ──▶ COMPLETE (all pass)
E2E WRITER ─┘    │    REVIEWER      │
                  │  (this agent)    │ ──▶ RETRY (test bugs → Writers)
                  └─────────────────┘
                           │
                           ├── Uses: test_runner_tool (tsc + playwright test)
                           ├── Uses: file_read_tool (read failing test files)
                           └── Produces: structured feedback + test results
```

### Contract with the rest of the system

| Concern | Commitment |
|---------|-----------|
| Inputs | Generated test files in {output_dir} + app URL + credentials |
| Outputs | Structured test results + categorised feedback for Writers |
| Execution | Runs `tsc --noEmit` first (compilation gate), then `npx playwright test` |
| Side effects | Only reads test files and runs them; never modifies test code |
| Decision output | Returns "complete" (all pass or max iterations) or "retry" (test bugs found) |
| Failure mode | Always produces a result — even if everything fails, provides diagnostics |

## 2. Inputs

### 2.1 Generated Test Files

The output directory containing:
```
{output_dir}/
├── playwright.config.ts
├── package.json
├── tsconfig.json
├── tests/
│   ├── api/         ← BE Writer's output
│   ├── ui/          ← FE Writer's output
│   └── e2e/         ← E2E Writer's output
├── ui/models/       ← FE Writer's Page Object Models
├── data/            ← Credentials, test data
├── fixtures/        ← Auth fixtures
└── core/            ← Types, constants
```

### 2.2 Application URL

Required to determine if the app is reachable (ENVIRONMENT failures).

### 2.3 Test Plan (for context)

Used to understand test intent when diagnosing failures:
- Was this test supposed to get a 403? (Then 403 is a PASS, not a failure)
- Is this a negative test? (Then an error message is expected)

### 2.4 Iteration Context

- Current iteration number (1, 2, or 3)
- Previous feedback (what was already suggested in prior iterations)
- Which tests already passed (don't re-run passing tests if possible)

## 3. Execution Strategy

### 3.1 Phase 1 — Compilation Gate

```bash
cd {output_dir}
npx tsc --noEmit
```

**If compilation fails:**
- Parse the TypeScript errors
- Map each error to the source file and line
- Categorise as TEST_BUG (always — compilation errors are always test writer's fault)
- Provide specific fix: "Missing import", "Type error", "Property does not exist"
- **Do NOT proceed to Phase 2** — no point running tests that don't compile
- Return immediately with COMPILE_ERROR feedback

**Common compilation errors and fixes:**
| Error | Typical Fix |
|-------|------------|
| `Cannot find module '../../ui/models/...'` | Model doesn't exist yet — Writer needs to create it |
| `Property 'x' does not exist on type 'y'` | Wrong method name on Model — check FE Writer's output |
| `Type 'string' is not assignable to type 'number'` | Wrong data type in test payload |
| `Parameter 'x' implicitly has an 'any' type` | Add type annotation |
| `Cannot find name 'expect'` | Missing import from @playwright/test |

### 3.2 Phase 2 — Test Execution

```bash
cd {output_dir}
npx playwright test --reporter=json
```

**Configuration:**
- Use JSON reporter for machine-parseable results
- Run all tests (don't cherry-pick — we need full picture)
- Timeout: use playwright.config.ts settings (default 30s per test)
- Retries: 0 on first reviewer pass (want to see real failures, not masked by retries)

### 3.3 Phase 3 — Results Analysis

Parse the JSON report and for each failure:

1. **Read the error message** — what actually went wrong
2. **Read the failing test file** — understand what the test was trying to do
3. **Read the stack trace** — identify the exact line that failed
4. **Categorise** the failure (see §4)
5. **Determine actionability** — can the Writer fix this?
6. **Provide specific fix instruction** — not vague "try again" but exact steps

## 4. Failure Categorisation

### 4.1 TEST_BUG — Actionable, route to Writer

The test code itself is wrong. The Writer can fix this.

| Symptom | Root Cause | Fix Instruction |
|---------|-----------|----------------|
| `locator.click: Target closed` | Wrong selector, element doesn't exist | "Use getByRole('button', { name: '...' }) instead" |
| `expect(received).toBe(expected)` | Wrong assertion value | "Expected value is X based on API spec; change assertion to X" |
| `TimeoutError: locator.click` | Element not visible, wrong page | "Navigate to correct page first" or "Wait for element with waitFor()" |
| `ReferenceError: X is not defined` | Missing import or variable | "Add import for X from ..." |
| `TypeError: Cannot read property 'x'` | Null reference in test logic | "Add null check or verify API response before accessing" |
| `net::ERR_CONNECTION_REFUSED` with wrong URL | Base URL misconfigured in test | "Use baseURL from config, not hardcoded URL" |

### 4.2 APP_BUG — Not actionable, report as finding

The application itself has a defect. The test is correct; the app is wrong.

| Symptom | How to Identify |
|---------|----------------|
| 500 Internal Server Error | The test sent a valid request; server crashed |
| Response body doesn't match documented schema | API spec says field X exists, but response lacks it |
| UI shows error for valid operation | Test followed the happy path correctly |
| Redirect to error page | Application threw an unhandled exception |

**Action:** Report in the findings section. Do NOT tell the Writer to change the test. The test correctly found a bug.

### 4.3 DATA_DEPENDENT — Not actionable on retry

The failure is because expected data doesn't exist in the target application.

| Symptom | How to Identify |
|---------|----------------|
| Empty list/table when test expects items | Test asserts on existing data that isn't present |
| 404 for a specific resource ID | Test references a resource that doesn't exist |
| "No results" message | Search/filter returns nothing |

**Action:** Report but do NOT route to Writer. This is a test environment issue. Note: if the test *should* be creating its own data (self-sufficient), then it's a TEST_BUG (missing data setup).

### 4.4 FLAKY — Partially actionable

The test sometimes passes, sometimes fails.

| Symptom | How to Identify |
|---------|----------------|
| Timeout on fast-loading page | Works locally, fails in CI-like conditions |
| Race condition in assertions | Element appears briefly then changes |
| Network timing issue | API response arrives after assertion |

**Action:** Suggest adding `test.retry(2)` annotation. If the same test is flaky across iterations, suggest `waitForResponse()` or `waitForLoadState()`.

### 4.5 ENVIRONMENT — Not actionable, blocking

The target application is unreachable or broken globally.

| Symptom | How to Identify |
|---------|----------------|
| All tests fail with connection refused | App is not running |
| All tests fail with timeout | App is running but not responding |
| All tests fail with SSL error | Certificate issue |

**Action:** Report as BLOCKED. Do NOT retry. The system cannot proceed until the environment is fixed.

## 5. Output Format

### 5.1 Structured Results (for state)

```json
{
  "summary": {
    "total": 45,
    "passed": 38,
    "failed": 5,
    "skipped": 2,
    "compile_errors": 0
  },
  "all_passing": false,
  "category_breakdown": {
    "TEST_BUG": 3,
    "APP_BUG": 1,
    "DATA_DEPENDENT": 1,
    "FLAKY": 0,
    "ENVIRONMENT": 0
  }
}
```

### 5.2 Feedback (for Writers)

Only TEST_BUG entries become feedback. Format:

```
TEST_BUG:|tests/api/projects.spec.ts|Selector '.create-btn' not found on line 42|Use page.getByRole('button', { name: 'Create Project' }) instead
TEST_BUG:|tests/ui/dashboard.spec.ts|Import error: ../../ui/models/dashboard/dashboard.model not found|FE Writer needs to create DashboardModel at ui/models/dashboard/dashboard.model.ts
TEST_BUG:|tests/e2e/project-lifecycle.e2e.spec.ts|Timeout waiting for navigation to /projects|Add await page.waitForURL('**/projects') after clicking the link
```

### 5.3 Findings Report (for output)

```markdown
## Test Findings

### App Bugs Discovered
1. **POST /api/projects returns 500 when description is null** (tests/api/projects.spec.ts:67)
   - Expected: 400 with validation error
   - Actual: 500 Internal Server Error
   - Severity: High — data validation gap

### Data Dependencies
1. **GET /api/projects returns empty list** (tests/api/projects.spec.ts:23)
   - The test assumes existing projects but the environment has none
   - Suggestion: Add data setup in beforeAll or skip if empty

### Environment Issues
- None detected
```

## 6. Decision Logic

After analysis, the Reviewer returns one of two routes:

### Route: "complete"
- ALL tests pass (ideal)
- OR max iterations reached (stop even if failures remain)
- OR only APP_BUG / DATA_DEPENDENT / ENVIRONMENT failures remain (Writers can't fix these)

### Route: "retry"
- At least one TEST_BUG exists
- AND iteration < max_iterations (default 3)
- AND the bugs are different from last iteration (not stuck in a loop)

**Loop detection:**
If the same file has the same error across 2 iterations, mark it as `test.skip()` in feedback:
"This test has failed twice with the same error. Suggest `test.skip('Known issue: [reason]')` to unblock the suite."

## 7. CrewAI Agent Definition

### 7.1 agents.yaml

```yaml
reviewer:
  role: "Test Suite Quality Reviewer"
  goal: >
    Execute the generated test suite, analyse every failure, categorise each as
    TEST_BUG (writer's fault), APP_BUG (genuine defect), DATA_DEPENDENT (environment),
    FLAKY (timing), or ENVIRONMENT (app unreachable). Provide specific, actionable
    fix instructions for TEST_BUG failures only. Never waste retry iterations on
    failures the writers cannot fix.
  backstory: >
    You are a senior QA lead who has seen every kind of test failure. You know the
    difference between a broken test and a broken app — and you never confuse the two.
    When a test fails, you read the error, the test code, and the expected behaviour,
    then you make a clear diagnosis. Your fix suggestions are specific: exact selectors,
    exact imports, exact assertion values. You never say "try again" without saying
    exactly what to try differently. You are the last quality gate before delivery —
    if you pass a test suite, it's genuinely ready.
  tools:
    - test_runner_tool
    - file_read_tool
  llm: openai/gpt-4o-mini
  max_iter: 3
  memory: true
  verbose: true
```

### 7.2 tasks.yaml

```yaml
execute_tests:
  description: >
    Run the generated test suite in {output_dir}:
    
    1. Use test_runner_tool with output_dir={output_dir}
       - Phase 1: tsc --noEmit (compilation gate)
       - Phase 2: npx playwright test (only if compilation passes)
    
    2. If compilation fails:
       - Parse every TypeScript error
       - Map each to a file and line
       - Categorise ALL as TEST_BUG
       - Provide specific fix per error
       - DO NOT run playwright test
       - Return immediately
    
    3. If compilation passes but tests fail:
       - Read each failing test file using file_read_tool
       - Read the error message and stack trace
       - Categorise each failure:
         * TEST_BUG: wrong selector, bad assertion, missing import → provide fix
         * APP_BUG: genuine application defect → report as finding, don't fix
         * DATA_DEPENDENT: missing data, empty state → report, don't feed back
         * FLAKY: intermittent → suggest retry annotation
         * ENVIRONMENT: app unreachable → report as blocked
    
    4. Output format:
    
       ## Results Summary
       - Total: X | Passed: Y | Failed: Z | Skipped: W
       - Compile Errors: (count or "none")
       
       ## TEST_BUG Failures (actionable)
       TEST_BUG:|[file_path]|[error description]|[specific fix instruction]
       TEST_BUG:|[file_path]|[error description]|[specific fix instruction]
       
       ## APP_BUG Findings
       - [description of genuine bugs found]
       
       ## DATA_DEPENDENT Issues
       - [description of data issues]
       
       ## Decision
       ROUTE: complete | retry
       REASON: [why]
    
    APP URL: {app_url}
    ROLES: {roles}
  expected_output: >
    Structured analysis with categorised failures, fix instructions for TEST_BUG
    entries, findings for APP_BUG entries, and a clear route decision.
  agent: reviewer
```

## 8. Model Selection: Why GPT-4o-mini

The Reviewer uses `openai/gpt-4o-mini` instead of GPT-4.1 because:
- Its task is analytical, not generative — reading errors and classifying them
- Speed matters — the Reviewer runs on every iteration (potentially 3x)
- Cost efficiency — Reviewer is the most frequently invoked agent
- Accuracy is sufficient — error categorisation doesn't need the smartest model
- The fixes it suggests are formulaic (add import, change selector, fix type)

If the Reviewer's accuracy proves insufficient (>20% miscategorisations), escalate to GPT-4.1.

## 9. Failure Modes & Handling

| Scenario | Handling |
|----------|---------|
| test_runner_tool unavailable (no Node.js) | Report ENVIRONMENT block; cannot proceed |
| package.json dependencies not installed | Run `npm install` first (test_runner_tool handles this) |
| playwright browsers not installed | Run `npx playwright install chromium` (test_runner_tool handles this) |
| All tests pass on first run | Return "complete" immediately; no feedback needed |
| Same test fails identically across 2 iterations | Suggest test.skip() — avoid infinite loops |
| More than 20 failures | Focus feedback on the first 10 (most likely compile errors cascading) |
| JSON reporter produces invalid output | Fall back to parsing stdout text output |
| Test files are empty or missing | Report as TEST_BUG with "file is empty — Writer failed to write content" |

## 10. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Running generated code | Tests only interact with the target app (already under test); no privilege escalation |
| Credential exposure in logs | test_runner_tool redacts any env var values from output |
| Test creating/deleting production data | Target URL must be a test environment; Reviewer doesn't validate this (orchestrator's responsibility) |
| Malicious test code (injection) | Tests are generated by our own agents from known inputs; no external code execution |

## 11. Performance & Cost

| Metric | Target |
|--------|--------|
| Compilation check | <10 seconds |
| Full test suite execution | 1-5 minutes depending on test count |
| LLM analysis of results | ~10K input / ~2K output tokens per run |
| Total per iteration | 2-6 minutes |
| Max iterations | 3 (configurable) |
| Total worst case | 3 × 6 min = 18 minutes |

## 12. Definition of Done

The Reviewer's task is complete when:

1. Tests have been executed (compilation + runtime)
2. Every failure is categorised (no uncategorised failures)
3. TEST_BUG failures have specific, actionable fix instructions
4. APP_BUG failures are documented as findings
5. A clear route decision is made: "complete" or "retry"
6. Feedback is structured in the parseable `TEST_BUG:|file|issue|fix` format
7. Results summary includes pass/fail/skip counts

## 13. Interaction with the Retry Loop

```
Iteration 1:
  Reviewer runs → finds 5 TEST_BUGs → routes "retry"
  Writers fix those 5 bugs

Iteration 2:
  Reviewer runs → finds 2 new TEST_BUGs (from the fixes) + 1 APP_BUG → routes "retry"
  Writers fix those 2 bugs (APP_BUG ignored)

Iteration 3:
  Reviewer runs → 1 TEST_BUG persists from iteration 2 → routes "complete" (max iterations)
  OR: all pass → routes "complete" (success)
```

**Iteration 3 special behaviour:**
Even if TEST_BUGs remain, the Reviewer returns "complete" because max iterations is reached. The remaining failures are documented in the findings report so the user knows what wasn't resolved.

## 14. Handoff

| Direction | What | Format |
|-----------|------|--------|
| → Orchestrator | Route decision | "complete" or "retry" string |
| → State | Test results | Structured dict with counts and categories |
| → Writers (via state) | Feedback | List of `{test_file, issue, fix_suggestion}` dicts |
| → Output | Findings report | Markdown file with app bugs and data issues |
