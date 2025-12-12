# Sprint 4: Multi-Repo & Validation

**Duration:** 1-1.5 weeks  
**Goal:** Scale to 20+ repositories with gitignore-style pattern matching and validation  
**Value Delivered:** Users can manage documentation across multiple repositories with pre-generation validation

---

## 🎯 Why This Sprint?

Sprint 3 gave you a working single-repo pipeline. Now it's time to **scale** to the real problem: 20+ repositories.

**Key challenges:**
1. **Multi-repo source specifications** - Define multiple repos in sources.yaml
2. **Pattern matching** - Gitignore-style patterns across repos (requires thorough testing)
3. **Source validation** - Preview what files will be used BEFORE expensive LLM calls
4. **Edge cases** - Empty repos, missing patterns, network failures

By the end of Sprint 4, you'll have:
- Multi-repository source specifications working
- Gitignore-style pattern matching (pathspec library)
- Source validation command (shows matched files)
- Outline/doc generation extended for multi-repo
- Tested with 3+ real repositories

After Sprint 4, the tool can handle the full complexity of multi-repo documentation. Sprint 5 adds change detection and review. Sprint 6 adds orchestration.

---

## 📦 Deliverables

### 1. Multi-Repo Source Parser (`sources.py`)
**Estimated Lines:** ~200 lines + ~150 lines tests

**What it does:**
- Parses sources.yaml with multiple repositories
- Validates repository URLs
- Supports gitignore-style patterns (using pathspec library)
- Handles both include and exclude patterns per repo
- Provides clear error messages for invalid configurations

**Why this sprint:**
Foundation for multi-repo support. Must be robust and handle edge cases.

**Implementation notes:**
```python
from pathlib import Path
from typing import List, Dict, Any
import yaml
from urllib.parse import urlparse
import pathspec

class SourceSpec:
    """Represents a single repository source specification."""
    
    def __init__(self, url: str, include: List[str], exclude: List[str]):
        self.url = url
        self.include_patterns = include
        self.exclude_patterns = exclude
        self.repo_name = self._extract_repo_name(url)
        
    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL."""
        # https://github.com/owner/repo.git → repo
        return url.rstrip('/').split('/')[-1].replace('.git', '')
    
    def validate(self):
        """Validate this source specification."""
        # Validate URL format
        parsed = urlparse(self.url)
        if not parsed.scheme or not parsed.netloc:
            raise SourceSpecError(
                f"Invalid repository URL: {self.url}\n"
                f"Expected format: https://github.com/owner/repo.git"
            )
        
        # Validate patterns are not empty
        if not self.include_patterns:
            raise SourceSpecError(
                f"Repository {self.repo_name} has no include patterns.\n"
                f"Specify at least one pattern (e.g., '*.py')"
            )
    
    def matches_file(self, file_path: str) -> bool:
        """Check if file matches this source's patterns.
        
        Uses gitignore-style pattern matching via pathspec library.
        """
        # Check include patterns first
        include_spec = pathspec.PathSpec.from_lines('gitwildmatch', self.include_patterns)
        if not include_spec.match_file(file_path):
            return False
        
        # If file matched include, check exclude patterns
        if self.exclude_patterns:
            exclude_spec = pathspec.PathSpec.from_lines('gitwildmatch', self.exclude_patterns)
            if exclude_spec.match_file(file_path):
                return False
        
        return True

class SourceParser:
    """Parses multi-repository source specifications."""
    
    @staticmethod
    def parse_sources_yaml(yaml_path: Path) -> List[SourceSpec]:
        """Parse sources.yaml into list of SourceSpec objects.
        
        Supports both single-repo (Sprint 1-3) and multi-repo formats.
        """
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'repositories' not in data:
            raise SourceSpecError(
                f"Missing 'repositories' key in {yaml_path}\n"
                f"Expected structure:\n"
                f"  repositories:\n"
                f"    - url: https://github.com/...\n"
                f"      include: ['*.py']"
            )
        
        repos = data['repositories']
        if not isinstance(repos, list):
            raise SourceSpecError("'repositories' must be a list")
        
        source_specs = []
        for i, repo_config in enumerate(repos):
            try:
                source_spec = SourceParser._parse_repo_config(repo_config)
                source_spec.validate()
                source_specs.append(source_spec)
            except Exception as e:
                raise SourceSpecError(
                    f"Error in repository #{i+1}: {e}"
                )
        
        return source_specs
    
    @staticmethod
    def _parse_repo_config(config: Dict[str, Any]) -> SourceSpec:
        """Parse single repository configuration."""
        url = config.get('url')
        if not url:
            raise SourceSpecError("Missing 'url' field")
        
        include = config.get('include', [])
        exclude = config.get('exclude', [])
        
        return SourceSpec(url, include, exclude)

class SourceSpecError(Exception):
    """Error in source specification."""
    pass
```

