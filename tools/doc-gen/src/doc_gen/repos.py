"""Repository management for doc-gen."""

import tempfile
from pathlib import Path
from typing import List, Optional

from git import Repo


class RepoManager:
    """Manages Git repository operations."""

    def __init__(self, temp_dir: Optional[Path] = None):
        """Initialize repository manager.

        Args:
            temp_dir: Optional custom temp directory. If None, uses system temp.
        """
        self.temp_dir_obj = None
        self.temp_dir = temp_dir

    def __enter__(self):
        """Enter context manager - create temp directory."""
        if self.temp_dir is None:
            # Use system temp directory (auto-cleanup)
            self.temp_dir_obj = tempfile.TemporaryDirectory()
            self.temp_dir = Path(self.temp_dir_obj.name)
        else:
            # Use custom temp directory (persist)
            self.temp_dir = Path(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - cleanup temp directory if needed."""
        if self.temp_dir_obj:
            self.temp_dir_obj.cleanup()

    def clone_repo(self, repo_url: str, shallow: bool = True) -> Path:
        """Clone repository to temp directory.

        Args:
            repo_url: Git repository URL
            shallow: If True, use --depth 1 for faster cloning

        Returns:
            Path to cloned repository
        """
        # Extract repo name from URL
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        clone_path = self.temp_dir / repo_name

        # Clone with shallow option for speed
        if shallow:
            Repo.clone_from(repo_url, clone_path, depth=1)
        else:
            Repo.clone_from(repo_url, clone_path)

        return clone_path

    def get_file_commit_hash(self, repo_path: Path, file_path: str) -> str:
        """Get latest commit hash for a specific file.

        Args:
            repo_path: Path to cloned repository
            file_path: Relative path to file within repo

        Returns:
            Full commit hash (40 characters)

        Raises:
            ValueError: If no commits found for file
        """
        try:
            repo = Repo(repo_path)
            commits = list(repo.iter_commits(paths=file_path, max_count=1))

            if not commits:
                raise ValueError(f"No commits found for file: {file_path}")

            return commits[0].hexsha
        except Exception as e:
            # Catch GitPython errors (e.g., no refs in empty repo)
            if "Reference" in str(e) or "does not exist" in str(e):
                raise ValueError(f"No commits found for file: {file_path}")
            raise

    def list_files(self, repo_path: Path, include_patterns: List[str]) -> List[Path]:
        """List files matching include patterns.

        Sprint 1: Simple glob matching
        Sprint 4: Will enhance with pathspec for gitignore-style patterns

        Args:
            repo_path: Path to repository
            include_patterns: List of glob patterns

        Returns:
            List of file paths (relative to repo root)
        """
        matched_files = []

        for pattern in include_patterns:
            # Simple glob matching for Sprint 1
            for match in repo_path.glob(pattern):
                # Only include files, not directories
                if match.is_file():
                    matched_files.append(match)

        # Convert to relative paths
        relative_files = [f.relative_to(repo_path) for f in matched_files]

        # Remove duplicates
        return list(set(relative_files))
