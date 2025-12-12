"""Tests for metadata management."""

import json
from pathlib import Path

import pytest
import yaml

from doc_gen.metadata import MetadataManager


class TestMetadataManager:
    """Test MetadataManager for sources, outlines, and staging."""

    def test_metadata_manager_creates_paths(self):
        """MetadataManager should create proper paths from doc path."""
        # ARRANGE
        doc_path = "docs/modules/providers/openai.md"

        # ACT
        metadata = MetadataManager(doc_path)

        # ASSERT
        assert metadata.doc_path == Path("docs/modules/providers/openai.md")
        expected_metadata_dir = Path(".doc-gen/metadata/docs/modules/providers/openai")
        assert metadata.metadata_dir == expected_metadata_dir
        assert metadata.sources_path == expected_metadata_dir / "sources.yaml"
        assert metadata.outline_path == expected_metadata_dir / "outline.json"
        assert metadata.staging_dir == expected_metadata_dir / "staging"

    def test_init_sources_creates_template(self, tmp_path, monkeypatch):
        """init_sources should create sources.yaml template."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata = MetadataManager(doc_path)

        # ACT
        metadata.init_sources()

        # ASSERT
        assert metadata.sources_path.exists()
        with open(metadata.sources_path, "r") as f:
            data = yaml.safe_load(f)

        assert "repositories" in data
        assert len(data["repositories"]) == 1
        assert "url" in data["repositories"][0]
        assert "include" in data["repositories"][0]
        assert "exclude" in data["repositories"][0]
        assert "metadata" in data
        assert "purpose" in data["metadata"]

    def test_init_sources_creates_parent_directories(self, tmp_path, monkeypatch):
        """init_sources should create parent directories if needed."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/deep/nested/path/test.md"
        metadata = MetadataManager(doc_path)

        # ACT
        metadata.init_sources()

        # ASSERT
        assert metadata.metadata_dir.exists()
        assert metadata.sources_path.exists()

    def test_read_sources_parses_yaml(self, tmp_path, monkeypatch):
        """read_sources should parse sources.yaml file."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata = MetadataManager(doc_path)
        metadata.init_sources()

        # Modify the sources file
        sources_data = {
            "repositories": [
                {
                    "url": "https://github.com/test/repo.git",
                    "include": ["*.py"],
                    "exclude": ["tests/**"],
                }
            ],
            "metadata": {"purpose": "Test document"},
        }
        with open(metadata.sources_path, "w") as f:
            yaml.dump(sources_data, f)

        # ACT
        loaded_data = metadata.read_sources()

        # ASSERT
        assert loaded_data["repositories"][0]["url"] == "https://github.com/test/repo.git"
        assert loaded_data["repositories"][0]["include"] == ["*.py"]
        assert loaded_data["metadata"]["purpose"] == "Test document"

    def test_read_sources_raises_error_if_missing(self, tmp_path, monkeypatch):
        """read_sources should raise helpful error if sources.yaml missing."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata = MetadataManager(doc_path)

        # ACT & ASSERT
        with pytest.raises(FileNotFoundError, match="Sources not found"):
            metadata.read_sources()

    def test_save_outline_creates_json_file(self, tmp_path, monkeypatch):
        """save_outline should create outline.json with data."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata = MetadataManager(doc_path)

        outline_data = {
            "sections": [
                {"title": "Overview", "content": "Introduction"},
                {"title": "Usage", "content": "How to use"},
            ],
            "commit_hashes": {"file1.py": "abc123"},
        }

        # ACT
        metadata.save_outline(outline_data)

        # ASSERT
        assert metadata.outline_path.exists()
        with open(metadata.outline_path, "r") as f:
            loaded = json.load(f)

        assert loaded["sections"][0]["title"] == "Overview"
        assert loaded["commit_hashes"]["file1.py"] == "abc123"

    def test_read_outline_loads_json(self, tmp_path, monkeypatch):
        """read_outline should load outline.json data."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata = MetadataManager(doc_path)

        outline_data = {"sections": [], "commit_hashes": {}}
        metadata.save_outline(outline_data)

        # ACT
        loaded = metadata.read_outline()

        # ASSERT
        assert "sections" in loaded
        assert "commit_hashes" in loaded

    def test_read_outline_raises_error_if_missing(self, tmp_path, monkeypatch):
        """read_outline should raise helpful error if outline.json missing."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata = MetadataManager(doc_path)

        # ACT & ASSERT
        with pytest.raises(FileNotFoundError, match="Outline not found"):
            metadata.read_outline()

    def test_get_staging_path_returns_correct_path(self, tmp_path, monkeypatch):
        """get_staging_path should return staging directory path."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/modules/test.md"
        metadata = MetadataManager(doc_path)

        # ACT
        staging_path = metadata.get_staging_path()

        # ASSERT
        expected = metadata.staging_dir / "test.md"
        assert staging_path == expected

    def test_get_staging_path_creates_directory(self, tmp_path, monkeypatch):
        """get_staging_path should create staging directory if needed."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)
        doc_path = "docs/test.md"
        metadata = MetadataManager(doc_path)

        # ACT
        staging_path = metadata.get_staging_path()

        # ASSERT
        assert metadata.staging_dir.exists()
        assert metadata.staging_dir.is_dir()

    def test_find_all_docs_returns_empty_when_no_metadata(self, tmp_path, monkeypatch):
        """find_all_docs should return empty list when no metadata exists."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)

        # ACT
        docs = MetadataManager.find_all_docs()

        # ASSERT
        assert docs == []

    def test_find_all_docs_finds_initialized_docs(self, tmp_path, monkeypatch):
        """find_all_docs should find all documents with sources.yaml."""
        # ARRANGE
        monkeypatch.chdir(tmp_path)

        # Create multiple docs
        doc1 = MetadataManager("docs/doc1.md")
        doc1.init_sources()

        doc2 = MetadataManager("docs/subdir/doc2.md")
        doc2.init_sources()

        # ACT
        docs = MetadataManager.find_all_docs()

        # ASSERT
        assert len(docs) == 2
        # Convert to strings for easier comparison
        doc_strs = [str(d) for d in docs]
        assert any("doc1" in d for d in doc_strs)
        assert any("doc2" in d for d in doc_strs)
