# Sprint 3: Document Generation (Second LLM Integration)

**Duration:** 1 week  
**Goal:** Generate markdown documents from outlines using LLM with staging workflow  
**Value Delivered:** End-to-end pipeline working (single repo: sources → outline → document → staging)

---

## 🎯 Why This Sprint?

Sprint 3 completes the **two-phase generation pipeline**. Sprint 2 gave you outline generation; now you add document generation from those outlines.

**Good news:** Sprint 3 will be **faster** than Sprint 2 because:
1. LLM client already built (reuse from Sprint 2)
2. Error handling patterns established
3. Prompt engineering experience gained
4. Just need to build on proven patterns

By the end of Sprint 3, you'll have:
- Document generation from outlines
- Staging workflow (docs go to staging, not live)
- End-to-end single-repo pipeline working
- Quality document prompts (some iteration expected)
- Confidence the full workflow works

After Sprint 3, you can generate documentation from a single repository end-to-end. Sprint 4 adds multi-repo support. Sprint 5 adds change detection and review. Sprint 6 adds orchestration.

---

## 📦 Deliverables

### 1. Document Generator (`generation.py`)
**Estimated Lines:** ~220 lines + ~130 lines tests

**What it does:**
- Generates markdown documentation from outline using LLM
- Constructs prompts with outline structure + source context
- Validates markdown output quality
- Writes to staging directory (not live docs)
- Preserves frontmatter and metadata

**Why this sprint:**
Second phase of pipeline - cheaper doc generation from expensive outline. Enables iteration on doc quality without re-outlining.

**Implementation notes:**
```python
from pathlib import Path
from typing import Dict, Any, List
from .llm_client import LLMClient, LLMResponse
from .metadata import MetadataManager

class DocumentGenerator:
    """Generates markdown documentation from outlines using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        self.client = llm_client
        
    def generate_document(
        self, 
        outline: Dict[str, Any],
        source_files: Dict[str, str],  # {file_path: content}
        doc_purpose: str
    ) -> str:
        """Generate markdown document from outline.
        
        Args:
            outline: Structured outline from Sprint 2
            source_files: Dict of file paths to contents
            doc_purpose: Documentation purpose
            
        Returns:
            Markdown document as string
        """
        # 1. Create prompt with outline + sources
        prompt = self._create_prompt(outline, source_files, doc_purpose)
        
        # 2. Call LLM (no JSON mode - want markdown)
        response = self.client.generate(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            json_mode=False,  # Want markdown, not JSON
            temperature=0.7
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
2. Write clear, accessible explanations
3. Include relevant code examples from sources
4. Use proper markdown formatting
5. Link concepts together logically
6. Be technically accurate and detailed

Focus on clarity and completeness. Write for a technical audience who wants to understand both the "what" and the "how"."""
    
    def _create_prompt(
        self, 
        outline: Dict[str, Any], 
        source_files: Dict[str, str],
        doc_purpose: str
    ) -> str:
        """Create user prompt for document generation.
        
        Sprint 3: Iterate on this based on output quality.
        """
        prompt_parts = [
            f"Generate technical documentation for: {doc_purpose}\n",
            f"\n## Outline to Follow:\n",
            f"```json\n{json.dumps(outline, indent=2)}\n```\n",
            f"\n## Source Files for Reference:\n"
        ]
        
        # Include source files mentioned in outline
        mentioned_files = self._extract_mentioned_files(outline)
        
        for file_path in mentioned_files:
            if file_path in source_files:
                content = source_files[file_path]
                
                # Truncate large files
                if len(content) > 8000:
                    content = content[:8000] + "\n... (truncated)"
                
                prompt_parts.append(f"\n### {file_path}\n```\n{content}\n```\n")
        
        prompt_parts.append("""
\n## Task:
Write comprehensive markdown documentation following the outline structure.

Requirements:
- Follow section headings from the outline
- Write clear explanations for each topic
- Include relevant code examples
- Use proper markdown formatting (headers, lists, code blocks)
- Be technically accurate
- Link related concepts
- Write for developers familiar with code

Do NOT include:
- Markdown frontmatter (will be added separately)
- Placeholder text like [TODO] or [To be written]
- Apologies or meta-commentary

Start with the first section heading and write complete documentation.
""")
        
        return "".join(prompt_parts)
    
    def _extract_mentioned_files(self, outline: Dict[str, Any]) -> List[str]:
        """Extract file paths mentioned in outline sources."""
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
        """
        # Check it's not empty
        if not markdown.strip():
            raise DocumentValidationError("Generated document is empty")
        
        # Check it has some content
        if len(markdown) < 100:
            raise DocumentValidationError(
                "Generated document is too short (< 100 chars)"
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
        """
        title = outline.get("title", "Documentation")
        generated_at = outline.get("_metadata", {}).get("generated_at")
        
        frontmatter = f"""---
title: {title}
generated: true
generated_at: {generated_at}
---

"""
        
        return frontmatter + markdown
    
    def save_to_staging(
        self, 
        content: str, 
        metadata_mgr: MetadataManager
    ) -> Path:
        """Write generated content to staging directory."""
        staging_path = metadata_mgr.get_staging_path()
        
        # Ensure staging directory exists
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        staging_path.write_text(content)
        
        return staging_path

class DocumentValidationError(Exception):
    """Document validation failed."""
    pass
```

