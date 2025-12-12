# Convergence Complete: doc-gen Tool

**Date:** 2025-12-12  
**Project:** doc-gen-tool  
**Repository:** amplifier-docs/tools/doc-gen/  
**Convergence Phase:** COMPLETE ✅

---

## Executive Summary

Successfully converged from broad exploration to focused MVP scope for the **doc-gen** documentation generation tool. The tool will automate documentation generation from 20+ GitHub repositories with systematic change detection and review workflows.

**Core Value Proposition:**  
*Generate and maintain documentation from multi-repo sources with automated change detection, replacing ad-hoc scripts with a systematic CLI tool.*

---

## The Four Phases

### Phase 1: DIVERGE ✅

**Objective:** Explore the problem space without constraints

**Activities Completed:**
- Reviewed existing ad-hoc Python scripts (`regenerate_module_docs.py`, `regenerate_from_outlines.py`)
- Analyzed doc-evergreen repository patterns
- Prototyped key concepts (multi-repo sourcing, two-phase generation, change detection)
- Explored workflow patterns (staging → review → promote)
- Investigated sourcing patterns (include/exclude, multiple repos)
- Considered various enhancement ideas (evaluation harness, GitHub Actions, smart detection)

**Key Insights:**
- Two-phase generation (outline → document) is fundamental, not optional
- Change detection via commit hashes is sufficient for MVP
- Cross-platform temp directory cloning avoids disk bloat
- Hand-editable metadata enables power user workflows
- Staging workflow prevents accidental publication of bad generations

**Artifacts:** Background research, prototype scripts, design discussions

---

### Phase 2: CAPTURE ✅

**Objective:** Organize and structure all explored ideas

**Activities Completed:**
- Documented directory structure design
- Specified 8 CLI commands with clear responsibilities
- Defined metadata format (sources.yaml, outline.json, staging/)
- Outlined key technical decisions (temp cloning, include OR exclude, commit hash tracking)
- Listed potential features beyond MVP (14 total deferred features)
- Established clear boundaries (Git-only, current version docs, CLI-first)

**Key Design Decisions:**
1. **Two-Phase Separation:** Outline generation (expensive) vs doc generation (cheaper)
2. **Multi-Repo First:** 20+ repositories is core requirement, not edge case
3. **Safety First:** All generations go to staging, require explicit promotion
4. **Hand-Edit Friendly:** outline.json can be manually edited before doc generation
5. **Simple Change Detection:** Commit hash comparison (not semantic analysis)

**Artifacts:** Directory structure, CLI command specifications, technical decisions

---

### Phase 3: CONVERGE ✅

**Objective:** Define the minimum viable product scope

**Decisions Made:**

**✅ IN SCOPE (4 Core Features):**

1. **Multi-Repo Source Management**
   - Commands: `init`, `validate-sources`
   - Rationale: Foundation - can't generate docs without specifying sources
   - Validation prevents wasted LLM calls on broken specs

2. **Two-Phase Generation Pipeline**
   - Commands: `generate-outline`, `generate-doc`
   - Rationale: Separates expensive outline generation from cheaper doc generation
   - Enables iteration and hand-editing of outlines

3. **Staging & Promotion Workflow**
   - Commands: `review`, `promote`
   - Rationale: Safety mechanism - prevents unreviewed AI content from reaching live site
   - Essential for quality control

4. **Change Detection & Orchestration**
   - Commands: `check-changes`, `regenerate-changed`
   - Rationale: Solves the core problem - systematic detection of stale docs
   - This is the "killer feature" that makes the tool valuable

**❌ OUT OF SCOPE (14 Deferred Features):**
- Evaluation harness for prompt testing
- Smart change detection (line count thresholds)
- GitHub Actions automation
- Advanced batch operations
- Interactive source editor
- Web UI for review
- Template system
- Multi-source type support (beyond Git)
- Incremental outline updates
- Documentation quality metrics
- Multi-language documentation
- Version-specific documentation
- AI-powered change summarization
- Plugin system for custom generators

