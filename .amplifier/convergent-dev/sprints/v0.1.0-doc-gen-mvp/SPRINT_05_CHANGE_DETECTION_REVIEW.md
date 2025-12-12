# Sprint 5: Change Detection & Review

**Duration:** 1 week  
**Goal:** Detect stale documentation and enable safe review/promotion workflow  
**Value Delivered:** Users know which docs need updating and can safely review changes before publishing

---

## 🎯 Why This Sprint?

Sprint 5 delivers the **killer features** that make this tool indispensable:

1. **Change Detection** - Automatically know which docs are stale (no manual tracking!)
2. **Review Workflow** - Safely inspect diffs before promoting to live docs
3. **Promote with Backups** - Safe promotion with automatic backups

These features naturally work together - detect changes, regenerate, review, promote. This completes the core workflow loop.

By the end of Sprint 5, you'll have:
- Change detection via commit hash comparison
- Check changes command (single doc or all docs)
- Review command (show diffs with colorization)
- Promote command (with automatic backups)
- Complete safety workflow

After Sprint 5, the MVP is functionally complete. Sprint 6 adds batch orchestration and polish.

---

## 📦 Deliverables

### 1. Change Detector (`change_detection.py`)
**Estimated Lines:** ~220 lines + ~160 lines tests

**What it does:**
- Compares commit hashes in outline.json vs current repo state
- Reports which files have changed, been added, or removed
- Determines if regeneration is needed
- Extracts commit messages for changed files (context!)

**Why this sprint:**
The foundational logic for change detection. Enables automated staleness checking.

**Implementation notes:**
```python
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass
from git import Repo

@dataclass
class FileChange:
    """Represents a change to a single file."""
    file_path: str
    old_hash: str
    new_hash: str
    commit_message: str = ""

@dataclass
class ChangeReport:
    """Report of source file changes for a document."""
    doc_path: str
    changed_files: List[FileChange]
    new_files: List[str]
    removed_files: List[str]
    unchanged_files: List[str]
    
    def needs_regeneration(self) -> bool:
        """Returns True if any meaningful changes detected."""
        return len(self.changed_files) > 0 or len(self.new_files) > 0
    
    def total_changes(self) -> int:
        """Total number of changes."""
        return len(self.changed_files) + len(self.new_files) + len(self.removed_files)

class ChangeDetector:
    """Detects source file changes via commit hash comparison."""
    
    def check_changes(
        self, 
        outline: Dict[str, Any],
        repo_paths: Dict[str, Path],  # {repo_name: local_path}
        doc_path: str
    ) -> ChangeReport:
        """Compare outline commit hashes with current repo state.
        
        Args:
            outline: Outline with embedded commit hashes
            repo_paths: Dict of repo names to cloned paths
            doc_path: Path to document being checked
            
        Returns:
            ChangeReport with all detected changes
        """
        # Extract file → hash mapping from outline
        outline_hashes = self._extract_hashes_from_outline(outline)
        
        # Get current hashes from repositories
        current_hashes = self._get_current_hashes(outline_hashes.keys(), repo_paths)
        
        # Compare and categorize
        changed_files = []
        unchanged_files = []
        
        for file_path in outline_hashes.keys():
            if file_path in current_hashes:
                old_hash = outline_hashes[file_path]
                new_hash = current_hashes[file_path]
                
                if old_hash != new_hash:
                    # File changed - get commit message
                    repo_name, relative_path = self._split_file_path(file_path)
                    repo_path = repo_paths.get(repo_name)
                    
                    commit_msg = self._get_commit_message(
                        repo_path, relative_path, new_hash
                    ) if repo_path else ""
                    
                    changed_files.append(FileChange(
                        file_path=file_path,
                        old_hash=old_hash[:7],  # Short hash for display
                        new_hash=new_hash[:7],
                        commit_message=commit_msg
                    ))
                else:
                    unchanged_files.append(file_path)
        
        # Find new files (in current but not in outline)
        new_files = [f for f in current_hashes.keys() if f not in outline_hashes]
        
        # Find removed files (in outline but not in current)
        removed_files = [f for f in outline_hashes.keys() if f not in current_hashes]
        
        return ChangeReport(
            doc_path=doc_path,
            changed_files=changed_files,
            new_files=new_files,
            removed_files=removed_files,
            unchanged_files=unchanged_files
        )
    
    def _extract_hashes_from_outline(self, outline: Dict[str, Any]) -> Dict[str, str]:
        """Extract file → hash mapping from outline."""
        return outline.get("_commit_hashes", {})
    
    def _get_current_hashes(
        self, 
        file_paths: Set[str], 
        repo_paths: Dict[str, Path]
    ) -> Dict[str, str]:
        """Get current commit hashes for files."""
        current_hashes = {}
        
        for file_path in file_paths:
            repo_name, relative_path = self._split_file_path(file_path)
            repo_path = repo_paths.get(repo_name)
            
            if repo_path:
                try:
                    hash_val = self._get_file_commit_hash(repo_path, relative_path)
                    current_hashes[file_path] = hash_val
                except Exception:
                    # File might have been deleted
                    pass
        
        return current_hashes
    
    def _split_file_path(self, file_path: str) -> tuple[str, str]:
        """Split 'repo_name/path/to/file' into (repo_name, path/to/file)."""
        parts = file_path.split('/', 1)
        return (parts[0], parts[1] if len(parts) > 1 else "")
    
    def _get_file_commit_hash(self, repo_path: Path, file_path: str) -> str:
        """Get latest commit hash for a file."""
        repo = Repo(repo_path)
        commits = list(repo.iter_commits(paths=file_path, max_count=1))
        return commits[0].hexsha if commits else ""
    
    def _get_commit_message(self, repo_path: Path, file_path: str, commit_hash: str) -> str:
        """Get commit message for a specific commit."""
        try:
            repo = Repo(repo_path)
            commit = repo.commit(commit_hash)
            # Get first line of commit message
            return commit.message.split('\n')[0]
        except Exception:
            return ""
```

