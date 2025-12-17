"""Documentation validator with iterative fixing using LLM."""

import json
import urllib.request
from pathlib import Path
from typing import Any
from urllib.error import URLError

from doc_gen.llm_client import ClaudeClient
from doc_gen.generate.outline_models import DocumentOutline


class ValidationIssue:
    """Represents a documentation validation issue."""
    
    def __init__(self, priority: str, section: str, description: str, 
                 sources: list[str], recommendation: str):
        self.priority = priority
        self.section = section
        self.description = description
        self.sources = sources
        self.recommendation = recommendation
    
    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "section": self.section,
            "description": self.description,
            "sources": self.sources,
            "recommendation": self.recommendation
        }


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, iteration: int, needs_fixing: bool, issues: list[ValidationIssue]):
        self.iteration = iteration
        self.needs_fixing = needs_fixing
        self.issues = issues
    
    @property
    def high_priority_count(self) -> int:
        return sum(1 for issue in self.issues if issue.priority == "HIGH")
    
    @property
    def medium_priority_count(self) -> int:
        return sum(1 for issue in self.issues if issue.priority == "MEDIUM")
    
    @property
    def low_priority_count(self) -> int:
        return sum(1 for issue in self.issues if issue.priority == "LOW")
    
    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "needs_fixing": self.needs_fixing,
            "total_issues": len(self.issues),
            "high_priority_count": self.high_priority_count,
            "medium_priority_count": self.medium_priority_count,
            "low_priority_count": self.low_priority_count,
            "issues": [issue.to_dict() for issue in self.issues]
        }


