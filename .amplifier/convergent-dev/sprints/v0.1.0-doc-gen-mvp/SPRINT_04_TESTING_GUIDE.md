# Sprint 4: Multi-Repository Support - Testing Guide

**Status:** Ready for User Testing  
**Date:** 2025-12-12  
**Version:** v0.1.0 (Sprint 4/6)

---

## 🚀 Sprint 4: Ready for User Testing

### ✅ What's New and Working

**Sprint 4 delivers multi-repository support** - scale from 1 to 20+ repositories!

---

## 📋 Features Ready to Test

### 1. **Multi-Repo Source Specifications**

Create a `sources.yaml` with multiple repositories:

```yaml
repositories:
  - url: https://github.com/microsoft/amplifier.git
    include:
      - "src/**/*.py"
      - "README.md"
    exclude:
      - "**/__pycache__/**"
      - "**/*.pyc"
  
  - url: https://github.com/another-org/another-repo.git
    include:
      - "**/*.ts"
      - "**/*.tsx"
  
  - url: https://github.com/third-org/docs-repo.git
    include:
      - "docs/**/*.md"

metadata:
  purpose: "Document the combined functionality from multiple repositories"
```

**Pattern Matching Features:**
- ✅ Gitignore-style patterns (`**`, `*`, `?`, `[abc]`)
- ✅ Include patterns (required)
- ✅ Exclude patterns (optional)
- ✅ Per-repository pattern control

---

### 2. **NEW: validate-sources Command** ⭐

**Validate your sources BEFORE expensive LLM calls:**

```bash
doc-gen validate-sources docs/example.md
```

**What it shows:**
- ✓ Which files matched from each repo
- ✓ File counts and line counts per repo
- ✓ Token estimates
- ✓ **Cost estimates** (in USD, GPT-4 pricing)
- ✓ Preview of matched files (first 10 per repo)

**Example output:**
```
Loading sources for docs/example.md...
✓ Found 3 repository(ies)

Validating repositories...

✓ amplifier-kernel
  URL: https://github.com/microsoft/amplifier.git
  Matched files: 47
  Sample files:
    - src/kernel.py (234 lines)
    - src/events.py (189 lines)
    - src/providers.py (156 lines)
    ... and 44 more files
  Total lines: 5,432
  Estimated tokens: ~67,900

✓ amplifier-docs
  URL: https://github.com/microsoft/amplifier-docs.git
  Matched files: 23
  ...

============================================================
Summary:
  Repositories: 3/3 successful
  Total files: 127
  Total lines: 15,234
  Estimated tokens: ~190,425
  Estimated cost: ~$5.71 (GPT-4 pricing)

✓ All sources valid!

Next steps:
  doc-gen generate-outline docs/example.md
```

---

### 3. **Multi-Repo Outline Generation**

```bash
doc-gen generate-outline docs/example.md
```

**Now handles multiple repositories:**
- Clones all repositories specified in sources.yaml
- Applies pattern matching per repo
- Combines files from all repos
- File keys prefixed with repo name: `repo-name/path/to/file.py`
- All existing Sprint 2 features work (debug mode, etc.)

---

### 4. **Multi-Repo Document Generation**

```bash
doc-gen generate-doc docs/example.md
```

**Now handles multiple repositories:**
- Works with multi-repo outlines
- Clones all repositories mentioned in outline
- Resolves file references to correct repo
- Backward compatible with single-repo outlines

---

## 🧪 Test Scenarios

### **Scenario 1: Single Repository (Backward Compatibility)**

Test that Sprint 1-3 workflows still work:

```bash
# Should work exactly as before
doc-gen init docs/single-repo.md
# Edit sources.yaml with ONE repository
doc-gen validate-sources docs/single-repo.md
doc-gen generate-outline docs/single-repo.md
doc-gen generate-doc docs/single-repo.md
```

**Expected:** Everything works as in Sprint 3

---

### **Scenario 2: Two Repositories**

Test basic multi-repo functionality:

```bash
doc-gen init docs/multi-repo.md
# Edit sources.yaml with TWO repositories
doc-gen validate-sources docs/multi-repo.md
```

**Expected:**
- Shows files from both repos
- Separate counts per repo
- Combined totals in summary
- Cost estimate for combined files

Then continue:
```bash
doc-gen generate-outline docs/multi-repo.md
doc-gen generate-doc docs/multi-repo.md
```

**Expected:**
- Outline includes files from both repos (prefixed with repo name)
- Document generation finds files in correct repos

---

### **Scenario 3: Pattern Matching Validation**

Test gitignore-style patterns:

```yaml
repositories:
  - url: https://github.com/test/repo.git
    include:
      - "**/*.py"      # All Python files recursively
      - "src/**/*.ts"  # TypeScript in src/
      - "README.md"    # Specific file
    exclude:
      - "**/tests/**"  # Exclude test directories
      - "**/__pycache__/**"
```

```bash
doc-gen validate-sources docs/pattern-test.md
```

