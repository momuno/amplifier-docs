# Sprint 2: Outline Generation (First LLM Integration)

**Duration:** 1-1.5 weeks  
**Goal:** Integrate LLM for outline generation with robust prompt engineering  
**Value Delivered:** Users can generate structured outlines from source code using LLM

---

## 🎯 Why This Sprint?

Sprint 2 is your **first LLM integration** - this is where things get real. You're not just calling an API; you're:

1. **Prompt engineering** - Crafting prompts that produce quality outlines (requires iteration!)
2. **JSON parsing** - Validating LLM responses match expected schema
3. **Error handling** - Dealing with timeouts, rate limits, malformed responses
4. **Token management** - Counting tokens and tracking costs
5. **Commit hash embedding** - Tracking sources for future change detection

By the end of Sprint 2, you'll have:
- Working LLM integration (OpenAI initially, extensible for others)
- Reliable outline generation from single repository
- Robust error handling for LLM failures
- Token counting and cost awareness
- Quality prompts (after iteration!)

This sprint **WILL take time**. Budget 1-1.5 weeks because:
- First LLM integration is always harder than expected
- Prompt engineering requires iteration based on real output
- Error handling for LLM APIs is non-trivial
- You'll discover edge cases as you test

**This is normal and expected.** Sprint 3 will be faster because you'll reuse patterns from Sprint 2.

---

## 📦 Deliverables

### 1. LLM Client Abstraction (`llm_client.py`)
**Estimated Lines:** ~200 lines + ~120 lines tests

**What it does:**
- Abstracts LLM provider APIs (OpenAI initially)
- Handles authentication via config
- Implements retry logic for transient failures
- Tracks token usage for cost estimation
- Provides consistent interface for outline and doc generation

**Why this sprint:**
Foundation for all LLM interactions. Build it right now, reuse in Sprint 3.

**Implementation notes:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
from openai import OpenAI
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Response from LLM API call."""
    content: str
    tokens_used: int
    model: str
    duration_seconds: float

class LLMClient(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate text from prompt."""
        pass

