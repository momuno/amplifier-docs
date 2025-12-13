"""Tests for source validation functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from doc_gen.validation import (
    SourceValidator,
    RepoValidationResult,
    ValidationReport
)
from doc_gen.sources import SourceSpec


class TestRepoValidationResult:
    """Test RepoValidationResult dataclass."""

    def test_repo_validation_result_initializes_with_success(self):
        """Should initialize validation result with success data."""
        # ARRANGE & ACT
        result = RepoValidationResult(
            repo_name="test-repo",
            repo_url="https://github.com/owner/test-repo.git",
            success=True,
            matched_files=[(Path("main.py"), 100), (Path("test.py"), 50)],
            total_files=2,
            total_lines=150,
            estimated_tokens=1875
        )

        # ASSERT
        assert result.repo_name == "test-repo"
        assert result.repo_url == "https://github.com/owner/test-repo.git"
        assert result.success is True
        assert result.error_message is None
        assert len(result.matched_files) == 2
        assert result.total_files == 2
        assert result.total_lines == 150
        assert result.estimated_tokens == 1875

    def test_repo_validation_result_initializes_with_failure(self):
        """Should initialize validation result with failure data."""
        # ARRANGE & ACT
        result = RepoValidationResult(
            repo_name="failed-repo",
            repo_url="https://github.com/owner/failed-repo.git",
            success=False,
            error_message="Clone failed: repository not found"
        )

        # ASSERT
        assert result.repo_name == "failed-repo"
        assert result.success is False
        assert result.error_message == "Clone failed: repository not found"
        assert result.matched_files == []
        assert result.total_files == 0
        assert result.total_lines == 0
        assert result.estimated_tokens == 0

    def test_repo_validation_result_defaults(self):
        """Should use default values for optional fields."""
        # ARRANGE & ACT
        result = RepoValidationResult(
            repo_name="minimal-repo",
            repo_url="https://github.com/owner/minimal-repo.git",
            success=True
        )

        # ASSERT
        assert result.error_message is None
        assert result.matched_files == []
        assert result.total_files == 0
        assert result.total_lines == 0
        assert result.estimated_tokens == 0


class TestValidationReport:
    """Test ValidationReport dataclass."""

    def test_validation_report_initializes(self):
        """Should initialize validation report with summary data."""
        # ARRANGE
        repo_results = [
            RepoValidationResult(
                repo_name="repo1",
                repo_url="https://github.com/owner/repo1.git",
                success=True,
                total_files=10,
                total_lines=500,
                estimated_tokens=6250
            ),
            RepoValidationResult(
                repo_name="repo2",
                repo_url="https://github.com/owner/repo2.git",
                success=True,
                total_files=5,
                total_lines=250,
                estimated_tokens=3125
            )
        ]

        # ACT
        report = ValidationReport(
            repo_results=repo_results,
            total_repos=2,
            successful_repos=2,
            total_files=15,
            total_lines=750,
            estimated_tokens=9375,
            estimated_cost_usd=0.28125
        )

        # ASSERT
        assert len(report.repo_results) == 2
        assert report.total_repos == 2
        assert report.successful_repos == 2
        assert report.total_files == 15
        assert report.total_lines == 750
        assert report.estimated_tokens == 9375
        assert report.estimated_cost_usd == 0.28125

    def test_is_valid_returns_true_when_all_repos_successful(self):
        """Should return True when all repos validated successfully."""
        # ARRANGE
        report = ValidationReport(
            repo_results=[],
            total_repos=3,
            successful_repos=3,
            total_files=10,
            total_lines=500,
            estimated_tokens=6250,
            estimated_cost_usd=0.1875
        )

        # ACT & ASSERT
        assert report.is_valid() is True

    def test_is_valid_returns_false_when_some_repos_failed(self):
        """Should return False when some repos failed validation."""
        # ARRANGE
        report = ValidationReport(
            repo_results=[],
            total_repos=3,
            successful_repos=2,
            total_files=10,
            total_lines=500,
            estimated_tokens=6250,
            estimated_cost_usd=0.1875
        )

        # ACT & ASSERT
        assert report.is_valid() is False

    def test_is_valid_returns_false_when_all_repos_failed(self):
        """Should return False when all repos failed validation."""
        # ARRANGE
        report = ValidationReport(
            repo_results=[],
            total_repos=3,
            successful_repos=0,
            total_files=0,
            total_lines=0,
            estimated_tokens=0,
            estimated_cost_usd=0.0
        )

        # ACT & ASSERT
        assert report.is_valid() is False

    def test_is_valid_returns_true_for_empty_report(self):
        """Should return True for report with no repos (edge case)."""
        # ARRANGE
        report = ValidationReport(
            repo_results=[],
            total_repos=0,
            successful_repos=0,
            total_files=0,
            total_lines=0,
            estimated_tokens=0,
            estimated_cost_usd=0.0
        )

        # ACT & ASSERT
        assert report.is_valid() is True


class TestSourceValidator:
    """Test SourceValidator class."""

    def test_source_validator_initializes(self):
        """Should initialize with RepoManager."""
        # ARRANGE
        mock_repo_manager = Mock()

        # ACT
        validator = SourceValidator(mock_repo_manager)

        # ASSERT
        assert validator.repo_manager == mock_repo_manager

    def test_validate_sources_with_single_successful_repo(self):
        """Should validate single repository successfully."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock file structure
        mock_files = [
            mock_repo_path / "main.py",
            mock_repo_path / "test.py",
            mock_repo_path / "README.md"
        ]

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_file_objects = []
            for f in mock_files:
                mock_file = Mock()
                mock_file.is_file.return_value = True
                mock_file.relative_to.return_value = Path(f.name)
                mock_file.read_text.return_value = "line1\nline2\nline3\n"
                mock_file.__str__ = lambda self, name=f.name: name
                mock_file_objects.append(mock_file)

            mock_rglob.return_value = mock_file_objects
            report = validator.validate_sources([source_spec])

        # ASSERT
        assert report.total_repos == 1
        assert report.successful_repos == 1
        assert report.is_valid() is True
        assert len(report.repo_results) == 1
        assert report.repo_results[0].success is True
        assert report.repo_results[0].repo_name == "test-repo"

    def test_validate_sources_with_multiple_successful_repos(self):
        """Should validate multiple repositories successfully."""
        # ARRANGE
        mock_repo_manager = Mock()

        def mock_clone(url):
            repo_name = url.split("/")[-1].replace(".git", "")
            return Path(f"/tmp/repos/{repo_name}")

        mock_repo_manager.clone_repo.side_effect = mock_clone

        source_specs = [
            SourceSpec("https://github.com/owner/repo1.git", ["*.py"]),
            SourceSpec("https://github.com/owner/repo2.git", ["*.js"])
        ]

        validator = SourceValidator(mock_repo_manager)

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = []
            report = validator.validate_sources(source_specs)

        # ASSERT
        assert report.total_repos == 2
        assert report.successful_repos == 2
        assert report.is_valid() is True
        assert len(report.repo_results) == 2

    def test_validate_sources_with_clone_failure(self):
        """Should handle repository clone failure gracefully."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_manager.clone_repo.side_effect = Exception("Clone failed: authentication required")

        source_spec = SourceSpec(
            url="https://github.com/owner/private-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # ACT
        report = validator.validate_sources([source_spec])

        # ASSERT
        assert report.total_repos == 1
        assert report.successful_repos == 0
        assert report.is_valid() is False
        assert len(report.repo_results) == 1
        assert report.repo_results[0].success is False
        assert "Clone failed" in report.repo_results[0].error_message
        assert report.total_files == 0
        assert report.total_lines == 0

    def test_validate_sources_with_partial_failures(self):
        """Should handle mix of successful and failed repos."""
        # ARRANGE
        mock_repo_manager = Mock()

        def mock_clone(url):
            if "fail" in url:
                raise Exception("Clone failed")
            repo_name = url.split("/")[-1].replace(".git", "")
            return Path(f"/tmp/repos/{repo_name}")

        mock_repo_manager.clone_repo.side_effect = mock_clone

        source_specs = [
            SourceSpec("https://github.com/owner/success-repo.git", ["*.py"]),
            SourceSpec("https://github.com/owner/fail-repo.git", ["*.js"]),
            SourceSpec("https://github.com/owner/another-success.git", ["*.go"])
        ]

        validator = SourceValidator(mock_repo_manager)

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = []
            report = validator.validate_sources(source_specs)

        # ASSERT
        assert report.total_repos == 3
        assert report.successful_repos == 2
        assert report.is_valid() is False
        assert report.repo_results[0].success is True
        assert report.repo_results[1].success is False
        assert report.repo_results[2].success is True

    def test_validate_sources_calculates_token_estimates(self):
        """Should calculate token estimates from line counts."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock a file with 100 lines
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.relative_to.return_value = Path("main.py")
        mock_file.read_text.return_value = "\n".join([f"line {i}" for i in range(100)])

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = [mock_file]
            report = validator.validate_sources([source_spec])

        # ASSERT
        assert report.total_lines == 100
        # 100 lines * 50 chars/line = 5000 chars
        # 5000 chars / 4 chars/token = 1250 tokens
        assert report.estimated_tokens == 1250

    def test_validate_sources_calculates_cost_estimates(self):
        """Should calculate cost estimates from token counts."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock file with 1000 lines = 12500 tokens
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.relative_to.return_value = Path("main.py")
        mock_file.read_text.return_value = "\n".join([f"line {i}" for i in range(1000)])

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = [mock_file]
            report = validator.validate_sources([source_spec])

        # ASSERT
        # 1000 lines * 50 chars/line = 50000 chars
        # 50000 / 4 = 12500 tokens
        # 12500 tokens / 1000 * $0.03 = $0.375
        assert report.estimated_tokens == 12500
        assert report.estimated_cost_usd == 0.375

    def test_validate_sources_with_empty_repo(self):
        """Should handle repository with no matching files."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/empty-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/empty-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = []
            report = validator.validate_sources([source_spec])

        # ASSERT
        assert report.successful_repos == 1
        assert report.total_files == 0
        assert report.total_lines == 0
        assert report.estimated_tokens == 0
        assert report.estimated_cost_usd == 0.0

    def test_validate_sources_filters_by_patterns(self):
        """Should filter files by include/exclude patterns."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"],
            exclude=["test_*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock files: 2 .py files (one excluded), 1 .js file (not included)
        mock_files = []
        for filename, should_match in [
            ("main.py", True),
            ("test_main.py", False),  # Excluded
            ("script.js", False)  # Not included
        ]:
            mock_file = Mock()
            mock_file.is_file.return_value = True
            mock_file.relative_to.return_value = Path(filename)
            mock_file.read_text.return_value = "line1\nline2\n"
            mock_file.__str__ = lambda self, name=filename: name
            mock_files.append(mock_file)

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = mock_files
            report = validator.validate_sources([source_spec])

        # ASSERT
        assert report.successful_repos == 1
        # Only main.py should match
        assert report.total_files == 1

    def test_validate_sources_skips_unreadable_files(self):
        """Should skip files that can't be read (binary, permissions)."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["**/*"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock files: one readable, one unreadable
        mock_readable = Mock()
        mock_readable.is_file.return_value = True
        mock_readable.relative_to.return_value = Path("readable.txt")
        mock_readable.read_text.return_value = "line1\nline2\n"

        mock_unreadable = Mock()
        mock_unreadable.is_file.return_value = True
        mock_unreadable.relative_to.return_value = Path("binary.bin")
        mock_unreadable.read_text.side_effect = UnicodeDecodeError(
            'utf-8', b'', 0, 1, 'invalid start byte'
        )

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = [mock_readable, mock_unreadable]
            report = validator.validate_sources([source_spec])

        # ASSERT
        assert report.successful_repos == 1
        # Only readable file should be counted
        assert report.total_files == 1
        assert report.total_lines == 2

    def test_validate_sources_only_counts_files_not_directories(self):
        """Should only count files, not directories."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["**/*"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock items: files and directories
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.relative_to.return_value = Path("file.txt")
        mock_file.read_text.return_value = "content\n"

        mock_dir = Mock()
        mock_dir.is_file.return_value = False  # It's a directory

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = [mock_file, mock_dir]
            report = validator.validate_sources([source_spec])

        # ASSERT
        assert report.total_files == 1

    def test_validate_sources_accumulates_stats_across_repos(self):
        """Should accumulate file/line/token stats across all repos."""
        # ARRANGE
        mock_repo_manager = Mock()

        def mock_clone(url):
            repo_name = url.split("/")[-1].replace(".git", "")
            return Path(f"/tmp/repos/{repo_name}")

        mock_repo_manager.clone_repo.side_effect = mock_clone

        source_specs = [
            SourceSpec("https://github.com/owner/repo1.git", ["*.py"]),
            SourceSpec("https://github.com/owner/repo2.git", ["*.py"])
        ]

        validator = SourceValidator(mock_repo_manager)

        # Mock 2 files per repo, 100 lines each
        def make_mock_files(count):
            files = []
            for i in range(count):
                mock_file = Mock()
                mock_file.is_file.return_value = True
                mock_file.relative_to.return_value = Path(f"file{i}.py")
                mock_file.read_text.return_value = "\n".join([f"line {j}" for j in range(100)])
                files.append(mock_file)
            return files

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.side_effect = [make_mock_files(2), make_mock_files(3)]
            report = validator.validate_sources(source_specs)

        # ASSERT
        assert report.total_repos == 2
        assert report.successful_repos == 2
        assert report.total_files == 5  # 2 + 3
        assert report.total_lines == 500  # 5 * 100
        # 500 lines * 50 chars/line / 4 chars/token = 6250 tokens
        assert report.estimated_tokens == 6250

    def test_validate_sources_only_accumulates_successful_repos(self):
        """Should only accumulate stats from successful repos."""
        # ARRANGE
        mock_repo_manager = Mock()

        def mock_clone(url):
            if "fail" in url:
                raise Exception("Clone failed")
            repo_name = url.split("/")[-1].replace(".git", "")
            return Path(f"/tmp/repos/{repo_name}")

        mock_repo_manager.clone_repo.side_effect = mock_clone

        source_specs = [
            SourceSpec("https://github.com/owner/success1.git", ["*.py"]),
            SourceSpec("https://github.com/owner/fail.git", ["*.py"]),
            SourceSpec("https://github.com/owner/success2.git", ["*.py"])
        ]

        validator = SourceValidator(mock_repo_manager)

        # Mock 1 file with 10 lines for successful repos
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.relative_to.return_value = Path("file.py")
        mock_file.read_text.return_value = "\n".join([f"line {i}" for i in range(10)])

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = [mock_file]
            report = validator.validate_sources(source_specs)

        # ASSERT
        assert report.total_repos == 3
        assert report.successful_repos == 2
        # Only count files from 2 successful repos
        assert report.total_files == 2
        assert report.total_lines == 20  # 2 * 10

    def test_validate_repo_returns_success_result(self):
        """Should return successful result for valid repository."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.relative_to.return_value = Path("main.py")
        mock_file.read_text.return_value = "line1\nline2\nline3\n"

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = [mock_file]
            result = validator._validate_repo(source_spec)

        # ASSERT
        assert result.success is True
        assert result.repo_name == "test-repo"
        assert result.repo_url == "https://github.com/owner/test-repo.git"
        assert result.error_message is None
        assert result.total_files == 1
        assert result.total_lines == 3
        assert len(result.matched_files) == 1

    def test_validate_repo_returns_failure_result_on_exception(self):
        """Should return failure result when exception occurs."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_manager.clone_repo.side_effect = Exception("Network error")

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # ACT
        result = validator._validate_repo(source_spec)

        # ASSERT
        assert result.success is False
        assert result.repo_name == "test-repo"
        assert result.error_message == "Network error"
        assert result.total_files == 0
        assert result.total_lines == 0
        assert result.matched_files == []

    def test_validate_repo_includes_matched_files_with_line_counts(self):
        """Should include list of matched files with line counts."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock multiple files with different line counts
        mock_files = []
        for name, lines in [("a.py", 10), ("b.py", 20), ("c.py", 15)]:
            mock_file = Mock()
            mock_file.is_file.return_value = True
            mock_file.relative_to.return_value = Path(name)
            mock_file.read_text.return_value = "\n".join([f"line {i}" for i in range(lines)])
            mock_files.append(mock_file)

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = mock_files
            result = validator._validate_repo(source_spec)

        # ASSERT
        assert len(result.matched_files) == 3
        assert result.matched_files[0] == (Path("a.py"), 10)
        assert result.matched_files[1] == (Path("b.py"), 20)
        assert result.matched_files[2] == (Path("c.py"), 15)
        assert result.total_lines == 45

    def test_validate_sources_with_empty_source_list(self):
        """Should handle empty source specifications list."""
        # ARRANGE
        mock_repo_manager = Mock()
        validator = SourceValidator(mock_repo_manager)

        # ACT
        report = validator.validate_sources([])

        # ASSERT
        assert report.total_repos == 0
        assert report.successful_repos == 0
        assert report.is_valid() is True  # No repos = all valid
        assert report.total_files == 0
        assert report.estimated_cost_usd == 0.0

    def test_token_estimation_formula(self):
        """Should use correct token estimation formula."""
        # ARRANGE
        mock_repo_manager = Mock()
        mock_repo_path = Path("/tmp/repos/test-repo")
        mock_repo_manager.clone_repo.return_value = mock_repo_path

        source_spec = SourceSpec(
            url="https://github.com/owner/test-repo.git",
            include=["*.py"]
        )

        validator = SourceValidator(mock_repo_manager)

        # Mock file with exactly 100 lines
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.relative_to.return_value = Path("test.py")
        mock_file.read_text.return_value = "\n".join([f"line {i}" for i in range(100)])

        # ACT
        with patch.object(Path, 'rglob') as mock_rglob:
            mock_rglob.return_value = [mock_file]
            result = validator._validate_repo(source_spec)

        # ASSERT
        # Formula: lines * 50 chars/line / 4 chars/token
        # 100 * 50 / 4 = 1250 tokens
        assert result.total_lines == 100
        assert result.estimated_tokens == 1250

    def test_cost_estimation_formula(self):
        """Should use correct cost estimation formula."""
        # ARRANGE
        mock_repo_manager = Mock()
        validator = SourceValidator(mock_repo_manager)

        # Create report with known token count
        report = ValidationReport(
            repo_results=[],
            total_repos=1,
            successful_repos=1,
            total_files=1,
            total_lines=1000,
            estimated_tokens=10000,  # Known token count
            estimated_cost_usd=(10000 / 1000) * 0.03
        )

        # ASSERT
        # Formula: (tokens / 1000) * $0.03
        # (10000 / 1000) * 0.03 = $0.30
        assert report.estimated_cost_usd == 0.30