**Expected:**
- Only matching files shown
- Excluded files NOT shown
- Pattern matching works as expected

---

### **Scenario 4: Cost Estimation**

Test with a large repository:

```bash
doc-gen validate-sources docs/large-repo.md
```

**Expected:**
- Accurate file/line counts
- Reasonable token estimate
- Cost estimate helps decide if generation is worth it

---

### **Scenario 5: Error Handling**

Test invalid configurations:

```bash
# Invalid URL
doc-gen validate-sources docs/bad-url.md
# Expected: Clear error message

# No include patterns
doc-gen validate-sources docs/no-patterns.md
# Expected: Clear error message

# Missing sources.yaml
doc-gen validate-sources docs/not-initialized.md
# Expected: Helpful error with next steps
```

---

## ⚠️ Known Limitations (Tracked in Beads)

**4 edge case bugs discovered by testing** (tracked, not blocking):

1. **SSH URLs not supported** (P2)
   - `git@github.com:owner/repo.git` format rejected
   - Workaround: Use `https://` URLs
   - Bug ID: `momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-ao4`
   - Query: `bd show momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-ao4`

2. **Malformed YAML** (P3)
   - Shows technical stack trace instead of friendly error
   - Bug ID: `momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-o9u`
   - Query: `bd show momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-o9u`

3. **Empty YAML file** (P3)
   - Crashes instead of helpful error
   - Bug ID: `momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-ixo`
   - Query: `bd show momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-ixo`

4. **Whitespace-only YAML** (P3)
   - Same as #3
   - Bug ID: `momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-3hn`
   - Query: `bd show momuno_amplifier-docs.doc-gen-tool_convergent-dev-collection-3hn`

**Query all Sprint 4 bugs:**
```bash
bd list --label from-sprint-4-testing --type bug --status open
```

**These are edge cases and won't affect normal usage.**

---

## 📊 What's Been Tested

**Test Coverage:**
- ✅ 73 comprehensive tests
- ✅ 100% coverage for sources.py
- ✅ 100% coverage for validation.py
- ✅ Pattern matching (all gitignore patterns)
- ✅ Multi-repo parsing
- ✅ Validation logic
- ✅ Error handling

**Test Files:**
- `tools/doc-gen/tests/test_sources.py` (46 tests)
- `tools/doc-gen/tests/test_validation.py` (28 tests)

---

## 🎯 Recommended Test Flow

1. **Start Simple** - Single repo validation
2. **Add Second Repo** - Test multi-repo validation
3. **Generate Outline** - Test multi-repo outline generation
4. **Generate Doc** - Test multi-repo document generation
5. **Try Debug Mode** - `doc-gen --debug generate-outline docs/example.md`

---

## 📝 Quick Reference: New Commands

### Initialize sources
```bash
doc-gen init docs/example.md
```

### Validate sources (NEW in Sprint 4)
```bash
doc-gen validate-sources docs/example.md
```

### Generate outline (multi-repo in Sprint 4)
```bash
doc-gen generate-outline docs/example.md
```

### Generate document (multi-repo in Sprint 4)
```bash
doc-gen generate-doc docs/example.md
```

### Debug mode (any command)
```bash
doc-gen --debug generate-outline docs/example.md
# Creates log file in .doc-gen/debug/
```

---

## 🔍 Debugging Tips

### View validation details
```bash
doc-gen validate-sources docs/example.md
# Shows exactly what files will be used
```

### Check pattern matching
Edit sources.yaml and re-run validate to see what matches:
```bash
doc-gen validate-sources docs/example.md
```

### View full LLM prompts
```bash
doc-gen --debug generate-outline docs/example.md
# Log file: .doc-gen/debug/generate-outline_YYYYMMDD_HHMMSS.log
```

### Check outline contents
```bash
cat .doc-gen/metadata/docs/example/outline.json | jq '.sections[].sources'
# See which files were referenced
```

---

## 🎉 Success Criteria

Sprint 4 is successful if:
- ✅ Can validate sources from multiple repos
- ✅ Can generate outline from multiple repos
- ✅ Can generate document from multiple repos
- ✅ Pattern matching works as expected
- ✅ Cost estimates help decision-making
- ✅ Single-repo workflows still work (backward compatibility)

---

## 📚 Additional Resources

- Sprint 4 Plan: `.amplifier/convergent-dev/sprints/v0.1.0-doc-gen-mvp/SPRINT_04_MULTI_REPO_VALIDATION.md`
- Sprint 4 Results: `.amplifier/convergent-dev/sprints/v0.1.0-doc-gen-mvp/SPRINT_04_RESULTS.md` (to be written)
- Test Files: `tools/doc-gen/tests/test_sources.py`, `test_validation.py`
- Bug Tracking: Query beads with `bd list --label from-sprint-4-testing`

---

**Sprint 4 Status:** ✅ **Feature complete, tested, ready for user validation!**

The tool now scales from 1 to 20+ repositories seamlessly! 🚀