**Success Criteria:**
- 8 CLI commands implemented and tested
- Successfully generate and promote 5+ real docs from amplifier-docs
- Change detection validated with actual git history
- User confirms it's better than ad-hoc scripts
- Documentation exists for each command

**Timeline:** 3-4 weeks (3 sprints)

**Artifacts:** `FEATURE_SCOPE.md` (this directory)

---

### Phase 4: DEFER ✅

**Objective:** Preserve deferred ideas for future consideration

**Features Deferred:** 14 total

**By Priority:**
- **Phase 2 (High Priority):** 3 features
  - Evaluation harness for prompt testing
  - Smart change detection
  - GitHub Actions automation
  
- **Phase 3 (Medium Priority):** 5 features
  - Advanced batch operations
  - Interactive source editor
  - Web UI for review and promotion
  - Template system for doc structure
  - Multi-source type support (beyond Git)
  - Incremental outline updates
  
- **Future/Parking Lot:** 6 features
  - Documentation quality metrics
  - Multi-language documentation
  - Version-specific documentation
  - AI-powered change summarization
  - Plugin system for custom generators

**By Complexity:**
- Low: 0 features
- Medium: 4 features
- Medium-High: 3 features
- High: 6 features
- Very High: 1 feature

**By Theme:**
- Quality assurance & testing: 3 features
- UX & interaction improvements: 4 features
- Automation & integration: 3 features
- Extensibility & plugins: 3 features
- Optimization & performance: 3 features

**Rationale for Deferral:**
Most deferred features are optimization and polish on top of core MVP. The MVP delivers the essential value; these features improve ergonomics, scale, and flexibility. Better to validate core value first, then enhance based on real usage patterns.

**Tracking:** All deferred features tracked in beads with labels:
- `origin-2025-12-12-doc-gen-tool`
- `phase-2`, `phase-3`, or `future`
- Individual theme labels
- Priority 4 (backlog)

**Artifacts:** `DEFERRED_FEATURES.md` (this directory), beads issues

---

## Statistics

### Feature Exploration
- **Total Ideas Explored:** ~20+ (including variations and sub-features)
- **Converged to MVP:** 4 core features (8 CLI commands)
- **Deferred for Later:** 14 features
- **Convergence Ratio:** 22% immediate, 78% deferred

### Complexity Distribution (Deferred Features)
- Low: 0 (0%)
- Medium: 4 (29%)
- Medium-High: 3 (21%)
- High: 6 (43%)
- Very High: 1 (7%)

### Timeline
- **MVP Estimate:** 3-4 weeks (3 sprints)
- **Phase 2 Features:** Additional 3-5 weeks
- **Phase 3 Features:** Additional 8-11 weeks
- **Total Future Work:** 11-16 weeks if all features built

### Effort Distribution (Deferred Features)
- 1 week: 2 features
- 1-2 weeks: 4 features
- 2 weeks: 3 features
- 2-3 weeks: 4 features
- 3-4 weeks: 2 features

**Key Insight:** Deferred work is 3-4x larger than MVP, confirming we've successfully identified the minimum viable scope.

---

## Files Created

All convergence artifacts are located in:  
`ai_working/amplifier-docs/convergence/2025-12-12-doc-gen-tool/`

### Core Documentation

1. **FEATURE_SCOPE.md** (10,892 bytes)
   - The ONE problem statement
   - MVP feature scope (4 features)
   - Success criteria
   - Timeline estimate (3-4 weeks)
   - Architecture overview
   - Definition of done

2. **DEFERRED_FEATURES.md** (14,202 bytes)
   - 14 deferred features documented
   - Organized by phase (2, 3, future)
   - Each feature includes:
     - Description and functionality
     - Why deferred
     - Reconsider criteria
     - Effort estimate
     - Complexity rating
     - Theme tags

3. **CONVERGENCE_COMPLETE.md** (this file)
   - Summary of all 4 phases
   - Statistics and metrics
   - Files created
   - Next steps guidance

### Beads Tracking

All 14 deferred features tracked in beads with:
- Priority: 4 (backlog)
- Labels: `origin-2025-12-12-doc-gen-tool`, phase labels, theme labels
- Full descriptions and reconsideration criteria

