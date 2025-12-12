# Sprint Plan: doc-gen Tool v0.1.0 (REVISED)

**Project:** doc-gen - Multi-Repository Documentation Generation Tool  
**Version:** v0.1.0 (Initial MVP)  
**Timeline:** 6-7 weeks (REVISED from 3 weeks)  
**Status:** Ready for Implementation  
**Revision Date:** 2025-12-12

---

## 🚨 Why This Revision?

The original 3-sprint plan **underestimated LLM integration complexity**:

### Critical Issues Identified:
1. **LLM Integration Underestimated**: Outline and document generation requires:
   - Prompt engineering (iteration to get quality output)
   - JSON parsing from LLM responses (validation, error handling)
   - Error handling (timeouts, rate limits, malformed JSON)
   - Token counting and cost tracking
   - **Minimum 1-1.5 weeks per LLM integration**, not 2 days

2. **Config Management Missing**: `.doc-gen/config.yaml` for API keys needed BEFORE first LLM call

3. **Multi-Repo Pattern Matching**: Gitignore-style patterns across repos has edge cases needing thorough testing

4. **Prompt Iteration Time**: Real usage requires tuning prompts based on output quality

### New Reality: **6 sprints, 6-7 weeks**

---

## 🎯 MVP Scope

**The ONE Problem:**  
Documentation drifts from reality as code evolves across 20+ repositories, with no systematic way to detect changes or regenerate affected documentation.

**The Solution:**  
A CLI tool that manages multi-repo sources, generates documentation through a two-phase pipeline (outline → document), tracks changes via git commit hashes, and provides a staging workflow for review before promotion.

---

## 📅 Timeline Overview (REVISED)

| Sprint | Duration | Name | Goal |
|--------|----------|------|------|
| Sprint 1 | 1 week | **Core Infrastructure & Config** | Project setup, CLI, metadata, single-repo cloning, config management |
| Sprint 2 | 1-1.5 weeks | **Outline Generation (LLM 1st)** | First LLM integration with prompt engineering |
| Sprint 3 | 1 week | **Document Generation (LLM 2nd)** | Second LLM integration, staging workflow |
| Sprint 4 | 1-1.5 weeks | **Multi-Repo & Validation** | Scale to 20+ repos, pattern matching |
| Sprint 5 | 1 week | **Change Detection & Review** | Detect stale docs, review workflow |
| Sprint 6 | 1 week | **Orchestration & Polish** | Batch operations, error handling polish |
| **Total** | **6.5-7.5 weeks** | | **Production-ready MVP** |

---

## 🚀 Value Progression

### Sprint 1: Core Infrastructure & Config
**User Value:** "I have a working CLI tool with proper config management"

- ✅ Working CLI framework (Click)
- ✅ Metadata management (sources.yaml, outline.json)
- ✅ Single-repo cloning (proof it works)
- ✅ Config management (.doc-gen/config.yaml for API keys)
- ✅ Foundation for everything else
- ~600 LOC + tests

### Sprint 2: Outline Generation (First LLM Integration)
**User Value:** "I can generate structured outlines from source code with LLM"

- ✅ LLM client integration (OpenAI initially)
- ✅ Prompt engineering for outline generation (expect iteration!)
- ✅ JSON schema validation
- ✅ Error handling (timeouts, rate limits, malformed JSON)
- ✅ Token counting and cost tracking
- ✅ Commit hash embedding in outline
- ~500 LOC + tests
- **This WILL take time - first LLM integration is hard**

### Sprint 3: Document Generation (Second LLM Integration)
**User Value:** "I have end-to-end single-repo pipeline working"

- ✅ LLM integration for document generation
- ✅ Reuse patterns from Sprint 2 (faster now)
- ✅ Prompt engineering for doc quality
- ✅ Staging workflow
- ✅ End-to-end pipeline validated
- ~450 LOC + tests

### Sprint 4: Multi-Repo & Validation
**User Value:** "I can manage documentation from 20+ repositories with validation"

- ✅ Multi-repo source specifications
- ✅ Gitignore-style pattern matching (pathspec library)
- ✅ Source validation command (preview files)
- ✅ Extend outline/doc generation for multi-repo
- ✅ Test with 3+ repos
- ~550 LOC + tests

### Sprint 5: Change Detection & Review
**User Value:** "I know which docs are stale and can safely review changes"

- ✅ Change detection (commit hash comparison)
- ✅ Check changes command (single + all docs)
- ✅ Review command (show diffs)
- ✅ Promote command (with backups)
- ✅ These features work together naturally
- ~500 LOC + tests

### Sprint 6: Orchestration & Polish
**User Value:** "Production-ready tool that replaces manual scripts"

- ✅ Regenerate-changed command (orchestration)
- ✅ Error handling polish across all commands
- ✅ Comprehensive documentation
- ✅ Final testing and bug fixes
- ~450 LOC + tests

---

## 🏗️ Architecture Overview

