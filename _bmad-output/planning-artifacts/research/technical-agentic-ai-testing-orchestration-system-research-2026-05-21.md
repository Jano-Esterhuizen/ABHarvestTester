---
stepsCompleted: [1, 2]
inputDocuments: []
workflowType: 'research'
lastStep: 2
research_type: 'technical'
research_topic: 'Agentic AI Testing Orchestration System'
research_goals: 'Evaluate frameworks and patterns for building a multi-agent test orchestration system that discovers codebases, generates tests, and executes them via Playwright MCP'
user_name: 'TheBadenhorsts'
date: '2026-05-21'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-05-21
**Author:** TheBadenhorsts
**Research Type:** Technical

---

## Research Overview

**Topic:** Agentic AI Testing Orchestration System
**Goals:** Evaluate frameworks and patterns for building a multi-agent test orchestration system that discovers codebases, generates tests, and executes them via Playwright MCP

**System Under Research — Agent Architecture:**

| Agent | Role |
|-------|------|
| ORC (Orchestrator) | Controls agent sequencing and routing |
| Repo Reader | Reads target repo → produces context document for all other agents |
| Scraper | Scrapes repo to generate Swagger/OpenAPI doc → passes to test writers |
| Front End Test Writer | Writes positive + negative UI tests with Playwright |
| Back End Test Writer | Writes contract/integration tests with Playwright |
| Reviewer | Runs tests, investigates failures, routes failure info back to writers |

**Technical Research Scope:**

- Architecture Analysis — multi-agent orchestration patterns, agent-to-agent communication, task routing
- Implementation Approaches — discovery agents, test-writing agents, test-execution agents, feedback loops
- Technology Stack — LangGraph, AutoGen, CrewAI, custom orchestrators, Playwright, MCP SDK
- Integration Patterns — MCP as universal integration layer, Playwright MCP for test execution
- Performance Considerations — parallel agent execution, scaling test generation

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-05-21

---

## Technology Stack Analysis

### Multi-Agent Orchestration Frameworks

#### Microsoft Agent Framework (MAF) — RECOMMENDED
_Status: Production-ready v1.5.0 (released May 2026). Enterprise successor to AutoGen._
_Languages: Python + C#/.NET_
_License: MIT_
_Source: https://github.com/microsoft/agent-framework (10.6k stars)_

- **Graph-based orchestration patterns**: sequential, concurrent, handoff, and group collaboration
- **MCP integration built-in**: `Microsoft.Agents.AI.Workflows.Declarative.Mcp` package available
- **Durability & restartability**: checkpointing, time-travel debugging, human-in-the-loop
- **Observability**: Built-in OpenTelemetry integration for distributed tracing
- **Declarative Agents**: Define agents using YAML for faster setup and versioning
- **Azure-native**: Foundry hosted agents, Azure Functions hosting, A2A protocol support
- **Multi-provider**: Azure OpenAI, OpenAI, and extensible model support
- **Middleware system**: Flexible request/response processing and custom pipelines
- **Key advantage for your use case**: .NET support means alignment with typical enterprise stacks; Python support gives flexibility for AI/ML tooling

#### LangGraph (LangChain)
_Status: Stable, MIT-licensed open-source_
_Language: Python (primary), JS/TS available_
_Source: https://github.com/langchain-ai/langgraph_

- **Low-level orchestration primitives**: Full control over agent workflows
- **Multi-agent architectures**: Single, multi-agent, hierarchical — all in one framework
- **Built-in memory**: Conversation histories and context persistence across sessions
- **Human-in-the-loop**: Easy-to-add moderation and quality controls
- **First-class streaming**: Token-by-token for real-time UX
- **LangSmith integration**: Observability, evaluation, deployment platform
- **Key advantage for your use case**: Most flexible for custom orchestration logic; strong community
- **Consideration**: Python-only for production; no native .NET

#### CrewAI
_Status: Production-ready, enterprise tier available_
_Language: Python_
_Source: https://github.com/crewAIInc/crewAI_

- **Role-based agent design**: Each agent has role, goal, backstory, tools
- **YAML configuration**: Declarative agent and task definition (recommended approach)
- **Delegation**: Agents can delegate tasks to other agents
- **Memory & knowledge**: Built-in memory, knowledge sources, embedder configuration
- **Reasoning mode**: Agents can reflect and plan before executing
- **Context window management**: Automatic summarization when limits exceeded
- **Code execution**: Sandboxed execution via E2B or Modal
- **Structured output**: Pydantic models for typed agent responses
- **Key advantage for your use case**: Easiest to get started; natural "crew" metaphor maps well to your agent roles
- **Consideration**: Less low-level control than LangGraph; Python-only

#### AutoGen (Microsoft) — DEPRECATED
_Status: ⚠️ MAINTENANCE MODE — no new features_
_Successor: Microsoft Agent Framework_
_Source: https://github.com/microsoft/autogen (58.3k stars)_

- Previously the leading multi-agent framework
- Has `McpWorkbench` extension for MCP server integration
- Built-in Playwright MCP example in quickstart
- **Do not use for new projects** — Microsoft explicitly recommends migrating to MAF
- Migration guide available at learn.microsoft.com

