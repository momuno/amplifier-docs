# Sprint 1: Core Infrastructure & Config

**Duration:** 1 week  
**Goal:** Build foundational infrastructure with proper config management  
**Value Delivered:** Working CLI tool with metadata management and config for API keys

---

## 🎯 Why This Sprint?

Sprint 1 establishes the **foundation** for everything else. Before we can integrate LLMs (Sprint 2), we need:

1. **Working CLI framework** - Users interact via commands
2. **Metadata management** - Store sources, outlines, staging docs
3. **Config management** - API keys and settings (BEFORE first LLM call!)
4. **Repository cloning** - Prove we can clone and extract from Git repos
5. **Project structure** - Installable Python package

By the end of Sprint 1, you'll have:
- A working `doc-gen` CLI tool that can be installed
- Config management for API keys (no hardcoded credentials)
- Basic commands: `init`, and infrastructure for future commands
- Single-repo cloning working (proves the concept)
- Clear foundation for Sprint 2's LLM integration

This is your **embarrassingly simple foundation** - no LLM integration yet, no multi-repo, but everything is in place to add those features incrementally.

---

## 📦 Deliverables

### 1. Project Structure & Setup
**Estimated Lines:** ~50 lines (setup files)

**What it does:**
- Creates proper Python package structure
- Defines dependencies in `pyproject.toml`
- Sets up testing infrastructure
- Enables installation via `pip install -e .`

**Why this sprint:**
Foundation for everything else. Need this before we can write code that imports properly.

**Implementation notes:**
```
tools/doc-gen/
├── pyproject.toml          # Package definition
├── README.md               # Basic usage guide
├── .env.example            # Example environment variables
├── src/doc_gen/
│   ├── __init__.py         # Package marker
│   ├── cli.py              # CLI commands
│   ├── config.py           # Config management (NEW!)
│   ├── metadata.py         # Metadata management
│   └── repos.py            # Repository operations
└── tests/
    ├── __init__.py         # Test package marker
    ├── test_config.py      # Config tests
    ├── test_metadata.py    # Metadata tests
    └── test_repos.py       # Repository tests
```

**Key decisions:**
- Use `pyproject.toml` (modern Python packaging)
- Use `click` for CLI (better than argparse for commands)
- Use `pytest` for testing (industry standard)
- Support Python 3.11+ only (no legacy baggage)

---

### 2. Config Management (`config.py`)
**Estimated Lines:** ~120 lines + ~100 lines tests

**What it does:**
- Manages global configuration in `.doc-gen/config.yaml`
- Loads API keys from config or environment variables
- Supports model selection (gpt-4, claude-3, etc.)
- Validates configuration on load
- Provides defaults for optional settings

**Why this sprint:**
MUST have config management BEFORE Sprint 2's LLM integration. No hardcoded API keys.

**Implementation notes:**
```python
from pathlib import Path
import yaml
import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class Config:
    """Global configuration for doc-gen."""
    
    # LLM Configuration
    llm_provider: str = "openai"  # openai, anthropic
    llm_model: str = "gpt-4"
    llm_api_key: Optional[str] = None
    llm_timeout: int = 60  # seconds
    
    # Repository Configuration
    temp_dir: Optional[Path] = None  # None = use system temp
    
    @classmethod
    def load(cls, config_path: Path = Path(".doc-gen/config.yaml")) -> "Config":
        """Load configuration from file and environment."""
        # 1. Load from config.yaml if exists
        # 2. Override with environment variables
        # 3. Validate required fields
        pass
    
    def save(self, config_path: Path = Path(".doc-gen/config.yaml")):
        """Save configuration to file."""
        pass
    
    def validate(self):
        """Validate configuration is complete."""
        if not self.llm_api_key:
            raise ValueError(
                "LLM API key not found. Set in config.yaml or environment:\n"
                "  export OPENAI_API_KEY=your-key-here"
            )
```

**Config file format (.doc-gen/config.yaml):**
```yaml
# doc-gen global configuration
llm:
  provider: openai  # openai, anthropic
  model: gpt-4      # gpt-4, gpt-3.5-turbo, claude-3-opus, etc.
  # API key loaded from environment variable:
  # - OPENAI_API_KEY for OpenAI
  # - ANTHROPIC_API_KEY for Anthropic
  timeout: 60       # seconds

repositories:
  # temp_dir: /custom/temp/dir  # Optional: custom temp directory
```

