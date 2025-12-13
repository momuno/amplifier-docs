# Hooks API

The Hooks API provides programmatic control over Amplifier's execution flow through event-driven handlers. Hooks execute at specific lifecycle points and return structured results that determine how operations proceed.

**Core Components:**
- **HookRegistry**: Manages hook registration and event emission
- **HookResult**: Structured response that controls execution flow
- **Event System**: Predefined events throughout Amplifier's lifecycle

**Key Capabilities:**

| Capability | Description | Primary Use Cases |
|------------|-------------|-------------------|
| **Observe** | Monitor operations without interference | Logging, metrics, audit trails |
| **Block** | Prevent operations from proceeding | Security validation, policy enforcement |
| **Modify** | Transform event data before processing | Input preprocessing, data enrichment |
| **Inject Context** | Add feedback to agent's conversation | Automated correction, quality feedback |
| **Request Approval** | Ask user for permission | Dynamic policies, high-risk operations |
| **Control Output** | Manage what users see | Clean UX, hide verbose processing |

**Basic Usage Pattern:**

```python
from amplifier_core.hooks import HookRegistry
from amplifier_core.models import HookResult

# Get registry instance
registry = HookRegistry()

# Define handler
async def my_hook(event: str, data: dict) -> HookResult:
    # Hook logic here
    return HookResult(action="continue")

# Register hook
unregister = registry.register("tool:pre", my_hook)

# Later: remove hook
unregister()
```

**Handler Signature:**
All hook handlers must be async functions with the signature:
```python
async def handler(event: str, data: dict[str, Any]) -> HookResult
```

**Execution Flow:**
1. Event occurs in Amplifier (e.g., tool execution)
2. Registry emits event to all registered handlers
3. Handlers execute sequentially by priority (lower = earlier)
4. Each handler returns a `HookResult` indicating desired action
5. Amplifier processes results and continues/modifies/blocks accordingly

**Security Model:**
- All context injections are size-limited and audited
- Hooks can only suppress their own output, not tool output
- Approval gates default to "deny" for security
- Event data should be validated before use

## HookRegistry

The `HookRegistry` class serves as the central coordinator for Amplifier's event-driven hook system. It manages the registration of hook handlers and orchestrates their execution when lifecycle events occur throughout the system.

**Core Responsibilities:**
- **Handler Registration**: Maintains collections of hook handlers organized by event type
- **Priority Management**: Ensures handlers execute in deterministic order based on priority values
- **Event Emission**: Coordinates sequential handler execution with proper error handling
- **Result Processing**: Handles different action types (deny, modify, inject_context, ask_user) appropriately

**Predefined Event Constants:**

| Event Category | Events | Description |
|----------------|---------|-------------|
| **Session** | `SESSION_START`, `SESSION_END` | Session lifecycle management |
| **Prompt** | `PROMPT_SUBMIT` | User input processing |
| **Tool** | `TOOL_PRE`, `TOOL_POST` | Tool execution boundaries |
| **Context** | `CONTEXT_PRE_COMPACT` | Context management operations |
| **Agent** | `AGENT_SPAWN`, `AGENT_COMPLETE` | Agent lifecycle events |
| **Orchestrator** | `ORCHESTRATOR_COMPLETE` | High-level orchestration completion |
| **User** | `USER_NOTIFICATION` | User-facing notifications |
| **Decision** | `DECISION_TOOL_RESOLUTION`, `DECISION_AGENT_RESOLUTION`, `DECISION_CONTEXT_RESOLUTION` | Decision-making events |
| **Error** | `ERROR_TOOL`, `ERROR_PROVIDER`, `ERROR_ORCHESTRATION` | Error handling events |

**Execution Model:**
The registry implements a sequential execution model where handlers run in priority order (lower numbers execute first). Execution follows these rules:

- **Short-circuit on Deny**: If any handler returns `action="deny"`, execution stops immediately
- **Data Chaining**: Handlers returning `action="modify"` can transform data for subsequent handlers
- **Context Injection Merging**: Multiple `inject_context` results are automatically combined
- **Error Isolation**: Handler failures don't prevent other handlers from executing

**Default Field Support:**
The registry supports setting default fields that are automatically merged with all emitted events, useful for session-wide data like user IDs or session identifiers.

```python
# Set defaults that apply to all events
registry.set_default_fields(session_id="abc123", user_id="user456")

# These fields will be included in all subsequent emit() calls
```

