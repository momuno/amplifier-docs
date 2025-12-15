"""Tests for batch orchestration (Sprint 6)."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from doc_gen.orchestration import (
    RegenerationResult,
    BatchReport,
    BatchOrchestrator,
)


class TestRegenerationResult:
    """Tests for RegenerationResult dataclass."""

    def test_regeneration_result_success(self):
        result = RegenerationResult(
            doc_path="docs/test.md",
            success=True,
            error_message=None,
            outline_tokens=1000,
            doc_tokens=2000,
            duration_seconds=5.5,
        )

        assert result.doc_path == "docs/test.md"
        assert result.success is True
        assert result.error_message is None
        assert result.outline_tokens == 1000
        assert result.doc_tokens == 2000
        assert result.duration_seconds == 5.5

    def test_regeneration_result_failure(self):
        result = RegenerationResult(
            doc_path="docs/test.md",
            success=False,
            error_message="LLM API timeout",
            outline_tokens=0,
            doc_tokens=0,
            duration_seconds=2.0,
        )

        assert result.doc_path == "docs/test.md"
        assert result.success is False
        assert result.error_message == "LLM API timeout"
        assert result.outline_tokens == 0
        assert result.doc_tokens == 0

    def test_regeneration_result_total_tokens(self):
        result = RegenerationResult(
            doc_path="docs/test.md",
            success=True,
            error_message=None,
            outline_tokens=1000,
            doc_tokens=2000,
            duration_seconds=5.5,
        )

        assert result.outline_tokens + result.doc_tokens == 3000


class TestBatchReport:
    """Tests for BatchReport dataclass."""

    def test_batch_report_all_successful(self):
        results = [
            RegenerationResult("docs/test1.md", True, None, 1000, 2000, 5.0),
            RegenerationResult("docs/test2.md", True, None, 1500, 2500, 6.0),
        ]

        report = BatchReport(
            total_docs=2,
            successful=2,
            failed=0,
            total_tokens=7000,
            total_duration_seconds=11.0,
            estimated_cost_usd=0.14,
            results=results,
        )

        assert report.total_docs == 2
        assert report.successful == 2
        assert report.failed == 0
        assert report.total_tokens == 7000
        assert report.total_duration_seconds == 11.0
        assert report.estimated_cost_usd == 0.14
        assert len(report.results) == 2

    def test_batch_report_with_failures(self):
        results = [
            RegenerationResult("docs/test1.md", True, None, 1000, 2000, 5.0),
            RegenerationResult("docs/test2.md", False, "Error", 0, 0, 1.0),
            RegenerationResult("docs/test3.md", True, None, 1500, 2500, 6.0),
        ]

        report = BatchReport(
            total_docs=3,
            successful=2,
            failed=1,
            total_tokens=7000,
            total_duration_seconds=12.0,
            estimated_cost_usd=0.14,
            results=results,
        )

        assert report.total_docs == 3
        assert report.successful == 2
        assert report.failed == 1

    def test_batch_report_success_rate_100_percent(self):
        results = [
            RegenerationResult("docs/test1.md", True, None, 1000, 2000, 5.0),
            RegenerationResult("docs/test2.md", True, None, 1500, 2500, 6.0),
        ]

        report = BatchReport(
            total_docs=2,
            successful=2,
            failed=0,
            total_tokens=7000,
            total_duration_seconds=11.0,
            estimated_cost_usd=0.14,
            results=results,
        )

        assert report.success_rate() == 100.0

    def test_batch_report_success_rate_50_percent(self):
        results = [
            RegenerationResult("docs/test1.md", True, None, 1000, 2000, 5.0),
            RegenerationResult("docs/test2.md", False, "Error", 0, 0, 1.0),
        ]

        report = BatchReport(
            total_docs=2,
            successful=1,
            failed=1,
            total_tokens=3000,
            total_duration_seconds=6.0,
            estimated_cost_usd=0.06,
            results=results,
        )

        assert report.success_rate() == 50.0

    def test_batch_report_success_rate_zero_docs(self):
        report = BatchReport(
            total_docs=0,
            successful=0,
            failed=0,
            total_tokens=0,
            total_duration_seconds=0.0,
            estimated_cost_usd=0.0,
            results=[],
        )

        assert report.success_rate() == 0.0

    def test_batch_report_success_rate_all_failed(self):
        results = [
            RegenerationResult("docs/test1.md", False, "Error 1", 0, 0, 1.0),
            RegenerationResult("docs/test2.md", False, "Error 2", 0, 0, 1.0),
        ]

        report = BatchReport(
            total_docs=2,
            successful=0,
            failed=2,
            total_tokens=0,
            total_duration_seconds=2.0,
            estimated_cost_usd=0.0,
            results=results,
        )

        assert report.success_rate() == 0.0


class TestBatchOrchestratorFindChangedDocs:
    """Tests for BatchOrchestrator._find_changed_docs method."""

    def test_find_changed_docs_returns_empty_when_no_docs(self):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)

        with patch("doc_gen.orchestration.MetadataManager") as mock_metadata:
            mock_metadata.find_all_docs.return_value = []

            changed_docs = orchestrator._find_changed_docs()

            assert changed_docs == []

    def test_find_changed_docs_detects_changed_doc(self, tmp_path):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)

        doc_path = Path("docs/test.md")
        
        mock_metadata_instance = Mock()
        mock_metadata_instance.read_outline.return_value = {
            "_commit_hashes": {"repo/file.py": "abc123"}
        }
        mock_metadata_instance.read_sources.return_value = {
            "repositories": [{"url": "https://github.com/test/repo.git", "include": ["*.py"]}]
        }

        mock_change_detector = Mock()
        mock_change_report = Mock()
        mock_change_report.needs_regeneration.return_value = True
        mock_change_detector.check_changes.return_value = mock_change_report

        mock_spec = Mock()
        mock_spec.url = "https://github.com/test/repo.git"
        mock_spec.repo_name = "repo"

        with patch("doc_gen.orchestration.MetadataManager") as mock_metadata_cls, \
             patch("doc_gen.orchestration.ChangeDetector", return_value=mock_change_detector), \
             patch("doc_gen.orchestration.SourceParser") as mock_parser, \
             patch("doc_gen.orchestration.RepoManager") as mock_rm_cls:
            
            mock_metadata_cls.find_all_docs.return_value = [doc_path]
            mock_metadata_cls.return_value = mock_metadata_instance
            mock_parser.parse_sources_yaml.return_value = [mock_spec]
            
            mock_rm_instance = Mock()
            mock_rm_instance.__enter__ = Mock(return_value=mock_rm_instance)
            mock_rm_instance.__exit__ = Mock(return_value=False)
            mock_rm_instance.clone_repo.return_value = tmp_path / "repo"
            mock_rm_cls.return_value = mock_rm_instance

            changed_docs = orchestrator._find_changed_docs()

            assert len(changed_docs) == 1
            assert str(changed_docs[0]) == "docs/test.md"

    def test_find_changed_docs_skips_unchanged_doc(self, tmp_path):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)

        doc_path = Path("docs/test.md")
        
        mock_metadata_instance = Mock()
        mock_metadata_instance.read_outline.return_value = {
            "_commit_hashes": {"repo/file.py": "abc123"}
        }
        mock_metadata_instance.read_sources.return_value = {
            "repositories": [{"url": "https://github.com/test/repo.git", "include": ["*.py"]}]
        }

        mock_change_detector = Mock()
        mock_change_report = Mock()
        mock_change_report.needs_regeneration.return_value = False
        mock_change_detector.check_changes.return_value = mock_change_report

        mock_spec = Mock()
        mock_spec.url = "https://github.com/test/repo.git"
        mock_spec.repo_name = "repo"

        with patch("doc_gen.orchestration.MetadataManager") as mock_metadata_cls, \
             patch("doc_gen.orchestration.ChangeDetector", return_value=mock_change_detector), \
             patch("doc_gen.orchestration.SourceParser") as mock_parser, \
             patch("doc_gen.orchestration.RepoManager") as mock_rm_cls:
            
            mock_metadata_cls.find_all_docs.return_value = [doc_path]
            mock_metadata_cls.return_value = mock_metadata_instance
            mock_parser.parse_sources_yaml.return_value = [mock_spec]
            
            mock_rm_instance = Mock()
            mock_rm_instance.__enter__ = Mock(return_value=mock_rm_instance)
            mock_rm_instance.__exit__ = Mock(return_value=False)
            mock_rm_instance.clone_repo.return_value = tmp_path / "repo"
            mock_rm_cls.return_value = mock_rm_instance

            changed_docs = orchestrator._find_changed_docs()

            assert changed_docs == []

    def test_find_changed_docs_handles_missing_outline(self):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)

        doc_path = Path("docs/test.md")
        
        mock_metadata_instance = Mock()
        mock_metadata_instance.read_outline.side_effect = FileNotFoundError("No outline")

        with patch("doc_gen.orchestration.MetadataManager") as mock_metadata_cls:
            mock_metadata_cls.find_all_docs.return_value = [doc_path]
            mock_metadata_cls.return_value = mock_metadata_instance

            changed_docs = orchestrator._find_changed_docs()

            assert changed_docs == []


class TestBatchOrchestratorRegenerateSingleDoc:
    """Tests for BatchOrchestrator._regenerate_single_doc method."""

    def test_regenerate_single_doc_success(self, tmp_path):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)

        doc_path = "docs/test.md"
        
        mock_metadata_instance = Mock()
        mock_metadata_instance.read_sources.return_value = {
            "repositories": [{"url": "https://github.com/test/repo.git", "include": ["*.py"]}],
            "metadata": {"purpose": "Test doc"}
        }
        mock_metadata_instance.get_staging_path.return_value = tmp_path / "staging.md"

        mock_source_spec = Mock()
        mock_source_spec.url = "https://github.com/test/repo.git"
        mock_source_spec.repo_name = "repo"
        mock_source_spec.matches_file.return_value = True

        mock_repo_path = tmp_path / "repo"
        mock_repo_path.mkdir()
        (mock_repo_path / "test.py").write_text("print('hello')")

        mock_outline_response = Mock()
        mock_outline_response.tokens_used = 1000
        mock_outline_response.duration_seconds = 2.0

        mock_doc_response = Mock()
        mock_doc_response.tokens_used = 2000
        mock_doc_response.duration_seconds = 3.0

        mock_outline_gen = Mock()
        mock_outline_gen.generate_outline.return_value = {
            "title": "Test",
            "_metadata": {"tokens_used": 1000}
        }
        mock_outline_gen.client.generate.return_value = mock_outline_response

        mock_doc_gen = Mock()
        mock_doc_gen.generate_document.return_value = "# Test Doc\n\nContent " * 500
        mock_doc_gen.client.generate.return_value = mock_doc_response

        with patch("doc_gen.orchestration.MetadataManager", return_value=mock_metadata_instance), \
             patch("doc_gen.orchestration.SourceParser") as mock_parser, \
             patch("doc_gen.orchestration.RepoManager") as mock_rm_cls, \
             patch("doc_gen.orchestration.OutlineGenerator", return_value=mock_outline_gen), \
             patch("doc_gen.orchestration.DocumentGenerator", return_value=mock_doc_gen):
            
            mock_parser.parse_sources_yaml.return_value = [mock_source_spec]
            
            mock_rm_instance = Mock()
            mock_rm_instance.__enter__ = Mock(return_value=mock_rm_instance)
            mock_rm_instance.__exit__ = Mock(return_value=False)
            mock_rm_instance.clone_repo.return_value = mock_repo_path
            mock_rm_instance.get_file_commit_hash.return_value = "abc123def456"
            mock_rm_cls.return_value = mock_rm_instance

            result = orchestrator._regenerate_single_doc(doc_path)

            assert result.doc_path == doc_path
            assert result.success is True
            assert result.error_message is None
            assert result.outline_tokens == 1000
            assert result.doc_tokens > 1500
            assert result.duration_seconds > 0

    def test_regenerate_single_doc_handles_outline_error(self):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)

        doc_path = "docs/test.md"
        
        mock_metadata_instance = Mock()
        mock_metadata_instance.read_sources.return_value = {
            "repositories": [{"url": "https://github.com/test/repo.git", "include": ["*.py"]}],
            "metadata": {"purpose": "Test doc"}
        }

        mock_outline_gen = Mock()
        mock_outline_gen.generate_outline.side_effect = Exception("LLM timeout")

        with patch("doc_gen.orchestration.MetadataManager", return_value=mock_metadata_instance), \
             patch("doc_gen.orchestration.SourceParser") as mock_parser, \
             patch("doc_gen.orchestration.RepoManager") as mock_rm_cls, \
             patch("doc_gen.orchestration.OutlineGenerator", return_value=mock_outline_gen):
            
            mock_parser.parse_sources_yaml.return_value = [Mock(url="test", repo_name="repo")]
            
            mock_rm_instance = Mock()
            mock_rm_instance.__enter__ = Mock(return_value=mock_rm_instance)
            mock_rm_instance.__exit__ = Mock(return_value=False)
            mock_rm_instance.clone_repo.return_value = Path("/tmp/repo")
            mock_rm_cls.return_value = mock_rm_instance

            result = orchestrator._regenerate_single_doc(doc_path)

            assert result.doc_path == doc_path
            assert result.success is False
            assert "LLM timeout" in result.error_message
            assert result.outline_tokens == 0
            assert result.doc_tokens == 0

    def test_regenerate_single_doc_handles_document_error(self, tmp_path):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)

        doc_path = "docs/test.md"
        
        mock_metadata_instance = Mock()
        mock_metadata_instance.read_sources.return_value = {
            "repositories": [{"url": "https://github.com/test/repo.git", "include": ["*.py"]}],
            "metadata": {"purpose": "Test doc"}
        }

        mock_outline_gen = Mock()
        mock_outline_gen.generate_outline.return_value = {
            "title": "Test",
            "_metadata": {"tokens_used": 1000}
        }

        mock_doc_gen = Mock()
        mock_doc_gen.generate_document.side_effect = Exception("Document validation failed")

        with patch("doc_gen.orchestration.MetadataManager", return_value=mock_metadata_instance), \
             patch("doc_gen.orchestration.SourceParser") as mock_parser, \
             patch("doc_gen.orchestration.RepoManager") as mock_rm_cls, \
             patch("doc_gen.orchestration.OutlineGenerator", return_value=mock_outline_gen), \
             patch("doc_gen.orchestration.DocumentGenerator", return_value=mock_doc_gen):
            
            mock_parser.parse_sources_yaml.return_value = [Mock(url="test", repo_name="repo")]
            
            mock_rm_instance = Mock()
            mock_rm_instance.__enter__ = Mock(return_value=mock_rm_instance)
            mock_rm_instance.__exit__ = Mock(return_value=False)
            mock_rm_instance.clone_repo.return_value = Path("/tmp/repo")
            mock_rm_cls.return_value = mock_rm_instance

            result = orchestrator._regenerate_single_doc(doc_path)

            assert result.doc_path == doc_path
            assert result.success is False
            assert "Document validation failed" in result.error_message


class TestBatchOrchestratorRegenerateChanged:
    """Tests for BatchOrchestrator.regenerate_changed method."""

    def test_regenerate_changed_empty_batch(self):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)
        orchestrator._find_changed_docs = Mock(return_value=[])

        report = orchestrator.regenerate_changed()

        assert report.total_docs == 0
        assert report.successful == 0
        assert report.failed == 0
        assert report.total_tokens == 0
        assert report.total_duration_seconds == 0.0
        assert report.estimated_cost_usd == 0.0
        assert len(report.results) == 0

    def test_regenerate_changed_all_successful(self):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)
        orchestrator._find_changed_docs = Mock(return_value=["docs/test1.md", "docs/test2.md"])
        
        result1 = RegenerationResult("docs/test1.md", True, None, 1000, 2000, 5.0)
        result2 = RegenerationResult("docs/test2.md", True, None, 1500, 2500, 6.0)
        
        orchestrator._regenerate_single_doc = Mock(side_effect=[result1, result2])

        report = orchestrator.regenerate_changed()

        assert report.total_docs == 2
        assert report.successful == 2
        assert report.failed == 0
        assert report.total_tokens == 7000
        assert report.total_duration_seconds == 11.0
        assert report.estimated_cost_usd > 0
        assert len(report.results) == 2

    def test_regenerate_changed_continues_on_error(self):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)
        orchestrator._find_changed_docs = Mock(return_value=["docs/test1.md", "docs/test2.md", "docs/test3.md"])
        
        result1 = RegenerationResult("docs/test1.md", True, None, 1000, 2000, 5.0)
        result2 = RegenerationResult("docs/test2.md", False, "Error occurred", 0, 0, 1.0)
        result3 = RegenerationResult("docs/test3.md", True, None, 1500, 2500, 6.0)
        
        orchestrator._regenerate_single_doc = Mock(side_effect=[result1, result2, result3])

        report = orchestrator.regenerate_changed()

        assert report.total_docs == 3
        assert report.successful == 2
        assert report.failed == 1
        assert report.total_tokens == 7000
        assert len(report.results) == 3

    def test_regenerate_changed_calculates_cost(self):
        mock_llm = Mock()
        mock_repo_manager = Mock()

        orchestrator = BatchOrchestrator(mock_llm, mock_repo_manager)
        orchestrator._find_changed_docs = Mock(return_value=["docs/test1.md"])
        
        result1 = RegenerationResult("docs/test1.md", True, None, 10000, 20000, 5.0)
        
        orchestrator._regenerate_single_doc = Mock(return_value=result1)

        report = orchestrator.regenerate_changed()

        assert report.total_tokens == 30000
        assert report.estimated_cost_usd == pytest.approx(0.6, rel=0.1)
