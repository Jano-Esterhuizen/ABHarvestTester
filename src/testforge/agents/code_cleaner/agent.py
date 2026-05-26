"""Code Cleaner — fixes LLM generation artifacts in test files before review."""

import logging
import os
import re
import subprocess
from pathlib import Path

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew

from testforge.state import TestForgeState
from testforge.llm import get_llm

logger = logging.getLogger("testforge")


def _strip_markdown_fences(content: str) -> str:
    """Remove markdown code fences and leading/trailing whitespace."""
    # Remove any line that is just a fence, with optional language tag.
    # Handles variations like leading spaces, ts/typescript tags, and mixed casing.
    content = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*$", "", content, flags=re.MULTILINE)

    # Remove accidental inline fence tokens that occasionally leak into output.
    content = content.replace("```typescript", "")
    content = content.replace("```ts", "")
    content = content.replace("```", "")

    # Collapse excessive blank lines introduced by fence removal.
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _fix_playwright_imports(content: str) -> str:
    """Fix common Playwright import mistakes."""
    # Fix: `request` is a fixture in Playwright, not an export — remove it from imports
    # Generic approach: find any @playwright/test import containing `request` and strip it
    def _strip_request_from_import(m: re.Match) -> str:
        symbols = [s.strip() for s in m.group(1).split(",")]
        # request is a fixture, not an import. RequestOptions is a common hallucinated type.
        symbols = [s for s in symbols if s not in {"request", "RequestOptions"}]
        if not symbols:
            return ""  # Remove the entire import line
        return f"import {{ {', '.join(symbols)} }} from '@playwright/test'"

    content = re.sub(
        r"import\s*\{([^}]+)\}\s*from\s*['\"]@playwright/test['\"]",
        _strip_request_from_import,
        content,
    )
    # Clean up empty lines left by removed import
    content = re.sub(r"^\s*;\s*\n", "", content, flags=re.MULTILINE)

    # Fix: import { Page } from 'playwright' -> import { Page } from '@playwright/test'
    content = re.sub(
        r"from\s*['\"]playwright['\"]",
        "from '@playwright/test'",
        content,
    )

    # Ensure 'expect' is imported if used but not imported
    if "expect(" in content or "expect." in content:
        first_import = re.search(r"import\s*\{([^}]+)\}\s*from\s*['\"]@playwright/test['\"]", content)
        if first_import:
            symbols = first_import.group(1)
            if "expect" not in symbols:
                content = content.replace(first_import.group(0),
                    f"import {{{symbols}, expect }} from '@playwright/test'")
        elif not re.search(r"import.*expect.*from", content):
            # No playwright import at all — add one
            content = "import { test, expect } from '@playwright/test';\n\n" + content

    # Fix: `page` and `context` fixtures cannot be used in beforeAll (per-test only)
    # Convert test.beforeAll(async ({ page }) => to test.beforeEach(async ({ page }) =>
    content = re.sub(
        r"test\.beforeAll\(async\s*\(\{[^}]*(page|context)[^}]*\}\)\s*=>",
        lambda m: m.group(0).replace("beforeAll", "beforeEach"),
        content,
    )

    # Fix: standalone `request` usage in beforeAll without fixture pattern
    # If beforeAll uses `request` but not as fixture param, wrap it
    # Pattern: test.beforeAll(async () => { ... request.post ... })
    # Should be: test.beforeAll(async ({ request }) => { ... })
    content = re.sub(
        r"test\.beforeAll\(async\s*\(\)\s*=>\s*\{",
        "test.beforeAll(async ({ request }) => {",
        content,
    )

    # Fix: `test.request.post/get/...` → just `request.post/get/...`
    # (test.request is not a valid Playwright API; request is a fixture)
    content = re.sub(r"\btest\.request\.(post|get|put|patch|delete|head)\(", r"request.\1(", content)

    # Fix: standalone functions that use bare `request` — add request parameter
    # Pattern: async function login(...) { ... request.post(...) ... }
    # Should be: async function login(..., request: any) { ... }
    if re.search(r"(?<!\w)request\.(post|get|put|patch|delete|head|fetch)\(", content):
        # Find function declarations that reference `request.` in their body
        lines = content.split("\n")
        func_pattern = re.compile(r"^(\s*)(export\s+)?(async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*(\{?)")
        func_fixes: list[tuple[str, str, str]] = []  # (func_name, old_params, new_params)

        i = 0
        while i < len(lines):
            m = func_pattern.match(lines[i])
            if m:
                params = m.group(5)
                func_name = m.group(4)
                # Check if 'request' is already a parameter
                if "request" not in params:
                    # Scan the function body for bare `request.`
                    brace_count = lines[i].count("{") - lines[i].count("}")
                    uses_request = False
                    for j in range(i + 1, min(i + 50, len(lines))):
                        brace_count += lines[j].count("{") - lines[j].count("}")
                        if re.search(r"\brequest\.(post|get|put|patch|delete|head|fetch)\(", lines[j]):
                            uses_request = True
                        if brace_count <= 0:
                            break
                    if uses_request:
                        func_fixes.append((func_name, params, params))
            i += 1

        # Apply function parameter fixes
        for func_name, old_params, _ in func_fixes:
            # Add `request: any` parameter
            if old_params.strip():
                new_params = f"{old_params}, request: any"
            else:
                new_params = "request: any"
            # Fix the function declaration
            content = re.sub(
                rf"((?:async\s+)?function\s+{re.escape(func_name)}\s*\(){re.escape(old_params)}(\))",
                rf"\g<1>{new_params}\2",
                content,
                count=1,
            )
            # Fix call sites — add `request` argument
            # Pattern: funcName(args) → funcName(args, request) or funcName(request)
            def _fix_call(m: re.Match) -> str:
                args = m.group(1)
                if args.strip():
                    return f"{func_name}({args}, request)"
                return f"{func_name}(request)"
            content = re.sub(
                rf"(?<!function\s){re.escape(func_name)}\(([^)]*)\)(?!\s*\{{)",
                _fix_call,
                content,
            )

    # Fix: test callbacks that use `request` without destructuring it from fixture
    # Pattern: test('...', async () => { ... request.post ... })
    # Should be: test('...', async ({ request }) => { ... })
    # Find test callbacks with empty params that use request inside
    def _fix_test_request_scope(m: re.Match) -> str:
        """If the test body references `request.`, add it to fixtures."""
        prefix = m.group(0)
        # Look ahead to see if request is used (we'll just always add it for the matched pattern)
        return prefix.replace("async () =>", "async ({ request }) =>")

    # Only fix if `request.` is used somewhere in the file (as standalone, not response.request)
    if re.search(r"(?<!\w)request\.(post|get|put|patch|delete|head|fetch)\(", content):
        content = re.sub(
            r"test\([^)]+,\s*async\s*\(\)\s*=>",
            lambda m: m.group(0).replace("async () =>", "async ({ request }) =>"),
            content,
        )

    # Fix: response.data -> (await response.json()) — Playwright doesn't have .data
    content = re.sub(
        r"(\w+Response|\w+response|response)\.data\b",
        r"(await \1.json())",
        content,
    )

    return content


