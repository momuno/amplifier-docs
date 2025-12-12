"""Metadata management for doc-gen."""

import json
from pathlib import Path
from typing import Any, Dict

import yaml


class MetadataManager:
    """Manages .doc-gen metadata for a document."""

    def __init__(self, doc_path: str):
        """Initialize metadata manager for a document.

        Args:
            doc_path: Path to the document (e.g., "docs/modules/providers/openai.md")
        """
        self.doc_path = Path(doc_path)
        # .doc-gen/metadata/docs/modules/providers/openai/
        self.metadata_dir = (
            Path(".doc-gen/metadata") / self.doc_path.parent / self.doc_path.stem
        )
        self.sources_path = self.metadata_dir / "sources.yaml"
        self.outline_path = self.metadata_dir / "outline.json"
        self.staging_dir = self.metadata_dir / "staging"

    def init_sources(self):
        """Create sources.yaml template."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        template = {
            "repositories": [
                {
                    "url": "https://github.com/owner/repo.git",
                    # Use EITHER include OR exclude patterns (not both)
                    # Include: specify what files to include
                    "include": [
                        "**/*.py",      # All Python files (recursive)
                        "**/*.md",      # All Markdown files (recursive)
                        "README.md",    # Specific files
                    ],
                    # OR exclude: specify what files to exclude (uncomment to use)
                    # "exclude": [
                    #     "tests/**",
                    #     "**/__pycache__/**",
                    #     "**/*.pyc",
                    # ],
                }
            ],
            "metadata": {
                "purpose": "Document the [feature/module] functionality",
                "last_updated": None,
            },
        }

        with open(self.sources_path, "w") as f:
            yaml.dump(template, f, sort_keys=False, default_flow_style=False)

    def read_sources(self) -> Dict[str, Any]:
        """Load sources.yaml configuration.

        Returns:
            Dictionary containing sources configuration

        Raises:
            FileNotFoundError: If sources.yaml does not exist
        """
        if not self.sources_path.exists():
            raise FileNotFoundError(
                f"Sources not found: {self.sources_path}\n"
                f"Initialize with: doc-gen init {self.doc_path}"
            )

        with open(self.sources_path, "r") as f:
            return yaml.safe_load(f)

    def save_outline(self, outline_data: Dict[str, Any]):
        """Save outline.json with commit hashes.

        Args:
            outline_data: Dictionary containing outline data
        """
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        with open(self.outline_path, "w") as f:
            json.dump(outline_data, f, indent=2)

    def read_outline(self) -> Dict[str, Any]:
        """Load existing outline.json.

        Returns:
            Dictionary containing outline data

        Raises:
            FileNotFoundError: If outline.json does not exist
        """
        if not self.outline_path.exists():
            raise FileNotFoundError(
                f"Outline not found: {self.outline_path}\n"
                f"Generate with: doc-gen generate-outline {self.doc_path}"
            )

        with open(self.outline_path, "r") as f:
            return json.load(f)

    def get_staging_path(self) -> Path:
        """Return path to staging document.

        Returns:
            Path to the staging document file
        """
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        return self.staging_dir / f"{self.doc_path.name}"

    @staticmethod
    def find_all_docs() -> list[Path]:
        """Find all docs with metadata (Sprint 5 will use this).

        Returns:
            List of document paths that have been initialized
        """
        metadata_root = Path(".doc-gen/metadata")
        if not metadata_root.exists():
            return []

        # Find all sources.yaml files
        sources_files = list(metadata_root.rglob("sources.yaml"))
        
        # Convert back to doc paths
        doc_paths = []
        for sources_file in sources_files:
            # Get relative path from metadata root
            rel_path = sources_file.parent.relative_to(metadata_root)
            # Reconstruct original doc path by adding .md extension
            doc_path = Path(str(rel_path) + ".md")
            doc_paths.append(doc_path)
        
        return doc_paths
