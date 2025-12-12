# Feature Scope: doc-gen Tool

**Date:** 2025-12-12  
**Project:** doc-gen-tool  
**Repository:** amplifier-docs/tools/doc-gen/  
**Status:** MVP Definition - Ready for Sprint Planning

---

## The ONE Problem

**Documentation drifts from reality as code evolves across 20+ repositories, with no systematic way to detect changes or regenerate affected documentation.**

Users manually maintain documentation across multiple repositories, leading to:
- Stale docs that don't reflect current code
- No visibility into which docs need updating
- Time-consuming manual regeneration workflows
- Inconsistent documentation quality

---

## The Specific User

**Documentation maintainers** who:
- Manage docs that source from 20+ GitHub repositories
- Need to keep documentation in sync with evolving codebases
- Want structured generation workflows (outline → document)
- Need to review changes before publishing
- Currently solve this with manual ad-hoc Python scripts

---

## Current Solution & Why It Fails

**Current approach:**
- Ad-hoc Python scripts (`regenerate_module_docs.py`, `regenerate_from_outlines.py`)
- Manual tracking of which docs need updates
- No standardized source specification
- Throwaway scripts without consistent CLI interface

**Why insufficient:**
- Scripts lack discoverability (which commands exist?)
- No change detection - must manually decide what to regenerate
- No staging workflow - changes go directly to live docs
- Hard to validate source specifications before generation
- Each script reinvents the same patterns

---

## MVP Solution (4 Must-Have Features)

### 1. **Multi-Repo Source Management**

**What it does:**
- Initialize source specifications with `doc-gen init <doc-path>`
- Define which files from which repos via `sources.yaml`:
  - Multiple repositories with full URLs (supports forks)
  - Include OR exclude patterns per repo
  - Repo-specific authentication if needed
- Validate source specs with `doc-gen validate-sources <doc-path>`
  - Show which files match patterns
  - Catch errors before expensive generation

**Why essential:**
Core capability - can't generate docs without specifying sources. Multiple repos are fundamental to the problem (20+ repos). Validation prevents wasted LLM calls on broken specs.

**Commands:** `init`, `validate-sources`

---

### 2. **Two-Phase Generation Pipeline**

**What it does:**
- Generate outline from sources: `doc-gen generate-outline <doc-path>`
  - Clones repos to temp directory (cross-platform)
  - Aggregates source files
  - LLM creates structured outline with full context
  - Saves `outline.json` with commit hashes embedded
- Generate document from outline: `doc-gen generate-doc <doc-path>`
  - Uses outline + sources to generate markdown
  - Cheaper operation (can retry without re-outlining)
  - Outputs to staging directory