def _fix_missing_expect_import(content: str) -> str:
    """Add expect to import if it's used but not imported."""
    if "expect(" not in content and "expect." not in content:
        return content

    # Check if expect is already imported
    import_match = re.search(r"import\s*\{([^}]+)\}\s*from\s*['\"]@playwright/test['\"]", content)
    if import_match:
        symbols = import_match.group(1)
        if "expect" not in symbols:
            new_symbols = symbols.rstrip() + ", expect "
            content = content[:import_match.start(1)] + new_symbols + content[import_match.end(1):]

    # Normalize multiple spaces in imports
    content = re.sub(r"import\s*\{\s*(.+?)\s*\}", lambda m: "import { " + ", ".join(s.strip() for s in m.group(1).split(",") if s.strip()) + " }", content)

    return content


def _deduplicate_imports(content: str) -> str:
    """Remove duplicate import statements and consolidate imports from same module."""
    lines = content.split("\n")
    module_imports: dict[str, set[str]] = {}
    module_order: list[str] = []
    passthrough_imports: list[str] = []
    body_lines: list[str] = []

    named_import_pattern = re.compile(
        r"^import\s*\{([^}]+)\}\s*from\s*(['\"][^'\"]+['\"])\s*;?\s*$"
    )

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import "):
            m = named_import_pattern.match(stripped)
            if m:
                names = {n.strip() for n in m.group(1).split(",") if n.strip()}
                module_path = m.group(2)
                if module_path not in module_imports:
                    module_imports[module_path] = set()
                    module_order.append(module_path)
                module_imports[module_path].update(names)
            else:
                if stripped not in passthrough_imports:
                    passthrough_imports.append(stripped)
        else:
            body_lines.append(line)

    merged_imports: list[str] = []
    for module_path in module_order:
        names = sorted(module_imports[module_path])
        merged_imports.append(f"import {{ {', '.join(names)} }} from {module_path};")
    merged_imports.extend(passthrough_imports)

    if not merged_imports:
        return content

    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)

    return "\n".join(merged_imports) + "\n\n" + "\n".join(body_lines)


def _remove_phantom_imports(content: str) -> str:
    """Remove import statements that reference non-existent local modules."""
    lines = content.split("\n")
    # Find all classes defined in this file
    class_names = set(re.findall(r"(?:export\s+)?class\s+(\w+)", content))

    result = []
    for line in lines:
        # Check if it's a relative import (./something or ../something)
        match = re.match(r"import\s*\{([^}]+)\}\s*from\s*['\"](\.\./|\./)", line)
        if match:
            imported = {s.strip() for s in match.group(1).split(",")}
            # If all imported names are defined in this file, remove the import
            if imported.issubset(class_names):
                continue
            # Remove any relative import from paths like ../src/app/... (hallucinated)
            if re.search(r"from\s*['\"]\.\.?/src/", line):
                continue
        result.append(line)

    return "\n".join(result)