**Key decisions:**
- API keys from environment variables (not stored in config file)
- Config file is optional (can use all environment variables)
- Validate config on load (fail fast if misconfigured)
- Create config template on first run if missing

---

### 3. CLI Framework (`cli.py`)
**Estimated Lines:** ~150 lines + ~100 lines tests

**What it does:**
- Defines Click command group `doc-gen`
- Implements `init` command
- Provides `--help` text for each command
- Handles basic error display
- Loads config before executing commands

**Why this sprint:**
Users interact with CLI first. Must be discoverable and work immediately.

**Implementation notes:**
```python
import click
from pathlib import Path
from .config import Config
from .metadata import MetadataManager

@click.group()
@click.pass_context
def cli(ctx):
    """Multi-repository documentation generation tool."""
    # Load config and store in context
    ctx.ensure_object(dict)
    try:
        ctx.obj['config'] = Config.load()
    except FileNotFoundError:
        # Config doesn't exist yet - create template
        click.echo("No config found. Creating template at .doc-gen/config.yaml")
        Config().save()
        click.echo("Please edit config and add your API key, or set environment variable.")
        ctx.exit(1)

@cli.command()
@click.argument('doc-path', type=click.Path())
def init(doc_path: str):
    """Initialize source specification for a document.
    
    Creates a sources.yaml template at:
      .doc-gen/metadata/{doc-path}/sources.yaml
    
    Example:
      doc-gen init docs/modules/providers/openai.md
    """
    metadata = MetadataManager(doc_path)
    metadata.init_sources()
    
    click.echo(f"✓ Initialized sources for {doc_path}")
    click.echo(f"✓ Edit: {metadata.sources_path}")
    click.echo(f"\nNext steps:")
    click.echo(f"  1. Edit sources.yaml to define repositories")
    click.echo(f"  2. Run: doc-gen generate-outline {doc_path}")

# Placeholder commands for future sprints
@cli.command()
@click.argument('doc-path', type=click.Path())
@click.pass_context
def generate_outline(ctx, doc_path: str):
    """Generate outline from source files (Sprint 2)."""
    click.echo("Coming in Sprint 2: Outline generation")
    
@cli.command()
@click.argument('doc-path', type=click.Path())
def generate_doc(doc_path: str):
    """Generate document from outline (Sprint 3)."""
    click.echo("Coming in Sprint 3: Document generation")
```

**Key decisions:**
- Use Click's `@click.group()` for subcommands
- Use `click.argument()` for required `doc-path`
- Use `click.echo()` for output (not print)
- Return proper exit codes (0 = success, 1 = error)
- Load config in group decorator (available to all commands)

---

### 4. Metadata Management (`metadata.py`)
**Estimated Lines:** ~180 lines + ~120 lines tests

**What it does:**
- Creates metadata directory structure: `.doc-gen/metadata/{doc-path}/`
- Writes `sources.yaml` template with comments
- Reads source specifications
- Manages `outline.json` storage (Sprint 2 will use this)
- Manages staging directory (Sprint 3 will use this)

**Why this sprint:**
All other modules need to read/write metadata. Build this foundation first.

