# Kernel Philosophy

The Amplifier kernel follows a philosophy directly inspired by the Linux kernel: **provide mechanisms, not policy**. This fundamental principle shapes every design decision, from what code belongs in the kernel core to how modules interact with the system.

Just as the Linux kernel provides syscalls, memory management, and process scheduling without dictating how applications should behave, the Amplifier kernel provides session management, event dispatch, and module loading capabilities while leaving all behavioral decisions to modules. The kernel is deliberately small, stable, and boring—a reliable foundation that changes rarely so that innovation can happen rapidly at the edges.

This philosophy creates a clear separation of concerns: the kernel implements **mechanisms** (the "how" of capabilities), while modules implement **policies** (the "what" and "when" of behavior). If two teams might want different behavior for the same capability, that's a strong signal the functionality belongs in a module, not the kernel.

The Linux kernel metaphor provides a powerful decision framework. When facing unclear requirements, we map Amplifier concepts to their Linux equivalents:

| Linux Concept | Amplifier Analog | Design Implication |
|---------------|------------------|-------------------|
| Ring 0 kernel | `amplifier-core` | Mechanisms only, never policy decisions |
| Syscalls | Session operations | Few, stable APIs: `create_session()`, `mount()`, `emit()` |
| Loadable drivers | Modules | Compete at edges, comply with protocols |
| Signals/events | Event bus | Non-blocking observation of kernel lifecycle |
| /proc filesystem | Unified JSONL log | Single source of truth for all diagnostics |

This architecture enables several key benefits:

**Parallel Innovation**: Multiple teams can develop competing modules simultaneously without coordinating kernel changes. A team building a streaming orchestrator and another building a planning orchestrator both use the same kernel mechanisms but implement completely different policies.

**Backward Compatibility**: The kernel maintains stable contracts that don't break existing modules. New capabilities are added additively, and deprecations follow long sunset periods with clear migration paths.

**Regenerative Development**: Modules are designed as self-contained "bricks" with clear interfaces. When requirements change, modules can be regenerated from specifications rather than incrementally patched, enabling AI-assisted development workflows.

**Observable by Default**: Every important action emits canonical events to a unified JSONL stream. This event-first approach means the system's behavior is always inspectable and debuggable without hidden state or magic globals.

The philosophy extends beyond code architecture to development practices. We start with vertical slices that prove end-to-end value, then expand horizontally. We prototype at module boundaries first, only extracting common patterns to the kernel after multiple implementations converge on the same need. We ruthlessly prioritize simplicity, questioning every abstraction and minimizing the number of moving parts.

This kernel philosophy creates a system where the center stays still so the edges can move fast. The kernel provides a stable, predictable foundation while modules compete through better policies, innovative approaches, and specialized capabilities. The result is a platform that can evolve rapidly without breaking existing functionality—exactly the kind of reliable foundation needed for AI agent development.

## Core Tenets

Four fundamental tenets guide every design decision in Amplifier, creating a coherent philosophy that ensures the system remains maintainable, extensible, and reliable as it evolves. These tenets work together to establish clear boundaries between what belongs in the kernel versus modules, how components should interact, and how the system can grow without breaking existing functionality.

These principles are not abstract ideals but practical guidelines with concrete implications for code organization, API design, and development workflows. Each tenet addresses a specific aspect of system architecture while reinforcing the others to create a unified approach to building AI agent infrastructure.

The tenets emerge from hard-learned lessons in software architecture: that mixing mechanism with policy creates brittle systems, that complexity grows exponentially without deliberate constraints, that backward compatibility is sacred for platform adoption, and that composition scales better than inheritance for complex behaviors.

Together, these four tenets create a decision framework that helps developers determine where functionality belongs, how components should interact, and how to evolve the system safely. They provide the conceptual foundation for the Linux kernel metaphor and inform every aspect of Amplifier's architecture, from the smallest API design to the largest system boundaries.

Understanding these tenets is essential for anyone working with Amplifier, whether building new modules, contributing to the kernel, or simply trying to understand why the system is designed the way it is. They represent the distilled wisdom that guides all technical decisions and ensures the platform remains true to its core mission of providing a stable foundation for AI agent development.

### 1. Mechanism, Not Policy

The kernel provides capabilities and stable contracts while leaving all behavioral decisions to modules. This fundamental separation ensures that the core system remains small, stable, and unopinionated while enabling diverse policies to compete at the edges.

When the kernel exposes a mechanism like `mount()` or `emit()`, it defines *how* something can be done but never *what* should be done. The decision of which provider to use, how to orchestrate execution, or what to log belongs entirely outside the kernel. This separation allows multiple teams to build different solutions using the same underlying infrastructure.

| Kernel Responsibilities (Mechanism) | Module Responsibilities (Policy) |
|-------------------------------------|----------------------------------|
| Stable contracts and protocols | Provider and model selection |
| Module loading/unloading (`mount`/`unmount`) | Orchestration strategy (basic, streaming, planning) |
| Event dispatch (`emit` lifecycle events) | Tool behavior and execution logic |
| Capability checks (enforcement mechanism) | Output formatting and logging destinations |
| Minimal context plumbing (session_id, request_id) | Product decisions and user experience |
| **Never:** Select, optimize, format, route, or plan | Configuration resolution and defaults |

The coordinator exemplifies this principle by providing infrastructure context—session IDs, mount point access, and module loading capabilities—without making decisions about how modules should use these mechanisms:

```python
# Kernel provides mechanism: capability registration
coordinator.register_capability('agents.list', agent_list_function)

# Modules decide policy: which capabilities to register and how
def my_agent_policy():
    return [agent for agent in agents if agent.status == 'active']

coordinator.register_capability('agents.active', my_agent_policy)
```

The litmus test for this boundary is simple: **if two teams could reasonably want different behavior, it's policy and belongs in a module**. For example, one team might want to log everything to files while another prefers structured events to a database. The kernel provides the `emit()` mechanism; hook modules implement the logging policies.

This separation enables the system to evolve without breaking existing functionality. New orchestration strategies can be implemented as modules without touching kernel code. Different providers can compete by offering better policies while using the same mounting mechanisms. The kernel's job is to make these diverse policies possible, not to choose between them.

When requirements seem unclear, ask: "Could another team legitimately want to do this differently?" If the answer is yes, build it as a module that uses kernel mechanisms rather than extending the kernel itself. This keeps the core system focused on providing stable, general-purpose capabilities that many different policies can leverage.

### 2. Small, Stable, and Boring

The kernel is intentionally minimal at approximately 2,600 lines of code and follows a philosophy of deliberate constraint. Changes to the kernel are rare events that require extraordinary justification, and backward compatibility is treated as sacred. This approach ensures the system remains comprehensible, reliable, and maintainable over time.

**Small** means the entire kernel can be audited and understood in a single afternoon. Every line of code must justify its existence, and the default response to new requirements is to find ways to address them through modules rather than kernel expansion. The coordinator and core infrastructure provide just enough mechanism to enable rich policies at the edges without becoming complex themselves.

**Stable** means backward compatibility is never compromised. Existing modules must continue to work without modification when the kernel evolves. This stability enables teams to build on the platform with confidence, knowing their investments won't be invalidated by kernel changes. When evolution is necessary, it follows additive patterns with clear deprecation windows and migration paths.

**Boring** means no clever tricks, no surprises, and no magic. The kernel favors explicit, predictable behavior over elegant abstractions. Code should be immediately comprehensible to any maintainer, with clear data flows and obvious failure modes. Innovation and cleverness belong in modules where they can compete and evolve rapidly without affecting system stability.

This philosophy creates a virtuous cycle: because the kernel is small, it's easier to keep stable. Because it's stable, teams trust it enough to build sophisticated modules. Because innovation happens in modules, the kernel can remain boring and focused. The result is a system where the center stays still so the edges can move fast.

The two-implementation rule enforces this discipline: kernel features require evidence from at least two independent modules that need the same mechanism. This prevents premature generalization and ensures that kernel additions solve real, proven needs rather than hypothetical futures. When in doubt, the answer is always to prototype at the edges first and extract common mechanisms only after patterns emerge from actual usage.

### 3. Don't Break Modules

Backward compatibility in kernel interfaces is sacred and non-negotiable. Once a module can successfully mount and operate with the kernel, that contract must be preserved indefinitely. This principle ensures that teams can build on Amplifier with confidence, knowing their investments won't be invalidated by future kernel changes.

The kernel follows three strict principles for evolution that protect existing modules:

**Additive Evolution Only**: All kernel changes must be purely additive. New capabilities can be introduced through optional fields in schemas, additional event types, or extended protocols that modules can choose to adopt. Existing functionality must continue to work exactly as before. If a change would require modifying how existing modules operate, it belongs in a new module rather than the kernel.

**Clear Deprecation with Migration Paths**: When removal becomes absolutely necessary, the kernel provides explicit deprecation notices with dual-path support. Both old and new approaches must coexist during the transition period, allowing modules to migrate at their own pace. Deprecation warnings appear in the unified JSONL log stream with clear guidance on migration steps and timelines.

**Long Sunset Periods for Changes**: Deprecated functionality remains supported for extended periods, typically measured in quarters rather than weeks. This gives module maintainers sufficient time to plan and execute migrations without disrupting their development cycles. The kernel errs on the side of maintaining compatibility longer rather than forcing rapid changes.

These principles create a stable foundation that enables innovation at the edges. Modules can experiment with new approaches, compete through better policies, and evolve rapidly while relying on unchanging kernel mechanisms. The result is a system where sophisticated functionality emerges from simple, stable building blocks rather than complex, evolving abstractions.

When evaluating potential kernel changes, the compatibility test is simple: would this require any existing module to modify its code to continue working? If yes, the change either needs redesign as an additive enhancement or implementation as a competing module that demonstrates superior approaches through actual usage rather than forced migration.