def _remove_missing_file_imports(content: str, spec_file: Path) -> str:
    """Remove relative imports where the referenced file doesn't exist on disk."""
    lines = content.split("\n")
    result = []
    spec_dir = spec_file.parent

    for line in lines:
        # Match both named imports: import { X } from './path'
        # and default imports: import X from './path'
        match = re.match(r"import\s+(?:\{[^}]+\}|\w+)\s+from\s*['\"](\.[^'\"]+)['\"]", line)
        if match:
            rel_module = match.group(1)
            # Try resolving the module path (with .ts extension)
            candidates = [
                spec_dir / (rel_module + ".ts"),
                spec_dir / (rel_module + ".js"),
                spec_dir / rel_module / "index.ts",
                spec_dir / rel_module / "index.js",
            ]
            if not any(c.exists() for c in candidates):
                logger.info(f"  Removing import of non-existent module: {rel_module}")
                continue
        result.append(line)

    return "\n".join(result)


def _fix_auth_password_placeholders(content: str, credentials: dict) -> str:
    """Replace obvious placeholder passwords with real role passwords.

    Only updates entries where email/username matches a known role and the
    password is a known placeholder value.
    """
    roles = credentials.get("roles", []) if isinstance(credentials, dict) else []
    if not roles:
        return content

    placeholder_values = {
        "password",
        "your_password",
        "password123",
        "changeme",
        "<password>",
        "testpass",
    }

    for role in roles:
        email_or_user = role.get("username") or role.get("email") or ""
        password = role.get("password") or ""
        if not email_or_user or not password:
            continue

        # Match login payloads like:
        # email: 'director@x', password: 'password'
        # username: 'director@x', password: 'your_password'
        pattern = re.compile(
            rf"((?:email|username)\s*:\s*['\"]{re.escape(email_or_user)}['\"]\s*,\s*password\s*:\s*['\"])([^'\"]+)(['\"])",
            flags=re.IGNORECASE,
        )

        def _replace_if_placeholder(m: re.Match) -> str:
            current = m.group(2).strip().lower()
            if current in placeholder_values:
                return f"{m.group(1)}{password}{m.group(3)}"
            return m.group(0)

        content = pattern.sub(_replace_if_placeholder, content)

    return content


def _enforce_login_payload_contract(content: str, credentials: dict) -> str:
    """Align auth payload keys with credentials.login config (e.g., email vs username)."""
    if not isinstance(credentials, dict):
        return content

    login_cfg = credentials.get("login", {})
    username_field = str(login_cfg.get("username_field", "username") or "username").strip()
    password_field = str(login_cfg.get("password_field", "password") or "password").strip()

    # Only apply this rewrite to files that appear to test auth/login flows.
    if "/api/auth/login" not in content and "auth/login" not in content:
        return content

    if username_field and username_field != "username":
        content = re.sub(r"\busername\s*:", f"{username_field}:", content)
    if password_field and password_field != "password":
        content = re.sub(r"\bpassword\s*:", f"{password_field}:", content)

    return content


def _relax_invalid_login_status_assertions(content: str) -> str:
    """Normalize invalid-login assertions to allow either 400 or 401."""
    if "/api/auth/login" not in content and "invalid credentials" not in content.lower():
        return content

    # Replace brittle exact 401 checks near invalid-login tests.
    content = re.sub(
        r"expect\(\s*response\.status\(\)\s*\)\.toBe\(\s*401\s*\)\s*;",
        "expect([400, 401]).toContain(response.status());",
        content,
    )
    return content


def _ensure_exported_pom_classes(content: str, spec_file: Path) -> str:
    """Ensure .page.ts classes are exported so spec imports are constructible at runtime."""
    if not spec_file.name.endswith(".page.ts"):
        return content

    return re.sub(
        r"^\s*class\s+(\w+Page)\b",
        r"export class \1",
        content,
        flags=re.MULTILINE,
    )