### Directory Structure
```
amplifier-docs/
├── docs/                          # LIVE docs
│   └── modules/providers/openai.md
│
├── .doc-gen/                      # Tool metadata
│   ├── config.yaml                # Global config (API keys, model)
│   └── metadata/
│       └── docs/modules/providers/openai/
│           ├── sources.yaml       # Source spec
│           ├── outline.json       # Generated outline + hashes
│           └── staging/
│               └── openai.md      # Staged doc

└── tools/doc-gen/                 # The tool
    ├── pyproject.toml
    ├── src/doc_gen/
    │   ├── cli.py
    │   ├── config.py              # NEW: Config management
    │   ├── sources.py
    │   ├── repos.py
    │   ├── outline.py
    │   ├── generation.py
    │   ├── change_detection.py
    │   └── metadata.py
    └── tests/
```

### Key Technical Decisions

1. **Python 3.11+** with Click for CLI
2. **Config-first**: `.doc-gen/config.yaml` for API keys before LLM calls
3. **YAML** for source specifications (human-editable)
4. **JSON** for outlines (with embedded commit hashes)
5. **Tempfile** for repo cloning (cross-platform, auto-cleanup)
6. **Git commit hashes** for change detection
7. **Staging-first** - all generations require explicit promotion
8. **Two-phase** - outline generation separate from doc generation
9. **TDD throughout** - test-first development for all features

---

## 🎯 8 CLI Commands (MVP)

| Command | Sprint | Purpose |
|---------|--------|---------|
| `init <doc-path>` | 1 | Initialize sources.yaml template |
| `validate-sources <doc-path>` | 4 | Validate source spec (show matched files) |
| `generate-outline <doc-path>` | 2 | Generate outline from sources |
| `generate-doc <doc-path>` | 3 | Generate document from outline |
| `review <doc-path>` | 5 | Show diff between staging and live |
| `promote <doc-path>` | 5 | Copy staging doc to live |
| `check-changes [doc-path]` | 5 | Detect which docs have stale sources |
| `regenerate-changed` | 6 | Regenerate all changed docs |

---

## 📦 Dependencies

### External Tools
- **Git** - Clone repos, fetch commit hashes
- **LLM API** - OpenAI or Anthropic for generation

### Python Libraries
- `click` - CLI framework
- `pyyaml` - YAML parsing
- `gitpython` - Git operations
- `pathspec` - Gitignore pattern matching (Sprint 4)
- `openai` or `anthropic` - LLM APIs
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `python-dotenv` - Environment variable management

---

## ✅ Success Criteria

### Functional Success
- [ ] All 8 CLI commands implemented and tested
- [ ] Config management working (API keys, model selection)
- [ ] Can generate outlines from single repo (Sprint 2)
- [ ] Can generate documents from outlines (Sprint 3)
- [ ] Can manage sources from 20+ repositories (Sprint 4)
- [ ] Can validate source specs before generation (Sprint 4)
- [ ] Can detect source changes via commit hash comparison (Sprint 5)
- [ ] Can review and promote staged docs safely (Sprint 5)
- [ ] Can regenerate all changed docs with single command (Sprint 6)

### Quality Success
- [ ] Test coverage >80% for new code (TDD throughout)
- [ ] CLI help text is clear and discoverable
- [ ] Error messages guide users to fix issues
- [ ] LLM prompts produce quality output
- [ ] Generated docs are reviewable (not auto-promoted)
- [ ] Change detection accurately identifies stale docs

### Adoption Success
- [ ] Documentation maintainer uses it instead of ad-hoc scripts
- [ ] At least 5 docs successfully generated and promoted
- [ ] Change detection catches real source updates
- [ ] User reports "this is better than manual scripts"

---

## 🚫 Explicitly Deferred to v0.2.0

These are valuable but NOT part of v0.1.0 MVP:

- ❌ **Evaluation harness** for prompt testing
  - Why: Can iterate on prompts manually in MVP
  - Reconsider: When we have >10 docs and need systematic prompt optimization

- ❌ **Smart change detection** (line count thresholds, significance filtering)
  - Why: Simple commit hash comparison is sufficient for MVP
  - Reconsider: If we get false positives (e.g., formatting-only changes)

- ❌ **GitHub Actions automation** for scheduled regeneration
  - Why: Manual regeneration is fine for MVP validation
  - Reconsider: After MVP proves valuable and we want automation

- ❌ **Interactive source editor** (TUI for editing sources.yaml)
  - Why: Manual YAML editing works for MVP
  - Reconsider: If users struggle with YAML syntax

- ❌ **Web UI** for reviewing diffs
  - Why: CLI diff display is sufficient for MVP
  - Reconsider: If reviewing in terminal is painful for users

- ❌ **Template system** for doc structure customization
  - Why: LLM generates structure automatically
  - Reconsider: If users need consistent doc structures across projects

- ❌ **Parallel regeneration** for batch operations
  - Why: Sequential is simpler and sufficient for MVP
  - Reconsider: If batch operations are too slow