**Implementation notes:**
```python
from pathlib import Path
import yaml
import json
from typing import Dict, Any, Optional

class MetadataManager:
    """Manages .doc-gen metadata for a document."""
    
    def __init__(self, doc_path: str):
        self.doc_path = Path(doc_path)
        # .doc-gen/metadata/docs/modules/providers/openai/
        self.metadata_dir = (
            Path('.doc-gen/metadata') / 
            self.doc_path.parent / 
            self.doc_path.stem
        )
        self.sources_path = self.metadata_dir / 'sources.yaml'
        self.outline_path = self.metadata_dir / 'outline.json'
        self.staging_dir = self.metadata_dir / 'staging'
        
    def init_sources(self):
        """Create sources.yaml template."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        template = {
            'repositories': [
                {
                    'url': 'https://github.com/owner/repo.git',
                    'include': [
                        '*.py',
                        'README.md',
                    ],
                    'exclude': [
                        'tests/**',
                        '**/__pycache__/**',
                    ]
                }
            ],
            'metadata': {
                'purpose': 'Document the [feature/module] functionality',
                'last_updated': None,
            }
        }
        
        with open(self.sources_path, 'w') as f:
            yaml.dump(template, f, sort_keys=False, default_flow_style=False)
        
    def read_sources(self) -> Dict[str, Any]:
        """Load sources.yaml configuration."""
        if not self.sources_path.exists():
            raise FileNotFoundError(
                f"Sources not found: {self.sources_path}\n"
                f"Initialize with: doc-gen init {self.doc_path}"
            )
        
        with open(self.sources_path, 'r') as f:
            return yaml.safe_load(f)
        
    def save_outline(self, outline_data: Dict[str, Any]):
        """Save outline.json with commit hashes."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.outline_path, 'w') as f:
            json.dump(outline_data, f, indent=2)
        
    def read_outline(self) -> Dict[str, Any]:
        """Load existing outline.json."""
        if not self.outline_path.exists():
            raise FileNotFoundError(
                f"Outline not found: {self.outline_path}\n"
                f"Generate with: doc-gen generate-outline {self.doc_path}"
            )
        
        with open(self.outline_path, 'r') as f:
            return json.load(f)
        
    def get_staging_path(self) -> Path:
        """Return path to staging document."""
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        return self.staging_dir / f"{self.doc_path.name}"
    
    @staticmethod
    def find_all_docs() -> list[Path]:
        """Find all docs with metadata (Sprint 5 will use this)."""
        metadata_root = Path('.doc-gen/metadata')
        if not metadata_root.exists():
            return []
        
        # Find all sources.yaml files
        sources_files = list(metadata_root.rglob('sources.yaml'))
        # Convert back to doc paths
        return [
            Path('docs') / sources_file.parent.relative_to(metadata_root)
            for sources_file in sources_files
        ]
```

**Key decisions:**
- Use pathlib.Path for all file operations
- Use PyYAML for YAML parsing
- Create directories with `mkdir(parents=True, exist_ok=True)`
- Store everything under `.doc-gen/` (hidden from users)
- Template includes comments and examples

---

### 5. Repository Management (`repos.py`)
**Estimated Lines:** ~150 lines + ~120 lines tests

**What it does:**
- Clones Git repositories to temp directory
- Manages temporary directory lifecycle
- Extracts commit hashes for files
- Lists files matching patterns (basic in Sprint 1, enhanced in Sprint 4)

**Why this sprint:**
Must be able to clone and inspect source repositories. Proves the concept works.

**Implementation notes:**
```python
import tempfile
from pathlib import Path
from git import Repo
from typing import Optional, List

class RepoManager:
    """Manages Git repository operations."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir_obj = None
        self.temp_dir = temp_dir
        
    def __enter__(self):
        if self.temp_dir is None:
            self.temp_dir_obj = tempfile.TemporaryDirectory()
            self.temp_dir = Path(self.temp_dir_obj.name)
        else:
            self.temp_dir = Path(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir_obj:
            self.temp_dir_obj.cleanup()
    
    def clone_repo(self, repo_url: str, shallow: bool = True) -> Path:
        """Clone repository to temp directory.
        
        Args:
            repo_url: Git repository URL
            shallow: If True, use --depth 1 for faster cloning
            
        Returns:
            Path to cloned repository
        """
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        clone_path = self.temp_dir / repo_name
        
        # Clone with shallow option for speed
        if shallow:
            Repo.clone_from(repo_url, clone_path, depth=1)
        else:
            Repo.clone_from(repo_url, clone_path)
        
        return clone_path
    
    def get_file_commit_hash(self, repo_path: Path, file_path: str) -> str:
        """Get latest commit hash for a specific file.
        
        Args:
            repo_path: Path to cloned repository
            file_path: Relative path to file within repo
            
        Returns:
            Full commit hash (40 characters)
        """
        repo = Repo(repo_path)
        commits = list(repo.iter_commits(paths=file_path, max_count=1))
        
        if not commits:
            raise ValueError(f"No commits found for file: {file_path}")
        
        return commits[0].hexsha
    
    def list_files(self, repo_path: Path, include_patterns: List[str]) -> List[Path]:
        """List files matching include patterns.
        
        Sprint 1: Simple glob matching
        Sprint 4: Will enhance with pathspec for gitignore-style patterns
        
        Args:
            repo_path: Path to repository
            include_patterns: List of glob patterns
            
        Returns:
            List of file paths (relative to repo root)
        """
        matched_files = []
        
        for pattern in include_patterns:
            # Simple glob matching for Sprint 1
            matched_files.extend(repo_path.glob(pattern))
        
        # Convert to relative paths and filter out directories
        relative_files = [
            f.relative_to(repo_path)
            for f in matched_files
            if f.is_file()
        ]
        
        # Remove duplicates
        return list(set(relative_files))
```