class OpenAIClient(LLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", timeout: int = 60):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.timeout = timeout
        
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate text from OpenAI API.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (instructions)
            json_mode: If True, use JSON mode for structured output
            temperature: Creativity level (0.0-2.0)
            
        Returns:
            LLMResponse with content and metadata
            
        Raises:
            LLMTimeoutError: Request timed out
            LLMRateLimitError: Rate limit exceeded
            LLMAPIError: Other API errors
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "timeout": self.timeout,
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            
            duration = time.time() - start_time
            
            return LLMResponse(
                content=response.choices[0].message.content,
                tokens_used=response.usage.total_tokens,
                model=response.model,
                duration_seconds=duration
            )
            
        except Exception as e:
            # Transform exceptions into custom error types
            raise self._handle_error(e)
    
    def _handle_error(self, error: Exception):
        """Transform OpenAI errors into custom error types."""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            raise LLMTimeoutError(f"OpenAI request timed out after {self.timeout}s")
        elif "rate limit" in error_str:
            raise LLMRateLimitError("OpenAI rate limit exceeded. Wait and retry.")
        else:
            raise LLMAPIError(f"OpenAI API error: {error}")

# Custom exceptions
class LLMError(Exception):
    """Base exception for LLM errors."""
    pass

class LLMTimeoutError(LLMError):
    """LLM request timed out."""
    pass

class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""
    pass

class LLMAPIError(LLMError):
    """Other LLM API errors."""
    pass
```

**Key decisions:**
- Abstract interface for future LLM providers (Sprint 2: OpenAI only)
- Consistent error handling across providers
- Token tracking built-in (for cost awareness)
- Retry logic can be added here later
- JSON mode flag for structured output

---

### 2. Outline Generator (`outline.py`)
**Estimated Lines:** ~250 lines + ~150 lines tests

**What it does:**
- Generates structured outlines from source files using LLM
- Constructs prompts with source context
- Validates LLM response matches JSON schema
- Embeds commit hashes in outline for change tracking
- Handles large source files (truncation strategies)

**Why this sprint:**
Core feature - the expensive outline generation phase. This is where prompt engineering happens.

**Implementation notes:**
```python
from pathlib import Path
from typing import Dict, Any, List
import json
from .llm_client import LLMClient, LLMResponse
from .repos import RepoManager

class OutlineGenerator:
    """Generates structured documentation outlines using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        self.client = llm_client
        
    def generate_outline(
        self, 
        source_files: Dict[str, str],  # {file_path: content}
        commit_hashes: Dict[str, str],  # {file_path: commit_hash}
        purpose: str
    ) -> Dict[str, Any]:
        """Generate outline from source files.
        
        Args:
            source_files: Dict of file paths to contents
            commit_hashes: Dict of file paths to commit hashes
            purpose: Documentation purpose (from sources.yaml)
            
        Returns:
            Outline dict with embedded commit hashes
        """
        # 1. Create prompt with source context
        prompt = self._create_prompt(source_files, purpose)
        
        # 2. Call LLM with JSON mode
        response = self.client.generate(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            json_mode=True,
            temperature=0.7  # Balanced creativity
        )
        
        # 3. Parse and validate JSON response
        outline = self._parse_and_validate(response.content)
        
        # 4. Embed commit hashes for change tracking
        outline = self._embed_commit_hashes(outline, commit_hashes)
        
        # 5. Add generation metadata
        outline["_metadata"] = {
            "generated_at": time.time(),
            "model": response.model,
            "tokens_used": response.tokens_used,
            "duration_seconds": response.duration_seconds,
        }
        
        return outline
    
    def _get_system_prompt(self) -> str:
        """System prompt for outline generation."""
        return """You are a technical documentation expert. Your task is to analyze source code and create a structured outline for comprehensive documentation.

Your outline should:
1. Identify the main purpose and functionality
2. Break down into logical sections
3. Note important implementation details
4. Reference specific source files for each topic
5. Be structured for a technical audience

Return your response as valid JSON matching the provided schema."""
    
    def _create_prompt(self, source_files: Dict[str, str], purpose: str) -> str:
        """Create user prompt with source context.
        
        This is where prompt engineering happens!
        Expect to iterate on this during Sprint 2.
        """
        prompt_parts = [
            f"Create a documentation outline for: {purpose}\n",
            "\n## Source Files:\n"
        ]
        
        for file_path, content in source_files.items():
            # Truncate very large files
            if len(content) > 10000:
                content = content[:10000] + "\n... (truncated)"
            
            prompt_parts.append(f"\n### {file_path}\n```\n{content}\n```\n")
        
        prompt_parts.append("""
\n## Task:
Generate a JSON outline with this structure:
{
  "title": "Clear, descriptive title",
  "sections": [
    {
      "heading": "Section name",
      "topics": ["Topic 1", "Topic 2"],
      "sources": [
        {
          "file": "path/to/file",
          "relevant_lines": "20-45",
          "note": "What to cover from this source"
        }
      ]
    }
  ]
}

Focus on:
- Clear section organization
- Specific line ranges where relevant
- Notes on what each source contributes
- Logical flow from overview to details
""")
        
        return "".join(prompt_parts)
    
    def _parse_and_validate(self, json_string: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON response.
        
        This WILL fail sometimes. LLMs aren't perfect.
        """
        try:
            outline = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise OutlineValidationError(
                f"LLM returned invalid JSON: {e}\n"
                f"Response: {json_string[:500]}..."
            )
        
        # Validate required fields
        required_fields = ["title", "sections"]
        for field in required_fields:
            if field not in outline:
                raise OutlineValidationError(
                    f"Missing required field: {field}\n"
                    f"Got: {outline.keys()}"
                )
        
        # Validate sections structure
        if not isinstance(outline["sections"], list):
            raise OutlineValidationError("'sections' must be a list")
        
        for i, section in enumerate(outline["sections"]):
            if "heading" not in section:
                raise OutlineValidationError(
                    f"Section {i} missing 'heading'"
                )
        
        return outline
    
    def _embed_commit_hashes(
        self, 
        outline: Dict[str, Any], 
        commit_hashes: Dict[str, str]
    ) -> Dict[str, Any]:
        """Embed commit hashes in outline for change detection."""
        # Add top-level commit hash mapping
        outline["_commit_hashes"] = commit_hashes
        
        # Also embed in each source reference
        for section in outline.get("sections", []):
            for source in section.get("sources", []):
                file_path = source.get("file")
                if file_path in commit_hashes:
                    source["commit_hash"] = commit_hashes[file_path]
        
        return outline

class OutlineValidationError(Exception):
    """Outline JSON validation failed."""
    pass
```

**Key decisions:**
- JSON mode for structured output (reduces parsing errors)
- Validation catches schema mismatches early
- Truncate large files (token limit management)
- Embed commit hashes for Sprint 5's change detection
- System prompt + user prompt pattern
- **Prompt will need iteration** - expect to refine based on output quality

---

### 3. Generate Outline Command (`cli.py` update)
**Estimated Lines:** ~100 lines + ~80 lines tests

**What it does:**
- New command: `doc-gen generate-outline <doc-path>`
- Loads config and sources
- Clones repository
- Calls OutlineGenerator
- Saves outline.json
- Reports success with token usage

**Why this sprint:**
User-facing interface for outline generation. First end-to-end LLM workflow.

**Implementation notes:**
```python
@cli.command()
@click.argument('doc-path', type=click.Path())
@click.pass_context
def generate_outline(ctx, doc_path: str):
    """Generate structured outline from source files.
    
    Uses LLM to analyze source code and create a documentation outline.
    Sources must be configured first (run: doc-gen init <doc-path>)
    
    Example:
      doc-gen generate-outline docs/modules/providers/openai.md
    """
    config = ctx.obj['config']
    metadata = MetadataManager(doc_path)
    
    try:
        # 1. Load sources
        click.echo(f"Loading sources for {doc_path}...")
        sources_config = metadata.read_sources()
        
        # 2. Clone repository
        click.echo("Cloning repository...")
        with RepoManager() as repo_mgr:
            repo_url = sources_config['repositories'][0]['url']
            repo_path = repo_mgr.clone_repo(repo_url)
            
            # 3. List and read source files
            click.echo("Reading source files...")
            include_patterns = sources_config['repositories'][0]['include']
            file_paths = repo_mgr.list_files(repo_path, include_patterns)
            
            source_files = {}
            commit_hashes = {}
            
            for file_path in file_paths:
                full_path = repo_path / file_path
                source_files[str(file_path)] = full_path.read_text()
                commit_hashes[str(file_path)] = repo_mgr.get_file_commit_hash(
                    repo_path, str(file_path)
                )
            
            click.echo(f"✓ Read {len(source_files)} files")
            
            # 4. Generate outline
            click.echo("Generating outline with LLM...")
            llm_client = OpenAIClient(
                api_key=config.llm_api_key,
                model=config.llm_model,
                timeout=config.llm_timeout
            )
            generator = OutlineGenerator(llm_client)
            
            purpose = sources_config['metadata']['purpose']
            outline = generator.generate_outline(
                source_files, 
                commit_hashes, 
                purpose
            )
            
            # 5. Save outline
            metadata.save_outline(outline)
            
            # 6. Report success
            click.echo(f"\n✓ Outline generated successfully!")
            click.echo(f"✓ Saved to: {metadata.outline_path}")
            click.echo(f"\nMetadata:")
            click.echo(f"  Model: {outline['_metadata']['model']}")
            click.echo(f"  Tokens: {outline['_metadata']['tokens_used']}")
            click.echo(f"  Duration: {outline['_metadata']['duration_seconds']:.1f}s")
            click.echo(f"\nNext steps:")
            click.echo(f"  1. Review outline: cat {metadata.outline_path}")
            click.echo(f"  2. Generate document: doc-gen generate-doc {doc_path}")
            
    except FileNotFoundError as e:
        click.echo(f"✗ Error: {e}", err=True)
        ctx.exit(1)
    except LLMError as e:
        click.echo(f"✗ LLM Error: {e}", err=True)
        click.echo(f"\nTroubleshooting:")
        click.echo(f"  - Check API key is set correctly")
        click.echo(f"  - Try again (may be transient)")
        click.echo(f"  - Check LLM provider status")
        ctx.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if ctx.obj.get('debug'):
            raise
        ctx.exit(2)
```

**Key decisions:**
- Single repository in Sprint 2 (multi-repo is Sprint 4)
- Report token usage (cost awareness)
- Clear error messages for common failures
- Show next steps after success
- Debug flag for full stack traces

---

### 4. Prompt Engineering Iteration
**Estimated Time:** 2-3 days embedded in sprint

**What it does:**
- Test outline generation with real repositories
- Evaluate output quality
- Iterate on prompts to improve results
- Document what works and what doesn't

**Why this sprint:**
Prompt engineering IS the work. Budget explicit time for iteration.

**Iteration process:**
```
Day 3-4 of Sprint 2:

1. Generate outline from test repo
2. Review output quality:
   - Is the structure logical?
   - Are sections well-organized?
   - Are source references accurate?
   - Does it capture key information?

3. Identify issues:
   - Too vague?
   - Missing important details?
   - Incorrect source references?
   - Poor section organization?

4. Refine prompt:
   - Adjust instructions
   - Add examples
   - Clarify expectations
   - Change temperature

5. Regenerate and compare
6. Repeat until satisfied

This is NORMAL. Budget 2-3 days for this.
```

**Prompt engineering checklist:**
- [ ] Test with small repo (5-10 files)
- [ ] Test with medium repo (20-30 files)
- [ ] Test with large repo (50+ files)
- [ ] Verify source references are accurate
- [ ] Check section organization is logical
- [ ] Ensure technical details are captured
- [ ] Validate JSON schema compliance
- [ ] Test edge cases (empty files, binary files)

---

## 🚫 What Gets Punted (Deliberately Excluded)

### Document Generation
- ❌ LLM integration for document generation
- Why: Sprint 2 focuses on outline generation only. Sprint 3 adds document generation.
- Reconsider: Sprint 3 (immediate next step)

### Multi-Repository Support
- ❌ Multiple repos in one outline
- Why: Sprint 2 proves LLM integration works with single repo. Sprint 4 adds multi-repo.
- Reconsider: Sprint 4 (after LLM patterns established)

### Retry Logic
- ❌ Automatic retry on transient failures
- Why: Manual retry is fine for MVP
- Reconsider: Sprint 6 (orchestration and polish)

### Prompt Templates
- ❌ Configurable prompt templates
- Why: Inline prompts work for MVP
- Reconsider: v0.2.0 if users need customization

### Cost Optimization
- ❌ Caching of outlines
- ❌ Incremental outline updates
- Why: Full regeneration is fine for MVP
- Reconsider: v0.2.0 if costs are prohibitive

---

## 🔗 Dependencies

**Requires from previous sprints:**
- Sprint 1: Config management (loads API keys)
- Sprint 1: Metadata management (saves outline.json)
- Sprint 1: Repository cloning (gets source files)
- Sprint 1: CLI framework (adds new command)

**Provides for future sprints:**
- LLM client abstraction (Sprint 3 reuses for document generation)
- Prompt engineering patterns (Sprint 3 learns from)
- Error handling patterns (Sprint 3-6 build on)
- Token tracking (Sprint 6 uses for batch operations)

---

## ✅ Acceptance Criteria

### Must Have

- ✅ **LLM client working**: Can call OpenAI API with config
- ✅ **Error handling**: Graceful handling of timeouts, rate limits, API errors
- ✅ **Outline generation**: `doc-gen generate-outline <doc-path>` works
  - Loads sources from sources.yaml
  - Clones repository
  - Reads source files
  - Generates structured outline
  - Embeds commit hashes
  - Saves to outline.json
- ✅ **JSON validation**: Validates outline matches schema
- ✅ **Token tracking**: Reports token usage and duration
- ✅ **Quality prompts**: Outlines are structured and useful (after iteration)
- ✅ **Single repo working**: Successfully generates outline from test repo
- ✅ **Test coverage**: >80% for new modules

### Nice to Have (Defer if time constrained)

- ❌ Multiple LLM provider support (Claude, etc.)
- ❌ Progress bars during generation
- ❌ Automatic retry on transient failures

---

## 🛠️ Technical Approach

### Testing Strategy

**TDD for all new functionality:**

1. **🔴 RED - Write failing tests first**
   - Test LLM client with mocked API responses
   - Test outline generator with mock LLM
   - Test JSON validation with invalid schemas
   - Test error handling for various failure modes

2. **🟢 GREEN - Write minimal implementation**
   - Implement just enough to pass tests
   - Use real LLM calls for integration tests

3. **🔵 REFACTOR - Improve code quality**
   - Extract prompt construction logic
   - Clean up error handling
   - Improve validation messages

**Unit Tests:**
- `LLMClient` handles timeouts, rate limits, errors
- `OutlineGenerator._parse_and_validate()` catches schema issues
- `OutlineGenerator._embed_commit_hashes()` embeds correctly
- Token counting is accurate

**Integration Tests:**
- End-to-end: Config → Repo clone → Outline generation → Save
- Real LLM calls with test repositories (use cheap model for tests)
- Error recovery scenarios

**Manual Testing (Prompt Engineering):**
- [ ] Generate outline from amplifier module (5-10 files)
- [ ] Generate outline from medium project (20-30 files)
- [ ] Inspect outline quality manually
- [ ] Iterate on prompts based on results
- [ ] Test with different repository types (lib, app, docs)

**Test Coverage Target:** >80% for new code

**Mocking Strategy:**
- Mock LLM API calls in unit tests (fast, deterministic)
- Use real LLM calls in integration tests (confidence)
- Use cheap model for automated tests (cost control)

---

### Token Management Strategy

**Problem:** Large repositories can exceed token limits

**Solutions:**

1. **File Truncation** (Sprint 2)
   - Truncate files >10,000 characters
   - Show "... (truncated)" in prompt
   - Simple but effective for MVP

2. **Smart Summarization** (Deferred to v0.2.0)
   - Summarize large files before including
   - Use separate LLM call for summarization
   - More expensive but better quality

3. **Selective Inclusion** (Deferred to v0.2.0)
   - Only include most relevant files
   - Use heuristics (file size, importance)
   - Requires more sophistication

**Sprint 2 uses truncation** - simple and works for MVP.

---

### Error Handling Strategy

**Common LLM errors and handling:**

1. **Timeout** (request exceeds timeout)
   - Message: "LLM request timed out after 60s"
   - Suggestion: "Try again, or increase timeout in config"

2. **Rate Limit** (too many requests)
   - Message: "Rate limit exceeded. Please wait and retry."
   - Suggestion: "Wait 60 seconds, or use --delay flag"

3. **Invalid JSON** (LLM returns malformed JSON)
   - Message: "LLM returned invalid JSON"
   - Suggestion: "Try regenerating. LLMs are non-deterministic."
   - Show first 500 chars of response

4. **Auth Error** (invalid API key)
   - Message: "Authentication failed"
   - Suggestion: "Check API key in config or environment variable"

5. **API Error** (service down, etc.)
   - Message: "LLM service error"
   - Suggestion: "Check provider status page, try again later"

**All errors include:**
- Clear description of what went wrong
- Actionable suggestion for user
- Exit code (1 = user error, 2 = system error)

---

## 📋 Implementation Order

**Follow TDD: 🔴 Write test → 🟢 Implement → 🔵 Refactor → ✅ Commit**

### Day 1-2: LLM Client Abstraction

**Day 1 Morning:**
- 🔴 Write test: `LLMClient` interface
- 🟢 Implement abstract base class
- 🔴 Write test: `OpenAIClient.generate()` success case (mocked)
- 🟢 Implement basic OpenAI integration
- ✅ Commit: "feat: Add LLM client abstraction and OpenAI implementation"

**Day 1 Afternoon:**
- 🔴 Write test: Handle timeout errors
- 🟢 Implement timeout handling
- 🔴 Write test: Handle rate limit errors
- 🟢 Implement rate limit handling
- 🔴 Write test: Handle API errors
- 🟢 Implement generic error handling
- 🔵 Refactor: Extract error transformation logic
- ✅ Commit: "feat: Add comprehensive error handling to LLM client"

**Day 2 Morning:**
- 🔴 Write test: Token counting is accurate
- 🟢 Implement token tracking in response
- 🔴 Write test: Duration tracking
- 🟢 Add timing to response
- 🔴 Write test: JSON mode flag works
- 🟢 Implement JSON mode support
- ✅ Commit: "feat: Add token tracking and JSON mode to LLM client"

**Day 2 Afternoon:**
- 🔴 Write integration test: Real OpenAI call (with mock key check)
- 🟢 Test against real API (if key available)
- 🔵 Refactor: Clean up client code
- Manual testing: Test with real API key
- ✅ Commit: "test: Add integration tests for LLM client"

### Day 3-4: Outline Generator & Prompt Engineering

**Day 3 Morning:**
- 🔴 Write test: `OutlineGenerator._create_prompt()` formats correctly
- 🟢 Implement basic prompt creation
- 🔴 Write test: Prompt includes source files
- 🟢 Add source file inclusion
- 🔴 Write test: Prompt includes purpose
- 🟢 Add purpose to prompt
- ✅ Commit: "feat: Add prompt construction for outline generation"

**Day 3 Afternoon:**
- 🔴 Write test: `_parse_and_validate()` accepts valid JSON
- 🟢 Implement JSON parsing
- 🔴 Write test: Validation catches missing fields
- 🟢 Add schema validation
- 🔴 Write test: Validation catches invalid types
- 🟢 Add type checking
- 🔵 Refactor: Extract validation logic
- ✅ Commit: "feat: Add JSON validation for outline schema"

**Day 4 Morning: PROMPT ITERATION**
- Generate outline from test repo (5-10 files)
- Manually review outline quality
- Identify issues (too vague? missing details?)
- Adjust prompt instructions
- Regenerate and compare
- Repeat 3-5 times until satisfied
- ✅ Commit: "feat: Iterate on outline generation prompts"

**Day 4 Afternoon: MORE ITERATION**
- Test with medium repo (20-30 files)
- Test with different code types (Python, JS, etc.)
- Refine prompt based on results
- Document what works in code comments
- ✅ Commit: "refactor: Refine outline prompts based on testing"

### Day 5-6: Commit Hash Embedding & CLI Integration

**Day 5 Morning:**
- 🔴 Write test: `_embed_commit_hashes()` adds hashes to outline
- 🟢 Implement commit hash embedding
- 🔴 Write test: Hashes added to each source reference
- 🟢 Add hashes to individual sources
- 🔴 Write test: Metadata section added
- 🟢 Add generation metadata
- ✅ Commit: "feat: Add commit hash embedding to outlines"

**Day 5 Afternoon:**
- 🔴 Write test: `generate_outline` command loads config
- 🟢 Implement command skeleton
- 🔴 Write test: Command clones repo and reads files
- 🟢 Wire up repo operations
- 🔴 Write test: Command calls generator
- 🟢 Wire up outline generator
- ✅ Commit: "feat: Add generate-outline CLI command"

**Day 6 Morning:**
- 🔴 Write test: Command saves outline to correct path
- 🟢 Add outline saving
- 🔴 Write test: Command reports success with metadata
- 🟢 Add success reporting
- 🔴 Write test: Error handling for missing sources
- 🟢 Add error handling
- 🔵 Refactor: Extract reporting logic
- ✅ Commit: "feat: Complete generate-outline command with error handling"

**Day 6 Afternoon:**
- 🔴 Write integration test: Full workflow end-to-end
- 🟢 Test: Config → Clone → Generate → Save
- 🔵 Fix integration bugs
- Manual testing: Run against real repos
- ✅ Commit: "test: Add end-to-end integration tests for outline generation"

### Day 7: Polish & Documentation

**Day 7 Morning:**
- Improve error messages based on testing
- Add helpful suggestions to errors
- Polish CLI output formatting
- Test edge cases (large repos, empty files)
- ✅ Commit: "polish: Improve error messages and CLI output"

**Day 7 Afternoon:**
- Update README with outline generation examples
- Document prompt engineering learnings
- Add troubleshooting section
- Update CLI help text
- ✅ Commit: "docs: Document outline generation feature"

**Day 7 Evening: Sprint Review**
- Demo outline generation with real repos
- Show token usage tracking
- Demonstrate error handling
- Verify all acceptance criteria met
- ✅ Sprint 2 complete! 🎉

---

## 📊 What You Learn

After Sprint 2, you'll discover:

1. **Prompt patterns that work** → Informs Sprint 3's document generation prompts
2. **LLM error frequencies** → Informs retry strategy in Sprint 6
3. **Token usage patterns** → Informs cost projections for multi-repo (Sprint 4)
4. **Quality vs speed tradeoffs** → Informs model selection
5. **JSON validation importance** → Validates schema-first approach

These learnings directly enable Sprint 3's document generation and inform Sprint 6's orchestration.

---

## 🎯 Success Metrics

### Quantitative
- ✅ 3 new modules (~550 LOC + ~350 LOC tests)
- ✅ Test coverage >80%
- ✅ All tests passing
- ✅ Outline generation completes in <60 seconds for small repos
- ✅ Token usage tracked for all operations

### Qualitative
- ✅ Generated outlines are well-structured
- ✅ Outlines capture key information from sources
- ✅ Source references are accurate
- ✅ Error messages are helpful
- ✅ User says "this outline is useful!"

---

## 🚧 Known Limitations (By Design)

1. **Single repository only** - Multi-repo is Sprint 4
2. **No retry logic** - Manual retry for MVP
3. **Simple truncation** - Smart summarization is v0.2.0
4. **OpenAI only** - Other providers in v0.2.0
5. **No caching** - Full regeneration each time

These limitations are **intentional**. Sprint 2 proves LLM integration works. Future sprints add sophistication.

---

## 🔮 Next Sprint Preview

After Sprint 2 ships, the next step is:

**Sprint 3: Document Generation** - Second LLM integration (1 week)

Sprint 3 will be **faster** than Sprint 2 because:
- LLM client already built (reuse patterns)
- Error handling patterns established
- Prompt engineering experience gained
- Just need document generation prompts

Sprint 3 delivers end-to-end pipeline: sources → outline → document → staging

Let's finish Sprint 2 first! 🚀

---

**Ready to tackle LLM integration? Start with Day 1 and follow the TDD workflow. Budget 1-1.5 weeks for this sprint - it's worth the time investment!**