### 4. Extensibility Through Composition

New behavior in Amplifier comes from plugging in different modules, not from toggling configuration flags. This composition-based approach prevents the exponential growth of configuration options while maintaining clean separation between mechanism (what the kernel provides) and policy (how modules behave).

The kernel uses a simple type-to-mount-point mapping to enable plug-and-play extensibility. When a module declares its type through the `__amplifier_module_type__` attribute, the kernel automatically derives the correct mount point using a stable mapping:

```python
# Kernel mechanism: stable type → mount point mapping
TYPE_TO_MOUNT_POINT = {
    "orchestrator": "orchestrator",
    "provider": "providers", 
    "tool": "tools",
    "hook": "hooks",
    "context": "context",
    "resolver": "module-source-resolver",
}
```

This design eliminates the need for configuration flags by making behavior changes a matter of swapping modules rather than changing settings.

**Anti-Pattern: Configuration Explosion**

```python
# ❌ Avoid: Flags create exponential complexity
class BadOrchestrator:
    def __init__(self, config):
        self.streaming = config.get("enable_streaming", False)
        self.planning = config.get("enable_planning", False) 
        self.parallel = config.get("enable_parallel", False)
        self.retry_strategy = config.get("retry_strategy", "exponential")
        self.timeout_mode = config.get("timeout_mode", "strict")
        # Every new feature adds more flags...
        
    async def execute(self, request):
        if self.streaming and self.planning:
            # Special case 1
        elif self.streaming and not self.planning:
            # Special case 2  
        elif self.parallel and self.retry_strategy == "linear":
            # Special case 3
        # Exponential growth of code paths...
```

This approach leads to untestable complexity as the number of possible configurations grows exponentially. Teams end up with different bugs in different flag combinations, and the orchestrator becomes impossible to reason about.

**Correct Pattern: Composition Through Modules**

```python
# ✅ Correct: Different modules for different behaviors
# amplifier_module_orchestrator_basic/__init__.py
__amplifier_module_type__ = "orchestrator"

async def mount(coordinator, config):
    async def basic_orchestrator(request):
        # Simple sequential execution
        for step in request.steps:
            result = await execute_step(step)
            if not result.success:
                return result
        return success_result
    
    coordinator.mount("orchestrator", basic_orchestrator)

# amplifier_module_orchestrator_streaming/__init__.py  
__amplifier_module_type__ = "orchestrator"

async def mount(coordinator, config):
    async def streaming_orchestrator(request):
        # Streaming execution with real-time updates
        async for partial_result in stream_execution(request):
            coordinator.emit("orchestrator:progress", partial_result)
            yield partial_result
    
    coordinator.mount("orchestrator", streaming_orchestrator)

# amplifier_module_orchestrator_planning/__init__.py
__amplifier_module_type__ = "orchestrator"  

async def mount(coordinator, config):
    async def planning_orchestrator(request):
        # Multi-step planning with backtracking
        plan = await generate_plan(request)
        return await execute_with_replanning(plan)
    
    coordinator.mount("orchestrator", planning_orchestrator)
```

Each orchestrator module implements a complete, coherent strategy without conditional complexity. Teams choose behavior by mounting different modules, not by setting flags.

The module loader discovers and loads modules based on their declared type, automatically placing them at the correct mount point. This happens through the kernel's composition mechanism:

```python
# Module declares type, kernel derives mount point
module_type = getattr(module, "__amplifier_module_type__", None)
mount_point = TYPE_TO_MOUNT_POINT.get(module_type)

# Kernel mounts module at derived location
coordinator.mount(mount_point, module_implementation)
```

This composition approach extends to all module types. Instead of adding provider selection flags, teams mount different provider modules. Instead of tool configuration options, teams compose different tool modules. Instead of logging flags, teams mount different hook modules that implement their preferred logging policies.

The result is a system where complexity lives in individual modules rather than in combinatorial configuration. Each module can be developed, tested, and reasoned about independently. Teams get exactly the behavior they want by choosing the right modules, and the kernel remains simple because it only provides the mounting mechanism, never the policy decisions.

When teams need new behavior, they write new modules that implement the desired policy. When they need to change behavior, they swap modules. The kernel's stable contracts ensure that module changes don't break the system, while the composition mechanism ensures that new capabilities emerge from module innovation rather than kernel complexity.

## What Belongs in the Kernel

The fundamental question in Amplifier architecture is determining what functionality belongs in the kernel versus what should be implemented as modules. This distinction follows the Linux kernel principle of **mechanism versus policy** - the kernel provides capabilities and stable contracts (mechanisms), while modules make behavioral decisions (policies).

The litmus test for any proposed kernel functionality is simple: **Could two teams want different behavior?** If the answer is yes, it belongs in a module, not the kernel. This principle ensures the kernel remains small, stable, and unopinionated while enabling innovation at the edges through competing module implementations.

Consider the orchestration examples from the previous section. Rather than building a configurable orchestrator with flags for different strategies, Amplifier provides the mounting mechanism in the kernel and lets teams choose between `basic`, `streaming`, or `planning` orchestrator modules. Each module implements a complete strategy without conditional complexity, and teams get exactly the behavior they want by selecting the appropriate module.

This separation creates clear architectural boundaries:

```python
# Kernel provides the mechanism
coordinator.mount("orchestrator", implementation)
coordinator.emit("session:created", event_data)

# Modules provide the policy  
async def planning_orchestrator(request):
    # Module decides HOW to orchestrate
    plan = await generate_plan(request)
    return await execute_with_replanning(plan)
```

The kernel's role is to provide stable contracts that modules can rely on. When a provider module calls `coordinator.emit("provider:response", data)`, it trusts that the kernel will dispatch this event to any registered hooks without the module needing to know which hooks are mounted or how they process events. This contract stability enables modules to be developed independently and composed dynamically.

Evolution follows the **two-implementation rule**: functionality only moves into the kernel after at least two independent modules demonstrate the need for a common mechanism. This prevents premature abstraction and ensures that kernel additions solve real, proven needs rather than hypothetical future requirements.

The kernel maintains backward compatibility as a sacred principle. Existing modules must continue working when the kernel evolves, which constrains kernel changes to be additive and carefully designed. This stability contract is what enables the ecosystem of modules to flourish without constant breakage.

### Kernel Responsibilities (Mechanisms)

The kernel implements five core mechanisms that provide the foundational infrastructure for all module operations. These mechanisms follow the principle of providing capabilities without dictating how they should be used, enabling modules to implement diverse policies while maintaining system coherence.

**Stable Contracts (Protocol Definitions)**

The kernel defines and maintains stable protocols that modules use to interact with the system and each other. These contracts include event schemas, mount point interfaces, and capability registration patterns. For example, when a provider module emits a `provider:response` event, it follows a canonical schema that hooks can reliably process:

```python
# Kernel defines the contract
await coordinator.emit("provider:response", {
    "provider": "anthropic",
    "model": "claude-3-sonnet",
    "content": response_text,
    "usage": {"input_tokens": 150, "output_tokens": 300}
})
```

The kernel maintains these contracts across versions, ensuring that modules developed against one version continue working as the system evolves. This stability enables the ecosystem of modules to grow without constant breakage from kernel changes.

**Lifecycle Coordination (Load/Unload/Mount/Unmount)**

The kernel provides mechanisms for dynamic module management through the `ModuleCoordinator` and `ModuleLoader` classes. Modules are discovered, validated, loaded, and mounted at specific attachment points:

```python
# Kernel provides mounting mechanism
await coordinator.mount("providers", anthropic_provider, "anthropic")
await coordinator.mount("tools", filesystem_tool, "filesystem")

# And unmounting for cleanup
await coordinator.unmount("providers", "anthropic")
```

The loader supports multiple discovery methods including Python entry points, environment variables, and filesystem paths. It handles module validation before loading and tracks dependencies for proper cleanup. The mounting system uses a stable mapping between module types and mount points:

```python
TYPE_TO_MOUNT_POINT = {
    "orchestrator": "orchestrator",
    "provider": "providers", 
    "tool": "tools",
    "hook": "hooks",
    "context": "context"
}
```

**Event Emission (Canonical Events for Observability)**

The kernel provides a unified event system that enables observability without requiring modules to implement their own logging or monitoring. All significant actions flow through canonical events with standardized schemas:

```python
# Kernel injects standard fields into all events
event_data = {
    "session_id": self.session_id,
    "parent_id": self.parent_id, 
    "timestamp": datetime.now().isoformat(),
    **user_data
}
```

Events are dispatched to registered hooks without blocking the main execution flow. The kernel ensures that hook failures don't interfere with core operations, maintaining system reliability while enabling rich observability through hook modules.

**Capability Enforcement (Permission Checks, Approvals)**

The kernel provides mechanisms for capability registration and approval workflows, but delegates policy decisions to modules. The capability registry enables inter-module communication without direct dependencies:

```python
# Modules register capabilities
coordinator.register_capability("agents.list", list_agents_fn)
coordinator.register_capability("agents.get", get_agent_fn)

# Other modules access capabilities
agents_list = coordinator.get_capability("agents.list")
if agents_list:
    available_agents = await agents_list()
```

For approval workflows, the kernel routes requests to the configured approval system but doesn't dictate approval policies:

```python
# Hook requests approval
result = HookResult(
    action="ask_user",
    approval_prompt="Allow file system access?",
    approval_options=["Allow", "Deny"],
    approval_timeout=30
)

# Kernel routes to approval system (policy)
decision = await approval_system.request_approval(
    prompt=result.approval_prompt,
    options=result.approval_options,
    timeout=result.approval_timeout
)
```

**Minimal Context (Session IDs, Basic State)**

The kernel maintains minimal context necessary for module coordination without imposing specific state management policies. This includes session identity, configuration access, and basic tracking:

```python
# Infrastructure context available to all modules
@property
def session_id(self) -> str:
    return self._session.session_id

@property  
def parent_id(self) -> str | None:
    return self._session.parent_id

@property
def config(self) -> dict:
    return self._session.config
```

The kernel tracks per-turn state like injection budgets when configured, but the limits themselves are policy decisions stored in session configuration:

```python
# Kernel provides mechanism
budget = self.injection_budget_per_turn  # From session config
if budget is not None and tokens > budget:
    logger.warning("Injection budget exceeded")

# Policy (limits) comes from configuration
"session": {
    "injection_budget_per_turn": 1000,
    "injection_size_limit": 4096
}
```

This minimal context approach ensures modules have the infrastructure they need while keeping the kernel small and avoiding policy decisions about how context should be managed or what limits should be enforced.

### Kernel Non-Goals (Policies)

The kernel explicitly avoids implementing policies that would constrain how modules operate or make decisions that different teams might want to handle differently. This separation ensures the kernel remains stable and minimal while enabling innovation at the edges.

**Provider and Model Selection**

The kernel never chooses which AI provider to use or which model to invoke. These decisions belong to provider modules and application configuration:

```python
# ❌ Kernel never does this
if task_type == "coding":
    provider = "anthropic"
    model = "claude-3-5-sonnet"
elif task_type == "analysis":
    provider = "openai" 
    model = "gpt-4"

# ✅ Provider modules handle selection
class AnthropicProvider:
    def select_model(self, context):
        # Provider-specific model selection logic
        return self.determine_best_model(context)
```

The kernel provides mounting mechanisms for providers but delegates all selection logic to modules or application-layer configuration.

**Orchestration Strategy**

The kernel does not decide how to execute requests, whether to use streaming, planning, or basic execution. These are orchestrator module responsibilities:

```python
# ❌ Kernel never implements orchestration logic
async def execute_request(self, request):
    if request.complexity > threshold:
        return await self.planning_orchestrator.execute(request)
    else:
        return await self.basic_orchestrator.execute(request)

# ✅ Orchestrator modules compete with different strategies
class PlanningOrchestrator:
    async def execute(self, request):
        # Multi-step planning and execution
        
class StreamingOrchestrator:
    async def execute(self, request):
        # Real-time streaming execution
```

Teams can swap orchestration strategies by mounting different orchestrator modules without kernel changes.

**Tool Behavior and Domain Rules**

The kernel provides tool mounting and capability registration but never dictates how tools should behave or what domain-specific rules they should follow:

```python
# ❌ Kernel never enforces tool behavior
class FileSystemTool:
    def read_file(self, path):
        if path.startswith("/etc/"):
            raise SecurityError("System files forbidden")
        # Tool-specific behavior

# ✅ Tools implement their own behavior policies
class RestrictedFileSystemTool:
    def __init__(self, allowed_paths):
        self.allowed_paths = allowed_paths
        
class UnrestrictedFileSystemTool:
    def __init__(self):
        pass  # No restrictions
```

Different tool implementations can enforce different security models, access patterns, or domain rules while using the same kernel mounting infrastructure.

**Output Formatting and Logging Destinations**

The kernel emits canonical events to a unified JSONL stream but never decides how output should be formatted for users or where logs should be written:

```python
# ❌ Kernel never does formatting decisions
def format_response(self, response):
    if self.output_format == "markdown":
        return self.to_markdown(response)
    elif self.output_format == "json":
        return self.to_json(response)

# ✅ Hook modules handle formatting and routing
class MarkdownFormatterHook:
    async def on_response(self, event_data):
        formatted = self.to_markdown(event_data["response"])
        self.display_system.show(formatted)

class JSONLoggerHook:
    async def on_response(self, event_data):
        self.json_logger.write(event_data)
```

The kernel provides the event dispatch mechanism and basic infrastructure for hook result processing, but formatting and destination decisions remain with hook modules.

**Business Logic and Product Defaults**

The kernel avoids embedding business logic or product-specific defaults that would favor particular use cases:

```python
# ❌ Kernel never includes business defaults
DEFAULT_CONFIG = {
    "max_iterations": 5,  # Business decision
    "safety_level": "strict",  # Product decision
    "billing_tier": "premium"  # Business logic
}

# ✅ Application layer provides defaults
# Session configuration comes from app-layer policy
session_config = {
    "session": {
        "injection_budget_per_turn": None,  # Unlimited by default
        "injection_size_limit": None        # No size limit by default
    }
}
```

When the kernel needs configurable limits (like injection budgets), it provides the enforcement mechanism but takes policy from session configuration. Default values in the kernel are always `None` (unlimited/disabled), requiring explicit policy decisions at the application layer.

This strict separation ensures that the kernel can support diverse use cases - from restrictive enterprise environments to permissive development workflows - without requiring kernel modifications for different deployment scenarios.

## Invariants

The Amplifier kernel maintains five critical invariants that must hold at all times. These invariants form the foundation of system reliability and enable the modular architecture to function safely.

**Backward Compatibility**

Existing modules must continue to work across kernel updates without modification. The kernel treats backward compatibility as sacred - any change that would break existing modules requires explicit deprecation notices, dual-path support during transition periods, and long sunset windows. This invariant enables teams to develop modules independently without fear of kernel changes breaking their work.

```python
# ✅ Additive evolution preserves compatibility
class ModuleCoordinator:
    async def mount(self, mount_point: str, module: Any, 
                   capabilities: list[str] | None = None):  # New optional parameter
        # Existing modules work unchanged
        # New modules can use capabilities parameter
```

The kernel enforces this through the two-implementation rule - mechanisms are only added to the kernel after at least two independent modules demonstrate the need, proving the interface is genuinely general rather than specific to one use case.

**Non-Interference**

Faulty modules cannot crash the kernel or interfere with other modules. The kernel isolates module failures and maintains system stability even when individual modules behave incorrectly or maliciously.

```python
# Module validation at load time prevents basic failures
class ModuleValidationError(Exception):
    """Raised when a module fails validation at load time."""
    pass

# Kernel validates modules before allowing them to mount
async def _validate_module(self, module_id: str, module_path: Path) -> None:
    validator = validators.get(module_type)
    result = await validator.validate(package_path)
    
    if not result.passed:
        raise ModuleValidationError(
            f"Module '{module_id}' failed validation: {result.summary()}"
        )
```

The loader validates modules before mounting them, checking for required interfaces, proper error handling, and adherence to protocols. Modules that fail validation are rejected before they can affect system stability.

**Bounded Side-Effects**

The kernel never makes irreversible external changes without explicit session-level authorization. All external actions (file writes, network calls, system modifications) must be explicitly approved through the capability system and remain traceable through the event stream.

```python
# ✅ Kernel mechanisms are reversible and traceable
async def emit(self, event_type: str, data: dict[str, Any]) -> None:
    """Emit event to unified stream - observable, not destructive"""
    
async def mount(self, mount_point: str, module: Any) -> None:
    """Mount module - reversible via unmount"""

# ❌ Kernel never does irreversible external actions
# No file I/O, network calls, or system modifications in kernel
```

The kernel provides mechanisms for modules to request capabilities and emit events, but the actual external actions remain under module control and session policy. This ensures that kernel operations can always be undone or rolled back.

**Deterministic Semantics**

Given identical inputs and session state, kernel operations produce identical outputs and side-effects. This predictability enables reliable testing, debugging, and reasoning about system behavior.

```python
# Mount point derivation is deterministic
TYPE_TO_MOUNT_POINT = {
    "orchestrator": "orchestrator",
    "provider": "providers", 
    "tool": "tools",
    "hook": "hooks",
    "context": "context",
}

# Same module type always maps to same mount point
mount_point = TYPE_TO_MOUNT_POINT.get(module_type)
```

The kernel avoids non-deterministic operations like random number generation, timestamp-based decisions, or dependency on external state that could vary between runs. Module loading, event dispatch, and capability checking follow deterministic rules based solely on inputs and current session state.

**Minimal Dependencies**

The kernel maintains a minimal dependency footprint to avoid transitive dependency sprawl that could create version conflicts or security vulnerabilities. Dependencies are added only when they provide essential functionality that cannot be reasonably implemented within the kernel itself.

```python
# Kernel imports show minimal external dependencies
import importlib
import importlib.metadata  
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal

# No heavy frameworks, no optional dependencies
# Standard library preferred over external packages
```

The kernel relies primarily on Python's standard library, adding external dependencies only for core functionality like JSON schema validation or async primitives. This minimalism reduces the attack surface, simplifies deployment, and prevents the kernel from becoming coupled to rapidly-changing external ecosystems.

These invariants work together to create a stable foundation that supports rapid innovation at the module layer. Modules can experiment with new approaches, fail safely, and evolve quickly because the kernel provides reliable, predictable infrastructure that maintains these guarantees across all operations.

## Evolution Rules

The kernel evolves through four fundamental rules that maintain stability while enabling innovation. These rules, inspired by Linux kernel development practices, ensure that changes strengthen the system without breaking existing functionality or compromising the core architectural principles.

These evolution rules work together to create a disciplined approach to kernel development. They prevent the common pitfalls of software evolution: feature creep, breaking changes, premature abstraction, and unbounded complexity growth. By following these rules, the kernel maintains its role as a stable, predictable foundation while modules at the edges can innovate rapidly.

**Rule Interaction and Enforcement**

The four rules reinforce each other through natural checks and balances:

```python
# Example: Adding a new capability to the kernel
# 1. Additive First: New capability doesn't break existing modules
async def request_capability(self, capability: str, **kwargs) -> bool:
    """Request capability - new capabilities added without changing signature"""
    
# 2. Two-Implementation Rule: Proven need from multiple modules
# Evidence from both file-tool and web-search modules needing async execution

# 3. Spec Before Code: Clear contract definition
"""
Capability: async_execution
Purpose: Allow tools to run long operations without blocking session
Inputs: timeout_seconds (optional), progress_callback (optional)
Outputs: execution_handle for monitoring
"""

# 4. Complexity Budget: Simple mechanism, complexity stays in modules
# Kernel provides execution primitive, modules handle strategy
```

