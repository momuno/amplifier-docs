# Hooks API

The Hooks API provides a powerful event-driven system for extending Amplifier's behavior at key lifecycle points. The system consists of three core components:

- **HookRegistry** - Central registry for managing hook handlers with priority-based execution
- **Hook Handler** - Functions that execute when specific events occur during Amplifier's operation
- **HookResult** - Return value that controls how Amplifier responds to hook execution

Key capabilities include:

| Capability | Description |
|------------|-------------|
| **Observe** | Monitor operations for logging, metrics, and audit trails |
| **Block** | Prevent operations from proceeding based on validation or security rules |
| **Modify** | Transform event data before it's processed |
| **Inject Context** | Add feedback directly to the agent's conversation for immediate correction |
| **Request Approval** | Ask users for permission on high-risk operations |
| **Control Output** | Hide verbose processing details while showing clean status messages |

Hooks execute sequentially by priority, with data modifications chaining through subsequent handlers. The system supports short-circuiting on deny actions and merging multiple context injections from different hooks on the same event.

```python
from amplifier_core.hooks import HookRegistry
from amplifier_core.models import HookResult

# Basic hook registration
registry = HookRegistry()

async def my_hook(event: str, data: dict) -> HookResult:
    return HookResult(action="continue")

unregister = registry.register("tool:post", my_hook)
```

## HookRegistry

The `HookRegistry` class is the central component for managing lifecycle hooks in Amplifier. It provides deterministic execution with priority ordering and supports various hook actions including observation, modification, denial, context injection, and user approval requests.

**Source:** [`amplifier_core/hooks.py`](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/hooks.py)

**Key Capabilities:**

| Capability | Description |
|------------|-------------|
| **Priority Execution** | Handlers execute sequentially by priority (lower numbers first) |
| **Short-Circuit Denial** | Stops execution immediately when a handler returns "deny" |
| **Data Chaining** | Modifications from one handler flow to the next |
| **Context Merging** | Multiple context injections are automatically combined |
| **Error Resilience** | Individual handler failures don't stop other handlers |
| **Response Collection** | Gather responses from multiple handlers for decision-making |

**Basic Usage:**

```python
from amplifier_core.hooks import HookRegistry
from amplifier_core.models import HookResult

# Create registry and register a handler
registry = HookRegistry()

async def audit_tool_usage(event: str, data: dict) -> HookResult:
    tool_name = data.get("tool_name", "unknown")
    print(f"Tool executed: {tool_name}")
    return HookResult(action="continue")

# Register with priority (lower = earlier execution)
unregister = registry.register("tool:post", audit_tool_usage, priority=10)

# Emit events to trigger handlers
result = await registry.emit("tool:post", {"tool_name": "calculator"})
```

### Methods

The `HookRegistry` provides methods for registering handlers, emitting events, and managing the hook lifecycle. The core workflow involves registering handlers with `register()`, emitting events with `emit()`, and optionally collecting responses with `emit_and_collect()`.

| Method | Purpose |
|--------|---------|
| `register()` | Register a hook handler for an event with priority |
| `on()` | Alias for `register()` for backwards compatibility |
| `set_default_fields()` | Set default data fields merged with all events |
| `emit()` | Emit event to handlers with sequential execution |
| `emit_and_collect()` | Emit event and collect all handler responses |
| `list_handlers()` | List registered handlers for debugging |

#### register

Register a hook handler for an event with priority-based execution ordering.

```python
def register(
    self,
    event: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[HookResult]],
    priority: int = 0,
    name: str | None = None,
) -> Callable[[], None]
```

Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str` | Required | Event name to hook into |
| `handler` | `Callable[[str, dict[str, Any]], Awaitable[HookResult]]` | Required | Async function that handles the event |
| `priority` | `int` | `0` | Execution priority (lower numbers execute first) |
| `name` | `str \| None` | `None` | Optional handler name for debugging |

Returns: `Callable[[], None]` - Unregister function to remove the handler

```python
async def security_check(event: str, data: dict) -> HookResult:
    if data.get("tool_name") == "dangerous_tool":
        return HookResult(action="deny", reason="Tool blocked by security policy")
    return HookResult(action="continue")

