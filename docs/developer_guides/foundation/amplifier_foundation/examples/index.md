---
title: amplifier-foundation Examples
description: Progressive examples from hello world to production applications
---

# amplifier-foundation Examples

Progressive examples demonstrating how to use amplifier-foundation, from basic concepts to production applications.

## Learning Paths

<div class="grid cards" markdown>

-   :material-school: __For Beginners__

    ---

    1. [Hello World](hello_world.md) - See it work (2 min)
    2. [Custom Configuration](custom_configuration.md) - Composition (5 min)
    3. [Custom Tool](custom_tool.md) - Build capabilities (10 min)

-   :material-wrench: __For Builders__

    ---

    1. [CLI Application](cli_application.md) - Best practices (15 min)
    2. [Multi-Agent System](multi_agent_system.md) - Complex systems (30 min)

</div>

## Examples Catalog

| Example | Time | Complexity | Key Concepts |
|---------|------|------------|--------------|
| [Hello World](hello_world.md) | 2 min | ⭐ Beginner | Bundle loading, composition, execution |
| [Custom Configuration](custom_configuration.md) | 5 min | ⭐ Beginner | Composition patterns, adding tools |
| [Custom Tool](custom_tool.md) | 10 min | ⭐⭐ Intermediate | Tool protocol, registration |
| [CLI Application](cli_application.md) | 15 min | ⭐⭐ Intermediate | App architecture, error handling |
| [Multi-Agent System](multi_agent_system.md) | 30 min | ⭐⭐⭐ Advanced | Agent workflows, orchestration |

## Running Examples

All examples are in the [amplifier-foundation repository](https://github.com/microsoft/amplifier-foundation):

```bash
# Clone the repo
git clone https://github.com/microsoft/amplifier-foundation
cd amplifier-foundation

# Set API key
export ANTHROPIC_API_KEY='your-key-here'

# Run any example
uv run python examples/05_hello_world.py
uv run python examples/06_custom_configuration.py
uv run python examples/07_custom_tool.py
uv run python examples/08_cli_application.py
uv run python examples/09_multi_agent_system.py
```

## Example Summaries

### Hello World
Your first AI agent in ~15 lines. Learn the basic workflow: load → compose → prepare → execute.

**Key Takeaway:** Bundle composition makes it easy to configure Amplifier agents.

### Custom Configuration
Tailoring agents via composition. Learn to add tools, enable streaming, and swap orchestrators.

**Key Takeaway:** Composition over configuration - swap capabilities, not flags.

### Custom Tool
Build domain-specific capabilities. Implement the tool protocol and register custom tools.

**Key Takeaway:** Tools are just classes with `name`, `description`, `input_schema`, and `execute()`.

### CLI Application
Building production CLI tools. Application architecture, error handling, logging, configuration management.

**Key Takeaway:** Proper patterns for building real applications.

### Multi-Agent System
Coordinating specialized agents. Sequential workflows, agent specialization, context passing.

**Key Takeaway:** Build sophisticated systems by composing specialized agents.

## Common Patterns

### Pattern: Foundation + Provider

```python
foundation = await load_bundle(foundation_path)
provider = await load_bundle(provider_path)
composed = foundation.compose(provider)
prepared = await composed.prepare()

async with await prepared.create_session() as session:
    response = await session.execute(prompt)
```

### Pattern: Adding Tools

```python
tools = Bundle(
    name="tools",
    tools=[
        {"module": "tool-filesystem", "source": "git+..."},
        {"module": "tool-bash", "source": "git+..."}
    ]
)
composed = foundation.compose(provider).compose(tools)
```

### Pattern: Custom Tool Registration

```python
class MyTool:
    @property
    def name(self) -> str:
        return "my-tool"
    
    @property
    def description(self) -> str:
        return "What this tool does"
    
    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {...}}
    
    async def execute(self, input: dict) -> ToolResult:
        return ToolResult(success=True, output="result")

# Register after session creation
await coordinator.mount("tools", MyTool(), name="my-tool")
```

### Pattern: Multi-Agent Workflow

```python
architect = create_architect_agent(provider)
implementer = create_implementer_agent(provider)
reviewer = create_reviewer_agent(provider)

# Sequential workflow
for agent_name, instruction, agent_bundle in workflow:
    composed = foundation.compose(agent_bundle)
    prepared = await composed.prepare()
    
    async with await prepared.create_session() as session:
        result = await session.execute(instruction)
        results[agent_name] = result
```

## Next Steps

Choose your path:

- **New to amplifier-foundation?** → Start with [Hello World](hello_world.md)
- **Want to understand bundles?** → Read [Core Concepts](../concepts.md)
- **Building an application?** → See [CLI Application](cli_application.md)
- **Need API details?** → Check [API Reference](../api_reference.md)