**Key decisions:**
- Only compare files that exist in both outline and current
- New files trigger regeneration (might be relevant)
- Removed files reported but don't block
- Include commit messages (provides context)
- Use short hashes for display (7 chars)

---

### 2. Check Changes Command (`cli.py` update)
**Estimated Lines:** ~180 lines + ~120 lines tests

**What it does:**
- New command: `doc-gen check-changes [doc-path]`
- Without doc-path: Check ALL docs in repo
- With doc-path: Check specific doc
- Display colorized change report
- Exit code indicates if changes found

**Why this sprint:**
User-facing interface for change detection. The command users run daily.

**Implementation notes:**
```python
@cli.command()
@click.argument('doc-path', required=False, type=click.Path())
@click.option('--all', 'check_all', is_flag=True, help='Check all documents')
@click.pass_context
def check_changes(ctx, doc_path: str, check_all: bool):
    """Detect which documents have stale sources.
    
    Compares commit hashes in outlines with current repository state.
    Shows which files changed and their commit messages.
    
    Examples:
      doc-gen check-changes docs/modules/providers/openai.md  # Check one doc
      doc-gen check-changes --all  # Check all docs
      doc-gen check-changes  # Same as --all
    """
    config = ctx.obj['config']
    
    # Determine which docs to check
    if doc_path:
        docs_to_check = [Path(doc_path)]
    else:
        # Check all docs with metadata
        docs_to_check = MetadataManager.find_all_docs()
        if not docs_to_check:
            click.echo("No documents found with metadata.")
            click.echo("Initialize with: doc-gen init <doc-path>")
            ctx.exit(0)
    
    click.echo(f"✓ Checking {len(docs_to_check)} document(s) for changes...\n")
    
    docs_with_changes = []
    docs_up_to_date = []
    docs_no_outline = []
    
    with RepoManager() as repo_mgr:
        for doc in docs_to_check:
            result = _check_single_doc(doc, repo_mgr, ctx)
            
            if result == "changes":
                docs_with_changes.append(doc)
            elif result == "up_to_date":
                docs_up_to_date.append(doc)
            else:  # "no_outline"
                docs_no_outline.append(doc)
    
    # Summary
    click.echo("\n" + "━" * 60)
    click.echo(click.style("Summary", bold=True))
    
    if docs_with_changes:
        click.echo(click.style(
            f"  ⚠  {len(docs_with_changes)} document(s) need regeneration",
            fg='yellow'
        ))
    if docs_up_to_date:
        click.echo(click.style(
            f"  ✓ {len(docs_up_to_date)} document(s) up-to-date",
            fg='green'
        ))
    if docs_no_outline:
        click.echo(click.style(
            f"  ✗ {len(docs_no_outline)} document(s) not yet generated",
            fg='red'
        ))
    
    if docs_with_changes:
        click.echo(f"\nRegenerate with:")
        click.echo(f"  doc-gen regenerate-changed")
        ctx.exit(1)  # Exit 1 = changes found
    else:
        ctx.exit(0)  # Exit 0 = all up-to-date

def _check_single_doc(doc_path: Path, repo_mgr: RepoManager, ctx) -> str:
    """Check a single document. Returns status string."""
    metadata = MetadataManager(str(doc_path))
    
    try:
        # Load outline
        outline = metadata.read_outline()
    except FileNotFoundError:
        click.echo(f"{doc_path}")
        click.echo(click.style("  ✗ Outline not found (never generated)", fg='red'))
        click.echo()
        return "no_outline"
    
    try:
        # Load sources and clone repos
        sources_config = metadata.read_sources()
        source_specs = SourceParser.parse_sources_yaml(metadata.sources_path)
        
        # Clone repos
        repo_paths = {}
        for spec in source_specs:
            repo_path = repo_mgr.clone_repo(spec.url)
            repo_paths[spec.repo_name] = repo_path
        
        # Check for changes
        detector = ChangeDetector()
        report = detector.check_changes(outline, repo_paths, str(doc_path))
        
        # Display results
        click.echo(f"{doc_path}")
        
        if report.needs_regeneration():
            click.echo(click.style(
                f"  ⚠  {report.total_changes()} change(s) detected:",
                fg='yellow'
            ))
            
            for change in report.changed_files:
                click.echo(f"    - {change.file_path}")
                click.echo(f"      ({change.old_hash} → {change.new_hash}) \"{change.commit_message}\"")
            
            for new_file in report.new_files:
                click.echo(f"    + {new_file} (new file)")
            
            for removed_file in report.removed_files:
                click.echo(f"    - {removed_file} (removed)")
            
            click.echo(f"  ✓ {len(report.unchanged_files)} file(s) unchanged")
            click.echo()
            return "changes"
        else:
            generated_at = outline.get("_metadata", {}).get("generated_at", "unknown")
            click.echo(click.style("  ✓ All sources unchanged", fg='green'))
            click.echo(f"    Last generated: {generated_at}")
            click.echo()
            return "up_to_date"
            
    except Exception as e:
        click.echo(click.style(f"  ✗ Error checking: {e}", fg='red'))
        click.echo()
        return "error"
```