**Key decisions:**
- No JSON mode (want natural markdown)
- Include only sources mentioned in outline (token efficiency)
- Basic validation (can enhance later)
- Add frontmatter automatically
- Save to staging (never directly to live)
- Reuse outline metadata for tracking

---

### 2. Generate Document Command (`cli.py` update)
**Estimated Lines:** ~120 lines + ~90 lines tests

**What it does:**
- New command: `doc-gen generate-doc <doc-path>`
- Loads config, outline, and sources
- Re-clones repository (or uses cache)
- Calls DocumentGenerator
- Saves to staging directory
- Reports success with file location

**Why this sprint:**
User-facing interface for document generation. Completes the two-phase workflow.

**Implementation notes:**
```python
@cli.command()
@click.argument('doc-path', type=click.Path())
@click.pass_context
def generate_doc(ctx, doc_path: str):
    """Generate markdown document from outline.
    
    Requires outline to exist (run: doc-gen generate-outline <doc-path>)
    Document is saved to staging directory for review.
    
    Example:
      doc-gen generate-doc docs/modules/providers/openai.md
    """
    config = ctx.obj['config']
    metadata = MetadataManager(doc_path)
    
    try:
        # 1. Load outline
        click.echo(f"Loading outline for {doc_path}...")
        outline = metadata.read_outline()
        
        # 2. Load sources config
        sources_config = metadata.read_sources()
        
        # 3. Clone repository and read files
        click.echo("Cloning repository...")
        with RepoManager() as repo_mgr:
            repo_url = sources_config['repositories'][0]['url']
            repo_path = repo_mgr.clone_repo(repo_url)
            
            # Read source files mentioned in outline
            click.echo("Reading source files...")
            mentioned_files = DocumentGenerator(None)._extract_mentioned_files(outline)
            
            source_files = {}
            for file_path in mentioned_files:
                full_path = repo_path / file_path
                if full_path.exists():
                    source_files[file_path] = full_path.read_text()
            
            click.echo(f"✓ Read {len(source_files)} source files")
            
            # 4. Generate document
            click.echo("Generating document with LLM...")
            llm_client = OpenAIClient(
                api_key=config.llm_api_key,
                model=config.llm_model,
                timeout=config.llm_timeout
            )
            generator = DocumentGenerator(llm_client)
            
            doc_purpose = sources_config['metadata']['purpose']
            markdown = generator.generate_document(
                outline, 
                source_files, 
                doc_purpose
            )
            
            # 5. Save to staging
            staging_path = generator.save_to_staging(markdown, metadata)
            
            # 6. Report success
            click.echo(f"\n✓ Document generated successfully!")
            click.echo(f"✓ Saved to: {staging_path}")
            click.echo(f"\nDocument info:")
            click.echo(f"  Length: {len(markdown)} characters")
            click.echo(f"  Lines: {len(markdown.splitlines())}")
            click.echo(f"\nNext steps:")
            click.echo(f"  1. Review document: cat {staging_path}")
            click.echo(f"  2. If satisfied, promote to live (Sprint 5)")
            click.echo(f"  3. Or regenerate: doc-gen generate-doc {doc_path}")
            
    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    except LLMError as e:
        click.echo(f"✗ LLM Error: {e}", err=True)
        ctx.exit(1)
    except DocumentValidationError as e:
        click.echo(f"✗ Validation Error: {e}", err=True)
        click.echo(f"\nTry regenerating - LLMs are non-deterministic.")
        ctx.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if ctx.obj.get('debug'):
            raise
        ctx.exit(2)
```

