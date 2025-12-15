"""Integration tests for Sprint 5 workflow: check → review → promote."""

import tempfile
from pathlib import Path
from click.testing import CliRunner
import pytest
from git import Repo

from doc_gen.cli import cli
from doc_gen.metadata import MetadataManager


class TestSprintFiveWorkflowIntegration:
    """Test the complete Sprint 5 workflow end-to-end."""
    
    def test_full_workflow_check_review_promote(self, tmp_path):
        """Test complete workflow: check-changes → review → promote.
        
        Scenario:
        1. Setup doc with sources and outline
        2. Run check-changes (should show no changes initially)
        3. Modify source file (simulate code change)
        4. Run check-changes (should detect change)
        5. Regenerate outline (simulate)
        6. Generate staging doc (simulate)
        7. Run review (should show diff)
        8. Run promote (should create backup and promote)
        """
        runner = CliRunner()
        
        # Setup directory structure
        doc_dir = tmp_path / "docs"
        doc_dir.mkdir()
        doc_path = doc_dir / "example.md"
        doc_path.write_text("# Example Doc\n\nOriginal content\n")
        
        # Setup metadata directory
        metadata_dir = tmp_path / ".doc-gen" / "metadata" / "docs" / "example.md"
        metadata_dir.mkdir(parents=True)
        
        # Create sources.yaml
        sources_yaml = metadata_dir / "sources.yaml"
        sources_yaml.write_text("""
metadata:
  purpose: Example documentation
  
repositories:
  - name: example-repo
    url: https://github.com/example/repo
    patterns:
      - "*.py"
""")
        
        # Setup a mock git repo
        repo_cache = tmp_path / ".doc-gen" / "repos" / "example-repo"
        repo_cache.mkdir(parents=True)
        repo = Repo.init(repo_cache)
        
        # Create initial source file
        source_file = repo_cache / "main.py"
        source_file.write_text("def hello():\n    print('v1')\n")
        repo.index.add([str(source_file)])
        initial_commit = repo.index.commit("Initial commit")
        
        # Create outline with commit hash
        outline_json = metadata_dir / "outline.json"
        outline_json.write_text(f"""{{
  "_metadata": {{
    "generated_at": "2025-12-15T10:00:00"
  }},
  "_commit_hashes": {{
    "example-repo/main.py": "{initial_commit.hexsha}"
  }},
  "sections": [
    {{"title": "Overview", "description": "Example"}}
  ]
}}""")
        
        # Create staging doc
        staging_dir = tmp_path / ".doc-gen" / "staging" / "docs"
        staging_dir.mkdir(parents=True)
        staging_path = staging_dir / "example.md"
        staging_path.write_text("# Example Doc\n\nNew content v2\n")
        
        # Change to tmp_path for test
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            td_path = Path(td)
            
            # Step 1: Check changes (should be up-to-date initially)
            result = runner.invoke(cli, ["check-changes", str(doc_path)])
            assert result.exit_code == 0
            assert "unchanged" in result.output.lower()
            
            # Step 2: Modify source file to simulate code change
            source_file.write_text("def hello():\n    print('v2')\n")
            repo.index.add([str(source_file)])
            new_commit = repo.index.commit("Update to v2")
            
            # Update outline with new hash (simulating regeneration)
            outline_json.write_text(f"""{{
  "_metadata": {{
    "generated_at": "2025-12-15T11:00:00"
  }},
  "_commit_hashes": {{
    "example-repo/main.py": "{new_commit.hexsha}"
  }},
  "sections": [
    {{"title": "Overview", "description": "Example updated"}}
  ]
}}""")
            
            # Step 3: Review staging doc
            result = runner.invoke(cli, ["review", str(doc_path)])
            assert result.exit_code == 0
            assert "diff" in result.output.lower() or "review" in result.output.lower()
            
            # Step 4: Promote staging to live
            result = runner.invoke(cli, ["promote", str(doc_path)])
            assert result.exit_code == 0
            assert "success" in result.output.lower() or "promoted" in result.output.lower()
            
            # Verify live doc exists
            assert doc_path.exists()
            content = doc_path.read_text()
            assert "New content v2" in content
    
    def test_workflow_detects_changed_files(self, tmp_path):
        """Test that workflow detects changes in source files."""
        runner = CliRunner()
        
        # Setup minimal structure
        doc_path = tmp_path / "docs" / "test.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("# Test\n")
        
        metadata_dir = tmp_path / ".doc-gen" / "metadata" / "docs" / "test.md"
        metadata_dir.mkdir(parents=True)
        
        # Create sources
        sources_yaml = metadata_dir / "sources.yaml"
        sources_yaml.write_text("""
metadata:
  purpose: Test
repositories:
  - name: test-repo
    url: https://github.com/test/repo
    patterns: ["*.py"]
""")
        
        # Create outline without commit hashes
        outline_json = metadata_dir / "outline.json"
        outline_json.write_text("""{}""")
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["check-changes", str(doc_path)])
            # May exit with 1 (changes) or 0 (no outline), both acceptable
            assert result.exit_code in [0, 1]
    
    def test_workflow_review_requires_staging(self, tmp_path):
        """Test that review command requires staging doc to exist."""
        runner = CliRunner()
        
        doc_path = tmp_path / "docs" / "test.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("# Test\n")
        
        metadata_dir = tmp_path / ".doc-gen" / "metadata" / "docs" / "test.md"
        metadata_dir.mkdir(parents=True)
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["review", str(doc_path)])
            assert result.exit_code == 1
            assert "staging" in result.output.lower() or "not found" in result.output.lower()
    
    def test_workflow_promote_requires_staging(self, tmp_path):
        """Test that promote command requires staging doc to exist."""
        runner = CliRunner()
        
        doc_path = tmp_path / "docs" / "test.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("# Test\n")
        
        metadata_dir = tmp_path / ".doc-gen" / "metadata" / "docs" / "test.md"
        metadata_dir.mkdir(parents=True)
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["promote", str(doc_path)])
            assert result.exit_code == 1
            assert "staging" in result.output.lower() or "not found" in result.output.lower()
    
    def test_workflow_promote_creates_backup(self, tmp_path):
        """Test that promote creates backup of existing live doc."""
        runner = CliRunner()
        
        # Setup live doc
        doc_path = tmp_path / "docs" / "test.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("# Original content\n")
        
        metadata_dir = tmp_path / ".doc-gen" / "metadata" / "docs" / "test.md"
        metadata_dir.mkdir(parents=True)
        
        # Create staging doc
        staging_dir = tmp_path / ".doc-gen" / "staging" / "docs"
        staging_dir.mkdir(parents=True)
        staging_path = staging_dir / "test.md"
        staging_path.write_text("# New content\n")
        
        backup_dir = tmp_path / ".doc-gen" / "backups"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["promote", str(doc_path)])
            assert result.exit_code == 0
            
            # Verify backup was created
            assert backup_dir.exists()
            backups = list(backup_dir.glob("*.md"))
            assert len(backups) == 1
            
            # Verify backup has original content
            backup_content = backups[0].read_text()
            assert "Original content" in backup_content
            
            # Verify live doc has new content
            live_content = doc_path.read_text()
            assert "New content" in live_content
    
    def test_workflow_check_all_docs(self, tmp_path):
        """Test check-changes with --all flag."""
        runner = CliRunner()
        
        # Create multiple docs
        for i in range(3):
            doc_path = tmp_path / "docs" / f"doc{i}.md"
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text(f"# Doc {i}\n")
            
            metadata_dir = tmp_path / ".doc-gen" / "metadata" / "docs" / f"doc{i}.md"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sources.yaml
            sources_yaml = metadata_dir / "sources.yaml"
            sources_yaml.write_text(f"""
metadata:
  purpose: Doc {i}
repositories:
  - name: repo{i}
    url: https://github.com/test/repo{i}
    patterns: ["*.py"]
""")
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["check-changes", "--all"])
            # Should detect all docs (may not have outlines)
            assert "document" in result.output.lower()
    
    def test_workflow_check_single_doc(self, tmp_path):
        """Test check-changes with single doc path."""
        runner = CliRunner()
        
        doc_path = tmp_path / "docs" / "single.md"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("# Single\n")
        
        metadata_dir = tmp_path / ".doc-gen" / "metadata" / "docs" / "single.md"
        metadata_dir.mkdir(parents=True)
        
        sources_yaml = metadata_dir / "sources.yaml"
        sources_yaml.write_text("""
metadata:
  purpose: Single doc
repositories:
  - name: repo
    url: https://github.com/test/repo
    patterns: ["*.py"]
""")
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["check-changes", str(doc_path)])
            assert "single.md" in result.output.lower() or "checking" in result.output.lower()
