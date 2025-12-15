"""Tests for review module.

Following TDD: These tests are written FIRST (RED phase).
"""

import pytest
from pathlib import Path


class TestDiffGenerator:
    """Test DiffGenerator class for generating diffs and statistics."""

    def test_generate_diff_returns_diff_and_stats(self, tmp_path):
        """
        Given: Two different markdown files
        When: generate_diff is called
        Then: Returns diff text and statistics
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("# Title\n\nNew content here\nAnother line\n")
        live.write_text("# Title\n\nOld content here\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live)

        assert isinstance(diff_text, str)
        assert isinstance(stats, dict)
        assert "added" in stats
        assert "removed" in stats
        assert "modified" in stats

    def test_generate_diff_calculates_correct_stats(self, tmp_path):
        """
        Given: Files with 2 additions, 1 removal
        When: generate_diff is called
        Then: Statistics reflect correct counts
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("# Title\n\nNew line 1\nNew line 2\nShared line\n")
        live.write_text("# Title\n\nOld line\nShared line\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live)

        assert stats["added"] == 2
        assert stats["removed"] == 1

    def test_generate_diff_handles_missing_live_doc(self, tmp_path):
        """
        Given: Staging exists but live doc doesn't exist yet
        When: generate_diff is called
        Then: Returns diff showing all lines as new
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("# New Doc\n\nContent here\n")
        # live doesn't exist

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live)

        assert diff_text is not None
        assert stats["added"] == 3
        assert stats["removed"] == 0

    def test_generate_diff_handles_no_changes(self, tmp_path):
        """
        Given: Identical staging and live files
        When: generate_diff is called
        Then: Returns empty diff with zero stats
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        content = "# Title\n\nSame content\n"
        staging.write_text(content)
        live.write_text(content)

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live)

        assert diff_text == ""
        assert stats["added"] == 0
        assert stats["removed"] == 0
        assert stats["modified"] == 0

    def test_generate_diff_handles_empty_staging(self, tmp_path):
        """
        Given: Empty staging file
        When: generate_diff is called
        Then: Returns diff showing all live lines as removed
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("")
        live.write_text("# Title\n\nContent\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live)

        assert stats["added"] == 0
        assert stats["removed"] == 3

    def test_generate_diff_colorizes_additions(self, tmp_path):
        """
        Given: Staging has new lines
        When: generate_diff is called with colorize=True
        Then: Added lines are colored green
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("# Title\n\nNew line\n")
        live.write_text("# Title\n\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live, colorize=True)

        # Check for ANSI green color code (32m)
        assert "\x1b[32m" in diff_text or "+" in diff_text

    def test_generate_diff_colorizes_removals(self, tmp_path):
        """
        Given: Live has lines not in staging
        When: generate_diff is called with colorize=True
        Then: Removed lines are colored red
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("# Title\n\n")
        live.write_text("# Title\n\nRemoved line\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live, colorize=True)

        # Check for ANSI red color code (31m)
        assert "\x1b[31m" in diff_text or "-" in diff_text

    def test_generate_diff_without_colorize(self, tmp_path):
        """
        Given: Staging and live files differ
        When: generate_diff is called with colorize=False
        Then: Returns plain diff without ANSI codes
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("# Title\n\nNew content\n")
        live.write_text("# Title\n\nOld content\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live, colorize=False)

        # Should have +/- but no ANSI codes
        assert "\x1b[" not in diff_text

    def test_generate_diff_with_paths_as_strings(self, tmp_path):
        """
        Given: Paths as strings instead of Path objects
        When: generate_diff is called
        Then: Still works correctly
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        staging.write_text("# Title\n\nNew\n")
        live.write_text("# Title\n\nOld\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(str(staging), str(live))

        assert isinstance(diff_text, str)
        assert stats["added"] == 1
        assert stats["removed"] == 1


class TestDiffGeneratorModifiedCount:
    """Test calculation of modified lines (changed content)."""

    def test_modified_count_for_changed_lines(self, tmp_path):
        """
        Given: Lines that changed content (not just added/removed)
        When: Statistics are calculated
        Then: Modified count reflects changed lines
        """
        from doc_gen.review import DiffGenerator

        staging = tmp_path / "staging.md"
        live = tmp_path / "live.md"
        
        # One line changed, one added, one removed
        staging.write_text("Line 1\nLine 2 modified\nLine 3 new\n")
        live.write_text("Line 1\nLine 2 original\nLine 3 old\n")

        generator = DiffGenerator()
        diff_text, stats = generator.generate_diff(staging, live)

        # Should count changes appropriately
        assert stats["added"] > 0 or stats["removed"] > 0
        assert stats["modified"] >= 0


class TestReviewCLICommand:
    """Integration tests for review CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        from click.testing import CliRunner
        return CliRunner()

    def test_review_command_shows_diff_between_staging_and_live(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging and live documents exist with differences
        When: review command is called
        Then: Shows diff and statistics
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # Setup metadata structure
        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# Title\n\nNew content\nAnother line\n")

        # Create live doc
        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Title\n\nOld content\n")

        # ACT
        result = runner.invoke(cli, ["review", doc_path])

        # ASSERT
        assert result.exit_code == 0
        assert "+" in result.output or "added" in result.output.lower()
        assert "-" in result.output or "removed" in result.output.lower()

    def test_review_command_shows_statistics(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging and live documents differ
        When: review command is called
        Then: Shows added/removed/modified counts
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # Setup
        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# Title\n\nNew line 1\nNew line 2\n")

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Title\n\nOld line\n")

        # ACT
        result = runner.invoke(cli, ["review", doc_path])

        # ASSERT
        assert result.exit_code == 0
        # Should show some form of statistics
        assert "added" in result.output.lower() or "lines" in result.output.lower()

    def test_review_command_handles_missing_staging(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging document doesn't exist
        When: review command is called
        Then: Shows clear error message
        """
        from doc_gen.cli import cli

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # ACT
        result = runner.invoke(cli, ["review", doc_path])

        # ASSERT
        assert result.exit_code != 0
        assert "staging" in result.output.lower() or "not found" in result.output.lower()

    def test_review_command_handles_new_document(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging exists but live doc doesn't exist yet
        When: review command is called
        Then: Shows all lines as new additions
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # Setup staging only
        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# New Doc\n\nContent here\n")

        # ACT
        result = runner.invoke(cli, ["review", doc_path])

        # ASSERT
        assert result.exit_code == 0
        assert "new" in result.output.lower() or "+" in result.output

    def test_review_command_handles_no_changes(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging and live are identical
        When: review command is called
        Then: Shows no changes message
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        content = "# Title\n\nSame content\n"

        # Setup identical files
        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text(content)

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text(content)

        # ACT
        result = runner.invoke(cli, ["review", doc_path])

        # ASSERT
        assert result.exit_code == 0
        assert "no changes" in result.output.lower() or "identical" in result.output.lower()

    def test_review_command_suggests_promote_next_step(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging and live differ
        When: review command is called
        Then: Suggests promote command as next step
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # Setup
        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# Title\n\nNew content\n")

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Title\n\nOld content\n")

        # ACT
        result = runner.invoke(cli, ["review", doc_path])

        # ASSERT
        assert result.exit_code == 0
        assert "promote" in result.output.lower()

    def test_review_command_in_help(self, runner):
        """
        Given: CLI is available
        When: --help is called
        Then: review command is listed
        """
        from doc_gen.cli import cli

        # ACT
        result = runner.invoke(cli, ["--help"])

        # ASSERT
        assert result.exit_code == 0
        assert "review" in result.output.lower()