def _add_pom_imports(content: str, spec_file: Path) -> str:
    """Auto-add imports for POM classes used but not imported in spec files."""
    # Only for spec files (not POM files)
    if ".page." in spec_file.name or "class " in content:
        return content

    # Find class names used either as constructors or type annotations.
    # Examples:
    #   new LoginPage(page)
    #   let loginPage: LoginPage;
    #   private pageObj: LoginPage;
    used_classes = set(re.findall(r"new\s+(\w+Page)\s*\(", content))
    used_classes.update(re.findall(r":\s*(\w+Page)\b", content))
    if not used_classes:
        return content

    # Find which are already imported (support grouped named imports)
    already_imported: set[str] = set()
    for line in content.split("\n"):
        stripped = line.strip()
        # import { APage, BPage } from '...'
        m_named = re.match(r"import\s*\{([^}]+)\}\s*from\s*['\"][^'\"]+['\"]", stripped)
        if m_named:
            for name in [n.strip() for n in m_named.group(1).split(",") if n.strip()]:
                if name.endswith("Page"):
                    already_imported.add(name)
            continue

        # import APage from '...'
        m_default = re.match(r"import\s+(\w+Page)\s+from\s*['\"][^'\"]+['\"]", stripped)
        if m_default:
            already_imported.add(m_default.group(1))

    missing = used_classes - already_imported
    if not missing:
        return content

    # Try to find POM files in pages/ subdirectory
    spec_dir = spec_file.parent
    pages_dir = spec_dir / "pages"
    imports_to_add = []

    for cls in missing:
        resolved = False

        # 1) Try slug-based candidates first.
        slug = re.sub(r"Page$", "", cls)
        slug = re.sub(r"([A-Z])", r"-\1", slug).lower().strip("-")
        candidates = [
            pages_dir / f"{slug}.page.ts",
            spec_dir / f"{slug}.page.ts",
        ]
        for candidate in candidates:
            if candidate.exists():
                pom_content = candidate.read_text(encoding="utf-8")
                if f"class {cls}" in pom_content:
                    if candidate.parent == pages_dir:
                        rel_path = f"./pages/{candidate.stem}"
                    else:
                        rel_path = f"./{candidate.stem}"
                    imports_to_add.append(f"import {{ {cls} }} from '{rel_path}';")
                    resolved = True
                    break

        if resolved:
            continue

        # 2) Fallback: scan all POM files and resolve by exported class name.
        search_files = []
        if pages_dir.exists():
            search_files.extend(sorted(pages_dir.glob("*.page.ts")))
        search_files.extend(sorted(spec_dir.glob("*.page.ts")))

        for pom_file in search_files:
            try:
                pom_content = pom_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if re.search(rf"\b(?:export\s+)?class\s+{re.escape(cls)}\b", pom_content):
                if pom_file.parent == pages_dir:
                    rel_path = f"./pages/{pom_file.stem}"
                else:
                    rel_path = f"./{pom_file.stem}"
                imports_to_add.append(f"import {{ {cls} }} from '{rel_path}';")
                break

    if imports_to_add:
        # Insert after existing imports
        lines = content.split("\n")
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("import "):
                last_import_idx = i
        insert_point = last_import_idx + 1 if last_import_idx >= 0 else 0
        for imp in imports_to_add:
            lines.insert(insert_point, imp)
            insert_point += 1
        content = "\n".join(lines)

    return content


