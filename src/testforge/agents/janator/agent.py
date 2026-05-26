"""Janator agent - project boilerplate and dependency setup."""

import json
import logging
import subprocess
from pathlib import Path

from testforge.state import TestForgeState

logger = logging.getLogger("testforge")


def _missing_markers(output_dir: Path) -> list[str]:
    """Return scaffold markers that are currently missing."""
    markers = ["playwright.config.ts", "package.json", "tsconfig.json"]
    return [m for m in markers if not (output_dir / m).exists()]


def _ensure_package_json(output_dir: Path) -> None:
    """Ensure package.json contains required scripts and dev dependencies."""
    pkg_path = output_dir / "package.json"
    if not pkg_path.exists():
        return

    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))

    scripts = pkg.setdefault("scripts", {})
    scripts.setdefault("test", "npx playwright test")
    scripts.setdefault("test:ui", "npx playwright test --ui")
    scripts.setdefault("report", "npx playwright show-report")

    dev_deps = pkg.setdefault("devDependencies", {})
    dev_deps.setdefault("@playwright/test", "^1.50.0")
    dev_deps.setdefault("typescript", "^5.7.0")
    dev_deps.setdefault("@types/node", "^22.0.0")

    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")


def _ensure_tsconfig(output_dir: Path) -> None:
    """Ensure tsconfig has node types so process/env references compile."""
    tsconfig_path = output_dir / "tsconfig.json"
    if not tsconfig_path.exists():
        return

    cfg = json.loads(tsconfig_path.read_text(encoding="utf-8"))
    compiler_options = cfg.setdefault("compilerOptions", {})
    types = compiler_options.setdefault("types", [])
    if "node" not in types:
        types.append("node")

    # Keep strict mode on for deterministic compile quality.
    compiler_options.setdefault("strict", True)

    tsconfig_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def _run_npm_install(output_dir: Path) -> None:
    """Install/refresh Node dependencies for generated test project."""
    if not (output_dir / "package.json").exists():
        logger.warning("Janator: package.json missing, skipping npm install")
        return

    logger.info("Janator: running npm install...")
    result = subprocess.run(
        "npm install --no-audit --no-fund",
        cwd=str(output_dir),
        capture_output=True,
        text=True,
        timeout=180,
        shell=True,
    )
    if result.returncode != 0:
        logger.warning(f"Janator: npm install failed: {result.stderr[:300]}")
    else:
        logger.info("Janator: npm install complete")


def run_janator(state: TestForgeState) -> None:
    """Prepare generated test project boilerplate after writers complete."""
    output_dir = Path(state.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = _missing_markers(output_dir)
    if missing:
        logger.info(f"Janator: missing scaffold files {missing} - scaffolding")
        from testforge.agents.scaffold import scaffold_output

        scaffold_output(state)

    _ensure_package_json(output_dir)
    _ensure_tsconfig(output_dir)
    _run_npm_install(output_dir)