# Register with high priority (executes first)
unregister = registry.register("tool:pre", security_check, priority=1, name="security")

# Later remove the handler
unregister()
```

Execution Behavior:
Handlers are automatically sorted by priority after registration. Lower priority numbers execute first, allowing critical handlers like security checks to run before other processing.

#### on

Alias for the `register()` method provided for backwards compatibility.

```python
def on(
    self,
    event: str,
    handler: Callable[[str, dict[str, Any]], Awaitable[HookResult]],
    priority: int = 0,
    name: str | None = None,
) -> Callable[[], None]
```

Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str` | Required | Event name to hook into |
| `handler` | `Callable[[str, dict[str, Any]], Awaitable[HookResult]]` | Required | Async function that handles the event |
| `priority` | `int` | `0` | Execution priority (lower numbers execute first) |
| `name` | `str \| None` | `None` | Optional handler name for debugging |

Returns: `Callable[[], None]` - Unregister function to remove the handler

```python
# Alternative registration syntax
unregister = registry.on("session:start", session_logger, priority=5)
```

Execution Behavior:
Identical to `register()` - this is simply an alias for developers who prefer the `.on()` syntax.

#### set_default_fields

Set default fields that will be merged with all emitted events, useful for adding session context.

```python
def set_default_fields(self, **defaults) -> None
```

Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `**defaults` | `Any` | Required | Key-value pairs to include in all events |

Returns: `None`

```python
# Set session context for all events
registry.set_default_fields(
    session_id="sess_123",
    user_id="user_456",
    environment="production"
)

# Now all emitted events will include these fields
await registry.emit("tool:pre", {"tool_name": "calculator"})
# Event data will be: {"session_id": "sess_123", "user_id": "user_456", 
#                      "environment": "production", "tool_name": "calculator"}
```

Execution Behavior:
Default fields are merged with event data before handlers execute. Explicit event data takes precedence over defaults when keys conflict.

#### emit

Emit an event to all registered handlers with sequential execution and data chaining.

```python
async def emit(self, event: str, data: dict[str, Any]) -> HookResult
```

Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str` | Required | Event name to emit |
| `data` | `dict[str, Any]` | Required | Event data (may be modified by handlers) |

Returns: `HookResult` - Final result after all handlers execute

```python
# Emit tool execution event
result = await registry.emit("tool:post", {
    "tool_name": "file_reader",
    "file_path": "/tmp/data.txt",
    "success": True
})

if result.action == "deny":
    print(f"Operation blocked: {result.reason}")
elif result.action == "inject_context":
    print(f"Context to inject: {result.context_injection}")
```

Execution Behavior:
Handlers execute sequentially by priority. Data modifications chain through handlers. Execution stops immediately on "deny" actions. Multiple "inject_context" results are automatically merged.

#### emit_and_collect

Emit event and collect all handler responses for decision-making scenarios.

```python
async def emit_and_collect(self, event: str, data: dict[str, Any], timeout: float = 1.0) -> list[Any]
```

Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str` | Required | Event name to emit |
| `data` | `dict[str, Any]` | Required | Event data |
| `timeout` | `float` | `1.0` | Max time to wait for each handler (seconds) |

Returns: `list[Any]` - List of non-None response data from handlers

```python
# Collect tool recommendations from multiple handlers
responses = await registry.emit_and_collect("decision:tool_resolution", {
    "user_query": "What's the weather like?",
    "available_tools": ["weather_api", "web_search"]
})

# Responses might be: [{"tool": "weather_api", "confidence": 0.9}, 
#                      {"tool": "web_search", "confidence": 0.3}]
tool_scores = {r["tool"]: r["confidence"] for r in responses}
```

