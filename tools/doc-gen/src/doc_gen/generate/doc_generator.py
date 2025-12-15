"""Document generation from outline."""

import re
import urllib.request
from pathlib import Path
from urllib.error import URLError

from doc_gen.generate.outline_models import DocumentOutline, Section
from doc_gen.llm_client import ClaudeClient


class DocumentGenerator:
    """Generates complete documents from outlines using LLM.

    Uses depth-first traversal to generate content, maintaining context
    from parent sections to child sections for coherent flow.
    """

    def __init__(self, project_root: Path = Path.cwd(), llm_client=None, progress_callback=None):
        """Initialize generator.

        Args:
            project_root: Project root directory for reading source files
            llm_client: LLM client for content generation (optional, will create if None)
            progress_callback: Optional callback for progress updates (callable(str))
        """
        self.project_root = project_root
        self.llm_client = llm_client or ClaudeClient()
        self.section_context = []  # Stack of parent section content for DFS context flow
        self.generated_document = []  # Full document content generated so far (for coherence)
        self.progress_callback = progress_callback
        self.sections_completed = 0
        self.total_sections = 0
        self.outline_updated = False  # Track if outline was modified with new commit hashes

    def generate_from_outline(self, outline_path: Path, output_path: str) -> str:
        """Generate complete document from outline.

        Args:
            outline_path: Path to outline.json file
            output_path: Where to write the generated documentation (relative to project root)

        Returns:
            Generated document content as string
        """
        # Load outline
        outline = DocumentOutline.load(outline_path)

        # Store outline for access in section generation
        self.outline = outline
        self.outline_path = outline_path

        # Count total sections for progress
        self.total_sections = self._count_sections(outline.sections)
        self.sections_completed = 0

        if self.progress_callback:
            self.progress_callback(f"📝 Generating {self.total_sections} sections...\n")

        # Generate content for all sections (top-down DFS)
        document_parts = []

        # Generate sections
        for section in outline.sections:
            section_content = self._generate_section(section)
            document_parts.append(section_content)

        # Save updated outline if any commit hashes were updated
        if self.outline_updated:
            if self.progress_callback:
                self.progress_callback(f"\n💾 Updating outline with current commit hashes...\n")
            outline.save(outline_path)

        # Assemble complete document
        full_document = "\n\n".join(document_parts)

        # Write to output file (use provided output_path instead of outline's)
        output_file = self.project_root / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(full_document)

        if self.progress_callback:
            self.progress_callback(f"\n✅ Document written to: {output_path}\n")

        return full_document

    def _count_sections(self, sections: list) -> int:
        """Count total sections recursively."""
        count = len(sections)
        for section in sections:
            count += self._count_sections(section.sections)
        return count

    def _generate_section(self, section: Section, depth: int = 0) -> str:
        """Generate content for a section recursively using DFS.

        DFS approach: Generate parent content first, then children with parent context.

        Args:
            section: Section to generate
            depth: Current nesting depth (for indentation tracking)

        Returns:
            Generated section content with subsections
        """
        parts = []

        # Show progress
        self.sections_completed += 1
        if self.progress_callback:
            indent = "  " * depth
            source_count = len(section.sources)
            progress_msg = (
                f"{indent}[{self.sections_completed}/{self.total_sections}] "
                f"Generating: {section.heading}\n"
                f"{indent}    Sources: {source_count} file{'s' if source_count != 1 else ''}\n"
            )
            self.progress_callback(progress_msg)

        # Add heading
        parts.append(section.heading)

        # Add heading to generated document BEFORE generating content
        # This ensures the LLM sees the heading in context and won't duplicate it
        self.generated_document.append(section.heading)

        # Generate content for this level using LLM with full document context
        content = self._generate_section_content(section)
        parts.append(content)

        # Add the content to generated document (heading already added above)
        self.generated_document.append(content)

        # Show completion
        if self.progress_callback:
            indent = "  " * depth
            char_count = len(content)
            self.progress_callback(f"{indent}    ✓ Complete ({char_count} chars)\n")

        # Push this section's content onto context stack for children (DFS)
        self.section_context.append(content)

        # Recursively generate subsections with parent context
        if section.sections:
            subsection_parts = []
            for subsection in section.sections:
                subsection_content = self._generate_section(subsection, depth + 1)
                subsection_parts.append(subsection_content)

            # Add subsections
            if subsection_parts:
                parts.append("\n\n".join(subsection_parts))

        # Pop context when leaving this section (maintain DFS stack)
        self.section_context.pop()

        return "\n\n".join(parts)

    def _parse_github_url(self, url: str) -> tuple[str, str, str] | None:
        """Parse GitHub URL into (owner, repo, file_path).

        Args:
            url: GitHub URL (blob or raw format)

        Returns:
            Tuple of (owner, repo, file_path) or None if not a valid GitHub URL

        Examples:
            https://github.com/microsoft/amplifier/blob/main/README.md
            → ("microsoft", "amplifier", "README.md")
            
            https://raw.githubusercontent.com/microsoft/amplifier/abc123/README.md
            → ("microsoft", "amplifier", "README.md")
        """
        # Try blob URL pattern: github.com/owner/repo/blob/branch/path
        blob_pattern = r'^https?://github\.com/([^/]+)/([^/]+)/blob/[^/]+/(.+)$'
        match = re.match(blob_pattern, url)
        if match:
            return (match.group(1), match.group(2), match.group(3))
        
        # Try raw URL pattern: raw.githubusercontent.com/owner/repo/commit/path
        raw_pattern = r'^https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/[^/]+/(.+)$'
        match = re.match(raw_pattern, url)
        if match:
            return (match.group(1), match.group(2), match.group(3))
        
        return None

    def _github_url_to_raw(self, url: str, commit: str) -> str | None:
        """Convert GitHub blob URL to raw URL with specific commit.

        Args:
            url: GitHub blob URL
            commit: Commit hash to fetch

        Returns:
            Raw GitHub URL with commit, or None if parsing failed

        Example:
            https://github.com/microsoft/amplifier/blob/main/README.md + "abc123"
            → https://raw.githubusercontent.com/microsoft/amplifier/abc123/README.md
        """
        parsed = self._parse_github_url(url)
        if not parsed:
            return None
        
        owner, repo, file_path = parsed
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/{file_path}"

    def _fetch_remote_file(self, url: str) -> str | None:
        """Fetch content from a remote URL.

        Args:
            url: URL to fetch

        Returns:
            File content as string, or None if fetch failed
        """
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')
                return content
        except (URLError, TimeoutError, UnicodeDecodeError):
            return None

    def _read_source_files(self, section: Section) -> str:
        """Read and format source files for a section.

        Fetches source files from GitHub URLs at specific commit hashes.

        Args:
            section: Section with source file references

        Returns:
            Formatted source file content
        """
        if not section.sources:
            return "No source files provided for this section."

        source_parts = []
        for source in section.sources:
            # All source files must be GitHub URLs
            if not source.file.startswith(("http://", "https://")):
                source_parts.append(f"**{source.file}** (must be a GitHub URL)")
                continue
            
            # Require commit hash for version pinning
            if not source.commit:
                source_parts.append(f"**{source.file}** (requires commit hash)")
                continue
            
            # Convert to raw URL with commit
            raw_url = self._github_url_to_raw(source.file, source.commit)
            if not raw_url:
                source_parts.append(f"**{source.file}** (invalid GitHub URL)")
                continue
            
            # Fetch remote content
            content = self._fetch_remote_file(raw_url)
            if content is None:
                source_parts.append(f"**{source.file}** (failed to fetch from GitHub)")
                continue
            
            # Build source entry
            source_entry_parts = [f"**File: {source.file}**"]
            if hasattr(source, 'reasoning') and source.reasoning:
                source_entry_parts.append(f"**Why this file is relevant:** {source.reasoning}")
            source_entry_parts.append(f"```\n{content}\n```")
            source_parts.append("\n".join(source_entry_parts))

        return "\n\n".join(source_parts)

    def _generate_section_content(self, section: Section) -> str:
        """Generate content for a section using LLM.

        Passes full document generated so far for coherence and to avoid duplication.

        Args:
            section: Section to generate content for

        Returns:
            Generated content
        """
        # Build context from the full document generated so far
        document_so_far = ""
        if self.generated_document:
            document_so_far = "\n\n".join(self.generated_document)
            # Truncate if too long (keep last 5000 chars for context)
            if len(document_so_far) > 5000:
                document_so_far = "...\n\n" + document_so_far[-5000:]

        # Read source files
        source_content = self._read_source_files(section)

        # Build comprehensive subsection structure visibility
        def collect_all_subsection_headings(sections, depth=0):
            """Recursively collect ALL subsection headings with hierarchy."""
            headings = []
            for s in sections:
                indent = "  " * depth
                headings.append(f"{indent}{s.heading}")
                if s.sections:
                    headings.extend(collect_all_subsection_headings(s.sections, depth + 1))
            return headings

        # Always show subsection constraints (even if no subsections)
        if section.sections:
            all_subsection_headings = collect_all_subsection_headings(section.sections)
            subsection_count = len(all_subsection_headings)

            subsection_guidance = f"""

==============================================================================
CRITICAL: EXACT SUBSECTION STRUCTURE - NO DEVIATIONS ALLOWED
==============================================================================

The section "{section.heading}" has EXACTLY {subsection_count} subsection(s) defined in the outline.
These are THE ONLY subsections that will exist. They are shown below with full hierarchy:

COMPLETE SUBSECTION STRUCTURE (these will be generated separately):
{chr(10).join(all_subsection_headings)}

ABSOLUTE RULES:
  ✗ DO NOT write content for ANY of the subsections listed above
  ✗ DO NOT create ANY subsections beyond those listed above
  ✗ DO NOT add extra sections like "Overview", "Introduction", "Key Concepts", etc.
  ✗ DO NOT include ANY markdown headings at or below the {section.heading[:2]} level
  ✗ The subsections shown above are COMPLETE - no additions allowed

YOUR OUTPUT MUST CONTAIN:
  ✓ ONLY introductory/explanatory content for "{section.heading}" itself
  ✓ NO markdown headings of any kind (the {subsection_count} subsections above will appear automatically)
  ✓ Plain text, tables, code blocks, lists - but NO headings

The {subsection_count} subsection(s) above will appear AFTER your content in the exact order shown.

==============================================================================
"""
        else:
            subsection_guidance = f"""

==============================================================================
CRITICAL: NO SUBSECTIONS FOR THIS SECTION
==============================================================================

The section "{section.heading}" has NO subsections defined in the outline.

ABSOLUTE RULES:
  ✗ DO NOT create ANY subsections of any kind
  ✗ DO NOT add headings like "Overview", "Examples", "Usage", etc.
  ✗ DO NOT include ANY markdown headings at or below the {section.heading[:2]} level

YOUR OUTPUT MUST CONTAIN:
  ✓ ONLY content for "{section.heading}" itself
  ✓ NO markdown headings of any kind
  ✓ Plain text, tables, code blocks, lists - but NO headings

==============================================================================
"""

        # Build context section with clear boundaries
        context_section = ""
        if document_so_far:
            context_section = f"""

==============================================================================
PREVIOUSLY WRITTEN CONTENT (for context and continuity)
==============================================================================

{document_so_far}

==============================================================================
END OF PREVIOUSLY WRITTEN CONTENT
==============================================================================

CRITICAL Guidelines for Using Previous Content:
- The content above is PROVIDED FOR CONTEXT ONLY
- DO NOT duplicate or restate information already covered
- DO NOT copy content from earlier sections
- DO NOT repeat prerequisites, installation steps, or concepts already explained
- Reference previous sections briefly if needed (e.g., "As mentioned earlier...")
- Focus ONLY on NEW information for THIS specific section
- Ensure this section flows naturally from what came before
"""
        else:
            context_section = "\n(This is the first section - no previous content exists yet.)\n"

        # Build document instruction context
        document_instruction = ""
        if hasattr(self, 'outline') and self.outline.document_instruction:
            document_instruction = f"""
==============================================================================
DOCUMENT INSTRUCTION
==============================================================================
{self.outline.document_instruction}

"""

        prompt = f"""You are a technical documentation writer. Generate content for the following section.
{document_instruction}
==============================================================================
YOUR TASK
==============================================================================

{section.prompt}

==============================================================================
SOURCE MATERIALS (reference these for accurate information)
==============================================================================

{source_content}
{context_section}{subsection_guidance}

==============================================================================
IMPORTANT: EXCLUDE DEPRECATED CODE
==============================================================================

- DO NOT document any code, features, or commands marked as DEPRECATED
- DO NOT document any code with comments indicating it's outdated or replaced
- If you discover deprecated code in source files, IGNORE IT completely
- Only document current, active, non-deprecated functionality
- If a feature has been superseded by a newer approach, document ONLY the new approach

==============================================================================
OUTPUT INSTRUCTIONS
==============================================================================

- Write clear, concise, beginner-friendly content
- Use concrete examples from the source files (excluding deprecated code)
- Focus on practical, actionable information that hasn't been covered yet
- Use proper markdown formatting
- Keep the tone professional but approachable
- Ensure coherence with previous sections but avoid redundancy

Generate the content now:"""

        # Generate content using LLM with outline-specified configuration
        content = self.llm_client.generate(
            prompt,
            temperature=self.outline.temperature,
            model=self.outline.model,
            max_tokens=self.outline.max_response_tokens,
            location="generate/doc_generator.py:generate_from_outline"
        )

        return content.strip()
