# doc-gen

AI-powered documentation generation tool that creates high-quality documentation from structured JSON outlines using Anthropic Claude.

## Overview

doc-gen separates documentation structure (outlines) from content generation. You define what documentation to create and which source files to reference, then Claude generates the actual content. This enables:

- **Consistency** - Same outline always produces similar documentation
- **Maintainability** - Update sources and regenerate when code changes
- **Version Control** - Outlines and generated docs both tracked in git
- **Source Traceability** - Every section references specific source files with commit hashes

## Features

| Feature | Description |
|---------|-------------|
| **Outline-Based Generation** | Define structure, prompts, and sources in JSON |
| **Debug Logging** | Optional `--debug-prompts` flag logs all LLM interactions |
| **Hierarchical Generation** | Depth-first traversal maintains context across sections |
| **Staging Workflow** | Review generated docs before promoting to final location |

## Quick Start

### 1. Run the Wrapper

The `doc-gen` wrapper script handles installation automatically on first run:

```bash
# From project root
tools/doc-gen/doc-gen init
```

This creates:
- `.doc-gen/config.yaml` - Configuration and outline registry if does not exist
- `.doc-gen/amplifier-docs-cache/` - Storage for registered outlines, if does not exist
- `.doc-gen/examples/sample-outline.json` - Sample outline to for reference, if does not exist

### 2. Set Up API Key

Configure your Anthropic API key using either method:

**Option 1: Environment Variable**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**Option 2: File**
```bash
mkdir -p ~/.claude
echo "sk-ant-api03-..." > ~/.claude/api_key.txt
```

### 3. Try the Sample

Generate official documentation from the pre-registered outline:

```bash
tools/doc-gen/doc-gen generate ./docs/api/core/hooks.md
```
You will see logging on generation progress. A new `hooks.md` file will be placed under `.doc-gen/staging/`

### 4. Your Turn

Now create your own outline! Ask Amplifier to generate one for you using reference outlines as examples, or copy an existing outline.

Once you have an outline, here's what to customize (see [Outline Format](#outline-format) for complete structure reference):

#### Key Fields to Edit

| Field | Purpose | Examples & Tips |
|-------|---------|-----------------|
| **Document Instruction**<br>`_meta.document_instruction` | Sets overall style for ALL sections.<br>Included in every prompt to Claude. | **API docs:** `"Write precise, technical API documentation. Use code examples and tables."`<br>**Tutorial:** `"Write friendly, beginner-focused tutorials. Use simple language and step-by-step instructions."`<br>**How-to:** `"Write goal-oriented guides. Focus on accomplishing specific tasks."` |
| **Section Prompts**<br>`sections[].prompt` | Specific instructions for each section.<br>Be clear about format needed. | ✅ **Good:** `"Document the authenticate() method. Show code example with error handling."`<br>❌ **Bad:** `"Write about authentication"` |
| **Source Reasoning**<br>`sources[].reasoning` | Explains WHY each source is relevant.<br>Helps Claude extract right info. | ✅ **Good:** `"Contains authenticate() implementation with error handling that we need to document"`<br>❌ **Bad:** `"Has authentication code"` |
| **Temperature**<br>`_meta.temperature` | Controls creativity vs consistency.<br>(0.0 = deterministic, 1.0 = creative) | **0.1-0.2:** Technical docs, API reference (default)<br>**0.3-0.4:** Tutorials with examples<br>**0.5+:** Creative content |
| **Model**<br>`_meta.model` | Chooses which Claude model to use. | **Default:** `claude-sonnet-4-20250514` (great for most docs)<br>**Complex only:** `claude-opus-4-20250514` (slower, more expensive) |


#### Generate Your Outline

```bash
tools/doc-gen/doc-gen --debug-prompts generate-from-outline <OUTLINE_PATH> <OUTPUT_PATH> 
```

> Use `--debug-prompts` to see exactly what Claude receives:
>
> Check `.doc-gen/debug/prompts-*.json` to see the full prompt sent for each section.

Use this to refine your prompts!

To run `generate` on this new outline, please see the `register-outline` command below.

## Commands

### `init`

