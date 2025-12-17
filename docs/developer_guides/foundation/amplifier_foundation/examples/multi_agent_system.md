---
title: Multi-Agent System Example
description: Coordinating specialized agents in workflows
---

# Multi-Agent System Example

Learn how to build sophisticated systems by coordinating specialized agents - each with different capabilities, tools, and expertise working together in workflows.

## What This Example Demonstrates

- **Agent Specialization**: Define agents with different tools and instructions
- **Sequential Workflows**: Chain agents together (agent1 → agent2 → agent3)
- **Context Passing**: Agents build on previous agents' work
- **Real-World Architectures**: Patterns for production multi-agent systems

**Time to Complete**: 30 minutes  
**Complexity**: ⭐⭐⭐ Advanced

## Running the Example

```bash
# Clone the repository
git clone https://github.com/microsoft/amplifier-foundation
cd amplifier-foundation

# Set your API key
export ANTHROPIC_API_KEY='your-key-here'

# Run the example (shows architect → implementer → reviewer workflow)
uv run python examples/09_multi_agent_system.py
```

[:material-github: View Full Source Code](https://github.com/microsoft/amplifier-foundation/blob/main/examples/09_multi_agent_system.py){ .md-button }

## How It Works

Multi-agent systems solve complex problems by **dividing work among specialized agents**.

### Agent Specialization

Each agent has:
- **Different tools** - Architect reads docs, Implementer writes code
- **Different instructions** - Each agent has specific expertise
- **Different configuration** - Can use different models or settings

```python
def create_architect_agent(provider: Bundle) -> Bundle:
    """Designs system architecture and specifications"""
    return Bundle(
        name="architect",
        tools=[{"module": "tool-filesystem", "source": "..."}],
        instruction="""You are a Software Architect expert.
        
        Your role:
        - Design system architectures and specifications
        - Break down complex problems into modules
        - Define clear interfaces and contracts
        
        Focus on design, not implementation."""
    ).compose(provider)
```

The architect has **read-only filesystem access** and focuses on **design**.

```python
def create_implementer_agent(provider: Bundle) -> Bundle:
    """Implements code based on specifications"""
    return Bundle(
        name="implementer",
        tools=[
            {"module": "tool-filesystem", "source": "..."},
            {"module": "tool-bash", "source": "..."}
        ],
        instruction="""You are a Software Implementation expert.
        
        Your role:
        - Implement code based on specifications
        - Write clean, tested, documented code
        - Run tests to verify correctness"""
    ).compose(provider)
```

The implementer has **full filesystem and bash access** for **implementation**.

### Sequential Workflow

```python
workflow = [
    ("architect", "Design a rate limiting module", architect_bundle),
    ("implementer", "Implement the design", implementer_bundle),
    ("reviewer", "Review the implementation", reviewer_bundle)
]

for agent_name, instruction, agent_bundle in workflow:
    # Create session for this agent
    composed = foundation.compose(agent_bundle)
    prepared = await composed.prepare()
    
    # Execute with context from previous agents
    async with await prepared.create_session() as session:
        result = await session.execute(instruction_with_context)
        results[agent_name] = result
```

Each agent:
1. Receives the original task
2. Gets outputs from previous agents
3. Performs its specialized work
4. Passes results to next agent

### Context Passing

```python
def _format_context(self, context: dict, previous_results: dict) -> str:
    """Format context from previous agents"""
    sections = [f"Task: {context['task']}"]
    
    for agent_name, result in previous_results.items():
        sections.append(f"\n{agent_name.upper()} OUTPUT:")
        sections.append(result[:500])  # Truncate for brevity
    
    return "\n".join(sections)
```

Each agent sees:
- The original task description
- All previous agents' outputs
- Can build on their work

## Real-World Use Cases

### Software Development Pipeline

```
Architect → Implementer → Reviewer → Tester
```

- **Architect**: Designs system architecture
- **Implementer**: Writes the code
- **Reviewer**: Reviews for quality and security
- **Tester**: Creates and runs tests

### Data Analysis Pipeline

```
Collector → Analyzer → Visualizer → Reporter
```

- **Collector**: Gathers data from sources
- **Analyzer**: Analyzes patterns and insights
- **Visualizer**: Creates charts and graphs
- **Reporter**: Writes analysis report

### Content Creation Pipeline

```
Researcher → Writer → Editor → Publisher
```

- **Researcher**: Gathers information and sources
- **Writer**: Creates content draft
- **Editor**: Refines language and structure
- **Publisher**: Formats and publishes

### Customer Support System

```
Classifier → Resolver → Escalator
```

- **Classifier**: Categorizes support tickets
- **Resolver**: Handles common issues
- **Escalator**: Routes complex issues to humans

## Expected Output

```
🤝 Amplifier Multi-Agent Systems
============================================================

WORKFLOW: Build a Feature (Design → Implement → Review)
============================================================

============================================================
🤖 Agent: ARCHITECT
============================================================
Instruction: Design a rate limiting module...
⏳ Preparing agent...
✓ Modules prepared
🔄 Executing...

✓ architect completed
Response length: 1523 chars

============================================================
🤖 Agent: IMPLEMENTER
============================================================
Instruction: Implement the design...
ARCHITECT OUTPUT:
[Previous design here]

⏳ Preparing agent...
🔄 Executing...

✓ implementer completed
Response length: 2341 chars

============================================================
🤖 Agent: REVIEWER
============================================================
Instruction: Review the implementation...
ARCHITECT OUTPUT: [...]
IMPLEMENTER OUTPUT: [...]

⏳ Preparing agent...
🔄 Executing...

✓ reviewer completed
Response length: 1127 chars

============================================================
WORKFLOW COMPLETE - SUMMARY
============================================================
```

## Why This Works

**Multi-agent systems are powerful because**:

1. **Specialization** - Each agent focuses on what it does best
2. **Modularity** - Agents can be developed and tested independently
3. **Reusability** - Same agents can be used in different workflows
4. **Scalability** - Add more agents without changing existing ones
5. **Observability** - Each agent's work is clearly separated

## Architecture Pattern

```python
class MultiAgentSystem:
    """Orchestrates multiple specialized agents"""
    
    def __init__(self, foundation: Bundle, provider: Bundle):
        self.foundation = foundation
        self.provider = provider
    
    async def execute_workflow(
        self,
        task: str,
        workflow: list[tuple[str, str, Bundle]]
    ) -> dict[str, Any]:
        """Execute a multi-agent workflow"""
        results = {}
        context = {"task": task}
        
        for agent_name, instruction, agent_bundle in workflow:
            # Compose foundation + agent
            composed = self.foundation.compose(agent_bundle)
            prepared = await composed.prepare()
            
            # Add context from previous agents
            full_instruction = self._format_context(context, results)
            full_instruction += f"\n\n{instruction}"
            
            # Execute
            async with await prepared.create_session() as session:
                result = await session.execute(full_instruction)
                results[agent_name] = result
        
        return results
```

## Parallel Execution Pattern

For **independent tasks**, agents can run in parallel:

```python
# Sequential (one after another)
for agent in agents:
    result = await execute_agent(agent)

# Parallel (all at once)
tasks = [execute_agent(agent) for agent in agents]
results = await asyncio.gather(*tasks)
```

Use parallel when:
- Agents don't depend on each other's outputs
- You want faster overall execution
- Tasks are truly independent

## Agent Configuration Patterns

### Pattern 1: Bundle per Agent

```python
architect = Bundle(name="architect", tools=[...], instruction="...")
implementer = Bundle(name="implementer", tools=[...], instruction="...")
```

### Pattern 2: Agent Files

```
agents/
├── architect.md
├── implementer.md
└── reviewer.md
```

Load from files:
```python
architect = await load_bundle("./agents/architect.md")
```

### Pattern 3: Dynamic Configuration

```python
def create_agent(role: str, tools: list, temperature: float) -> Bundle:
    return Bundle(
        name=role,
        tools=tools,
        providers=[{
            "module": "provider-anthropic",
            "config": {"temperature": temperature}
        }],
        instruction=load_instruction(role)
    )
```

## Related Concepts

- **[Agents](/user_guide/agents.md)** - Agent concepts for end users
- **[Bundle Composition](../concepts.md#composition)** - How bundles merge
- **[Tool Modules](/modules/tools/)** - Available tools for agents
- **[Orchestrators](/modules/orchestrators/)** - Execution strategies
- **[Session API](/api/core/session.md)** - Session management

## Next Steps

- **[Application Guide](/developer_guides/applications/)** - Production patterns
- **[Agents User Guide](/user_guide/agents.md)** - Using agents in CLI
- **[Custom Tool Example](custom_tool.md)** - Build agent-specific tools