**Key decisions:**
- Default to checking all docs (most common use case)
- Show commit messages (provides context)
- Use exit codes: 0 = no changes, 1 = changes found
- Colorized output (yellow warning, green ok, red error)
- Continue checking even if one doc fails

---

### 3. Review Command (`cli.py` + `review.py`)
**Estimated Lines:** ~200 lines + ~130 lines tests

**What it does:**
- New command: `doc-gen review <doc-path>`
- Shows diff between staging and live documentation
- Colorized diff output (additions, deletions, context)
- Reports change statistics

**Why this sprint:**
Safety mechanism - users must see what changed before promoting.

**Implementation notes:**
```python
# review.py
import difflib
from pathlib import Path
from typing import List, Tuple
import click

class DiffGenerator:
    """Generates and formats diffs between documents."""
    
    def generate_diff(self, staging_path: Path, live_path: Path) -> Tuple[str, dict]:
        """Generate diff between staging and live docs.
        
        Returns:
            (diff_text, stats) where stats = {added, removed, modified}
        """
        # Read files
        staging_lines = self._read_file_lines(staging_path)
        
        if live_path.exists():
            live_lines = self._read_file_lines(live_path)
        else:
            live_lines = []
        
        # Generate unified diff
        diff = difflib.unified_diff(
            live_lines,
            staging_lines,
            fromfile=str(live_path),
            tofile=str(staging_path),
            lineterm=''
        )
        
        # Process diff and calculate stats
        diff_lines = list(diff)
        stats = self._calculate_stats(diff_lines)
        
        # Format with colors
        formatted_diff = self._format_diff(diff_lines)
        
        return formatted_diff, stats
    
    def _read_file_lines(self, path: Path) -> List[str]:
        """Read file and return lines."""
        if path.exists():
            return path.read_text().splitlines(keepends=True)
        return []
    
    def _calculate_stats(self, diff_lines: List[str]) -> dict:
        """Calculate diff statistics."""
        added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        
        return {
            'added': added,
            'removed': removed,
            'modified': min(added, removed)  # Rough estimate
        }
    
    def _format_diff(self, diff_lines: List[str]) -> str:
        """Format diff with colors."""
        formatted = []
        
        for line in diff_lines:
            if line.startswith('+++') or line.startswith('---'):
                # File headers
                formatted.append(click.style(line, bold=True))
            elif line.startswith('+'):
                # Additions
                formatted.append(click.style(line, fg='green'))
            elif line.startswith('-'):
                # Deletions
                formatted.append(click.style(line, fg='red'))
            elif line.startswith('@@'):
                # Chunk headers
                formatted.append(click.style(line, fg='cyan'))
            else:
                # Context
                formatted.append(line)
        
        return '\n'.join(formatted)

# CLI command
@cli.command()
@click.argument('doc-path', type=click.Path())
@click.pass_context
def review(ctx, doc_path: str):
    """Review staged document changes before promotion.
    
    Shows diff between staging and live documentation.
    Use this before 'promote' to verify changes are correct.
    
    Example:
      doc-gen review docs/modules/providers/openai.md
    """
    metadata = MetadataManager(doc_path)
    
    # Check staging exists
    staging_path = metadata.get_staging_path()
    if not staging_path.exists():
        click.echo(f"✗ No staged document found: {staging_path}")
        click.echo(f"\nGenerate first:")
        click.echo(f"  doc-gen generate-doc {doc_path}")
        ctx.exit(1)
    
    live_path = metadata.get_live_path()
    
    # Display header
    click.echo("━" * 60)
    click.echo(click.style(f"Review: {doc_path}", bold=True))
    click.echo("━" * 60)
    click.echo()
    click.echo(f"Staging: {staging_path}")
    click.echo(f"Live:    {live_path}")
    click.echo()
    
    # Generate and display diff
    diff_gen = DiffGenerator()
    diff_text, stats = diff_gen.generate_diff(staging_path, live_path)
    
    if stats['added'] == 0 and stats['removed'] == 0:
        click.echo(click.style("✓ No changes detected", fg='green'))
        ctx.exit(0)
    
    click.echo("Changes:")
    click.echo(f"  +{stats['added']} lines added")
    click.echo(f"  -{stats['removed']} lines removed")
    click.echo(f"  ~{stats['modified']} lines modified")
    click.echo()
    click.echo("─" * 60)
    click.echo("Diff:")
    click.echo("─" * 60)
    click.echo(diff_text)
    click.echo("─" * 60)
    click.echo()
    click.echo("Next step:")
    click.echo(f"  doc-gen promote {doc_path}")
```

