# Hooks API

The Hooks API provides a powerful event-driven system for extending Amplifier's behavior at key lifecycle points. The system consists of two core components:

**HookRegistry** - The central registry that manages hook registration and event emission. It handles the execution of hooks in priority order, supports data modification chaining, and provides deterministic behavior with proper error handling.

**HookResult** - The response object returned by hook handlers that controls execution flow. It supports five primary actions (`continue`, `deny`, `modify`, `inject_context`, `ask_user`) along with rich configuration options for context injection, approval gates, and output control.

Key capabilities include:

- **Event Interception** - Hook into 15+ lifecycle events including tool execution, session management, and error handling
- **Flow Control** - Block operations, modify event data, or request user approval
- **Context Injection** - Add feedback directly to the agent's conversation for immediate correction
- **Output Management** - Control what users see with custom messages and output suppression
- **Priority Ordering** - Execute multiple hooks in deterministic order with data chaining

The system is designed for safety-first operation with secure defaults, automatic error recovery, and comprehensive logging. Hooks execute asynchronously without blocking the main execution flow unless explicitly designed to do so.

## HookRegistry

The `HookRegistry` class serves as the central orchestrator for Amplifier's event-driven hook system. It manages the registration, execution, and lifecycle of hook handlers across all framework events.

**Source:** [`amplifier_core/hooks.py`](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/hooks.py)

The registry operates on a priority-based execution model where hooks are executed sequentially in deterministic order. Lower priority numbers execute first, allowing fine-grained control over execution flow. The system supports data modification chaining, where each hook can transform event data that flows to subsequent hooks.

Key operational characteristics:

- **Sequential Execution** - Hooks run one after another, not concurrently
- **Short-Circuit Logic** - Execution stops immediately on `deny` actions
- **Data Chaining** - Modified data flows through the hook chain
- **Error Isolation** - Individual hook failures don't break the chain
- **Response Collection** - Special methods gather responses for decision-making

The registry maintains separate handler lists for each event type, automatically sorting them by priority when registered. It provides both fire-and-forget emission (`emit`) and response collection (`emit_and_collect`) patterns to support different integration needs.

```python
# Basic registry usage
registry = HookRegistry()

# Register a hook with priority
unregister = registry.register(
    event=HookRegistry.TOOL_PRE,
    handler=my_validation_hook,
    priority=10,
    name="input_validator"
)

# Emit event and handle result
result = await registry.emit("tool:pre", {"tool": "calculator", "args": {}})
if result.action == "deny":
    print(f"Tool blocked: {result.reason}")
```

### Methods

The `HookRegistry` provides five core methods for managing the complete lifecycle of hook handlers. These methods handle registration, event emission, response collection, configuration, and introspection of the hook system.

**Available Methods:**

| Method | Purpose | Return Type |
|--------|---------|-------------|
| `register()` | Register a new hook handler with priority and optional naming | `Callable[[], None]` (unregister function) |
| `emit()` | Fire an event to all handlers with data chaining and flow control | `HookResult` |
| `emit_and_collect()` | Emit event and collect all handler responses for decision-making | `list[Any]` |
| `set_default_fields()` | Configure default data fields merged into all emitted events | `None` |
| `list_handlers()` | Inspect registered handlers for debugging and monitoring | `dict[str, list[str]]` |

The methods follow two primary patterns: **registration methods** (`register`, `set_default_fields`) for setup and configuration, and **execution methods** (`emit`, `emit_and_collect`) for runtime event handling. The `list_handlers` method provides introspection capabilities for debugging and system monitoring.

All methods are designed to work together seamlessly - handlers registered via `register()` automatically receive default fields from `set_default_fields()` when events are emitted through `emit()` or `emit_and_collect()`.

```python
# Typical method usage flow
registry = HookRegistry()

# 1. Configure defaults
registry.set_default_fields(session_id="abc123", user_id="user456")

# 2. Register handlers
unregister_fn = registry.register(
    event=HookRegistry.TOOL_PRE,
    handler=my_hook,
    priority=5
)

# 3. Emit events (includes defaults automatically)
result = await registry.emit("tool:pre", {"tool_name": "calculator"})

# 4. Inspect system state
handlers = registry.list_handlers("tool:pre")
```

#### register

Registers a hook handler for a specific event with priority-based execution control. Returns an unregister function for cleanup.

```python
unregister = registry.register(
    event: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[HookResult]],
    priority: int = 0,
    name: str | None = None
) -> Callable[[], None]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str` | Required | Event name to hook into (e.g., `"tool:pre"`, `"session:start"`) |
| `handler` | `Callable[[str, dict], Awaitable[HookResult]]` | Required | Async function that processes the event |
| `priority` | `int` | `0` | Execution order (lower numbers execute first) |
| `name` | `str \| None` | `None` | Handler identifier for debugging (defaults to `handler.__name__`) |

**Returns:** `Callable[[], None]` - Function to unregister this handler

**Handler Signature:** `async def handler(event: str, data: dict[str, Any]) -> HookResult`

```python
async def security_check(event: str, data: dict[str, Any]) -> HookResult:
    """Block dangerous file operations."""
    if data.get("tool_name") == "Write" and "/etc/" in data.get("file_path", ""):
        return HookResult(action="deny", reason="System files are protected")
    return HookResult(action="continue")

# Register with high priority (executes early)
unregister = registry.register(
    event=HookRegistry.TOOL_PRE,
    handler=security_check,
    priority=1,
    name="file_security"
)

# Later: remove the handler
unregister()
```