Initialize doc-gen configuration in your project.

```bash
tools/doc-gen/doc-gen init
```

Creates:
- Configuration file at `.doc-gen/config.yaml`
- Outline storage directory at `.doc-gen/amplifier-docs-cache/`
- Sample outline at `.doc-gen/examples/sample-outline.json`

### `generate-from-outline`

Generate documentation directly from an outline file to a specified output path.

```bash
tools/doc-gen/doc-gen generate-from-outline <OUTLINE_PATH> <OUTPUT_PATH>
```

**Arguments:**
- `OUTLINE_PATH` - Path to the outline JSON file
- `OUTPUT_PATH` - Where to write the generated documentation

**Example:**
```bash
tools/doc-gen/doc-gen generate-from-outline \
  my-outline.json \
  docs/api/overview.md
```

Use this for quick generation or when you don't need the outline registry.

### `register-outline`

Register an outline in the config for a documentation file.

```bash
tools/doc-gen/doc-gen register-outline <OUTLINE_PATH> <DOC_PATH>
```

**Arguments:**
- `OUTLINE_PATH` - Path to the outline JSON file (will be copied to cache)
- `DOC_PATH` - Documentation file path (e.g., `docs/api/overview.md`)

**Example:**
```bash
tools/doc-gen/doc-gen register-outline \
  /tmp/my-outline.json \
  docs/api/overview.md
```

This:
1. Copies outline to `.doc-gen/amplifier-docs-cache/docs-api-overview/overview_outline.json`
2. Registers the mapping in `.doc-gen/config.yaml`

### `generate`

Generate documentation from a registered outline to staging area.

```bash
tools/doc-gen/doc-gen generate <DOC_PATH>
```

**Arguments:**
- `DOC_PATH` - Documentation file path (e.g., `docs/api/overview.md`)

**Example:**
```bash
tools/doc-gen/doc-gen generate docs/api/overview.md
```

This:
1. Looks up the registered outline in config
2. Generates documentation to `.doc-gen/staging/docs/api/overview.md`
3. Preserves final location for review before promotion

### `promote`

Promote a staged document to its final location.

```bash
tools/doc-gen/doc-gen promote <DOC_PATH>
```

**Arguments:**
- `DOC_PATH` - Documentation file path (e.g., `docs/api/overview.md`)

**Example:**
```bash
tools/doc-gen/doc-gen promote docs/api/overview.md
```

This:
1. Copies from `.doc-gen/staging/docs/api/overview.md` to `docs/api/overview.md`
2. Removes the staged file
3. Cleans up empty staging directories

### `--debug-prompts`

Global flag that logs all LLM prompts and responses.

```bash
tools/doc-gen/doc-gen --debug-prompts <COMMAND>
```

**Example:**
```bash
tools/doc-gen/doc-gen --debug-prompts generate docs/api/overview.md
```

Debug logs are saved to `.doc-gen/debug/prompts-YYYYMMDD-HHMMSS.json` with:
- Full prompts sent to Claude
- Complete responses received
- Token estimates
- Timestamps and model info
- Source locations in code

Use this to:
- Debug generation issues
- Understand what prompts are being sent
- Optimize outline prompts
- Track API usage

## Outline Format

Outlines are JSON files that define documentation structure. See `examples/sample-outline.json` for a complete example.

### Structure

```json
{
  "_meta": {
    "name": "unique-outline-name",
    "document_instruction": "Overall guidance for content generation",
    "model": "claude-sonnet-4-20250514",
    "max_response_tokens": 8000,
    "temperature": 0.2
  },
  "document": {
    "title": "Document Title",
    "output": "docs/path/to/output.md",
    "sections": [...]
  }
}
```

### _meta Fields

- `name` - Unique identifier for this outline
- `document_instruction` - High-level instructions for the entire document
- `model` - Claude model identifier (default: `claude-sonnet-4-20250514`)
- `max_response_tokens` - Maximum tokens per section (default: `8000`)
- `temperature` - Creativity level 0.0-1.0 (default: `0.2` for technical docs)

### document Fields

- `title` - Document title (for reference, not written to output)
- `output` - Output path relative to project root
- `sections` - Array of section objects (hierarchical)