**Key decisions:**
- Use Python's difflib (standard, well-tested)
- Colorized output (green add, red delete, cyan context)
- Show statistics summary (added/removed/modified)
- Clear next step messaging
- Works even if live doc doesn't exist yet

---

### 4. Promote Command (`cli.py` + `promotion.py`)
**Estimated Lines:** ~180 lines + ~120 lines tests

**What it does:**
- New command: `doc-gen promote <doc-path>`
- Creates backup of current live doc (if exists)
- Copies staging doc to live location
- Updates metadata with promotion timestamp
- Validates staging is newer than live

**Why this sprint:**
Completes the safe workflow. Makes "staging → live" explicit and traceable.

**Implementation notes:**
```python
# promotion.py
from pathlib import Path
from datetime import datetime
import shutil

class DocumentPromoter:
    """Handles safe promotion of staged documents to live."""
    
    def __init__(self, metadata_mgr: MetadataManager):
        self.metadata = metadata_mgr
        self.backup_dir = Path('.doc-gen/backups')
        
    def promote(self) -> dict:
        """Promote staging doc to live with backup.
        
        Returns:
            dict with promotion details
        """
        staging_path = self.metadata.get_staging_path()
        live_path = self.metadata.get_live_path()
        
        # Validate staging exists
        if not staging_path.exists():
            raise PromotionError(
                f"Staging document not found: {staging_path}\n"
                f"Generate first: doc-gen generate-doc {self.metadata.doc_path}"
            )
        
        # Create backup if live exists
        backup_path = None
        if live_path.exists():
            backup_path = self._create_backup(live_path)
        
        # Ensure live directory exists
        live_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy staging to live
        shutil.copy2(staging_path, live_path)
        
        # Update metadata
        promotion_time = datetime.now().isoformat()
        
        return {
            'staging_path': staging_path,
            'live_path': live_path,
            'backup_path': backup_path,
            'promoted_at': promotion_time
        }
    
    def _create_backup(self, live_path: Path) -> Path:
        """Create timestamped backup of live document."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup filename: YYYY-MM-DD-HHMMSS-original-name.md
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        backup_name = f"{timestamp}-{live_path.name}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(live_path, backup_path)
        
        return backup_path

class PromotionError(Exception):
    """Error during promotion."""
    pass

# CLI command
@cli.command()
@click.argument('doc-path', type=click.Path())
@click.pass_context
def promote(ctx, doc_path: str):
    """Promote staged document to live.
    
    Creates backup of current live doc (if exists) and copies
    staging document to live location. Always review first!
    
    Example:
      doc-gen promote docs/modules/providers/openai.md
    """
    metadata = MetadataManager(doc_path)
    promoter = DocumentPromoter(metadata)
    
    try:
        click.echo("✓ Validating staging document...")
        
        # Promote
        result = promoter.promote()
        
        # Report success
        click.echo("✓ Validation passed")
        click.echo()
        
        if result['backup_path']:
            click.echo("✓ Creating backup...")
            click.echo(f"  Backed up: {result['live_path']}")
            click.echo(f"  → {result['backup_path']}")
            click.echo()
        
        click.echo("✓ Promoting to live...")
        click.echo(f"  Copied: {result['staging_path']}")
        click.echo(f"  → {result['live_path']}")
        click.echo()
        
        click.echo("━" * 60)
        click.echo(click.style(f"✓ Successfully promoted {doc_path}", fg='green', bold=True))
        click.echo("━" * 60)
        click.echo()
        click.echo("Next steps:")
        click.echo("  1. Verify the live doc looks correct")
        click.echo(f"  2. Commit changes: git add {result['live_path']}")
        click.echo("  3. Push to publish: git push")
        
    except PromotionError as e:
        click.echo(click.style(f"✗ Promotion failed: {e}", fg='red'), err=True)
        ctx.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Unexpected error: {e}", fg='red'), err=True)
        if ctx.obj.get('debug'):
            raise
        ctx.exit(2)
```