**Evolution Velocity**

These rules create intentionally different evolution speeds for different parts of the system:

- **Kernel**: Slow, deliberate changes with high confidence
- **Modules**: Rapid iteration and experimentation
- **Protocols**: Stable interfaces that change only when proven necessary
- **Applications**: Fast adaptation to user needs and market changes

This multi-speed evolution allows the system to be both stable and innovative. The kernel's stability enables module developers to build with confidence, while the module layer's flexibility allows quick responses to new requirements.

**Backward Compatibility as Sacred Principle**

All four rules ultimately serve backward compatibility, which is treated as inviolable. Breaking changes are considered design failures, not acceptable trade-offs. This philosophy comes directly from Linux kernel development, where maintaining compatibility with existing userspace is paramount.

```python
# Backward compatibility in practice
# Old modules continue working even as kernel adds capabilities
class Session:
    async def emit(self, event_type: str, data: dict) -> None:
        """Original signature preserved forever"""
        
    async def emit_with_metadata(self, event_type: str, data: dict, 
                                metadata: dict = None) -> None:
        """New functionality added alongside, never replacing"""
```

The evolution rules ensure that innovation happens through addition and extension, not replacement and breaking changes. This creates a system that grows more capable over time while remaining reliable for existing users.

### 1. Additive First

The "Additive First" rule prioritizes extending existing contracts through optional capabilities rather than making breaking changes. This approach ensures that existing modules continue working even as the kernel evolves to support new functionality.

**Core Principle: Optional Extensions Over Breaking Changes**

When the kernel needs new capabilities, they are added as optional parameters with sensible defaults, allowing existing code to continue working unchanged while enabling new modules to leverage enhanced functionality.

```python
# GOOD: Adding optional capability without breaking existing providers
class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    # New optional field - existing providers ignore it
    streaming: bool = Field(default=False, description="Enable streaming responses")
    timeout: float | None = Field(default=None, description="Request timeout in seconds")

# Existing provider implementations continue working:
async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
    # Provider can ignore new fields or implement them gradually
    messages = request.messages
    tools = request.tools
    # streaming and timeout are optional - no breaking change
```

```python
# BAD: Adding required parameter breaks all existing providers
class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    config: dict[str, Any]
    # This breaks every existing provider implementation
    required_new_field: str  # No default value!

# Every provider must be updated immediately or it fails:
async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
    # Crashes if required_new_field not provided
    new_value = request.required_new_field  # Breaking change!
```

**Protocol Evolution Through Optional Methods**

The Protocol-based interface system enables additive evolution by allowing new optional methods to be added without breaking existing implementations:

```python
@runtime_checkable
class Provider(Protocol):
    """Provider interface evolves additively"""
    
    # Core methods - always required
    @property
    def name(self) -> str: ...
    
    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...
    
    # Optional capability - new providers can implement, old ones ignore
    async def stream_complete(self, request: ChatRequest, **kwargs) -> AsyncIterator[ChatResponse]:
        """Optional streaming capability - not required for compatibility"""
        ...

# Kernel checks for capability before using it
if hasattr(provider, 'stream_complete') and request.streaming:
    async for chunk in provider.stream_complete(request):
        yield chunk
else:
    # Fallback to standard completion
    response = await provider.complete(request)
    yield response
```

**Schema Extension Patterns**

The design philosophy emphasizes extending schemas with optional fields rather than creating new incompatible versions:

```python
# Evolution of ApprovalRequest - additive only
class ApprovalRequest(BaseModel):
    # Original required fields - never change
    tool_name: str
    action: str
    risk_level: str
    
    # Optional fields added over time
    details: dict[str, Any] = Field(default_factory=dict)  # Added in v1.1
    timeout: float | None = Field(default=None)            # Added in v1.2
    # Future: priority: str = Field(default="normal")      # Could add in v1.3
    
    # Validation ensures backward compatibility
    def model_post_init(self, __context: Any) -> None:
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("Timeout must be positive or None")
```

**Capability Negotiation Over Version Checking**

Rather than forcing version upgrades, the system uses capability detection to enable new features gracefully:

```python
# Kernel discovers what each module supports
def get_module_capabilities(module) -> set[str]:
    """Discover what capabilities a module supports"""
    capabilities = set()
    
    if hasattr(module, 'stream_complete'):
        capabilities.add('streaming')
    if hasattr(module, 'batch_complete'):
        capabilities.add('batching')
    if hasattr(module, 'get_embeddings'):
        capabilities.add('embeddings')
        
    return capabilities

# Use capabilities when available, degrade gracefully when not
async def execute_with_provider(provider: Provider, request: ChatRequest):
    capabilities = get_module_capabilities(provider)
    
    if 'streaming' in capabilities and request.streaming:
        return await provider.stream_complete(request)
    else:
        return await provider.complete(request)
```

**Deprecation Windows for Removals**

When functionality must eventually be removed, the additive-first approach provides long deprecation windows with dual-path support:

```python
# Phase 1: Add new method alongside old one
class ContextManager(Protocol):
    async def add_message(self, message: dict[str, Any]) -> None:
        """Preferred method"""
        ...
    
    async def append_message(self, message: dict[str, Any]) -> None:
        """DEPRECATED: Use add_message instead. Will be removed in v2.0"""
        # Internally delegates to new method
        return await self.add_message(message)

# Phase 2: (6+ months later) Remove deprecated method
# Only after confirming no modules use the old interface
```

This additive evolution strategy ensures that the kernel can grow new capabilities without breaking existing modules, maintaining the stability that enables rapid innovation at the edges. Modules can adopt new features at their own pace while continuing to function with their current implementations.

### 2. Two-Implementation Rule

The Two-Implementation Rule prevents premature abstraction by requiring evidence that a mechanism is genuinely needed across multiple independent contexts before promoting it to the kernel. This rule ensures that kernel additions solve real, general problems rather than one-off use cases.

**The Progression Pattern**

The rule follows a three-stage progression that proves generality through convergent evolution:

1. **Module A needs capability X** → Prototype X inside Module A
2. **Module B independently needs capability X** → Prototype X inside Module B  
3. **A and B converge on similar solutions** → Extract X to kernel as a general mechanism

This pattern demonstrates that the capability represents a fundamental need rather than a specific implementation detail.

**Example: Event Emission Mechanism**

Consider how event emission might evolve following this rule:

```python
# Stage 1: Provider module needs to log completion events
class OpenAIProvider:
    async def complete(self, request: ChatRequest) -> ChatResponse:
        response = await self._call_api(request)
        
        # Prototype: Direct logging inside module
        print(json.dumps({
            "event": "provider:completion",
            "provider": "openai",
            "model": request.model,
            "timestamp": datetime.now().isoformat()
        }))
        
        return response

# Stage 2: Tool module independently needs to log execution events  
class PythonTool:
    async def execute(self, code: str) -> ToolResult:
        result = await self._run_code(code)
        
        # Prototype: Similar logging pattern emerges
        print(json.dumps({
            "event": "tool:execution", 
            "tool": "python",
            "success": result.success,
            "timestamp": datetime.now().isoformat()
        }))
        
        return result
```

At this point, two independent modules have converged on the same need: structured event logging. The similar patterns indicate a general mechanism is warranted.

```python
# Stage 3: Extract to kernel as general capability
# Kernel now provides emit() mechanism
class AmplifierCore:
    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """General event emission mechanism"""
        event = {
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        self._write_to_jsonl_stream(event)

# Modules now use kernel mechanism
class OpenAIProvider:
    def __init__(self, kernel: AmplifierCore):
        self.kernel = kernel
    
    async def complete(self, request: ChatRequest) -> ChatResponse:
        response = await self._call_api(request)
        
        # Use kernel mechanism instead of local prototype
        self.kernel.emit("provider:completion", {
            "provider": "openai", 
            "model": request.model
        })
        
        return response
```

**Preventing Single-Use Abstractions**

The rule specifically guards against abstractions that serve only one module:

```python
# Anti-pattern: Adding to kernel based on single module need
class SpecializedOrchestrator:
    def needs_custom_retry_logic(self):
        # Only this orchestrator needs this specific retry pattern
        pass

# Kernel should NOT add retry mechanisms based on this alone
# Wait for second module to independently need retry capabilities
```

**Evidence of Convergence**

Valid convergence indicators include:

- **Similar interfaces**: Both modules expose comparable method signatures
- **Shared data structures**: Both modules work with similar data shapes  
- **Common patterns**: Both modules follow similar execution flows
- **Overlapping concerns**: Both modules address the same fundamental problem

**Counter-Examples**

The rule helps avoid these premature abstractions:

- Adding configuration management because one module needs settings
- Creating specialized data types for a single module's domain model
- Building orchestration primitives that only one strategy uses
- Implementing caching mechanisms that only one provider requires

**Timing the Extraction**

Extract to kernel when:
- Two modules have working prototypes solving the same problem
- The solutions show clear commonalities in approach
- The abstraction would eliminate meaningful duplication
- The mechanism could reasonably serve future modules

Don't extract when:
- Only one module currently needs the capability
- The solutions are too different to share an interface
- The abstraction would be more complex than the duplicated code
- The need might be temporary or module-specific

This disciplined approach ensures that kernel mechanisms represent proven, general needs rather than speculative abstractions, keeping the kernel focused on capabilities that truly serve multiple independent use cases.

### 3. Spec Before Code

Every kernel change begins with a short specification document that serves as both design blueprint and acceptance criteria. This spec-first approach ensures that proposed changes are well-reasoned, properly scoped, and aligned with kernel principles before any code is written.

**Required Specification Elements**