def _quick_fix(content: str) -> str:
    """Apply deterministic fixes that don't need an LLM."""
    # Strip markdown fences
    content = _strip_markdown_fences(content)

    # Remove lines that are just path comments like "// src/app/page.spec.ts"
    content = re.sub(r"^//\s*src/.*\n?", "", content, flags=re.MULTILINE)

    # Remove duplicate blank lines (more than 2 consecutive)
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Fix stray trailing dot after call expressions:
    #   expect.soft(x).toHaveProperty('y').  -> expect.soft(x).toHaveProperty('y');
    content = re.sub(r"\)\.\s*;", ");", content)
    content = re.sub(r"\)\.\s*$", ")", content, flags=re.MULTILINE)

    # Fix Playwright-specific import issues
    content = _fix_playwright_imports(content)
    content = _fix_missing_expect_import(content)

    # Fix untyped `page` parameters in POM files — add `: Page` type
    has_untyped_page = bool(re.search(r"\(page[,)]", content))
    has_typed_page = bool(re.search(r"\(page:\s*Page[,)]", content))
    if (has_untyped_page or has_typed_page) and "class " in content:
        # Check if Page type is already imported (not just part of a class name like LoginPage)
        has_page_import = bool(re.search(r"import\s*\{[^}]*\bPage\b", content))
        if not has_page_import:
            if "from '@playwright/test'" in content:
                # Add Page to existing import
                content = re.sub(
                    r"import\s*\{([^}]+)\}\s*from\s*'@playwright/test'",
                    lambda m: f"import {{ {m.group(1).strip()}, Page }} from '@playwright/test'",
                    content,
                    count=1,
                )
            else:
                content = "import { Page } from '@playwright/test';\n\n" + content
        # Type the page parameters (only in function/method declarations, not calls)
        content = re.sub(r"(async\s+\w+)\(page\)", r"\1(page: Page)", content)
        content = re.sub(r"(async\s+\w+)\(page,\s*", r"\1(page: Page, ", content)

    # Always fix accidental typing in constructor calls: new Foo(page: Page) -> new Foo(page)
    content = re.sub(r"new\s+(\w+)\(page:\s*Page\)", r"new \1(page)", content)

    # Fix POM classes that reference bare `page` without constructor injection.
    # If a class has methods using `page.` but no `this.page` or `page` param,
    # add `constructor(private page: Page) {}` and replace `page.` with `this.page.`
    if "class " in content:
        lines = content.split("\n")
        in_class = False
        class_indent = 0
        has_constructor = False
        class_uses_bare_page = False
        class_start_idx = -1

        for i, line in enumerate(lines):
            if re.match(r"^\s*(export\s+)?(default\s+)?class\s+\w+", line):
                in_class = True
                class_indent = len(line) - len(line.lstrip())
                has_constructor = False
                class_uses_bare_page = False
                class_start_idx = i
            elif in_class:
                stripped = line.strip()
                indent = len(line) - len(line.lstrip()) if stripped else 0
                if indent <= class_indent and stripped and not stripped.startswith("}"):
                    in_class = False
                elif "constructor" in line:
                    has_constructor = True
                elif re.search(r"\bpage\.", line) and "this.page" not in line:
                    class_uses_bare_page = True

        # If any class uses bare `page`, do the transformation
        if class_uses_bare_page:
            new_lines = []
            in_class = False
            class_indent = 0
            has_constructor = False
            class_body_start = -1

            for i, line in enumerate(lines):
                if re.match(r"^\s*(export\s+)?(default\s+)?class\s+\w+", line):
                    in_class = True
                    class_indent = len(line) - len(line.lstrip())
                    has_constructor = False
                    class_body_start = -1
                    new_lines.append(line)
                elif in_class:
                    stripped = line.strip()
                    indent = len(line) - len(line.lstrip()) if stripped else 0
                    if indent <= class_indent and stripped == "}":
                        in_class = False
                        new_lines.append(line)
                    elif "constructor" in line:
                        has_constructor = True
                        new_lines.append(line)
                    else:
                        # First real line after class opening brace — inject constructor if needed
                        if class_body_start == -1 and stripped and "{" not in lines[i - 1] if i > 0 else True:
                            class_body_start = i
                            if not has_constructor:
                                member_indent = " " * (class_indent + 4)
                                new_lines.append(f"{member_indent}constructor(private page: Page) {{}}")
                                new_lines.append("")
                                has_constructor = True
                        # Replace bare `page.` with `this.page.`
                        if re.search(r"\bpage\.", line) and "this.page" not in line:
                            line = re.sub(r"\bpage\.", "this.page.", line)
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            content = "\n".join(new_lines)
            # Ensure Page is imported
            if not re.search(r"import\s*\{[^}]*\bPage\b", content):
                if "from '@playwright/test'" in content:
                    content = re.sub(
                        r"import\s*\{([^}]+)\}\s*from\s*'@playwright/test'",
                        lambda m: f"import {{ {m.group(1).strip()}, Page }} from '@playwright/test'",
                        content,
                        count=1,
                    )
                else:
                    content = "import { Page } from '@playwright/test';\n\n" + content

    # Fix for...in loops indexing typed objects: add `as keyof typeof` cast
    # Pattern: `for (const X in OBJ)` followed by `OBJ[X]` → add cast
    for_in_match = re.findall(r"for\s*\(\s*const\s+(\w+)\s+in\s+(\w+)\s*\)", content)
    for var_name, obj_name in for_in_match:
        # Check if there's an indexing expression like OBJ[var] without a cast
        pattern = re.escape(obj_name) + r"\[" + re.escape(var_name) + r"\]"
        if re.search(pattern, content):
            # Add cast: `const role in CREDENTIALS` → `const role of Object.keys(CREDENTIALS) as (keyof typeof CREDENTIALS)[]`
            # Simpler fix: cast at usage site: CREDENTIALS[role] → CREDENTIALS[role as keyof typeof CREDENTIALS]
            old_idx = f"{obj_name}[{var_name}]"
            new_idx = f"{obj_name}[{var_name} as keyof typeof {obj_name}]"
            content = content.replace(old_idx, new_idx)

    # Fix spec files that reference bare `page` in tests without the fixture
    # test('...', async () => { ... page.click ... }) → test('...', async ({ page }) => { ...
    if "test(" in content and "class " not in content:
        # Fix: `new XxxPage()` → `new XxxPage(page)` for POM instantiation
        content = re.sub(r"new\s+(\w*Page)\(\)", r"new \1(page)", content)

        # Fix: test callbacks that use `page` but don't have it as fixture param
        lines = content.split("\n")
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Match test/beforeAll/beforeEach callbacks without `page` fixture
            m = re.match(r"^(\s*)(test(?:\.beforeAll|\.beforeEach|\.afterAll|\.afterEach)?)\s*\((.*?)async\s*\((\{[^}]*\})?\)\s*=>\s*\{", line)
            if m:
                indent, keyword, middle, existing_fixtures = m.groups()
                # Check if subsequent lines (until closing) use `page.`
                uses_page = False
                for j in range(i + 1, min(i + 30, len(lines))):
                    if re.search(r"\bpage\.", lines[j]):
                        uses_page = True
                        break
                    if lines[j].strip() in ("});", "}"):
                        break
                if uses_page:
                    if existing_fixtures:
                        # Has fixtures like { request } → add page: { page, request }
                        fixtures_inner = existing_fixtures.strip("{} ")
                        if "page" not in fixtures_inner:
                            new_fixtures = f"{{ page, {fixtures_inner} }}"
                            line = f"{indent}{keyword}({middle}async ({new_fixtures}) => {{"
                    else:
                        # No fixtures → add { page }
                        line = f"{indent}{keyword}({middle}async ({{ page }}) => {{"
            # Also match simple test callbacks: test('title', async () => {
            elif re.match(r"^(\s*)test\s*\(['\"].*?['\"]\s*,\s*async\s*\(\)\s*=>\s*\{", line):
                indent_m = re.match(r"^(\s*)", line)
                indent = indent_m.group(1) if indent_m else ""
                uses_page = False
                for j in range(i + 1, min(i + 30, len(lines))):
                    if re.search(r"\bpage\.", lines[j]):
                        uses_page = True
                        break
                    if lines[j].strip() in ("});", "}"):
                        break
                if uses_page:
                    line = re.sub(r"async\s*\(\)\s*=>", "async ({ page }) =>", line)
            fixed_lines.append(line)
            i += 1
        content = "\n".join(fixed_lines)

        # Fix protected POM page access in specs: dashboardPage.page.title() -> page.title()
        # This avoids TypeScript errors when POM defines `protected page`.
        content = re.sub(r"\b\w+Page\.page\.title\(\)", "page.title()", content)

        # Fix non-existent Playwright helper on Page instances.
        # page.waitForNetworkIdle() -> page.waitForLoadState('networkidle')
        content = re.sub(
            r"\bpage\.waitForNetworkIdle\(\)",
            "page.waitForLoadState('networkidle')",
            content,
        )

        # Fix common untyped login helper signature in generated specs.
        # const login = async (page, { username, password }) => { ... }
        content = re.sub(
            r"const\s+login\s*=\s*async\s*\(\s*page\s*,\s*\{\s*username\s*,\s*password\s*\}\s*\)\s*=>",
            "const login = async (page: Page, { username, password }: { username: string; password: string }) =>",
            content,
        )

        # If Page type annotations were introduced, ensure Page is imported.
        if ": Page" in content and not re.search(r"import\s*\{[^}]*\bPage\b", content):
            m = re.search(r"import\s*\{([^}]+)\}\s*from\s*['\"]@playwright/test['\"]", content)
            if m:
                names = [n.strip() for n in m.group(1).split(",") if n.strip()]
                if "Page" not in names:
                    names.append("Page")
                new_import = f"import {{ {', '.join(sorted(set(names)))} }} from '@playwright/test';"
                content = content[:m.start()] + new_import + content[m.end():]
            else:
                content = "import { Page, expect, test } from '@playwright/test';\n\n" + content

        # Fix duplicate identifier pattern in beforeAll/beforeEach:
        #   async ({ page, browser }) => { const context = ...; const page = await context.newPage(); }
        # Keep local page variable and remove page fixture from params.
        content = re.sub(
            r"(test\.(?:beforeAll|beforeEach)\(async\s*\(\{)\s*page\s*,\s*browser\s*(\}\)\s*=>\s*\{)",
            r"\1 browser\2",
            content,
        )
        content = re.sub(
            r"(test\.(?:beforeAll|beforeEach)\(async\s*\(\{)\s*browser\s*,\s*page\s*(\}\)\s*=>\s*\{)",
            r"\1 browser\2",
            content,
        )

    # Deduplicate imports and remove phantom local imports
    content = _deduplicate_imports(content)
    content = _remove_phantom_imports(content)

    # ── Brace-closure fixer ──
    # Fix `}` ↔ `});` using bracket counting.
    # Rules:
    #   - Callbacks opened by test(), test.describe(), test.beforeAll(), etc. → close with `});`
    #   - Class method bodies and standalone functions → close with `}`
    #   - Class body itself → close with `}`
    lines = content.split("\n")
    callback_pattern = re.compile(
        r"^\s*(test\.describe|test\.beforeAll|test\.beforeEach|test\.afterAll|test\.afterEach|test)\s*\("
    )
    class_pattern = re.compile(r"^\s*(export\s+)?class\s+\w+")
    func_def_pattern = re.compile(r"^(\s*)(export\s+)?(async\s+)?function\s+\w+")

    # Pass 1: Ensure test callbacks close with `});`
    # Use bracket-counting to find the matching `}` for each callback opener
    fixed_lines = list(lines)
    i = 0
    while i < len(fixed_lines):
        line = fixed_lines[i]
        if callback_pattern.match(line):
            # Count braces from this line to find the closing
            brace_count = 0
            started = False
            for j in range(i, len(fixed_lines)):
                for ch in fixed_lines[j]:
                    if ch == '{':
                        brace_count += 1
                        started = True
                    elif ch == '}':
                        brace_count -= 1
                if started and brace_count == 0:
                    # Line j has the closing brace
                    closing = fixed_lines[j].rstrip()
                    if closing.strip() == "}":
                        indent = len(closing) - len(closing.lstrip())
                        fixed_lines[j] = " " * indent + "});"
                    break
        i += 1
    content = "\n".join(fixed_lines)
    lines = content.split("\n")

    # Pass 2: In pure POM/class files (no test callbacks), convert stray `});` to `}`
    has_class = bool(class_pattern.search(content))
    has_callbacks = bool(callback_pattern.search(content))
    if has_class and not has_callbacks:
        fixed_lines = []
        for line in lines:
            if line.strip() == "});":
                indent = len(line) - len(line.lstrip())
                line = " " * indent + "}"
            fixed_lines.append(line)
        content = "\n".join(fixed_lines)
        lines = content.split("\n")

    # Pass 3: Standalone function definitions should close with `}` not `});`
    in_function = False
    func_indent = 0
    brace_count = 0
    fixed_lines = []
    for line in lines:
        stripped = line.rstrip()
        indent = len(line) - len(line.lstrip()) if line.strip() else 0
        if not in_function and func_def_pattern.match(line):
            in_function = True
            func_indent = indent
            brace_count = 0
            for ch in line:
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
            if brace_count == 0:
                in_function = False  # Single-line function
        elif in_function:
            for ch in line:
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
            if brace_count == 0:
                # This line closes the function
                if stripped.strip() == "});":
                    line = " " * func_indent + "}"
                in_function = False
        fixed_lines.append(line)
    content = "\n".join(fixed_lines)

    # Final cleanup of multiple blank lines that may have been introduced
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Remove trailing non-code text after the last top-level `});`
    # LLMs sometimes append explanatory paragraphs after the code
    lines = content.strip().split("\n")
    last_close_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "});":
            last_close_idx = i
    if last_close_idx >= 0 and last_close_idx < len(lines) - 1:
        # Check if remaining lines after last }); are non-code (no braces, no semicolons, no imports)
        trailing = "\n".join(lines[last_close_idx + 1:])
        if not re.search(r"[{};]|import\s|export\s|const\s|let\s|var\s|function\s|class\s|test\(|describe\(", trailing):
            lines = lines[:last_close_idx + 1]
            content = "\n".join(lines)

    return content.strip() + "\n"