Execution Behavior:
Unlike `emit()`, this method collects responses rather than chaining data. Individual handler timeouts prevent blocking. Failed handlers don't stop collection from others.

#### list_handlers

List registered handlers for debugging and introspection.

```python
def list_handlers(self, event: str | None = None) -> dict[str, list[str]]
```

Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event` | `str \| None` | `None` | Optional event to filter by |

Returns: `dict[str, list[str]]` - Dict mapping event names to handler names

```python
# List all handlers
all_handlers = registry.list_handlers()
# Returns: {"tool:pre": ["security", "validator"], "tool:post": ["audit", "metrics"]}

# List handlers for specific event
tool_handlers = registry.list_handlers("tool:pre")
# Returns: {"tool:pre": ["security", "validator"]}
```

Execution Behavior:
Returns handler names in priority order. Only includes handlers that were registered with explicit names.

### Standard Events

The HookRegistry class defines standard event constants for common lifecycle, decision, and error scenarios. These constants provide a stable interface for hooking into Amplifier's core operations.

**Lifecycle Events**

| Constant | String Value | Description |
|----------|--------------|-------------|
| `SESSION_START` | `"session:start"` | Fired when a new session begins |
| `SESSION_END` | `"session:end"` | Fired when a session terminates |
| `PROMPT_SUBMIT` | `"prompt:submit"` | Fired when user submits a prompt |
| `TOOL_PRE` | `"tool:pre"` | Fired before tool execution |
| `TOOL_POST` | `"tool:post"` | Fired after tool execution completes |
| `CONTEXT_PRE_COMPACT` | `"context:pre-compact"` | Fired before context compaction |
| `AGENT_SPAWN` | `"agent:spawn"` | Fired when an agent is created |
| `AGENT_COMPLETE` | `"agent:complete"` | Fired when an agent completes |
| `ORCHESTRATOR_COMPLETE` | `"orchestrator:complete"` | Fired when orchestration finishes |
| `USER_NOTIFICATION` | `"user:notification"` | Fired for user notifications |

**Decision Events**

| Constant | String Value | Description |
|----------|--------------|-------------|
| `DECISION_TOOL_RESOLUTION` | `"decision:tool_resolution"` | Fired to resolve tool selection |
| `DECISION_AGENT_RESOLUTION` | `"decision:agent_resolution"` | Fired to resolve agent selection |
| `DECISION_CONTEXT_RESOLUTION` | `"decision:context_resolution"` | Fired to resolve context decisions |

**Error Events**

| Constant | String Value | Description |
|----------|--------------|-------------|
| `ERROR_TOOL` | `"error:tool"` | Fired when tool execution fails |
| `ERROR_PROVIDER` | `"error:provider"` | Fired when provider calls fail |
| `ERROR_ORCHESTRATION` | `"error:orchestration"` | Fired when orchestration fails |

```python
from amplifier_core.hooks import HookRegistry
from amplifier_core.models import HookResult

registry = HookRegistry()

# Hook into tool execution lifecycle
@registry.register(HookRegistry.TOOL_PRE)
async def validate_tool(event: str, data: dict) -> HookResult:
    if data.get("tool_name") == "dangerous_tool":
        return HookResult(action="deny", reason="Tool not allowed")
    return HookResult(action="continue")

# Hook into decision events for custom logic
@registry.register(HookRegistry.DECISION_TOOL_RESOLUTION)
async def suggest_tool(event: str, data: dict) -> HookResult:
    return HookResult(action="continue", data={"recommended_tool": "calculator"})