Each kernel change proposal must include five essential components:

**Purpose Statement**: A clear, concise explanation of what the change accomplishes and why it's needed. This should reference the two-implementation rule by citing specific modules that have independently converged on needing this mechanism.

```markdown
## Purpose
Add `emit()` mechanism to kernel core to support structured event logging.

Evidence: Both OpenAIProvider and AnthropicProvider modules have independently 
implemented similar event emission patterns for observability. The convergent 
implementations indicate a general mechanism is warranted.
```

**Alternatives Considered**: Document other approaches that were evaluated and explain why they were rejected. This demonstrates thorough analysis and helps reviewers understand the decision rationale.

```markdown
## Alternatives Considered
1. Module-level logging libraries - Rejected: Creates inconsistent event formats
2. Shared utility module - Rejected: Still requires each module to import/configure
3. Kernel emit() mechanism - Selected: Provides unified interface and canonical format
```

**Impact on Invariants**: Explicitly analyze how the change affects kernel invariants, particularly backward compatibility, non-interference between modules, and the mechanism-vs-policy boundary.

```markdown
## Invariant Analysis
- Backward compatibility: ✅ Additive change, no existing interfaces modified
- Non-interference: ✅ Event emission is fire-and-forget, cannot block modules
- Mechanism boundary: ✅ Kernel provides emit capability, modules decide what to log
- Stable contracts: ✅ Event schema versioned, optional fields for evolution
```

**Test Strategy**: Define how the change will be validated, including both automated tests and manual verification procedures. Focus on testing the mechanism itself and its integration points.

```markdown
## Test Strategy
- Unit tests: Event formatting, timestamp generation, schema validation
- Integration tests: Multiple modules emitting events simultaneously
- Contract tests: Event schema compatibility across versions
- Manual verification: JSONL output inspection, event ordering validation
```

**Rollback Plan**: Specify how to safely revert the change if issues arise after deployment. This should include both technical steps and communication procedures.

```markdown
## Rollback Plan
1. Technical: Feature flag allows disabling emit() mechanism
2. Fallback: Modules gracefully handle missing emit() capability
3. Data: Event stream remains readable during rollback period
4. Timeline: 24-hour monitoring window before considering rollback
```

**Specification Review Process**

The specification undergoes review before any implementation begins:

- **Mechanism Validation**: Confirm this provides a general capability rather than solving a single module's specific need
- **Interface Design**: Ensure the proposed API is minimal, stable, and follows text-first principles  
- **Invariant Preservation**: Verify that kernel principles remain intact
- **Implementation Scope**: Check that the change is appropriately sized and focused

**Acceptance Criteria Alignment**

The specification must demonstrate alignment with the kernel's acceptance criteria from the design philosophy:

- Implements mechanism, not policy
- Has evidence from two or more independent modules
- Preserves backward compatibility and non-interference
- Proposes a small, explicit, text-first interface
- Includes comprehensive tests and documentation
- Retires equivalent complexity elsewhere in the system

**Living Documentation**

Approved specifications become part of the kernel's permanent documentation, serving as both historical record and guidance for future changes. They help maintainers understand the reasoning behind design decisions and provide context for subsequent modifications.

This spec-first approach ensures that kernel evolution remains deliberate, well-reasoned, and aligned with the core principle of providing stable mechanisms that enable innovation at the module level. By requiring thorough analysis before implementation, the process maintains the kernel's stability while enabling controlled growth based on proven needs.

### 4. Complexity Budget

Every change to the kernel must justify its complexity cost and demonstrate that it provides proportional value. This principle, inspired by the Linux kernel's disciplined approach to growth, ensures the kernel remains small, stable, and maintainable by a single person.

**Complexity Accounting**

When proposing a kernel change, you must account for the complexity it introduces:

- **Lines of code added**: More code means more surface area for bugs
- **New abstractions**: Each layer must justify its existence with clear benefits
- **Interface complexity**: Additional parameters, return values, or behavioral modes
- **Cognitive load**: How much more must a maintainer understand to work with the system
- **Testing burden**: New code paths require comprehensive test coverage

**The Retirement Requirement**

As stated in the design philosophy, additions must retire equivalent complexity elsewhere. This isn't just good practice—it's a hard requirement. Before adding new functionality, identify what existing complexity can be eliminated:

```markdown
## Complexity Analysis
Adding: Event emission mechanism (+150 LOC, +1 public API)
Retiring: Ad-hoc logging in 3 modules (-200 LOC, -3 private interfaces)
Net change: -50 LOC, +1 canonical interface, -3 inconsistent patterns
```

**Complexity Budget Examples**

Consider these scenarios and their complexity implications:

**Approved Addition**: Adding a standardized `emit()` function that replaces multiple modules' custom logging approaches. The kernel gains one clean interface while modules lose dozens of inconsistent implementations.

**Rejected Addition**: Adding configuration file parsing to the kernel because "modules need it." This violates the mechanism-vs-policy boundary—configuration handling is policy that belongs in modules or the application layer.

**Complexity Debt**: When modules repeatedly implement similar patterns, this signals potential kernel work. But the kernel waits for at least two independent implementations before extracting common mechanisms.

**Measuring Complexity Impact**

Use these criteria to evaluate whether a change respects the complexity budget:

- **Conceptual weight**: Can a new maintainer understand this change in isolation?
- **Interaction effects**: Does this change require modifications to existing code paths?
- **Documentation burden**: How much explanation does this require?
- **Maintenance cost**: What ongoing effort will this require?

**The Simplicity Test**

Before implementing any kernel change, apply this test: "If I had to explain this entire kernel to someone new, would this change make that explanation longer or shorter?" Changes that make the kernel harder to explain are usually adding complexity without retiring enough elsewhere.

**Enforcement Through Review**

The complexity budget is enforced during the specification review process. Proposals that don't demonstrate complexity retirement or that add disproportionate complexity for their benefit are rejected, regardless of their technical merit. This maintains the kernel's essential characteristic: remaining comprehensible to a single maintainer while providing stable mechanisms for unlimited module innovation.

## Interface Guidance

Kernel interfaces are the contracts that enable modules to interact with the core system while maintaining stability and predictability. These interfaces must be designed with extreme care, as they become the foundation upon which all module innovation depends. Poor interface design creates technical debt that compounds over time, while well-designed interfaces enable unlimited creativity at the edges.

The kernel's interface design follows three fundamental principles that ensure long-term maintainability and module independence. These principles work together to create interfaces that are easy to understand, stable across versions, and provide clear feedback when things go wrong.

**Interface Design Philosophy**

Every kernel interface represents a commitment to backward compatibility. Once an interface is published, it becomes part of the permanent contract between kernel and modules. This permanence demands careful consideration of each parameter, return value, and behavioral guarantee.

The Linux kernel metaphor guides interface design decisions. Just as Linux syscalls remain stable across decades while enabling diverse userspace innovation, Amplifier's interfaces must provide stable mechanisms that support varied module policies without imposing specific approaches.

**Design Process**

Interface design begins with understanding the mechanism being exposed, not the policies that will use it. The kernel provides capabilities—mounting modules, emitting events, managing sessions—while modules decide how to use these capabilities. This separation ensures interfaces remain general enough for unforeseen use cases.

Before adding any interface, the two-implementation rule applies: at least two independent modules must demonstrate the need for a particular mechanism. This prevents premature abstraction and ensures the interface solves real problems rather than hypothetical ones.

**Interface Categories**

Amplifier's kernel interfaces fall into distinct categories, each with specific design constraints:

**Session Operations**: Core lifecycle management functions like `create_session()` and session teardown. These interfaces handle the fundamental unit of work within the system.

**Module Management**: Functions for mounting and unmounting modules, including capability negotiation and dependency resolution.

**Event System**: The `emit()` function and related event dispatch mechanisms that enable observability without coupling.

**Context Management**: Interfaces for managing session state, including context compaction and retrieval operations.

Each category has evolved to minimize surface area while maximizing expressiveness, following the principle that interfaces should be as small as possible but no smaller.

### Small and Sharp

Kernel interfaces follow the Unix philosophy of doing one thing well. Each operation should have a single, clear purpose with minimal parameters and predictable behavior. This approach creates interfaces that are easy to understand, test, and maintain while avoiding the complexity of multi-purpose functions.

The principle manifests in Amplifier's core operations, which are deliberately narrow in scope. Rather than creating Swiss Army knife methods that handle multiple scenarios through parameters, the kernel provides focused operations that do exactly what their names suggest.

**Good: Focused Operations**

The ModuleCoordinator demonstrates this principle through separate mount points and focused methods:

```python
# Each mount point has a specific purpose
await coordinator.mount("orchestrator", orchestrator_module)
await coordinator.mount("providers", provider_module, "openai")
await coordinator.mount("tools", tool_module, "filesystem")

# Separate methods for different concerns
coordinator.register_capability("agents.list", list_agents_fn)
coordinator.register_contributor("observability.events", "tool-task", event_callback)

# Clean unmounting with specific targets
await coordinator.unmount("providers", "openai")
await coordinator.unmount("orchestrator")
```

Each method has a single responsibility. `mount()` attaches modules to specific mount points. `register_capability()` enables inter-module communication. `register_contributor()` sets up event aggregation. There's no ambiguity about what each operation does or when to use it.

**Bad: Swiss Army Knife Interface**

Contrast this with a hypothetical "do-everything" interface that violates the small and sharp principle:

```python
# Anti-pattern: One method trying to handle everything
await coordinator.manage_module(
    operation="mount",           # Parameter determines behavior
    module_type="provider",      # Multiple concepts mixed
    module=provider_module,
    name="openai",
    capabilities=["chat", "embedding"],
    auto_register_events=True,   # Side effects hidden in parameters
    fallback_on_error="log",     # Error handling as configuration
    timeout=30
)

# Unclear what this does without reading documentation
await coordinator.manage_module(
    operation="capability_register",
    capability_name="agents.list",
    callback=list_agents_fn,
    scope="session"
)
```

