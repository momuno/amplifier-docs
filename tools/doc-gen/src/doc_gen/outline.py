"""Outline generation using LLM."""

import json
import time
from typing import Any, Dict

from .llm_client import LLMClient


class OutlineGenerator:
    """Generates structured documentation outlines using LLM."""

    def __init__(self, llm_client: LLMClient):
        """Initialize outline generator.

        Args:
            llm_client: LLM client for API calls
        """
        self.client = llm_client

    def generate_outline(
        self,
        source_files: Dict[str, str],  # {file_path: content}
        commit_hashes: Dict[str, str],  # {file_path: commit_hash}
        purpose: str,
    ) -> Dict[str, Any]:
        """Generate outline from source files.

        Args:
            source_files: Dict of file paths to contents
            commit_hashes: Dict of file paths to commit hashes
            purpose: Documentation purpose (from sources.yaml)

        Returns:
            Outline dict with embedded commit hashes

        Raises:
            OutlineValidationError: If LLM returns invalid outline
        """
        # 1. Create prompt with source context
        prompt = self._create_prompt(source_files, purpose)

        # 2. Call LLM with JSON mode
        response = self.client.generate(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            json_mode=True,
            temperature=0.7,  # Balanced creativity
        )

        # 3. Parse and validate JSON response
        outline = self._parse_and_validate(response.content)

        # 4. Embed commit hashes for change tracking
        outline = self._embed_commit_hashes(outline, commit_hashes)

        # 5. Add generation metadata
        outline["_metadata"] = {
            "generated_at": time.time(),
            "model": response.model,
            "tokens_used": response.tokens_used,
            "duration_seconds": response.duration_seconds,
        }

        return outline

    def _get_system_prompt(self) -> str:
        """System prompt for outline generation."""
        return """You are a technical documentation expert. Your task is to analyze source code and create a structured outline for comprehensive documentation.

Your outline should:
1. Identify the main purpose and functionality
2. Break down into logical sections
3. Note important implementation details
4. Reference specific source files for each topic
5. Be structured for a technical audience

Return your response as valid JSON matching the provided schema."""

    def _create_prompt(self, source_files: Dict[str, str], purpose: str) -> str:
        """Create user prompt with source context.

        This is where prompt engineering happens!
        Expect to iterate on this during Sprint 2.

        Args:
            source_files: Dict of file paths to contents
            purpose: Documentation purpose

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Create a documentation outline for: {purpose}\n",
            "\n## Source Files:\n",
        ]

        for file_path, content in source_files.items():
            # Truncate very large files
            if len(content) > 10000:
                content = content[:10000] + "\n... (truncated)"

            prompt_parts.append(f"\n### {file_path}\n```\n{content}\n```\n")

        prompt_parts.append(
            """
## Task:
Generate a JSON outline with this structure:
{
  "title": "Clear, descriptive title",
  "sections": [
    {
      "heading": "Section name",
      "topics": ["Topic 1", "Topic 2"],
      "sources": [
        {
          "file": "path/to/file",
          "relevant_lines": "20-45",
          "note": "What to cover from this source"
        }
      ]
    }
  ]
}

Focus on:
- Clear section organization
- Specific line ranges where relevant
- Notes on what each source contributes
- Logical flow from overview to details
"""
        )

        return "".join(prompt_parts)

    def _parse_and_validate(self, json_string: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON response.

        This WILL fail sometimes. LLMs aren't perfect.

        Args:
            json_string: JSON string from LLM

        Returns:
            Parsed and validated outline dict

        Raises:
            OutlineValidationError: If JSON is invalid or missing required fields
        """
        # Strip markdown code fences if present (common LLM behavior)
        json_string = json_string.strip()
        if json_string.startswith("```json"):
            json_string = json_string[7:]  # Remove ```json
        elif json_string.startswith("```"):
            json_string = json_string[3:]  # Remove ```
        if json_string.endswith("```"):
            json_string = json_string[:-3]  # Remove trailing ```
        json_string = json_string.strip()
        
        try:
            outline = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise OutlineValidationError(
                f"LLM returned invalid JSON: {e}\n"
                f"Response: {json_string[:500]}..."
            )

        # Validate required fields
        required_fields = ["title", "sections"]
        for field in required_fields:
            if field not in outline:
                raise OutlineValidationError(
                    f"Missing required field: {field}\n" f"Got: {list(outline.keys())}"
                )

        # Validate sections structure
        if not isinstance(outline["sections"], list):
            raise OutlineValidationError("'sections' must be a list")

        for i, section in enumerate(outline["sections"]):
            if "heading" not in section:
                raise OutlineValidationError(f"Section {i} missing 'heading'")

        return outline

    def _embed_commit_hashes(
        self, outline: Dict[str, Any], commit_hashes: Dict[str, str]
    ) -> Dict[str, Any]:
        """Embed commit hashes in outline for change detection.

        Args:
            outline: Parsed outline dict
            commit_hashes: Dict of file paths to commit hashes

        Returns:
            Outline with embedded commit hashes
        """
        # Add top-level commit hash mapping
        outline["_commit_hashes"] = commit_hashes

        # Also embed in each source reference
        for section in outline.get("sections", []):
            for source in section.get("sources", []):
                file_path = source.get("file")
                if file_path in commit_hashes:
                    source["commit_hash"] = commit_hashes[file_path]

        return outline


class OutlineValidationError(Exception):
    """Outline JSON validation failed."""

    pass