**Key decisions:**
- Requires outline to exist (fail if missing)
- Re-clones repo (Sprint 4 will add caching)
- Only reads files mentioned in outline (efficient)
- Clear next steps after success
- Specific error types for different failures

---

### 3. Prompt Engineering for Document Quality
**Estimated Time:** 1-2 days embedded in sprint

**What it does:**
- Test document generation with real outlines
- Evaluate output quality (clarity, completeness, accuracy)
- Iterate on prompts to improve results
- Compare to hand-written docs

**Why this sprint:**
Document quality is critical. Budget time for prompt iteration.

**Iteration process:**
```
Day 2-3 of Sprint 3:

1. Generate document from test outline
2. Review output quality:
   - Are explanations clear?
   - Are code examples relevant?
   - Is technical accuracy good?
   - Does it follow outline structure?
   - Is markdown formatting correct?

3. Compare to ideal:
   - What's missing?
   - What's excessive?
   - What's unclear?

4. Refine prompt:
   - Adjust instructions
   - Add examples of good docs
   - Clarify formatting expectations

5. Regenerate and compare
6. Repeat until satisfied
```

**Document quality checklist:**
- [ ] Follows outline structure exactly
- [ ] Explanations are clear and accessible
- [ ] Code examples are relevant and correct
- [ ] Markdown formatting is proper
- [ ] Technical details are accurate
- [ ] Links between concepts make sense
- [ ] Appropriate length (not too short, not excessive)
- [ ] No placeholder text or TODOs

---

### 4. Staging Directory Management
**Estimated Lines:** ~50 lines (enhancements to metadata.py) + ~40 lines tests

**What it does:**
- Ensures staging directory structure is correct
- Handles staging file naming
- Manages staging vs live paths
- Enables future review workflow

**Why this sprint:**
Foundation for Sprint 5's review/promote workflow.

**Implementation notes:**
```python
# Enhancements to MetadataManager from Sprint 1

class MetadataManager:
    """Enhanced staging management for Sprint 3."""
    
    def get_staging_path(self) -> Path:
        """Return path to staging document.
        
        Example:
          .doc-gen/metadata/docs/modules/providers/openai/staging/openai.md
        """
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        return self.staging_dir / self.doc_path.name
    
    def get_live_path(self) -> Path:
        """Return path to live document.
        
        Example:
          docs/modules/providers/openai.md
        """
        return self.doc_path
    
    def staging_exists(self) -> bool:
        """Check if staging document exists."""
        return self.get_staging_path().exists()
    
    def live_exists(self) -> bool:
        """Check if live document exists."""
        return self.get_live_path().exists()
```

**Key decisions:**
- Staging path mirrors live path structure
- Simple file naming (same as live)
- Helper methods for Sprint 5's review/promote

---

## 🚫 What Gets Punted (Deliberately Excluded)

### Review/Promote Workflow
- ❌ `review` command (show diffs)
- ❌ `promote` command (copy to live)
- Why: Sprint 3 focuses on generation. Sprint 5 adds workflow safety.
- Reconsider: Sprint 5 (immediate after Sprint 4)

### Multi-Repository Support
- ❌ Documents from multiple repos
- Why: Sprint 3 completes single-repo pipeline. Sprint 4 adds multi-repo.
- Reconsider: Sprint 4 (next sprint after this)

### Document Quality Metrics
- ❌ Automated quality scoring
- ❌ Readability analysis
- Why: Manual review is sufficient for MVP
- Reconsider: v0.2.0 if quality is inconsistent

### Template System
- ❌ Document templates or sections
- Why: LLM generates structure from outline
- Reconsider: v0.2.0 if users want consistency

### Incremental Regeneration
- ❌ Only regenerate changed sections
- Why: Full regeneration is fine for MVP
- Reconsider: v0.2.0 if full regen is too slow

---

## 🔗 Dependencies

**Requires from previous sprints:**
- Sprint 1: Config management, metadata, staging paths
- Sprint 1: CLI framework (add new command)
- Sprint 2: LLM client (reuse for document generation)
- Sprint 2: Outline structure (input for this sprint)

**Provides for future sprints:**
- Staging workflow (Sprint 5 uses for review/promote)
- Document generation patterns (Sprint 4 extends for multi-repo)
- End-to-end pipeline (Sprint 6 orchestrates)

---

## ✅ Acceptance Criteria

### Must Have

- ✅ **Document generation**: `doc-gen generate-doc <doc-path>` works
  - Loads outline from outline.json
  - Reads source files
  - Generates markdown document
  - Saves to staging directory
  - Reports success
