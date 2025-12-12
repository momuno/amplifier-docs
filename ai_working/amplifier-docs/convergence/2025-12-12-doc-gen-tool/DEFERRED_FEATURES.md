# Deferred Features: doc-gen Tool

**Date:** 2025-12-12  
**Origin:** doc-gen-tool convergence  
**MVP Scope:** 4 core features (source management, generation pipeline, staging workflow, change detection)

---

## Phase 2 (High Priority - Consider Next)

### Evaluation Harness for Prompt Testing

**What it does:**
- Test prompt variations against known-good documentation examples
- Automated quality scoring (completeness, accuracy, formatting)
- A/B comparison of different prompt strategies
- Regression detection when prompts change
- Metrics dashboard for prompt performance

**Functionality includes:**
- Define evaluation datasets (source files → expected doc qualities)
- Run generation with multiple prompt variants
- Score outputs automatically (embedding similarity, structure validation, etc.)
- Compare results side-by-side
- Track prompt performance over time

**Why deferred:** 
MVP focuses on getting the core pipeline working. Prompt optimization is valuable but requires the core system to exist first. Current approach: manual review of generated docs.

**Reconsider when:**
- MVP ships and users report quality issues
- We need to iterate on prompts systematically
- Multiple doc types require different prompt strategies
- Users request better control over generation quality

**Effort:** 1-2 weeks  
**Complexity:** High  
**Theme:** quality-assurance, prompt-engineering, testing

---

### Smart Change Detection

**What it does:**
- Detect *significant* changes, not just any commit
- Line count thresholds (e.g., only regenerate if >10% lines changed)
- Filter by file type (ignore README changes, focus on code)
- Semantic analysis (did the API actually change?)
- Confidence scoring for "how stale is this doc?"

**Functionality includes:**
- Configure change thresholds in `config.yaml`
- `check-changes --smart` flag for filtered detection
- Report change significance scores
- `regenerate-changed --threshold=0.7` to regenerate only high-confidence stale docs
- Explain *why* regeneration is recommended

**Why deferred:**
MVP uses simple commit hash comparison - regenerate if ANY tracked file changed. This is sufficient to prove the concept. Smart detection requires tuning and may over-complicate initial release.

**Reconsider when:**
- Users complain about too many false positive regenerations
- Source repos have frequent non-meaningful commits
- Regeneration costs become significant (too many LLM calls)
- Users want more control over when to regenerate

**Effort:** 1-2 weeks  
**Complexity:** Medium-High  
**Theme:** change-detection, optimization, cost-control

---

### GitHub Actions Automation

**What it does:**
- Scheduled workflow to check changes daily/weekly
- Auto-regenerate and create PRs with updated docs
- Post-commit hooks to detect changes on push
- Notification system (Slack, email) when docs are stale
- Integration with CI/CD for automated validation

**Functionality includes:**
- `.github/workflows/doc-gen-check.yml` for scheduled checks
- `doc-gen check-changes --ci` mode with machine-readable output
- `doc-gen regenerate-changed --create-pr` to auto-create PRs
- Status badges showing doc freshness
- Webhook integration for external triggers

**Why deferred:**
MVP is CLI-first. Automation is valuable but requires stable core system first. Users can manually run commands until automation is needed. Premature automation adds complexity.

**Reconsider when:**
- MVP proves valuable and users want automation
- Manual regeneration becomes tedious
- Team wants scheduled doc updates without manual intervention
- Multiple contributors need automated doc validation

**Effort:** 1 week  
**Complexity:** Medium  
**Theme:** automation, ci-cd, integration

---

## Phase 3 (Medium Priority)

### Advanced Batch Operations

**What it does:**
- Batch operations beyond `regenerate-changed`
- `doc-gen regenerate-all` - Force regenerate everything
- `doc-gen regenerate-pattern "modules/*"` - Regenerate by path pattern
- `doc-gen validate-all` - Validate all source specs
- `doc-gen promote-all` - Bulk promotion of reviewed docs
- Parallel execution for faster batch operations

**Functionality includes:**
- Glob pattern matching for selective operations
- `--parallel` flag for concurrent execution
- Progress bars for long-running operations
- Dry-run modes (`--dry-run`) to preview actions
- Logging and error handling for batch failures

**Why deferred:**
MVP focuses on per-doc operations and simple orchestration. Batch operations are convenient but not essential for initial validation. Users can script their own batch operations if needed.

