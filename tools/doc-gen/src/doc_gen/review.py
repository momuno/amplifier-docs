"""Review module for comparing staging and live documentation."""

from pathlib import Path
from typing import Union, Tuple, Dict
import difflib

import click


class DiffGenerator:
    """Generate unified diffs between staging and live documents."""

    def generate_diff(
        self,
        staging_path: Union[str, Path],
        live_path: Union[str, Path],
        colorize: bool = True
    ) -> Tuple[str, Dict[str, int]]:
        """Generate unified diff between staging and live documents.

        Args:
            staging_path: Path to staging document
            live_path: Path to live document
            colorize: Whether to colorize the diff output

        Returns:
            Tuple of (diff_text, stats) where stats contains:
                - added: Number of lines added
                - removed: Number of lines removed
                - modified: Number of lines modified (changed content)
        """
        staging_path = Path(staging_path)
        live_path = Path(live_path)

        # Read files
        if staging_path.exists():
            staging_lines = staging_path.read_text().splitlines(keepends=True)
        else:
            staging_lines = []

        if live_path.exists():
            live_lines = live_path.read_text().splitlines(keepends=True)
        else:
            live_lines = []

        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            live_lines,
            staging_lines,
            fromfile=str(live_path),
            tofile=str(staging_path),
            lineterm=""
        ))

        # Calculate statistics
        stats = self._calculate_stats(diff_lines)

        # Format diff
        if not diff_lines:
            return "", stats

        # Colorize if requested
        if colorize:
            diff_text = self._colorize_diff(diff_lines)
        else:
            diff_text = "\n".join(diff_lines)

        return diff_text, stats

    def _calculate_stats(self, diff_lines: list) -> Dict[str, int]:
        """Calculate statistics from diff lines.

        Args:
            diff_lines: List of unified diff lines

        Returns:
            Dictionary with added, removed, modified counts
        """
        added = 0
        removed = 0

        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1

        # For modified: count pairs of changes at same location
        # Simplified: if both added and removed, some are modifications
        modified = min(added, removed)

        return {
            "added": added,
            "removed": removed,
            "modified": modified
        }

    def _colorize_diff(self, diff_lines: list) -> str:
        """Apply color codes to diff lines.

        Args:
            diff_lines: List of unified diff lines

        Returns:
            Colorized diff text
        """
        colored_lines = []

        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                # Green for additions
                colored_lines.append(click.style(line, fg="green"))
            elif line.startswith("-") and not line.startswith("---"):
                # Red for removals
                colored_lines.append(click.style(line, fg="red"))
            elif line.startswith("@@"):
                # Cyan for context markers
                colored_lines.append(click.style(line, fg="cyan"))
            else:
                colored_lines.append(line)

        return "\n".join(colored_lines)