**Key decisions:**
- Use pathspec library for gitignore-style matching (standard, well-tested)
- Support both include and exclude patterns per repo
- Validate URLs early (fail fast)
- Backward compatible with Sprint 1-3 single-repo format
- Clear error messages with examples

---

### 2. Source Validator (`validation.py`)
**Estimated Lines:** ~220 lines + ~140 lines tests

**What it does:**
- Clones all repositories from sources.yaml
- Lists files matching patterns for each repo
- Reports file counts, line counts, estimated tokens
- Catches errors BEFORE expensive LLM calls
- Provides preview of what will be generated

**Why this sprint:**
Critical for multi-repo. Users need to validate their patterns work correctly before burning tokens.

**Implementation notes:**
```python
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from .sources import SourceSpec
from .repos import RepoManager

@dataclass
class RepoValidationResult:
    """Validation results for a single repository."""
    repo_name: str
    repo_url: str
    success: bool
    error_message: str = None
    matched_files: List[Tuple[Path, int]] = None  # [(file_path, line_count), ...]
    total_files: int = 0
    total_lines: int = 0
    estimated_tokens: int = 0

@dataclass
class ValidationReport:
    """Overall validation report for all repositories."""
    repo_results: List[RepoValidationResult]
    total_repos: int
    successful_repos: int
    total_files: int
    total_lines: int
    estimated_tokens: int
    estimated_cost_usd: float
    
    def is_valid(self) -> bool:
        """Returns True if all repos validated successfully."""
        return self.successful_repos == self.total_repos

class SourceValidator:
    """Validates source specifications before generation."""
    
    def __init__(self, repo_manager: RepoManager):
        self.repo_manager = repo_manager
        
    def validate_sources(self, source_specs: List[SourceSpec]) -> ValidationReport:
        """Validate all source specifications.
        
        Clones repos, matches files, counts lines, estimates tokens.
        """
        repo_results = []
        
        for source_spec in source_specs:
            result = self._validate_repo(source_spec)
            repo_results.append(result)
        
        # Build summary
        successful_repos = sum(1 for r in repo_results if r.success)
        total_files = sum(r.total_files for r in repo_results if r.success)
        total_lines = sum(r.total_lines for r in repo_results if r.success)
        estimated_tokens = sum(r.estimated_tokens for r in repo_results if r.success)
        
        # Rough cost estimate (GPT-4: ~$0.03 per 1K tokens for input)
        estimated_cost_usd = (estimated_tokens / 1000) * 0.03
        
        return ValidationReport(
            repo_results=repo_results,
            total_repos=len(source_specs),
            successful_repos=successful_repos,
            total_files=total_files,
            total_lines=total_lines,
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost_usd
        )
    
    def _validate_repo(self, source_spec: SourceSpec) -> RepoValidationResult:
        """Validate a single repository."""
        try:
            # Clone repository
            repo_path = self.repo_manager.clone_repo(source_spec.url)
            
            # List all files in repo
            all_files = list(repo_path.rglob('*'))
            all_files = [f for f in all_files if f.is_file()]
            
            # Filter by patterns
            matched_files = []
            for file_path in all_files:
                relative_path = file_path.relative_to(repo_path)
                if source_spec.matches_file(str(relative_path)):
                    try:
                        # Count lines
                        content = file_path.read_text(errors='ignore')
                        line_count = len(content.splitlines())
                        matched_files.append((relative_path, line_count))
                    except Exception:
                        # Skip files that can't be read (binary, etc.)
                        pass
            
            total_files = len(matched_files)
            total_lines = sum(lines for _, lines in matched_files)
            
            # Estimate tokens (rough: 4 chars per token)
            estimated_tokens = total_lines * 50  # ~50 chars per line avg
            estimated_tokens = estimated_tokens // 4
            
            return RepoValidationResult(
                repo_name=source_spec.repo_name,
                repo_url=source_spec.url,
                success=True,
                matched_files=matched_files,
                total_files=total_files,
                total_lines=total_lines,
                estimated_tokens=estimated_tokens
            )
            
        except Exception as e:
            return RepoValidationResult(
                repo_name=source_spec.repo_name,
                repo_url=source_spec.url,
                success=False,
                error_message=str(e)
            )
```