### Section Object

```json
{
  "heading": "# Section Title",
  "level": 1,
  "prompt": "Instructions for generating this section's content",
  "sources": [
    {
      "file": "https://github.com/org/repo/blob/main/path/file.py",
      "reasoning": "Why this source is relevant",
      "commit": "abc123def456"
    }
  ],
  "sections": []
}
```

**Fields:**
- `heading` - Markdown heading with level indicator (e.g., `# Title`, `## Subtitle`)
- `level` - Heading level 1-6
- `prompt` - What to generate for this section
- `sources` - Array of source file references
- `sections` - Nested subsections (recursive structure)

### Source References

Sources must be GitHub URLs in blob format:

```
https://github.com/org/repo/blob/branch/path/to/file
```

**Required Fields:**
- `file` - GitHub blob URL
- `reasoning` - Why this source is relevant to the section
- `commit` - Git commit hash for version pinning (required)

doc-gen automatically converts blob URLs to raw URLs using the commit hash, ensuring stable references even as the default branch changes.

## Outline Tips

Creating effective outlines is key to generating high-quality documentation. Here are the most important elements to customize:

### What to Customize

#### 1. Document Instruction (`_meta.document_instruction`)

**What it does:** Provides overall guidance that applies to EVERY section generation.

**Why it matters:** This instruction is included in every prompt sent to Claude, setting the tone and style for the entire document.

**Examples:**
```json
// For technical API documentation
"document_instruction": "Write precise, technical API documentation. Use code examples, parameter tables, and return value descriptions. Keep explanations concise and accurate."

// For beginner tutorials
"document_instruction": "Write friendly, beginner-focused tutorials. Use simple language, step-by-step instructions, and encouraging tone. Include 'what you'll learn' and 'what you'll need' sections."

// For how-to guides
"document_instruction": "Write goal-oriented how-to guides. Focus on accomplishing specific tasks. Start with the goal, show steps clearly, avoid explaining concepts."
```

**Tip:** This is the single most impactful field for controlling documentation style.

#### 2. Section Prompts (`sections[].prompt`)

**What it does:** Specific instructions for generating THAT section's content.

**Why it matters:** While `document_instruction` sets overall style, the section `prompt` tells Claude exactly what to write for that specific section.

**Examples:**
```json
// Good - Specific and actionable
"prompt": "Document the authenticate() method. Show a complete code example with error handling. Explain each parameter and what happens on success vs failure."

// Bad - Vague
"prompt": "Write about authentication"

// Good - Clear expectations
"prompt": "Provide step-by-step installation instructions. Show the exact commands users need to run. Include troubleshooting for common installation errors."

// Bad - Unclear
"prompt": "Talk about how to install"
```

**Tip:** Be specific about format (code examples, tables, bullet points) and what information to include.

#### 3. Source Reasoning (`sources[].reasoning`)

**What it does:** Explains WHY each source file is relevant to the section.

**Why it matters:** Helps Claude understand what information to extract from the source file and how it relates to the section.

**Examples:**
```json
// Good - Specific about what's in the file
"reasoning": "Lines 45-67 implement the authentication logic with error handling and token generation"

// Better - Explains relevance
"reasoning": "Contains the authenticate() method implementation showing parameter validation, token generation, and error responses that we need to document"

// Bad - Too vague
"reasoning": "Has authentication code"
```

**Tip:** Mention specific lines or components if you know them. Explain what information the file provides.

#### 4. Model Selection (`_meta.model`)

**What it does:** Chooses which Claude model to use for generation.

**When to customize:**
- Use `claude-sonnet-4-20250514` (default) for most documentation - good balance of quality and speed
- Use `claude-opus-4-20250514` for complex technical content requiring deep reasoning (slower, more expensive)

**Example:**
```json
"model": "claude-sonnet-4-20250514"  // Default - use this unless you need Opus
```

#### 5. Temperature (`_meta.temperature`)

**What it does:** Controls creativity vs consistency (0.0 = deterministic, 1.0 = creative).

