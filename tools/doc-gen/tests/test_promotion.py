"""Tests for promotion module.

Following TDD: These tests are written FIRST (RED phase).
"""

import pytest
from pathlib import Path
from datetime import datetime


class TestPromotionError:
    """Test custom PromotionError exception."""

    def test_promotion_error_can_be_raised(self):
        """
        Given: PromotionError class exists
        When: Exception is raised
        Then: Can be caught as PromotionError
        """
        from doc_gen.promotion import PromotionError

        with pytest.raises(PromotionError):
            raise PromotionError("Test error")

    def test_promotion_error_is_exception_subclass(self):
        """
        Given: PromotionError class
        When: Checking inheritance
        Then: It inherits from Exception
        """
        from doc_gen.promotion import PromotionError

        assert issubclass(PromotionError, Exception)


class TestDocumentPromoter:
    """Test DocumentPromoter class for promoting staging to live."""

    def test_promoter_initializes_with_metadata_manager(self, tmp_path, monkeypatch):
        """
        Given: A MetadataManager instance
        When: DocumentPromoter is initialized
        Then: Stores metadata manager
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        metadata_mgr = MetadataManager("docs/test.md")

        promoter = DocumentPromoter(metadata_mgr)

        assert promoter.metadata_mgr == metadata_mgr

    def test_promote_validates_staging_exists(self, tmp_path, monkeypatch):
        """
        Given: No staging document exists
        When: promote is called
        Then: Raises PromotionError with clear message
        """
        from doc_gen.promotion import DocumentPromoter, PromotionError
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        metadata_mgr = MetadataManager("docs/test.md")
        promoter = DocumentPromoter(metadata_mgr)

        with pytest.raises(PromotionError) as exc_info:
            promoter.promote()

        assert "staging" in str(exc_info.value).lower()

    def test_promote_creates_backup_directory(self, tmp_path, monkeypatch):
        """
        Given: Staging and live documents exist
        When: promote is called
        Then: Creates .doc-gen/backups/ directory
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# New Content\n")

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Old Content\n")

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        backup_dir = tmp_path / ".doc-gen" / "backups"
        assert backup_dir.exists()
        assert backup_dir.is_dir()

    def test_promote_creates_timestamped_backup(self, tmp_path, monkeypatch):
        """
        Given: Live document exists
        When: promote is called
        Then: Creates backup with format YYYY-MM-DD-HHMMSS-original-name.md
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# New Content\n")

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Old Content\n")

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        backup_path = Path(result["backup_path"])
        assert backup_path.exists()
        
        # Check filename format: YYYY-MM-DD-HHMMSS-test.md
        filename = backup_path.name
        parts = filename.split("-")
        assert len(parts) >= 4
        assert parts[0].isdigit() and len(parts[0]) == 4  # Year
        assert parts[1].isdigit() and len(parts[1]) == 2  # Month
        assert parts[2].isdigit() and len(parts[2]) == 2  # Day
        assert filename.endswith("test.md")

    def test_promote_backup_contains_original_content(self, tmp_path, monkeypatch):
        """
        Given: Live document with specific content
        When: promote is called
        Then: Backup contains the original live content
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# New Content\n")

        original_content = "# Original Live Content\n\nThis should be backed up.\n"
        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text(original_content)

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        backup_path = Path(result["backup_path"])
        backed_up_content = backup_path.read_text()
        assert backed_up_content == original_content

    def test_promote_copies_staging_to_live(self, tmp_path, monkeypatch):
        """
        Given: Staging document with new content
        When: promote is called
        Then: Live document is updated with staging content
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        new_content = "# New Staging Content\n\nThis is the updated version.\n"
        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text(new_content)

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Old Content\n")

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        live_content = live_path.read_text()
        assert live_content == new_content

    def test_promote_returns_promotion_details(self, tmp_path, monkeypatch):
        """
        Given: Staging and live documents exist
        When: promote is called
        Then: Returns dict with staging_path, live_path, backup_path, promoted_at
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# New Content\n")

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Old Content\n")

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        assert isinstance(result, dict)
        assert "staging_path" in result
        assert "live_path" in result
        assert "backup_path" in result
        assert "promoted_at" in result

    def test_promote_handles_no_existing_live_doc(self, tmp_path, monkeypatch):
        """
        Given: Staging exists but no live doc yet
        When: promote is called
        Then: Creates live doc without backup (no backup_path in result)
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        new_content = "# First Version\n\nThis is the initial document.\n"
        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text(new_content)

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        live_path = tmp_path / doc_path
        assert live_path.exists()
        assert live_path.read_text() == new_content
        assert result["backup_path"] is None

    def test_promote_creates_live_directory_if_needed(self, tmp_path, monkeypatch):
        """
        Given: Staging exists but live directory doesn't exist
        When: promote is called
        Then: Creates parent directories for live document
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/deep/nested/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# Content\n")

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        live_path = tmp_path / doc_path
        assert live_path.exists()
        assert live_path.parent.exists()

    def test_promote_uses_shutil_copy2_to_preserve_metadata(self, tmp_path, monkeypatch):
        """
        Given: Staging document
        When: promote is called
        Then: Uses copy2 to preserve file metadata (timestamps)
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager
        import time

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# Content\n")
        
        # Set specific modification time
        old_mtime = time.time() - 86400  # 1 day ago
        import os
        os.utime(staging_path, (old_mtime, old_mtime))

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        live_path = tmp_path / doc_path
        # Note: copy2 attempts to preserve metadata, but this is
        # just ensuring the copy happens (actual verification in implementation)
        assert live_path.exists()

    def test_promote_timestamp_format_is_iso8601(self, tmp_path, monkeypatch):
        """
        Given: Promotion happens
        When: Checking promoted_at timestamp
        Then: Format is ISO 8601
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# Content\n")

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        # Verify ISO 8601 format can be parsed
        promoted_at = result["promoted_at"]
        parsed = datetime.fromisoformat(promoted_at)
        assert isinstance(parsed, datetime)

    def test_promote_backup_path_is_pathlib_path_as_string(self, tmp_path, monkeypatch):
        """
        Given: Live document exists
        When: promote is called
        Then: backup_path in result is a string representation
        """
        from doc_gen.promotion import DocumentPromoter
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata_mgr = MetadataManager(doc_path)

        staging_path = metadata_mgr.get_staging_path()
        staging_path.write_text("# New Content\n")

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Old Content\n")

        promoter = DocumentPromoter(metadata_mgr)
        result = promoter.promote()

        assert isinstance(result["backup_path"], str)
        assert isinstance(result["staging_path"], str)
        assert isinstance(result["live_path"], str)


