"""Change detection for documentation regeneration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from git import Repo


@dataclass
class FileChange:
    """Represents a changed file with commit information."""

    file_path: str
    old_hash: str
    new_hash: str
    commit_message: str


@dataclass
class ChangeReport:
    """Report of changes detected in source files."""

    doc_path: str
    changed_files: List[FileChange]
    new_files: List[str]
    removed_files: List[str]
    unchanged_files: List[str]

    def needs_regeneration(self) -> bool:
        """Check if documentation needs regeneration.

        Returns:
            True if any files changed, added, or removed
        """
        return len(self.changed_files) > 0 or len(self.new_files) > 0 or len(self.removed_files) > 0

    def total_changes(self) -> int:
        """Count total number of changes.

        Returns:
            Sum of changed, new, and removed files
        """
        return len(self.changed_files) + len(self.new_files) + len(self.removed_files)


class ChangeDetector:
    """Detects changes in source files for documentation regeneration."""

    def check_changes(
        self,
        outline: Dict,
        repo_paths: Dict[str, Path],
        doc_path: str
    ) -> ChangeReport:
        """Check for changes in source files.

        Args:
            outline: Documentation outline with _commit_hashes
            repo_paths: Dict mapping repo names to their paths
            doc_path: Path to documentation file

        Returns:
            ChangeReport with categorized changes
        """
        commit_hashes = outline.get("_commit_hashes", {})

        changed_files = []
        new_files = []
        removed_files = []
        unchanged_files = []

        outline_files = set(commit_hashes.keys())
        current_files = self._get_current_files(repo_paths)

        for file_path in outline_files:
            if file_path not in current_files:
                removed_files.append(file_path)
            else:
                old_hash = commit_hashes[file_path]
                new_hash = current_files[file_path]

                if old_hash == new_hash:
                    unchanged_files.append(file_path)
                else:
                    commit_msg = self._get_commit_message(file_path, repo_paths)
                    change = FileChange(
                        file_path=file_path,
                        old_hash=old_hash[:7],
                        new_hash=new_hash[:7],
                        commit_message=commit_msg
                    )
                    changed_files.append(change)

        for file_path in current_files:
            if file_path not in outline_files:
                new_files.append(file_path)

        return ChangeReport(
            doc_path=doc_path,
            changed_files=changed_files,
            new_files=new_files,
            removed_files=removed_files,
            unchanged_files=unchanged_files
        )

    def _get_current_files(self, repo_paths: Dict[str, Path]) -> Dict[str, str]:
        """Get current commit hashes for all files in repos.

        Args:
            repo_paths: Dict mapping repo names to their paths

        Returns:
            Dict mapping "repo-name/file-path" to commit hash
        """
        current_files = {}

        for repo_name, repo_path in repo_paths.items():
            repo_files = self._get_repo_files(repo_name, repo_path)
            current_files.update(repo_files)

        return current_files

    def _get_repo_files(self, repo_name: str, repo_path: Path) -> Dict[str, str]:
        """Get all tracked files and their commit hashes from a repo.

        Args:
            repo_name: Name of the repository
            repo_path: Path to the repository

        Returns:
            Dict mapping "repo-name/file-path" to commit hash
        """
        files = {}

        try:
            repo = Repo(repo_path)
            for item in repo.tree().traverse():
                if item.type == "blob":
                    file_path = item.path
                    commit_hash = self._get_file_commit_hash(repo, file_path)
                    if commit_hash:
                        full_path = f"{repo_name}/{file_path}"
                        files[full_path] = commit_hash
        except Exception:
            pass

        return files

    def _get_file_commit_hash(self, repo: Repo, file_path: str) -> str:
        """Get the latest commit hash for a file.

        Args:
            repo: Git repository instance
            file_path: Relative path to file within repo

        Returns:
            Full commit hash or empty string if not found
        """
        try:
            commits = list(repo.iter_commits(paths=file_path, max_count=1))
            if commits:
                return commits[0].hexsha
        except Exception:
            pass

        return ""

    def _get_commit_message(self, file_path: str, repo_paths: Dict[str, Path]) -> str:
        """Get first line of commit message for a file.

        Args:
            file_path: File path in format "repo-name/relative-path"
            repo_paths: Dict mapping repo names to their paths

        Returns:
            First line of commit message
        """
        repo_name, relative_path = self._split_file_path(file_path)
        if not repo_name or repo_name not in repo_paths:
            return ""

        try:
            repo = Repo(repo_paths[repo_name])
            commits = list(repo.iter_commits(paths=relative_path, max_count=1))
            if commits:
                message = commits[0].message.strip()
                return message.split("\n")[0]
        except Exception:
            pass

        return ""

    def _split_file_path(self, file_path: str) -> tuple[str, str]:
        """Split file path into repo name and relative path.

        Args:
            file_path: File path in format "repo-name/relative-path"

        Returns:
            Tuple of (repo_name, relative_path) or ("", "") if invalid
        """
        parts = file_path.split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return "", ""
