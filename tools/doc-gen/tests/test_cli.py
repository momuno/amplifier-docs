"""Tests for CLI commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from doc_gen.cli import cli


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

    def test_generate_outline_shows_coming_soon(self, runner, tmp_path, monkeypatch):
        """generate-outline command should show Sprint 2 message."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)

        # ACT
        result = runner.invoke(cli, ["generate-outline", "docs/test.md"])

        # ASSERT
        assert result.exit_code == 0
        assert "Sprint 2" in result.output

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