```

Note: This section documents the core lifecycle events defined in HookRegistry. The canonical event taxonomy in [amplifier_core/events.py](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/events.py) uses underscore format (e.g., `context:pre_compact`) for consistency with the evolving event taxonomy. When referencing events programmatically, prefer the `HookRegistry` constants or canonical `events.py` definitions.

## Hook Handler

Hook handlers are async functions that respond to lifecycle events. They must follow a specific signature and return a `HookResult` to participate in the hook system's execution flow.

**Handler Signature**

```python
async def handler(event: str, data: dict[str, Any]) -> HookResult
```

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `str` | The event name that triggered this handler |
| `data` | `dict[str, Any]` | Event data dictionary (may include default fields) |

**Return Value**

Must return a `HookResult` instance with an appropriate action. Invalid return types are logged as warnings and ignored.

**Implementation Requirements**

- Handler must be async (use `async def`)
- Must accept exactly two parameters: `event` and `data`
- Must return a `HookResult` instance
- Should handle exceptions gracefully (uncaught exceptions are logged but don't stop other handlers)
- Should not assume specific data fields exist (use `.get()` for optional fields)
- Should not mutate the input `data` dict directly (return modified data via `HookResult`)

**Example Implementation**

```python
async def security_validator(event: str, data: dict[str, Any]) -> HookResult:
    tool_name = data.get("tool_name")
    if tool_name in ["rm", "delete", "format"]:
        return HookResult(action="deny", reason=f"Tool {tool_name} blocked by security policy")
    
    # Add security metadata
    modified_data = {**data, "security_validated": True}
    return HookResult(action="modify", data=modified_data)
```

The handler receives the current event data, which may have been modified by previous handlers in the priority chain. Default fields set via `set_default_fields()` are automatically merged into the data dictionary before handlers execute.

## HookResult

The `HookResult` class represents the response from a hook handler, controlling how the hook system processes events and manages execution flow. It provides a structured way for handlers to communicate their decisions back to the hook registry.

**Source:** [amplifier_core/models.py](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/models.py)

**Key Capabilities**

- **Flow Control**: Direct event processing with actions like continue, deny, or modify
- **Data Transformation**: Modify event data that flows to subsequent handlers
- **Context Injection**: Add content directly to the agent's conversation context
- **User Interaction**: Request approval or confirmation from users
- **Output Management**: Control visibility and persistence of injected content
- **Error Handling**: Provide structured denial reasons for debugging and logging
- **Token Budget Control**: Configure injection limits via `session.injection_budget_per_turn`

**Basic Usage Example**

```python
from amplifier_core.models import HookResult

# Simple continue action
result = HookResult(action="continue")

# Deny with reason
result = HookResult(
    action="deny", 
    reason="Operation not permitted in production"
)

# Modify event data
modified_data = {**original_data, "validated": True}
result = HookResult(action="modify", data=modified_data)

# Inject context for agent
result = HookResult(
    action="inject_context",
    context_injection="Security scan completed successfully",
    context_injection_role="system"
)
```

The `HookResult` instance returned by your handler determines whether event processing continues, stops, or takes special actions like injecting context or requesting user approval.

### Actions

The `action` field in `HookResult` determines what happens after your hook executes. It controls the flow of event processing and enables different types of hook behavior.

| Action | Description | When to Use |
|--------|-------------|-------------|
| `continue` | Proceed normally with the operation | Default behavior, monitoring, logging |
| `deny` | Block the operation from proceeding | Security violations, validation failures |
| `modify` | Transform event data for subsequent handlers | Data enrichment, preprocessing |
| `inject_context` | Add content to agent's conversation context | Automated feedback, correction loops |
| `ask_user` | Request user approval before proceeding | Dynamic permissions, high-risk operations |

**Flow Behavior:**
- `continue` and `modify` allow the event to proceed to the next handler in the priority chain
- `deny` immediately stops processing and blocks the operation
- `inject_context` and `ask_user` perform their special action then continue processing

```python
# Block dangerous operations
if tool_name in ["rm", "format", "delete"]:
    return HookResult(action="deny", reason="Destructive tool blocked")

# Inject linter feedback to agent
if linter_errors:
    return HookResult(
        action="inject_context",
        context_injection=f"Linter found {len(linter_errors)} issues",
        user_message="Code quality check completed"
    )

