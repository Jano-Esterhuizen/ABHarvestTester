"""Scaffold module — creates the test framework output structure."""

import logging
from pathlib import Path

from testforge.state import TestForgeState

logger = logging.getLogger("testforge")


def scaffold_output(state: TestForgeState) -> None:
    """Create the 6-layer test framework structure from templates."""
    output = Path(state.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    dirs = [
        "core/types",
        "core/constants",
        "core/interfaces",
        "data/credentials",
        "data/generators",
        "data/models",
        "utils/actions",
        "utils/wait",
        "utils/logger",
        "ui/pages",
        "ui/objects",
        "ui/models",
        "business/workflows",
        "business/validators",
        "tests/api/auth",
        "tests/api/endpoints",
        "tests/api/roles",
        "tests/ui/auth",
        "tests/ui/pages",
        "tests/ui/roles",
        "tests/e2e",
        "fixtures",
    ]

    for d in dirs:
        (output / d).mkdir(parents=True, exist_ok=True)

    # Write config files from templates
    _write_playwright_config(output, state)
    _write_package_json(output)
    _write_tsconfig(output)
    _write_core_types(output, state)
    _write_credentials(output, state)
    _write_fixtures(output, state)

    logger.info(f"Framework scaffolded at: {output}")


def _write_playwright_config(output: Path, state: TestForgeState):
    content = f'''import {{ defineConfig, devices }} from "@playwright/test";

export default defineConfig({{
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html"], ["json", {{ outputFile: "results.json" }}]],
  use: {{
    baseURL: "{state.app_url}",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  }},
  projects: [
    {{
      name: "chromium",
      use: {{ ...devices["Desktop Chrome"] }},
    }},
  ],
}});
'''
    (output / "playwright.config.ts").write_text(content, encoding="utf-8")


def _write_package_json(output: Path):
    content = """{
  "name": "testforge-generated-tests",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "test": "npx playwright test",
    "test:ui": "npx playwright test --ui",
    "report": "npx playwright show-report"
  },
  "devDependencies": {
    "@playwright/test": "^1.50.0",
    "typescript": "^5.7.0"
  }
}
"""
    (output / "package.json").write_text(content, encoding="utf-8")


def _write_tsconfig(output: Path):
    content = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "outDir": "./dist",
    "rootDir": ".",
    "baseUrl": ".",
    "paths": {
      "@core/*": ["core/*"],
      "@data/*": ["data/*"],
      "@utils/*": ["utils/*"],
      "@ui/*": ["ui/*"],
      "@business/*": ["business/*"],
      "@fixtures/*": ["fixtures/*"]
    }
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
"""
    (output / "tsconfig.json").write_text(content, encoding="utf-8")


def _write_core_types(output: Path, state: TestForgeState):
    # Enums
    roles = state.credentials.get("roles", [])
    role_values = ", ".join(f'  {r["name"].upper()} = "{r["name"]}"' for r in roles)
    enums = f'''export enum UserRole {{
{role_values}
}}

export enum TestStatus {{
  PASSED = "passed",
  FAILED = "failed",
  SKIPPED = "skipped",
}}
'''
    (output / "core/types/enums.ts").write_text(enums, encoding="utf-8")

    # Constants
    constants = f'''export const APP_CONSTANTS = {{
  BASE_URL: process.env.BASE_URL || "{state.app_url}",
  DEFAULT_TIMEOUT: 30000,
  NAVIGATION_TIMEOUT: 15000,
}};
'''
    (output / "core/constants/app.constants.ts").write_text(constants, encoding="utf-8")


def _write_credentials(output: Path, state: TestForgeState):
    roles = state.credentials.get("roles", [])
    imports = "import { UserRole } from '../../core/types/enums';\n\n"
    interface = """export interface AccountCredentials {
  role: UserRole;
  username: string;
  password: string;
  description: string;
}

"""
    accounts_array = "const accounts: AccountCredentials[] = [\n"
    for role in roles:
        accounts_array += f"""  {{
    role: UserRole.{role['name'].upper()},
    username: process.env.{role['name'].upper()}_USERNAME || "{role['username']}",
    password: process.env.{role['name'].upper()}_PASSWORD || "{role['password']}",
    description: "{role.get('description', '')}",
  }},
\n"""
    accounts_array += "];\n\n"

    getter = """export function getAccountByRole(role: string): AccountCredentials {
  const account = accounts.find(a => a.role === role);
  if (!account) throw new Error(`No account found for role: ${role}`);
  return account;
}

export function getAllAccounts(): AccountCredentials[] {
  return accounts;
}
"""
    content = imports + interface + accounts_array + getter
    (output / "data/credentials/accounts.ts").write_text(content, encoding="utf-8")


def _write_fixtures(output: Path, state: TestForgeState):
    login = state.credentials.get("login", {})
    url_path = login.get("url_path", "/login")

    content = f'''import {{ test as base, Page }} from "@playwright/test";
import {{ getAccountByRole, AccountCredentials }} from "../data/credentials/accounts";

type AuthFixtures = {{
  authenticatedPage: Page;
  account: AccountCredentials;
}};

export const test = base.extend<AuthFixtures & {{ role: string }}>( {{
  role: ["user", {{ option: true }}],

  account: async ({{ role }}, use) => {{
    const account = getAccountByRole(role);
    await use(account);
  }},

  authenticatedPage: async ({{ page, account }}, use) => {{
    await page.goto("{url_path}");
    await page.locator("{login.get('username_field', '#email')}").fill(account.username);
    await page.locator("{login.get('password_field', '#password')}").fill(account.password);
    await page.locator("{login.get('submit_button', 'button[type=submit]')}").click();
    await page.waitForLoadState("networkidle");
    await use(page);
  }},
}});

export {{ expect }} from "@playwright/test";
'''
    (output / "fixtures/auth.fixture.ts").write_text(content, encoding="utf-8")
