---
title: Custom Configuration Example
description: Tailoring agents via composition
---

# Custom Configuration Example

Learn how to customize your agent by composing different capabilities - adding tools, enabling streaming, and swapping orchestrators.

## What This Example Demonstrates

- **Adding Tools**: Compose tools into your agent for filesystem and bash access
- **Streaming**: Swap orchestrators to enable real-time response streaming
- **Composition Patterns**: Build customized agents by layering bundles
- **Module Sources**: Specify where to download modules from

**Time to Complete**: 5 minutes  
**Complexity**: ⭐ Beginner

## Running the Example

```bash
# Clone the repository
git clone https://github.com/microsoft/amplifier-foundation
cd amplifier-foundation

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Run the example (shows 3 different configurations)
uv run python examples/06_custom_configuration.py
```

[:material-github: View Full Source Code](https://github.com/microsoft/amplifier-foundation/blob/main/examples/06_custom_configuration.py){ .md-button }

## How It Works

This example shows **three progressive configurations**:

### 1. Basic Agent (No Tools)

```python
composed = foundation.compose(provider)
```

Just foundation + provider = minimal agent with no tools.

**Result**: Agent can answer questions but cannot execute tools.

### 2. Agent with Tools

```python
tools_config = Bundle(
    name="tools-config",
    tools=[
        {"module": "tool-filesystem", "source": "git+https://..."},
        {"module": "tool-bash", "source": "git+https://..."}
    ]
)

composed = foundation.compose(provider).compose(tools_config)
```

**Composition chain**: foundation → provider → tools

**Result**: Agent can now read/write files and execute bash commands.

Learn more: [Tool modules](/modules/tools/)

### 3. Streaming Agent

```python
streaming_config = Bundle(
    name="streaming-config",
    session={
        "orchestrator": {
            "module": "loop-streaming",
            "source": "git+https://..."
        }
    },
    hooks=[
        {"module": "hooks-streaming-ui", "source": "git+https://..."}
    ]
)

composed = foundation.compose(provider).compose(streaming_config)
```

**Key changes**:
- **Orchestrator swap**: `loop-basic` → `loop-streaming`
- **Hook added**: `hooks-streaming-ui` displays streaming output

**Result**: Real-time response streaming to console.

Learn more: [Orchestrator modules](/modules/orchestrators/)

## Key Concept: Composition Over Configuration

amplifier-foundation uses **composition, not configuration**:

❌ **Configuration approach** (not used):
```yaml
tools:
  filesystem: true  # Toggle flag
  bash: true
streaming: true     # Toggle flag
```

✅ **Composition approach** (used):
```python
foundation.compose(provider).compose(tools).compose(streaming)
```

**Why composition is better**:
- Modules are independently versioned
- Each module can be swapped without affecting others
- Clear dependency chain
- No combinatorial explosion of flag combinations

Learn more: [Composition Patterns](../patterns.md)

## Adding Tools Pattern

Create a bundle with tools and compose it:

```python
from amplifier_foundation import Bundle

tools = Bundle(
    name="my-tools",
    tools=[
        {
            "module": "tool-filesystem",
            "source": "git+https://github.com/microsoft/amplifier-module-tool-filesystem@main"
        },
        {
            "module": "tool-bash",
            "source": "git+https://github.com/microsoft/amplifier-module-tool-bash@main"
        }
    ]
)

composed = foundation.compose(provider).compose(tools)
```

**Module sources**: The `source:` field tells `prepare()` where to download modules from.

Learn more: [Module Resolution](/libraries/module_resolution.md)

## Swapping Orchestrators Pattern

Change execution behavior by swapping the orchestrator:

```python
streaming = Bundle(
    name="streaming",
    session={
        "orchestrator": {
            "module": "loop-streaming",  # Instead of loop-basic
            "source": "git+https://..."
        }
    }
)

composed = foundation.compose(provider).compose(streaming)
```

**Available orchestrators**:
- `loop-basic`: Simple request/response
- `loop-streaming`: Real-time streaming responses
- `loop-events`: Event-driven execution

Learn more: [Orchestrator Contract](/developer/contracts/orchestrator.md)

## Why This Works

**Composition is powerful because**:

1. **Modules are self-contained** - Each module is independently developed and versioned
2. **Later wins** - Provider config can override foundation defaults
3. **No side effects** - Composing bundles doesn't modify them
4. **Reusable** - Create reusable bundle "templates" for common configurations

The foundation bundle provides sensible defaults, and you **layer on capabilities** as needed.

## Expected Output

The example runs three agents and shows their different capabilities:

```
🎨 Amplifier Configuration Showcase
============================================================

EXAMPLE 1: Basic Agent (No Tools)
============================================================
✓ Response: I don't have access to tools to list files...

EXAMPLE 2: Agent with Tools (Filesystem + Bash)
============================================================
✓ Response: [Lists actual files from current directory]

EXAMPLE 3: Streaming Agent (Real-time Responses)
============================================================
[Streams poem line by line in real-time]
```

## Related Concepts

- **[Bundles](../concepts.md)** - Understanding bundle structure
- **[Composition](../concepts.md#composition)** - How merging works
- **[Module System](/architecture/modules.md)** - Module types and contracts
- **[Tools](/modules/tools/)** - Available tool modules
- **[Orchestrators](/modules/orchestrators/)** - Execution strategies
- **[Hooks](/modules/hooks/)** - Observability and control

## Next Steps

- **[Custom Tool Example](custom_tool.md)** - Build your own tool from scratch
- **[CLI Application Example](cli_application.md)** - Production application patterns
- **[Patterns Guide](../patterns.md)** - More composition patterns