**Handler Management:**
Each registered handler is wrapped in a `HookHandler` object that includes the handler function, priority, and optional name for debugging. The registry maintains sorted lists of handlers per event type to ensure consistent execution order.

### Methods

The HookRegistry provides several key methods for managing hook handlers and emitting events. These methods form the core interface for interacting with the hook system, enabling registration of handlers, event emission, and registry management.

| Method | Purpose | Return Type |
|--------|---------|-------------|
| `register()` | Register a hook handler for a specific event with priority | `Callable[[], None]` (unregister function) |
| `on()` | Alias for `register()` method (backwards compatibility) | `Callable[[], None]` (unregister function) |
| `set_default_fields()` | Set default fields merged with all emitted events | `None` |
| `emit()` | Emit an event to all registered handlers with sequential execution | `HookResult` |
| `emit_and_collect()` | Emit event and collect all handler responses with timeout | `list[Any]` |
| `list_handlers()` | List registered handlers for debugging and inspection | `dict[str, list[str]]` |

**Method Categories:**

- **Registration Methods**: `register()` and `on()` for adding handlers to events
- **Configuration Methods**: `set_default_fields()` for setting registry-wide defaults  
- **Emission Methods**: `emit()` for standard event processing and `emit_and_collect()` for response collection
- **Inspection Methods**: `list_handlers()` for debugging and monitoring

**Key Method Characteristics:**

- **Async Support**: Event emission methods are async and work with async handler functions
- **Error Handling**: Methods include comprehensive error handling to prevent handler failures from breaking the system
- **Type Safety**: All methods use proper type hints for better IDE support and runtime validation
- **Logging Integration**: Methods include detailed logging for debugging and monitoring hook execution

The two primary methods you'll use most frequently are `register()` for setting up hooks and `emit()` for triggering them during application lifecycle events.

#### register

Register a hook handler for a specific event with priority-based execution order.

```python
from amplifier_core.hooks import HookRegistry
from amplifier_core.models import HookResult

registry = HookRegistry()

async def my_hook_handler(event: str, data: dict[str, Any]) -> HookResult:
    """Example hook handler that logs tool usage."""
    if event == "tool:pre":
        print(f"About to execute tool: {data.get('tool_name')}")
    return HookResult(action="continue")

# Register the handler
unregister = registry.register(
    event="tool:pre",
    handler=my_hook_handler,
    priority=10,
    name="tool_logger"
)

# Later, remove the handler if needed
unregister()
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `event` | `str` | Yes | - | Event name to hook into (e.g., `"tool:pre"`, `"session:start"`) |
| `handler` | `Callable[[str, dict], Awaitable[HookResult]]` | Yes | - | Async function that processes the event |
| `priority` | `int` | No | `0` | Execution order (lower numbers execute first) |
| `name` | `str \| None` | No | `handler.__name__` | Handler identifier for debugging |

**Handler Function Signature:**
The handler function must accept two parameters and return a `HookResult`:
- `event: str` - The event name that triggered the handler
- `data: dict[str, Any]` - Event-specific data dictionary

**Return Value:**
Returns an unregister function (`Callable[[], None]`) that removes the handler from the registry when called.

**Priority Ordering:**
Handlers execute sequentially by priority value. Lower numbers have higher priority:

```python
# This handler runs first (priority 0)
registry.register("tool:pre", first_handler, priority=0)

# This handler runs second (priority 10) 
registry.register("tool:pre", second_handler, priority=10)

# This handler runs third (priority 20)
registry.register("tool:pre", third_handler, priority=20)
```

**Registration Behavior:**
- Handlers are automatically sorted by priority when registered
- Multiple handlers can have the same priority (execution order undefined within same priority)
- Handler names default to the function's `__name__` attribute if not specified
- Registration is logged at debug level for troubleshooting

**Unregistration:**
The returned unregister function safely removes the handler and logs the removal:

```python
unregister = registry.register("tool:post", my_handler)

# Remove handler when no longer needed
unregister()  # Logs: "Unregistered hook 'my_handler' from event 'tool:post'"
```

#### emit

Emit an event to all registered handlers with sequential execution and data modification chaining.

```python
from amplifier_core.hooks import HookRegistry
from amplifier_core.models import HookResult

registry = HookRegistry()

# Register some handlers first
async def validation_handler(event: str, data: dict) -> HookResult:
    if not data.get("tool_name"):
        return HookResult(action="deny", reason="Tool name required")
    return HookResult(action="continue")