**Why essential:**
Separating expensive outline generation from cheaper doc generation enables:
- Iterate on doc generation without re-outlining
- Hand-edit outlines before generating docs
- Cost efficiency (don't re-analyze sources for each doc iteration)

Two-phase is fundamental to the design - not optional.

**Commands:** `generate-outline`, `generate-doc`

---

### 3. **Staging & Promotion Workflow**

**What it does:**
- Review staged changes: `doc-gen review <doc-path>`
  - Show diff between staging and live docs
  - Optionally open in editor for manual review
  - Confirm before promotion
- Promote to live: `doc-gen promote <doc-path>`
  - Copy staging doc to live docs directory
  - Update metadata with promotion timestamp
  - Preserve source tracking

**Why essential:**
Safety mechanism - can't push unreviewed AI-generated docs to live site. Users need to verify quality before publication. This prevents bad generations from reaching users.

**Commands:** `review`, `promote`

---

### 4. **Change Detection & Orchestration**

**What it does:**
- Detect source changes: `doc-gen check-changes [doc-path]`
  - Compare commit hashes in `outline.json` vs current repo state
  - Report which docs have stale sources
  - Show specific files that changed
- Regenerate changed docs: `doc-gen regenerate-changed`
  - Automatically regenerate all docs with detected changes
  - Run generate-outline → generate-doc for each
  - Report success/failure for each doc

**Why essential:**
Solves the core problem - without change detection, users still manually track what needs updating. Orchestration makes regeneration systematic, not ad-hoc. This is the "killer feature" that makes the tool valuable.

**Commands:** `check-changes`, `regenerate-changed`

---

## Architecture Overview

### Directory Structure

```
amplifier-docs/
├── docs/                          # LIVE docs (served by mkdocs)
│   ├── modules/
│   │   └── providers/
│   │       └── openai.md          # Live documentation
│   └── ...
│
├── .doc-gen/                      # Metadata and staging
│   ├── config.yaml                # Global config (temp dir, defaults)
│   └── metadata/                  # Per-document metadata
│       └── docs/modules/providers/openai/
│           ├── sources.yaml       # Source specification
│           ├── outline.json       # Generated outline + commit hashes
│           └── staging/
│               └── openai.md      # Staged doc (under review)
│
└── tools/doc-gen/                 # The tool itself
    ├── pyproject.toml
    ├── src/doc_gen/
    │   ├── __init__.py
    │   ├── cli.py                 # Click CLI commands
    │   ├── sources.py             # Source spec validation
    │   ├── repos.py               # Repository cloning
    │   ├── outline.py             # Outline generation
    │   ├── generation.py          # Doc generation
    │   ├── change_detection.py    # Commit hash comparison
    │   └── metadata.py            # Metadata management
    └── tests/
```

### Key Technical Decisions

1. **Repository Cloning:** Clone to temp directory by default (cross-platform, no disk bloat)
2. **Source Specification:** Include OR exclude patterns per repo (not both - simpler)
3. **Outline Format:** JSON with embedded commit hashes and full repo URLs
4. **Two-Phase Separation:** Outline generation (expensive) vs doc generation (cheaper)
5. **Hand-Editable:** `outline.json` can be manually edited before doc generation
6. **Staging First:** All generations go to staging, require explicit promotion

### Data Flow

```
User Action          → Command                → Output
─────────────────────────────────────────────────────────────
Define sources       → init                   → sources.yaml (template)
Validate sources     → validate-sources       → Matched files report
Generate outline     → generate-outline       → outline.json + commit hashes
Generate document    → generate-doc           → staging/[name].md
Review changes       → review                 → Diff display
Promote to live      → promote                → docs/[path]/[name].md
Check for changes    → check-changes          → Stale docs report
Regenerate all       → regenerate-changed     → Updated staging docs
```

### External Dependencies

- **Git:** Clone repositories, fetch commit hashes
- **GitHub API:** Optional (for authenticated access to private repos)
- **LLM Provider:** OpenAI/Anthropic for outline and doc generation
- **Python Libraries:**
  - `click` - CLI framework
  - `pyyaml` - YAML parsing
  - `gitpython` - Git operations
  - `openai` / `anthropic` - LLM APIs

---

## Success Criteria

The MVP succeeds when:

✅ **Functional Success:**
- [ ] Can initialize and validate source specs for multi-repo docs
- [ ] Can generate outlines from 20+ repositories with commit hash tracking
- [ ] Can generate documents from outlines to staging
- [ ] Can review diffs and promote staged docs to live
- [ ] Can detect source changes via commit hash comparison
- [ ] Can regenerate all changed docs with single command

✅ **Quality Success:**
- [ ] Generated docs are reviewable (not auto-promoted)
- [ ] Change detection accurately identifies stale docs
- [ ] CLI commands are discoverable (`doc-gen --help` shows all commands)
- [ ] Error messages guide users to fix issues (bad YAML, missing files, etc.)

✅ **Adoption Success:**
- [ ] Documentation maintainer uses it instead of ad-hoc scripts
- [ ] At least 5 docs successfully generated and promoted
- [ ] Change detection catches real source updates within 1 day
- [ ] User reports "this is better than manual scripts"

---

## Timeline Estimate

**Target:** Ship MVP within **3-4 weeks** (split into 3 sprints)

**Sprint 1 (1 week):** Core infrastructure
- Project setup, CLI framework
- Source specification and validation
- Repository cloning utilities

**Sprint 2 (1-2 weeks):** Generation pipeline  
- Outline generation from multi-repo sources
- Document generation from outlines
- Staging directory management

**Sprint 3 (1 week):** Change detection & orchestration
- Commit hash tracking
- Change detection logic
- Promotion workflow
- Regenerate-changed command

**Buffer:** 1 week for iteration, bug fixes, and polish

---

## Out of Scope (Explicitly Deferred)

The following are valuable but NOT part of MVP:

- ❌ Evaluation harness for prompt testing
- ❌ Smart change detection (line count thresholds, significance filtering)
- ❌ GitHub Actions automation for scheduled regeneration
- ❌ Advanced batch operations beyond `regenerate-changed`
- ❌ Interactive source editor (just edit YAML manually in MVP)
- ❌ Web UI for reviewing diffs (CLI is sufficient for MVP)
- ❌ Template system for doc structure customization
- ❌ Support for non-Git source repositories

These will be considered for future versions after MVP validation.

---

## Definition of Done

The MVP is complete when:

1. All 8 CLI commands are implemented and tested
2. Documentation exists for each command (README + CLI help)
3. Successfully generated and promoted 5+ real docs from amplifier-docs
4. Change detection tested with actual git history
5. User (documentation maintainer) validates it solves their problem
6. Code reviewed for simplicity and maintainability

---

## Next Steps

1. **Review this feature scope** - Confirm this is the right MVP
2. **Sprint Planning** - Break into executable tasks with sprint-planner agent
3. **Implementation** - Build following modular-builder patterns
4. **Validation** - Test with real amplifier-docs documentation

---

**Note:** No version number assigned yet. The sprint-planner will determine the initial version (likely v0.1.0) based on release strategy.