# Default: let operation continue
return HookResult(action="continue")
```

### Fields

The `HookResult` class provides a comprehensive set of fields that control event processing, data flow, and user interaction. These fields are organized into logical categories based on their purpose and functionality.

| Category | Field | Type | Default | Description |
|----------|-------|------|---------|-------------|
| **Core Action** | `action` | `Literal` | `"continue"` | Primary action to take |
| **Data Flow** | `data` | `dict \| None` | `None` | Modified event data for chaining |
| | `reason` | `str \| None` | `None` | Explanation for deny/modification |
| **Context Injection** | `context_injection` | `str \| None` | `None` | Text to inject into agent's context |
| | `context_injection_role` | `Literal` | `"system"` | Role for injected message |
| | `ephemeral` | `bool` | `False` | Temporary injection flag |
| | `append_to_last_tool_result` | `bool` | `False` | Append to last tool result |
| **User Approval** | `approval_prompt` | `str \| None` | `None` | Question for user approval |
| | `approval_options` | `list[str] \| None` | `None` | User choice options |
| | `approval_timeout` | `float` | `300.0` | Timeout in seconds |
| | `approval_default` | `Literal` | `"deny"` | Default action on timeout |
| **Output Control** | `suppress_output` | `bool` | `False` | Hide hook's output |
| | `user_message` | `str \| None` | `None` | Message to display to user |
| | `user_message_level` | `Literal` | `"info"` | Severity level for user message |

#### action
Primary action that determines how event processing continues after the hook executes.

**Type:** `Literal["continue", "deny", "modify", "inject_context", "ask_user"]`  
**Default:** `"continue"`

Controls the fundamental behavior of the hook system's response to your handler. Use `continue` for monitoring, `deny` for blocking operations, `modify` for data transformation, `inject_context` for agent feedback, and `ask_user` for dynamic permissions.

#### data
Modified event data that chains through to subsequent handlers in the priority order.

**Type:** `dict[str, Any] | None`  
**Default:** `None`

Only used with `action="modify"`. The provided dictionary replaces the event data for all remaining handlers in the chain. Should contain the complete modified event data, not just changes.

#### reason
Human-readable explanation for deny actions or modifications, shown to the agent when operations are blocked.

**Type:** `str | None`  
**Default:** `None`

Provides context for debugging and logging when operations are denied or modified. The agent sees this message when a tool execution is blocked, helping with troubleshooting.

#### context_injection
Text content to inject directly into the agent's conversation context, enabling automated feedback loops.

**Type:** `str | None`  
**Default:** `None`

Only used with `action="inject_context"`. The agent sees this content and can respond to it within the same conversation turn. Size is unlimited by default but configurable via `session.injection_size_limit`. Content is audited and tagged with the source hook for provenance tracking.

#### context_injection_role
Role for the injected message in the conversation context.

**Type:** `Literal["system", "user", "assistant"]`  
**Default:** `"system"`

Determines how the injected content appears in the conversation. Use `system` for environmental feedback (recommended), `user` to simulate user input, or `assistant` for agent self-talk scenarios.

#### ephemeral
Controls whether injected content is temporary or permanently stored in conversation history.

**Type:** `bool`  
**Default:** `False`

When `True`, the injection is only added for the current LLM call and not stored in persistent conversation history. Useful for transient state like todo reminders that update frequently.

#### append_to_last_tool_result
Appends ephemeral context injection to the last tool result message instead of creating a new message.

**Type:** `bool`  
**Default:** `False`

Only applicable when `action="inject_context"` and `ephemeral=True`. Use for contextual reminders that relate directly to the tool that just executed. Falls back to creating a new message if the last message isn't a tool result.

#### approval_prompt
Question displayed to the user when requesting approval for an operation.

**Type:** `str | None`  
**Default:** `None`

Only used with `action="ask_user"`. Should clearly explain what operation requires approval and why. Displayed in the approval UI along with the available options.

#### approval_options
List of choices presented to the user for approval decisions.

**Type:** `list[str] | None`  
**Default:** `None`

When `None`, defaults to `["Allow", "Deny"]`. Can include options like `"Allow once"`, `"Allow always"`, `"Deny"` for flexible permission control with session-scoped caching.

#### approval_timeout
Maximum time in seconds to wait for user response before taking the default action.

**Type:** `float`  
**Default:** `300.0`

Prevents operations from hanging indefinitely when user approval is required. After timeout expires, the `approval_default` action is automatically taken.

#### approval_default
Default decision when approval times out or encounters an error.

**Type:** `Literal["allow", "deny"]`  
**Default:** `"deny"`

Security-focused default that denies operations when user input cannot be obtained. Use `"allow"` only for low-risk operations where blocking would be more disruptive than proceeding.

#### suppress_output
Hides the hook's stdout/stderr output from the user transcript.

**Type:** `bool`  
**Default:** `False`

Prevents verbose processing output from cluttering the user interface. Only suppresses the hook's own output for security reasons - tool output cannot be suppressed by hooks.

#### user_message
Direct message to display to the user, separate from context injection.

**Type:** `str | None`  
**Default:** `None`

Use for alerts, warnings, or status updates that the user should see immediately. Displayed with the specified severity level in the user interface.

#### user_message_level
Severity level for the user message, affecting how it's displayed in the interface.

**Type:** `Literal["info", "warning", "error"]`  
**Default:** `"info"`

Controls the visual presentation and urgency of user messages. Use `info` for status updates, `warning` for non-critical issues, and `error` for failures requiring attention.

### Examples

The following examples demonstrate common `HookResult` usage patterns for different scenarios. Each example shows the complete hook handler function with appropriate error handling and follows established best practices.

These patterns cover the core use cases: monitoring operations without interference, blocking invalid operations, transforming event data, providing automated feedback to agents, managing temporary context, implementing approval workflows, and controlling output visibility. The examples use realistic scenarios you'll encounter when building hook-based workflows.

All examples assume you have access to the `HookResult` class and are working within an async hook handler function with the signature `async def handler(event: str, data: dict[str, Any]) -> HookResult`.

#### Continue (observe only)

The simplest hook pattern is observation-only monitoring, where you log or track operations without affecting execution flow. Return `HookResult(action="continue")` to proceed normally.

```python
async def audit_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Log all tool executions for audit trail."""
    if event == "tool:pre":
        logger.info(f"Tool starting: {data['tool_name']}")
    elif event == "tool:post":
        success = data.get("tool_result", {}).get("success", False)
        logger.info(f"Tool completed: {data['tool_name']} (success={success})")
    
    return HookResult(action="continue")
```

This hook logs tool execution without interfering with the operation. The agent and user experience remain unchanged while you collect metrics, audit trails, or debugging information in the background.

#### Deny operation

Block operations that fail validation or violate security policies by returning `action="deny"` with a descriptive reason. The reason is shown to the agent when the operation is blocked.

```python
async def security_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Block writes to sensitive directories."""
    if event != "tool:pre" or data.get("tool_name") != "Write":
        return HookResult(action="continue")
    
    file_path = data["tool_input"]["file_path"]
    
    if any(sensitive in file_path for sensitive in ["/etc/", "/.ssh/", "/root/"]):
        return HookResult(
            action="deny",
            reason=f"Access denied: {file_path} is in a protected directory"
        )
    
    return HookResult(action="continue")
