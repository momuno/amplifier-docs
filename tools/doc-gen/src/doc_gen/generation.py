"""Document generation from outlines using LLM."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient, LLMResponse


class DocumentGenerator:
    """Generates markdown documentation from outlines using LLM."""

    def __init__(self, llm_client: LLMClient):
        """Initialize document generator.

        Args:
            llm_client: LLM client for API calls
        """
        self.client = llm_client

    def generate_document(
        self,
        outline: Dict[str, Any],
        source_files: Dict[str, str],  # {file_path: content}
        doc_purpose: str,
    ) -> str:
        """Generate markdown document from outline.

        Args:
            outline: Structured outline from Sprint 2
            source_files: Dict of file paths to contents
            doc_purpose: Documentation purpose

        Returns:
            Markdown document as string

        Raises:
            DocumentValidationError: If generated document is invalid
        """
        # 1. Create prompt with outline + sources
        prompt = self._create_prompt(outline, source_files, doc_purpose)

        # 2. Call LLM (no JSON mode - want markdown)
        response = self.client.generate(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            json_mode=False,  # Want markdown, not JSON
            temperature=0.7,
        )

        # 3. Validate markdown quality
        markdown = self._validate_markdown(response.content)

        # 4. Add frontmatter with metadata
        markdown = self._add_frontmatter(markdown, outline)

        return markdown

    def _get_system_prompt(self) -> str:
        """System prompt for document generation."""
        return """You are a technical documentation expert. Your task is to write comprehensive, clear documentation from a structured outline and source code.

Your documentation should:
1. Follow the outline structure exactly
2. Use the section-level prompts to guide what content to write
3. Write clear, accessible explanations
4. Include relevant code examples from sources
5. Use proper markdown formatting
6. Link concepts together logically
7. Be technically accurate and detailed

Focus on clarity and completeness. Write for a technical audience who wants to understand both the "what" and the "how"."""

    def _create_prompt(
        self, outline: Dict[str, Any], source_files: Dict[str, str], doc_purpose: str
    ) -> str:
        """Create user prompt for document generation.

        This uses the section-level "prompt" fields from Sprint 2 enhancement.

        Args:
            outline: Outline with sections containing "prompt" fields
            source_files: Dict of file paths to contents
            doc_purpose: Documentation purpose

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Generate technical documentation for: {doc_purpose}\n",
            f"\n## Document Title: {outline.get('title', 'Documentation')}\n",
            "\n## Outline Structure:\n",
        ]

        # Include outline sections with their prompts
        for i, section in enumerate(outline.get("sections", []), 1):
            heading = section.get("heading", f"Section {i}")
            section_prompt = section.get("prompt", "Write about this section")
            topics = section.get("topics", [])

            prompt_parts.append(f"\n### {i}. {heading}\n")
            prompt_parts.append(f"**Instructions:** {section_prompt}\n")
            if topics:
                prompt_parts.append(f"**Topics to cover:** {', '.join(topics)}\n")

        # Include source files mentioned in outline
        prompt_parts.append("\n## Source Files for Reference:\n")
        mentioned_files = self._extract_mentioned_files(outline)

        for file_path in mentioned_files:
            if file_path in source_files:
                content = source_files[file_path]

                # Truncate large files
                if len(content) > 8000:
                    content = content[:8000] + "\n... (truncated)"

                prompt_parts.append(f"\n### {file_path}\n```\n{content}\n```\n")

        prompt_parts.append(
            """
## Task:
Write comprehensive markdown documentation following the outline structure.

Requirements:
- Follow section headings from the outline exactly
- Use the section-level instructions to guide your writing
- Write clear explanations for each topic
- Include relevant code examples from the source files
- Use proper markdown formatting (headers, lists, code blocks)
- Be technically accurate
- Link related concepts
- Write for developers familiar with code

Do NOT include:
- Markdown frontmatter (will be added separately)
- Placeholder text like [TODO] or [To be written]
- Apologies or meta-commentary
- Explanations of what you're doing (just write the docs)

Start with the first section heading and write complete documentation.
"""
        )

        return "".join(prompt_parts)

    def _extract_mentioned_files(self, outline: Dict[str, Any]) -> List[str]:
        """Extract file paths mentioned in outline sources.

        Args:
            outline: Outline with sections containing sources

        Returns:
            Sorted list of unique file paths
        """
        files = set()

        for section in outline.get("sections", []):
            for source in section.get("sources", []):
                file_path = source.get("file")
                if file_path:
                    files.add(file_path)

        return sorted(files)

    def _validate_markdown(self, markdown: str) -> str:
        """Validate markdown quality.

        Basic validation in Sprint 3. Can enhance later.

        Args:
            markdown: Generated markdown content

        Returns:
            Validated markdown content

        Raises:
            DocumentValidationError: If validation fails
        """
        # Check it's not empty
        if not markdown.strip():
            raise DocumentValidationError("Generated document is empty")

        # Check it has some content
        if len(markdown) < 100:
            raise DocumentValidationError(
                f"Generated document is too short ({len(markdown)} chars, minimum 100)"
            )

        # Check for common issues
        if "[TODO]" in markdown or "[To be written]" in markdown:
            raise DocumentValidationError(
                "Generated document contains placeholder text"
            )

        return markdown

    def _add_frontmatter(self, markdown: str, outline: Dict[str, Any]) -> str:
        """Add YAML frontmatter to markdown.

        Frontmatter includes metadata for doc site (mkdocs, etc.)

        Args:
            markdown: Markdown content
            outline: Outline with metadata

        Returns:
            Markdown with frontmatter prepended
        """
        title = outline.get("title", "Documentation")
        metadata = outline.get("_metadata", {})
        generated_at = metadata.get("generated_at")

        frontmatter = f"""---
title: {title}
generated: true
generated_at: {generated_at}
model: {metadata.get("model", "unknown")}
---

"""

        return frontmatter + markdown


class DocumentValidationError(Exception):
    """Document validation failed."""

    pass
