---
title: Hello World Example
description: Your first Amplifier agent in ~15 lines of code
---

# Hello World Example

The simplest possible amplifier-foundation application - load bundles, compose them, and execute a prompt.

## What This Example Demonstrates

- **Bundle Loading**: Load foundation and provider bundles from sources
- **Composition**: Layer bundles to build your configuration
- **Preparation**: Automatic module downloading and caching
- **Session Creation**: Creating a ready-to-use agent session
- **Execution**: Running prompts through the configured agent

**Time to Complete**: 2 minutes  
**Complexity**: ⭐ Beginner

## Running the Example

```bash
# Clone the repository
git clone https://github.com/microsoft/amplifier-foundation
cd amplifier-foundation

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Run the example
uv run python examples/05_hello_world.py
```

[:material-github: View Full Source Code](https://github.com/microsoft/amplifier-foundation/blob/main/examples/05_hello_world.py){ .md-button }

## How It Works

### 1. Load the Foundation Bundle

```python
foundation = await load_bundle(str(foundation_path))
```

The **foundation bundle** provides the base configuration:
- Orchestrator (controls execution flow)
- Context manager (handles conversation memory)
- Hooks (observability points)
- Base system instruction

Learn more: [What is a Bundle?](../concepts.md)

### 2. Load a Provider Bundle

```python
provider = await load_bundle(str(provider_path / "anthropic-sonnet.yaml"))
```

The **provider bundle** adds the LLM backend:
- Which model to use (Claude Sonnet 4.5)
- API configuration
- Module source (where to download the provider module)

Learn more: [Provider modules](/modules/providers/)

### 3. Compose Bundles

```python
composed = foundation.compose(provider)
```

**Composition** merges the configurations - later bundles override earlier ones. This gives you:
- Orchestrator from foundation
- Context manager from foundation
- Provider from provider bundle
- Combined system instruction

Learn more: [Bundle Composition](../concepts.md#composition)

### 4. Prepare (Download Modules)

```python
prepared = await composed.prepare()
```

**Preparation** resolves module sources and downloads them:
- Clones git repositories to `~/.amplifier/modules/`
- Registers Python entry points
- First run: ~30 seconds (downloading)
- Subsequent runs: instant (cached)

Learn more: [Module Resolution](/architecture/modules.md)

### 5. Create Session and Execute

```python
async with await prepared.create_session() as session:
    response = await session.execute("Write a haiku about Python")
    print(response)
```

Creates an **AmplifierSession** instance with all modules loaded, then executes a prompt through the configured agent.

Learn more: [Session Lifecycle](/api/core/session.md)

## Key Code Snippet

```python
from amplifier_foundation import load_bundle

async def main():
    # Load and compose
    foundation = await load_bundle(str(foundation_path))
    provider = await load_bundle(str(provider_path))
    composed = foundation.compose(provider)
    
    # Prepare and execute
    prepared = await composed.prepare()
    async with await prepared.create_session() as session:
        response = await session.execute("Write a haiku about Python")
        print(response)
```

## Expected Output

```
✓ Loaded foundation: foundation v1.0.0
✓ Loaded provider: anthropic-sonnet
✓ Composed bundles
⏳ Preparing (downloading modules if needed, this may take 30s first time)...
✓ Modules prepared
⏳ Creating session...
✓ Session ready

Response:
Code flows like water
Functions branch and merge as trees
Python's grace in code

✅ That's it! You just ran your first AI agent.
```

## Why This Works

This example demonstrates the **core amplifier-foundation pattern**:

1. **Bundles are composable** - Build your configuration by layering bundles
2. **Modules are declarative** - Specify what you want, preparation handles the how
3. **Sessions are isolated** - Each session is independent and clean
4. **Execution is simple** - Call `execute()` with your prompt

The power comes from **composition over configuration** - you don't toggle flags, you compose capabilities.

## Common Issues

!!! warning "First run takes 30+ seconds"
    
    This is normal - modules are being downloaded from GitHub and cached.
    Subsequent runs will be fast (< 1 second).
    
    Check your cache: `ls ~/.amplifier/modules/`

!!! warning "API key error"
    
    Make sure your API key is set:
    ```bash
    export ANTHROPIC_API_KEY='your-key-here'
    ```

## Related Concepts

- **[Bundles](../concepts.md)** - Understanding bundle structure and purpose
- **[Composition](../concepts.md#composition)** - How bundles merge
- **[Module System](/architecture/modules.md)** - How modules are loaded
- **[Session Lifecycle](/api/core/session.md)** - Session creation and cleanup

## Next Steps

- **[Custom Configuration Example](custom_configuration.md)** - Add tools and streaming
- **[Custom Tool Example](custom_tool.md)** - Build your own capabilities
- **[Bundle System Deep Dive](../bundle_system.md)** - Learn the internals