```

The agent receives the reason message and cannot proceed with the blocked operation. Use this pattern for validation failures, security violations, or policy enforcement where the operation should not continue under any circumstances.

#### Modify event data

Transform event data by returning `action="modify"` with updated data. The modified data flows to subsequent hooks and the operation itself.

```python
async def sanitize_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Remove sensitive data from tool inputs."""
    if event != "tool:pre" or data.get("tool_name") != "SendEmail":
        return HookResult(action="continue")
    
    # Create modified copy of the data
    modified_data = data.copy()
    tool_input = modified_data["tool_input"].copy()
    
    # Redact sensitive patterns
    tool_input["body"] = re.sub(r'\b\d{4}-\d{4}-\d{4}-\d{4}\b', '[REDACTED]', tool_input["body"])
    modified_data["tool_input"] = tool_input
    
    return HookResult(action="modify", data=modified_data)
```

The modified data becomes the new event data for subsequent hooks and the actual operation. Use this pattern for sanitization, enrichment, or transformation of inputs before they reach tools or agents.

#### Inject context to agent

Provide automated feedback to the agent by injecting context that appears in their conversation. The agent can see and respond to this feedback within the same turn, enabling immediate correction loops.

```python
async def linter_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Run linter after file writes and inject feedback."""
    if event != "tool:post" or data.get("tool_name") != "Write":
        return HookResult(action="continue")
    
    file_path = data["tool_input"]["file_path"]
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

