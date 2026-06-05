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
    skip_fe: bool = False
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

    # Validate credentials only when provided.
    if config.credentials:
        roles = config.credentials.get("roles", [])

        # If roles are provided, each role only needs username/password.
        if roles:
            for i, role in enumerate(roles):
                for field_name in ("username", "password"):
                    if field_name not in role:
                        errors.append(f"Role {i} missing required field: {field_name}")
        else:
            # No roles provided: allow top-level credentials shape.
            has_top_level = (
                "username" in config.credentials and "password" in config.credentials
            )
            has_test_user = (
                isinstance(config.credentials.get("testUser"), dict)
                and "username" in config.credentials["testUser"]
                and "password" in config.credentials["testUser"]
            )
            if not has_top_level and not has_test_user:
                errors.append(
                    "Credentials must include either roles[].username/password, top-level username/password, or testUser.username/password"
                )

    return errors
