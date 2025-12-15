"""Data models for document outlines."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SourceReference:
    """Source file reference with reasoning."""

    file: str
    reasoning: str
    commit: str | None = None  # Optional commit hash for tracking file version

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "file": self.file,
            "reasoning": self.reasoning,
        }
        # Only include commit if it's set (for cleaner JSON)
        if self.commit is not None:
            result["commit"] = self.commit
        return result


@dataclass
class Section:
    """Section in the document outline."""

    heading: str
    level: int
    prompt: str
    sources: list[SourceReference]
    sections: list["Section"]

    def to_dict(self) -> dict:
        """Convert to dictionary recursively."""
        return {
            "heading": self.heading,
            "level": self.level,
            "prompt": self.prompt,
            "sources": [s.to_dict() for s in self.sources],
            "sections": [s.to_dict() for s in self.sections],
        }


@dataclass
class DocumentOutline:
    """Complete document outline."""

    title: str
    output_path: str
    doc_type: str
    purpose: str
    sections: list[Section]
    generated_at: str = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary with metadata."""
        return {
            "_meta": {
                "name": f"generated-{self.doc_type}-{datetime.now().strftime('%Y%m%d')}",
                "description": self.purpose,
                "use_case": self.purpose,
                "quadrant": self.doc_type,
                "doc_type": self.doc_type,
                "user_intent": self.purpose,
                "output": self.output_path,
            },
            "document": {
                "title": self.title,
                "output": self.output_path,
                "sections": [s.to_dict() for s in self.sections],
            }
        }

    def save(self, path: Path) -> None:
        """Save outline to JSON file.

        Args:
            path: Path to save outline (will be created with parent dirs)
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "DocumentOutline":
        """Load outline from JSON file."""
        data = json.loads(path.read_text())

        def parse_section(s_data) -> Section:
            return Section(
                heading=s_data["heading"],
                level=s_data["level"],
                prompt=s_data["prompt"],
                sources=[SourceReference(
                    file=src["file"],
                    reasoning=src["reasoning"],
                    commit=src.get("commit")  # Optional commit hash
                ) for src in s_data["sources"]],
                sections=[parse_section(sub) for sub in s_data["sections"]],
            )

        sections = [parse_section(s) for s in data["document"]["sections"]]

        return cls(
            title=data["document"]["title"],
            output_path=data["document"]["output"],
            doc_type=data["_meta"]["doc_type"],
            purpose=data["_meta"]["user_intent"],
            sections=sections,
            generated_at=data["_meta"].get("generated_at", ""),
        )