**Key decisions:**
- Always create backup (never overwrite without backup)
- Timestamped backup filenames (sortable, clear)
- Validate staging exists before promoting
- Clear success messaging with next steps
- Store backups in `.doc-gen/backups/` (organized, hidden)

---

## 🚫 What Gets Punted (Deliberately Excluded)

### Batch Regeneration
- ❌ `regenerate-changed` command
- Why: Sprint 5 detects changes. Sprint 6 adds batch orchestration.
- Reconsider: Sprint 6 (immediate next step)

### Rollback Command
- ❌ `doc-gen rollback <doc-path>` to undo promotion
- Why: Can manually copy from backup
- Reconsider: v0.2.0 if rollbacks are common

### Advanced Backup Management
- ❌ Backup retention policy (auto-delete old backups)
- ❌ Backup listing command
- Why: Manual backup management works for MVP
- Reconsider: v0.2.0 if backups pile up

### Smart Change Detection
- ❌ Filter by significance (ignore formatting changes)
- ❌ Threshold-based (ignore if <10 lines changed)
- Why: Simple hash comparison is sufficient for MVP
- Reconsider: v0.2.0 if false positives are a problem

---

## 🔗 Dependencies

**Requires from previous sprints:**
- Sprint 1: Metadata management (outline.json reading)
- Sprint 2: Commit hash embedding in outlines
- Sprint 3: Staging workflow
- Sprint 4: Multi-repo support