class DocumentValidator:
    """Validates and fixes documentation iteratively using LLM."""
    
    MAX_ITERATIONS = 5
    
    def __init__(self, project_root: Path, llm_client: ClaudeClient = None, 
                 progress_callback=None):
        """Initialize validator.
        
        Args:
            project_root: Project root directory
            llm_client: LLM client for validation/fixing (optional)
            progress_callback: Callback for progress updates (callable(str))
        """
        self.project_root = project_root
        self.llm_client = llm_client or ClaudeClient()
        self.progress_callback = progress_callback
    
    def _fetch_source_file(self, url: str) -> str | None:
        """Fetch source file content from URL.
        
        Args:
            url: Source file URL (should be raw GitHub URL)
        
        Returns:
            File content or None if fetch failed
        """
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode('utf-8')
        except (URLError, TimeoutError, UnicodeDecodeError):
            return None
    
    def _read_source_files(self, outline: DocumentOutline) -> dict[str, str]:
        """Read all source files referenced in the outline.
        
        Args:
            outline: Loaded outline
        
        Returns:
            Dict mapping source URLs to their content
        """
        sources = {}
        
        def collect_sources(sections):
            for section in sections:
                for source in section.sources:
                    if source.file not in sources:
                        # Convert to raw URL if needed
                        url = source.file
                        if 'github.com' in url and '/blob/' in url:
                            url = url.replace('github.com', 'raw.githubusercontent.com')
                            url = url.replace('/blob/', '/')
                        
                        if self.progress_callback:
                            self.progress_callback(f"  📥 Fetching: {source.file}")
                        
                        content = self._fetch_source_file(url)
                        if content:
                            sources[source.file] = content
                        else:
                            if self.progress_callback:
                                self.progress_callback(f"  ⚠️  Failed to fetch: {source.file}")
                
                # Recurse into subsections
                if section.sections:
                    collect_sources(section.sections)
        
        collect_sources(outline.sections)
        return sources
    
    def check_completeness(self, staged_file: Path, outline_file: Path, 
                          iteration: int = 1) -> ValidationResult:
        """Check documentation completeness against outline and sources.
        
        Args:
            staged_file: Path to staged markdown file
            outline_file: Path to outline JSON
            iteration: Current iteration number
        
        Returns:
            ValidationResult with issues found
        """
        if self.progress_callback:
            self.progress_callback(f"\n🔍 Iteration {iteration}: Checking completeness...")
        
        # Load files
        md_content = staged_file.read_text()
        outline = DocumentOutline.load(outline_file)
        
        # Fetch all source files
        if self.progress_callback:
            self.progress_callback("📚 Fetching source files...")
        source_contents = self._read_source_files(outline)
        
        if self.progress_callback:
            self.progress_callback(f"✓ Loaded {len(source_contents)} source files")
        
        # Build context for LLM
        sources_text = "\n\n".join([
            f"=== SOURCE: {url} ===\n{content[:5000]}{'...(truncated)' if len(content) > 5000 else ''}"
            for url, content in source_contents.items()
        ])
        
        outline_json = json.dumps(outline.to_dict(), indent=2)
        
        # Create prompt for completeness check
        prompt = f"""DOCUMENTATION COMPLETENESS CHECK - ITERATION {iteration}

Task: Check if material from source files listed in the outline is MISSING from the generated documentation.

STAGED MARKDOWN:
```markdown
{md_content[:10000]}{'...(truncated)' if len(md_content) > 10000 else ''}
```

OUTLINE (structure and source references):
```json
{outline_json[:5000]}{'...(truncated)' if len(outline_json) > 5000 else ''}
```

SOURCE FILES:
{sources_text[:15000]}{'...(truncated)' if len(sources_text) > 15000 else ''}

INSTRUCTIONS:
1. For EACH section in the outline:
   a. Find the corresponding section in the staged markdown
   b. Read the section's prompt (what should be documented)
   c. Read the reasoning for each source file
   d. Check if material from those sources that SHOULD be present is MISSING

2. Evaluation criteria (determine "should be present"):
   - Document intent: {outline.document_instruction}
   - Section prompt: What did the outline ask for?
   - Source content: What relevant material exists?
   - Reasoning: Why was each source included?

3. Priority classification:
   - HIGH: Missing functional examples, critical API details, core concepts mentioned in reasoning
   - MEDIUM: Missing key details, important context, patterns mentioned in reasoning
   - LOW: Minor details, polish, formatting

Respond with valid JSON only (no markdown, no extra text):
{{
  "needs_fixing": true/false,
  "issues": [
    {{
      "priority": "HIGH|MEDIUM|LOW",
      "section": "## Section Heading",
      "description": "Specific material from source that is missing",
      "sources": ["file URLs where this material exists"],
      "recommendation": "What specific content should be added"
    }}
  ]
}}

Focus on HIGH and MEDIUM priority issues only. Be specific about what's missing from the sources."""

        # Call LLM
        if self.progress_callback:
            self.progress_callback("🤖 Analyzing with LLM...")
        
        response = self.llm_client.generate(
            prompt,
            temperature=0.1,
            max_tokens=4096,
            location=f"validator:check_completeness:iteration_{iteration}"
        )
        
        # Parse response
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_clean = response.strip()
            if response_clean.startswith('```'):
                # Remove markdown code block
                lines = response_clean.split('\n')
                response_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_clean
            
            result_data = json.loads(response_clean)
            
            # Create ValidationIssue objects
            issues = []
            for issue_data in result_data.get("issues", []):
                issues.append(ValidationIssue(
                    priority=issue_data.get("priority", "LOW"),
                    section=issue_data.get("section", ""),
                    description=issue_data.get("description", ""),
                    sources=issue_data.get("sources", []),
                    recommendation=issue_data.get("recommendation", "")
                ))
            
            return ValidationResult(
                iteration=iteration,
                needs_fixing=result_data.get("needs_fixing", False),
                issues=issues
            )
        
        except json.JSONDecodeError as e:
            if self.progress_callback:
                self.progress_callback(f"⚠️  Failed to parse LLM response as JSON: {e}")
                self.progress_callback(f"Response was: {response[:500]}")
            
            # Return empty result on parse failure
            return ValidationResult(iteration=iteration, needs_fixing=False, issues=[])
    
    def fix_issues(self, staged_file: Path, validation_result: ValidationResult, 
                   outline_file: Path) -> bool:
        """Fix documentation issues using LLM.
        
        Args:
            staged_file: Path to staged markdown file
            validation_result: Validation result with issues to fix
            outline_file: Path to outline JSON
        
        Returns:
            True if fixes were applied, False otherwise
        """
        # Filter for HIGH and MEDIUM priority only
        issues_to_fix = [
            issue for issue in validation_result.issues 
            if issue.priority in ("HIGH", "MEDIUM")
        ]
        
        if not issues_to_fix:
            if self.progress_callback:
                self.progress_callback("✓ No HIGH/MEDIUM priority issues to fix")
            return False
        
        if self.progress_callback:
            self.progress_callback(f"\n🔧 Fixing {len(issues_to_fix)} issues...")
        
        # Load current markdown
        md_content = staged_file.read_text()
        
        # Load outline for context
        outline = DocumentOutline.load(outline_file)
        source_contents = self._read_source_files(outline)
        
        # Build sources context
        sources_text = "\n\n".join([
            f"=== SOURCE: {url} ===\n{content[:3000]}{'...(truncated)' if len(content) > 3000 else ''}"
            for url, content in source_contents.items()
        ])
        
        # Create fix prompt
        issues_json = json.dumps([issue.to_dict() for issue in issues_to_fix], indent=2)
        
        prompt = f"""FIX DOCUMENTATION ISSUES - ITERATION {validation_result.iteration}

Task: Fix HIGH and MEDIUM priority issues in the documentation.

CURRENT MARKDOWN:
```markdown
{md_content}
```

ISSUES TO FIX:
```json
{issues_json}
```

SOURCE FILES (for reference):
{sources_text[:10000]}{'...(truncated)' if len(sources_text) > 10000 else ''}

INSTRUCTIONS:
1. For EACH issue:
   a. Find the exact section in the markdown
   b. Read the source files mentioned
   c. Add the missing content to the appropriate location
   d. Maintain document structure, style, and formatting
   e. Ensure code examples are functional

2. Do NOT fix LOW priority issues
3. Keep all existing content - only ADD missing material
4. Maintain consistent markdown formatting

Respond with the COMPLETE UPDATED MARKDOWN (no JSON, no explanations, just the markdown):"""

        # Call LLM
        if self.progress_callback:
            self.progress_callback("🤖 Generating fixes with LLM...")
        
        response = self.llm_client.generate(
            prompt,
            temperature=0.2,
            max_tokens=8000,
            location=f"validator:fix_issues:iteration_{validation_result.iteration}"
        )
        
        # Clean response (remove markdown code blocks if present)
        fixed_content = response.strip()
        if fixed_content.startswith('```markdown'):
            lines = fixed_content.split('\n')
            fixed_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else fixed_content
        elif fixed_content.startswith('```'):
            lines = fixed_content.split('\n')
            fixed_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else fixed_content
        
        # Write fixed content
        staged_file.write_text(fixed_content)
        
        if self.progress_callback:
            self.progress_callback(f"✓ Applied fixes to {staged_file}")
        
        return True
    
    def validate_and_fix(self, staged_file: Path, outline_file: Path) -> dict[str, Any]:
        """Run iterative validation and fixing process.
        
        Args:
            staged_file: Path to staged markdown file
            outline_file: Path to outline JSON
        
        Returns:
            Dict with final status and iteration history
        """
        if self.progress_callback:
            self.progress_callback("\n" + "=" * 80)
            self.progress_callback("DOCUMENTATION VALIDATION & ITERATIVE FIXING")
            self.progress_callback("=" * 80)
        
        history = []
        
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            # Check completeness
            validation_result = self.check_completeness(staged_file, outline_file, iteration)
            
            # Log results
            if self.progress_callback:
                self.progress_callback(f"\n📊 Iteration {iteration} Results:")
                self.progress_callback(f"  Total issues: {len(validation_result.issues)}")
                self.progress_callback(f"  HIGH: {validation_result.high_priority_count}")
                self.progress_callback(f"  MEDIUM: {validation_result.medium_priority_count}")
                self.progress_callback(f"  LOW: {validation_result.low_priority_count}")
            
            history.append({
                "iteration": iteration,
                "check": validation_result.to_dict(),
                "fixes_applied": False
            })
            
            # If no issues or no HIGH/MEDIUM issues, we're done
            if not validation_result.needs_fixing or \
               (validation_result.high_priority_count == 0 and validation_result.medium_priority_count == 0):
                if self.progress_callback:
                    self.progress_callback(f"\n✅ PASSED at iteration {iteration}!")
                return {
                    "status": "PASSED",
                    "iterations": iteration,
                    "history": history
                }
            
            # Fix issues
            fixes_applied = self.fix_issues(staged_file, validation_result, outline_file)
            history[-1]["fixes_applied"] = fixes_applied
            
            if not fixes_applied:
                if self.progress_callback:
                    self.progress_callback(f"\n✅ No fixes needed at iteration {iteration}")
                return {
                    "status": "PASSED",
                    "iterations": iteration,
                    "history": history
                }
        
        # Max iterations reached
        if self.progress_callback:
            self.progress_callback(f"\n⚠️  Reached maximum iterations ({self.MAX_ITERATIONS})")
            self.progress_callback("🔴 HUMAN REVIEW REQUIRED")
        
        return {
            "status": "NEEDS_REVIEW",
            "iterations": self.MAX_ITERATIONS,
            "history": history,
            "message": f"Document still has issues after {self.MAX_ITERATIONS} iterations"
        }