**Execution Behavior:**

Handlers execute sequentially by priority order (ascending). The registry maintains sorted handler lists and automatically logs registration/unregistration events. Each handler receives the current event data, which may have been modified by earlier handlers in the chain.

**Note:** The `on()` method is an alias for `register()` provided for backwards compatibility.

#### emit

Emits an event to all registered handlers with sequential execution, data chaining, and flow control. Handlers execute by priority order with short-circuit logic on deny actions.

```python
result = await registry.emit(
    event: str,
    data: dict[str, Any]
) -> HookResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `str` | Event name to emit (e.g., `"tool:pre"`, `"session:start"`) |
| `data` | `dict[str, Any]` | Event data passed to handlers (may be modified during execution) |

**Returns:** `HookResult` - Final result after all handlers complete or early termination

```python
# Emit tool validation event
result = await registry.emit("tool:pre", {
    "tool_name": "calculator", 
    "args": {"expression": "2+2"}
})

if result.action == "deny":
    raise PermissionError(result.reason)
elif result.action == "modify":
    # Use modified data from handlers
    updated_args = result.data["args"]
```

**Execution Behavior:**

The method processes handlers sequentially in priority order with sophisticated flow control. Default fields configured via `set_default_fields()` are automatically merged with event data, with explicit event data taking precedence.

**Flow Control Logic:**
- **Deny Actions** - Execution stops immediately and returns the deny result
- **Modify Actions** - Data is updated and flows to subsequent handlers  
- **Inject Context Actions** - Multiple injections are merged into a single result
- **Ask User Actions** - First ask_user result is preserved (cannot merge user prompts)
- **Continue Actions** - Execution proceeds to next handler

**Error Handling:** Individual handler failures are logged but don't break the execution chain. The method continues processing remaining handlers even if some throw exceptions.

**Special Action Merging:** When multiple handlers return `inject_context` actions, their context injections are combined with double newlines while preserving the first handler's role and formatting settings.

#### emit_and_collect

Emits an event to all registered handlers and collects their responses for decision-making processes. Unlike `emit()` which processes handlers sequentially with flow control, this method gathers all handler outputs for aggregation and analysis.

```python
responses = await registry.emit_and_collect(
    event: str,
    data: dict[str, Any],
    timeout: float = 1.0
) -> list[Any]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str` | Required | Event name to emit (e.g., `"decision:tool_resolution"`) |
| `data` | `dict[str, Any]` | Required | Event data passed to all handlers |
| `timeout` | `float` | `1.0` | Maximum seconds to wait for each handler response |

**Returns:** `list[Any]` - List of non-None `HookResult.data` values from all handlers

```python
# Collect tool recommendations from multiple handlers
responses = await registry.emit_and_collect(
    "decision:tool_resolution", 
    {"user_query": "What's the weather?", "available_tools": ["weather", "web"]},
    timeout=2.0
)

# Aggregate responses for decision making
tool_votes = [r.get("recommended_tool") for r in responses if r.get("recommended_tool")]
selected_tool = max(set(tool_votes), key=tool_votes.count)  # Most popular choice
```

**Execution Behavior:**

All handlers execute concurrently with individual timeout protection. The method collects only the `data` field from `HookResult` objects, filtering out `None` values. Handler failures and timeouts are logged but don't affect other handlers or break the collection process.

This method is specifically designed for decision events where multiple handlers provide input (votes, recommendations, scores) that need to be aggregated using reduction algorithms like voting, averaging, or consensus building.

#### set_default_fields

Configures default fields that are automatically merged into all emitted events. These defaults provide consistent context (like session IDs or user information) across all hook executions without requiring explicit inclusion in each emit call.

```python
registry.set_default_fields(**defaults) -> None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `**defaults` | `dict[str, Any]` | Key-value pairs to include in all future event emissions |

**Returns:** `None`

```python
# Set session context for all events
registry.set_default_fields(
    session_id="sess_123",
    user_id="user_456",
    environment="production"
)

# Later emissions automatically include defaults
await registry.emit("tool:pre", {"tool_name": "calculator"})
# Handler receives: {"session_id": "sess_123", "user_id": "user_456", 
#                   "environment": "production", "tool_name": "calculator"}
```

**Execution Behavior:**

Default fields are merged with event data during `emit()` calls using dictionary unpacking with explicit event data taking precedence. This means if an event explicitly provides a field that exists in defaults, the event's value overwrites the default value.

The defaults persist for the lifetime of the registry instance and apply to all subsequent emissions. Setting new defaults completely replaces the previous default set rather than merging with existing defaults.

#### list_handlers

Provides introspection capabilities to examine registered handlers across events. This method enables debugging, monitoring, and dynamic analysis of the hook system's current state.

```python
handlers = registry.list_handlers(event: str | None = None) -> dict[str, list[str]]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str \| None` | `None` | Optional event name to filter results. If `None`, returns all events |

**Returns:** `dict[str, list[str]]` - Dictionary mapping event names to lists of handler names