- ✅ **Quality documents**: Generated docs are clear and useful (after prompt iteration)
- ✅ **Staging workflow**: Documents go to staging, not live
- ✅ **Frontmatter**: Markdown includes YAML frontmatter
- ✅ **Validation**: Catches empty or placeholder documents
- ✅ **End-to-end working**: Can run init → generate-outline → generate-doc
- ✅ **Test coverage**: >80% for new modules

### Nice to Have (Defer if time constrained)

- ❌ Configurable temperature/model per document
- ❌ Custom frontmatter fields
- ❌ Side-by-side comparison with previous version

---

## 🛠️ Technical Approach

### Testing Strategy

**TDD for all new functionality:**

1. **🔴 RED - Write failing tests first**
   - Test document generator with mock LLM
   - Test prompt construction
   - Test validation catches issues
   - Test staging file creation

2. **🟢 GREEN - Write minimal implementation**
   - Implement just enough to pass
   - Use real LLM for integration tests

3. **🔵 REFACTOR - Improve code quality**
   - Extract prompt logic
   - Clean up validation
   - Improve error messages

**Unit Tests:**
- `DocumentGenerator._create_prompt()` includes outline and sources
- `DocumentGenerator._validate_markdown()` catches issues
- `DocumentGenerator._add_frontmatter()` formats correctly
- Staging path creation works correctly

**Integration Tests:**
- End-to-end: Outline → Document → Staging
- Real LLM calls with test outlines
- Multiple document types (different content)

**Manual Testing (Prompt Engineering):**
- [ ] Generate doc from small outline (3-5 sections)
- [ ] Generate doc from medium outline (10+ sections)
- [ ] Compare to ideal documentation
- [ ] Iterate on prompts based on quality
- [ ] Test with different code types

**Test Coverage Target:** >80% for new code

---

### Prompt Quality Iteration

**Goal:** Generate docs that match hand-written quality

**Evaluation criteria:**
1. **Clarity**: Explanations are easy to understand
2. **Completeness**: All outline topics covered
3. **Accuracy**: Technical details are correct
4. **Examples**: Code examples are relevant and helpful
5. **Structure**: Follows outline organization
6. **Formatting**: Proper markdown (headers, lists, code blocks)