This anti-pattern forces users to understand multiple concepts simultaneously. The `operation` parameter makes the method's behavior unpredictable without examining the parameter value. Hidden side effects like `auto_register_events` create unexpected coupling between operations.

**Session Operations Follow the Same Pattern**

Session management maintains sharp boundaries between operations:

```python
# Creating a session does one thing
session = await amplifier.create_session(config=session_config)

# Emitting events does one thing
await session.emit("user:message", {"content": "Hello", "role": "user"})

# Processing turns does one thing
response = await session.process_turn("What's the weather like?")
```

Each operation has a clear contract. `create_session()` returns a configured session. `emit()` dispatches an event. `process_turn()` handles user input and returns a response. There's no overlap or ambiguity between these responsibilities.

**Benefits of Small and Sharp Interfaces**

Focused operations enable better testing since each method has a single code path to verify. Error handling becomes clearer because failures have obvious causes. Documentation stays concise because each operation has a simple purpose to explain.

Module authors benefit from predictable interfaces that behave consistently. When `mount()` always attaches modules and `unmount()` always detaches them, there are no surprising edge cases or parameter combinations to handle.

The kernel's stability depends on this principle. Small interfaces change less frequently than large ones because they have fewer reasons to evolve. When changes are necessary, focused operations can be deprecated and replaced without affecting unrelated functionality.

**Implementation Guidelines**

When designing kernel interfaces, prefer multiple focused methods over single configurable ones. If a method needs an "operation type" parameter, split it into separate methods. If a method has optional parameters that change its fundamental behavior, create distinct operations instead.

Keep parameter lists minimal and avoid boolean flags that alter method behavior. Each parameter should refine the operation's target rather than change what the operation does. When in doubt, create two methods rather than one flexible method with conditional logic.

This principle extends to return values and error conditions. Methods should return exactly what their names promise, nothing more. Error conditions should be specific to the operation's purpose rather than generic failures that could mean anything.

### Stable Schemas

All data structures crossing kernel boundaries must include explicit version information to ensure backward compatibility and graceful evolution. The kernel uses Pydantic models with schema versioning to maintain stable contracts between components while allowing controlled schema evolution.

**Schema Version Fields**

Every request and response model includes version metadata to enable safe schema evolution:

```python
class ChatRequest(BaseModel):
    """Complete chat request to provider with schema versioning."""
    
    schema_version: str = Field(default="1.0", description="Request schema version")
    messages: list[Message]
    tools: list[ToolSpec] | None = None
    response_format: ResponseFormat | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    conversation_id: str | None = None
    stream: bool | None = False
    metadata: dict[str, Any] | None = None
```

The `schema_version` field allows providers and tools to understand which version of the request format they're receiving. This enables backward compatibility when new fields are added or existing fields are modified.

**Additive Schema Evolution**

New schema versions add optional fields with sensible defaults rather than modifying existing fields. This ensures older components continue working without modification:

```python
# Version 1.0 - Original schema
class ChatRequest(BaseModel):
    schema_version: str = Field(default="1.0")
    messages: list[Message]
    tools: list[ToolSpec] | None = None
    stream: bool | None = False

# Version 1.1 - Added temperature control
class ChatRequest(BaseModel):
    schema_version: str = Field(default="1.1")
    messages: list[Message]
    tools: list[ToolSpec] | None = None
    stream: bool | None = False
    temperature: float | None = None  # New optional field with default

# Version 1.2 - Added response format control
class ChatRequest(BaseModel):
    schema_version: str = Field(default="1.2")
    messages: list[Message]
    tools: list[ToolSpec] | None = None
    stream: bool | None = False
    temperature: float | None = None
    response_format: ResponseFormat | None = None  # Another optional addition
```

Each new version maintains compatibility with previous versions by making all additions optional. A provider written for schema version 1.0 will receive `None` values for newer fields, allowing it to function normally with its original behavior.

**Pydantic Validation and Extra Fields**

The kernel uses Pydantic's `extra="allow"` configuration to handle forward compatibility gracefully:

```python
class Message(BaseModel):
    """Message with forward-compatible schema handling."""
    
    model_config = ConfigDict(extra="allow")
    
    role: Literal["system", "developer", "user", "assistant", "function", "tool"]
    content: Union[str, list[ContentBlockUnion]]
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] | None = None
```

This configuration allows newer schema versions to include additional fields that older components will ignore rather than reject. A component expecting schema version 1.0 can safely process a version 1.2 message by using only the fields it understands.

**Version-Aware Processing**

Components should check schema versions and adapt their behavior accordingly:

```python
async def process_request(request: ChatRequest) -> ChatResponse:
    """Process chat request with version-aware handling."""
    
    # Extract version, defaulting to 1.0 for legacy requests
    version = getattr(request, 'schema_version', '1.0')
    
    # Handle version-specific features
    if version >= '1.1' and request.temperature is not None:
        # Use temperature parameter if available
        config.temperature = request.temperature
    
    if version >= '1.2' and request.response_format is not None:
        # Apply response format constraints if supported
        config.response_format = request.response_format
    
    # Core processing works regardless of version
    return await generate_response(request.messages, config)
```

This pattern allows components to take advantage of newer schema features when available while maintaining compatibility with older request formats.

**Schema Documentation and Validation**

The kernel maintains JSON Schema definitions alongside Pydantic models to enable validation in non-Python components:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ChatRequest",
  "type": "object",
  "properties": {
    "schema_version": {
      "type": "string",
      "default": "1.2",
      "description": "Request schema version"
    },
    "messages": {
      "type": "array",
      "items": {"$ref": "#/definitions/Message"}
    },
    "temperature": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 2.0,
      "description": "Added in v1.1"
    }
  },
  "required": ["messages"],
  "additionalProperties": true
}
```

The `additionalProperties: true` setting mirrors Pydantic's `extra="allow"` configuration, ensuring consistent validation behavior across language boundaries.

**Breaking Changes and Migration**

When breaking changes become necessary, the kernel introduces new major versions with explicit migration paths:

```python
# Legacy v1.x handler
async def handle_v1_request(request: ChatRequestV1) -> ChatResponseV1:
    """Handle legacy v1.x requests with automatic migration."""
    
    # Convert to current format
    current_request = ChatRequest(
        schema_version="2.0",
        messages=migrate_messages(request.messages),
        tools=request.tools,
        parameters=migrate_parameters(request)  # Consolidate scattered params
    )
    
    response = await handle_current_request(current_request)
    
    # Convert response back to v1 format
    return ChatResponseV1(
        content=response.content,
        tool_calls=response.tool_calls,
        usage=response.usage
    )
```

This approach provides a transition period where both old and new schemas are supported, allowing gradual migration of components without forcing simultaneous updates across the entire system.

### Explicit Errors

The kernel follows a strict "fail closed" philosophy - when errors occur, the system fails visibly with actionable diagnostics rather than silently falling back to potentially incorrect behavior. This ensures problems are caught early and developers receive clear guidance for resolution.

**Clear Error Types with Context**

The kernel defines specific error types that provide both the failure reason and available remediation options:

```python
class ModuleValidationError(Exception):
    """Raised when a module fails validation at load time."""
    pass

# Usage in module loader
if not result.passed:
    error_details = "; ".join(f"{e.name}: {e.message}" for e in result.errors)
    raise ModuleValidationError(
        f"Module '{module_id}' failed validation: {result.summary()}. "
        f"Errors: {error_details}"
    )
```

This error provides the module name, validation summary, and specific error details, giving developers everything needed to fix the issue.

**Explicit Warnings for Missing Dependencies**

Rather than silently degrading functionality, the coordinator explicitly warns when required systems are unavailable:

```python
# Log warnings if systems not provided (kernel doesn't decide fallback - that's policy)
if self.approval_system is None:
    logger.warning("No approval system provided - approval requests will fail")
if self.display_system is None:
    logger.warning("No display system provided - hook messages will be logged only")
```

**Good vs Bad Error Handling**

**❌ Bad: Silent fallback with hidden behavior**

```python
# ANTI-PATTERN: Silently falls back without indication
async def load_module(module_id: str):
    try:
        return load_from_registry(module_id)
    except ModuleNotFound:
        # Silent fallback - user doesn't know what happened
        return create_default_module()
```

**✅ Good: Clear error with context and options**

```python
# CORRECT: Explicit about what failed and what options exist
async def load_module(module_id: str):
    try:
        return load_from_registry(module_id)
    except ModuleNotFound as e:
        # Clear error with available alternatives
        available = list_available_modules()
        raise ValueError(
            f"Module '{module_id}' not found. "
            f"Available modules: {', '.join(available)}. "
            f"Check module name spelling or install the module."
        ) from e
```

**Validation with Actionable Feedback**

When validation fails, the system provides specific guidance rather than generic error messages:

```python
# Size limit validation with clear context
if size_limit is not None and len(content) > size_limit:
    logger.error(
        f"Hook injection too large: {hook_name}",
        extra={"size": len(content), "limit": size_limit},
    )
    raise ValueError(
        f"Context injection exceeds {size_limit} bytes. "
        f"Current size: {len(content)} bytes. "
        f"Consider reducing content or increasing limit in session config."
    )
```

**Budget Enforcement with Clear Boundaries**

The system enforces limits explicitly and provides clear feedback when boundaries are exceeded:

```python
# Budget check with detailed context
if budget is not None and self._current_turn_injections + tokens > budget:
    logger.warning(
        "Warning: Hook injection budget exceeded",
        extra={
            "hook": hook_name,
            "current": self._current_turn_injections,
            "attempted": tokens,
            "budget": budget,
        },
    )
