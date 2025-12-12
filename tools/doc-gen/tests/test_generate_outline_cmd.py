"""Tests for generate-outline CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from doc_gen.cli import cli


class TestGenerateOutlineCommand:
    """Test generate-outline CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_generate_outline_command_exists(self, runner):
        """generate-outline command should exist."""
        # ACT
        result = runner.invoke(cli, ["generate-outline", "--help"])

        # ASSERT
        assert result.exit_code == 0
        assert "generate-outline" in result.output.lower()

    @patch('doc_gen.cli.RepoManager')
    @patch('doc_gen.cli.OpenAIClient')
    @patch('doc_gen.cli.OutlineGenerator')
    def test_generate_outline_loads_sources(
        self, mock_generator_class, mock_client_class, mock_repo_mgr_class, runner, tmp_path, monkeypatch
    ):
        """generate-outline should load sources from metadata."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        
        # Create config
        config_dir = tmp_path / ".doc-gen"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("llm:\n  provider: openai\n  model: gpt-4\n")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Create sources
        from doc_gen.metadata import MetadataManager
        metadata = MetadataManager("docs/test.md")
        metadata.init_sources()

        # Mock repo manager
        mock_repo_mgr = Mock()
        mock_repo_mgr.__enter__ = Mock(return_value=mock_repo_mgr)
        mock_repo_mgr.__exit__ = Mock(return_value=None)
        mock_repo_mgr.clone_repo.return_value = tmp_path / "repo"
        mock_repo_mgr.list_files.return_value = [Path("test.py")]
        mock_repo_mgr.get_file_commit_hash.return_value = "abc123"
        mock_repo_mgr_class.return_value = mock_repo_mgr

        # Create test file
        (tmp_path / "repo").mkdir()
        (tmp_path / "repo" / "test.py").write_text("print('hello')")

        # Mock generator
        mock_generator = Mock()
        mock_outline = {
            "title": "Test",
            "sections": [],
            "_metadata": {"model": "gpt-4", "tokens_used": 100, "duration_seconds": 1.0}
        }
        mock_generator.generate_outline.return_value = mock_outline
        mock_generator_class.return_value = mock_generator

        # ACT
        result = runner.invoke(cli, ["generate-outline", "docs/test.md"])

        # ASSERT
        assert result.exit_code == 0
        assert "✓" in result.output
        # Should have called generate_outline
        mock_generator.generate_outline.assert_called_once()

    @patch('doc_gen.cli.RepoManager')
    @patch('doc_gen.cli.OpenAIClient')
    @patch('doc_gen.cli.OutlineGenerator')
    def test_generate_outline_clones_repository(
        self, mock_generator_class, mock_client_class, mock_repo_mgr_class, runner, tmp_path, monkeypatch
    ):
        """generate-outline should clone repository from sources."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        
        config_dir = tmp_path / ".doc-gen"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("llm:\n  provider: openai\n")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from doc_gen.metadata import MetadataManager
        metadata = MetadataManager("docs/test.md")
        metadata.init_sources()

        mock_repo_mgr = Mock()
        mock_repo_mgr.__enter__ = Mock(return_value=mock_repo_mgr)
        mock_repo_mgr.__exit__ = Mock(return_value=None)
        mock_repo_mgr.clone_repo.return_value = tmp_path / "repo"
        mock_repo_mgr.list_files.return_value = []
        mock_repo_mgr_class.return_value = mock_repo_mgr

        mock_generator = Mock()
        mock_generator.generate_outline.return_value = {
            "title": "Test",
            "sections": [],
            "_metadata": {"model": "gpt-4", "tokens_used": 100, "duration_seconds": 1.0}
        }
        mock_generator_class.return_value = mock_generator

        # ACT
        result = runner.invoke(cli, ["generate-outline", "docs/test.md"])

        # ASSERT
        mock_repo_mgr.clone_repo.assert_called_once()

    @patch('doc_gen.cli.RepoManager')
    @patch('doc_gen.cli.OpenAIClient')
    @patch('doc_gen.cli.OutlineGenerator')
    def test_generate_outline_saves_outline(
        self, mock_generator_class, mock_client_class, mock_repo_mgr_class, runner, tmp_path, monkeypatch
    ):
        """generate-outline should save outline to metadata."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        
        config_dir = tmp_path / ".doc-gen"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("llm:\n  provider: openai\n")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from doc_gen.metadata import MetadataManager
        metadata = MetadataManager("docs/test.md")
        metadata.init_sources()

        mock_repo_mgr = Mock()
        mock_repo_mgr.__enter__ = Mock(return_value=mock_repo_mgr)
        mock_repo_mgr.__exit__ = Mock(return_value=None)
        mock_repo_mgr.clone_repo.return_value = tmp_path / "repo"
        mock_repo_mgr.list_files.return_value = []
        mock_repo_mgr_class.return_value = mock_repo_mgr

        mock_generator = Mock()
        mock_outline = {
            "title": "Test Outline",
            "sections": [],
            "_metadata": {"model": "gpt-4", "tokens_used": 100, "duration_seconds": 1.0}
        }
        mock_generator.generate_outline.return_value = mock_outline
        mock_generator_class.return_value = mock_generator

        # ACT
        result = runner.invoke(cli, ["generate-outline", "docs/test.md"])

        # ASSERT
        assert result.exit_code == 0
        # Outline should be saved
        outline_path = tmp_path / ".doc-gen/metadata/docs/test/outline.json"
        assert outline_path.exists()

    def test_generate_outline_handles_missing_sources(self, runner, tmp_path, monkeypatch):
        """generate-outline should error if sources not initialized."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        
        config_dir = tmp_path / ".doc-gen"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("llm:\n  provider: openai\n")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # ACT - No sources initialized
        result = runner.invoke(cli, ["generate-outline", "docs/test.md"])

        # ASSERT
        assert result.exit_code == 1
        assert "Sources not found" in result.output or "Error" in result.output

    @patch('doc_gen.cli.RepoManager')
    @patch('doc_gen.cli.OpenAIClient')
    @patch('doc_gen.cli.OutlineGenerator')
    def test_generate_outline_reports_metadata(
        self, mock_generator_class, mock_client_class, mock_repo_mgr_class, runner, tmp_path, monkeypatch
    ):
        """generate-outline should report tokens and duration."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        
        config_dir = tmp_path / ".doc-gen"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("llm:\n  provider: openai\n")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from doc_gen.metadata import MetadataManager
        metadata = MetadataManager("docs/test.md")
        metadata.init_sources()

        mock_repo_mgr = Mock()
        mock_repo_mgr.__enter__ = Mock(return_value=mock_repo_mgr)
        mock_repo_mgr.__exit__ = Mock(return_value=None)
        mock_repo_mgr.clone_repo.return_value = tmp_path / "repo"
        mock_repo_mgr.list_files.return_value = []
        mock_repo_mgr_class.return_value = mock_repo_mgr

        mock_generator = Mock()
        mock_outline = {
            "title": "Test",
            "sections": [],
            "_metadata": {
                "model": "gpt-4-turbo",
                "tokens_used": 2500,
                "duration_seconds": 3.8
            }
        }
        mock_generator.generate_outline.return_value = mock_outline
        mock_generator_class.return_value = mock_generator

        # ACT
        result = runner.invoke(cli, ["generate-outline", "docs/test.md"])

        # ASSERT
        assert result.exit_code == 0
        assert "Tokens" in result.output or "2500" in result.output
        assert "Model" in result.output or "gpt-4" in result.output
