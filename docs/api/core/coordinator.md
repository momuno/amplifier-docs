# Coordinator API

The Coordinator API provides the central infrastructure context and module management system for Amplifier. The system consists of one core component and supporting subsystems:

**ModuleCoordinator** - The central coordination hub that manages module lifecycle, provides infrastructure context, and enables inter-module communication. It handles module mounting/unmounting, capability registration, hook result processing, and cleanup orchestration.

Key capabilities include:

- **Module Lifecycle** - Mount and unmount modules at standardized mount points
- **Infrastructure Context** - Provide session IDs, parent IDs, and configuration access to all modules
- **Inter-Module Communication** - Capability registry for loose coupling between modules
- **Hook Result Processing** - Route hook actions (context injection, approvals, user messages) to appropriate subsystems
- **Resource Management** - Coordinate cleanup functions and maintain mount point integrity
- **Contribution Channels** - Generic aggregation mechanism for collecting module contributions

The coordinator embodies the kernel philosophy of "minimal context plumbing" - providing just enough infrastructure to make module boundaries work without imposing policy decisions. All modules receive the same coordinator instance, creating a shared infrastructure backbone.

## ModuleCoordinator

The `ModuleCoordinator` class serves as the central infrastructure hub for all Amplifier modules. It provides the essential context and plumbing that enables modules to work together without tight coupling.

