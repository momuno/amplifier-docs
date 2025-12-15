"""Tests for change detection module.

Following TDD: These tests are written FIRST (RED phase).
"""

import pytest
from pathlib import Path
from git import Repo
from unittest.mock import Mock, patch


class TestFileChange:
    """Test FileChange dataclass."""

    def test_file_change_creates_with_all_fields(self):
        """
        Given: Valid file change data
        When: FileChange is created
        Then: All fields are set correctly
        """
        from doc_gen.change_detection import FileChange

        change = FileChange(
            file_path="src/kernel.py",
            old_hash="abc123d",
            new_hash="def456g",
            commit_message="feat: add new feature"
        )

        assert change.file_path == "src/kernel.py"
        assert change.old_hash == "abc123d"
        assert change.new_hash == "def456g"
        assert change.commit_message == "feat: add new feature"

    def test_file_change_stores_short_hashes(self):
        """
        Given: 7-character short hashes
        When: FileChange is created
        Then: Hashes are stored as-is (7 chars for display)
        """
        from doc_gen.change_detection import FileChange

        change = FileChange(
            file_path="test.py",
            old_hash="1234567",
            new_hash="abcdefg",
            commit_message="fix: bug fix"
        )

        assert len(change.old_hash) == 7
        assert len(change.new_hash) == 7


class TestChangeReport:
    """Test ChangeReport dataclass."""

    def test_change_report_creates_with_all_fields(self):
        """
        Given: Valid change report data
        When: ChangeReport is created
        Then: All fields are set correctly
        """
        from doc_gen.change_detection import ChangeReport, FileChange

        changes = [
            FileChange("file1.py", "abc123d", "def456g", "Update file1"),
            FileChange("file2.py", "111222a", "333444b", "Update file2")
        ]

        report = ChangeReport(
            doc_path="docs/api.md",
            changed_files=changes,
            new_files=["file3.py", "file4.py"],
            removed_files=["old_file.py"],
            unchanged_files=["stable.py"]
        )

        assert report.doc_path == "docs/api.md"
        assert len(report.changed_files) == 2
        assert len(report.new_files) == 2
        assert len(report.removed_files) == 1
        assert len(report.unchanged_files) == 1

    def test_needs_regeneration_returns_true_when_files_changed(self):
        """
        Given: ChangeReport with changed files
        When: needs_regeneration() is called
        Then: Returns True
        """
        from doc_gen.change_detection import ChangeReport, FileChange

        report = ChangeReport(
            doc_path="docs/api.md",
            changed_files=[FileChange("file1.py", "abc", "def", "Update")],
            new_files=[],
            removed_files=[],
            unchanged_files=[]
        )

        assert report.needs_regeneration() is True

    def test_needs_regeneration_returns_true_when_new_files(self):
        """
        Given: ChangeReport with new files
        When: needs_regeneration() is called
        Then: Returns True
        """
        from doc_gen.change_detection import ChangeReport

        report = ChangeReport(
            doc_path="docs/api.md",
            changed_files=[],
            new_files=["new_file.py"],
            removed_files=[],
            unchanged_files=[]
        )

        assert report.needs_regeneration() is True

    def test_needs_regeneration_returns_true_when_removed_files(self):
        """
        Given: ChangeReport with removed files
        When: needs_regeneration() is called
        Then: Returns True
        """
        from doc_gen.change_detection import ChangeReport

        report = ChangeReport(
            doc_path="docs/api.md",
            changed_files=[],
            new_files=[],
            removed_files=["deleted.py"],
            unchanged_files=[]
        )

        assert report.needs_regeneration() is True

    def test_needs_regeneration_returns_false_when_no_changes(self):
        """
        Given: ChangeReport with only unchanged files
        When: needs_regeneration() is called
        Then: Returns False
        """
        from doc_gen.change_detection import ChangeReport

        report = ChangeReport(
            doc_path="docs/api.md",
            changed_files=[],
            new_files=[],
            removed_files=[],
            unchanged_files=["stable.py", "constant.py"]
        )

        assert report.needs_regeneration() is False

    def test_total_changes_counts_all_changes(self):
        """
        Given: ChangeReport with various changes
        When: total_changes() is called
        Then: Returns sum of changed, new, and removed files
        """
        from doc_gen.change_detection import ChangeReport, FileChange

        report = ChangeReport(
            doc_path="docs/api.md",
            changed_files=[
                FileChange("f1.py", "a", "b", "msg1"),
                FileChange("f2.py", "c", "d", "msg2")
            ],
            new_files=["f3.py", "f4.py", "f5.py"],
            removed_files=["old.py"],
            unchanged_files=["stable.py"]
        )

        assert report.total_changes() == 6  # 2 + 3 + 1

    def test_total_changes_returns_zero_when_no_changes(self):
        """
        Given: ChangeReport with no changes
        When: total_changes() is called
        Then: Returns 0
        """
        from doc_gen.change_detection import ChangeReport

        report = ChangeReport(
            doc_path="docs/api.md",
            changed_files=[],
            new_files=[],
            removed_files=[],
            unchanged_files=["stable.py"]
        )

        assert report.total_changes() == 0