### Browser Automation & Test Execution

#### Playwright MCP (Microsoft Official)
_Status: Active development, v0.0.75 (May 2026), 65 releases_
_Source: https://github.com/microsoft/playwright-mcp (32.8k stars, 66 contributors)_
_Language: TypeScript/JavaScript_

- **MCP server for browser automation** — the exact tool your agents need
- **Accessibility tree based**: No vision models needed, operates on structured data
- **Deterministic tool application**: Avoids ambiguity of screenshot-based approaches
- **Key capabilities**:
  - Core automation (click, fill, navigate, select)
  - Tab management
  - Test assertions (opt-in via `--caps=testing`)
  - Code generation (`--codegen typescript`)
  - Network monitoring (opt-in via `--caps=network`)
  - DevTools access (opt-in via `--caps=devtools`)
  - PDF generation (opt-in via `--caps=pdf`)
- **Session management**: Persistent profiles, isolated contexts, or browser extension connection
- **Configuration**: Extensive CLI flags or JSON config file
- **Standalone mode**: Can run as HTTP server (`--port 8931`) for remote access
- **Note from Microsoft**: For high-throughput coding agents, consider Playwright CLI + SKILLS over MCP for token efficiency. MCP remains better for "exploratory automation, self-healing tests, or long-running autonomous workflows" — **which is exactly your use case**

#### Playwright CLI + SKILLS
_Source: https://github.com/microsoft/playwright-cli_

- Token-efficient alternative to MCP for coding agents
- CLI invocations avoid loading large tool schemas
- Better for agents that must balance browser automation with large codebases
- Could be used by your test-writing agents for efficiency, while reviewer agent uses MCP for exploratory testing

### Integration Protocol

#### Model Context Protocol (MCP)
_Status: Open standard, broad ecosystem support_
_Source: https://modelcontextprotocol.io_

- **Open-source standard** for connecting AI applications to external systems
- Supported by: Claude, ChatGPT, VS Code, Cursor, Windsurf, Goose, and many others
- **Architecture**: Client-server model where AI apps are clients, tools/data are servers
- **Your design alignment**: Other teams build MCP servers for their apps → your agents consume them as MCP clients
- **Key benefit**: "Build once, integrate everywhere" — standardized interface regardless of what the other teams build

### Programming Languages

| Language | Role in This Project | Rationale |
|----------|---------------------|-----------|
| **Python** | Primary agent orchestration, AI/ML tooling | All major agent frameworks support Python; richest LLM ecosystem |
| **TypeScript** | Playwright MCP server, test output format | Playwright is TS-native; test codegen outputs TypeScript by default |
| **C#/.NET** | Optional if team prefers (MAF supports it) | Enterprise alignment; MAF has full .NET parity |

### Development Tools and Platforms

| Tool | Purpose |
|------|---------|
| **VS Code** | Primary IDE — native MCP client, Copilot integration |
| **Playwright** | Browser automation engine (via MCP or CLI) |
| **Docker** | Isolated test execution environments |
| **Git** | Source control for generated tests |
| **OpenTelemetry** | Observability across agent interactions |

### Technology Adoption Trends

- **MCP adoption is accelerating**: 32.8k stars on Playwright MCP alone; standard is now supported by all major AI IDEs and assistants
- **Multi-agent is maturing**: Microsoft invested heavily (AutoGen → MAF migration shows commitment to production-grade multi-agent)
- **Agent-as-tool pattern emerging**: MAF's `AgentTool` and CrewAI's delegation show the industry converging on agents-wrapping-agents
- **Playwright dominates browser testing**: Accessibility-tree approach over pixel-based is now the standard for AI-driven testing
- **Framework consolidation**: AutoGen deprecated in favour of MAF signals market consolidation; LangGraph and CrewAI remain independent alternatives

## Integration Patterns Analysis

### Core Protocol: Model Context Protocol (MCP)

_Source: https://modelcontextprotocol.io/docs/learn/architecture_
_Protocol Version: 2025-06-18 (latest spec: 2025-11-25)_

MCP is THE integration protocol for this project. It defines how your agents will consume other teams' services.

**Architecture:**
- **MCP Host** — Your orchestrator (the AI application coordinating agents)
- **MCP Client** — One per connected server; maintains dedicated connection
- **MCP Server** — Other teams' apps, Playwright, filesystem, etc.

**Transport options:**
| Transport | Use Case | Your System |
|-----------|----------|-------------|
| **STDIO** | Local process communication, zero network overhead | Playwright MCP, local tools |
| **Streamable HTTP** | Remote servers, supports auth (OAuth, API keys, bearer tokens) | Other teams' app MCPs |

**Three primitives servers expose:**
1. **Tools** — Executable functions (e.g., `run_test`, `get_endpoints`, `navigate_page`)
2. **Resources** — Data sources for context (e.g., file contents, API docs, schemas)
3. **Prompts** — Reusable interaction templates

