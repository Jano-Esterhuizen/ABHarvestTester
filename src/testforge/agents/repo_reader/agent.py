"""Repo Reader — pure Python repository analyzer (no LLM needed).

Reads target repo files and produces a structured context document
within budget for downstream LLM agents.
"""

import json
import logging
from pathlib import Path

from testforge.state import TestForgeState

logger = logging.getLogger("testforge")

# Directories to skip
SKIP_DIRS = {
    "node_modules", ".git", ".next", "dist", "build", ".venv",
    "venv", "coverage", ".nyc_output", "__pycache__", ".cache",
}

# Key files to read for context
MARKER_FILES = ["package.json", "pyproject.toml", "Gemfile", "go.mod", "Cargo.toml"]
SCHEMA_PATTERNS = ["prisma/schema.prisma", "schema.prisma", "models.py", "schema.graphql"]
AUTH_PATTERNS = ["middleware.ts", "middleware.js", "lib/auth.ts", "lib/auth.js", "auth.ts"]


def run_repo_reader(state: TestForgeState) -> None:
    """Analyze the target repository using Python (no LLM) and produce context document."""
    repo = Path(state.repo_path)
    if not repo.exists():
        state.context_document = f"ERROR: Repo path not found: {state.repo_path}"
        return

    # Find the actual app directory (might be nested)
    app_root = _find_app_root(repo)
    logger.info(f"App root detected: {app_root}")

    context_parts = []

    # 1. Tech Stack
    tech = _detect_tech_stack(app_root)
    context_parts.append(f"## Tech Stack\n{_format_dict(tech)}")

    # 2. API Routes (from directory structure)
    api_routes = _extract_api_routes(app_root)
    if api_routes:
        routes_table = "| Method | Path | File |\n|--------|------|------|\n"
        for r in api_routes[:50]:  # Cap at 50
            routes_table += f"| {r['methods']} | {r['path']} | {r['file']} |\n"
        context_parts.append(f"## API Routes ({len(api_routes)} total)\n{routes_table}")

    # 3. UI Routes (from page files)
    ui_routes = _extract_ui_routes(app_root)
    if ui_routes:
        ui_table = "| Path | File |\n|------|------|\n"
        for r in ui_routes[:30]:
            ui_table += f"| {r['path']} | {r['file']} |\n"
        context_parts.append(f"## UI Routes ({len(ui_routes)} total)\n{ui_table}")

    # 4. Data Models (from Prisma/etc)
    models = _extract_models(app_root)
    if models:
        context_parts.append(f"## Data Models\n{models}")

    # 5. Auth & Middleware
    auth_info = _extract_auth_info(app_root)
    if auth_info:
        context_parts.append(f"## Authentication & Authorization\n{auth_info}")

    # 6. Roles from credentials
    roles = state.credentials.get("roles", [])
    if roles:
        roles_text = "\n".join(f"- **{r['name']}**: {r.get('description', 'No description')}" for r in roles)
        context_parts.append(f"## User Roles\n{roles_text}")

    state.context_document = f"# Target Application Context\n\n" + "\n\n".join(context_parts)
    logger.info(f"Context document: {len(state.context_document)} chars")


def _find_app_root(repo: Path) -> Path:
    """Find the actual application root (handles monorepos)."""
    # Direct markers
    if (repo / "package.json").exists():
        return repo
    # Check one level deep for app directories
    for child in repo.iterdir():
        if child.is_dir() and child.name not in SKIP_DIRS:
            if (child / "package.json").exists():
                return child
    return repo


def _detect_tech_stack(root: Path) -> dict:
    """Detect tech stack from marker files."""
    tech = {}
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            tech["runtime"] = "Node.js"
            if "next" in deps:
                tech["framework"] = f"Next.js {deps['next']}"
            elif "react" in deps:
                tech["framework"] = "React"
            if "@prisma/client" in deps:
                tech["orm"] = "Prisma"
            if "drizzle-orm" in deps:
                tech["orm"] = "Drizzle"
            if "next-auth" in deps or "@auth/core" in deps:
                tech["auth"] = "NextAuth.js"
            if "@playwright/test" in deps:
                tech["testing"] = "Playwright"
            tech["language"] = "TypeScript" if (root / "tsconfig.json").exists() else "JavaScript"
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return tech