**Reconsider when:**
- Users manage 50+ docs and need bulk operations
- Manual iteration over docs becomes tedious
- Performance becomes an issue (need parallelization)
- Common patterns emerge for batch workflows

**Effort:** 1 week  
**Complexity:** Medium  
**Theme:** batch-operations, performance, ux

---

### Interactive Source Editor

**What it does:**
- TUI (Terminal UI) for editing `sources.yaml`
- Visual file browser to select includes/excludes
- Real-time validation as you edit
- Repository preview (show matched files before saving)
- Templates for common source patterns

**Functionality includes:**
- `doc-gen edit-sources <doc-path>` opens TUI
- Browse repository file tree interactively
- Toggle include/exclude patterns visually
- Live preview of matched files
- Save and validate in one step
- Common patterns library (e.g., "all Python files", "API docs only")

**Why deferred:**
MVP uses manual YAML editing, which is sufficient for power users. Interactive editor is nice-to-have but adds significant complexity. YAML is hand-editable and version-controllable.

**Reconsider when:**
- Non-technical users need to define sources
- Common errors emerge from manual YAML editing
- Users request "easier way to specify sources"
- Pattern selection becomes tedious

**Effort:** 2 weeks  
**Complexity:** Medium-High  
**Theme:** ux, interactive, tui

---

### Web UI for Review and Promotion

**What it does:**
- Local web server for reviewing docs visually
- Side-by-side diff viewer (live vs staging)
- Markdown preview with styling
- One-click promotion from browser
- Batch review interface for multiple docs

**Functionality includes:**
- `doc-gen serve-review` starts local web server
- Navigate all docs with staging changes
- Visual diff highlighting
- Promote/reject buttons per doc
- Comments/notes on reviewed docs
- Export review decisions as audit log

**Why deferred:**
CLI-based review (`doc-gen review`) with diff output is sufficient for MVP. Web UI is more user-friendly but adds significant development overhead. Terminal users are comfortable with CLI diffs.

**Reconsider when:**
- Non-technical reviewers need to approve docs
- Team wants centralized review workflow
- Visual diff becomes essential (complex formatting)
- Multiple reviewers need coordination

**Effort:** 2-3 weeks  
**Complexity:** High  
**Theme:** ux, web-ui, collaboration

---

### Template System for Doc Structure

**What it does:**
- Define custom templates for doc structure
- Per-doc-type templates (API docs, guides, tutorials)
- Template variables and sections
- Conditional content based on source characteristics
- Template inheritance and composition

**Functionality includes:**
- `templates/` directory with Jinja2 templates
- `sources.yaml` specifies template: `template: api-reference`
- Template variables populated from outline
- Conditional sections (e.g., "Examples" only if examples exist)
- Override templates per doc or globally

**Why deferred:**
MVP generates freeform markdown based on LLM prompts. Templates add structure but limit flexibility. Better to learn what structure works before codifying templates.

**Reconsider when:**
- Generated docs have inconsistent structure
- Multiple doc types need different formats
- Users want more control over doc structure
- Certain sections should always be present/absent

**Effort:** 2 weeks  
**Complexity:** Medium  
**Theme:** templates, structure, customization

---

### Multi-Source Type Support (Beyond Git)

**What it does:**
- Support non-Git sources (local directories, archives, URLs)
- Pull from documentation systems (Confluence, Notion, etc.)
- Aggregate from API endpoints (OpenAPI specs, etc.)
- Mixed-source docs (Git + API + local files)
- Source plugins for extensibility

**Functionality includes:**
- `source_type: local` in `sources.yaml` for local directories
- `source_type: url` for direct file downloads
- `source_type: api` for structured API sources
- Plugin system for custom source types
- Unified interface regardless of source type

**Why deferred:**
MVP focuses on Git repositories (the stated problem domain). Supporting other sources adds complexity without validating core value. Git sources cover 95% of use cases.

**Reconsider when:**
- Users need to source from non-Git systems
- Documentation spans multiple source types
- Integration with other systems becomes common
- Plugin ecosystem emerges

**Effort:** 2-3 weeks  
**Complexity:** High  
**Theme:** extensibility, integration, sources

---

### Incremental Outline Updates

**What it does:**
- Update outlines incrementally instead of full regeneration
- Detect which sections of outline need updating
- Preserve manually edited sections of outline
- Merge strategy for outline conflicts
- Partial regeneration of documents