**Source:** [`amplifier_core/coordinator.py`](https://github.com/microsoft/amplifier-core/blob/main/amplifier_core/coordinator.py)

The coordinator operates as a dependency injection container and service locator combined. It maintains mount points where modules attach themselves, provides infrastructure primitives (session IDs, configuration), and coordinates cross-cutting concerns like cleanup and hook result processing.

Key operational characteristics:

- **Mechanism, Not Policy** - Provides capabilities without making decisions about how they're used
- **Infrastructure Propagation** - Automatically injects session_id and parent_id into all hook events
- **Loose Coupling** - Modules communicate through capability registry rather than direct dependencies
- **Lifecycle Coordination** - Manages module initialization and cleanup in proper order
- **Hook Result Routing** - Delegates specialized actions (approvals, injections) to app-layer subsystems

The coordinator is created by `AmplifierSession` during initialization and injected into every module's mount function. This ensures all modules share the same infrastructure context and can discover each other through standardized mount points.

```python
# Coordinator is created by session and injected into modules
session = AmplifierSession(config)
coordinator = session.coordinator  # Created during session init

# Modules receive coordinator in their mount function
async def mount(coordinator, config):
    # Access infrastructure context
    session_id = coordinator.session_id
    parent_id = coordinator.parent_id
    
    # Access other modules through mount points
    context = coordinator.get("context")
    providers = coordinator.get("providers")
    
    # Register capabilities for other modules
    coordinator.register_capability("my_feature.action", my_function)
    
    # Register cleanup
    return cleanup_function
```

### Properties

The `ModuleCoordinator` exposes seven core properties that provide infrastructure context and access to mounted modules. These properties are read-only and provide the essential information modules need to participate in the system.

**Available Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `session` | `AmplifierSession` | Parent session reference for spawning child sessions |
| `session_id` | `str` | Current session ID for persistence and correlation |
| `parent_id` | `str \| None` | Parent session ID for child sessions (lineage tracking) |
| `config` | `dict` | Session configuration/mount plan with module settings |
| `loader` | `ModuleLoader` | Module loader for dynamic module loading |
| `hooks` | `HookRegistry` | Hook registry for event emission and handler registration |
| `mount_points` | `dict` | All mount points (orchestrator, providers, tools, context, hooks) |

The properties fall into three categories: **infrastructure identifiers** (session_id, parent_id) for correlation and lineage, **system references** (session, loader, hooks) for accessing kernel capabilities, and **configuration access** (config, mount_points) for reading module settings and discovering other modules.

Properties are designed for read access - modules should not modify coordinator state directly. Use methods like `mount()`, `register_capability()`, and `register_cleanup()` to interact with the coordinator.

```python
# Typical property usage in a module
async def mount(coordinator, config):
    # Infrastructure context
    logger.info(f"Mounting in session {coordinator.session_id}")
    if coordinator.parent_id:
        logger.info(f"  Child of session {coordinator.parent_id}")
    
    # Access configuration
    my_config = config  # Module-specific config passed to mount
    session_config = coordinator.config.get("session", {})
    
    # Register hooks using the registry
    coordinator.hooks.register("tool:pre", my_hook, priority=10)
    
    # Access other modules
    providers = coordinator.mount_points["providers"]
```

#### session

Returns the parent `AmplifierSession` instance that created this coordinator. This reference enables modules to spawn child sessions for delegation workflows.

```python
@property
def session(self) -> AmplifierSession
```

**Returns:** `AmplifierSession` - Parent session reference

```python
# Spawn a child session from within a module
async def delegate_task(coordinator, task):
    parent_session = coordinator.session
    
    # Create child session with agent config overlay
    child_config = parent_session._merge_configs(
        parent_session.config,
        {"agents": {"researcher": {"max_iterations": 5}}}
    )
    
    child_session = AmplifierSession(
        config=child_config,
        parent_id=coordinator.session_id  # Track lineage
    )
    
    async with child_session as session:
        result = await session.execute(task)
        return result
```

**Use Case:** The session reference is primarily used for spawning child sessions in delegation patterns. Task agents, research agents, and specialized sub-agents create child sessions to maintain separate conversation contexts while preserving lineage tracking.

#### session_id

Returns the current session's unique identifier. This ID is automatically injected into all hook events via `set_default_fields()` and used for persistence, logging correlation, and lineage tracking.

```python
@property
def session_id(self) -> str
```

**Returns:** `str` - Current session UUID

```python
# Use session_id for correlation and logging
async def mount(coordinator, config):
    session_id = coordinator.session_id
    
    # Correlate logs with session
    logger.info(f"Tool initialized in session {session_id}")
    
    # Store session-scoped state
    cache_key = f"cache:{session_id}:results"
    
    # Session ID automatically included in all hook events
    # (via coordinator.hooks.set_default_fields)
```

**Infrastructure Propagation:** The coordinator automatically calls `hooks.set_default_fields(session_id=self.session_id)` during initialization, ensuring every hook event includes the session ID without explicit parameter passing.

#### parent_id

Returns the parent session ID if this is a child session, or `None` for top-level sessions. Used to track session lineage in delegation workflows.

```python
@property
def parent_id(self) -> str | None
```

**Returns:** `str | None` - Parent session UUID or None for root sessions

```python
# Check if this is a child session
async def mount(coordinator, config):
    if coordinator.parent_id:
        logger.info(f"Child session of {coordinator.parent_id}")
        # Child sessions might have different policies
        # (e.g., reduced permissions, specific agent configs)
    else:
        logger.info("Root session")
```

**Lineage Tracking:** When a child session is created with `parent_id` set, the kernel emits a `session:fork` event during initialization. All subsequent events from the child session include both `session_id` and `parent_id` fields, enabling observability systems to track delegation hierarchies.

#### config

Returns the complete session configuration (mount plan) containing all module configurations and settings. This is the dictionary passed to `AmplifierSession(config=...)`.

```python
@property
def config(self) -> dict
```

**Returns:** `dict` - Session configuration/mount plan

**Configuration Structure:**

```python
{
    "session": {
        "orchestrator": "loop-basic",
        "context": "context-simple",
        "injection_budget_per_turn": 50000,  # Optional policy
        "injection_size_limit": 100000       # Optional policy
    },
    "providers": [
        {"module": "provider-anthropic", "config": {...}}
    ],
    "tools": [
        {"module": "tool-bash", "config": {...}}
    ],
    "hooks": [
        {"module": "hook-linter", "config": {...}}
    ],
    "agents": {
        # App-layer data for agent spawning (not module configs)
        "researcher": {"max_iterations": 10}
    }
}
```

```python
# Access configuration in a module
async def mount(coordinator, config):
    # Module-specific config is passed directly
    my_setting = config.get("timeout", 30)
    
    # Access session-level settings
    session_config = coordinator.config.get("session", {})
    orchestrator_name = session_config.get("orchestrator")
    
    # Access other module configs (rarely needed)
    tool_configs = coordinator.config.get("tools", [])
```

**Note:** The `agents` section contains app-layer configuration overlays for child session spawning, not module definitions. The kernel passes it through without interpretation.

#### loader

Returns the `ModuleLoader` instance used for dynamic module loading. Modules can use this to load additional modules at runtime.

```python
@property
def loader(self) -> ModuleLoader
```

**Returns:** `ModuleLoader` - Module loader with discovery and loading capabilities

```python
# Dynamically load a module at runtime
async def mount(coordinator, config):
    tool_id = config.get("dynamic_tool")
    
    if tool_id:
        # Load and mount tool dynamically
        tool_mount = await coordinator.loader.load(tool_id, {})
        cleanup = await tool_mount(coordinator)
        if cleanup:
            coordinator.register_cleanup(cleanup)
```

**Note:** Most modules receive all their dependencies through the coordinator's mount points rather than loading modules dynamically. Dynamic loading is primarily used by app-layer code and specialized orchestrators.

#### hooks

Returns the `HookRegistry` instance for event emission and hook handler registration. This property provides direct access to the hook system for modules that need to emit custom events or register handlers.

```python
@property
def hooks(self) -> HookRegistry
```

**Returns:** `HookRegistry` - Hook registry for the current session

```python
# Register hooks in a module
async def mount(coordinator, config):
    # Register a hook handler
    unregister = coordinator.hooks.register(
        event="tool:pre",
        handler=my_validation_hook,
        priority=10
    )
    
    # Emit custom events
    await coordinator.hooks.emit("custom:event", {
        "data": "example"
    })
    
    # Cleanup: unregister on shutdown
    coordinator.register_cleanup(unregister)
```

**Infrastructure Default Fields:** The coordinator automatically configures the hook registry with default fields (`session_id`, `parent_id`) during initialization via `hooks.set_default_fields()`. All emitted events automatically include these fields.

#### mount_points

Returns a dictionary containing all mount points and their mounted modules. This provides low-level access to the module registry for introspection and debugging.

```python
@property
def mount_points(self) -> dict
```

**Returns:** `dict` - Mount points structure with all mounted modules

**Mount Points Structure:**

```python
{
    "orchestrator": <orchestrator_instance> | None,  # Single
    "context": <context_instance> | None,            # Single
    "providers": {<name>: <provider_instance>, ...}, # Multiple
    "tools": {<name>: <tool_instance>, ...},         # Multiple
    "hooks": <HookRegistry_instance>,                # Built-in
    "module-source-resolver": <resolver> | None      # Optional
}
```

```python
# Access mount points for introspection
async def mount(coordinator, config):
    # Check what's mounted (prefer using get() method)
    if coordinator.mount_points["orchestrator"] is None:
        raise RuntimeError("No orchestrator mounted")
    
    # Iterate through all providers
    for name, provider in coordinator.mount_points["providers"].items():
        logger.info(f"Provider available: {name}")
    
    # Introspection and debugging
    tool_count = len(coordinator.mount_points["tools"])
    logger.info(f"Session has {tool_count} tools mounted")
```

**Note:** Use the `get()` method instead of accessing `mount_points` directly for cleaner code. Direct mount_points access is useful for debugging and introspection scenarios.

### Methods

The `ModuleCoordinator` provides twelve core methods for managing modules, coordinating lifecycle, and enabling inter-module communication. These methods handle everything from mounting/unmounting modules to processing hook results and collecting contributions.

**Available Methods:**

| Method | Purpose | Return Type |
|--------|---------|-------------|
| `mount()` | Mount a module at a specific mount point | `None` |
| `unmount()` | Remove a module from a mount point | `None` |
| `get()` | Retrieve mounted module(s) from a mount point | `Any` |
| `register_cleanup()` | Register cleanup function for shutdown | `None` |
| `register_capability()` | Register capability for inter-module communication | `None` |
| `get_capability()` | Retrieve a registered capability | `Any \| None` |
| `register_contributor()` | Register contributor to named channel | `None` |
| `collect_contributions()` | Collect contributions from a channel | `list[Any]` |
| `process_hook_result()` | Process HookResult and route to subsystems | `HookResult` |
| `cleanup()` | Execute all registered cleanup functions | `None` |
| `reset_turn()` | Reset per-turn tracking (token budgets) | `None` |

The methods follow three primary patterns: **module management** (`mount`, `unmount`, `get`) for lifecycle operations, **capability system** (`register_capability`, `get_capability`, `register_contributor`, `collect_contributions`) for inter-module communication, and **infrastructure coordination** (`process_hook_result`, `cleanup`, `reset_turn`) for cross-cutting concerns.

All async methods should be awaited. The coordinator handles both sync and async cleanup functions automatically during shutdown.

```python
# Typical method usage flow in a module
async def mount(coordinator, config):
    # 1. Mount the module itself
    tool = MyTool()
    await coordinator.mount("tools", tool, name="my-tool")
    
    # 2. Register capabilities for other modules
    coordinator.register_capability("my-tool.analyze", tool.analyze)
    
    # 3. Access other modules
    context = coordinator.get("context")
    
    # 4. Register cleanup
    async def cleanup():
        await tool.shutdown()
    
    coordinator.register_cleanup(cleanup)
    return cleanup
```

#### mount

Mounts a module at a specific mount point, making it available to other modules in the system. Mount points have different behaviors: single-module points (orchestrator, context) replace existing modules, while multi-module points (providers, tools) maintain a dictionary by name.

```python
async def mount(
    mount_point: str,
    module: Any,
    name: str | None = None
) -> None
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mount_point` | `str` | Required | Where to mount: `"orchestrator"`, `"providers"`, `"tools"`, `"context"`, `"module-source-resolver"` |
| `module` | `Any` | Required | The module instance implementing the appropriate protocol |
| `name` | `str \| None` | `None` | Module name (required for multi-module mount points, optional for single) |

**Returns:** `None`

**Raises:** 
- `ValueError` - If mount point is unknown, name is missing for multi-module points, or attempting to mount at "hooks"

```python
# Single-module mount point (replaces existing)
await coordinator.mount("orchestrator", orchestrator_instance)
await coordinator.mount("context", context_instance)

# Multi-module mount point (requires name)
await coordinator.mount("providers", provider, name="anthropic")
await coordinator.mount("tools", tool, name="bash")

# Auto-detect name from module.name property
class MyTool:
    @property
    def name(self) -> str:
        return "my-tool"

tool = MyTool()
await coordinator.mount("tools", tool)  # Uses tool.name automatically
```

**Mount Point Behaviors:**

| Mount Point | Cardinality | Name Required | Behavior |
|-------------|-------------|---------------|----------|
| `orchestrator` | Single | No | Replaces existing (warns if replacing) |
| `context` | Single | No | Replaces existing |
| `module-source-resolver` | Single | No | Replaces existing |
| `providers` | Multiple | Yes (or auto) | Stores in dict by name |
| `tools` | Multiple | Yes (or auto) | Stores in dict by name |
| `hooks` | Built-in | N/A | Use `hooks.register()` instead |

**Note:** The `hooks` mount point contains the built-in `HookRegistry`. Hook handlers should be registered using `coordinator.hooks.register()` rather than mounting through `mount()`.

#### unmount

Removes a module from a mount point, cleaning up its registration. For single-module mount points, this sets the slot to `None`. For multi-module mount points, it removes the named entry from the dictionary.

```python
async def unmount(
    mount_point: str,
    name: str | None = None
) -> None
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mount_point` | `str` | Required | Mount point to unmount from |
| `name` | `str \| None` | `None` | Module name (required for multi-module mount points) |

**Returns:** `None`

**Raises:** `ValueError` - If mount point is unknown or name is missing for multi-module points

```python
# Unmount single-module mount point
await coordinator.unmount("orchestrator")
await coordinator.unmount("context")

# Unmount from multi-module mount point (name required)
await coordinator.unmount("providers", name="anthropic")
await coordinator.unmount("tools", name="bash")

# Example: Hot-swap a provider
await coordinator.unmount("providers", name="openai")
await coordinator.mount("providers", new_provider, name="openai")
```

**Note:** Unmounting does not automatically call cleanup functions registered with `register_cleanup()`. Modules should handle their own cleanup in their registered cleanup function before unmounting.

#### get

Retrieves a mounted module or dictionary of modules from a mount point. For single-module mount points, returns the module instance or `None`. For multi-module mount points, returns a dictionary when no name is specified, or a specific module when a name is provided.

```python
def get(
    mount_point: str,
    name: str | None = None
) -> Any
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mount_point` | `str` | Required | Mount point to get from |
| `name` | `str \| None` | `None` | Module name (for multi-module mount points) |

**Returns:** `Any` - The mounted module, dictionary of modules, or `None`

**Raises:** `ValueError` - If mount point is unknown

```python
# Get single-module mount points
orchestrator = coordinator.get("orchestrator")
context = coordinator.get("context")
hooks = coordinator.get("hooks")

# Get all modules at a multi-module mount point
all_providers = coordinator.get("providers")  # Returns dict[str, Provider]
all_tools = coordinator.get("tools")          # Returns dict[str, Tool]

# Get specific module by name
anthropic = coordinator.get("providers", "anthropic")
bash_tool = coordinator.get("tools", "bash")

# Check if module exists
if coordinator.get("providers", "openai") is not None:
    # OpenAI provider is available
    pass
```

**Return Type Examples:**

```python
# Single-module mount points
orchestrator: Orchestrator | None = coordinator.get("orchestrator")

# Multi-module without name
providers: dict[str, Provider] = coordinator.get("providers")

# Multi-module with name
provider: Provider | None = coordinator.get("providers", "anthropic")
```

**Note:** The return type is `Any` for flexibility, but follows predictable patterns. Single-module mount points return the instance or `None`. Multi-module mount points return a dict when accessed without a name, or the specific module (or `None`) when accessed with a name.

#### register_cleanup

Registers a cleanup function to be called during session shutdown. Cleanup functions are executed in reverse registration order (LIFO), ensuring proper dependency teardown.

```python
def register_cleanup(cleanup_fn: Callable) -> None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `cleanup_fn` | `Callable` | Function to call on shutdown (can be sync or async) |

**Returns:** `None`

**Cleanup Function Signature:** `def cleanup() -> None` or `async def cleanup() -> None`

```python
# Register sync cleanup
def cleanup_sync():
    logger.info("Cleaning up sync resources")

coordinator.register_cleanup(cleanup_sync)

# Register async cleanup
async def cleanup_async():
    await connection.close()
    logger.info("Cleaned up async resources")

coordinator.register_cleanup(cleanup_async)

# Common pattern: return cleanup from mount function
async def mount(coordinator, config):
    tool = MyTool()
    await coordinator.mount("tools", tool, name="my-tool")
    
    async def cleanup():
        await tool.shutdown()
    
    coordinator.register_cleanup(cleanup)
    return cleanup  # Also return for module loader tracking
```

**Execution Order:** Cleanup functions execute in reverse registration order (LIFO/stack). If module A registers first and module B registers second, B's cleanup runs before A's cleanup. This ensures dependencies are torn down in the correct order.

**Error Handling:** Individual cleanup failures are logged but don't prevent other cleanup functions from executing. The coordinator continues processing the cleanup chain even if some functions throw exceptions.

#### register_capability

Registers a capability that other modules can discover and use. Capabilities provide a loose coupling mechanism for inter-module communication without direct dependencies.

```python
def register_capability(
    name: str,
    value: Any
) -> None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Capability name (e.g., `"agents.list"`, `"workspace.get_path"`) |
| `value` | `Any` | The capability (typically a callable, but can be any value) |

**Returns:** `None`

```python
# Register a capability
async def list_agents():
    return ["researcher", "coder", "reviewer"]

coordinator.register_capability("agents.list", list_agents)

# Register multiple related capabilities
coordinator.register_capability("agents.list", list_agents)
coordinator.register_capability("agents.get", get_agent_config)
coordinator.register_capability("agents.spawn", spawn_agent)

# Register data capability (not just functions)
coordinator.register_capability("workspace.path", "/home/user/project")
coordinator.register_capability("session.user_id", "user_123")
```

**Naming Convention:** Use dot-notation for capability names (`module.action`) to create logical namespaces. This prevents collisions and makes capabilities self-documenting.

**Use Case:** Capabilities are ideal for optional dependencies. A task tool can register agent spawning capabilities without requiring all sessions to load task infrastructure. Other modules check for capability existence before using it.

#### get_capability

Retrieves a registered capability by name. Returns `None` if the capability doesn't exist, allowing modules to gracefully handle missing capabilities.

```python
def get_capability(name: str) -> Any | None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Capability name to retrieve |

**Returns:** `Any | None` - The capability if registered, `None` otherwise

```python
# Check and use a capability
list_agents = coordinator.get_capability("agents.list")
if list_agents:
    agents = await list_agents()
    logger.info(f"Available agents: {agents}")
else:
    logger.info("Agent system not available")

# Capability-based feature detection
if coordinator.get_capability("workspace.path"):
    # Workspace features available
    path = coordinator.get_capability("workspace.path")
    logger.info(f"Working in: {path}")

# Type-safe capability usage
from typing import Callable

spawn_agent: Callable | None = coordinator.get_capability("agents.spawn")
if spawn_agent:
    await spawn_agent("researcher", task="analyze codebase")
```

**Pattern:** Check for capability existence before use. This enables graceful degradation when optional features aren't available and allows modules to adapt to different system configurations.

#### register_contributor

Registers a module as a contributor to a named channel. Contributions are collected on-demand using `collect_contributions()`. This provides a generic aggregation mechanism for gathering data from multiple modules.

```python
def register_contributor(
    channel: str,
    name: str,
    callback: Callable[[], Any] | Callable[[], Awaitable[Any]]
) -> None
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `channel` | `str` | Channel name (e.g., `"observability.events"`, `"capabilities"`) |
| `name` | `str` | Module name for debugging and logging |
| `callback` | `Callable` | Function returning contribution (can be sync or async, can return `None`) |

**Returns:** `None`

**Callback Signature:** `def contribute() -> Any` or `async def contribute() -> Any`

```python
# Register event contributions
async def contribute_events():
    return [
        "tool:execute",
        "tool:complete",
        "tool:error"
    ]

coordinator.register_contributor(
    channel="observability.events",
    name="tool-bash",
    callback=contribute_events
)

# Register capability contributions
def contribute_capabilities():
    return {
        "bash.execute": execute_command,
        "bash.validate": validate_syntax
    }

coordinator.register_contributor(
    channel="capabilities",
    name="tool-bash",
    callback=contribute_capabilities
)

# Conditional contribution (return None to skip)
def contribute_metrics():
    if enable_metrics:
        return get_current_metrics()
    return None  # Filtered out during collection

coordinator.register_contributor(
    channel="metrics.snapshot",
    name="my-module",
    callback=contribute_metrics
)
```

**Channel Semantics:** The kernel doesn't interpret channels or contributions - it's purely a mechanism. Callers of `collect_contributions()` define the meaning and format. This enables app-layer protocols without kernel involvement.

#### collect_contributions

Collects all contributions from a named channel by calling registered contributor callbacks. Returns raw contributions with `None` values filtered out. Caller interprets the format and aggregates as needed.

```python
async def collect_contributions(channel: str) -> list[Any]
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `channel` | `str` | Channel name to collect from |

**Returns:** `list[Any]` - List of non-None contributions from all registered contributors

```python
# Collect event contributions
events = await coordinator.collect_contributions("observability.events")
# Returns: [["tool:execute", "tool:complete"], ["session:start"], ...]

# Flatten event lists
all_events = []
for contribution in events:
    if isinstance(contribution, list):
        all_events.extend(contribution)

# Collect capability contributions
capabilities = await coordinator.collect_contributions("capabilities")
# Returns: [{"bash.execute": <fn>, ...}, {"workspace.path": <fn>, ...}]

# Merge capability dicts
merged = {}
for contribution in capabilities:
    if isinstance(contribution, dict):
        merged.update(contribution)
```

**Error Handling:** Individual contributor failures are logged but don't break the collection process. If one contributor throws an exception, other contributors still execute and their contributions are returned.

**Use Cases:** 
- **Event Aggregation** - Collect all events emitted by modules for documentation
- **Capability Discovery** - Gather all capabilities available in the session
- **Metrics Collection** - Snapshot current metrics from all modules
- **Plugin Registration** - Collect plugin registrations from modules

#### process_hook_result

Processes a `HookResult` from hook execution and routes actions to appropriate subsystems. This method bridges hook handlers and the infrastructure needed to fulfill their actions (context injection, approvals, user messages).

```python
async def process_hook_result(
    result: HookResult,
    event: str,
    hook_name: str = "unknown"
) -> HookResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result` | `HookResult` | Required | HookResult from hook handler execution |
| `event` | `str` | Required | Event name that triggered the hook |
| `hook_name` | `str` | `"unknown"` | Hook name for logging and audit trails |

**Returns:** `HookResult` - Processed result (may be modified by approval flow)

```python
# Typically called by orchestrator after hook emission
hook_result = await coordinator.hooks.emit("tool:pre", tool_data)
processed = await coordinator.process_hook_result(
    result=hook_result,
    event="tool:pre",
    hook_name="security-validator"
)

# Check processed result
if processed.action == "deny":
    raise PermissionError(processed.reason)
```

**Processing Flow:**

1. **Context Injection** - If `action="inject_context"`, adds content to context manager with provenance metadata
2. **Approval Request** - If `action="ask_user"`, delegates to approval system and returns modified result
3. **User Message** - If `user_message` is set, routes to display system
4. **Output Suppression** - If `suppress_output=True`, logs the request (orchestrator implements filtering)

**Budget Enforcement:** Context injections respect `session.injection_budget_per_turn` and `session.injection_size_limit` from config. Exceeding size limit raises `ValueError`. Exceeding budget logs a warning but allows injection (kernel mechanism, not hard policy).

**Subsystem Requirements:** The method requires `approval_system` and `display_system` to be injected into the coordinator (app-layer responsibility). If missing, approval requests fail and user messages fall back to logging.

#### cleanup

Executes all registered cleanup functions in reverse registration order (LIFO). Handles both sync and async cleanup functions automatically.

```python
async def cleanup() -> None
```

**Parameters:** None

**Returns:** `None`

```python
# Called by session during shutdown
async with AmplifierSession(config) as session:
    await session.execute("Do work")
# session.__aexit__ calls coordinator.cleanup()

# Manual cleanup
await coordinator.cleanup()
```

**Execution Behavior:**

- Cleanup functions execute in **reverse registration order** (LIFO/stack)
- Both sync and async functions are supported and handled automatically
- Individual failures are logged but don't stop cleanup chain
- Exceptions are caught and logged, preventing cleanup cascade failures

**Example Cleanup Order:**

```python
# Registration order
coordinator.register_cleanup(cleanup_a)  # Registered first
coordinator.register_cleanup(cleanup_b)  # Registered second
coordinator.register_cleanup(cleanup_c)  # Registered third

# Execution order (reversed)
await coordinator.cleanup()
# Calls: cleanup_c() → cleanup_b() → cleanup_a()
```

**Note:** Session's `cleanup()` method calls `coordinator.cleanup()` and then `loader.cleanup()` to ensure complete resource teardown.

#### reset_turn

Resets per-turn tracking counters. Called at turn boundaries to reset token budget tracking for context injections.

```python
def reset_turn() -> None
```

**Parameters:** None

**Returns:** `None`

```python
# Called by orchestrator at turn boundaries
async def execute_turn(prompt):
    coordinator.reset_turn()  # Reset budget tracking
    
    # Process turn...
    messages = await context.get_messages()
    response = await provider.complete(messages)
    
    # Injections during this turn count against budget
    await coordinator.process_hook_result(injection_result, "tool:post", "linter")
```

**Tracked State:** Currently resets `_current_turn_injections` counter used for enforcing `injection_budget_per_turn` policy. This counter tracks estimated tokens from context injections.

**Note:** Turn boundary management is orchestrator policy. The kernel provides the mechanism (`reset_turn()`) but doesn't define when turns begin or end.

### Hook Result Processing

The coordinator provides specialized processing for `HookResult` actions that require infrastructure coordination. When hooks return results with actions like `inject_context`, `ask_user`, or set fields like `user_message`, the coordinator routes these to appropriate subsystems.

**Processing Pipeline:**

```python
# Orchestrator flow with hook result processing
result = await coordinator.hooks.emit("tool:pre", tool_data)

if result.action != "continue":
    # Process the result through coordinator
    processed = await coordinator.process_hook_result(
        result=result,
        event="tool:pre",
        hook_name="security"
    )
    
    # Handle final result
    if processed.action == "deny":
        raise PermissionError(processed.reason)
```

**Subsystem Routing:**

| HookResult Field | Subsystem | Coordinator Responsibility |
|------------------|-----------|---------------------------|
| `context_injection` | Context Manager | Add message with provenance metadata, enforce size/budget limits |
| `approval_prompt` | Approval System | Delegate to UI, handle timeout, convert decision to continue/deny |
| `user_message` | Display System | Route message with severity level to UI |
| `suppress_output` | Orchestrator | Log request (orchestrator implements filtering) |

**Context Injection Processing:**

```python
# Coordinator handles context injection
if result.action == "inject_context":
    # 1. Validate size against injection_size_limit
    if len(result.context_injection) > coordinator.injection_size_limit:
        raise ValueError("Context injection exceeds size limit")
    
    # 2. Track token budget (if configured)
    tokens = len(result.context_injection) // 4
    coordinator._current_turn_injections += tokens
    if coordinator._current_turn_injections > coordinator.injection_budget_per_turn:
        logger.warning("Injection budget exceeded")
    
    # 3. Add to context with provenance (if not ephemeral)
    if not result.ephemeral:
        await context.add_message({
            "role": result.context_injection_role,
            "content": result.context_injection,
            "metadata": {
                "source": "hook",
                "hook_name": hook_name,
                "event": event,
                "timestamp": datetime.now().isoformat()
            }
        })
```

**Approval Request Processing:**

```python
# Coordinator delegates to approval system
if result.action == "ask_user":
    # 1. Extract approval parameters
    prompt = result.approval_prompt or "Allow this operation?"
    options = result.approval_options or ["Allow", "Deny"]
    
    # 2. Request approval from user (blocks until response/timeout)
    decision = await coordinator.approval_system.request_approval(
        prompt=prompt,
        options=options,
        timeout=result.approval_timeout,
        default=result.approval_default
    )
    
    # 3. Convert decision to HookResult
    if decision == "Deny":
        return HookResult(action="deny", reason=f"User denied: {prompt}")
    return HookResult(action="continue")
```

**Ephemeral Injection Handling:**

Ephemeral injections (`ephemeral=True`) are NOT stored in context history. The orchestrator must append them to the current LLM call's messages:

```python
# Orchestrator handles ephemeral injections
messages = await context.get_messages()

# Process hook and check for ephemeral injection
result = await coordinator.process_hook_result(hook_result, "tool:post", "reminder")

if result.action == "inject_context" and result.ephemeral:
    # Append to current call only (don't store)
    ephemeral_message = {
        "role": result.context_injection_role,
        "content": result.context_injection
    }
    
    if result.append_to_last_tool_result and messages[-1].get("role") == "tool":
        # Append to last tool result
        messages[-1]["content"] += "\n\n" + result.context_injection
    else:
        # Add as new message
        messages.append(ephemeral_message)
    
    # Use messages with ephemeral content for this call only
    response = await provider.complete(messages)
```

### Capability System

The coordinator provides a lightweight capability registry for inter-module communication without tight coupling. Modules register capabilities they provide and query for capabilities they need, enabling flexible composition.

**Capability Pattern:**

```python
# Provider module registers capabilities
async def mount(coordinator, config):
    tool = MyTool()
    
    # Register capabilities for discovery
    coordinator.register_capability("my-tool.execute", tool.execute)
    coordinator.register_capability("my-tool.validate", tool.validate)
    coordinator.register_capability("my-tool.config", tool.get_config)
```

```python
# Consumer module uses capabilities
async def mount(coordinator, config):
    # Check if capability exists
    execute_fn = coordinator.get_capability("my-tool.execute")
    
    if execute_fn:
        # Use the capability
        result = await execute_fn({"param": "value"})
    else:
        # Graceful degradation
        logger.info("my-tool not available, using fallback")
```

**Common Capability Patterns:**

| Pattern | Example Name | Purpose |
|---------|--------------|---------|
| **Action** | `module.action` | Function that performs an operation |
| **Query** | `module.get_*` | Function that retrieves data |
| **Configuration** | `module.config` | Module configuration or settings |
| **Data** | `workspace.path` | Simple value (not a function) |
| **Factory** | `module.create` | Function that creates instances |

**Capability Namespacing:**

Use dot-notation to create logical namespaces and prevent collisions:

```python
# Agent system capabilities
coordinator.register_capability("agents.list", list_agents)
coordinator.register_capability("agents.get", get_agent_config)
coordinator.register_capability("agents.spawn", spawn_agent)

# Workspace capabilities
coordinator.register_capability("workspace.path", "/home/user/project")
coordinator.register_capability("workspace.read_file", read_file)
coordinator.register_capability("workspace.write_file", write_file)

# Observability capabilities
coordinator.register_capability("observability.emit", emit_metric)
coordinator.register_capability("observability.flush", flush_metrics)
```

**Type-Safe Capability Usage:**

```python
from typing import Callable, Awaitable

# Define capability interface
SpawnAgentFn = Callable[[str, dict], Awaitable[str]]

# Get and use with type safety
spawn_agent: SpawnAgentFn | None = coordinator.get_capability("agents.spawn")
if spawn_agent:
    session_id = await spawn_agent("researcher", {"max_iterations": 10})
```

**Capability Discovery:**

The contribution channel system can aggregate capabilities for discovery:

```python
# Modules contribute their capabilities
def contribute_capabilities():
    return {
        "my-tool.execute": tool.execute,
        "my-tool.validate": tool.validate
    }

coordinator.register_contributor(
    channel="capabilities",
    name="my-tool",
    callback=contribute_capabilities
)

# Collector aggregates all capabilities
all_capabilities = await coordinator.collect_contributions("capabilities")
merged = {}
for cap_dict in all_capabilities:
    if isinstance(cap_dict, dict):
        merged.update(cap_dict)

# Now all capabilities are in one dict
for name, capability in merged.items():
    print(f"Available: {name}")
```

### Examples

The following examples demonstrate common coordinator usage patterns in module development. Each example shows real-world scenarios for mounting modules, registering capabilities, processing hook results, and managing cleanup.

These examples progress from basic module mounting to advanced patterns like capability registration and hook result processing. All examples assume the coordinator is passed to the module's `mount()` function.

```python
# Basic module structure used in examples
from amplifier_core.models import HookResult

async def mount(coordinator, config):
    # Module initialization and registration
    # ...
    return cleanup_function
```

#### Basic Module Mounting

The most common pattern: mount a module, access infrastructure context, and register cleanup.

```python
async def mount(coordinator, config):
    """Basic tool module mounting pattern."""
    # Create tool instance
    tool = MyTool(config.get("setting", "default"))
    
    # Access infrastructure context
    logger.info(f"Mounting in session {coordinator.session_id}")
    
    # Mount the tool
    await coordinator.mount("tools", tool, name="my-tool")
    
    # Register cleanup
    async def cleanup():
        await tool.shutdown()
        logger.info("Tool cleanup complete")
    
    coordinator.register_cleanup(cleanup)
    return cleanup
```

**Pattern:** Create instance → Access context → Mount → Register cleanup. This is the standard module structure that works for all module types.

#### Multi-Module Access

Accessing other mounted modules to integrate with existing infrastructure.

```python
async def mount(coordinator, config):
    """Hook module that needs access to context and tools."""
    # Get mounted modules
    context = coordinator.get("context")
    all_tools = coordinator.get("tools")
    bash_tool = coordinator.get("tools", "bash")
    
    # Check if required modules exist
    if context is None:
        raise RuntimeError("Context manager required")
    
    # Create hook that uses other modules
    async def tool_logger(event: str, data: dict) -> HookResult:
        tool_name = data.get("tool_name")
        
        # Log tool execution
        logger.info(f"Tool {tool_name} executing")
        
        # Could inject context
        if tool_name == "bash":
            await context.add_message({
                "role": "system",
                "content": f"Bash command logged at {datetime.now()}"
            })
        
        return HookResult(action="continue")
    
    # Register hook
    coordinator.hooks.register("tool:pre", tool_logger, priority=10)
```

**Pattern:** Use `get()` to access other modules, check for `None`, integrate across module boundaries.

#### Capability Registration

Registering capabilities for other modules to discover and use.

```python
async def mount(coordinator, config):
    """Agent system registering capabilities for task tool."""
    agent_configs = config.get("agents", {})
    
    async def list_agents() -> list[str]:
        """List available agent configurations."""
        return list(agent_configs.keys())
    
    async def get_agent_config(agent_id: str) -> dict:
        """Get configuration for specific agent."""
        return agent_configs.get(agent_id, {})
    
    async def spawn_agent(agent_id: str, task: str) -> str:
        """Spawn a child session with agent config."""
        agent_config = agent_configs.get(agent_id)
        if not agent_config:
            raise ValueError(f"Unknown agent: {agent_id}")
        
        # Spawn child session
        child_config = coordinator.session._merge_configs(
            coordinator.config,
            agent_config
        )
        
        child = AmplifierSession(
            config=child_config,
            parent_id=coordinator.session_id
        )
        
        async with child as session:
            result = await session.execute(task)
            return result
    
    # Register capabilities
    coordinator.register_capability("agents.list", list_agents)
    coordinator.register_capability("agents.get", get_agent_config)
    coordinator.register_capability("agents.spawn", spawn_agent)
    
    logger.info("Agent capabilities registered")
```

**Pattern:** Define functions that other modules need, register them with namespaced names, document the interface in module docs.

#### Hook Result Processing

Processing hook results with context injection and approval requests.

```python
async def execute_with_hooks(coordinator, tool_name: str, tool_input: dict):
    """Orchestrator pattern for hook result processing."""
    # Emit pre-hook
    pre_result = await coordinator.hooks.emit("tool:pre", {
        "tool_name": tool_name,
        "tool_input": tool_input
    })
    
    # Process result through coordinator
    processed = await coordinator.process_hook_result(
        result=pre_result,
        event="tool:pre",
        hook_name="security"
    )
    
    # Handle denial
    if processed.action == "deny":
        logger.warning(f"Tool {tool_name} blocked: {processed.reason}")
        raise PermissionError(processed.reason)
    
    # Handle modification
    if processed.action == "modify":
        tool_input = processed.data.get("tool_input", tool_input)
    
    # Execute tool
    result = await tool.execute(tool_input)
    
    # Emit post-hook with result
    post_result = await coordinator.hooks.emit("tool:post", {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_result": result
    })
    
    # Process post-hook (might inject context)
    await coordinator.process_hook_result(
        result=post_result,
        event="tool:post",
        hook_name="linter"
    )
    
    return result
```

**Pattern:** Emit hook → Process result → Handle actions → Continue execution. This is the standard orchestrator pattern for integrating hooks.

#### Contribution Channel

Using contribution channels to aggregate data from multiple modules.

```python
async def mount(coordinator, config):
    """Module contributing to observability events channel."""
    # Define events this module emits
    def contribute_events():
        return [
            "my-module:started",
            "my-module:completed",
            "my-module:error"
        ]
    
    # Register as contributor
    coordinator.register_contributor(
        channel="observability.events",
        name="my-module",
        callback=contribute_events
    )
```

```python
# Collector aggregates all contributions
async def collect_all_events(coordinator):
    """Collect all events from all modules."""
    contributions = await coordinator.collect_contributions("observability.events")
    
    # Flatten list of lists
    all_events = []
    for contribution in contributions:
        if isinstance(contribution, list):
            all_events.extend(contribution)
    
    # Remove duplicates and sort
    unique_events = sorted(set(all_events))
    
    logger.info(f"System emits {len(unique_events)} unique events")
    return unique_events
```

**Pattern:** Contributors register lightweight callbacks, collector aggregates and interprets. This enables event documentation, capability discovery, and dynamic system introspection.

#### Child Session Spawning

Creating child sessions for delegation workflows.

```python
async def delegate_task(coordinator, task: str, agent_config: dict) -> str:
    """Spawn child session for delegated task."""
    # Get parent session
    parent = coordinator.session
    
    # Merge agent config overlay
    child_config = parent._merge_configs(parent.config, agent_config)
    
    # Create child session with lineage tracking
    child = AmplifierSession(
        config=child_config,
        session_id=None,  # Generate new ID
        parent_id=coordinator.session_id  # Track parent
    )
    
    # Execute in child session
    async with child as session:
        logger.info(f"Child session {session.session_id} spawned from {coordinator.session_id}")
        result = await session.execute(task)
        return result
    
    # Child session cleanup automatic via context manager
```

**Pattern:** Access parent session → Merge configs → Create child with parent_id → Execute and cleanup. Child sessions inherit module configuration but maintain separate conversation contexts.

## See Also

- **[Session API](docs/api/core/session.md)** - Complete specification for AmplifierSession lifecycle and configuration
- **[Hooks API](docs/api/core/hooks.md)** - Hook system that coordinator processes and coordinates
- **[Module Contracts](docs/contracts/README.md)** - Protocol definitions for all module types
- **[Mount Plan Specification](docs/specifications/MOUNT_PLAN.md)** - Configuration format for session initialization
- **[Session Forking](docs/specifications/SESSION_FORK.md)** - Child session creation and lineage tracking
- **[Design Philosophy](docs/DESIGN_PHILOSOPHY.md)** - Kernel principles of mechanism vs policy
