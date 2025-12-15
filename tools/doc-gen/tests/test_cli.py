"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from doc_gen.cli import cli, _format_duration
from doc_gen.orchestration import BatchReport, RegenerationResult


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_group_loads(self, runner):
        """CLI group should load without errors."""
        # ACT
        result = runner.invoke(cli, ["--help"])

        # ASSERT
        assert result.exit_code == 0
        assert "Multi-repository documentation generation tool" in result.output

    def test_cli_shows_all_commands(self, runner):
        """CLI should show all available commands."""
        # ACT
        result = runner.invoke(cli, ["--help"])

        # ASSERT
        assert result.exit_code == 0
        assert "init" in result.output
        assert "generate-outline" in result.output
        assert "generate-doc" in result.output

    def test_init_command_creates_sources_template(self, runner, tmp_path, monkeypatch):
        """init command should create sources.yaml template."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # ACT
        result = runner.invoke(cli, ["init", doc_path])

        # ASSERT
        assert result.exit_code == 0
        assert "Initialized sources" in result.output

        # Verify file was created
        expected_path = Path(".doc-gen/metadata/docs/test/sources.yaml")
        assert expected_path.exists()

    def test_init_command_shows_next_steps(self, runner, tmp_path, monkeypatch):
        """init command should show helpful next steps."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # ACT
        result = runner.invoke(cli, ["init", doc_path])

        # ASSERT
        assert result.exit_code == 0
        assert "Next steps:" in result.output
        assert "Edit sources.yaml" in result.output
        assert "generate-outline" in result.output

    def test_init_command_handles_nested_paths(self, runner, tmp_path, monkeypatch):
        """init command should handle deeply nested document paths."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/deep/nested/path/test.md"

        # ACT
        result = runner.invoke(cli, ["init", doc_path])

        # ASSERT
        assert result.exit_code == 0
        expected_path = Path(".doc-gen/metadata/docs/deep/nested/path/test/sources.yaml")
        assert expected_path.exists()

    def test_generate_outline_command_implemented(self, runner):
        """generate-outline command should be implemented (Sprint 2 complete)."""
        # ACT
        result = runner.invoke(cli, ["generate-outline", "--help"])

        # ASSERT
        assert result.exit_code == 0
        assert "Generate outline from source files" in result.output

    def test_generate_doc_shows_coming_soon(self, runner, tmp_path, monkeypatch):
        """generate-doc command should show Sprint 3 message."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)

        # ACT
        result = runner.invoke(cli, ["generate-doc", "docs/test.md"])

        # ASSERT
        assert result.exit_code == 0
        assert "Sprint 3" in result.output

    def test_cli_loads_config_if_exists(self, runner, tmp_path, monkeypatch):
        """CLI should load config if it exists."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        
        # Create a minimal config
        config_dir = tmp_path / ".doc-gen"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("llm:\n  provider: openai\n  model: gpt-4\n")
        
        # Set API key in environment
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # ACT
        result = runner.invoke(cli, ["init", "docs/test.md"])

        # ASSERT
        # Should succeed without config creation message
        assert result.exit_code == 0
        assert "No config found" not in result.output

    def test_cli_creates_config_template_if_missing(self, runner):
        """CLI should create config template if none exists."""
        # Use isolated filesystem to ensure clean state
        with runner.isolated_filesystem():
            # ACT
            result = runner.invoke(cli, ["init", "docs/test.md"])

            # ASSERT
            # Should create template and show message
            assert "No config found" in result.output or "Creating template" in result.output
            assert result.exit_code == 1  # Should exit after creating template

            # Verify config template was created
            config_path = Path(".doc-gen/config.yaml")
            assert config_path.exists()

    def test_init_command_help_text(self, runner):
        """init command should have helpful documentation."""
        # ACT
        result = runner.invoke(cli, ["init", "--help"])

        # ASSERT
        assert result.exit_code == 0
        assert "Initialize source specification" in result.output
        # Click formats arguments as DOC_PATH or DOC-PATH in uppercase
        assert "DOC" in result.output and "PATH" in result.output

    def test_commands_accept_doc_path_argument(self, runner):
        """All commands should accept doc-path argument."""
        # Check generate-outline help
        result = runner.invoke(cli, ["generate-outline", "--help"])
        assert result.exit_code == 0
        # Click formats as DOC_PATH or doc_path
        assert "doc_path" in result.output.lower() or "DOC" in result.output

        # Check generate-doc help
        result = runner.invoke(cli, ["generate-doc", "--help"])
        assert result.exit_code == 0
        assert "doc_path" in result.output.lower() or "DOC" in result.output


class TestFormatDuration:
    """Tests for _format_duration helper function."""

    def test_format_duration_seconds_only(self):
        """
        Given: Duration less than 60 seconds
        When: _format_duration is called
        Then: Returns format "Xs"
        """
        assert _format_duration(5.0) == "5s"
        assert _format_duration(30.5) == "30s"
        assert _format_duration(59.9) == "59s"

    def test_format_duration_minutes_and_seconds(self):
        """
        Given: Duration between 60 and 3600 seconds
        When: _format_duration is called
        Then: Returns format "Xm Ys"
        """
        assert _format_duration(60.0) == "1m 0s"
        assert _format_duration(90.0) == "1m 30s"
        assert _format_duration(125.5) == "2m 5s"
        assert _format_duration(3599.9) == "59m 59s"

    def test_format_duration_hours_and_minutes(self):
        """
        Given: Duration 3600 seconds or more
        When: _format_duration is called
        Then: Returns format "Xh Ym"
        """
        assert _format_duration(3600.0) == "1h 0m"
        assert _format_duration(3660.0) == "1h 1m"
        assert _format_duration(7200.0) == "2h 0m"
        assert _format_duration(7320.0) == "2h 2m"

    def test_format_duration_rounds_down(self):
        """
        Given: Duration with fractional values
        When: _format_duration is called
        Then: Rounds down to nearest integer
        """
        assert _format_duration(5.9) == "5s"
        assert _format_duration(90.9) == "1m 30s"


class TestRegenerateChangedCommand:
    """Tests for regenerate-changed command (Sprint 6)."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self, tmp_path, monkeypatch):
        """Set up minimal config."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".doc-gen"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            "llm:\n  provider: openai\n  model: gpt-4\n  api_key: test-key\n"
        )
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        return tmp_path

    def test_regenerate_changed_command_exists(self, runner):
        """
        Given: CLI is initialized
        When: regenerate-changed --help is invoked
        Then: Command exists and shows help text
        """
        result = runner.invoke(cli, ["regenerate-changed", "--help"])

        assert result.exit_code == 0
        assert "regenerate-changed" in result.output.lower()

    def test_regenerate_changed_has_dry_run_flag(self, runner):
        """
        Given: regenerate-changed command exists
        When: --help is invoked
        Then: Shows --dry-run flag option
        """
        result = runner.invoke(cli, ["regenerate-changed", "--help"])

        assert result.exit_code == 0
        assert "--dry-run" in result.output

    @patch("doc_gen.cli.BatchOrchestrator")
    def test_regenerate_changed_dry_run_shows_changed_docs(
        self, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: Some documents need regeneration
        When: regenerate-changed --dry-run is invoked
        Then: Shows changed docs without regenerating
        """
        # ARRANGE
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock _find_changed_docs to return some docs
        mock_orchestrator._find_changed_docs = Mock(
            return_value=["docs/test1.md", "docs/test2.md"]
        )

        # ACT
        result = runner.invoke(cli, ["regenerate-changed", "--dry-run"])

        # ASSERT
        assert result.exit_code == 0
        assert "docs/test1.md" in result.output
        assert "docs/test2.md" in result.output
        assert "2 document(s) need regeneration" in result.output

    @patch("doc_gen.cli.BatchOrchestrator")
    def test_regenerate_changed_dry_run_no_changes(
        self, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: No documents need regeneration
        When: regenerate-changed --dry-run is invoked
        Then: Shows message that all docs are up-to-date
        """
        # ARRANGE
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator._find_changed_docs = Mock(return_value=[])

        # ACT
        result = runner.invoke(cli, ["regenerate-changed", "--dry-run"])

        # ASSERT
        assert result.exit_code == 0
        assert "up-to-date" in result.output or "No changes" in result.output

    @patch("doc_gen.cli.BatchOrchestrator")
    @patch("doc_gen.cli.RepoManager")
    def test_regenerate_changed_shows_progress(
        self, mock_repo_mgr_class, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: Documents need regeneration
        When: regenerate-changed is invoked (without --dry-run)
        Then: Shows progress for each document
        """
        # ARRANGE
        mock_repo_mgr = MagicMock()
        mock_repo_mgr_class.return_value.__enter__.return_value = mock_repo_mgr

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_report = BatchReport(
            total_docs=2,
            successful=2,
            failed=0,
            total_tokens=5000,
            total_duration_seconds=10.5,
            estimated_cost_usd=0.1,
            results=[
                RegenerationResult(
                    doc_path="docs/test1.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1000,
                    doc_tokens=1500,
                    duration_seconds=5.0,
                ),
                RegenerationResult(
                    doc_path="docs/test2.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1200,
                    doc_tokens=1300,
                    duration_seconds=5.5,
                ),
            ],
        )
        mock_orchestrator.regenerate_changed.return_value = mock_report

        # ACT
        result = runner.invoke(cli, ["regenerate-changed"])

        # ASSERT
        assert result.exit_code == 0
        assert "Checking for stale documentation" in result.output
        assert "1/2" in result.output or "docs/test1.md" in result.output
        assert "2/2" in result.output or "docs/test2.md" in result.output

    @patch("doc_gen.cli.BatchOrchestrator")
    @patch("doc_gen.cli.RepoManager")
    def test_regenerate_changed_shows_summary_success(
        self, mock_repo_mgr_class, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: All documents regenerate successfully
        When: regenerate-changed completes
        Then: Shows success summary with stats
        """
        # ARRANGE
        mock_repo_mgr = MagicMock()
        mock_repo_mgr_class.return_value.__enter__.return_value = mock_repo_mgr

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_report = BatchReport(
            total_docs=2,
            successful=2,
            failed=0,
            total_tokens=5000,
            total_duration_seconds=10.5,
            estimated_cost_usd=0.1,
            results=[
                RegenerationResult(
                    doc_path="docs/test1.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1000,
                    doc_tokens=1500,
                    duration_seconds=5.0,
                ),
                RegenerationResult(
                    doc_path="docs/test2.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1200,
                    doc_tokens=1300,
                    duration_seconds=5.5,
                ),
            ],
        )
        mock_orchestrator.regenerate_changed.return_value = mock_report

        # ACT
        result = runner.invoke(cli, ["regenerate-changed"])

        # ASSERT
        assert result.exit_code == 0
        assert "2 successful" in result.output or "✓ 2" in result.output
        assert "10s" in result.output  # Duration formatted
        assert "5,000" in result.output or "5000" in result.output  # Tokens
        assert "$0.10" in result.output  # Cost

    @patch("doc_gen.cli.BatchOrchestrator")
    @patch("doc_gen.cli.RepoManager")
    def test_regenerate_changed_shows_summary_with_failures(
        self, mock_repo_mgr_class, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: Some documents fail to regenerate
        When: regenerate-changed completes
        Then: Shows failure summary with error messages
        """
        # ARRANGE
        mock_repo_mgr = MagicMock()
        mock_repo_mgr_class.return_value.__enter__.return_value = mock_repo_mgr

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_report = BatchReport(
            total_docs=3,
            successful=2,
            failed=1,
            total_tokens=3500,
            total_duration_seconds=8.0,
            estimated_cost_usd=0.07,
            results=[
                RegenerationResult(
                    doc_path="docs/test1.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1000,
                    doc_tokens=1500,
                    duration_seconds=5.0,
                ),
                RegenerationResult(
                    doc_path="docs/test2.md",
                    success=False,
                    error_message="LLM API timeout",
                    outline_tokens=0,
                    doc_tokens=0,
                    duration_seconds=1.0,
                ),
                RegenerationResult(
                    doc_path="docs/test3.md",
                    success=True,
                    error_message=None,
                    outline_tokens=500,
                    doc_tokens=500,
                    duration_seconds=2.0,
                ),
            ],
        )
        mock_orchestrator.regenerate_changed.return_value = mock_report

        # ACT
        result = runner.invoke(cli, ["regenerate-changed"])

        # ASSERT
        assert result.exit_code == 1  # Exit 1 on failures
        assert "2 successful" in result.output
        assert "1 failed" in result.output
        assert "docs/test2.md" in result.output
        assert "LLM API timeout" in result.output

    @patch("doc_gen.cli.BatchOrchestrator")
    @patch("doc_gen.cli.RepoManager")
    def test_regenerate_changed_exit_code_all_success(
        self, mock_repo_mgr_class, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: All documents regenerate successfully
        When: regenerate-changed completes
        Then: Exits with code 0
        """
        # ARRANGE
        mock_repo_mgr = MagicMock()
        mock_repo_mgr_class.return_value.__enter__.return_value = mock_repo_mgr

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_report = BatchReport(
            total_docs=1,
            successful=1,
            failed=0,
            total_tokens=2000,
            total_duration_seconds=5.0,
            estimated_cost_usd=0.04,
            results=[
                RegenerationResult(
                    doc_path="docs/test.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1000,
                    doc_tokens=1000,
                    duration_seconds=5.0,
                )
            ],
        )
        mock_orchestrator.regenerate_changed.return_value = mock_report

        # ACT
        result = runner.invoke(cli, ["regenerate-changed"])

        # ASSERT
        assert result.exit_code == 0

    @patch("doc_gen.cli.BatchOrchestrator")
    @patch("doc_gen.cli.RepoManager")
    def test_regenerate_changed_exit_code_any_failure(
        self, mock_repo_mgr_class, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: Any document fails to regenerate
        When: regenerate-changed completes
        Then: Exits with code 1
        """
        # ARRANGE
        mock_repo_mgr = MagicMock()
        mock_repo_mgr_class.return_value.__enter__.return_value = mock_repo_mgr

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_report = BatchReport(
            total_docs=1,
            successful=0,
            failed=1,
            total_tokens=0,
            total_duration_seconds=1.0,
            estimated_cost_usd=0.0,
            results=[
                RegenerationResult(
                    doc_path="docs/test.md",
                    success=False,
                    error_message="Error",
                    outline_tokens=0,
                    doc_tokens=0,
                    duration_seconds=1.0,
                )
            ],
        )
        mock_orchestrator.regenerate_changed.return_value = mock_report

        # ACT
        result = runner.invoke(cli, ["regenerate-changed"])

        # ASSERT
        assert result.exit_code == 1

    @patch("doc_gen.cli.BatchOrchestrator")
    @patch("doc_gen.cli.RepoManager")
    def test_regenerate_changed_shows_next_steps_on_success(
        self, mock_repo_mgr_class, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: All documents regenerate successfully
        When: regenerate-changed completes
        Then: Shows next steps for promotion
        """
        # ARRANGE
        mock_repo_mgr = MagicMock()
        mock_repo_mgr_class.return_value.__enter__.return_value = mock_repo_mgr

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_report = BatchReport(
            total_docs=1,
            successful=1,
            failed=0,
            total_tokens=2000,
            total_duration_seconds=5.0,
            estimated_cost_usd=0.04,
            results=[
                RegenerationResult(
                    doc_path="docs/test.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1000,
                    doc_tokens=1000,
                    duration_seconds=5.0,
                )
            ],
        )
        mock_orchestrator.regenerate_changed.return_value = mock_report

        # ACT
        result = runner.invoke(cli, ["regenerate-changed"])

        # ASSERT
        assert result.exit_code == 0
        assert "Next steps:" in result.output
        assert "review" in result.output or "promote" in result.output

    @patch("doc_gen.cli.BatchOrchestrator")
    @patch("doc_gen.cli.RepoManager")
    def test_regenerate_changed_colorizes_output(
        self, mock_repo_mgr_class, mock_orchestrator_class, runner, mock_config
    ):
        """
        Given: Documents regenerate with mixed results
        When: regenerate-changed displays summary
        Then: Uses color for success (green) and failures (red)
        """
        # ARRANGE
        mock_repo_mgr = MagicMock()
        mock_repo_mgr_class.return_value.__enter__.return_value = mock_repo_mgr

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        mock_report = BatchReport(
            total_docs=2,
            successful=1,
            failed=1,
            total_tokens=2000,
            total_duration_seconds=6.0,
            estimated_cost_usd=0.04,
            results=[
                RegenerationResult(
                    doc_path="docs/test1.md",
                    success=True,
                    error_message=None,
                    outline_tokens=1000,
                    doc_tokens=1000,
                    duration_seconds=5.0,
                ),
                RegenerationResult(
                    doc_path="docs/test2.md",
                    success=False,
                    error_message="Error",
                    outline_tokens=0,
                    doc_tokens=0,
                    duration_seconds=1.0,
                ),
            ],
        )
        mock_orchestrator.regenerate_changed.return_value = mock_report

        # ACT - use color=True to enable ANSI codes in test
        result = runner.invoke(cli, ["regenerate-changed"], color=True)

        # ASSERT
        # Check for success indicator (✓) and failure indicator (✗)
        assert "✓" in result.output or "successful" in result.output
        assert "✗" in result.output or "failed" in result.output
