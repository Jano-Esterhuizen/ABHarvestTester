"""File system tools for reading target repos and writing test output."""

import os
from pathlib import Path
from crewai.tools import tool

# Module-level repo path — set by the flow before agents run
_repo_path: str = ""
_output_dir: str = ""


def set_repo_path(repo_path: str):
    """Set the target repo path for file tools to resolve relative paths."""
    global _repo_path
    _repo_path = repo_path


def set_output_dir(output_dir: str):
    """Set the test output directory for file tools to resolve relative paths."""
    global _output_dir
    _output_dir = output_dir


def _resolve_path(file_path: str) -> Path:
    """Resolve a path, trying relative to repo if not absolute."""
    path = Path(file_path)
    if path.is_absolute():
        return path
    # Try relative to output dir first (for reviewer reading test files)
    if _output_dir:
        output_relative = Path(_output_dir) / file_path
        if output_relative.exists():
            return output_relative
    # Try relative to repo path
    if _repo_path:
        repo_relative = Path(_repo_path) / file_path
        if repo_relative.exists():
            return repo_relative
    # Fall back to CWD-relative
    return path


@tool("read_file")
def file_read_tool(file_path: str) -> str:
    """Read the contents of a file from the target repository.

    Args:
        file_path: Absolute or relative path to the file to read.
                   Relative paths are resolved against the target repository.

    Returns:
        The file contents as a string.
    """
    path = _resolve_path(file_path)
    if not path.exists():
        return f"ERROR: File not found: {file_path}"
    if not path.is_file():
        return f"ERROR: Not a file: {file_path}"
    try:
        content = path.read_text(encoding="utf-8")
        # Truncate very large files to avoid blowing token budgets
        if len(content) > 50000:
            return content[:50000] + "\n\n... [TRUNCATED — file too large]"
        return content
    except UnicodeDecodeError:
        return f"ERROR: Cannot read binary file: {file_path}"


@tool("list_directory")
def directory_list_tool(directory_path: str = "", max_depth: int = 3) -> str:
    """List directory contents recursively up to a specified depth.

    Args:
        directory_path: Path to the directory to list. If relative or empty,
                       resolved against the target repository root.
        max_depth: Maximum recursion depth (default 3).

    Returns:
        A tree-style listing of files and folders.
    """
    if not directory_path or directory_path == ".":
        path = Path(_repo_path) if _repo_path else Path(".")
    else:
        path = _resolve_path(directory_path)

    if not path.exists():
        return f"ERROR: Directory not found: {directory_path}"
    if not path.is_dir():
        return f"ERROR: Not a directory: {directory_path}"

    lines = []
    _walk_dir(path, lines, prefix="", depth=0, max_depth=max_depth)
    return "\n".join(lines)


def _walk_dir(path: Path, lines: list, prefix: str, depth: int, max_depth: int):
    """Recursive directory walker."""
    if depth >= max_depth:
        return

    # Skip common non-essential directories
    skip_dirs = {
        "node_modules", ".git", "__pycache__", ".next", "dist",
        "build", ".venv", "venv", "coverage", ".nyc_output",
    }

    entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    dirs = [e for e in entries if e.is_dir() and e.name not in skip_dirs]
    files = [e for e in entries if e.is_file()]

    for d in dirs:
        lines.append(f"{prefix}{d.name}/")
        _walk_dir(d, lines, prefix=prefix + "  ", depth=depth + 1, max_depth=max_depth)

    for f in files:
        lines.append(f"{prefix}{f.name}")


@tool("write_file")
def file_write_tool(file_path: str, content: str) -> str:
    """Write content to a file, creating directories as needed.

    Args:
        file_path: Absolute path where the file should be written.
        content: The content to write.

    Returns:
        Confirmation message.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    # Real-time terminal progress — visible as each file is written
    line_count = content.count("\n") + 1
    rel = path.name
    ext = path.suffix

    if ext == ".ts":
        icon = "🧪"
    elif ext == ".md":
        icon = "📋"
    elif ext == ".json":
        icon = "📦"
    else:
        icon = "📄"

    print(f"\n  {icon}  Written: {file_path}  ({line_count} lines)", flush=True)

    return f"Written: {file_path} ({line_count} lines, {len(content)} chars)"