**Key decisions:**
- Validate all repos even if one fails (complete picture)
- Estimate tokens and costs (help users understand expense)
- Count lines to show magnitude
- Skip binary files gracefully
- Return structured report (easy to format for CLI)

---

### 3. Validate Sources Command (`cli.py` update)
**Estimated Lines:** ~150 lines + ~100 lines tests

**What it does:**
- New command: `doc-gen validate-sources <doc-path>`
- Loads sources.yaml
- Validates all repositories
- Shows detailed report (colorized)
- Reports success/failure with exit codes

**Why this sprint:**
User-facing interface for validation. Catches errors before expensive generation.

**Implementation notes:**
```python
@cli.command()
@click.argument('doc-path', type=click.Path())
@click.option('--keep-repos', is_flag=True, help='Keep cloned repos for faster iteration')
@click.pass_context
def validate_sources(ctx, doc_path: str, keep_repos: bool):
    """Validate source specifications before generation.
    
    Clones repositories, matches patterns, shows what files will be included.
    Use this before generate-outline to catch errors early.
    
    Example:
      doc-gen validate-sources docs/modules/providers/openai.md
    """
    config = ctx.obj['config']
    metadata = MetadataManager(doc_path)
    
    try:
        # Load sources
        click.echo(f"✓ Loading sources for {doc_path}...")
        sources_config = metadata.read_sources()
        
        # Parse source specs
        source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
        click.echo(f"✓ Found {len(source_specs)} repositories\n")
        
        # Validate
        click.echo("Validating repositories...\n")
        
        with RepoManager() as repo_mgr:
            validator = SourceValidator(repo_mgr)
            report = validator.validate_sources(source_specs)
            
            # Display results
            _display_validation_report(report)
            
            # Exit with appropriate code
            if report.is_valid():
                click.echo("\n✓ All sources valid!")
                click.echo(f"\nNext step:")
                click.echo(f"  doc-gen generate-outline {doc_path}")
                ctx.exit(0)
            else:
                click.echo("\n✗ Validation failed. Fix errors and try again.")
                ctx.exit(1)
                
    except SourceSpecError as e:
        click.echo(f"✗ Source specification error: {e}", err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if ctx.obj.get('debug'):
            raise
        ctx.exit(2)

def _display_validation_report(report: ValidationReport):
    """Display validation report with colors."""
    for result in report.repo_results:
        if result.success:
            click.echo(click.style(f"✓ {result.repo_name}", fg='green'))
            click.echo(f"  URL: {result.repo_url}")
            click.echo(f"  Matched files: {result.total_files}")
            
            # Show first 10 files as preview
            if result.matched_files:
                click.echo(f"  Files:")
                for file_path, line_count in result.matched_files[:10]:
                    click.echo(f"    - {file_path} ({line_count} lines)")
                
                if len(result.matched_files) > 10:
                    remaining = len(result.matched_files) - 10
                    click.echo(f"    ... and {remaining} more files")
            
            click.echo(f"  Total lines: {result.total_lines}")
            click.echo(f"  Estimated tokens: ~{result.estimated_tokens:,}")
            click.echo()
        else:
            click.echo(click.style(f"✗ {result.repo_name}", fg='red'))
            click.echo(f"  URL: {result.repo_url}")
            click.echo(f"  Error: {result.error_message}")
            click.echo()
    
    # Summary
    click.echo("━" * 60)
    click.echo(click.style("Summary", bold=True))
    click.echo(f"  Repositories: {report.successful_repos}/{report.total_repos} valid")
    click.echo(f"  Total files: {report.total_files}")
    click.echo(f"  Total lines: {report.total_lines:,}")
    click.echo(f"  Estimated tokens: ~{report.estimated_tokens:,}")
    click.echo(f"  Estimated cost: ~${report.estimated_cost_usd:.2f} (outline generation)")
```