The injected context appears as a system message in the agent's conversation, allowing them to see the linter errors and fix them immediately. Use `ephemeral=True` for temporary feedback that updates frequently, like todo reminders or live status information.

#### Ephemeral context injection

For temporary context that updates frequently, use `ephemeral=True` to inject content that appears only in the current LLM call without being stored in conversation history:

```python
async def todo_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Inject current todo list as temporary reminder."""
    if event != "tool:pre":
        return HookResult(action="continue")
    
    # Get current todos from state
    todos = get_active_todos()  # Your todo tracking logic
    if not todos:
        return HookResult(action="continue")
    
    todo_text = "Current todos:\n" + "\n".join(f"- {todo}" for todo in todos)
    
    return HookResult(
        action="inject_context",
        context_injection=todo_text,
        ephemeral=True  # Temporary - not stored in history
    )
```

The agent sees the current todo list for context but it doesn't clutter the permanent conversation history. Each turn gets fresh todo state without accumulating outdated reminders.

#### Request approval

Ask users for permission before executing high-risk operations by returning `action="ask_user"` with an approval prompt. The operation pauses until the user responds.

```python
async def production_guard_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Require approval for production file writes."""
    if event != "tool:pre" or data.get("tool_name") != "Write":
        return HookResult(action="continue")
    
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

The user sees the approval prompt and can choose from the provided options. If they don't respond within the timeout (5 minutes), the default action is taken. Use this pattern for production deployments, sensitive operations, or cost controls where explicit user consent is required.

#### Output control only

Control output visibility for a cleaner user experience without taking other actions:

```python
async def progress_hook(event: str, data: dict[str, Any]) -> HookResult:
    """Show clean progress message, hide verbose processing output."""
    if event != "tool:post":
        return HookResult(action="continue")
    
    files_processed = data.get("files_processed", 0)
    
    return HookResult(
        action="continue",
        user_message=f"Processed {files_processed} files successfully",
        user_message_level="info",
        suppress_output=True  # Hide detailed processing logs
    )
```

The user sees a clean progress message while verbose tool output is hidden from the transcript. Use this pattern for long-running operations, detailed processing logs, or any output that would clutter the user interface without providing value.

## See Also

- **[Event Taxonomy](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/events.py)** - Complete list of canonical event names for lifecycle hooks and observability
- **[Hook Validation Framework](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/validation/hook.py)** - Automated validation tools for hook module compliance and protocol checking
- **[Testing Utilities](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/testing.py)** - Test fixtures, mock objects, and helpers for hook development and testing
- **[Pytest Plugin](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/pytest_plugin.py)** - Pytest integration for behavioral validation and auto-detection of hook modules
- **[Approval System Protocol](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/approval.py)** - Interface for implementing user approval workflows in different environments
- **[Core Interfaces](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/interfaces.py)** - Protocol definitions for all Amplifier components including ApprovalProvider and related models