---

## Key Architectural Decisions

### Directory Structure
```
amplifier-docs/
├── docs/                          # LIVE docs (mkdocs webapp)
├── .doc-gen/                      # Metadata and staging
│   ├── metadata/                  # Per-doc metadata
│   │   └── docs/[path]/[name]/
│   │       ├── sources.yaml       # Source specification
│   │       ├── outline.json       # Generated outline + commit hashes
│   │       └── staging/[name].md  # Staged document
│   └── config.yaml                # Global config
└── tools/doc-gen/                 # The tool (new)
    ├── pyproject.toml
    ├── src/doc_gen/
    │   ├── cli.py                 # Click CLI
    │   ├── sources.py             # Source validation
    │   ├── repos.py               # Repository cloning
    │   ├── outline.py             # Outline generation
    │   ├── generation.py          # Doc generation
    │   ├── change_detection.py    # Commit hash comparison
    │   └── metadata.py            # Metadata management
    └── tests/
```

### Technical Decisions

1. **Repository Cloning:** Temp directory by default (cross-platform, no disk bloat)
2. **Source Specification:** Include OR exclude patterns (not both - simpler)
3. **Outline Format:** JSON with embedded commit hashes and full repo URLs
4. **Two-Phase Separation:** Essential for cost efficiency and iteration
5. **Hand-Editable Metadata:** Power users can manually edit outline.json
6. **Staging First:** All generations require explicit promotion

### Technology Stack
- **CLI Framework:** Click (Python)
- **YAML Parsing:** PyYAML
- **Git Operations:** GitPython
- **LLM Providers:** OpenAI / Anthropic
- **Testing:** pytest

---

## Next Steps

### Immediate (This Week)

1. **Sprint Planning** 🎯
   - Use `convergent-dev:sprint-planner` agent
   - Input: This convergence (FEATURE_SCOPE.md)
   - Output: 3 sprint plans with tasks, dependencies, acceptance criteria
   - Timeline: Today

2. **Review Convergence**
   - Validate feature scope with documentation maintainer
   - Confirm 4 core features solve the problem
   - Adjust if needed (rare - convergence should be stable)

### Sprint 1 (Week 1): Core Infrastructure

**Goal:** Foundation for all other work

Tasks (from sprint-planner):
- Project setup (pyproject.toml, directory structure)
- CLI framework with Click (8 command stubs)
- Source specification format (sources.yaml schema)
- Source validation logic
- Repository cloning utilities (temp directory management)

**Deliverable:** Can initialize and validate source specs

### Sprint 2 (Week 2-3): Generation Pipeline

**Goal:** Two-phase generation working end-to-end

Tasks (from sprint-planner):
- Outline generation from multi-repo sources
- LLM integration (OpenAI/Anthropic)
- Commit hash extraction and embedding
- Document generation from outlines
- Staging directory management
- Metadata persistence

**Deliverable:** Can generate outlines and docs to staging

### Sprint 3 (Week 3-4): Change Detection & Orchestration

**Goal:** Complete MVP with automation

Tasks (from sprint-planner):
- Change detection (commit hash comparison)
- Review workflow (diff display, editor integration)
- Promotion logic (staging → live)
- Regenerate-changed orchestration
- Error handling and logging
- Documentation (README, CLI help)

**Deliverable:** Full MVP ready for real-world use

### Post-MVP (Week 5+)

1. **Validation with Real Docs**
   - Generate 5+ docs from amplifier-docs
   - Test with actual git history
   - Collect user feedback

2. **Iteration**
   - Fix bugs discovered in real usage
   - Tune prompts based on quality feedback
   - Polish UX based on pain points

3. **Consider Phase 2 Features**
   - Evaluation harness (if quality issues emerge)
   - Smart change detection (if false positives are common)
   - GitHub Actions automation (if manual workflow is tedious)

---

## Convergence Quality Assessment

### Strengths ✅

1. **Clear Problem Definition**
   - Single, well-defined problem statement
   - Specific user persona identified
   - Current solution inadequacies understood