**Functionality includes:**
- `doc-gen update-outline <doc-path>` for incremental updates
- Diff existing outline with new source analysis
- Preserve manual edits with conflict markers
- `--sections` flag to update specific sections only
- Merge manual edits with LLM-generated updates

**Why deferred:**
MVP regenerates outlines completely when sources change. This is simpler and sufficient for initial validation. Incremental updates are optimization for established workflows.

**Reconsider when:**
- Outline regeneration becomes too slow
- Users frequently hand-edit outlines
- Merge conflicts become common pain point
- Partial updates are clearly needed

**Effort:** 2 weeks  
**Complexity:** High  
**Theme:** optimization, merge-strategies, ux

---

## Future / Parking Lot (Low Priority)

### Documentation Quality Metrics

**What it does:**
- Automated quality scoring for generated docs
- Metrics: completeness, clarity, accuracy, formatting
- Trend tracking over time
- Alerts when quality degrades

**Why deferred:**
Quality is initially validated by human review. Automated metrics require ML models or extensive heuristics. Premature optimization.

**Reconsider when:**
- Quality issues emerge systematically
- Need to track doc quality at scale
- Automated alerts would prevent issues

**Effort:** 2-3 weeks  
**Complexity:** High  
**Theme:** quality-assurance, metrics, monitoring

---

### Multi-Language Documentation

**What it does:**
- Generate docs in multiple languages
- Translation memory for consistency
- Language-specific templates
- Localization workflow

**Why deferred:**
Out of scope for MVP - single language (English) is sufficient. Translation is separate concern.

**Reconsider when:**
- Multiple language requirements emerge
- International users request localized docs
- Translation becomes bottleneck

**Effort:** 3-4 weeks  
**Complexity:** High  
**Theme:** i18n, localization, translation

---

### Version-Specific Documentation

**What it does:**
- Generate docs for multiple code versions
- Version selector in documentation
- Diff docs between versions
- Track breaking changes across versions

**Why deferred:**
MVP generates current-version docs. Version management is complex and not needed for initial validation.

**Reconsider when:**
- Need to maintain docs for multiple versions
- Breaking changes require version-specific docs
- Users request historical documentation

**Effort:** 2-3 weeks  
**Complexity:** High  
**Theme:** versioning, compatibility, history

---

### AI-Powered Change Summarization

**What it does:**
- LLM summarizes what changed in sources
- Natural language explanation of changes
- Impact analysis (breaking changes, new features, etc.)
- Automated changelog generation

**Why deferred:**
MVP focuses on detection and regeneration. Change summarization is nice-to-have for communication but not essential for core workflow.

**Reconsider when:**
- Need to communicate changes to stakeholders
- Changelog generation becomes tedious
- Impact analysis would improve decision-making

**Effort:** 1-2 weeks  
**Complexity:** Medium  
**Theme:** ai-features, changelog, communication

---

### Plugin System for Custom Generators

**What it does:**
- Plugin architecture for custom doc generators
- Hook system for pre/post processing
- Custom outline formats
- Custom LLM providers
- Community plugin marketplace

**Why deferred:**
MVP uses built-in generation logic. Plugins add architectural complexity before validating core value. Better to learn patterns before enabling customization.

**Reconsider when:**
- Users need custom generation logic
- Multiple doc types require different approaches
- Community wants to extend functionality
- Plugin ecosystem would add value

**Effort:** 3-4 weeks  
**Complexity:** Very High  
**Theme:** extensibility, plugins, architecture

---

## Summary

**Total deferred features:** 14

**By complexity:**
- Low: 0
- Medium: 4
- Medium-High: 3
- High: 6
- Very High: 1

**By phase:**
- Phase 2 (High Priority): 3 features
- Phase 3 (Medium Priority): 5 features
- Future/Parking Lot: 6 features

**Common themes:**
- Quality assurance & testing: 3 features
- UX & interaction improvements: 4 features
- Automation & integration: 3 features
- Extensibility & plugins: 3 features
- Optimization & performance: 3 features

**Key insight:** Most deferred features are optimization and polish on top of core MVP. The MVP delivers the essential value; these features improve ergonomics, scale, and flexibility.

---

**All deferred features will be tracked in beads via beads-expert as priority 4 (backlog) issues.**

Query these features:
```bash
bd list --label origin-2025-12-12-doc-gen-tool
bd list --label phase-2  # High priority deferred features
```