**Provides for future sprints:**
- Change detection (Sprint 6 uses for batch operations)
- Review workflow (foundation for approval tracking)
- Promotion with backups (foundation for rollback)

---

## ✅ Acceptance Criteria

### Must Have

- ✅ **Check changes (single)**: `doc-gen check-changes <doc-path>` works
  - Compares commit hashes
  - Reports changed, new, removed files
  - Shows commit messages
- ✅ **Check changes (all)**: `doc-gen check-changes` works
  - Scans all docs in repository
  - Reports which docs need regeneration
  - Summary shows counts
- ✅ **Review command**: `doc-gen review <doc-path>` works
  - Shows diff between staging and live
  - Colorized output
  - Reports statistics
- ✅ **Promote command**: `doc-gen promote <doc-path>` works
  - Creates backup of live doc
  - Copies staging to live
  - Reports success with next steps
- ✅ **Complete workflow**: Can run check → regenerate → review → promote
- ✅ **Test coverage**: >80% for new modules

### Nice to Have (Defer if time constrained)

- ❌ Interactive confirmation on promote
- ❌ Side-by-side diff view
- ❌ Backup retention policy

---

## 🛠️ Technical Approach

### Testing Strategy

**TDD for all new functionality:**

1. **Unit Tests**
   - Change detection with known hashes
   - Diff generation with sample files
   - Backup creation and naming
   - Statistics calculation

2. **Integration Tests**
   - Full change detection workflow
   - Review with real docs
   - Promotion with backup

3. **Manual Testing**
   - [ ] Make real commits and detect changes
   - [ ] Review diffs for readability
   - [ ] Promote and verify backup created
   - [ ] Test with multiple docs

**Test Coverage Target:** >80% for new code

---

## 📋 Implementation Order

**Follow TDD: 🔴 Write test → 🟢 Implement → 🔵 Refactor → ✅ Commit**

### Day 1-2: Change Detection

**Day 1 Morning:**
- 🔴 Write test: Extract hashes from outline
- 🟢 Implement hash extraction
- 🔴 Write test: Get current commit hashes
- 🟢 Implement current hash fetching
- ✅ Commit: "feat: Add commit hash extraction and comparison"

**Day 1 Afternoon:**
- 🔴 Write test: Compare hashes and categorize changes
- 🟢 Implement change detection logic
- 🔴 Write test: FileChange and ChangeReport dataclasses
- 🟢 Implement data structures
- 🔵 Refactor: Clean up comparison logic
- ✅ Commit: "feat: Add change detection core logic"

**Day 2 Morning:**
- 🔴 Write test: Get commit messages for changes
- 🟢 Implement commit message extraction
- 🔴 Write test: check-changes command for single doc
- 🟢 Implement CLI command
- ✅ Commit: "feat: Add check-changes command for single doc"