2. **Focused MVP**
   - 4 core features, not 10+
   - Each feature has clear rationale
   - Success criteria are measurable

3. **Comprehensive Deferral**
   - 14 features preserved for future
   - Each with reconsideration criteria
   - Organized by phase and priority

4. **Realistic Timeline**
   - 3-4 weeks is achievable
   - Broken into logical sprints
   - Buffer time included

5. **Architectural Clarity**
   - Directory structure defined
   - Technical decisions documented
   - Technology stack chosen

### Areas for Validation ⚠️

1. **LLM Cost Assumptions**
   - Assumption: Two-phase generation reduces costs
   - Validate: Track actual costs during MVP
   - Mitigation: Add evaluation harness if costs spiral

2. **Commit Hash Granularity**
   - Assumption: File-level commit hashes are sufficient
   - Validate: Test with real git histories
   - Mitigation: Add smart change detection if needed

3. **User Workflow Fit**
   - Assumption: CLI is sufficient for documentation maintainer
   - Validate: Observe actual usage patterns
   - Mitigation: Add Web UI if CLI proves insufficient

### Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Generated docs are low quality | Medium | High | Manual review workflow (in MVP) |
| Change detection has false positives | Medium | Medium | Smart detection (Phase 2) |
| LLM costs exceed budget | Low | High | Two-phase generation, prompt optimization |
| Multi-repo cloning is slow | Low | Medium | Parallel cloning (Phase 3) |
| Users prefer manual scripts | Low | High | Focus on discoverability and UX in MVP |

---

## Query Commands

### View All Deferred Features
```bash
bd list --label origin-2025-12-12-doc-gen-tool
```

### View by Phase
```bash
bd list --label phase-2    # High priority deferred features
bd list --label phase-3    # Medium priority deferred features
bd list --label future     # Low priority / parking lot
```

### View by Theme
```bash
bd list --label theme-quality-assurance
bd list --label theme-automation
bd list --label theme-ux
bd list --label theme-extensibility
bd list --label theme-optimization
```

### View by Complexity
```bash
bd list --label complexity-medium
bd list --label complexity-high
bd list --label complexity-very-high
```

---

## Conclusion

**Convergence Status:** ✅ COMPLETE

The doc-gen tool convergence successfully navigated from broad exploration (20+ ideas) to focused MVP (4 core features). All deferred features are preserved in beads for future consideration with clear reconsideration criteria.

**Ready for:** Sprint planning → Implementation → Validation

**Key Success Metric:** Documentation maintainer prefers doc-gen tool over ad-hoc Python scripts for managing documentation across 20+ repositories.

---

**Convergence Facilitator:** Amplifier (convergent-dev methodology)  
**Date Completed:** 2025-12-12  
**Next Milestone:** Sprint 1 kickoff (post sprint-planner)

---

## Appendix: Convergent-Dev Methodology Notes

This convergence followed the convergent-dev methodology:

**DIVERGE → CAPTURE → CONVERGE → DEFER**

### Methodology Strengths Observed

1. **Prevents Premature Narrowing**
   - Diverge phase explored 20+ ideas without judgment
   - Avoided "first idea is best idea" trap

2. **Preserves Context**
   - Deferred features documented with rationale
   - Future teams understand why decisions were made

3. **Forces Prioritization**
   - MVP limited to 4 features (22% of total)
   - Clear distinction between "must-have" and "nice-to-have"

4. **Enables Iteration**
   - Deferred features have reconsideration criteria
   - Not "no forever" but "not now"

5. **Maintains Velocity**
   - 3-4 week MVP is achievable
   - Avoids "analysis paralysis"

### Lessons Learned

1. **Design Work First**
   - Prototyping before convergence accelerated decision-making
   - Throwaway scripts validated key assumptions

2. **Timeline Realism**
   - Deferred work (11-16 weeks) is 3-4x MVP size
   - Confirms we identified minimum viable scope

3. **Rationale Documentation**
   - "Why essential?" for each MVP feature clarifies decisions
   - "Why deferred?" prevents re-litigation later

---

**End of Convergence Documentation**
