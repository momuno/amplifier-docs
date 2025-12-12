# Sprint 6: Orchestration & Polish

**Duration:** 1 week  
**Goal:** Batch orchestration of regeneration and final production polish  
**Value Delivered:** Production-ready MVP that replaces manual scripts completely

---

## 🎯 Why This Sprint?

Sprint 6 is the **final sprint** - it transforms individual commands into a complete, production-ready tool. You have all the pieces; now orchestrate them into seamless workflows.

**What Sprint 6 adds:**
1. **Batch Orchestration** - Regenerate all changed docs with one command
2. **Error Handling Polish** - Comprehensive error messages across all commands
3. **Reporting & Logging** - Clear visibility into what the tool is doing
4. **Documentation** - README, examples, troubleshooting
5. **Final Testing** - End-to-end validation with real usage

By the end of Sprint 6, you'll have:
- `regenerate-changed` command (orchestrates Sprint 5's change detection)
- Polished error handling across all commands
- Comprehensive user documentation
- Production-ready MVP ready for daily use

After Sprint 6, the MVP is **COMPLETE** and ready to replace manual scripts!

---

## 📦 Deliverables

### 1. Batch Orchestration (`orchestration.py`)
**Estimated Lines:** ~250 lines + ~150 lines tests

**What it does:**
- Orchestrates regeneration of multiple documents
- Uses Sprint 5's change detection to find stale docs
- Runs generate-outline → generate-doc for each
- Continues on error (one failure doesn't stop batch)
- Reports success/failure for each doc
- Tracks timing and costs

**Why this sprint:**
The payoff of all previous work. Turns "manually regenerate 15 docs" into "one command does it all."

**Implementation notes:**
```python
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import time
from .change_detection import ChangeDetector
from .outline import OutlineGenerator
from .generation import DocumentGenerator
from .llm_client import LLMClient

@dataclass
class RegenerationResult:
    """Result of regenerating a single document."""
    doc_path: str
    success: bool
    error_message: str = None
    outline_tokens: int = 0
    doc_tokens: int = 0
    duration_seconds: float = 0
    
@dataclass
class BatchReport:
    """Report for batch regeneration operation."""
    total_docs: int
    successful: int
    failed: int
    total_tokens: int
    total_duration_seconds: float
    estimated_cost_usd: float
    results: List[RegenerationResult]
    
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_docs == 0:
            return 0.0
        return (self.successful / self.total_docs) * 100

class BatchOrchestrator:
    """Orchestrates batch regeneration operations."""
    
    def __init__(
        self, 
        llm_client: LLMClient,
        repo_manager: RepoManager
    ):
        self.llm_client = llm_client
        self.repo_manager = repo_manager
        
    def regenerate_changed(self) -> BatchReport:
        """Regenerate all documents with source changes.
        
        Returns:
            BatchReport with results for each document
        """
        # Find all docs with changes
        docs_to_regenerate = self._find_changed_docs()
        
        if not docs_to_regenerate:
            return BatchReport(
                total_docs=0,
                successful=0,
                failed=0,
                total_tokens=0,
                total_duration_seconds=0,
                estimated_cost_usd=0,
                results=[]
            )
        
        # Regenerate each doc
        results = []
        total_tokens = 0
        start_time = time.time()
        
        for i, doc_path in enumerate(docs_to_regenerate, 1):
            click.echo(f"\n{'━' * 60}")
            click.echo(f"Regenerating: {doc_path} ({i}/{len(docs_to_regenerate)})")
            click.echo('━' * 60)
            
            result = self._regenerate_single_doc(doc_path)
            results.append(result)
            total_tokens += result.outline_tokens + result.doc_tokens
        
        total_duration = time.time() - start_time
        
        # Calculate stats
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        # Estimate cost (GPT-4: ~$0.03/1K input tokens, ~$0.06/1K output tokens)
        # Rough estimate: assume 50/50 split
        estimated_cost = (total_tokens / 1000) * 0.045
        
        return BatchReport(
            total_docs=len(docs_to_regenerate),
            successful=successful,
            failed=failed,
            total_tokens=total_tokens,
            total_duration_seconds=total_duration,
            estimated_cost_usd=estimated_cost,
            results=results
        )
    
    def _find_changed_docs(self) -> List[str]:
        """Find all documents with source changes."""
        all_docs = MetadataManager.find_all_docs()
        changed_docs = []
        
        for doc_path in all_docs:
            metadata = MetadataManager(str(doc_path))
            
            try:
                outline = metadata.read_outline()
                sources_config = metadata.read_sources()
                source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
                
                # Clone repos and check changes
                repo_paths = {}
                for spec in source_specs:
                    repo_path = self.repo_manager.clone_repo(spec.url)
                    repo_paths[spec.repo_name] = repo_path
                
                detector = ChangeDetector()
                report = detector.check_changes(outline, repo_paths, str(doc_path))
                
                if report.needs_regeneration():
                    changed_docs.append(str(doc_path))
                    
            except Exception:
                # Skip docs that can't be checked
                pass
        
        return changed_docs
    
    def _regenerate_single_doc(self, doc_path: str) -> RegenerationResult:
        """Regenerate a single document.
        
        Returns RegenerationResult even if operation fails.
        """
        start_time = time.time()
        
        try:
            metadata = MetadataManager(doc_path)
            sources_config = metadata.read_sources()
            source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
            
            # Clone repos
            click.echo("  ✓ Cloning repositories...")
            repo_paths = {}
            source_files = {}
            commit_hashes = {}
            
            for spec in source_specs:
                repo_path = self.repo_manager.clone_repo(spec.url)
                repo_paths[spec.repo_name] = repo_path
                
                # Collect files
                all_files = list(repo_path.rglob('*'))
                for file_path in all_files:
                    if file_path.is_file():
                        relative_path = file_path.relative_to(repo_path)
                        if spec.matches_file(str(relative_path)):
                            key = f"{spec.repo_name}/{relative_path}"
                            try:
                                source_files[key] = file_path.read_text()
                                commit_hashes[key] = self.repo_manager.get_file_commit_hash(
                                    repo_path, str(relative_path)
                                )
                            except Exception:
                                pass
            
            # Generate outline
            click.echo(f"  ✓ Generating outline...")
            outline_gen = OutlineGenerator(self.llm_client)
            purpose = sources_config['metadata']['purpose']
            outline = outline_gen.generate_outline(source_files, commit_hashes, purpose)
            metadata.save_outline(outline)
            
            outline_tokens = outline['_metadata']['tokens_used']
            click.echo(f"    Tokens: {outline_tokens}")
            
            # Generate document
            click.echo(f"  ✓ Generating document...")
            doc_gen = DocumentGenerator(self.llm_client)
            markdown = doc_gen.generate_document(outline, source_files, purpose)
            doc_gen.save_to_staging(markdown, metadata)
            
            # Estimate doc tokens (approximate from length)
            doc_tokens = len(markdown) // 4
            click.echo(f"    Length: {len(markdown)} chars")
            
            duration = time.time() - start_time
            click.echo(f"  ✓ Completed in {duration:.1f}s")
            
            return RegenerationResult(
                doc_path=doc_path,
                success=True,
                outline_tokens=outline_tokens,
                doc_tokens=doc_tokens,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            click.echo(f"  ✗ Failed: {e}")
            
            return RegenerationResult(
                doc_path=doc_path,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )
```

**Key decisions:**
- Continue on error (one failure doesn't stop batch)
- Show progress for each doc
- Track tokens and costs for transparency
- Report success/failure for each doc
- Return comprehensive batch report

---

### 2. Regenerate Changed Command (`cli.py` update)
**Estimated Lines:** ~150 lines + ~100 lines tests

**What it does:**
- New command: `doc-gen regenerate-changed`
- Finds all docs with changes (uses Sprint 5)
- Orchestrates batch regeneration
- Displays progress and results
- Shows summary with timing and costs

**Why this sprint:**
User-facing interface for batch orchestration. The command that makes the tool indispensable.

**Implementation notes:**
```python
@cli.command()
@click.option('--dry-run', is_flag=True, help='Show what would be regenerated without doing it')
@click.pass_context
def regenerate_changed(ctx, dry_run: bool):
    """Regenerate all documents with source changes.
    
    Automatically detects which docs have stale sources and regenerates them.
    Documents are saved to staging - review and promote separately.
    
    Example:
      doc-gen regenerate-changed          # Regenerate all changed docs
      doc-gen regenerate-changed --dry-run  # Preview what would be regenerated
    """
    config = ctx.obj['config']
    
    click.echo("━" * 60)
    click.echo("Checking for stale documentation...")
    click.echo("━" * 60)
    
    with RepoManager() as repo_mgr:
        orchestrator = BatchOrchestrator(
            llm_client=OpenAIClient(
                api_key=config.llm_api_key,
                model=config.llm_model,
                timeout=config.llm_timeout
            ),
            repo_manager=repo_mgr
        )
        
        if dry_run:
            # Just find changed docs
            changed_docs = orchestrator._find_changed_docs()
            
            if not changed_docs:
                click.echo("\n✓ All documents are up-to-date!")
                ctx.exit(0)
            
            click.echo(f"\n✓ Found {len(changed_docs)} document(s) needing regeneration:")
            for doc in changed_docs:
                click.echo(f"  - {doc}")
            
            click.echo(f"\nRun without --dry-run to regenerate.")
            ctx.exit(0)
        
        # Actually regenerate
        report = orchestrator.regenerate_changed()
        
        if report.total_docs == 0:
            click.echo("\n✓ All documents are up-to-date!")
            ctx.exit(0)
        
        # Display summary
        click.echo("\n" + "━" * 60)
        click.echo("Summary")
        click.echo("━" * 60)
        
        if report.successful > 0:
            click.echo(click.style(
                f"  ✓ {report.successful} document(s) successfully regenerated",
                fg='green'
            ))
        
        if report.failed > 0:
            click.echo(click.style(
                f"  ✗ {report.failed} document(s) failed",
                fg='red'
            ))
        
        click.echo(f"\n  Total time: {_format_duration(report.total_duration_seconds)}")
        click.echo(f"  Total tokens: ~{report.total_tokens:,}")
        click.echo(f"  Estimated cost: ~${report.estimated_cost_usd:.2f}")
        
        if report.successful > 0:
            click.echo(f"\nNext steps:")
            click.echo(f"  1. Review regenerated docs: doc-gen review <doc-path>")
            click.echo(f"  2. Promote approved docs: doc-gen promote <doc-path>")
        
        if report.failed > 0:
            click.echo(f"\nFailed documents (investigate manually):")
            for result in report.results:
                if not result.success:
                    click.echo(f"  ✗ {result.doc_path}")
                    click.echo(f"    Error: {result.error_message}")
        
        # Exit with appropriate code
        ctx.exit(0 if report.failed == 0 else 1)

def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
```

**Key decisions:**
- `--dry-run` flag for preview (safe exploration)
- Clear progress per document
- Comprehensive summary with costs
- Show next steps for success
- Show errors for failures (actionable)

---

### 3. Error Handling Polish (across all modules)
**Estimated Lines:** ~150 lines (modifications) + ~100 lines tests

**What it does:**
- Unified error handling across all commands
- Custom exception hierarchy
- User-friendly error messages with suggestions
- Proper exit codes for scripting
- Debug mode for full stack traces

**Why this sprint:**
Production readiness requires excellent error handling. Users must understand what went wrong.

**Implementation notes:**
```python
# errors.py - Unified error handling

class DocGenError(Exception):
    """Base exception for doc-gen errors."""
    exit_code = 1
    
    def user_message(self) -> str:
        """User-friendly error message."""
        return str(self)
    
    def suggestion(self) -> str:
        """Actionable suggestion for user."""
        return "Check command syntax: doc-gen --help"

class ConfigError(DocGenError):
    """Configuration error."""
    
    def suggestion(self) -> str:
        return (
            "Check configuration:\n"
            "  - Verify .doc-gen/config.yaml exists\n"
            "  - Set API key: export OPENAI_API_KEY=your-key"
        )

class SourceSpecError(DocGenError):
    """Error in sources.yaml."""
    
    def suggestion(self) -> str:
        return (
            "Check sources.yaml:\n"
            "  - Verify repository URLs are correct\n"
            "  - Ensure include patterns are specified\n"
            "  - Test patterns: doc-gen validate-sources <doc-path>"
        )

class LLMError(DocGenError):
    """LLM API error."""
    exit_code = 2  # System error
    
    def suggestion(self) -> str:
        return (
            "LLM provider error:\n"
            "  - Check API key is valid\n"
            "  - Verify account has credits\n"
            "  - Check provider status page\n"
            "  - Try again (may be transient)"
        )

class RepositoryError(DocGenError):
    """Repository cloning/access error."""
    
    def suggestion(self) -> str:
        return (
            "Repository access error:\n"
            "  - Verify repository URL is correct\n"
            "  - Check network connection\n"
            "  - For private repos, set up authentication"
        )

# Error handler wrapper for CLI commands
def handle_errors(func):
    """Decorator for consistent error handling in CLI commands."""
    @functools.wraps(func)
    def wrapper(ctx, *args, **kwargs):
        try:
            return func(ctx, *args, **kwargs)
        except DocGenError as e:
            click.echo(click.style(f"✗ Error: {e.user_message()}", fg='red'), err=True)
            click.echo(f"\n{e.suggestion()}")
            ctx.exit(e.exit_code)
        except Exception as e:
            click.echo(click.style(f"✗ Unexpected error: {e}", fg='red'), err=True)
            if ctx.obj.get('debug'):
                raise
            click.echo("\nRun with --debug for full traceback")
            ctx.exit(2)
    return wrapper

# Apply to all commands
@cli.command()
@handle_errors
def some_command(ctx):
    # Command implementation
    pass
```

**Key decisions:**
- Exception hierarchy for different error types
- Separate user messages from technical details
- Actionable suggestions for each error type
- Proper exit codes (1 = user error, 2 = system error)
- Debug mode for development

---

### 4. Comprehensive Documentation
**Estimated Lines:** ~500 lines (README, examples, troubleshooting)

**What it does:**
- Comprehensive README with examples
- Quick start guide
- Command reference
- Troubleshooting guide
- Example sources.yaml files
- FAQ section

**Why this sprint:**
Documentation IS the user experience. Good docs = good adoption.

**README structure:**
```markdown
# doc-gen: Multi-Repository Documentation Generator

Automatically generate and maintain documentation from source code across multiple repositories.

## Features

- 📚 **Multi-repo support** - Document across 20+ repositories
- 🔍 **Change detection** - Automatically detect stale documentation
- ✅ **Safe workflow** - Review changes before publishing
- 🤖 **LLM-powered** - Uses GPT-4/Claude for intelligent generation
- 📝 **Two-phase pipeline** - Outline → Document for cost efficiency

## Quick Start

### Installation

```bash
cd tools/doc-gen
pip install -e .
```

### Setup

1. Create configuration:
```bash
# Creates .doc-gen/config.yaml template
doc-gen init docs/my-doc.md
```

2. Set API key:
```bash
export OPENAI_API_KEY=your-key-here
```

3. Edit sources:
```yaml
# .doc-gen/metadata/docs/my-doc/sources.yaml
repositories:
  - url: https://github.com/owner/repo.git
    include:
      - "*.py"
      - "README.md"
    exclude:
      - "tests/**"
```

### Basic Workflow

```bash
# 1. Validate sources
doc-gen validate-sources docs/my-doc.md

# 2. Generate outline
doc-gen generate-outline docs/my-doc.md

# 3. Generate document
doc-gen generate-doc docs/my-doc.md

# 4. Review changes
doc-gen review docs/my-doc.md

# 5. Promote to live
doc-gen promote docs/my-doc.md
```

### Detect Changes & Batch Regenerate

```bash
# Check which docs need updating
doc-gen check-changes

# Regenerate all changed docs
doc-gen regenerate-changed

# Review and promote each
doc-gen review docs/changed-doc.md
doc-gen promote docs/changed-doc.md
```

## Commands

### `init <doc-path>`
Initialize source specification for a document.

### `validate-sources <doc-path>`
Validate patterns and show what files will be included.

### `generate-outline <doc-path>`
Generate structured outline from source code.

### `generate-doc <doc-path>`
Generate markdown document from outline.

### `review <doc-path>`
Show diff between staging and live documentation.

### `promote <doc-path>`
Promote staged document to live (with backup).

### `check-changes [doc-path]`
Detect which documents have stale sources.

### `regenerate-changed`
Regenerate all documents with source changes.

## Configuration

### Global Config (.doc-gen/config.yaml)

```yaml
llm:
  provider: openai  # openai, anthropic
  model: gpt-4
  timeout: 60

# API keys from environment:
# OPENAI_API_KEY or ANTHROPIC_API_KEY
```

### Source Specification

```yaml
repositories:
  - url: https://github.com/owner/repo1.git
    include:
      - "src/**/*.py"
      - "README.md"
    exclude:
      - "tests/**"
      - "**/__pycache__/**"
  
  - url: https://github.com/owner/repo2.git
    include:
      - "docs/**/*.md"

metadata:
  purpose: "Document the XYZ module functionality"
```

## Troubleshooting

### "API key not found"
Set environment variable:
```bash
export OPENAI_API_KEY=your-key-here
```

### "No matches found"
Check patterns with validate-sources:
```bash
doc-gen validate-sources docs/my-doc.md
```

### "LLM timeout"
Increase timeout in config.yaml or reduce source file count.

### "Failed to clone repository"
- Check repository URL is correct
- Verify network connection
- For private repos, set up git authentication

## FAQ

**Q: How much does it cost?**
Outline generation: ~$0.20-0.50 per doc (depending on source size)
Document generation: ~$0.10-0.30 per doc
Check costs with: `doc-gen validate-sources <doc-path>`

**Q: Can I edit the outline before generating the document?**
Yes! Edit `.doc-gen/metadata/.../outline.json` before running `generate-doc`.

**Q: How do I undo a promotion?**
Restore from backup in `.doc-gen/backups/`.

**Q: Can I use with private repositories?**
Yes, but you need to set up git authentication (SSH keys or token).

## Examples

See `examples/` directory for:
- Single repository documentation
- Multi-repository documentation
- Custom source patterns
- Workflow automation scripts
```

**Key decisions:**
- Start with quick start (get users productive fast)
- Include complete workflow examples
- Troubleshooting section for common issues
- FAQ addresses anticipated questions
- Examples directory with real cases

---

### 5. Final Testing & Bug Fixes
**Estimated Time:** 1-2 days embedded in sprint

**What it does:**
- End-to-end testing with real repositories
- Test all 8 CLI commands
- Verify error handling
- Check edge cases
- Fix discovered bugs

**Why this sprint:**
Production readiness requires thorough testing. Find and fix issues before release.

**Testing checklist:**
- [ ] Install from scratch (verify setup works)
- [ ] Initialize new document
- [ ] Validate sources with various patterns
- [ ] Generate outline from 3+ repos
- [ ] Generate document from outline
- [ ] Make changes and detect them
- [ ] Review diffs
- [ ] Promote with backup
- [ ] Regenerate changed batch (5+ docs)
- [ ] Test error cases (invalid config, bad URLs, LLM errors)
- [ ] Verify all help text is clear
- [ ] Check exit codes for scripting
- [ ] Test on different platforms (Linux, macOS, Windows)

---

## 🚫 What Gets Punted (Deliberately Excluded)

### Parallel Regeneration
- ❌ Regenerate docs in parallel
- Why: Sequential is simpler and sufficient for MVP
- Reconsider: v0.2.0 if speed is critical

### Advanced Reporting
- ❌ Dashboard for token usage over time
- ❌ Quality metrics per document
- Why: Basic reporting is sufficient
- Reconsider: v0.2.0 if users need analytics

### GitHub Actions Integration
- ❌ Automated scheduled regeneration
- ❌ PR comments with change detection
- Why: Manual workflow validates MVP first
- Reconsider: v0.2.0 after MVP proves valuable

### Web UI
- ❌ Web interface for review/promote
- Why: CLI is sufficient for MVP
- Reconsider: v0.2.0 if users want GUI

---

## 🔗 Dependencies

**Requires from previous sprints:**
- Sprint 1-5: All functionality (orchestrates everything)

**Provides for future versions:**
- Batch orchestration (foundation for automation)
- Reporting patterns (foundation for analytics)
- Error handling (foundation for reliability)
- Documentation (foundation for adoption)

---

## ✅ Acceptance Criteria

### Must Have

- ✅ **Regenerate changed**: `doc-gen regenerate-changed` works
  - Detects all changed docs
  - Regenerates each (outline + doc)
  - Continues on error
  - Reports summary with timing/costs
- ✅ **Dry run**: `--dry-run` flag shows preview
- ✅ **Error handling**: All commands have user-friendly errors
- ✅ **Documentation**: Comprehensive README with examples
- ✅ **All 8 commands working**: Full CLI tested end-to-end
- ✅ **Production ready**: Tool can replace manual scripts
- ✅ **Test coverage**: >80% overall

### Nice to Have (Defer if time constrained)

- ❌ Progress bars with animations
- ❌ JSON output mode for scripting
- ❌ Performance profiling

---

## 🛠️ Technical Approach

### Testing Strategy

**TDD for all new functionality:**

1. **Unit Tests**
   - Batch orchestration logic
   - Error handling for each error type
   - Duration formatting
   - Cost calculations

2. **Integration Tests**
   - Full batch regeneration
   - Error recovery scenarios
   - End-to-end workflows

3. **Manual Testing**
   - [ ] Regenerate 5+ docs with real changes
   - [ ] Test all error scenarios
   - [ ] Verify documentation accuracy
   - [ ] Test on different platforms

**Test Coverage Target:** >80% overall

---

## 📋 Implementation Order

**Follow TDD: 🔴 Write test → 🟢 Implement → 🔵 Refactor → ✅ Commit**

### Day 1-2: Batch Orchestration

**Day 1 Morning:**
- 🔴 Write test: Find changed docs
- 🟢 Implement changed doc detection
- 🔴 Write test: Regenerate single doc
- 🟢 Implement single doc regeneration
- ✅ Commit: "feat: Add batch orchestration core logic"

**Day 1 Afternoon:**
- 🔴 Write test: Batch regeneration with multiple docs
- 🟢 Implement batch processing
- 🔴 Write test: Continue on error
- 🟢 Add error recovery
- 🔵 Refactor: Extract orchestration logic
- ✅ Commit: "feat: Add multi-doc batch regeneration"

**Day 2 Morning:**
- 🔴 Write test: regenerate-changed command
- 🟢 Implement CLI command
- 🔴 Write test: Display progress and summary
- 🟢 Add reporting
- 🔴 Write test: --dry-run flag
- 🟢 Add dry run mode
- ✅ Commit: "feat: Add regenerate-changed command"

**Day 2 Afternoon:**
- Manual testing: Regenerate 5+ real docs
- Test with various failure scenarios
- Verify reporting accuracy
- ✅ Commit: "test: Validate batch regeneration"

### Day 3-4: Error Handling Polish

**Day 3 Morning:**
- 🔴 Write test: Custom exception hierarchy
- 🟢 Implement error classes
- 🔴 Write test: Error decorator for CLI
- 🟢 Implement error handler wrapper
- ✅ Commit: "feat: Add unified error handling"

**Day 3 Afternoon:**
- Apply error handling to all commands
- Add user-friendly messages
- Add actionable suggestions
- Test each error type
- ✅ Commit: "feat: Polish error messages across all commands"

**Day 4 Morning:**
- 🔴 Write test: Exit codes for scripting
- 🟢 Ensure proper exit codes
- 🔴 Write test: Debug mode shows traces
- 🟢 Add debug flag
- ✅ Commit: "feat: Add debug mode and proper exit codes"

**Day 4 Afternoon:**
- Test all error scenarios
- Verify suggestions are helpful
- Polish error formatting
- ✅ Commit: "test: Validate error handling"

### Day 5-6: Documentation & Testing

**Day 5 Morning:**
- Write comprehensive README
- Add quick start guide
- Document all commands
- ✅ Commit: "docs: Add comprehensive README"

**Day 5 Afternoon:**
- Write troubleshooting guide
- Add FAQ section
- Create example sources.yaml files
- Add examples directory
- ✅ Commit: "docs: Add troubleshooting and examples"

**Day 6: Full Integration Testing**
- Install from scratch
- Test complete workflow with real repos
- Verify all 8 commands work
- Test error scenarios
- Fix discovered bugs
- ✅ Commit: "test: End-to-end validation"

### Day 7: Final Polish & Release

**Day 7 Morning:**
- Polish CLI help text
- Verify all acceptance criteria met
- Run full test suite
- Check test coverage (>80%)
- ✅ Commit: "polish: Final CLI improvements"

**Day 7 Afternoon:**
- Update CHANGELOG
- Tag release (v0.1.0)
- Write release notes
- Demo to stakeholders
- ✅ Sprint 6 complete! 🎉
- ✅ **MVP COMPLETE!** 🚀

---

## 📊 What You Learn

After Sprint 6, you'll discover:

1. **Batch operation patterns** → Validates orchestration approach
2. **Common user errors** → Informs onboarding improvements
3. **Performance at scale** → Identifies optimization opportunities
4. **Documentation gaps** → Improves user experience
5. **Real-world edge cases** → Informs v0.2.0 priorities

These learnings inform the v0.2.0 roadmap.

---

## 🎯 Success Metrics

### Quantitative
- ✅ 2 new modules (~400 LOC + ~250 LOC tests)
- ✅ Test coverage >80% overall
- ✅ All tests passing
- ✅ Batch regeneration works reliably
- ✅ Comprehensive documentation complete

### Qualitative
- ✅ Users can regenerate all docs with one command
- ✅ Error messages are helpful and actionable
- ✅ Documentation answers common questions
- ✅ Tool feels production-ready
- ✅ User says "this completely replaces my scripts!"

---

## 🎉 MVP COMPLETE!

After Sprint 6 ships, you'll have:

✅ **All 8 CLI commands** implemented and tested  
✅ **Multi-repository support** (scale to 20+ repos)  
✅ **Change detection** (know what's stale instantly)  
✅ **Safe review workflow** (review before promoting)  
✅ **Batch orchestration** (one command updates all)  
✅ **Production error handling** (helpful messages)  
✅ **Comprehensive documentation** (README, examples, troubleshooting)  
✅ **Test coverage >80%** (reliable and maintainable)

**This is a COMPLETE MVP that solves the original problem:**
> Documentation drifts from reality as code evolves across 20+ repositories, with no systematic way to detect changes or regenerate affected documentation.

---

## 🔮 v0.2.0 Considerations

Based on Sprint 1-6 learnings, prioritize these features for v0.2.0:

### Performance
- Parallel regeneration
- Repository caching
- Incremental outline updates

### Intelligence
- Smart change detection (ignore formatting)
- Evaluation harness for prompts
- Template system for consistent structure

### Automation
- GitHub Actions workflow
- PR comments with change detection
- Scheduled regeneration

### UX
- Interactive source editor
- Web UI for review
- Progress bars and animations

### Enterprise
- Private repository authentication
- Multiple LLM providers
- Team approval workflows
- Audit logging

**Prioritize based on actual MVP usage feedback!**

---

**Ready to finish the MVP? Start with Day 1 and follow the TDD workflow. Ship this sprint in 1 week and celebrate! 🚀🎉**