```python
# List all registered handlers
all_handlers = registry.list_handlers()
# Returns: {"tool:pre": ["validator", "logger"], "session:start": ["auth_check"]}

# List handlers for specific event
tool_handlers = registry.list_handlers("tool:pre")
# Returns: {"tool:pre": ["validator", "logger"]}

# Check if event has handlers
if "custom:event" in registry.list_handlers():
    print("Custom event has registered handlers")
```

**Execution Behavior:**

The method returns only handlers that have explicit names (either provided during registration or derived from the function's `__name__` attribute). Anonymous handlers or those with `None` names are excluded from the results. When filtering by a specific event, the method returns a single-key dictionary for consistency, even if no handlers are found (empty list value). This introspection capability is particularly useful for debugging hook registration issues and verifying that expected handlers are properly attached to lifecycle events.

### Hook Handler

Hook handlers are async functions that process lifecycle events and return structured results to control execution flow. The registry expects a specific signature and return type for all registered handlers.

**Handler Signature:**

```python
async def handler(event: str, data: dict[str, Any]) -> HookResult:
    # Process event and data
    return HookResult(action="continue")
```

**Parameters Received:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `str` | The event name that triggered this handler (e.g., `"tool:pre"`) |
| `data` | `dict[str, Any]` | Event data merged with any default fields from the registry |

**Return Value:** Must return a `HookResult` object with an `action` field that determines how execution continues. Invalid return types are logged as warnings and ignored.

**Implementation Requirements:**

- **Async Function**: All handlers must be `async def` functions that can be awaited
- **Exception Safety**: Handlers should handle their own exceptions; uncaught exceptions are logged but don't break the hook chain
- **Timeout Awareness**: For `emit_and_collect()`, handlers should complete within the specified timeout (default 1 second)
- **Stateless Design**: Handlers receive all necessary context through the `data` parameter and should not rely on external state

**Example Implementation:**

```python
async def security_validator(event: str, data: dict[str, Any]) -> HookResult:
    if event == "tool:pre" and data.get("tool_name") == "file_system":
        if not data.get("user_authorized"):
            return HookResult(action="deny", reason="Unauthorized file access")
    
    return HookResult(action="continue")

# Register the handler
registry.register("tool:pre", security_validator, priority=10)
```

The handler receives the exact event name that was emitted, allowing a single handler function to process multiple event types with conditional logic. The `data` dictionary contains both the explicit event data and any default fields configured on the registry, with explicit data taking precedence over defaults.

### Standard Events

The `HookRegistry` class defines standard event constants as class attributes, providing a stable interface for common lifecycle events. These constants are organized into three categories based on their purpose in the system.

**Lifecycle Events**

| Constant | String Value | Description |
|----------|--------------|-------------|
| `SESSION_START` | `"session:start"` | Emitted when a new session begins |
| `SESSION_END` | `"session:end"` | Emitted when a session terminates |
| `PROMPT_SUBMIT` | `"prompt:submit"` | Emitted when user submits a prompt |
| `TOOL_PRE` | `"tool:pre"` | Emitted before tool execution |
| `TOOL_POST` | `"tool:post"` | Emitted after tool execution completes |
| `CONTEXT_PRE_COMPACT` | `"context:pre-compact"` | Emitted before context compaction |
| `AGENT_SPAWN` | `"agent:spawn"` | Emitted when an agent is created |
| `AGENT_COMPLETE` | `"agent:complete"` | Emitted when an agent completes |
| `ORCHESTRATOR_COMPLETE` | `"orchestrator:complete"` | Emitted when orchestration finishes |
| `USER_NOTIFICATION` | `"user:notification"` | Emitted for user notifications |

**Decision Events**

| Constant | String Value | Description |
|----------|--------------|-------------|
| `DECISION_TOOL_RESOLUTION` | `"decision:tool_resolution"` | Emitted for tool selection decisions |
| `DECISION_AGENT_RESOLUTION` | `"decision:agent_resolution"` | Emitted for agent selection decisions |
| `DECISION_CONTEXT_RESOLUTION` | `"decision:context_resolution"` | Emitted for context management decisions |

**Error Events**

| Constant | String Value | Description |
|----------|--------------|-------------|
| `ERROR_TOOL` | `"error:tool"` | Emitted when tool execution fails |
| `ERROR_PROVIDER` | `"error:provider"` | Emitted when provider calls fail |
| `ERROR_ORCHESTRATION` | `"error:orchestration"` | Emitted when orchestration fails |

**Usage Example:**

```python
from amplifier_core.hooks import HookRegistry
from amplifier_core.models import HookResult

registry = HookRegistry()

# Register handler using standard event constants
async def tool_logger(event: str, data: dict[str, Any]) -> HookResult:
    print(f"Tool {data.get('tool_name')} is executing")
    return HookResult(action="continue")

# Use class constants for type safety and consistency
registry.register(HookRegistry.TOOL_PRE, tool_logger)

# Emit events using the same constants
await registry.emit(HookRegistry.TOOL_PRE, {"tool_name": "calculator"})

# Register multiple related events
error_handler = lambda event, data: HookResult(action="continue")
registry.register(HookRegistry.ERROR_TOOL, error_handler)
registry.register(HookRegistry.ERROR_PROVIDER, error_handler)
```

Using these predefined constants ensures consistency across the codebase and provides IDE autocompletion support. The constants can be used both for registration and emission, reducing the risk of typos in event names.

**Note:** This section documents the core lifecycle events defined in HookRegistry. For the complete canonical event taxonomy including streaming events (content_block:*, thinking:*), provider events, approval events, and other specialized events, see [amplifier_core/events.py](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/events.py).

## HookResult

The `HookResult` class is the standardized return type for all hook handlers, defining how the hook system should respond to each event. Every hook handler must return a `HookResult` instance that specifies an action (continue, deny, modify, etc.) and any associated data or context modifications.

**Source:** [amplifier_core/models.py](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/models.py)

`HookResult` serves as the communication mechanism between hook handlers and the registry, enabling handlers to:

- **Observe events** by returning `continue` actions
- **Block operations** by returning `deny` actions with reasons
- **Transform data** by returning `modify` actions with updated data
- **Inject context** into agent conversations with specialized fields
- **Request approvals** through interactive approval gates
- **Control output** with suppression and formatting options

The class uses a discriminated union pattern where the `action` field determines which additional fields are relevant. This design ensures type safety while supporting the diverse range of hook behaviors needed across the system's lifecycle events.

```python
from amplifier_core.models import HookResult

# Simple observation - most common case
result = HookResult(action="continue")

# Block an operation with explanation
result = HookResult(action="deny", reason="Security policy violation")

# Modify event data as it flows through handlers
result = HookResult(action="modify", data={"user_id": "authenticated_user"})
```

The hook registry processes `HookResult` objects sequentially by priority, with certain actions like `deny` short-circuiting execution and others like `inject_context` being merged when multiple handlers return them for the same event.

### Actions

The `action` field determines how the hook system responds to an event. Each action type enables different behaviors, from simple observation to complex approval workflows.

| Action | Behavior | Use Case | Effect on Execution |
|--------|----------|----------|-------------------|
| `continue` | Proceed normally with operation | Default action, logging, metrics | No interruption |
| `deny` | Block operation from proceeding | Security violations, validation failures | Short-circuits handler chain |
| `modify` | Transform event data before next handler | Data enrichment, preprocessing | Chains modified data through remaining handlers |
| `inject_context` | Add content to agent's conversation | Automated feedback, error correction | Agent sees injected content in next response |
| `ask_user` | Request user approval before proceeding | Dynamic permissions, high-risk operations | Pauses execution until user responds |

**Sequential Processing:** Handlers execute by priority order. `deny` actions immediately stop processing, while `modify` actions chain data changes through subsequent handlers. Multiple `inject_context` actions from different handlers are merged together.

```python
# Block a dangerous operation
if "/etc/passwd" in file_path:
    return HookResult(action="deny", reason="System file access forbidden")

# Inject linter feedback to agent
if linter_errors:
    return HookResult(
        action="inject_context",
        context_injection=f"Fix these issues:\n{linter_errors}"
    )

# Request approval for production changes
return HookResult(action="ask_user", approval_prompt="Deploy to production?")
```

### Fields

The `HookResult` class contains 14 fields organized into four logical groups based on functionality. All fields are optional with sensible defaults, allowing handlers to specify only the fields relevant to their chosen action.

**Field Organization:**

| Group | Purpose | Key Fields | Primary Actions |
|-------|---------|------------|-----------------|
| **Core** | Basic hook behavior | `action`, `data`, `reason` | All actions |
| **Context Injection** | Agent conversation control | `context_injection`, `ephemeral` | `inject_context` |
| **Approval Gates** | User permission requests | `approval_prompt`, `approval_options` | `ask_user` |
| **Output Control** | UI and display management | `suppress_output`, `user_message` | Any action |

**Field Validation:** Pydantic automatically validates field types and constraints. Invalid combinations (like setting `approval_prompt` without `action="ask_user"`) are allowed at the model level but ignored by the hook registry during processing.

**Default Behavior:** Most fields default to `None` or `False`, making the minimal case (`HookResult()`) equivalent to `HookResult(action="continue")`. This design prioritizes simplicity for common observation use cases while supporting complex workflows when needed.

```python
# Minimal - uses all defaults
return HookResult()

# Complex - multiple field groups
return HookResult(
    action="inject_context",
    context_injection="Build failed: missing dependency",
    context_injection_role="system",
    user_message="Build process encountered errors",
    user_message_level="error",
    suppress_output=True
)
```

The fields are designed to work independently, allowing handlers to mix capabilities (e.g., inject context while also displaying a user message) without conflicts.

#### Core Fields

The three core fields form the foundation of every `HookResult`, providing the essential information needed for basic hook operations. These fields work together to define what action to take, how to modify data, and why an operation was blocked.

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `action` | `Literal["continue", "deny", "modify", "inject_context", "ask_user"]` | `"continue"` | Determines how the hook system responds to the event |
| `data` | `dict[str, Any] \| None` | `None` | Modified event data that chains through subsequent handlers |
| `reason` | `str \| None` | `None` | Human-readable explanation for deny actions or modifications |

**Action Field:** Controls the fundamental behavior of the hook result. The default `"continue"` action allows normal processing to proceed, making it the implicit choice for observation-only hooks. Other actions enable increasingly sophisticated behaviors:

```python
# Default behavior - observe without interference
HookResult()  # action="continue" by default

# Block operation with explanation
HookResult(action="deny", reason="File size exceeds 10MB limit")

# Transform data for next handler
HookResult(action="modify", data={"sanitized": True, "original_path": path})
```

**Data Field:** Contains the modified event data when using `action="modify"`. The hook registry passes this modified data to subsequent handlers in the chain, enabling data transformation pipelines. Only relevant for modify actions - ignored for other action types:

```python
# Add metadata to file operation
return HookResult(
    action="modify",
    data={
        **original_event_data,
        "timestamp": datetime.now().isoformat(),
        "validated": True
    }
)
```

**Reason Field:** Provides context for deny actions and modifications. The agent sees this explanation when operations are blocked, helping with debugging and user understanding. While optional, it's strongly recommended for deny actions:

```python
# Good - explains why operation was blocked
HookResult(action="deny", reason="Production deployments require approval")

# Poor - no context for the denial
HookResult(action="deny")  # Agent won't understand why
```

**Field Interactions:** The core fields work together to create a complete response. The `action` determines which fields are meaningful - `data` only matters for modify actions, while `reason` is most important for deny actions but can provide context for any action type.

#### Context Injection Fields

Context injection fields enable hooks to participate directly in the agent's conversation by adding messages to the context. These four fields work together to control what content is injected, how it appears, and where it's placed in the conversation flow.

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `context_injection` | `str \| None` | `None` | Text content to inject into agent's conversation context |
| `context_injection_role` | `Literal["system", "user", "assistant"]` | `"system"` | Role for the injected message in conversation |
| `ephemeral` | `bool` | `False` | Whether injection is temporary (current call only) vs stored in history |
| `append_to_last_tool_result` | `bool` | `False` | Append to last tool result instead of creating new message |

**Context Injection Content:** The `context_injection` field contains the actual text that gets added to the agent's conversation. This content becomes visible to the agent and can influence its responses, enabling automated feedback loops. The injection is unlimited by default (configurable via `session.injection_size_limit`) and gets audited with provenance metadata:

```python
# Inject linter feedback for immediate fixing
HookResult(
    action="inject_context",
    context_injection="Linter found 3 errors:\n- Line 42: Line too long\n- Line 55: Unused import\n- Line 67: Missing docstring"
)

# Inject build status information
HookResult(
    action="inject_context", 
    context_injection="Build completed successfully. 15 tests passed, 0 failed."
)
```

**Message Role:** The `context_injection_role` field determines how the injected content appears in the conversation. The default `"system"` role is recommended for most use cases as it represents environmental feedback. The `"user"` role simulates user input, while `"assistant"` creates agent self-talk:

```python
# System role (default) - environmental feedback
HookResult(
    action="inject_context",
    context_injection="File saved to /tmp/output.txt",
    context_injection_role="system"  # Can omit - this is default
)

# User role - simulate user providing information
HookResult(
    action="inject_context", 
    context_injection="The API key is in the .env file",
    context_injection_role="user"
)

# Assistant role - agent thinking out loud
HookResult(
    action="inject_context",
    context_injection="I should check the logs before proceeding",
    context_injection_role="assistant"
)
```

**Persistence Control:** The `ephemeral` field controls whether injected content persists in conversation history. When `False` (default), injections are stored permanently. When `True`, content appears only for the current LLM call, making it suitable for frequently-changing state like todo reminders:

```python
# Persistent injection - stored in conversation history
HookResult(
    action="inject_context",
    context_injection="Error: Database connection failed",
    ephemeral=False  # Default - will be remembered
)

# Temporary injection - only for current call
HookResult(
    action="inject_context", 
    context_injection="Current memory usage: 85% (reminder: optimize soon)",
    ephemeral=True  # Won't clutter conversation history
)
```

**Placement Control:** The `append_to_last_tool_result` field provides fine-grained control over where ephemeral injections appear. When `True`, the content gets appended to the last tool result message instead of creating a new message. This only works when `ephemeral=True` and falls back to a new message if the last message isn't a tool result:

```python
# Append contextual reminder to tool output
HookResult(
    action="inject_context",
    context_injection="\n\nReminder: This file needs review before deployment",
    ephemeral=True,
    append_to_last_tool_result=True  # Attach to last tool's output
)

# Create separate message (default behavior)
HookResult(
    action="inject_context",
    context_injection="Build artifacts ready for deployment", 
    ephemeral=True,
    append_to_last_tool_result=False  # New message
)
```

**Field Combinations:** These fields work together to create sophisticated injection behaviors. The most common patterns combine role selection with persistence control, while placement control is typically used for contextual annotations:

```python
# Pattern: Persistent system feedback
HookResult(
    action="inject_context",
    context_injection="Security scan completed: 2 vulnerabilities found",
    context_injection_role="system",
    ephemeral=False
)

# Pattern: Temporary user simulation  
HookResult(
    action="inject_context",
    context_injection="Please also check the staging environment",
    context_injection_role="user", 
    ephemeral=True
)

# Pattern: Contextual tool annotation
HookResult(
    action="inject_context",
    context_injection="\n[Hook: File backed up to ~/.amplifier/backups/]",
    context_injection_role="system",
    ephemeral=True,
    append_to_last_tool_result=True
)
```

#### Approval Gate Fields

The approval gate fields enable hooks to request user approval for operations, providing dynamic permission logic that goes beyond the kernel's built-in approval system. These four fields work together to define the approval prompt, available choices, timeout behavior, and fallback actions.

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `approval_prompt` | `str \| None` | `None` | Question to ask user in approval UI |
| `approval_options` | `list[str] \| None` | `None` | User choice options (defaults to `['Allow', 'Deny']`) |
| `approval_timeout` | `float` | `300.0` | Seconds to wait for user response |
| `approval_default` | `Literal["allow", "deny"]` | `"deny"` | Default decision on timeout or error |

**Approval Prompt:** The `approval_prompt` field contains the question displayed to the user in the approval UI. It should clearly explain what operation requires approval and why, providing enough context for the user to make an informed decision:

```python
# Basic approval request
HookResult(
    action="ask_user",
    approval_prompt="Allow write to production/config.py?"
)

# Detailed approval with context
HookResult(
    action="ask_user", 
    approval_prompt="Execute 'rm -rf /tmp/cache/*' to clear 2.3GB of temporary files?"
)

# Security-focused approval
HookResult(
    action="ask_user",
    approval_prompt="Allow network request to external API https://api.example.com/data?"
)
```

**Approval Options:** The `approval_options` field defines the choices presented to the user. When `None`, it defaults to `['Allow', 'Deny']`. Custom options enable flexible permission control, including session-scoped caching with "Allow always" choices:

```python
# Default options (Allow/Deny)
HookResult(
    action="ask_user",
    approval_prompt="Delete temporary files?",
    approval_options=None  # Uses ['Allow', 'Deny']
)

# Custom options with session caching
HookResult(
    action="ask_user",
    approval_prompt="Install npm package 'lodash'?",
    approval_options=["Allow once", "Allow always", "Deny"]
)

# Simple yes/no choice
HookResult(
    action="ask_user",
    approval_prompt="Continue with deployment?", 
    approval_options=["Yes", "No"]
)
```

**Timeout Control:** The `approval_timeout` field specifies how long to wait for user response in seconds. The default of 300.0 (5 minutes) balances user convenience with system responsiveness. On timeout, the `approval_default` action is taken automatically:

```python
# Standard timeout (5 minutes)
HookResult(
    action="ask_user",
    approval_prompt="Approve database migration?",
    approval_timeout=300.0  # Default value
)

# Quick timeout for non-critical operations
HookResult(
    action="ask_user",
    approval_prompt="Clear browser cache?",
    approval_timeout=30.0  # 30 seconds
)

# Extended timeout for complex decisions
HookResult(
    action="ask_user", 
    approval_prompt="Review and approve 47 file changes before commit?",
    approval_timeout=900.0  # 15 minutes
)
```

**Default Action:** The `approval_default` field determines what happens when the user doesn't respond within the timeout period or an error occurs. The default `"deny"` value prioritizes security, while `"allow"` may be appropriate for low-risk operations:

```python
# Secure default (deny on timeout)
HookResult(
    action="ask_user",
    approval_prompt="Allow write to system directory?",
    approval_default="deny"  # Safe for security-sensitive operations
)

# Permissive default for low-risk operations
HookResult(
    action="ask_user",
    approval_prompt="Save backup copy of edited file?",
    approval_default="allow",  # User likely wants backup
    approval_timeout=60.0
)
```

**Complete Approval Gate Example:** All fields work together to create sophisticated approval workflows. Approvals are session-scoped cached (e.g., "Allow always" choices are remembered for the current session) and integrate with the hook's reason field for comprehensive user feedback:

```python
# Comprehensive approval gate
HookResult(
    action="ask_user",
    approval_prompt="Execute sudo command 'systemctl restart nginx'?",
    approval_options=["Allow once", "Allow always for nginx", "Deny"],
    approval_timeout=180.0,  # 3 minutes
    approval_default="deny",  # Security-first
    reason="System service restart requires elevated privileges"
)

# File operation approval with context
HookResult(
    action="ask_user", 
    approval_prompt="Overwrite existing file 'important-data.json' (last modified 2 hours ago)?",
    approval_options=["Overwrite", "Create backup and overwrite", "Cancel"],
    approval_timeout=120.0,
    approval_default="deny",
    reason="Preventing accidental data loss"
)
```

#### Output Control Fields

The output control fields enable hooks to manage what users see in their terminal or UI, providing clean user experiences by hiding verbose processing details while highlighting important information. These three fields work together to control hook output visibility and display targeted messages to users.

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `suppress_output` | `bool` | `False` | Hide hook's stdout/stderr from user transcript |
| `user_message` | `str \| None` | `None` | Message to display to user (separate from context injection) |
| `user_message_level` | `Literal["info", "warning", "error"]` | `"info"` | Severity level for user message display |

**Output Suppression:** The `suppress_output` field controls whether the hook's stdout and stderr appear in the user transcript. When `True`, verbose processing output is hidden from the UI, preventing clutter while still allowing the hook to perform its work. Note that hooks can only suppress their own output, not tool output, for security reasons:

```python
# Hide verbose linting output
HookResult(
    action="continue",
    suppress_output=True,  # User won't see detailed linter logs
    user_message="Linting completed: 3 warnings found"
)

# Show processing details (default behavior)
HookResult(
    action="continue",
    suppress_output=False  # User sees all hook output
)

# Suppress output while injecting context
HookResult(
    action="inject_context",
    context_injection="Linter found error on line 42: Line too long",
    suppress_output=True,  # Hide verbose output
    user_message="Found 3 linting issues"  # Show summary
)
```

**User Messages:** The `user_message` field displays targeted messages to users, separate from context injection. Unlike context injection (which goes to the agent), user messages appear directly in the user interface for alerts, warnings, or status updates:

```python
# Status update message
HookResult(
    action="continue",
    user_message="Processed 10 files successfully",
    suppress_output=True
)

# Warning message
HookResult(
    action="continue", 
    user_message="Backup created before modifying system files",
    user_message_level="warning"
)

# Error notification
HookResult(
    action="deny",
    user_message="Operation blocked: insufficient disk space",
    user_message_level="error",
    reason="Less than 100MB free space remaining"
)
```

**Message Severity Levels:** The `user_message_level` field specifies the severity level for user messages, affecting how they're displayed in the UI. The three levels provide visual cues to help users understand message importance:

```python
# Informational message (default)
HookResult(
    action="continue",
    user_message="File backup completed",
    user_message_level="info"  # Default level
)

# Warning for non-critical issues
HookResult(
    action="continue",
    user_message="Large file detected (50MB) - upload may take time", 
    user_message_level="warning"
)

# Error for failures or blocks
HookResult(
    action="deny",
    user_message="Security scan failed - malicious content detected",
    user_message_level="error"
)
```

**Combined Output Control:** All three fields work together to create clean, informative user experiences. Common patterns include suppressing verbose output while showing concise status messages, or combining user messages with context injection for comprehensive feedback:

```python
# Clean UX: hide details, show summary
HookResult(
    action="continue",
    suppress_output=True,  # Hide verbose processing
    user_message="Code formatting applied to 15 files",
    user_message_level="info"
)

# Dual feedback: user sees alert, agent gets details
HookResult(
    action="inject_context",
    context_injection="Test failures:\n- test_auth.py:42 AssertionError\n- test_db.py:15 ConnectionError",
    user_message="Test suite failed (2 errors)",
    user_message_level="error",
    suppress_output=True
)

# Progressive disclosure: summary for user, full context for agent
HookResult(
    action="inject_context", 
    context_injection="Security scan results: 3 medium-risk vulnerabilities found in dependencies. Recommend updating: lodash@4.17.19 -> 4.17.21, axios@0.21.1 -> 0.21.4",
    user_message="Security vulnerabilities detected in dependencies",
    user_message_level="warning",
    suppress_output=True
)
```

### Examples

The following examples demonstrate each `HookResult` action type with practical use cases. Each example shows the complete hook function implementation, illustrating how to construct the appropriate `HookResult` for different scenarios.

These examples progress from simple observation patterns to complex multi-capability hooks, showing how to combine fields effectively. The patterns cover common real-world scenarios like validation, security gates, automated feedback, and user experience optimization.

All examples use async functions that match the required hook handler signature: `async def handler(event: str, data: dict[str, Any]) -> HookResult`. The event data structure varies by event type - see the Events Reference for complete schemas.

```python
# Basic hook structure used in all examples
from amplifier_core.models import HookResult
from amplifier_core.hooks import HookRegistry

registry = HookRegistry()

async def example_hook(event: str, data: dict[str, Any]) -> HookResult:
    # Hook logic here
    return HookResult(action="continue")

# Register the hook
unregister = registry.register(
    event="tool:pre",
    handler=example_hook,
    priority=0,
    name="example"
)
```

#### Continue (observe only)

The `continue` action allows hooks to observe operations without interfering. This is the default action and most common pattern for monitoring, logging, and metrics collection:

```python
async def audit_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Log all tool executions for audit trail."""
    if event == "tool:post":
        tool_name = data.get("tool_name", "unknown")
        success = data.get("tool_result", {}).get("success", False)
        
        # Log to audit system
        audit_logger.info(f"Tool {tool_name} executed: {'success' if success else 'failed'}")
        
        # Update metrics
        metrics.increment(f"tool.{tool_name}.{'success' if success else 'failure'}")
    
    # Continue normal execution
    return HookResult(action="continue")
```

This pattern is ideal for passive monitoring where you need visibility into operations but don't want to modify behavior. The hook executes its logic (logging, metrics, notifications) then returns `continue` to let the operation proceed normally.

#### Deny operation

The `deny` action blocks operations from proceeding, typically used for validation failures or security violations. The `reason` field provides explanation that's shown to the agent:

```python
async def security_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Block operations on sensitive files."""
    if event == "tool:pre" and data.get("tool_name") == "Write":
        file_path = data.get("tool_input", {}).get("file_path", "")
        
        if file_path.endswith((".env", ".key", ".pem")):
            return HookResult(
                action="deny",
                reason=f"Access denied: {file_path} contains sensitive data"
            )
    
    return HookResult(action="continue")
```

When denied, the operation stops immediately and the agent receives the reason message, allowing it to understand why the action was blocked and potentially try an alternative approach.

#### Modify event data

The `modify` action changes event data that flows to subsequent hooks and the operation itself. When a hook returns `modify`, the `data` field becomes the new event data:

```python
async def sanitize_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Clean and validate tool inputs before execution."""
    if event == "tool:pre" and data.get("tool_name") == "Write":
        tool_input = data.get("tool_input", {}).copy()
        
        # Sanitize file content
        if "content" in tool_input:
            tool_input["content"] = tool_input["content"].strip()
        
        # Update the event data
        modified_data = data.copy()
        modified_data["tool_input"] = tool_input
        
        return HookResult(action="modify", data=modified_data)
    
    return HookResult(action="continue")
```

The modified data flows through the hook chain - later hooks receive the updated data, and the final modified data is used by the operation. This enables data transformation pipelines where multiple hooks can sequentially modify the same event data.

#### Inject context to agent

The `inject_context` action adds feedback directly to the agent's conversation context, enabling automated correction loops within the same turn. The agent sees the injected content and can respond to it immediately:

```python
async def linter_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Run linter after file writes and inject feedback."""
    if event == "tool:post" and data.get("tool_name") == "Write":
        file_path = data.get("tool_input", {}).get("file_path", "")
        
        # Run linter
        result = subprocess.run(["ruff", "check", file_path], capture_output=True)
        
        if result.returncode != 0:
            return HookResult(
                action="inject_context",
                context_injection=f"Linter found issues in {file_path}:\n{result.stderr.decode()}",
                user_message="Found linting issues",
                user_message_level="warning"
            )
    
    return HookResult(action="continue")
```

The `context_injection` field contains the feedback text that gets added to the agent's context. Use `context_injection_role` to control whether it appears as a system message (default), user input, or assistant response. Set `ephemeral=True` for temporary feedback that doesn't persist in conversation history.

#### Ephemeral context injection

Ephemeral injections are temporary context that only appears for the current LLM call without being stored in conversation history. This is useful for frequently-changing state like todo reminders or status updates:

```python
async def todo_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Inject current todo list as temporary reminder."""
    if event == "tool:pre":
        # Get current todos from state
        todos = get_pending_todos()
        
        if todos:
            todo_text = "Current todos:\n" + "\n".join(f"- {todo}" for todo in todos)
            
            return HookResult(
                action="inject_context",
                context_injection=todo_text,
                ephemeral=True,  # Not stored in history
                suppress_output=True
            )
    
    return HookResult(action="continue")
```

The orchestrator must append ephemeral injections to the current LLM call's messages without storing them in the conversation context. This keeps the agent aware of current state while preventing history bloat from repetitive reminders.

#### Request approval

The `ask_user` action requests user approval for high-risk operations, creating dynamic permission gates. The operation pauses until the user responds or the timeout expires:

```python
async def production_protection_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Require user approval for production file writes."""
    if event == "tool:pre" and data.get("tool_name") == "Write":
        file_path = data.get("tool_input", {}).get("file_path", "")
        
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

The `approval_prompt` should clearly explain what operation needs permission and why. Use `approval_options` to provide flexible choices like "Allow always" for trusted operations. The `approval_default` determines what happens on timeout - "deny" is safer for security-sensitive operations.

#### Output control only

Sometimes you only need to control output visibility without taking other actions. Use `action="continue"` with output control fields to show clean messages while hiding verbose processing details:

```python
async def progress_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Show clean progress message, hide verbose processing output."""
    if event == "tool:post" and data.get("tool_name") == "ProcessFiles":
        files_count = data.get("tool_result", {}).get("files_processed", 0)
        
        return HookResult(
            action="continue",  # No other action needed
            user_message=f"Successfully processed {files_count} files",
            user_message_level="info",
            suppress_output=True  # Hide detailed processing logs
        )
    
    return HookResult(action="continue")
```

This pattern is useful for long-running operations where you want to show meaningful status updates to the user while preventing verbose tool output from cluttering the interface. The operation proceeds normally, but with controlled visibility.

## See Also

- **[Hook Contract](docs/contracts/HOOK_CONTRACT.md)** - Complete specification for implementing hook modules with protocol requirements and lifecycle guarantees
- **[Provider Contract](docs/contracts/PROVIDER_CONTRACT.md)** - Interface specification for LLM provider modules that hooks commonly interact with
- **[Tool Contract](docs/contracts/TOOL_CONTRACT.md)** - Protocol definition for tool modules that generate many hook events
- **[Orchestrator Contract](docs/contracts/ORCHESTRATOR_CONTRACT.md)** - Implementation guide for orchestrator modules that coordinate hook execution
- **[Context Contract](docs/contracts/CONTEXT_CONTRACT.md)** - Interface for context managers that hooks can modify through injections
- **Behavioral Testing** - Use `amplifier_core.validation.behavioral.HookBehaviorTests` base class for standardized hook module testing
- **Module Validation** - Run `amplifier-core validate hook /path/to/module` to verify protocol compliance and detect common issues
- **Testing Utilities** - Import `TestCoordinator`, `EventRecorder`, and `MockTool` from `amplifier_core.testing` for hook development
- **Pytest Integration** - Enable automatic fixture injection and behavioral tests by installing the `amplifier_core.pytest_plugin`
- **Event Reference** - See `amplifier_core.events` module for the complete canonical event taxonomy and naming conventions
- **Approval System** - Review `ApprovalProvider` protocol in `amplifier_core.interfaces` for implementing custom approval workflows