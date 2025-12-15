"""Configuration management for doc-gen."""

import yaml
from pathlib import Path
from typing import Dict, Optional


class Config:
    """doc-gen configuration."""

    def __init__(self, outline_storage: str, outlines: Dict[str, str]):
        self.outline_storage = outline_storage
        self.outlines = outlines  # Maps: doc_path -> outline_path (relative to storage)

    @classmethod
    def load(cls, project_root: Path = None) -> "Config":
        """Load config from .doc-gen/config.yaml.

        Args:
            project_root: Project root directory (defaults to cwd)

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        if project_root is None:
            project_root = Path.cwd()

        config_path = project_root / ".doc-gen" / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}\n"
                f"Run 'doc-gen init' to create it."
            )

        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        outline_storage = data.get('outline_storage', '.doc-gen/amplifier-docs-cache')
        outlines = data.get('outlines', {})

        return cls(outline_storage=outline_storage, outlines=outlines)

    def save(self, project_root: Path = None) -> None:
        """Save config to .doc-gen/config.yaml.

        Args:
            project_root: Project root directory (defaults to cwd)
        """
        if project_root is None:
            project_root = Path.cwd()

        config_path = project_root / ".doc-gen" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'outline_storage': self.outline_storage,
            'outlines': self.outlines
        }

        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_outline_path(self, doc_path: str, project_root: Path = None) -> Optional[Path]:
        """Get full outline path for a documentation file.

        Args:
            doc_path: Documentation file path (e.g., "docs/api/overview.md")
            project_root: Project root directory (defaults to cwd)

        Returns:
            Full path to outline file, or None if not registered
        """
        if project_root is None:
            project_root = Path.cwd()

        # Look up in registry
        outline_rel_path = self.outlines.get(doc_path)
        if outline_rel_path is None:
            return None

        # Build full path
        return project_root / self.outline_storage / outline_rel_path

    def register_outline(self, doc_path: str, outline_rel_path: str) -> None:
        """Register an outline for a documentation file.

        Args:
            doc_path: Documentation file path (e.g., "docs/api/overview.md")
            outline_rel_path: Outline path relative to storage (e.g., "docs-api-overview/overview_outline.json")
        """
        self.outlines[doc_path] = outline_rel_path


def create_default_config(project_root: Path = None) -> None:
    """Create default config file with commented examples.

    Args:
        project_root: Project root directory (defaults to cwd)
    """
    if project_root is None:
        project_root = Path.cwd()

    config_path = project_root / ".doc-gen" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create storage directory
    storage_dir = project_root / ".doc-gen" / "amplifier-docs-cache"
    storage_dir.mkdir(parents=True, exist_ok=True)

    # Write config with commented examples
    config_content = """# doc-gen configuration file

# Outline storage location (created automatically if doesn't exist)
outline_storage: .doc-gen/amplifier-docs-cache

# Registry: maps documentation files to their outlines
# Add entries using: doc-gen register-outline <outline-path> <doc-path>
outlines: {}
  # Example entries:
  # docs/api/overview.md: docs-api-overview/overview_outline.json
  # docs/api/cli/index.md: docs-api-cli-index/index_outline.json
  # docs/architecture/kernel.md: docs-architecture-kernel/kernel_outline.json
"""

    config_path.write_text(config_content)


def compute_outline_path(doc_path: str) -> str:
    """Compute outline path from documentation path using naming convention.

    Args:
        doc_path: Documentation file path (e.g., "docs/api/cli/index.md")

    Returns:
        Outline path relative to storage (e.g., "docs-api-cli-index/index_outline.json")

    Examples:
        >>> compute_outline_path("docs/api/overview.md")
        'docs-api-overview/overview_outline.json'
        >>> compute_outline_path("docs/api/cli/index.md")
        'docs-api-cli-index/index_outline.json'
    """
    doc_path_obj = Path(doc_path)

    # Convert path to directory name: docs/api/cli/index.md -> docs-api-cli-index
    dir_name = str(doc_path).replace('/', '-').replace('.md', '')

    # Build filename: index.md -> index_outline.json
    filename = f"{doc_path_obj.stem}_outline.json"

    # Combine: docs-api-cli-index/index_outline.json
    return f"{dir_name}/{filename}"
