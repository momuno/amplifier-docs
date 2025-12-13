"""Source validation for multi-repository specifications."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from .sources import SourceSpec
from .repos import RepoManager


@dataclass
class RepoValidationResult:
    """Validation results for a single repository."""

    repo_name: str
    repo_url: str
    success: bool
    error_message: str = None
    matched_files: List[Tuple[Path, int]] = field(default_factory=list)  # [(file_path, line_count), ...]
    total_files: int = 0
    total_lines: int = 0
    estimated_tokens: int = 0


@dataclass
class ValidationReport:
    """Overall validation report for all repositories."""

    repo_results: List[RepoValidationResult]
    total_repos: int
    successful_repos: int
    total_files: int
    total_lines: int
    estimated_tokens: int
    estimated_cost_usd: float

    def is_valid(self) -> bool:
        """Returns True if all repos validated successfully."""
        return self.successful_repos == self.total_repos


class SourceValidator:
    """Validates source specifications before generation.
    
    Clones repositories, matches files, counts lines, and estimates token costs
    to help users validate their source patterns before expensive LLM calls.
    """

    def __init__(self, repo_manager: RepoManager):
        """Initialize source validator.

        Args:
            repo_manager: RepoManager instance for cloning repositories
        """
        self.repo_manager = repo_manager

    def validate_sources(self, source_specs: List[SourceSpec]) -> ValidationReport:
        """Validate all source specifications.

        Clones repos, matches files, counts lines, estimates tokens.

        Args:
            source_specs: List of SourceSpec objects to validate

        Returns:
            ValidationReport with results for all repositories
        """
        repo_results = []

        for source_spec in source_specs:
            result = self._validate_repo(source_spec)
            repo_results.append(result)

        # Build summary
        successful_repos = sum(1 for r in repo_results if r.success)
        total_files = sum(r.total_files for r in repo_results if r.success)
        total_lines = sum(r.total_lines for r in repo_results if r.success)
        estimated_tokens = sum(r.estimated_tokens for r in repo_results if r.success)

        # Rough cost estimate (GPT-4: ~$0.03 per 1K tokens for input)
        # Claude Sonnet: ~$0.003 per 1K tokens (10x cheaper)
        # Use conservative GPT-4 estimate
        estimated_cost_usd = (estimated_tokens / 1000) * 0.03

        return ValidationReport(
            repo_results=repo_results,
            total_repos=len(source_specs),
            successful_repos=successful_repos,
            total_files=total_files,
            total_lines=total_lines,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

    def _validate_repo(self, source_spec: SourceSpec) -> RepoValidationResult:
        """Validate a single repository.

        Args:
            source_spec: SourceSpec to validate

        Returns:
            RepoValidationResult with validation details or error
        """
        try:
            # Clone repository
            repo_path = self.repo_manager.clone_repo(source_spec.url)

            # List all files in repo
            all_files = list(repo_path.rglob("*"))
            all_files = [f for f in all_files if f.is_file()]

            # Filter by patterns
            matched_files = []
            for file_path in all_files:
                relative_path = file_path.relative_to(repo_path)
                if source_spec.matches_file(str(relative_path)):
                    try:
                        # Count lines
                        content = file_path.read_text(errors="ignore")
                        line_count = len(content.splitlines())
                        matched_files.append((relative_path, line_count))
                    except Exception:
                        # Skip files that can't be read (binary, etc.)
                        pass

            total_files = len(matched_files)
            total_lines = sum(lines for _, lines in matched_files)

            # Estimate tokens (rough: 4 chars per token)
            # Assume ~50 chars per line on average
            estimated_tokens = total_lines * 50  # ~50 chars per line avg
            estimated_tokens = estimated_tokens // 4  # 4 chars per token

            return RepoValidationResult(
                repo_name=source_spec.repo_name,
                repo_url=source_spec.url,
                success=True,
                matched_files=matched_files,
                total_files=total_files,
                total_lines=total_lines,
                estimated_tokens=estimated_tokens,
            )

        except Exception as e:
            return RepoValidationResult(
                repo_name=source_spec.repo_name,
                repo_url=source_spec.url,
                success=False,
                error_message=str(e),
            )