@CrewBase
class CodeCleanerCrew:
    """Crew that cleans generated test files."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def code_cleaner(self) -> Agent:
        return Agent(
            config=self.agents_config["code_cleaner"],
            tools=[],
            llm=get_llm(),
            verbose=True,
        )

    @task
    def clean_code(self) -> Task:
        return Task(config=self.tasks_config["clean_code"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def _collect_spec_files(output_dir: str) -> list[Path]:
    """Find all TypeScript test and page object files in the output directory."""
    test_dir = Path(output_dir) / "tests"
    if not test_dir.exists():
        return []
    # Collect .spec.ts, .page.ts, .pom.ts and any other .ts files in tests/
    return list(test_dir.rglob("*.ts"))


def _run_npm_install(output_dir: str) -> bool:
    """Run npm install in the output directory. Returns True if successful."""
    pkg_json = Path(output_dir) / "package.json"
    if not pkg_json.exists():
        logger.warning("No package.json found — skipping npm install")
        return False

    # Ensure @types/node is in devDependencies
    import json
    pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
    dev_deps = pkg.setdefault("devDependencies", {})
    if "@types/node" not in dev_deps:
        dev_deps["@types/node"] = "^22.0.0"
        pkg_json.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
        logger.info("  Added @types/node to package.json")

    # Ensure tsconfig.json has "types": ["node"] so process.env resolves
    tsconfig_path = Path(output_dir) / "tsconfig.json"
    if tsconfig_path.exists():
        ts_cfg = json.loads(tsconfig_path.read_text(encoding="utf-8"))
        compiler_opts = ts_cfg.setdefault("compilerOptions", {})
        types_list = compiler_opts.setdefault("types", [])
        if "node" not in types_list:
            types_list.append("node")
            tsconfig_path.write_text(json.dumps(ts_cfg, indent=2) + "\n", encoding="utf-8")
            logger.info("  Added 'node' to tsconfig types")

    node_modules = Path(output_dir) / "node_modules"
    if node_modules.exists() and (node_modules / "@types" / "node").exists():
        logger.info("  node_modules already present with @types/node — skipping install")
        return True

    logger.info("  Running npm install...")
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )
        if result.returncode == 0:
            logger.info("  npm install complete")
            return True
        else:
            logger.warning(f"  npm install failed: {result.stderr[:200]}")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"  npm install error: {e}")
        return False


def _run_tsc_check(output_dir: str) -> dict[str, list[str]]:
    """Run tsc --noEmit and return errors grouped by file path."""
    errors: dict[str, list[str]] = {}
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit", "--pretty", "false"],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
        )
        # Parse tsc output: file(line,col): error TS1234: message
        for line in result.stdout.split("\n"):
            match = re.match(r"(.+?)\((\d+),(\d+)\):\s*error\s+TS\d+:\s*(.+)", line)
            if match:
                file_path = match.group(1).strip()
                error_msg = match.group(4).strip()
                errors.setdefault(file_path, []).append(error_msg)

        if errors:
            total = sum(len(v) for v in errors.values())
            logger.info(f"  TypeScript found {total} error(s) in {len(errors)} file(s)")
        else:
            logger.info("  TypeScript: no errors")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"  tsc check error: {e}")

    return errors


def run_code_cleaner(state: TestForgeState) -> None:
    """Clean all generated spec files — npm install, deterministic fixes, tsc check, then LLM for remaining issues."""
    spec_files = _collect_spec_files(state.output_dir)
    if not spec_files:
        logger.info("No spec files found to clean")
        return

    logger.info(f"Code Cleaner: processing {len(spec_files)} spec files")

    # Step 0: Install dependencies so tsc can run
    _run_npm_install(state.output_dir)

    # Pass 1: Deterministic fixes (no tokens spent)
    for spec_file in spec_files:
        original = spec_file.read_text(encoding="utf-8")
        cleaned = _quick_fix(original)
        cleaned = _ensure_exported_pom_classes(cleaned, spec_file)
        cleaned = _fix_auth_password_placeholders(cleaned, state.credentials)
        cleaned = _enforce_login_payload_contract(cleaned, state.credentials)
        cleaned = _relax_invalid_login_status_assertions(cleaned)

        # Remove imports from relative paths where the file doesn't exist
        cleaned = _remove_missing_file_imports(cleaned, spec_file)

        if cleaned != original:
            spec_file.write_text(cleaned, encoding="utf-8")
            logger.info(f"  Quick-fixed: {spec_file.name}")

    # Pass 1b: Auto-add POM imports (runs after all files are fixed so POM files exist)
    for spec_file in spec_files:
        original = spec_file.read_text(encoding="utf-8")
        cleaned = _add_pom_imports(original, spec_file)
        if cleaned != original:
            spec_file.write_text(cleaned, encoding="utf-8")
            logger.info(f"  Added POM imports: {spec_file.name}")

    # Step 2: Run tsc to find remaining errors
    tsc_errors = _run_tsc_check(state.output_dir)

    # Determine which files need LLM help
    files_needing_llm = []
    for spec_file in spec_files:
        content = spec_file.read_text(encoding="utf-8")
        # Check heuristic issues
        needs_fix = _needs_llm_fix(content)
        # Check tsc errors for this file
        rel_path = str(spec_file.relative_to(state.output_dir))
        has_tsc_errors = any(rel_path.replace("\\", "/") in k.replace("\\", "/") for k in tsc_errors)
        if needs_fix or has_tsc_errors:
            files_needing_llm.append(spec_file)

    # Pass 3: LLM-based fixes for files with structural issues
    if not files_needing_llm:
        logger.info("All files clean after deterministic pass")
        return

    # Demo mode: limit LLM calls
    if state.demo:
        files_needing_llm = files_needing_llm[:3]
        logger.info(f"DEMO MODE: limiting LLM cleaning to {len(files_needing_llm)} files")

    for spec_file in files_needing_llm:
        content = spec_file.read_text(encoding="utf-8")
        rel_path = str(spec_file.relative_to(state.output_dir))
        logger.info(f"  LLM cleaning: {spec_file.name}")

        # Gather tsc errors for this file to include in prompt
        file_errors = []
        for k, v in tsc_errors.items():
            if rel_path.replace("\\", "/") in k.replace("\\", "/"):
                file_errors.extend(v)
        error_context = ""
        if file_errors:
            error_context = "\n\nTYPESCRIPT COMPILER ERRORS:\n" + "\n".join(f"- {e}" for e in file_errors[:10])

        try:
            crew = CodeCleanerCrew()
            result = crew.crew().kickoff(
                inputs={
                    "file_path": str(spec_file),
                    "file_content": content[:4000] + error_context,
                }
            )

            cleaned_output = _strip_markdown_fences(str(result))

            # Sanity check: only write if result looks like TypeScript
            # and doesn't introduce local imports to non-existent files
            has_bad_imports = bool(re.search(
                r"import\s*\{[^}]+\}\s*from\s*['\"]\.\.?/(?!@)",
                cleaned_output
            ))
            looks_like_ts = ("import" in cleaned_output or "export" in cleaned_output or "test" in cleaned_output)

            if looks_like_ts and not has_bad_imports:
                # Run quick_fix on the LLM output to clean any remaining issues
                cleaned_output = _quick_fix(cleaned_output)
                cleaned_output = _ensure_exported_pom_classes(cleaned_output, spec_file)
                cleaned_output = _fix_auth_password_placeholders(cleaned_output, state.credentials)
                cleaned_output = _enforce_login_payload_contract(cleaned_output, state.credentials)
                cleaned_output = _relax_invalid_login_status_assertions(cleaned_output)
                spec_file.write_text(cleaned_output, encoding="utf-8")
                logger.info(f"  LLM-cleaned: {spec_file.name}")
            else:
                reason = "hallucinated local imports" if has_bad_imports else "not TypeScript"
                logger.warning(f"  LLM output rejected ({reason}), keeping original: {spec_file.name}")
        except Exception as e:
            logger.warning(f"  Failed to LLM-clean {spec_file.name}: {e}")


def _needs_llm_fix(content: str) -> bool:
    """Heuristic: does this file have issues beyond what quick_fix handles?"""
    issues = []

    # Check for remaining markdown fences
    if "```" in content:
        issues.append("markdown_fences")

    # Check for duplicate imports of same symbol
    import_lines = [l for l in content.split("\n") if l.strip().startswith("import")]
    imported_symbols = []
    for line in import_lines:
        symbols = re.findall(r"\b(\w+)\b", line.split("from")[0] if "from" in line else "")
        imported_symbols.extend(symbols)
    if len(imported_symbols) != len(set(imported_symbols)):
        issues.append("duplicate_imports")

    # Check for unbalanced braces
    if content.count("{") != content.count("}"):
        issues.append("unbalanced_braces")

    # Check for standalone `request.` usage outside test fixture context
    # (request used as a global variable instead of fixture parameter)
    if re.search(r"(?:^|\n)(?:async )?function\s+\w+.*\{[^}]*\brequest\.", content, re.DOTALL):
        issues.append("request_outside_fixture")

    # Check for parameters with implicit 'any' type (page without type annotation)
    if re.search(r"\(\s*page\s*[,)]", content) and "Page" not in content:
        issues.append("implicit_any_param")

    # Check for non-existent POM class instantiation outside describe
    if re.search(r"^const \w+ = new \w+\(\);", content, re.MULTILINE):
        class_usages = re.findall(r"new (\w+)\(\)", content)
        class_defs = re.findall(r"class (\w+)", content)
        for cls in class_usages:
            if cls not in class_defs and "Page" not in content.split("class"):
                issues.append("phantom_class")
                break

    return len(issues) > 0
