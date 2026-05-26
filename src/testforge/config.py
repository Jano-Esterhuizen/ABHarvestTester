"""TestForge configuration and validation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TestForgeConfig:
    """Immutable configuration loaded from CLI args + environment."""

    repo_path: str
    app_url: str
    credentials: dict
    output_dir: str
    force: bool = False
    demo: bool = False
    mcp_config_path: Optional[str] = None
    mcp_server_config: Optional[dict] = None
    github_token: str = ""


def validate_config(config: TestForgeConfig) -> list[str]:
    """Validate config and return list of errors (empty = valid)."""
    errors = []

    # Repo must exist
    if not Path(config.repo_path).is_dir():
        errors.append(f"Repository path does not exist: {config.repo_path}")

    # URL must be non-empty
    if not config.app_url:
        errors.append("App URL is required")

    # Credentials must have roles
    if "roles" not in config.credentials or not config.credentials["roles"]:
        errors.append("Credentials file must contain at least one role")

    # Each role must have required fields
    for i, role in enumerate(config.credentials.get("roles", [])):
        for field_name in ("name", "username", "password"):
            if field_name not in role:
                errors.append(f"Role {i} missing required field: {field_name}")

    # Login config must exist
    if "login" not in config.credentials:
        errors.append("Credentials file must contain a 'login' section")

    return errors