**When to customize:**
- `0.1-0.2` - Technical documentation, API references (default: `0.2`)
- `0.3-0.4` - Tutorials, explanations with examples
- `0.5-0.7` - Creative content, blog posts, marketing copy

**Examples:**
```json
// Precise API documentation
"temperature": 0.1

// Friendly tutorial
"temperature": 0.3

// Creative blog post
"temperature": 0.6
```

**Tip:** Lower temperature = more consistent output when regenerating. Higher temperature = more varied, creative writing.

### Debugging Your Outlines

To see EXACTLY what prompts are sent to Claude and what responses come back:

```bash
tools/doc-gen/doc-gen --debug-prompts generate docs/api/overview.md
```

This creates a debug log at `.doc-gen/debug/prompts-YYYYMMDD-HHMMSS.json` containing:

- Full prompt text sent to Claude
- Document instruction included
- Section prompt included
- All source file contents
- Previous section context
- Complete Claude response
- Token estimates (prompt and response)
- Timestamps and model info

**Use debug logs to:**
- See if your `document_instruction` is working as intended
- Check if section `prompts` are clear enough
- Verify source files contain the expected information
- Understand why output doesn't match expectations
- Optimize prompts based on what Claude actually receives

**Example workflow:**
```bash
# 1. Generate with debug
tools/doc-gen/doc-gen --debug-prompts generate docs/api/overview.md

# 2. Review the debug log
cat .doc-gen/debug/prompts-YYYYMMDD-HHMMSS.json | jq '.[].prompt' | less

# 3. Adjust your outline based on what you see
vim .doc-gen/amplifier-docs-cache/docs-api-overview/overview_outline.json

# 4. Regenerate
tools/doc-gen/doc-gen generate docs/api/overview.md
```

### Quick Start Template

Copy this as a starting point for your outline:

```json
{
  "_meta": {
    "name": "my-doc-outline",
    "document_instruction": "Write [STYLE] documentation. Use [FORMAT]. Keep [TONE].",
    "model": "claude-sonnet-4-20250514",
    "max_response_tokens": 8000,
    "temperature": 0.2
  },
  "document": {
    "title": "My Document Title",
    "output": "docs/my-doc.md",
    "sections": [
      {
        "heading": "# Main Section",
        "level": 1,
        "prompt": "Write [SPECIFIC INSTRUCTIONS]. Include [REQUIREMENTS].",
        "sources": [
          {
            "file": "https://github.com/org/repo/blob/main/path/file.py",
            "reasoning": "Contains [WHAT IT HAS] that we need for [PURPOSE]",
            "commit": "abc123"
          }
        ],
        "sections": []
      }
    ]
  }
}
```

Replace the bracketed placeholders with your specific requirements.

## Workflow

### Option 1: Direct Generation (Simple)

For quick generation without registry:

```bash
# Create outline
vim my-outline.json

# Generate directly
tools/doc-gen/doc-gen generate-from-outline \
  my-outline.json \
  docs/output.md
```

### Option 2: Registered Workflow (Recommended)

For maintained documentation with staging:

```bash
# 1. Initialize project
tools/doc-gen/doc-gen init

# 2. Create outline
vim my-outline.json

# 3. Register outline
tools/doc-gen/doc-gen register-outline \
  my-outline.json \
  docs/api/overview.md

# 4. Generate to staging
tools/doc-gen/doc-gen generate docs/api/overview.md

# 5. Review staged output
cat .doc-gen/staging/docs/api/overview.md

# 6. Promote to final location
tools/doc-gen/doc-gen promote docs/api/overview.md
```

### Regenerating Documentation

When source code changes:

```bash
# 1. Update outline's commit hashes to latest
vim .doc-gen/amplifier-docs-cache/docs-api-overview/overview_outline.json

# 2. Regenerate
tools/doc-gen/doc-gen generate docs/api/overview.md

# 3. Review and promote
cat .doc-gen/staging/docs/api/overview.md
tools/doc-gen/doc-gen promote docs/api/overview.md
```

## Configuration

### Config File: `.doc-gen/config.yaml`