**Day 2 Afternoon:**
- 🔴 Write test: check-changes for all docs
- 🟢 Implement batch checking
- 🔴 Write test: Summary output
- 🟢 Implement summary formatting
- 🔵 Refactor: Extract display logic
- ✅ Commit: "feat: Add batch change checking"

### Day 3-4: Review & Promote

**Day 3 Morning:**
- 🔴 Write test: Generate diff between files
- 🟢 Implement diff generation
- 🔴 Write test: Calculate diff statistics
- 🟢 Implement stats calculation
- 🔴 Write test: Colorize diff output
- 🟢 Implement colorization
- ✅ Commit: "feat: Add diff generation and formatting"

**Day 3 Afternoon:**
- 🔴 Write test: review command displays diff
- 🟢 Implement review command
- 🔴 Write test: Handle missing staging doc
- 🟢 Add error handling
- 🔵 Refactor: Extract formatting
- ✅ Commit: "feat: Add review command"

**Day 4 Morning:**
- 🔴 Write test: Create timestamped backup
- 🟢 Implement backup creation
- 🔴 Write test: Copy staging to live
- 🟢 Implement file copying
- ✅ Commit: "feat: Add backup creation for promotion"

**Day 4 Afternoon:**
- 🔴 Write test: promote command full workflow
- 🟢 Implement promote command
- 🔴 Write test: Error handling
- 🟢 Add validation and error handling
- 🔵 Refactor: Clean up promotion logic
- ✅ Commit: "feat: Add promote command with validation"

### Day 5-6: Integration & Testing

**Day 5 Morning:**
- 🔴 Write integration test: Full workflow
- 🟢 Test: Check → Review → Promote
- 🔴 Write integration test: Multiple docs
- 🟢 Test with various scenarios
- ✅ Commit: "test: Add integration tests for workflow"

**Day 5 Afternoon:**
- Manual testing: Make real commits
- Detect changes with real repos
- Review real diffs
- Promote and verify backups
- ✅ Commit: "test: Validate workflow with real changes"

**Day 6: Polish & Documentation**
- Improve error messages
- Polish CLI output
- Update README with workflow examples
- Add troubleshooting guide
- ✅ Commit: "docs: Document change detection and review workflow"
- ✅ Sprint 5 complete! 🎉

---

## 📊 What You Learn

After Sprint 5, you'll discover:

1. **Change frequency** → Validates need for automated detection
2. **Review usability** → Informs diff display improvements
3. **Backup usage** → Informs retention policy needs
4. **Workflow friction** → Identifies automation opportunities
5. **Common promotion patterns** → Informs Sprint 6 orchestration

These learnings inform Sprint 6's batch operations and final polish.

---

## 🎯 Success Metrics

### Quantitative
- ✅ 4 new modules (~780 LOC + ~530 LOC tests)
- ✅ Test coverage >80%
- ✅ All tests passing
- ✅ Change detection runs in <30 seconds
- ✅ Review displays diffs correctly

### Qualitative
- ✅ Users can detect stale docs instantly
- ✅ Diffs are readable and helpful
- ✅ Promotion feels safe (backups!)
- ✅ Workflow is clear and intuitive
- ✅ User says "I know exactly what to do!"

---

## 🚧 Known Limitations (By Design)

1. **No batch regeneration** - Orchestration is Sprint 6
2. **No rollback command** - Manual restore from backup
3. **No backup retention** - Manual cleanup
4. **Simple change detection** - Hash-based only
5. **Terminal-only review** - No web UI

These limitations are **intentional**. Sprint 5 delivers core workflow. Sprint 6 adds orchestration.

---

## 🔮 Next Sprint Preview

After Sprint 5 ships, the final step is:

**Sprint 6: Orchestration & Polish** (1 week)

Sprint 6 completes the MVP:
- Batch regeneration of all changed docs
- Error handling polish across all commands
- Comprehensive documentation
- Final testing and bug fixes

The MVP will be production-ready after Sprint 6!

Let's finish Sprint 5 first! 🚀

---

**Ready to add the killer features? Start with Day 1 and follow the TDD workflow. Ship this sprint in 1 week!**