---

## 📋 Implementation Notes

### Key Principle: One Hard Thing Per Sprint

**Original mistake**: Combined LLM integration + multi-repo in one sprint  
**New approach**: Separate LLM work (Sprints 2-3) from multi-repo work (Sprint 4)

### TDD Throughout

**Every sprint follows red-green-refactor:**
1. 🔴 Write failing test first
2. 🟢 Write minimal code to pass
3. 🔵 Refactor for quality
4. ✅ Commit with green tests

Target: >80% test coverage for all new code.

### Prompt Engineering Time

**Sprint 2 and 3 explicitly include prompt iteration time:**
- Days 1-2: Basic LLM call and JSON parsing
- Days 3-4: Prompt engineering (iterate on quality)
- Days 5-6: Error handling (timeouts, retries, malformed responses)
- Day 7: Integration testing and cost tracking

This is realistic for first-time LLM integration.

### Config-First Approach

**Sprint 1 includes config management:**
- `.doc-gen/config.yaml` for global settings
- API keys loaded from config or environment variables
- Model selection configurable
- Prevents hardcoded credentials

### Incremental Error Handling

**Build error handling as you go, not at the end:**
- Sprint 1: Basic error display
- Sprint 2: LLM-specific error handling (timeouts, rate limits)
- Sprint 3: Document generation errors
- Sprint 4: Multi-repo validation errors
- Sprint 5: Change detection edge cases
- Sprint 6: Polish and comprehensive error messages

---

## 🔄 Cross-Platform Considerations

- Use `tempfile.TemporaryDirectory()` for repo clones
- Use `pathlib.Path` for all file operations
- Test on Linux, macOS, and Windows
- Use forward slashes in YAML patterns (Git convention)

---

## 📚 Sprint Documents

- [Sprint 1: Core Infrastructure & Config](./SPRINT_01_CORE_INFRASTRUCTURE.md) - Setup, CLI, metadata, config (1 week)
- [Sprint 2: Outline Generation](./SPRINT_02_OUTLINE_GENERATION.md) - First LLM integration (1-1.5 weeks)
- [Sprint 3: Document Generation](./SPRINT_03_DOCUMENT_GENERATION.md) - Second LLM integration (1 week)
- [Sprint 4: Multi-Repo & Validation](./SPRINT_04_MULTI_REPO_VALIDATION.md) - Scale to 20+ repos (1-1.5 weeks)
- [Sprint 5: Change Detection & Review](./SPRINT_05_CHANGE_DETECTION_REVIEW.md) - Detect stale, review workflow (1 week)
- [Sprint 6: Orchestration & Polish](./SPRINT_06_ORCHESTRATION_POLISH.md) - Batch ops, final polish (1 week)

---

## 🎯 Sprint-by-Sprint Focus

### Sprint 1: Foundation
**Hard thing:** Project structure and metadata management  
**Value:** Working CLI you can install

### Sprint 2: First LLM Integration
**Hard thing:** Prompt engineering for outline generation  
**Value:** LLM generates structured outlines (single repo)

### Sprint 3: Second LLM Integration
**Hard thing:** Document quality from outlines  
**Value:** End-to-end pipeline working (single repo)

### Sprint 4: Multi-Repo Scaling
**Hard thing:** Pattern matching across 20+ repos  
**Value:** Can manage docs from multiple sources

### Sprint 5: Change Detection + Safety
**Hard thing:** Commit hash tracking and diff review  
**Value:** Know what's stale, review before promoting

### Sprint 6: Production Ready
**Hard thing:** Orchestration and error handling polish  
**Value:** One-command batch regeneration

---

## 🎉 Definition of Done (MVP Complete)

The MVP is complete when:

1. ✅ All 8 CLI commands are implemented and tested
2. ✅ Config management working (no hardcoded API keys)
3. ✅ Can generate quality docs from 20+ repositories
4. ✅ Change detection tested with actual git history
5. ✅ Review workflow prevents bad promotions
6. ✅ Batch regeneration handles 5+ docs successfully
7. ✅ Documentation exists for each command (README + CLI help)
8. ✅ User (documentation maintainer) validates it solves their problem
9. ✅ Code reviewed for simplicity and maintainability
10. ✅ Test coverage >80%

---

## 🔮 Next Steps

1. **Review Sprint 1 document** - Understand core infrastructure deliverables
2. **Set up development environment** - Python 3.11+, dependencies, testing
3. **Start building!** - Follow Sprint 1 implementation order with TDD
4. **Ship Sprint 1** - Get foundation working (1 week)
5. **Iterate through sprints** - Each sprint builds on previous

---

**Timeline Reality Check:**
- Original plan: 3 weeks (3 sprints)
- Revised plan: 6.5-7.5 weeks (6 sprints)
- **This is still aggressive** - allows for learning and iteration
- Buffer time built into each sprint for prompt tuning and bug fixes

**Ready to start Sprint 1? Let's build this the right way! 🚀**