```yaml
# Outline storage location
outline_storage: .doc-gen/amplifier-docs-cache

# Registry: maps documentation files to their outlines
outlines:
  docs/api/overview.md: docs-api-overview/overview_outline.json
  docs/architecture/kernel.md: docs-architecture-kernel/kernel_outline.json
```

**Fields:**
- `outline_storage` - Directory for storing outline files (relative to project root)
- `outlines` - Dictionary mapping doc paths to outline paths (relative to storage)

### Outline Storage Convention

Outlines are stored using this naming pattern:

```
docs/api/overview.md → .doc-gen/amplifier-docs-cache/docs-api-overview/overview_outline.json
```

Pattern: `{path-with-dashes}/{basename}_outline.json`

This keeps outlines organized and prevents naming conflicts.

## Architecture

### Module Overview

| Module | Purpose |
|--------|---------|
| `cli.py` | Command-line interface and command implementations |
| `config.py` | Configuration file management and outline registry |
| `llm_client.py` | Anthropic Claude API client with error handling |
| `prompt_logger.py` | Debug logging infrastructure for LLM interactions |
| `utils.py` | Utility functions (project root detection) |
| `generate/doc_generator.py` | Main documentation generation logic |
| `generate/outline_models.py` | Data models for outlines and sections |

### Generation Process

1. **Load Outline** - Parse JSON and validate structure
2. **Depth-First Traversal** - Process sections recursively
3. **Fetch Sources** - Download source files from GitHub at commit hash
4. **Generate Section** - Send prompt + sources + context to Claude
5. **Maintain Context** - Pass generated content to child sections
6. **Assemble Document** - Combine all sections into final markdown

### Context Flow

doc-gen uses depth-first traversal to maintain context:

```
Section A (generate)
  ├─ Section B (generate with A's context)
  │  └─ Section D (generate with A+B context)
  └─ Section C (generate with A's context)
     └─ Section E (generate with A+C context)
```

This ensures:
- Subsections have parent context
- Content flows naturally
- No duplication across sections
- Coherent narrative structure

## Examples

See `examples/` directory for sample outlines:
- `sample-outline.json` - Minimal beginner-friendly example
- `README.md` - Guide to creating outlines

See `.doc-gen/amplifier-docs-cache/` for real-world examples:
- Tutorial-style documentation
- API reference documentation
- How-to guides
- Conceptual explanations

## Requirements

- **Python** - 3.11 or higher
- **Dependencies** - Installed automatically by wrapper script
  - `click>=8.1.0` - Command-line interface
  - `anthropic>=0.18.0` - Claude API client
  - `pyyaml>=6.0` - Configuration file parsing

## Development

### Install in Development Mode

```bash
cd tools/doc-gen
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run Tests

```bash
# Test with sample outline
doc-gen generate-from-outline \
  examples/sample-outline.json \
  /tmp/test-output.md

# Test with debug logging
doc-gen --debug-prompts generate-from-outline \
  examples/sample-outline.json \
  /tmp/test-output.md

# Review debug log
cat .doc-gen/debug/prompts-*.json | jq '.'
```

### Wrapper Script

The `doc-gen` bash wrapper provides zero-setup experience:

- Detects Python availability (tries `python3`, then `python`)
- Creates `.venv` on first run
- Installs package with dependencies
- Passes all arguments to installed CLI

Users can run `tools/doc-gen/doc-gen` without manual installation.

## Troubleshooting

### API Key Not Found

```
Error: Anthropic API key not found
```

**Solution:** Set `ANTHROPIC_API_KEY` environment variable or create `~/.claude/api_key.txt`

### Source File Not Found

```
**file.py** (failed to fetch from GitHub)
```

**Solution:** 
- Verify GitHub URL is correct
- Ensure commit hash exists in repository
- Check internet connectivity

### Generation Produces Wrong Structure

**Solution:** Use `--debug-prompts` to see actual prompts sent to Claude. Check that:
- Outline structure is correct
- Prompts are clear and specific
- Sources contain relevant information

### Outline Not Registered

```
Error: No outline registered for: docs/api/overview.md
```

**Solution:** Run `doc-gen register-outline <outline> docs/api/overview.md`

## License

See main repository LICENSE file.