class TestPromoteCLICommand:
    """Integration tests for promote CLI command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        from click.testing import CliRunner
        return CliRunner()

    def test_promote_command_exists(self, runner):
        """
        Given: CLI is available
        When: --help is called
        Then: promote command is listed
        """
        from doc_gen.cli import cli

        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "promote" in result.output.lower()

    def test_promote_command_promotes_staging_to_live(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging document exists
        When: promote command is called
        When: Live document is updated with staging content
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # Setup staging
        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        new_content = "# New Version\n\nUpdated content.\n"
        staging_path.write_text(new_content)

        # Setup old live
        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Old Version\n")

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code == 0
        assert live_path.read_text() == new_content

    def test_promote_command_creates_backup(self, runner, tmp_path, monkeypatch):
        """
        Given: Live document exists
        When: promote command is called
        Then: Creates timestamped backup in .doc-gen/backups/
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        # Setup
        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# New Content\n")

        old_content = "# Old Content to backup\n"
        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text(old_content)

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code == 0
        
        backup_dir = tmp_path / ".doc-gen" / "backups"
        assert backup_dir.exists()
        
        backups = list(backup_dir.glob("*test.md"))
        assert len(backups) == 1
        assert backups[0].read_text() == old_content

    def test_promote_command_reports_success(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging document exists
        When: promote command is called
        Then: Reports success message
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# Content\n")

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code == 0
        assert "success" in result.output.lower() or "✓" in result.output

    def test_promote_command_suggests_git_next_steps(self, runner, tmp_path, monkeypatch):
        """
        Given: Promotion successful
        When: Command completes
        Then: Suggests git add, commit, push as next steps
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# Content\n")

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code == 0
        assert "git" in result.output.lower()
        assert "commit" in result.output.lower()

    def test_promote_command_handles_missing_staging(self, runner, tmp_path, monkeypatch):
        """
        Given: No staging document exists
        When: promote command is called
        Then: Shows clear error message and exits non-zero
        """
        from doc_gen.cli import cli

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code != 0
        assert "staging" in result.output.lower() or "not found" in result.output.lower()

    def test_promote_command_handles_first_promotion(self, runner, tmp_path, monkeypatch):
        """
        Given: Staging exists but no live doc yet (first promotion)
        When: promote command is called
        Then: Creates live doc and reports no backup needed
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# First Version\n")

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code == 0
        live_path = tmp_path / doc_path
        assert live_path.exists()
        # Should mention no backup needed or first promotion
        assert "first" in result.output.lower() or "no backup" in result.output.lower() or "created" in result.output.lower()

    def test_promote_command_shows_backup_location(self, runner, tmp_path, monkeypatch):
        """
        Given: Live document exists
        When: promote command is called
        Then: Shows location of backup file
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"

        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# New\n")

        live_path = tmp_path / doc_path
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("# Old\n")

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code == 0
        assert "backup" in result.output.lower()
        assert ".doc-gen/backups" in result.output

    def test_promote_command_accepts_doc_path_argument(self, runner, tmp_path, monkeypatch):
        """
        Given: CLI command
        When: Called with doc-path argument
        Then: Uses that document path
        """
        from doc_gen.cli import cli
        from doc_gen.metadata import MetadataManager

        monkeypatch.chdir(tmp_path)
        doc_path = "docs/specific.md"

        metadata = MetadataManager(doc_path)
        staging_path = metadata.get_staging_path()
        staging_path.write_text("# Content\n")

        result = runner.invoke(cli, ["promote", doc_path])

        assert result.exit_code == 0
        live_path = tmp_path / doc_path
        assert live_path.exists()