**Iteration workflow:**
1. Generate document
2. Read it carefully (as if you're the user)
3. Compare to ideal documentation
4. Identify specific issues
5. Adjust prompt to address issues
6. Regenerate and compare
7. Repeat until quality is good

**Budget 1-2 days for this.** It's worth the investment.

---

## 📋 Implementation Order

**Follow TDD: 🔴 Write test → 🟢 Implement → 🔵 Refactor → ✅ Commit**

### Day 1: Document Generator Core

**Morning:**
- 🔴 Write test: `DocumentGenerator._create_prompt()` includes outline
- 🟢 Implement prompt construction
- 🔴 Write test: Prompt includes source files
- 🟢 Add source file inclusion
- 🔴 Write test: Only mentioned files included
- 🟢 Implement selective file inclusion
- ✅ Commit: "feat: Add prompt construction for document generation"

**Afternoon:**
- 🔴 Write test: `generate_document()` calls LLM (mocked)
- 🟢 Implement basic document generation
- 🔴 Write test: Returns markdown string
- 🟢 Ensure proper return type
- 🔴 Write test: Handles LLM errors
- 🟢 Add error handling
- 🔵 Refactor: Extract prompt logic
- ✅ Commit: "feat: Add core document generation logic"

### Day 2-3: Prompt Engineering & Validation

**Day 2 Morning:**
- Generate document from test outline
- Manually review output quality
- Identify issues (too vague? missing details? poor structure?)
- ✅ Note: Document initial prompt quality

**Day 2 Afternoon:**
- Adjust prompt instructions based on review
- Add examples of good documentation
- Regenerate and compare quality
- ✅ Commit: "refactor: Initial document generation prompt iteration"

**Day 3 Morning: MORE ITERATION**
- Test with different outline types
- Test with various code sources
- Refine prompts based on results
- ✅ Commit: "refactor: Refine document generation prompts"

**Day 3 Afternoon:**
- 🔴 Write test: Validation catches empty documents
- 🟢 Implement validation
- 🔴 Write test: Validation catches placeholder text
- 🟢 Add placeholder detection
- 🔵 Refactor: Improve validation messages
- ✅ Commit: "feat: Add document validation"

### Day 4: Frontmatter & Staging

**Morning:**
- 🔴 Write test: `_add_frontmatter()` formats correctly
- 🟢 Implement frontmatter generation
- 🔴 Write test: Frontmatter includes metadata
- 🟢 Add metadata from outline
- 🔴 Write test: `save_to_staging()` creates file
- 🟢 Implement staging file creation
- ✅ Commit: "feat: Add frontmatter and staging file management"

**Afternoon:**
- 🔴 Write test: Staging path is correct
- 🟢 Enhance MetadataManager with staging helpers
- 🔴 Write test: Staging directory created automatically
- 🟢 Add directory creation
- ✅ Commit: "feat: Add staging directory management"

### Day 5: CLI Integration

**Morning:**
- 🔴 Write test: `generate-doc` command loads outline
- 🟢 Implement command skeleton
- 🔴 Write test: Command clones repo
- 🟢 Wire up repo operations
- 🔴 Write test: Command calls generator
- 🟢 Wire up document generator
- ✅ Commit: "feat: Add generate-doc CLI command"

**Afternoon:**
- 🔴 Write test: Command saves to staging
- 🟢 Add staging save
- 🔴 Write test: Command reports success
- 🟢 Add success reporting with metadata
- 🔴 Write test: Error handling
- 🟢 Add error handling for common cases
- 🔵 Refactor: Extract reporting logic
- ✅ Commit: "feat: Complete generate-doc command with error handling"

### Day 6: Integration Testing

**Morning:**
- 🔴 Write integration test: Full workflow (outline → doc)
- 🟢 Test: Load outline → Generate doc → Save staging
- 🔴 Write integration test: Multiple documents
- 🟢 Test with different outline structures
- 🔵 Fix integration bugs
- ✅ Commit: "test: Add end-to-end integration tests"

**Afternoon:**
- Manual testing: Generate docs from real outlines
- Test with various repository types
- Verify document quality
- Fix edge cases discovered
- ✅ Commit: "fix: Handle edge cases in document generation"

### Day 7: Polish & Documentation

**Morning:**
- Improve error messages based on testing
- Polish CLI output formatting
- Test edge cases (missing sources, invalid outline)
- ✅ Commit: "polish: Improve error messages and CLI output"

**Afternoon:**
- Update README with document generation examples
- Add full workflow example (init → outline → doc)
- Document prompt engineering learnings
- Update CLI help text
- ✅ Commit: "docs: Document complete generation workflow"

**Evening: Sprint Review**
- Demo end-to-end workflow with real repo
- Show generated documents
- Verify staging workflow
- All acceptance criteria met
- ✅ Sprint 3 complete! 🎉

---

## 📊 What You Learn

After Sprint 3, you'll discover:

1. **Document prompt patterns** → Informs future prompt work
2. **LLM consistency** → Validates two-phase approach
3. **Token costs** → Full picture of generation costs
4. **Staging workflow** → Confirms approach for Sprint 5
5. **Quality benchmarks** → Sets baseline for future improvements

These learnings enable Sprint 4's multi-repo support and Sprint 5's review workflow.

---

## 🎯 Success Metrics

### Quantitative
- ✅ 2 modules (~270 LOC + ~170 LOC tests)
- ✅ Test coverage >80%
- ✅ All tests passing
- ✅ Document generation completes in <45 seconds
- ✅ End-to-end pipeline working

### Qualitative
- ✅ Generated documents are clear and useful
- ✅ Documents follow outline structure
- ✅ Code examples are relevant
- ✅ Markdown formatting is correct
- ✅ User says "this document is good!"

---

## 🚧 Known Limitations (By Design)

1. **Single repository only** - Multi-repo is Sprint 4
2. **No review workflow** - Review/promote is Sprint 5
3. **Full regeneration** - Incremental updates in v0.2.0
4. **No quality scoring** - Manual review for MVP
5. **No document templates** - LLM generates structure

These limitations are **intentional**. Sprint 3 proves document generation works. Future sprints add sophistication.

---

## 🔮 Next Sprint Preview

After Sprint 3 ships, the next step is:

**Sprint 4: Multi-Repo & Validation** (1-1.5 weeks)

Sprint 4 scales to 20+ repositories:
- Multi-repo source specifications
- Gitignore-style pattern matching
- Source validation command
- Extend outline/doc generation for multi-repo

The hard LLM work is done. Sprint 4 focuses on **scaling** the working pipeline.

Let's finish Sprint 3 first! 🚀

---

**Ready to complete the pipeline? Start with Day 1 and follow the TDD workflow. Ship this sprint in 1 week!**
