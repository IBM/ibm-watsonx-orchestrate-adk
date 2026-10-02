from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

# Simulates a documentation search tool that returns large, unstructured text.
@tool(
    name="knowledge_base_search",
    description=(
        "Search the internal knowledge base for documentation on a given topic. "
        "Returns the full matching document sections, which may be lengthy."
    ),
    permission=ToolPermission.READ_ONLY,
)
def knowledge_base_search(query: str) -> str:
    """
    Search internal documentation and return matching content.

    Args:
        query: The topic or question to search for in the knowledge base.

    Returns:
        A string containing all matching document sections. Can be large
        for broad queries — this is intentional to exercise compaction.
    """
    
    # --- Mock: simulate a large documentation retrieval ---    
    # Might need to increase response lenght depending on your compaction settings
    mock_doc = f"""        
    # Knowledge Base Results for: "{query}"

    ## Section 1 — Overview
    IBM watsonx Orchestrate is an AI-powered automation platform that enables
    organizations to build, deploy, and manage AI agents and workflows at scale.
    It provides a low-code/no-code interface for business users alongside a
    developer-grade ADK (Agent Development Kit) for engineers who need full
    programmatic control.

    The platform is designed to meet the needs of both software developers and
    AI engineers. Business users can compose agents and workflows
    visually through the Agent Builder and Flow Builder interfaces, selecting
    from a catalog of pre-built tools and skills without writing a single line
    of code. Software engineers, on the other hand, can use the ADK to define
    agents programmatically in YAML or Python, version-control them in Git,
    and deploy them through CI/CD pipelines just like any other software
    artifact.

    The platform abstracts the underlying model inference layer, 
    allowing teams to swap models without rewriting agent logic. 
    Supported styles include ReAct (react_core), which enables
    iterative tool-use and reasoning loops, and planner-based styles for
    multi-step task decomposition.

    ## Section 2 — Integration Patterns
    Agents can integrate with external systems via multiple mechanisms, each
    suited to different integration scenarios and team skill sets.

    REST tools are defined using OpenAPI specifications. The ADK imports the
    spec and automatically generates the tool interface that the agent can
    invoke. This is the recommended approach for integrating with any system
    that exposes a well-documented HTTP API — SaaS platforms, internal
    microservices, or third-party data providers. Authentication is handled
    via connection objects that are stored securely and injected at runtime,
    keeping credentials out of agent definitions entirely.

    Python function tools are decorated with the @tool decorator from the
    ibm_watsonx_orchestrate.agent_builder.tools module. They give engineers
    full control over integration logic — data transformation, error handling,
    pagination, retries — all expressed in standard Python. Tools are imported
    into the platform via the orchestrate CLI and registered in the tool
    registry, where they become available to any agent with the appropriate
    permissions.

    MCP (Model Context Protocol) servers extend the tool surface by exposing
    collections of tools through a standardized protocol. An MCP server can
    wrap an entire system — a database, a file system, an internal API — and
    make all its capabilities available to agents without individually
    registering each function. This is particularly useful for teams managing
    large tool catalogs or integrating with systems that evolve frequently.

    Agent Skills are reusable, composable units of capability that can be
    shared across multiple agents. A skill encapsulates a specific domain
    competency — for example, looking up a customer record, calculating a
    shipping estimate, or summarizing a document — and can be published to
    the platform's skill catalog for discovery and reuse by other teams.

    ## Section 3 — Conversation Compaction
    A context window (also called context length) is the total number of tokens
    an LLM can consider during a single inference call. Think of it as the model's
    working memory. That includes: system prompts, conversation history, tool outputs,
    retrieved documents, etc.

    As agents handle longer, multi-turn conversations, the accumulated history
    can grow large enough to exceed the context window of the underlying LLM.
    Compaction addresses this by automatically managing conversation history
    so agents can continue operating without hitting context-length errors.

    Without compaction, every user message, assistant response, and tool result
    is appended to the conversation history in full. For short interactions this
    is fine, but for long-running sessions — a research assistant exploring a
    topic across dozens of turns, or a support agent handling a complex case
    with multiple tool calls — the history can grow to tens of thousands of
    tokens. Once the total exceeds the model's hard context limit, the agent
    fails with a context-length error and the conversation cannot continue.

    Compaction addresses this with two complementary mechanisms that operate
    at different granularities.

    Conversation-level compaction monitors the total token count of the
    conversation history. When it exceeds a configured threshold
    (context_compaction_threshold), the platform asynchronously compacts the
    history: the most recent N turns (compaction_sliding_window) are preserved
    verbatim, while all older turns are replaced with a concise LLM-generated
    summary. Because this runs asynchronously, the current user turn is not
    blocked — the user sees no interruption, and the compaction completes in
    the background before the next turn is processed.

    Large message handling operates at the level of individual messages rather
    than the full conversation. When a single message — most commonly a tool
    response returning a large document, dataset, or log dump — exceeds a
    configured token limit (large_message_threshold), it is compressed inline
    before being added to the conversation history. The compression strategy
    depends on the content type: unstructured content such as prose, logs, or
    documentation is handled via a map-reduce summarization pipeline, where
    the message is split into chunks, each chunk is summarized in parallel,
    and the summaries are combined into a final digest targeting a configured
    token length (large_message_target_summary). Structured content such as
    JSON objects or tabular data is instead truncated, which preserves the
    key-value semantics that the agent relies on for downstream reasoning.

    Together, these two mechanisms allow agents to sustain coherent, productive
    conversations across arbitrarily long sessions without requiring the
    developer to implement any custom memory management logic. Compaction is
    configured entirely through the compaction_settings block in the agent
    definition and is transparent to both the end user and the agent's tool
    implementations.

    ## Section 4 — Security Considerations
    Security in watsonx Orchestrate is enforced at multiple layers to ensure
    that agents operate within well-defined trust boundaries.

    Credentials required by tools — API keys, OAuth tokens, database passwords
    — are stored in a platform-managed vault and injected at runtime as
    connection objects. They are never embedded in agent definitions, tool
    source code, or conversation history. This means that credentials can be
    rotated centrally without modifying or redeploying the agents that depend
    on them.

    Role-based access control (RBAC) governs which users and agents can invoke
    which tools. Tool permissions are declared at import time using the
    ToolPermission enum (READ_ONLY, READ_WRITE, ADMIN) and enforced by the
    platform's authorization layer. An agent can only invoke tools that have
    been explicitly listed in its tools array and for which the runtime
    identity has the required permission level.

    All tool invocations are sandboxed. Python tools execute in isolated
    environments with no access to the host filesystem or network beyond what
    is explicitly permitted through registered connections. This containment
    ensures that a misbehaving or compromised tool cannot exfiltrate data or
    affect other agents running on the same platform.

    Conversation history is stored in the platform's Conversation Store and
    is scoped to the authenticated user's session. Agents cannot access
    conversation history belonging to other users, and history is retained
    only for the configured session duration before being purged.

    ## Section 5 — References
    - ADK Documentation: https://developer.watson-orchestrate.ibm.com
    - Conversation Compaction Settings: https://developer.watson-orchestrate.ibm.com/agents/build_agent#conversation-compaction-settings
    - ADK GitHub Repository: https://github.com/IBM/ibm-watsonx-orchestrate-adk
    - ADK Examples: https://github.com/IBM/ibm-watsonx-orchestrate-adk/tree/main/examples
    - Tool Permissions Reference: https://developer.watson-orchestrate.ibm.com/agents/tools
    """
    
    return mock_doc
