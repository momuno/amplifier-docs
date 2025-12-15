"""Batch orchestration for document regeneration (Sprint 6)."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .change_detection import ChangeDetector
from .generation import DocumentGenerator
from .llm_client import LLMClient
from .metadata import MetadataManager
from .outline import OutlineGenerator
from .repos import RepoManager
from .sources import SourceParser


@dataclass
class RegenerationResult:
    """Result of regenerating a single document."""

    doc_path: str
    success: bool
    error_message: str | None
    outline_tokens: int
    doc_tokens: int
    duration_seconds: float


@dataclass
class BatchReport:
    """Report for batch regeneration operation."""

    total_docs: int
    successful: int
    failed: int
    total_tokens: int
    total_duration_seconds: float
    estimated_cost_usd: float
    results: List[RegenerationResult]

    def success_rate(self) -> float:
        """Calculate success percentage.

        Returns:
            Success rate as percentage (0.0 to 100.0)
        """
        if self.total_docs == 0:
            return 0.0
        return (self.successful / self.total_docs) * 100.0


class BatchOrchestrator:
    """Orchestrates batch regeneration of changed documents."""

    def __init__(self, llm_client: LLMClient, repo_manager: RepoManager):
        """Initialize batch orchestrator.

        Args:
            llm_client: LLM client for API calls
            repo_manager: Repository manager for cloning
        """
        self.llm_client = llm_client
        self.repo_manager = repo_manager

    def regenerate_changed(self) -> BatchReport:
        """Regenerate all changed documents.

        Returns:
            BatchReport with results for all documents
        """
        changed_docs = self._find_changed_docs()

        if not changed_docs:
            return BatchReport(
                total_docs=0,
                successful=0,
                failed=0,
                total_tokens=0,
                total_duration_seconds=0.0,
                estimated_cost_usd=0.0,
                results=[],
            )

        results = []
        total_tokens = 0
        total_duration = 0.0
        successful = 0
        failed = 0

        for doc_path in changed_docs:
            result = self._regenerate_single_doc(doc_path)
            results.append(result)

            if result.success:
                successful += 1
            else:
                failed += 1

            total_tokens += result.outline_tokens + result.doc_tokens
            total_duration += result.duration_seconds

        estimated_cost = self._estimate_cost(total_tokens)

        return BatchReport(
            total_docs=len(changed_docs),
            successful=successful,
            failed=failed,
            total_tokens=total_tokens,
            total_duration_seconds=total_duration,
            estimated_cost_usd=estimated_cost,
            results=results,
        )

    def _find_changed_docs(self) -> List[str]:
        """Find all documents needing regeneration.

        Returns:
            List of document paths that need regeneration
        """
        all_docs = MetadataManager.find_all_docs()
        changed_docs = []

        for doc_path in all_docs:
            metadata_mgr = MetadataManager(str(doc_path))

            try:
                outline = metadata_mgr.read_outline()
                sources_config = metadata_mgr.read_sources()
            except FileNotFoundError:
                continue

            source_specs = SourceParser.parse_sources_yaml(metadata_mgr.sources_path)

            with RepoManager() as temp_repo_mgr:
                repo_paths = {}
                for spec in source_specs:
                    repo_path = temp_repo_mgr.clone_repo(spec.url, shallow=True)
                    repo_paths[spec.repo_name] = repo_path

                detector = ChangeDetector()
                report = detector.check_changes(outline, repo_paths, str(doc_path))

                if report.needs_regeneration():
                    changed_docs.append(str(doc_path))

        return changed_docs

    def _regenerate_single_doc(self, doc_path: str) -> RegenerationResult:
        """Regenerate a single document.

        Args:
            doc_path: Path to document to regenerate

        Returns:
            RegenerationResult with success status and metrics
        """
        start_time = time.time()
        outline_tokens = 0
        doc_tokens = 0

        try:
            metadata_mgr = MetadataManager(doc_path)
            sources_config = metadata_mgr.read_sources()
            source_specs = SourceParser.parse_sources_yaml(metadata_mgr.sources_path)
            doc_purpose = sources_config.get("metadata", {}).get(
                "purpose", "Documentation"
            )

            with RepoManager() as temp_repo_mgr:
                source_files, commit_hashes = self._collect_source_files(
                    source_specs, temp_repo_mgr
                )

                outline_gen = OutlineGenerator(self.llm_client)
                outline = outline_gen.generate_outline(
                    source_files, commit_hashes, doc_purpose
                )
                outline_tokens = outline.get("_metadata", {}).get("tokens_used", 0)

                doc_gen = DocumentGenerator(self.llm_client)
                markdown = doc_gen.generate_document(outline, source_files, doc_purpose)
                doc_tokens = int(len(markdown.split()) * 1.3)

                staging_path = metadata_mgr.get_staging_path()
                staging_path.write_text(markdown)
                metadata_mgr.save_outline(outline)

            duration = time.time() - start_time

            return RegenerationResult(
                doc_path=doc_path,
                success=True,
                error_message=None,
                outline_tokens=outline_tokens,
                doc_tokens=doc_tokens,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            return RegenerationResult(
                doc_path=doc_path,
                success=False,
                error_message=str(e),
                outline_tokens=outline_tokens,
                doc_tokens=doc_tokens,
                duration_seconds=duration,
            )

    def _collect_source_files(
        self, source_specs: List, repo_manager: RepoManager
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        """Collect source files from repositories.

        Args:
            source_specs: List of SourceSpec objects
            repo_manager: Repository manager for cloning

        Returns:
            Tuple of (source_files, commit_hashes) dictionaries
        """
        source_files = {}
        commit_hashes = {}

        for spec in source_specs:
            repo_path = repo_manager.clone_repo(spec.url, shallow=True)

            for file_path in repo_path.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(repo_path)
                    if spec.matches_file(str(relative_path)):
                        full_key = f"{spec.repo_name}/{relative_path}"
                        source_files[full_key] = file_path.read_text()

                        commit_hash = repo_manager.get_file_commit_hash(
                            repo_path, str(relative_path)
                        )
                        commit_hashes[full_key] = commit_hash

        return source_files, commit_hashes

    def _estimate_cost(self, total_tokens: int) -> float:
        """Estimate cost based on token usage.

        Uses GPT-4 pricing as baseline ($0.02 per 1K tokens).

        Args:
            total_tokens: Total tokens used

        Returns:
            Estimated cost in USD
        """
        return (total_tokens / 1000) * 0.02