**Key decisions:**
- Show first 10 files per repo (preview without overwhelming)
- Colorized output (green success, red errors)
- Estimate costs upfront (transparency)
- Exit codes for scripting (0 = valid, 1 = invalid)
- --keep-repos flag for development iteration

---

### 4. Multi-Repo Outline Generation (enhance existing)
**Estimated Lines:** ~100 lines (modifications) + ~80 lines tests

**What it does:**
- Extends Sprint 2's outline generation for multiple repos
- Clones all repositories
- Aggregates source files from all repos
- Maintains per-file commit hashes
- Updates CLI command to handle multi-repo

**Why this sprint:**
Makes outline generation work with Sprint 4's multi-repo sources.

**Implementation notes:**
```python
# Enhancements to generate_outline command

@cli.command()
@click.argument('doc-path', type=click.Path())
@click.pass_context
def generate_outline(ctx, doc_path: str):
    """Generate structured outline from source files (multi-repo support)."""
    config = ctx.obj['config']
    metadata = MetadataManager(doc_path)
    
    try:
        # Load and parse sources (now supports multi-repo)
        click.echo(f"Loading sources for {doc_path}...")
        source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
        click.echo(f"✓ Found {len(source_specs)} repositories")
        
        # Clone all repositories
        click.echo("Cloning repositories...")
        with RepoManager() as repo_mgr:
            source_files = {}
            commit_hashes = {}
            
            for i, source_spec in enumerate(source_specs, 1):
                click.echo(f"  [{i}/{len(source_specs)}] Cloning {source_spec.repo_name}...")
                
                repo_path = repo_mgr.clone_repo(source_spec.url)
                
                # List files matching patterns
                all_files = list(repo_path.rglob('*'))
                all_files = [f for f in all_files if f.is_file()]
                
                repo_file_count = 0
                for file_path in all_files:
                    relative_path = file_path.relative_to(repo_path)
                    if source_spec.matches_file(str(relative_path)):
                        # Use repo-prefixed key to avoid conflicts
                        key = f"{source_spec.repo_name}/{relative_path}"
                        try:
                            source_files[key] = file_path.read_text()
                            commit_hashes[key] = repo_mgr.get_file_commit_hash(
                                repo_path, str(relative_path)
                            )
                            repo_file_count += 1
                        except Exception:
                            # Skip files that can't be read
                            pass
                
                click.echo(f"    ✓ Read {repo_file_count} files from {source_spec.repo_name}")
            
            click.echo(f"\n✓ Total: {len(source_files)} files from {len(source_specs)} repos")
            
            # Rest of outline generation (same as Sprint 2)
            # ...
```

**Key decisions:**
- Prefix file paths with repo name (avoid conflicts)
- Show progress per repository
- Fail gracefully if one repo fails (continue with others)
- Reuse Sprint 2's outline generation logic

---

### 5. Multi-Repo Document Generation (enhance existing)
**Estimated Lines:** ~50 lines (modifications) + ~40 lines tests

**What it does:**
- Extends Sprint 3's document generation for multi-repo outlines
- Reads files from multi-repo outlines
- Maintains repo context in prompts

**Why this sprint:**
Makes document generation work with Sprint 4's multi-repo outlines.

---

## 🚫 What Gets Punted (Deliberately Excluded)

### Repository Caching
- ❌ Persistent repository caching
- Why: Temp directory cloning works for MVP
- Reconsider: Sprint 6 or v0.2.0 if cloning is too slow

### Parallel Repository Cloning
- ❌ Clone repos in parallel for speed
- Why: Sequential is simpler and sufficient for MVP
- Reconsider: v0.2.0 if batch operations are slow

### GitHub API Integration
- ❌ Use GitHub API instead of cloning
- ❌ Authentication for private repos
- Why: Public repos with git clone works for MVP
- Reconsider: v0.2.0 if private repos needed

