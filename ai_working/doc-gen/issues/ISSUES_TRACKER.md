# Issues Tracker - doc-gen

## Open Issues

### ISSUE-001: Add unit tests for document generation
- **Status**: Open
- **Priority**: Medium
- **Type**: Technical Debt
- **Assigned to**: Unassigned
- **Created**: 2025-12-12
- **Sprint**: Deferred from Sprint 3

**Description**: Document generation module (generation.py) was implemented without comprehensive unit tests. This was a pragmatic tradeoff to deliver Sprint 3 quickly, but tests should be added for maintainability.

**Scope**:
- Unit tests for DocumentGenerator class
- Tests for prompt construction (_create_prompt)
- Tests for markdown validation (_validate_markdown)
- Tests for frontmatter generation (_add_frontmatter)
- Tests for file extraction (_extract_mentioned_files)

**Acceptance Criteria**:
- [ ] >80% test coverage for generation.py
- [ ] All DocumentGenerator methods have unit tests
- [ ] Integration test for full document generation flow

**Related Files**:
- `tools/doc-gen/src/doc_gen/generation.py`
- `tools/doc-gen/tests/test_generation.py` (to be created)

**Sprint Assignment**: Sprint 4 or later (technical debt cleanup)

---

### ISSUE-002: Improve document generation prompt strategy
- **Status**: Open
- **Priority**: Medium
- **Type**: Enhancement
- **Assigned to**: Unassigned
- **Created**: 2025-12-12
- **Sprint**: Deferred from Sprint 3

**Description**: Current outline → document generation strategy uses basic prompts. Quality is acceptable for MVP but could be improved with better prompt engineering. Debug logs now available for iteration.

**Current Approach**:
- Single LLM call with full outline + all mentioned source files
- Basic system prompt + structured user prompt
- Section-level prompts from outline guide content generation

**Potential Improvements**:
- Iterative section-by-section generation (better quality per section)
- Better use of section "prompt" fields for targeted generation
- Improved examples in system prompt
- Better handling of code examples
- Chunk large source files more intelligently (currently truncates at 8000 chars)

**How to Investigate**:
Use debug mode to view current prompts:
```bash
doc-gen --debug generate-doc docs/test-example.md
# Review log file in .doc-gen/debug/
```

**Acceptance Criteria**:
- [ ] Document quality improved (subjective review)
- [ ] Better code example integration
- [ ] Improved clarity of explanations
- [ ] Better section structure

**Related Files**:
- `tools/doc-gen/src/doc_gen/generation.py` (lines 80-157: prompt construction)

**Sprint Assignment**: Post-MVP or when quality issues are reported

---

### ISSUE-003: Add .coverage to .gitignore
- **Status**: Open
- **Priority**: Low
- **Type**: Cleanup
- **Assigned to**: Unassigned
- **Created**: 2025-12-12
- **Sprint**: N/A (quick fix)

**Description**: Test coverage artifact `.coverage` keeps appearing as modified in git status. Should be added to .gitignore to prevent accidental commits.

**Acceptance Criteria**:
- [ ] Add `tools/doc-gen/.coverage` to .gitignore
- [ ] Add `*.coverage` pattern to .gitignore
- [ ] Verify `git status` no longer shows .coverage

**Related Files**:
- `.gitignore`
- `tools/doc-gen/.coverage`

**Sprint Assignment**: N/A (can be done anytime)

---

## Completed Issues

(No completed issues yet - this is the first tracker)

---

## Deferred Features (from Convergence)

These are features deferred during convergence that may become issues later:

### From Sprint 3 Planning
- ❌ **Configurable temperature/model per document** - Deferred to v0.2.0
- ❌ **Custom frontmatter fields** - Deferred to v0.2.0
- ❌ **Side-by-side comparison with previous version** - Sprint 5 will add review workflow
- ❌ **Multiple LLM provider support per document** - v0.2.0
- ❌ **Incremental section regeneration** - v0.2.0 if needed

---

## How to Use This Tracker

**Adding New Issues**:
1. Use format: `ISSUE-XXX: Brief title`
2. Include all required fields (Status, Priority, Type, etc.)
3. Add acceptance criteria checklist
4. Link to related files

**Updating Issues**:
1. Change Status when work begins or completes
2. Update Sprint Assignment when scheduled
3. Add resolution notes when closing

**Issue Status Values**:
- **Open** - Not yet started
- **In Progress** - Currently being worked on
- **Blocked** - Waiting on dependency
- **Resolved** - Completed and verified

**Priority Values**:
- **Critical** - Blocking progress or causing failures
- **High** - Important for quality or user experience
- **Medium** - Should be done but not urgent
- **Low** - Nice to have, cleanup, minor improvements

**Type Values**:
- **Bug** - Something broken or not working as intended
- **Enhancement** - Improvement to existing functionality
- **Feature** - New functionality
- **Technical Debt** - Code quality, tests, refactoring
- **Cleanup** - Housekeeping, organization, minor fixes

---

**Last Updated**: 2025-12-12 (Sprint 3 completion)