**Key decisions:**
- Use GitPython for Git operations
- Use `tempfile.TemporaryDirectory()` context manager
- Use `--depth 1` for shallow clones (faster, Sprint 1 proof)
- Return absolute paths initially, convert to relative as needed
- Simple glob matching in Sprint 1, pathspec in Sprint 4

---

## 🚫 What Gets Punted (Deliberately Excluded)

### LLM Integration
- ❌ Outline generation
- ❌ Document generation
- Why: Sprint 2 and 3 focus entirely on LLM work
- Reconsider: Sprint 2 (immediate next step)

### Multi-Repository Support
- ❌ Multiple repos in one sources.yaml
- Why: Sprint 1 proves single-repo works. Multi-repo is Sprint 4.
- Reconsider: Sprint 4 (after LLM integration works)

### Source Validation
- ❌ `validate-sources` command
- Why: Manual testing is fine for proving the concept
- Reconsider: Sprint 4 (when multi-repo makes validation critical)

### Change Detection
- ❌ `check-changes` command
- ❌ Commit hash comparison logic
- Why: Sprint 1 focuses on foundation, not workflows
- Reconsider: Sprint 5 (the killer feature)

### Review/Promote Workflow
- ❌ `review` and `promote` commands
- Why: No generated docs yet to review
- Reconsider: Sprint 5 (workflow safety)

---

## 🔗 Dependencies

**Requires from previous sprints:** None (this is Sprint 1!)

**Provides for future sprints:**
- Working CLI framework (add more commands in Sprint 2+)
- Config management (Sprint 2 uses for LLM API keys)
- Metadata management (Sprint 2+ uses for all operations)
- Repo cloning utilities (Sprint 4 scales to multiple repos)

---

## ✅ Acceptance Criteria

### Must Have

- ✅ **Install tool**: `cd tools/doc-gen && pip install -e .`
- ✅ **Config template**: First run creates `.doc-gen/config.yaml` template
- ✅ **Environment variable support**: Can set `OPENAI_API_KEY` instead of config
- ✅ **Initialize sources**: `doc-gen init docs/test.md`
  - Creates `.doc-gen/metadata/docs/test/sources.yaml`
  - YAML contains template with example repository
- ✅ **Read sources**: MetadataManager can parse sources.yaml
- ✅ **Clone repository**: RepoManager can clone a test repo to temp dir
- ✅ **Extract commit hash**: Can get commit hash for a file
- ✅ **List files**: Can list files matching glob patterns
- ✅ **Help text**: `doc-gen --help` shows all commands
- ✅ **Test coverage**: >80% for all new modules

### Nice to Have (Defer if time constrained)

- ❌ Colored terminal output
- ❌ Progress spinners
- ❌ Config validation subcommand

---

## 🛠️ Technical Approach

### Testing Strategy

**Follow TDD for all modules:**

1. **🔴 RED - Write failing test first**
   - Write test for behavior you want
   - Run test → Watch it fail → Good!

2. **🟢 GREEN - Write minimal implementation**
   - Just enough code to pass the test
   - Run test → Watch it pass → Good!

3. **🔵 REFACTOR - Improve code quality**
   - Clean up duplication
   - Improve names
   - Extract functions
   - Run tests → Still pass → Good!

4. **✅ COMMIT - Green tests**
   - Commit after each red-green-refactor cycle
   - All commits should have passing tests