### Pattern Testing UI
- ❌ Interactive pattern tester
- Why: Validate command shows results
- Reconsider: v0.2.0 if users struggle with patterns

---

## 🔗 Dependencies

**Requires from previous sprints:**
- Sprint 1: RepoManager (extend for multi-repo)
- Sprint 2: Outline generation (extend for multi-repo)
- Sprint 3: Document generation (extend for multi-repo)
- Sprint 1: CLI framework (add validate command)

**Provides for future sprints:**
- Multi-repo support (Sprint 5 detects changes across repos)
- Source validation (Sprint 6 uses before batch operations)
- Pattern matching (foundation for future features)

---

## ✅ Acceptance Criteria

### Must Have

- ✅ **Multi-repo sources**: sources.yaml can define 3+ repositories
- ✅ **Pattern matching**: Gitignore-style patterns work correctly
- ✅ **Validate sources**: `doc-gen validate-sources <doc-path>` works
  - Shows matched files per repository
  - Reports counts and estimates
  - Catches invalid patterns/URLs
- ✅ **Multi-repo outline**: `doc-gen generate-outline` works with multi-repo
  - Clones all repositories
  - Aggregates files
  - Generates outline from combined sources
- ✅ **Multi-repo document**: `doc-gen generate-doc` works with multi-repo outlines
- ✅ **Test with 3+ repos**: Successfully validated with real repositories
- ✅ **Test coverage**: >80% for new modules

### Nice to Have (Defer if time constrained)

- ❌ Parallel repository cloning
- ❌ Repository caching
- ❌ Pattern testing mode

---

## 🛠️ Technical Approach

### Testing Strategy

**TDD for all new functionality:**

1. **Unit Tests**
   - Pattern matching with various gitignore patterns
   - Source spec validation
   - Repository result aggregation
   - Error handling for invalid configs

2. **Integration Tests**
   - Validate with test repositories
   - Multi-repo outline generation
   - Pattern edge cases (exclude, nested patterns)

3. **Manual Testing**
   - [ ] Validate with 3+ real repositories
   - [ ] Test various pattern combinations
   - [ ] Test with large repos (100+ files)
   - [ ] Verify token estimates are reasonable

**Test Coverage Target:** >80% for new code

---

### Pattern Matching Testing

**Critical patterns to test:**
- `*.py` - All Python files (recursive)
- `src/**/*.py` - Python files under src/
- `README.md` - Specific file
- `docs/**/*.md` - Markdown in docs/
- `!tests/**` - Exclude patterns
- `**/__pycache__/**` - Nested exclusions

**Edge cases:**
- Empty include patterns
- No matches found
- Binary files
- Symlinks
- Very large files

---

## 📋 Implementation Order

**Follow TDD: 🔴 Write test → 🟢 Implement → 🔵 Refactor → ✅ Commit**

### Day 1-2: Multi-Repo Source Parsing

**Day 1 Morning:**
- 🔴 Write test: Parse multi-repo sources.yaml
- 🟢 Implement SourceParser
- 🔴 Write test: SourceSpec validation
- 🟢 Implement validation logic
- ✅ Commit: "feat: Add multi-repository source parsing"

**Day 1 Afternoon:**
- 🔴 Write test: Pattern matching with pathspec
- 🟢 Implement gitignore-style matching
- 🔴 Write test: Include and exclude patterns
- 🟢 Add exclude pattern support
- 🔵 Refactor: Extract pattern matching
- ✅ Commit: "feat: Add gitignore-style pattern matching"

**Day 2 Morning:**
- 🔴 Write test: Various pattern combinations
- 🟢 Test edge cases
- 🔴 Write test: Error messages for invalid patterns
- 🟢 Improve error handling
- ✅ Commit: "test: Add comprehensive pattern matching tests"

**Day 2 Afternoon:**
- Manual testing: Test patterns with real repos
- Document pattern syntax in code
- ✅ Commit: "docs: Document pattern matching syntax"

### Day 3-4: Source Validation

**Day 3 Morning:**
- 🔴 Write test: SourceValidator validates single repo
- 🟢 Implement SourceValidator
- 🔴 Write test: Count files and lines
- 🟢 Add counting logic
- 🔴 Write test: Estimate tokens
- 🟢 Add token estimation
- ✅ Commit: "feat: Add source validation logic"