async def enrichment_handler(event: str, data: dict) -> HookResult:
    # Modify data by adding metadata
    enriched_data = {**data, "timestamp": "2024-01-01T10:00:00Z"}
    return HookResult(action="modify", data=enriched_data)

registry.register("tool:pre", validation_handler, priority=0)
registry.register("tool:pre", enrichment_handler, priority=10)

# Emit the event
result = await registry.emit("tool:pre", {
    "tool_name": "calculator",
    "args": {"expression": "2 + 2"}
})

print(result.action)  # "continue"
print(result.data)    # Includes timestamp from enrichment_handler
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event` | `str` | Yes | Event name to emit (e.g., `"tool:pre"`, `"session:start"`) |
| `data` | `dict[str, Any]` | Yes | Event data dictionary that handlers can read and modify |

**Return Value:**
Returns a `HookResult` object containing the final state after all handlers execute:
- `action`: Final action from handlers (`"continue"`, `"deny"`, `"inject_context"`, or `"ask_user"`)
- `data`: Event data, potentially modified by handlers with `"modify"` actions
- Additional fields based on the final action type

**Execution Flow:**
Handlers execute sequentially by priority with specific behaviors:

1. **Short-circuit on deny**: If any handler returns `action="deny"`, execution stops immediately and returns the denial
2. **Data modification chaining**: Handlers with `action="modify"` update the data for subsequent handlers
3. **Special action preservation**: `inject_context` and `ask_user` actions are preserved and returned as the final result
4. **Error resilience**: Handler exceptions are logged but don't stop execution of remaining handlers

**Default Field Merging:**
Event data is automatically merged with default fields set via `set_default_fields()`:

```python
registry.set_default_fields(session_id="abc123", user_id="user456")

# Emitted data automatically includes defaults
result = await registry.emit("tool:pre", {"tool_name": "calculator"})
# result.data contains: {"session_id": "abc123", "user_id": "user456", "tool_name": "calculator"}
```

**Special Action Handling:**
- **Multiple `inject_context`**: Results are automatically merged into a single context injection
- **Multiple `ask_user`**: Only the first ask_user result is preserved (approvals cannot be merged)
- **Priority matters**: Special actions from higher-priority handlers take precedence

**No Handlers Behavior:**
If no handlers are registered for an event, `emit()` returns a default continue result:

```python
result = await registry.emit("unknown:event", {"data": "value"})
# Returns: HookResult(action="continue", data={"data": "value"})
```

## HookResult

`HookResult` is the data structure returned by hook handlers to control execution flow and orchestrate system behavior. It provides a unified interface for handlers to communicate their decisions back to the hook system, enabling sophisticated control patterns like operation blocking, data transformation, context injection, and user approval workflows.

The result object encapsulates both the action to take (`continue`, `deny`, `modify`, `inject_context`, `ask_user`) and any associated data or configuration needed to execute that action. This design allows handlers to remain focused on their specific logic while delegating execution control to the orchestrator.

**Key Capabilities:**
- **Flow Control**: Continue, block, or modify operations based on validation logic
- **Data Transformation**: Chain modifications through multiple handlers 
- **Context Injection**: Provide real-time feedback to the agent for immediate correction
- **Approval Gates**: Request user permission for sensitive operations
- **Output Management**: Control what users see vs. what gets logged

**Class Definition:**
```python
from amplifier_core.models import HookResult

class HookResult(BaseModel):
    # Core action (required)
    action: Literal["continue", "deny", "modify", "inject_context", "ask_user"]
    
    # Data and reasoning
    data: dict[str, Any] | None = None
    reason: str | None = None
    
    # Context injection fields
    context_injection: str | None = None
    context_injection_role: Literal["system", "user", "assistant"] = "system"
    ephemeral: bool = False
    
    # Approval workflow fields
    approval_prompt: str | None = None
    approval_options: list[str] | None = None
    approval_timeout: float = 300.0
    approval_default: Literal["allow", "deny"] = "deny"
    
    # Output control fields
    suppress_output: bool = False
    user_message: str | None = None
    user_message_level: Literal["info", "warning", "error"] = "info"
