---
title: Custom Tool Example
description: Build domain-specific capabilities in 20 lines
---

# Custom Tool Example

Learn how to create custom tools for domain-specific capabilities - weather data, database queries, API clients, or any functionality your agent needs.

## What This Example Demonstrates

- **Tool Contract**: The minimal interface a tool must implement
- **No Inheritance Required**: Just implement the protocol (name, description, input_schema, execute)
- **Registration**: How to register custom tools with the coordinator
- **Integration**: Custom tools work seamlessly with any orchestrator/provider

**Time to Complete**: 10 minutes  
**Complexity**: ⭐⭐ Intermediate

## Running the Example

```bash
# Clone the repository
git clone https://github.com/microsoft/amplifier-foundation
cd amplifier-foundation

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Run the example
uv run python examples/07_custom_tool.py
```

[:material-github: View Full Source Code](https://github.com/microsoft/amplifier-foundation/blob/main/examples/07_custom_tool.py){ .md-button }

## How It Works

### The Tool Contract

Every tool must implement these four things:

```python
class MyTool:
    @property
    def name(self) -> str:
        """Unique identifier for this tool"""
        return "my-tool"
    
    @property
    def description(self) -> str:
        """Description the LLM sees to decide when to use this tool"""
        return "What this tool does and when to use it"
    
    @property
    def input_schema(self) -> dict:
        """JSON schema defining the tool's parameters"""
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "..."}
            },
            "required": ["param1"]
        }
    
    async def execute(self, input: dict) -> ToolResult:
        """Execute the tool with the given input"""
        return ToolResult(success=True, output="result")
```

**No inheritance, no framework magic** - just implement these four members.

Learn more: [Tool Contract](/developer/contracts/tool.md)

## Example 1: Weather Tool

```python
from amplifier_core import ToolResult

class WeatherTool:
    @property
    def name(self) -> str:
        return "weather"
    
    @property
    def description(self) -> str:
        return "Get current weather for a location"
    
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or zip code"
                }
            },
            "required": ["location"]
        }
    
    async def execute(self, input: dict) -> ToolResult:
        location = input.get("location", "")
        
        # Your implementation here - could call a weather API
        weather_data = {
            "temperature": "72°F",
            "conditions": "Partly cloudy",
            "humidity": "65%"
        }
        
        return ToolResult(
            success=True,
            output=f"Weather for {location}: {weather_data['temperature']}, {weather_data['conditions']}"
        )
```

**Key points**:
- `input_schema` helps the LLM know what parameters to provide
- `execute()` returns a `ToolResult` with success/failure and output
- Error handling: Return `ToolResult(success=False, error={...})`

## Example 2: Database Tool

```python
class DatabaseTool:
    @property
    def name(self) -> str:
        return "database"
    
    @property
    def description(self) -> str:
        return "Query the application database"
    
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query"},
                "params": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["query"]
        }
    
    async def execute(self, input: dict) -> ToolResult:
        query = input.get("query")
        
        # In production: use asyncpg, SQLAlchemy, etc.
        # For demo: return mock data
        results = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        
        return ToolResult(success=True, output=results)
```

This demonstrates how to build **domain-specific tools** for your application.

## Registering Custom Tools

After creating a session, register your tools:

```python
# Create session
session = await prepared.create_session()

# Create tool instances
weather = WeatherTool()
database = DatabaseTool()

# Register with coordinator
await session.coordinator.mount("tools", weather, name=weather.name)
await session.coordinator.mount("tools", database, name=database.name)

# Now use the session
async with session:
    response = await session.execute("What's the weather in San Francisco?")
```

The coordinator makes tools available to the orchestrator, which the LLM can then use.

Learn more: [Coordinator API](/api/core/coordinator.md)

## Why This Works

**Protocol-based design** means:

1. **No inheritance required** - Your tool doesn't extend a base class
2. **No framework coupling** - Tools work with any Amplifier orchestrator
3. **Easy to test** - Test your tool independently of the framework
4. **Simple to understand** - Four methods, clear contract

The LLM uses:
- `name` to identify the tool
- `description` to decide when to use it
- `input_schema` to know what parameters to provide
- `execute()` is called with those parameters

## Expected Output

```
🔧 Building Custom Tools with Amplifier
============================================================

[Test 1: Weather Tool]
📝 Asking about weather...
✓ Response: Based on the weather tool, San Francisco currently has:
- Temperature: 72°F
- Conditions: Partly cloudy
- Humidity: 65%

[Test 2: Database Tool]
📝 Asking about database...
✓ Response: I queried the users table and found:
- Alice (ID: 1)
- Bob (ID: 2)

[Test 3: Multi-tool Usage]
📝 Using multiple tools together...
✓ Response: [Uses weather, database, and filesystem tools together]
```

## Input Schema Best Practices

The `input_schema` is critical - it guides the LLM:

```python
{
    "type": "object",
    "properties": {
        "location": {
            "type": "string",
            "description": "City name or zip code"  # Clear description helps LLM
        },
        "units": {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],  # Restrict valid values
            "description": "Temperature units"
        }
    },
    "required": ["location"]  # Mark required vs optional
}
```

**Tips**:
- Use clear descriptions - the LLM reads these
- Specify types accurately
- Use `enum` for restricted choices
- Mark truly required fields only

Learn more: [JSON Schema](https://json-schema.org/)

## Error Handling Pattern

```python
async def execute(self, input: dict) -> ToolResult:
    try:
        # Validate input
        if not input.get("location"):
            return ToolResult(
                success=False,
                error={"message": "Location is required"}
            )
        
        # Do work
        result = await call_weather_api(input["location"])
        
        return ToolResult(success=True, output=result)
        
    except Exception as e:
        return ToolResult(
            success=False,
            error={"message": str(e), "type": type(e).__name__}
        )
```

**Always return a ToolResult** - never raise exceptions from `execute()`.

## Related Concepts

- **[Tool Contract](/developer/contracts/tool.md)** - Complete contract specification
- **[Coordinator](/api/core/coordinator.md)** - Tool registration API
- **[ToolResult](/api/core/models.md)** - Return type specification
- **[Built-in Tools](/modules/tools/)** - Examples of tool implementations
- **[Module Development](/developer/module_development.md)** - Packaging tools as modules

## Next Steps

- **[CLI Application Example](cli_application.md)** - Production application patterns
- **[Multi-Agent System Example](multi_agent_system.md)** - Complex agent workflows
- **[Tool Contract](/developer/contracts/tool.md)** - Full contract details