```

**Approval System Failure Handling**

When required systems are unavailable, the kernel fails explicitly rather than proceeding unsafely:

```python
# Check if approval system is available
if self.approval_system is None:
    logger.error("Approval requested but no approval system provided", extra={"hook": hook_name})
    return HookResult(action="deny", reason="No approval system available")
```

This approach ensures that security-sensitive operations cannot proceed when approval mechanisms are missing, preventing potential security vulnerabilities from silent fallbacks.

**Timeout Handling with Default Policies**

Even timeout scenarios provide clear reasoning and respect configured policies:

```python
except ApprovalTimeoutError:
    logger.warning("Approval timeout", extra={"hook": hook_name, "default": result.approval_default})
    
    if result.approval_default == "deny":
        return HookResult(action="deny", reason=f"Approval timeout - denied by default: {prompt}")
    return HookResult(action="continue")
```

The key principle is that every error condition should provide enough context for the developer to understand what went wrong, why it went wrong, and what steps they can take to resolve the issue. Silent fallbacks are explicitly avoided as they hide problems and can lead to incorrect system behavior that's difficult to debug.

## Security Posture

The Amplifier kernel implements a security-first architecture based on three foundational principles that ensure safe operation in multi-module environments. Drawing from the Linux kernel security model, the system treats security as an area where complexity is justified to maintain strong guarantees.

**Security as a Core Design Constraint**

Security permeates every aspect of the kernel's design, from module loading to capability enforcement. Unlike areas where the kernel prioritizes simplicity, security decisions favor robust protection over ease of implementation. This approach ensures that modules cannot compromise system integrity or interfere with each other's operation.

**Capability-Based Security Model**

The kernel implements a capability-based security system inspired by Linux Security Modules (LSM). Rather than relying on implicit permissions, every operation requires explicit capability grants. This model provides fine-grained control over what modules can access and execute:

```python
# Capability check before allowing module operation
if not self.has_capability(module_id, "tool:execute"):
    logger.error("Module lacks required capability", 
                extra={"module": module_id, "capability": "tool:execute"})
    return HookResult(action="deny", reason="Insufficient capabilities")
```

**Approval System Integration**

Critical operations flow through an approval system that enforces policy decisions at runtime. When modules request sensitive capabilities, the kernel delegates authorization decisions to configured approval mechanisms while maintaining strict enforcement:

```python
# Approval required for sensitive operations
if requires_approval:
    approval_result = await self.approval_system.request_approval(
        operation=operation_type,
        context=security_context,
        timeout=approval_timeout
    )
    
    if not approval_result.approved:
        return HookResult(action="deny", reason=approval_result.reason)
```

**Event-Driven Security Monitoring**

All security-relevant actions generate canonical events in the unified JSONL stream. This approach ensures complete auditability without requiring modules to implement their own logging mechanisms. Security events include capability checks, approval requests, and boundary violations.

**Fail-Safe Defaults**

When security systems are unavailable or encounter errors, the kernel defaults to the most restrictive behavior. Operations that cannot be safely authorized are denied rather than allowed to proceed with reduced security guarantees.

### Deny by Default

The Amplifier kernel provides no ambient authority to modules - every capability must be explicitly requested and granted. This zero-trust approach ensures that modules cannot access system resources, communicate with other modules, or perform privileged operations without explicit permission.

When modules are loaded, they start with no capabilities whatsoever. The kernel's capability registry (`_capabilities` dict in the coordinator) maintains a strict mapping of available capabilities, but modules must actively request access to use them. This design prevents accidental or malicious access to sensitive functionality.

The capability system operates through explicit registration and retrieval:

```python
class FileSystemTool:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        # Module has no capabilities by default
        
    async def initialize(self):
        # Must explicitly request file system access capability
        fs_capability = self.coordinator.get_capability("filesystem.write")
        if fs_capability is None:
            raise ValueError("Required filesystem.write capability not available")
        
        self.fs_write = fs_capability
        
        # Request approval capability for sensitive operations
        approval_capability = self.coordinator.get_capability("approval.request")
        if approval_capability is None:
            logger.warning("No approval capability - will skip user confirmations")
            self.can_request_approval = False
        else:
            self.request_approval = approval_capability
            self.can_request_approval = True
    
    async def write_file(self, path: str, content: str):
        # Cannot write files without explicit capability
        if not hasattr(self, 'fs_write'):
            raise PermissionError("No filesystem write capability")
        
        # Request approval for sensitive paths
        if self.can_request_approval and self._is_sensitive_path(path):
            approved = await self.request_approval(
                f"Allow writing to {path}?",
                options=["Allow", "Deny"],
                timeout=30
            )
            if not approved:
                raise PermissionError("User denied file write operation")
        
        # Use the explicitly granted capability
        return await self.fs_write(path, content)
```

Capability providers must also explicitly register their services with the coordinator:

```python
class FileSystemProvider:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    async def initialize(self):
        # Explicitly register capabilities for other modules to request
        self.coordinator.register_capability("filesystem.read", self._read_file)
        self.coordinator.register_capability("filesystem.write", self._write_file)
        self.coordinator.register_capability("filesystem.list", self._list_directory)
        
        logger.info("Registered filesystem capabilities")
    
    async def _write_file(self, path: str, content: str):
        # Implementation with appropriate safety checks
        if not self._validate_path(path):
            raise ValueError(f"Invalid file path: {path}")
        
        # Actual file writing logic here
        with open(path, 'w') as f:
            f.write(content)
```

This explicit capability model extends to all inter-module communication. Modules cannot directly reference each other or assume that any services are available. Instead, they must request specific capabilities and handle cases where those capabilities are not granted:

```python
# Module requesting multiple capabilities with graceful degradation
async def setup_module(coordinator):
    # Core capability - required for operation
    core_capability = coordinator.get_capability("session.spawn")
    if core_capability is None:
        raise RuntimeError("Cannot operate without session spawning capability")
    
    # Optional capability - degrades gracefully
    metrics_capability = coordinator.get_capability("metrics.record")
    if metrics_capability is None:
        logger.info("No metrics capability - will skip performance tracking")
        metrics_capability = lambda *args, **kwargs: None  # No-op fallback
    
    return {
        "spawn_session": core_capability,
        "record_metric": metrics_capability
    }
```

The deny-by-default principle ensures that security boundaries remain intact even as the system evolves. New capabilities must be explicitly designed, registered, and requested - there is no path for modules to gain access to functionality through implicit means or system evolution.

### Sandbox Boundaries

All interactions that cross module boundaries are subject to comprehensive validation, attribution, and observability. The kernel ensures that every boundary crossing is logged, tracked, and can be audited, providing complete visibility into system behavior.

The hook system serves as the primary mechanism for boundary observability. Every significant operation - tool calls, agent spawns, context modifications, and inter-module communications - emits events that are captured with full attribution and sanitized data:

```python
# Example: Tool call boundary crossing with full observability
async def execute_tool(self, tool_name: str, parameters: dict):
    # Sanitize input data for logging
    sanitized_params = self._sanitize_parameters(parameters)
    
    # Emit pre-execution event with attribution
    result = await self.coordinator.hooks.emit("tool:pre", {
        "tool_name": tool_name,
        "parameters": sanitized_params,
        "session_id": self.coordinator.session_id,
        "parent_id": self.coordinator.parent_id,
        "timestamp": datetime.now().isoformat(),
        "user_id": self.session.user_id
    })
    
    if result.action == "deny":
        logger.warning(f"Tool execution denied: {result.reason}")
        raise PermissionError(f"Tool access denied: {result.reason}")
    
    try:
        # Execute the actual tool
        tool_result = await self._execute_tool_implementation(tool_name, parameters)
        
        # Emit post-execution event
        await self.coordinator.hooks.emit("tool:post", {
            "tool_name": tool_name,
            "success": True,
            "result_size": len(str(tool_result)),
            "session_id": self.coordinator.session_id,
            "execution_time_ms": execution_time
        })
        
        return tool_result
        
    except Exception as e:
        # Emit error event with sanitized error info
        await self.coordinator.hooks.emit("error:tool", {
            "tool_name": tool_name,
            "error_type": type(e).__name__,
            "error_message": str(e)[:200],  # Truncated for safety
            "session_id": self.coordinator.session_id
        })
        raise

def _sanitize_parameters(self, params: dict) -> dict:
    """Remove sensitive data from parameters for logging."""
    sanitized = {}
    for key, value in params.items():
        if key.lower() in ['password', 'token', 'secret', 'key']:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 100:
            sanitized[key] = value[:97] + "..."
        else:
            sanitized[key] = value
    return sanitized
```

The coordinator automatically injects attribution metadata into all hook events, ensuring that every boundary crossing can be traced back to its originating session and context. This happens transparently through the hook system's default field mechanism:

```python
# During coordinator initialization
self.hooks.set_default_fields(
    session_id=self.session_id,
    parent_id=self.parent_id,
    coordinator_instance=id(self)
)

# All subsequent hook emissions automatically include these fields
await self.hooks.emit("agent:spawn", {
    "agent_type": "task_executor",
    "config_override": sanitized_config
})
# Automatically becomes:
# {
#     "agent_type": "task_executor", 
#     "config_override": sanitized_config,
#     "session_id": "sess_abc123",
#     "parent_id": "sess_parent456",
#     "coordinator_instance": 140234567890
# }
```

Input validation occurs at every boundary through the hook system's handler chain. Handlers can inspect, modify, or reject operations before they cross boundaries:

```python
# Security hook that validates all tool parameters
async def validate_tool_parameters(event: str, data: dict) -> HookResult:
    if event != "tool:pre":
        return HookResult(action="continue")
    
    tool_name = data.get("tool_name")
    parameters = data.get("parameters", {})
    
    # Validate against tool schema
    if not self._validate_tool_schema(tool_name, parameters):
        return HookResult(
            action="deny", 
            reason=f"Invalid parameters for tool {tool_name}"
        )
    
    # Check for suspicious patterns
    if self._contains_suspicious_patterns(parameters):
        return HookResult(
            action="deny",
            reason="Parameters contain potentially malicious content"
        )
    
    # Sanitize parameters if needed
    sanitized_params = self._sanitize_dangerous_inputs(parameters)
    if sanitized_params != parameters:
        return HookResult(
            action="modify",
            data={**data, "parameters": sanitized_params}
        )
    
    return HookResult(action="continue")

