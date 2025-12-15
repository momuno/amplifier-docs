"""Document promotion from staging to live."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from .metadata import MetadataManager


class PromotionError(Exception):
    """Raised when document promotion fails."""
    pass


class DocumentPromoter:
    """Handles promotion of staging documents to live."""

    def __init__(self, metadata_mgr: MetadataManager):
        """Initialize promoter with metadata manager.

        Args:
            metadata_mgr: MetadataManager instance for the document
        """
        self.metadata_mgr = metadata_mgr

    def promote(self) -> Dict[str, Any]:
        """Promote staging document to live with backup.

        Returns:
            Dictionary with:
                - staging_path: Path to staging document (str)
                - live_path: Path to live document (str)
                - backup_path: Path to backup (str) or None if no backup created
                - promoted_at: ISO 8601 timestamp string

        Raises:
            PromotionError: If staging document doesn't exist
        """
        staging_path = self.metadata_mgr.get_staging_path()
        live_path = self.metadata_mgr.doc_path

        if not staging_path.exists():
            raise PromotionError(
                f"Staging document not found: {staging_path}\n"
                f"Generate staging first: doc-gen generate-doc {live_path}"
            )

        backup_path = None
        if live_path.exists():
            backup_path = self._create_backup(live_path)

        live_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staging_path, live_path)

        return {
            "staging_path": str(staging_path),
            "live_path": str(live_path),
            "backup_path": str(backup_path) if backup_path else None,
            "promoted_at": datetime.now().isoformat(),
        }

    def _create_backup(self, live_path: Path) -> Path:
        """Create timestamped backup of live document.

        Args:
            live_path: Path to live document

        Returns:
            Path to backup file
        """
        backup_dir = Path(".doc-gen/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        backup_filename = f"{timestamp}-{live_path.name}"
        backup_path = backup_dir / backup_filename

        shutil.copy2(live_path, backup_path)

        return backup_path
