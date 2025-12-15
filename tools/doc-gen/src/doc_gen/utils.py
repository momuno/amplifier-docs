"""Utility functions for doc-gen."""

from pathlib import Path


def find_project_root(start_dir: Path | None = None) -> Path | None:
    """Find project root by looking for .git directory.

    Searches up from start_dir (defaults to cwd) looking for .git directory.

    Args:
        start_dir: Directory to start searching from (defaults to cwd)

    Returns:
        Path to project root, or None if no root found
    """
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()

    # Search up directory tree
    while True:
        # Check for .git directory
        if (current / ".git").exists():
            return current

        # Move up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            return None
        current = parent