# Register the validation hook with high priority
coordinator.hooks.register("tool:pre", validate_tool_parameters, priority=10)
```

All boundary crossings generate audit trails through structured logging that includes the sanitized operation details, attribution information, and timing data. This creates a complete record of system behavior that can be analyzed for security, debugging, or compliance purposes:

```python
# Automatic audit logging for all hook events
logger.info(
    "Boundary crossing detected",
    extra={
        "event_type": event,
        "session_id": data.get("session_id"),
        "parent_id": data.get("parent_id"),
        "handler_count": len(handlers),
        "data_keys": list(data.keys()),
        "timestamp": datetime.now().isoformat(),
        "trace_id": self._generate_trace_id()
    }
)
```

The observability extends to capability requests and grants, ensuring that all inter-module communications are tracked:

```python
def get_capability(self, name: str) -> Any | None:
    """Get capability with full audit trail."""
    capability = self._capabilities.get(name)
    
    # Log capability access attempt
    logger.info(
        "Capability access",
        extra={
            "capability_name": name,
            "session_id": self.session_id,
            "granted": capability is not None,
            "requester_context": self._get_caller_context()
        }
    )
    
    if capability is None:
        logger.warning(f"Capability '{name}' not available")
    
    return capability
```

This comprehensive boundary observability ensures that the system maintains complete visibility into all cross-module interactions while preserving the security and isolation guarantees of the sandbox model.

### Non-Interference

Module failures are isolated from the kernel through comprehensive error handling that ensures system stability. When a module encounters an error, the kernel catches the exception, logs the failure, and continues operating normally without affecting other modules or the core system.

The hook system demonstrates this non-interference principle by wrapping all module execution in try-catch blocks that prevent individual handler failures from cascading:

```python
async def emit(self, event: str, data: dict[str, Any]) -> HookResult:
    """
    Emit an event to all registered handlers.
    Individual handler failures don't stop other handlers or crash the kernel.
    """
    handlers = self._handlers.get(event, [])
    
    for hook_handler in handlers:
        try:
            # Execute the module's handler
            result = await hook_handler.handler(event, current_data)
            
            if not isinstance(result, HookResult):
                logger.warning(f"Handler '{hook_handler.name}' returned invalid result type")
                continue  # Skip this handler, continue with others
            
            # Process valid results normally
            if result.action == "deny":
                return result
            elif result.action == "modify" and result.data is not None:
                current_data = result.data
                
        except Exception as e:
            # Isolate the failure - log it but don't let it crash the kernel
            logger.error(f"Error in hook handler '{hook_handler.name}' for event '{event}': {e}")
            # Continue with other handlers even if one fails
            continue
    
    # Return successful result even if some handlers failed
    return HookResult(action="continue", data=current_data)
```

This error isolation extends to the collection mechanism as well, where timeouts and exceptions are handled gracefully:

```python
async def emit_and_collect(self, event: str, data: dict[str, Any], timeout: float = 1.0) -> list[Any]:
    """
    Collect responses from handlers with timeout protection.
    Failed or slow handlers don't block the entire operation.
    """
    responses = []
    
    for hook_handler in handlers:
        try:
            # Protect against hanging handlers with timeout
            result = await asyncio.wait_for(hook_handler.handler(event, data), timeout=timeout)
            
            if result.data is not None:
                responses.append(result.data)
                
        except TimeoutError:
            logger.warning(f"Handler '{hook_handler.name}' timed out after {timeout}s")
            # Don't crash - just skip this handler's response
        except Exception as e:
            logger.error(f"Error in hook handler '{hook_handler.name}' for event '{event}': {e}")
            # Continue collecting from other handlers
            
    return responses  # Return whatever we successfully collected
```

The kernel maintains operational continuity by treating module failures as expected conditions rather than fatal errors. Each failure is logged with sufficient detail for debugging while preserving system stability. This approach ensures that a single misbehaving module cannot bring down the entire system or interfere with other modules' operation.

Error emission replaces error propagation - instead of allowing exceptions to bubble up and crash the kernel, failures are converted into structured log events that can be observed, analyzed, and acted upon by monitoring systems without disrupting ongoing operations.

## Red Flags

The following anti-patterns represent common mistakes that violate Amplifier's core principles. Recognizing these red flags helps maintain clean architecture and prevents technical debt:

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| **"Add a flag for this use case"** | Flags accumulate over time, creating complex configuration matrices and coupling policy decisions to the kernel. Use modules instead - they allow different teams to implement different behaviors without polluting the core with conditional logic. |
| **"Pass whole context for flexibility"** | Violates the principle of minimal capability. Modules should receive only the specific data they need to perform their function. Passing entire contexts creates unnecessary coupling and makes it harder to reason about what each module actually uses. |
| **"Break API now, adoption is small"** | Sets a dangerous precedent that backward compatibility isn't sacred. Even with small adoption, breaking changes establish a culture where stability can't be trusted. This discourages module development and creates fear of upgrading. |
| **"Add to kernel now, figure out policy later"** | Policy decisions inevitably leak into implementation details. Once policy is embedded in the kernel, it becomes extremely difficult to extract without breaking changes. Always prototype policy decisions in modules first. |
| **"It's only one more dependency"** | Dependencies compound exponentially in their complexity and maintenance burden. Each dependency brings its own update cycle, security considerations, and potential conflicts. The kernel should remain minimal and self-contained. |
| **"We need this in kernel for performance"** | Premature optimization that usually lacks benchmarking evidence. Most performance bottlenecks occur at module boundaries or in I/O operations, not in kernel logic. Prove performance requirements with measurements before sacrificing architectural clarity. |
| **"Let's make this configurable"** | Configuration is policy, and policy belongs in modules. Every configuration option doubles the testing matrix and creates maintenance overhead. If two teams need different behavior, they should use different modules, not different config flags. |
| **"This is a small change to existing code"** | Size of change doesn't determine architectural impact. Small changes can violate boundaries and create coupling that's difficult to undo later. Evaluate changes based on their effect on system boundaries, not line count. |
| **"We'll deprecate the old way later"** | Creates technical debt and dual maintenance burden. If the new approach is better, provide a clear migration path with tooling. Don't leave old patterns in place "temporarily" - they tend to become permanent. |
| **"Just this once, we'll bypass the protocol"** | Protocols exist to maintain system integrity and enable independent development. Bypassing them creates hidden dependencies and makes the system harder to reason about. Every bypass sets a precedent for future violations. |

These anti-patterns often seem reasonable in isolation but compound over time to create unmaintainable systems. When you recognize these patterns emerging, step back and consider how to achieve the same goal while respecting Amplifier's architectural boundaries.

## North Star

## North Star

Amplifier's vision centers on three fundamental principles that work together to create a sustainable, innovative platform:

**Unshakeable Center**: The kernel remains so small, stable, and boring that a single person can maintain it completely. Every line of kernel code justifies its existence by providing mechanisms that multiple modules need. Changes are rare, backward compatibility is sacred, and complexity lives elsewhere.

**Explosive Edges**: A flourishing ecosystem of competing modules drives innovation at the boundaries. Providers compete on model selection and optimization. Orchestrators experiment with different execution strategies. Tools implement diverse capabilities. Hooks enable custom observability and security policies. Each module can evolve independently, fail safely, and be replaced without touching the kernel.

**Forever Upgradeable**: The system ships improvements weekly at the edges while kernel updates remain infrequent and unremarkable. Modules regenerate from specifications rather than accumulating patches. Strong contracts enable parallel development across teams. The event-driven architecture ensures observability without coupling.

This architecture mirrors successful systems like Linux, where a tiny, stable kernel enables an explosive ecosystem of drivers, applications, and distributions. The kernel provides mounting, event emission, and capability checks—pure mechanisms. Modules provide all the policy decisions: which models to use, how to orchestrate requests, what to log, where to route traffic.

The result is a system that gets more powerful over time without becoming more complex at its core. Teams can experiment with radical new approaches by writing new modules, not by modifying shared infrastructure. The kernel stays boring so the edges can stay exciting.

When faced with any architectural decision, ask: "Could two teams reasonably want different behavior here?" If yes, it belongs in a module. If no, it might belong in the kernel—but only after at least two modules have independently demonstrated the need for that mechanism.

This creates a natural pressure valve: innovation happens where it's safe (modules), while stability is preserved where it matters most (kernel). The center stays still so the edges can move fast.

## References

For complete architectural guidance and decision frameworks, refer to these foundational documents:

**[DESIGN_PHILOSOPHY.md](docs/DESIGN_PHILOSOPHY.md)** - Complete design philosophy for Amplifier including core principles, the Linux Kernel Decision Framework, kernel vs module boundaries, evolution rules, implementation patterns, and governance guidelines. Use this document when requirements are unclear to make correct, aligned decisions.

**[KERNEL_PHILOSOPHY.md](docs/KERNEL_PHILOSOPHY.md)** - Detailed kernel philosophy covering the mechanism vs policy distinction, stability guarantees, backward compatibility requirements, and the rationale behind keeping the kernel small and boring while enabling innovation at the edges.

These documents provide the complete theoretical foundation for understanding Amplifier's architecture. When facing implementation decisions, consult the Linux Kernel Decision Framework in DESIGN_PHILOSOPHY.md to determine whether functionality belongs in the kernel (mechanism) or modules (policy).

For specific technical implementation details, see the inline documentation within the codebase and the protocol definitions in the kernel modules.