```

**Execution Behavior:**
When multiple handlers return different actions, the hook system applies precedence rules: `deny` actions short-circuit immediately, `modify` actions chain data through subsequent handlers, and special actions like `inject_context` and `ask_user` are preserved as the final result. This enables complex workflows where validation, transformation, and feedback injection can all occur in a single event emission.

### Actions

| Action | Description |
|--------|-------------|
| `continue` | Proceed with operation normally. Default action when no intervention is needed. |
| `deny` | Block the operation from proceeding. Used for validation failures, security violations, or policy enforcement. |
| `modify` | Transform the event data before continuing. Changes are passed to subsequent handlers in the chain. |
| `inject_context` | Add content to the agent's conversation context. Enables real-time feedback and correction loops. |
| `ask_user` | Request user approval before proceeding. Creates an interactive approval gate for sensitive operations. |

**Action Precedence:** When multiple handlers return different actions, `deny` takes highest precedence (immediately blocks), followed by `ask_user` and `inject_context` (preserved as final result), then `modify` (data chains through handlers), with `continue` as the default fallback.

### Fields

```python
from amplifier_core.models import HookResult

@dataclass
class HookResult:
    # Core action (required)
    action: Literal["continue", "deny", "modify", "inject_context", "ask_user"]
    
    # Data and reasoning
    data: dict[str, Any] | None = None
    reason: str | None = None
    
    # Context injection fields
    context_injection: str | None = None
    context_injection_role: Literal["system", "user", "assistant"] = "system"
    ephemeral: bool = False
    
    # Approval workflow fields
    approval_prompt: str | None = None
    approval_options: list[str] | None = None
    approval_timeout: float = 300.0
    approval_default: Literal["allow", "deny"] = "deny"
    
    # Output control fields
    suppress_output: bool = False
    user_message: str | None = None
    user_message_level: Literal["info", "warning", "error"] = "info"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| **`action`** | `Literal["continue", "deny", "modify", "inject_context", "ask_user"]` | *required* | Action to take after hook execution |
| **`data`** | `dict[str, Any] \| None` | `None` | Modified event data for `action="modify"`. Changes chain through subsequent handlers |
| **`reason`** | `str \| None` | `None` | Explanation for deny/modification actions. Shown to agent when operation is blocked |
| **`context_injection`** | `str \| None` | `None` | Text to inject into agent's conversation context. Size-limited (default 10 KB) and audited |
| **`context_injection_role`** | `Literal["system", "user", "assistant"]` | `"system"` | Role for injected message. Use `"system"` for environmental feedback |
| **`ephemeral`** | `bool` | `False` | If `True`, injection is temporary (current LLM call only, not stored in history) |
| **`approval_prompt`** | `str \| None` | `None` | Question to ask user for `action="ask_user"`. Should clearly explain the operation |
| **`approval_options`** | `list[str] \| None` | `None` | User choice options. Defaults to `["Allow", "Deny"]` if not specified |
| **`approval_timeout`** | `float` | `300.0` | Seconds to wait for user response. Uses `approval_default` on timeout |
| **`approval_default`** | `Literal["allow", "deny"]` | `"deny"` | Default decision on timeout or error. `"deny"` is safer for security-sensitive operations |
| **`suppress_output`** | `bool` | `False` | Hide hook's stdout/stderr from user transcript. Only affects hook's own output |
| **`user_message`** | `str \| None` | `None` | Message to display to user (separate from context injection). For alerts and status updates |
| **`user_message_level`** | `Literal["info", "warning", "error"]` | `"info"` | Severity level for user message display |

**Field Grouping by Purpose:**
- **Core Control**: `action`, `data`, `reason` - Basic flow control and data transformation
- **Context Injection**: `context_injection`, `context_injection_role`, `ephemeral` - Agent feedback and correction loops  
- **Approval Gates**: `approval_prompt`, `approval_options`, `approval_timeout`, `approval_default` - Interactive permission control
- **Output Management**: `suppress_output`, `user_message`, `user_message_level` - User experience and visibility control

### Examples

This section demonstrates common `HookResult` usage patterns through practical examples. Each pattern shows how to construct `HookResult` objects for different scenarios, from simple observation to complex approval workflows.

The examples below illustrate the four primary actions available in the hook system. Each example includes the complete `HookResult` construction with relevant fields and explains when to use that pattern.

**Pattern Categories:**
- **Observation**: Monitor operations without interference
- **Blocking**: Prevent operations based on validation or security rules  
- **Feedback Injection**: Provide automated correction and guidance to the agent
- **Interactive Control**: Request user approval for sensitive operations