def _extract_api_routes(root: Path) -> list[dict]:
    """Extract API routes from Next.js app router or pages/api structure."""
    routes = []

    # Next.js App Router: app/api/**/route.ts
    api_dir = root / "src" / "app" / "api"
    if not api_dir.exists():
        api_dir = root / "app" / "api"
    if api_dir.exists():
        for route_file in api_dir.rglob("route.*"):
            rel = route_file.relative_to(api_dir)
            path_parts = list(rel.parent.parts)
            api_path = "/api/" + "/".join(
                f":{p[1:-1]}" if p.startswith("[") and p.endswith("]") else p
                for p in path_parts
                if p != "."
            )
            # Detect HTTP methods from file content
            methods = _detect_http_methods(route_file)
            routes.append({
                "path": api_path,
                "methods": methods,
                "file": str(route_file.relative_to(root)),
            })

    # Pages Router: pages/api/**/*.ts
    pages_api = root / "pages" / "api"
    if pages_api.exists():
        for f in pages_api.rglob("*.ts"):
            rel = f.relative_to(pages_api)
            api_path = "/api/" + str(rel.with_suffix("")).replace("\\", "/")
            routes.append({"path": api_path, "methods": "GET,POST", "file": str(f.relative_to(root))})

    return sorted(routes, key=lambda r: r["path"])


def _detect_http_methods(route_file: Path) -> str:
    """Read a route file and detect exported HTTP methods."""
    try:
        content = route_file.read_text(encoding="utf-8")
        methods = []
        for m in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            if f"export async function {m}" in content or f"export function {m}" in content:
                methods.append(m)
        return ",".join(methods) if methods else "GET"
    except (UnicodeDecodeError, OSError):
        return "GET"


def _extract_ui_routes(root: Path) -> list[dict]:
    """Extract UI page routes from Next.js app router."""
    routes = []
    app_dir = root / "src" / "app"
    if not app_dir.exists():
        app_dir = root / "app"
    if not app_dir.exists():
        return routes

    for page_file in app_dir.rglob("page.*"):
        rel = page_file.relative_to(app_dir)
        path_parts = list(rel.parent.parts)
        # Skip api routes
        if "api" in path_parts:
            continue
        # Convert route groups (name) → empty, [param] → :param
        ui_path = "/" + "/".join(
            f":{p[1:-1]}" if p.startswith("[") and p.endswith("]")
            else "" if p.startswith("(") and p.endswith(")")
            else p
            for p in path_parts
            if p != "."
        ).strip("/").replace("//", "/")
        if not ui_path or ui_path == "/":
            ui_path = "/"
        routes.append({"path": ui_path, "file": str(page_file.relative_to(root))})

    return sorted(routes, key=lambda r: r["path"])


def _extract_models(root: Path) -> str:
    """Extract data model definitions (Prisma schema, etc.)."""
    schema_file = root / "prisma" / "schema.prisma"
    if not schema_file.exists():
        # Try nested
        for f in root.rglob("schema.prisma"):
            schema_file = f
            break
    if not schema_file.exists():
        return ""

    try:
        content = schema_file.read_text(encoding="utf-8")
        # Extract model definitions only (skip datasource/generator blocks)
        models = []
        current_model = []
        in_model = False
        for line in content.split("\n"):
            if line.strip().startswith("model "):
                in_model = True
                current_model = [line.strip()]
            elif in_model:
                current_model.append(line.rstrip())
                if line.strip() == "}":
                    in_model = False
                    models.append("\n".join(current_model))

        # Truncate if too many models
        if len(models) > 15:
            result = "\n\n".join(models[:15])
            result += f"\n\n... and {len(models) - 15} more models"
            return f"```prisma\n{result}\n```"
        return f"```prisma\n{'\\n\\n'.join(models)}\n```" if models else ""
    except (UnicodeDecodeError, OSError):
        return ""


def _extract_auth_info(root: Path) -> str:
    """Extract auth/middleware information."""
    info_parts = []

    # Read middleware
    for name in ["middleware.ts", "middleware.js"]:
        mw = root / "src" / name
        if not mw.exists():
            mw = root / name
        if mw.exists():
            try:
                content = mw.read_text(encoding="utf-8")
                # Extract key patterns: matchers, protected routes
                lines = content.split("\n")
                relevant = [l for l in lines if any(kw in l.lower() for kw in
                    ["matcher", "protect", "auth", "redirect", "session", "token", "role"])]
                if relevant:
                    info_parts.append(f"**Middleware** ({name}):\n```\n" + "\n".join(relevant[:20]) + "\n```")
            except (UnicodeDecodeError, OSError):
                pass

    # Read auth lib
    for pattern in ["lib/auth.ts", "lib/auth.js", "auth.ts"]:
        auth_file = root / "src" / pattern
        if not auth_file.exists():
            auth_file = root / pattern
        if auth_file.exists():
            try:
                content = auth_file.read_text(encoding="utf-8")[:3000]
                info_parts.append(f"**Auth module** ({pattern}):\n```typescript\n{content[:1500]}\n```")
            except (UnicodeDecodeError, OSError):
                pass
            break

    return "\n\n".join(info_parts) if info_parts else "Not detected"


def _format_dict(d: dict) -> str:
    """Format a dict as markdown bullet points."""
    return "\n".join(f"- **{k}**: {v}" for k, v in d.items())

