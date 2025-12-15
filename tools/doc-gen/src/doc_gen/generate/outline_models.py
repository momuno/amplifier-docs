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

    name: str
    document_instruction: str
    title: str
    output: str
    sections: list[Section]
    # LLM configuration (optional, with defaults)
    model: str = "claude-3-5-sonnet-20241022"
    max_response_tokens: int = 8000
    temperature: float = 0.3

    def to_dict(self) -> dict:
        """Convert to dictionary with _meta and document structure."""
        return {
            "_meta": {
                "name": self.name,
                "document_instruction": self.document_instruction,
                "model": self.model,
                "max_response_tokens": self.max_response_tokens,
                "temperature": self.temperature,
            },
            "document": {
                "title": self.title,
                "output": self.output,
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
            name=data["_meta"]["name"],
            document_instruction=data["_meta"]["document_instruction"],
            title=data["document"]["title"],
            output=data["document"]["output"],
            sections=sections,
            # LLM config with defaults if not present
            model=data["_meta"].get("model", "claude-3-5-sonnet-20241022"),
            max_response_tokens=data["_meta"].get("max_response_tokens", 8000),
            temperature=data["_meta"].get("temperature", 0.3),
        )