All examples assume you're working within a hook handler function with this signature:

```python
async def hook_handler(event: str, data: dict[str, Any]) -> HookResult:
    # Your hook logic here
    pass
```

The `data` parameter contains event-specific information (tool inputs, results, session state) that your hook can inspect and potentially modify. See the [Events Reference](./HOOKS_EVENTS.md) for complete data schemas for each event type.

#### Continue (observe only)

For observation-only hooks that monitor operations without interfering, return a simple `HookResult` with `action="continue"`:

```python
async def audit_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Log tool usage for audit trail."""
    tool_name = data.get("tool_name", "unknown")
    user_id = data.get("session", {}).get("user_id", "anonymous")
    
    # Log the operation
    logger.info(f"Tool {tool_name} used by {user_id}")
    
    # Continue without interference
    return HookResult(action="continue")
```

This pattern is ideal for logging, metrics collection, audit trails, and monitoring without affecting the operation flow. The hook executes its observation logic then allows normal processing to continue unchanged.

#### Deny operation

To block an operation, return `HookResult` with `action="deny"`. Include a clear `reason` to explain why the operation was blocked:

```python
async def security_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Block access to sensitive files."""
    file_path = data.get("tool_input", {}).get("file_path", "")
    
    if file_path.endswith((".env", ".key", ".pem")):
        return HookResult(
            action="deny",
            reason=f"Access denied: {file_path} contains sensitive data"
        )
    
    return HookResult(action="continue")
```

When a hook returns `action="deny"`, the operation stops immediately and the agent receives the `reason` message. This pattern is essential for security validation, access control, and preventing dangerous operations before they execute.

#### Inject context to agent

To inject feedback into the agent's context, return `HookResult` with `action="inject_context"`. The agent receives this feedback immediately and can respond to it within the same turn:

```python
async def validation_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Inject validation feedback to agent."""
    issues = validate_output(data.get("tool_result"))
    
    if issues:
        return HookResult(
            action="inject_context",
            context_injection=f"Validation errors found:\n{format_issues(issues)}",
            user_message="Found validation issues"
        )
    
    return HookResult(action="continue")
```

The `context_injection` field contains the feedback text that gets added to the agent's conversation context. This enables automated correction loops where the agent can immediately fix issues without waiting for the next user turn.

Key fields for context injection:

| Field | Purpose | Default |
|-------|---------|---------|
| `context_injection` | Feedback text for the agent | Required |
| `context_injection_role` | Message role (`"system"`, `"user"`, `"assistant"`) | `"system"` |
| `ephemeral` | Temporary injection (not stored in history) | `False` |
| `user_message` | Separate message shown to user | `None` |

Use `context_injection_role="system"` for environmental feedback (recommended), `"user"` to simulate user input, or `"assistant"` for agent self-talk. Set `ephemeral=True` for temporary state like todo reminders that update frequently.

This pattern is ideal for linting feedback, validation errors, constraint violations, and any automated guidance that helps the agent self-correct during execution.

#### Request approval

To request user approval for an operation, return `HookResult` with `action="ask_user"`. This creates an approval gate where the user must explicitly permit the operation to proceed:

```python
async def production_protection_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Require user approval for production file writes."""
    file_path = data["tool_input"]["file_path"]
    
    if "/production/" in file_path or file_path.endswith(".env"):
        return HookResult(
            action="ask_user",
            approval_prompt=f"Allow write to production file: {file_path}?",
            approval_options=["Allow once", "Allow always", "Deny"],
            approval_timeout=300.0,
            approval_default="deny"
        )
    
    return HookResult(action="continue")
```

The approval system presents the `approval_prompt` to the user and waits for their response. If no response is received within `approval_timeout` seconds (default 5 minutes), the `approval_default` action is taken. Setting `approval_default="deny"` provides safer behavior for security-sensitive operations.

Key approval fields:

| Field | Purpose | Default |
|-------|---------|---------|
| `approval_prompt` | Question to ask the user | Required |
| `approval_options` | Available choices | `["Allow", "Deny"]` |
| `approval_timeout` | Seconds to wait for response | `300.0` |
| `approval_default` | Action on timeout | `"deny"` |

The `approval_options` can include flexible choices like `"Allow once"`, `"Allow always"`, and `"Deny"` to give users granular control over permissions. This pattern is essential for production deployments, cost controls, and any high-risk operations that require explicit human oversight.