**Day 3 Afternoon:**
- 🔴 Write test: Validate multiple repos
- 🟢 Implement multi-repo validation
- 🔴 Write test: Continue on error
- 🟢 Add error recovery
- 🔵 Refactor: Extract validation result building
- ✅ Commit: "feat: Add multi-repo validation with error recovery"

**Day 4 Morning:**
- 🔴 Write test: validate-sources command
- 🟢 Implement CLI command
- 🔴 Write test: Display report with colors
- 🟢 Add formatted output
- ✅ Commit: "feat: Add validate-sources CLI command"

**Day 4 Afternoon:**
- Manual testing: Validate with real repos
- Test with invalid patterns
- Verify token estimates
- ✅ Commit: "test: Validate command with real repositories"

### Day 5-7: Multi-Repo Outline & Document Generation

**Day 5 Morning:**
- 🔴 Write test: generate-outline with multi-repo
- 🟢 Extend outline command for multi-repo
- 🔴 Write test: Aggregate files from multiple repos
- 🟢 Implement file aggregation
- ✅ Commit: "feat: Extend outline generation for multi-repo"

**Day 5 Afternoon:**
- 🔴 Write test: Commit hashes from multiple repos
- 🟢 Add multi-repo hash tracking
- 🔴 Write test: Repo-prefixed file keys
- 🟢 Implement key prefixing
- 🔵 Refactor: Clean up multi-repo logic
- ✅ Commit: "feat: Add commit hash tracking for multi-repo"

**Day 6 Morning:**
- 🔴 Write test: generate-doc with multi-repo outline
- 🟢 Extend document command for multi-repo
- 🔴 Write integration test: Full multi-repo workflow
- 🟢 Test: Validate → Outline → Document
- ✅ Commit: "feat: Extend document generation for multi-repo"

**Day 6 Afternoon:**
- Manual testing: Generate from 3+ repos
- Verify output quality
- Test various repo combinations
- ✅ Commit: "test: Validate multi-repo workflow with real repositories"

**Day 7: Polish & Documentation**
- Improve error messages
- Polish CLI output
- Update README with multi-repo examples
- Add troubleshooting section
- ✅ Commit: "docs: Document multi-repo features"
- ✅ Sprint 4 complete! 🎉

---

## 📊 What You Learn

After Sprint 4, you'll discover:

1. **Pattern complexity** → Validates pattern matching approach
2. **Repository sizes** → Informs optimization priorities
3. **Token costs at scale** → Real cost picture for 20+ repos
4. **Common pattern mistakes** → Informs better validation messages
5. **Network reliability** → Informs retry strategy for Sprint 6

These learnings inform Sprint 5's change detection and Sprint 6's orchestration.

---

## 🎯 Success Metrics

### Quantitative
- ✅ 3 new modules (~570 LOC + ~420 LOC tests)
- ✅ Test coverage >80%
- ✅ All tests passing
- ✅ Validation completes in <60 seconds for 20+ repos
- ✅ Multi-repo generation works end-to-end

### Qualitative
- ✅ Pattern matching is intuitive
- ✅ Validation catches errors effectively
- ✅ Multi-repo docs are coherent
- ✅ Token estimates are accurate
- ✅ User says "this scales to my repos!"

---

## 🚧 Known Limitations (By Design)

1. **Sequential cloning** - Parallel cloning in v0.2.0
2. **No caching** - Repository caching in v0.2.0
3. **Public repos only** - Private repo auth in v0.2.0
4. **No pattern testing UI** - Validate command is sufficient

These limitations are **intentional**. Sprint 4 proves multi-repo works. Future versions optimize.

---

## 🔮 Next Sprint Preview

After Sprint 4 ships, the next step is:

**Sprint 5: Change Detection & Review** (1 week)

Sprint 5 adds the killer features:
- Detect which docs have stale sources
- Review diffs before promoting
- Safe promotion workflow

The infrastructure is complete. Sprint 5 adds the workflow that makes this tool indispensable.

Let's finish Sprint 4 first! 🚀

---

**Ready to scale? Start with Day 1 and follow the TDD workflow. Ship this sprint in 1-1.5 weeks!**