**Unit Tests:**
- `Config.load()` from file and environment
- `Config.validate()` catches missing API key
- `MetadataManager.init_sources()` creates template
- `MetadataManager.read_sources()` parses YAML
- `RepoManager.clone_repo()` clones successfully
- `RepoManager.get_file_commit_hash()` returns hash
- `RepoManager.list_files()` matches patterns

**Integration Tests:**
- CLI command parsing
- `doc-gen init` creates proper structure
- End-to-end: Config load → Metadata init → Repo clone

**Manual Testing:**
- [ ] Install package and run `doc-gen --help`
- [ ] Create config with real API key
- [ ] Initialize sources for test document
- [ ] Clone a real repository (e.g., amplifier repo)
- [ ] Extract commit hashes from real files

**Test Coverage Target:** >80% for new code

**Mocking Strategy:**
- Mock Git clone operations in some tests (faster)
- Use real Git operations with test repos in others (confidence)
- Use real file I/O (with temp directories)

---

## 📋 Implementation Order

**Follow TDD: 🔴 Write test → 🟢 Implement → 🔵 Refactor → ✅ Commit**

### Day 1: Project Setup & Config Management

**Morning:**
- 🔴 Write test: pyproject.toml is valid
- 🟢 Create `pyproject.toml` with dependencies
- 🔵 Refactor: Add dev dependencies (pytest, coverage)
- ✅ Commit: "feat: Add project structure and dependencies"

**Afternoon:**
- 🔴 Write test: `Config.load()` loads from file
- 🟢 Implement `Config` dataclass and `load()` method
- 🔴 Write test: `Config.load()` loads from environment
- 🟢 Add environment variable support
- 🔴 Write test: `Config.validate()` catches missing API key
- 🟢 Implement validation
- 🔵 Refactor: Extract validation logic
- ✅ Commit: "feat: Add config management with validation"

### Day 2: Metadata Management

**Morning:**
- 🔴 Write test: `MetadataManager.__init__()` creates paths
- 🟢 Implement `MetadataManager.__init__()`
- 🔴 Write test: `init_sources()` creates YAML template
- 🟢 Implement `init_sources()`
- 🔴 Write test: Template YAML is valid
- 🟢 Ensure template structure is correct
- ✅ Commit: "feat: Add metadata management and sources.yaml template"

**Afternoon:**
- 🔴 Write test: `read_sources()` parses YAML
- 🟢 Implement `read_sources()`
- 🔴 Write test: `read_sources()` raises error if file missing
- 🟢 Add error handling with helpful message
- 🔴 Write test: `save_outline()` and `read_outline()`
- 🟢 Implement outline JSON handling
- 🔵 Refactor: Extract file I/O patterns
- ✅ Commit: "feat: Add sources and outline file management"

### Day 3: Repository Management

**Morning:**
- 🔴 Write test: `RepoManager` context manager
- 🟢 Implement `__enter__` and `__exit__`
- 🔴 Write test: Context manager creates temp directory
- 🟢 Add temp directory creation
- 🔴 Write test: Context manager cleans up
- 🟢 Ensure cleanup happens
- ✅ Commit: "feat: Add RepoManager with temp directory management"

**Afternoon:**
- 🔴 Write test: `clone_repo()` clones test repository
- 🟢 Implement using GitPython
- 🔴 Write test: Shallow clone is faster
- 🟢 Add `shallow` parameter
- 🔵 Refactor: Add error handling for clone failures
- ✅ Commit: "feat: Add repository cloning with shallow option"

### Day 4: Repository Operations

**Morning:**
- 🔴 Write test: `get_file_commit_hash()` returns hash
- 🟢 Implement using GitPython
- 🔴 Write test: Handles file not found
- 🟢 Add error handling
- ✅ Commit: "feat: Add commit hash extraction for files"

**Afternoon:**
- 🔴 Write test: `list_files()` matches glob patterns
- 🟢 Implement glob pattern matching
- 🔴 Write test: Filters out directories
- 🟢 Ensure only files returned
- 🔴 Write test: Removes duplicates
- 🟢 Add deduplication
- 🔵 Refactor: Clean up pattern matching logic
- ✅ Commit: "feat: Add file listing with pattern matching"

### Day 5: CLI Framework

