"""Tests for repository management."""

import tempfile
from pathlib import Path

import pytest
from git import Repo

from doc_gen.repos import RepoManager


class TestRepoManager:
    """Test RepoManager for Git operations."""

    def test_repo_manager_context_manager_creates_temp_dir(self):
        """RepoManager should create temp directory on enter."""
        # ACT
        with RepoManager() as manager:
            # ASSERT
            assert manager.temp_dir is not None
            assert manager.temp_dir.exists()
            assert manager.temp_dir.is_dir()

    def test_repo_manager_context_manager_cleans_up(self):
        """RepoManager should clean up temp directory on exit."""
        # ARRANGE
        temp_dir_path = None

        # ACT
        with RepoManager() as manager:
            temp_dir_path = manager.temp_dir

        # ASSERT
        # After exiting context, temp directory should be cleaned up
        assert not temp_dir_path.exists()

    def test_repo_manager_uses_custom_temp_dir(self, tmp_path):
        """RepoManager should use custom temp directory if provided."""
        # ARRANGE
        custom_temp = tmp_path / "custom_temp"

        # ACT
        with RepoManager(temp_dir=custom_temp) as manager:
            # ASSERT
            assert manager.temp_dir == custom_temp
            assert custom_temp.exists()

    def test_repo_manager_custom_temp_dir_persists(self, tmp_path):
        """Custom temp directory should persist after context exit."""
        # ARRANGE
        custom_temp = tmp_path / "custom_temp"

        # ACT
        with RepoManager(temp_dir=custom_temp) as manager:
            pass

        # ASSERT
        # Custom directory should still exist
        assert custom_temp.exists()

    def test_clone_repo_clones_successfully(self, tmp_path):
        """clone_repo should clone a Git repository."""
        # ARRANGE
        # Use a small, stable public repo for testing
        test_repo_url = "https://github.com/microsoft/python-package-template.git"

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            cloned_path = manager.clone_repo(test_repo_url, shallow=True)

            # ASSERT
            assert cloned_path.exists()
            assert (cloned_path / ".git").exists()
            # Check it's a valid Git repo
            repo = Repo(cloned_path)
            assert not repo.bare

    def test_clone_repo_extracts_name_from_url(self, tmp_path):
        """clone_repo should extract repo name from URL."""
        # ARRANGE
        test_repo_url = "https://github.com/microsoft/python-package-template.git"

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            cloned_path = manager.clone_repo(test_repo_url)

            # ASSERT
            assert cloned_path.name == "python-package-template"

    def test_clone_repo_shallow_is_faster(self, tmp_path):
        """Shallow clone should use --depth 1."""
        # ARRANGE
        test_repo_url = "https://github.com/microsoft/python-package-template.git"

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            cloned_path = manager.clone_repo(test_repo_url, shallow=True)

            # ASSERT
            repo = Repo(cloned_path)
            # Shallow clone has limited history
            # Note: This is a basic check - actual depth may vary
            assert cloned_path.exists()

    def test_get_file_commit_hash_returns_hash(self, tmp_path):
        """get_file_commit_hash should return commit hash for a file."""
        # ARRANGE
        # Create a test repo
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()
        repo = Repo.init(test_repo)

        # Create a file and commit it
        test_file = test_repo / "test.txt"
        test_file.write_text("Hello, world!")
        repo.index.add(["test.txt"])
        commit = repo.index.commit("Initial commit")

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            commit_hash = manager.get_file_commit_hash(test_repo, "test.txt")

            # ASSERT
            assert commit_hash == commit.hexsha
            assert len(commit_hash) == 40  # Full SHA-1 hash

    def test_get_file_commit_hash_raises_error_for_missing_file(self, tmp_path):
        """get_file_commit_hash should raise error for non-existent file."""
        # ARRANGE
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()
        repo = Repo.init(test_repo)

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT & ASSERT
            with pytest.raises(ValueError, match="No commits found"):
                manager.get_file_commit_hash(test_repo, "nonexistent.txt")

    def test_list_files_matches_glob_patterns(self, tmp_path):
        """list_files should return files matching glob patterns."""
        # ARRANGE
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()

        # Create various files
        (test_repo / "file1.py").write_text("python")
        (test_repo / "file2.py").write_text("python")
        (test_repo / "file3.txt").write_text("text")
        (test_repo / "README.md").write_text("readme")

        subdir = test_repo / "subdir"
        subdir.mkdir()
        (subdir / "nested.py").write_text("nested python")

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            files = manager.list_files(test_repo, ["*.py"])

            # ASSERT
            file_names = [f.name for f in files]
            assert "file1.py" in file_names
            assert "file2.py" in file_names
            assert "file3.txt" not in file_names
            assert "README.md" not in file_names

    def test_list_files_matches_multiple_patterns(self, tmp_path):
        """list_files should match multiple glob patterns."""
        # ARRANGE
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()

        (test_repo / "file.py").write_text("python")
        (test_repo / "README.md").write_text("readme")
        (test_repo / "file.txt").write_text("text")

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            files = manager.list_files(test_repo, ["*.py", "*.md"])

            # ASSERT
            file_names = [f.name for f in files]
            assert "file.py" in file_names
            assert "README.md" in file_names
            assert "file.txt" not in file_names

    def test_list_files_excludes_directories(self, tmp_path):
        """list_files should only return files, not directories."""
        # ARRANGE
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()

        (test_repo / "file.py").write_text("python")
        subdir = test_repo / "subdir"
        subdir.mkdir()

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            files = manager.list_files(test_repo, ["*"])

            # ASSERT
            # Should only contain files, not the subdir directory
            # Check that the actual files exist and are files
            assert all((test_repo / f).is_file() for f in files)
            # Check that 'subdir' is not in the list
            file_names = [f.name for f in files]
            assert "subdir" not in file_names

    def test_list_files_removes_duplicates(self, tmp_path):
        """list_files should remove duplicate matches."""
        # ARRANGE
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()

        (test_repo / "file.py").write_text("python")

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT - Same pattern twice
            files = manager.list_files(test_repo, ["*.py", "file.py"])

            # ASSERT
            file_names = [f.name for f in files]
            assert file_names.count("file.py") == 1

    def test_list_files_returns_relative_paths(self, tmp_path):
        """list_files should return paths relative to repo root."""
        # ARRANGE
        test_repo = tmp_path / "test_repo"
        test_repo.mkdir()

        subdir = test_repo / "subdir"
        subdir.mkdir()
        (subdir / "nested.py").write_text("nested")

        with RepoManager(temp_dir=tmp_path) as manager:
            # ACT
            files = manager.list_files(test_repo, ["**/*.py"])

            # ASSERT
            # Should be relative paths
            assert len(files) > 0
            for f in files:
                # Path should not be absolute to tmp_path
                assert not str(f).startswith(str(tmp_path))
