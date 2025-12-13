"""Multi-repository source specification parsing."""

from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import pathspec
import yaml


class SourceSpec:
    """Represents a single repository source specification."""

    def __init__(self, url: str, include: List[str], exclude: List[str] = None):
        """Initialize source specification.

        Args:
            url: Git repository URL
            include: List of gitignore-style include patterns
            exclude: List of gitignore-style exclude patterns (optional)
        """
        self.url = url
        self.include_patterns = include or []
        self.exclude_patterns = exclude or []
        self.repo_name = self._extract_repo_name(url)

    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL.

        Args:
            url: Git repository URL

        Returns:
            Repository name (e.g., "my-repo" from "https://github.com/owner/my-repo.git")
        """
        # https://github.com/owner/repo.git → repo
        return url.rstrip("/").split("/")[-1].replace(".git", "")

    def validate(self):
        """Validate this source specification.

        Raises:
            SourceSpecError: If specification is invalid
        """
        # Validate URL format
        parsed = urlparse(self.url)
        if not parsed.scheme or not parsed.netloc:
            raise SourceSpecError(
                f"Invalid repository URL: {self.url}\n"
                f"Expected format: https://github.com/owner/repo.git"
            )

        # Validate patterns are not empty
        if not self.include_patterns:
            raise SourceSpecError(
                f"Repository {self.repo_name} has no include patterns.\n"
                f"Specify at least one pattern (e.g., '*.py')"
            )

    def matches_file(self, file_path: str) -> bool:
        """Check if file matches this source's patterns.

        Uses gitignore-style pattern matching via pathspec library.

        Args:
            file_path: Relative file path to check

        Returns:
            True if file matches include patterns and not excluded
        """
        # Check include patterns first
        include_spec = pathspec.PathSpec.from_lines("gitwildmatch", self.include_patterns)
        if not include_spec.match_file(file_path):
            return False

        # If file matched include, check exclude patterns
        if self.exclude_patterns:
            exclude_spec = pathspec.PathSpec.from_lines(
                "gitwildmatch", self.exclude_patterns
            )
            if exclude_spec.match_file(file_path):
                return False

        return True


class SourceParser:
    """Parses multi-repository source specifications."""

    @staticmethod
    def parse_sources_yaml(yaml_path: Path) -> List[SourceSpec]:
        """Parse sources.yaml into list of SourceSpec objects.

        Supports both single-repo (Sprint 1-3) and multi-repo formats.

        Args:
            yaml_path: Path to sources.yaml file

        Returns:
            List of SourceSpec objects

        Raises:
            SourceSpecError: If sources.yaml is invalid
        """
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        if "repositories" not in data:
            raise SourceSpecError(
                f"Missing 'repositories' key in {yaml_path}\n"
                f"Expected structure:\n"
                f"  repositories:\n"
                f"    - url: https://github.com/...\n"
                f"      include: ['*.py']"
            )

        repos = data["repositories"]
        if not isinstance(repos, list):
            raise SourceSpecError("'repositories' must be a list")

        source_specs = []
        for i, repo_config in enumerate(repos):
            try:
                source_spec = SourceParser._parse_repo_config(repo_config)
                source_spec.validate()
                source_specs.append(source_spec)
            except Exception as e:
                raise SourceSpecError(f"Error in repository #{i+1}: {e}")

        return source_specs

    @staticmethod
    def _parse_repo_config(config: Dict[str, Any]) -> SourceSpec:
        """Parse single repository configuration.

        Args:
            config: Repository configuration dict

        Returns:
            SourceSpec object

        Raises:
            SourceSpecError: If config is invalid
        """
        url = config.get("url")
        if not url:
            raise SourceSpecError("Missing 'url' field")

        include = config.get("include", [])
        exclude = config.get("exclude", [])

        return SourceSpec(url, include, exclude)


class SourceSpecError(Exception):
    """Error in source specification."""

    pass