**Key protocol mechanics:**
- JSON-RPC 2.0 based — standard request/response/notification
- Capability negotiation at connection time (both sides declare what they support)
- Tool discovery via `tools/list` → execution via `tools/call`
- Real-time notifications when tools change (`notifications/tools/list_changed`)
- Structured output with JSON Schema validation (`outputSchema`)
- Error reporting: protocol errors (JSON-RPC) + tool execution errors (`isError: true`)

**Security requirements from spec:**
- Servers MUST validate all tool inputs, implement access controls, rate limit, sanitize outputs
- Clients SHOULD prompt for user confirmation on sensitive ops, validate results, implement timeouts

### Agent-to-Agent Communication: A2A Protocol

_Source: https://github.com/a2aproject/A2A (23.9k stars, v1.0.0 released March 2026)_
_SDKs: Python, Go, JS, Java, .NET_

A2A complements MCP — while MCP connects agents to tools/data, A2A connects agents to OTHER AGENTS.

**Why this matters for your orchestrator:**
- Your sub-agents (Repo Reader, Scraper, Test Writers, Reviewer) could communicate via A2A
- Enables "opaque" collaboration — agents don't expose internal state to each other
- Framework-agnostic — agents built with different frameworks can still collaborate

**Key features:**
- **Agent Cards**: JSON discovery documents describing capabilities and connection info
- **Flexible interaction**: Synchronous, streaming (SSE), and async push notifications
- **Rich data exchange**: Text, files, structured JSON
- **Task lifecycle**: Long-running task management with status tracking
- **Enterprise-ready**: Built-in auth, security, observability patterns

**Relationship to MCP:**
```
┌─────────────────────────────────────────────────────────┐
│           YOUR SYSTEM (MCP Host / A2A Network)          │
│                                                          │
│  Orchestrator ←─A2A─→ Repo Reader                       │
│       │        ←─A2A─→ Scraper                          │
│       │        ←─A2A─→ FE Test Writer                   │
│       │        ←─A2A─→ BE Test Writer                   │
│       │        ←─A2A─→ Reviewer                         │
└───────┼──────────────────────────────────────────────────┘
        │ MCP Client connections (outbound)
        ▼
┌───────────────────┐  ┌──────────────────┐  ┌─────────────┐
│ Other Team's App  │  │  Playwright MCP  │  │ Filesystem  │
│  MCP Server       │  │  Server          │  │ MCP Server  │
│ (HTTP transport)  │  │ (STDIO/HTTP)     │  │ (STDIO)     │
└───────────────────┘  └──────────────────┘  └─────────────┘
```

### Integration Pattern: How Other Teams Expose Their Apps

**What you need from other teams (their MCP server should provide):**

| Primitive | What They Expose | Your Agent Consumes |
|-----------|-----------------|---------------------|
| **Tools** | API endpoints (CRUD operations), UI navigation actions | Scraper, Test Writers |
| **Resources** | OpenAPI/Swagger spec, route maps, component trees, DB schema | Repo Reader |
| **Prompts** | Testing hints, business rules, validation criteria | Test Writers |

**Minimum viable MCP server for other teams:**
```json
{
  "capabilities": {
    "tools": { "listChanged": true },
    "resources": {}
  }
}
```
They expose tools for interacting with their app + resources for documentation/schema. Your agents discover and consume them dynamically.

### Communication Patterns for Your Orchestrator

| Pattern | When | Implementation |
|---------|------|----------------|
| **Sequential** | Repo Reader → Scraper → Test Writers (dependency chain) | Orchestrator waits for each step |
| **Parallel fan-out** | FE + BE Test Writers run simultaneously | Both receive same context, work independently |
| **Feedback loop** | Reviewer → back to Test Writer on failure | A2A task with status updates, or orchestrator re-routes |
| **Event-driven** | Tool list changes (new endpoints deployed) | MCP `notifications/tools/list_changed` triggers re-scan |

### Data Flow & Formats

| Handoff | Format | Why |
|---------|--------|-----|
| Repo Reader → All agents | Markdown context doc | LLM-friendly, structured, version-controlled |
| Scraper → Test Writers | OpenAPI/Swagger JSON | Standard, parseable, contains endpoint schemas |
| Test Writers → Reviewer | Playwright test files (.spec.ts) | Executable, standard format |
| Reviewer → Orchestrator | Structured JSON (pass/fail + diagnostics) | Machine-parseable for routing decisions |
| Reviewer → Test Writer (failures) | JSON with failure context + stack traces | Actionable for LLM to fix tests |

### Integration Security Considerations

| Concern | Mitigation |
|---------|-----------|
| **MCP server trust** | Only connect to known team MCPs; validate tool schemas |
| **Credential management** | OAuth/bearer tokens for remote MCPs; secrets never in agent prompts |
| **Rate limiting** | Respect `max_rpm` on tool calls; implement backoff |
| **Output validation** | Always validate structured tool results against `outputSchema` |
| **Sandboxing** | Run test execution in isolated Docker containers |
| **Data exfiltration** | Show tool inputs to human before sensitive operations |

<!-- Content will be appended sequentially through research workflow steps -->