**Morning:**
- 🔴 Write test: CLI group loads without errors
- 🟢 Implement `cli.py` with Click group
- 🔴 Write test: Config loaded in context
- 🟢 Add config loading to group decorator
- 🔴 Write test: Missing config creates template
- 🟢 Implement config template creation
- ✅ Commit: "feat: Add CLI framework with config loading"

**Afternoon:**
- 🔴 Write test: `init` command creates metadata
- 🟢 Implement `init` command (calls MetadataManager)
- 🔴 Write test: `init` shows helpful messages
- 🟢 Add success messages and next steps
- 🔵 Refactor: Extract message formatting
- ✅ Commit: "feat: Add init command for source initialization"

### Day 6: CLI Installation & Help

**Morning:**
- 🔴 Write test: Install package via pip
- 🟢 Configure entry points in pyproject.toml
- 🔴 Write test: `doc-gen --help` shows commands
- 🟢 Add help text to CLI group
- 🔴 Write test: Each command has help text
- 🟢 Add docstrings to all commands
- ✅ Commit: "feat: Make doc-gen installable CLI tool with help text"

**Afternoon:**
- 🔴 Write test: Placeholder commands return helpful messages
- 🟢 Add `generate-outline` and `generate-doc` placeholders
- 🔴 Write test: Commands show "Coming in Sprint X"
- 🟢 Add sprint preview messages
- ✅ Commit: "feat: Add placeholder commands for future sprints"

### Day 7: Integration Testing & Documentation

**Morning:**
- 🔴 Write integration test: Full init workflow
- 🟢 Test: Config → Init → Sources created
- 🔴 Write integration test: Clone real repo
- 🟢 Test: Clone → List files → Get hashes
- 🔵 Refactor: Fix integration bugs
- ✅ Commit: "test: Add integration tests for Sprint 1 features"

**Afternoon:**
- Manual testing: Install and run against real repos
- Write README.md with installation and usage
- Add .env.example file
- Update CLI help text based on testing
- ✅ Commit: "docs: Add README and usage examples"

**Evening: Sprint Review**
- Verify all acceptance criteria met
- Demo working tool: install, init, clone
- Celebrate foundation complete! 🎉
- ✅ Sprint 1 complete - ready for Sprint 2!

---

## 📊 What You Learn

After Sprint 1, you'll discover:

1. **Config patterns** → Informs how Sprint 2 loads LLM credentials
2. **Metadata structure** → Confirms directory layout works
3. **Repository operations** → Validates GitPython approach
4. **CLI usability** → Informs command design for Sprint 2+
5. **Testing patterns** → Establishes TDD workflow for future sprints

These learnings directly enable Sprint 2's LLM integration.

---

## 🎯 Success Metrics

### Quantitative
- ✅ 4 modules implemented (~600 LOC + ~440 LOC tests)
- ✅ Test coverage >80%
- ✅ All unit and integration tests passing
- ✅ CLI commands load in <1 second

### Qualitative
- ✅ User can install the tool
- ✅ User can configure API keys securely
- ✅ User can initialize sources for a document
- ✅ Repository cloning works reliably
- ✅ Team member says "the foundation looks solid!"

---

## 🚧 Known Limitations (By Design)

1. **No LLM integration** - That's Sprint 2 and 3
2. **Single repository only** - Multi-repo is Sprint 4
3. **Simple glob matching** - Pathspec patterns are Sprint 4
4. **No validation command** - Validation is Sprint 4
5. **No change detection** - Detection is Sprint 5
6. **No review/promote** - Workflow is Sprint 5

These limitations are **intentional**. Sprint 1 proves the infrastructure works. Sprints 2-6 add the features.

---

## 🔮 Next Sprint Preview

After Sprint 1 ships, the most pressing need is:

**Sprint 2: Outline Generation** - First LLM integration with prompt engineering

This will be **the hard sprint**. Budget 1-1.5 weeks for:
- LLM API integration
- Prompt engineering (iteration!)
- JSON parsing and validation
- Error handling (timeouts, rate limits)
- Token counting and cost tracking

Sprint 1's config management makes this possible. Let's build it! 🚀

---

**Ready to build? Start with Day 1 and follow the TDD workflow. Ship this sprint in 1 week!**
