"""Scraper — pure Python API specification extractor (no LLM needed).

Reads route files from the target repo and produces a canonical API spec
document that downstream agents use for test generation.
"""

import json
import logging
import re
from pathlib import Path

from testforge.state import TestForgeState

logger = logging.getLogger("testforge")


def run_scraper(state: TestForgeState) -> None:
    """Extract API specification from route files using Python (no LLM)."""
    repo = Path(state.repo_path)

    # Find app root
    app_root = _find_app_root(repo)

    # Find all route files
    api_dir = app_root / "src" / "app" / "api"
    if not api_dir.exists():
        api_dir = app_root / "app" / "api"

    if not api_dir.exists():
        state.api_spec = "No API routes found in repository."
        state.api_spec_source = "code_extraction"
        return

    state.api_spec_source = "code_extraction"

    # Build API spec from route files
    spec_parts = ["# API Specification\n"]
    spec_parts.append(f"Base URL: {state.app_url}\n")

    routes = []
    for route_file in sorted(api_dir.rglob("route.*")):
        route_info = _analyze_route_file(route_file, api_dir, app_root)
        if route_info:
            routes.extend(route_info)

    # Group by resource
    resources = {}
    for r in routes:
        # Extract resource name from path (first segment after /api/v1/ or /api/)
        parts = r["path"].split("/")
        resource = parts[3] if len(parts) > 3 and parts[2] == "v1" else parts[2] if len(parts) > 2 else "root"
        resources.setdefault(resource, []).append(r)

    for resource, endpoints in resources.items():
        spec_parts.append(f"\n## {resource.title()}\n")
        for ep in endpoints:
            spec_parts.append(f"### {ep['method']} {ep['path']}")
            if ep.get("auth_required"):
                spec_parts.append(f"- Auth: Required")
            if ep.get("roles"):
                spec_parts.append(f"- Roles: {', '.join(ep['roles'])}")
            if ep.get("params"):
                spec_parts.append(f"- Params: {', '.join(ep['params'])}")
            if ep.get("body_fields"):
                spec_parts.append(f"- Body: {', '.join(ep['body_fields'])}")
            spec_parts.append("")

    state.api_spec = "\n".join(spec_parts)
    logger.info(f"API spec extracted: {len(routes)} endpoints across {len(resources)} resources")


def _find_app_root(repo: Path) -> Path:
    """Find the actual application root."""
    if (repo / "package.json").exists():
        return repo
    for child in repo.iterdir():
        if child.is_dir() and child.name not in {"node_modules", ".git", ".next", "dist"}:
            if (child / "package.json").exists():
                return child
    return repo


def _analyze_route_file(route_file: Path, api_dir: Path, app_root: Path) -> list[dict]:
    """Analyze a single route file and extract endpoint info."""
    try:
        content = route_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    # Compute API path from file location
    rel = route_file.relative_to(api_dir)
    path_parts = list(rel.parent.parts)
    api_path = "/api/" + "/".join(
        f":{p[1:-1]}" if p.startswith("[") and p.endswith("]") else p
        for p in path_parts
        if p != "."
    )

    # Detect exported HTTP methods
    endpoints = []
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        if f"export async function {method}" in content or f"export function {method}" in content:
            ep = {
                "method": method,
                "path": api_path,
                "file": str(route_file.relative_to(app_root)),
                "auth_required": _check_auth(content),
                "roles": _extract_roles(content),
                "params": _extract_params(api_path),
                "body_fields": _extract_body_fields(content, method),
            }
            endpoints.append(ep)

    return endpoints


def _check_auth(content: str) -> bool:
    """Check if route requires authentication."""
    auth_patterns = [
        "getServerSession", "getSession", "auth()", "requireAuth",
        "verifyToken", "session", "currentUser", "getUser",
    ]
    return any(p in content for p in auth_patterns)


def _extract_roles(content: str) -> list[str]:
    """Extract role references from route file."""
    roles = set()
    role_patterns = [
        r'role\s*[=!]==?\s*["\'](\w+)["\']',
        r'hasRole\(["\'](\w+)["\']',
        r'requiredRole.*?["\'](\w+)["\']',
        r'UserRole\.(\w+)',
    ]
    for pattern in role_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            roles.add(match.group(1).lower())
    return sorted(roles)


def _extract_params(api_path: str) -> list[str]:
    """Extract path parameters."""
    return [p[1:] for p in api_path.split("/") if p.startswith(":")]


def _extract_body_fields(content: str, method: str) -> list[str]:
    """Extract likely request body fields for POST/PUT/PATCH."""
    if method == "GET" or method == "DELETE":
        return []
    fields = set()
    # Look for destructured body fields
    body_pattern = r'(?:body|data|json)\s*[=:]\s*(?:await\s+)?(?:req|request)\.(?:json|body)\(\)'
    if re.search(body_pattern, content):
        # Find destructured fields
        destruct = re.findall(r'const\s*\{([^}]+)\}\s*=\s*(?:body|data|json|await)', content)
        for d in destruct:
            for field in d.split(","):
                f = field.strip().split(":")[0].strip()
                if f and not f.startswith("//"):
                    fields.add(f)
    return sorted(fields)[:10]  # Cap at 10 fields