class TestChangeDetector:
    """Test ChangeDetector class."""

    def test_change_detector_initializes(self):
        """
        Given: No parameters
        When: ChangeDetector is created
        Then: Instance is created successfully
        """
        from doc_gen.change_detection import ChangeDetector

        detector = ChangeDetector()

        assert detector is not None

    def test_check_changes_returns_change_report(self):
        """
        Given: Valid outline and repo paths
        When: check_changes() is called
        Then: Returns ChangeReport instance
        """
        from doc_gen.change_detection import ChangeDetector, ChangeReport

        detector = ChangeDetector()

        outline = {
            "title": "Test Doc",
            "_commit_hashes": {}
        }
        repo_paths = {}

        result = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert isinstance(result, ChangeReport)
        assert result.doc_path == "docs/test.md"

    def test_check_changes_identifies_unchanged_files(self, tmp_path):
        """
        Given: File with same commit hash in outline and repo
        When: check_changes() is called
        Then: File is in unchanged_files list
        """
        from doc_gen.change_detection import ChangeDetector

        # Create git repo with file
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)

        test_file = repo_path / "test.py"
        test_file.write_text("print('hello')")
        repo.index.add(["test.py"])
        commit = repo.index.commit("Initial commit")
        commit_hash = commit.hexsha

        # Outline with same hash
        outline = {
            "title": "Test",
            "_commit_hashes": {
                "test-repo/test.py": commit_hash
            }
        }
        repo_paths = {"test-repo": repo_path}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert "test-repo/test.py" in report.unchanged_files
        assert len(report.changed_files) == 0

    def test_check_changes_identifies_changed_files(self, tmp_path):
        """
        Given: File with different commit hash in outline and repo
        When: check_changes() is called
        Then: File is in changed_files list with old and new hashes
        """
        from doc_gen.change_detection import ChangeDetector

        # Create git repo with two commits
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)

        test_file = repo_path / "test.py"
        test_file.write_text("print('v1')")
        repo.index.add(["test.py"])
        old_commit = repo.index.commit("First commit")
        old_hash = old_commit.hexsha

        # Second commit
        test_file.write_text("print('v2')")
        repo.index.add(["test.py"])
        new_commit = repo.index.commit("Second commit")
        new_hash = new_commit.hexsha

        # Outline with old hash
        outline = {
            "title": "Test",
            "_commit_hashes": {
                "test-repo/test.py": old_hash
            }
        }
        repo_paths = {"test-repo": repo_path}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert len(report.changed_files) == 1
        change = report.changed_files[0]
        assert change.file_path == "test-repo/test.py"
        assert change.old_hash == old_hash[:7]  # Short hash
        assert change.new_hash == new_hash[:7]  # Short hash
        assert change.commit_message == "Second commit"

    def test_check_changes_identifies_new_files(self, tmp_path):
        """
        Given: File in repo but not in outline
        When: check_changes() is called
        Then: File is in new_files list
        """
        from doc_gen.change_detection import ChangeDetector

        # Create git repo with file
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)

        test_file = repo_path / "new_file.py"
        test_file.write_text("print('new')")
        repo.index.add(["new_file.py"])
        repo.index.commit("Add new file")

        # Outline without this file
        outline = {
            "title": "Test",
            "_commit_hashes": {}
        }
        repo_paths = {"test-repo": repo_path}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert "test-repo/new_file.py" in report.new_files
        assert len(report.changed_files) == 0

    def test_check_changes_identifies_removed_files(self, tmp_path):
        """
        Given: File in outline but not in repo
        When: check_changes() is called
        Then: File is in removed_files list
        """
        from doc_gen.change_detection import ChangeDetector

        # Create git repo (empty)
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        Repo.init(repo_path)

        # Outline with file that doesn't exist
        outline = {
            "title": "Test",
            "_commit_hashes": {
                "test-repo/deleted_file.py": "abc123def456"
            }
        }
        repo_paths = {"test-repo": repo_path}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert "test-repo/deleted_file.py" in report.removed_files
        assert len(report.changed_files) == 0

    def test_check_changes_handles_multi_repo_file_paths(self, tmp_path):
        """
        Given: Files from multiple repositories
        When: check_changes() is called
        Then: Correctly splits repo name and relative path
        """
        from doc_gen.change_detection import ChangeDetector

        # Create two repos
        repo1_path = tmp_path / "repo1"
        repo1_path.mkdir()
        repo1 = Repo.init(repo1_path)
        file1 = repo1_path / "file1.py"
        file1.write_text("repo1")
        repo1.index.add(["file1.py"])
        commit1 = repo1.index.commit("Repo1 commit")

        repo2_path = tmp_path / "repo2"
        repo2_path.mkdir()
        repo2 = Repo.init(repo2_path)
        file2 = repo2_path / "file2.py"
        file2.write_text("repo2")
        repo2.index.add(["file2.py"])
        commit2 = repo2.index.commit("Repo2 commit")

        # Outline with both files
        outline = {
            "title": "Test",
            "_commit_hashes": {
                "repo1/file1.py": commit1.hexsha,
                "repo2/file2.py": commit2.hexsha
            }
        }
        repo_paths = {
            "repo1": repo1_path,
            "repo2": repo2_path
        }

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert "repo1/file1.py" in report.unchanged_files
        assert "repo2/file2.py" in report.unchanged_files

    def test_check_changes_extracts_first_line_of_commit_message(self, tmp_path):
        """
        Given: Multi-line commit message
        When: check_changes() is called
        Then: Only first line is stored in FileChange
        """
        from doc_gen.change_detection import ChangeDetector

        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)

        test_file = repo_path / "test.py"
        test_file.write_text("v1")
        repo.index.add(["test.py"])
        old_commit = repo.index.commit("First")
        old_hash = old_commit.hexsha

        # Multi-line commit
        test_file.write_text("v2")
        repo.index.add(["test.py"])
        new_commit = repo.index.commit("feat: add feature\n\nDetailed description\nMore details")
        new_hash = new_commit.hexsha

        outline = {
            "title": "Test",
            "_commit_hashes": {
                "test-repo/test.py": old_hash
            }
        }
        repo_paths = {"test-repo": repo_path}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert len(report.changed_files) == 1
        assert report.changed_files[0].commit_message == "feat: add feature"

    def test_check_changes_handles_empty_outline(self):
        """
        Given: Outline with no _commit_hashes field
        When: check_changes() is called
        Then: Returns empty report without errors
        """
        from doc_gen.change_detection import ChangeDetector

        outline = {
            "title": "Test"
            # No _commit_hashes field
        }
        repo_paths = {}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert report.doc_path == "docs/test.md"
        assert len(report.changed_files) == 0
        assert len(report.new_files) == 0
        assert len(report.removed_files) == 0
        assert len(report.unchanged_files) == 0

    def test_check_changes_handles_missing_commit_hashes(self, tmp_path):
        """
        Given: Outline with empty _commit_hashes dict
        When: check_changes() is called
        Then: Returns report without errors
        """
        from doc_gen.change_detection import ChangeDetector

        outline = {
            "title": "Test",
            "_commit_hashes": {}
        }
        repo_paths = {}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert len(report.changed_files) == 0
        assert report.needs_regeneration() is False

    def test_check_changes_handles_single_repo_backward_compat(self, tmp_path):
        """
        Given: File path without repo prefix (single-repo backward compat)
        When: check_changes() is called
        Then: Handles gracefully (treats as removed if no matching repo)
        """
        from doc_gen.change_detection import ChangeDetector

        # Outline with path without repo prefix
        outline = {
            "title": "Test",
            "_commit_hashes": {
                "src/file.py": "abc123def"
            }
        }
        repo_paths = {}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        # Should treat as removed since can't find matching repo
        assert "src/file.py" in report.removed_files

    def test_check_changes_handles_invalid_commit_hash(self, tmp_path):
        """
        Given: Outline with invalid/non-existent commit hash
        When: check_changes() is called
        Then: Treats file as removed (hash can't be found in repo)
        """
        from doc_gen.change_detection import ChangeDetector

        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)

        test_file = repo_path / "test.py"
        test_file.write_text("content")
        repo.index.add(["test.py"])
        repo.index.commit("Real commit")

        # Outline with fake hash
        outline = {
            "title": "Test",
            "_commit_hashes": {
                "test-repo/test.py": "0000000000000000000000000000000000000000"
            }
        }
        repo_paths = {"test-repo": repo_path}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        # Should detect as changed (different hash)
        assert len(report.changed_files) == 1

    def test_check_changes_categorizes_all_files_correctly(self, tmp_path):
        """
        Given: Mix of changed, new, removed, and unchanged files
        When: check_changes() is called
        Then: All files are categorized correctly
        """
        from doc_gen.change_detection import ChangeDetector

        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)

        # Unchanged file
        unchanged = repo_path / "unchanged.py"
        unchanged.write_text("unchanged")
        repo.index.add(["unchanged.py"])
        unchanged_commit = repo.index.commit("Unchanged")

        # Changed file (old version)
        changed = repo_path / "changed.py"
        changed.write_text("v1")
        repo.index.add(["changed.py"])
        old_commit = repo.index.commit("Old version")

        # Update changed file
        changed.write_text("v2")
        repo.index.add(["changed.py"])
        new_commit = repo.index.commit("New version")

        # New file (not in outline)
        new_file = repo_path / "new.py"
        new_file.write_text("new")
        repo.index.add(["new.py"])
        repo.index.commit("Add new file")

        # Outline with unchanged, changed, and removed files
        outline = {
            "title": "Test",
            "_commit_hashes": {
                "test-repo/unchanged.py": unchanged_commit.hexsha,
                "test-repo/changed.py": old_commit.hexsha,
                "test-repo/removed.py": "abc123"
            }
        }
        repo_paths = {"test-repo": repo_path}

        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, "docs/test.md")

        assert "test-repo/unchanged.py" in report.unchanged_files
        assert len(report.changed_files) == 1
        assert report.changed_files[0].file_path == "test-repo/changed.py"
        assert "test-repo/new.py" in report.new_files
        assert "test-repo/removed.py" in report.removed_files
        assert report.total_changes() == 3  # changed + new + removed
        assert report.needs_regeneration() is True
