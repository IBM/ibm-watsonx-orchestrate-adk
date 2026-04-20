"""Semantic attribute constants for observability spans.

These constants follow OpenTelemetry semantic conventions and provide
domain-specific attributes for LLM, agent, tool, and session tracing.
The module is framework-agnostic and works with any agentic platform.
"""

# --- Environment variable names ---
ENV_OTLP_ENDPOINT = "WXO_OTLP_ENDPOINT"

DEFAULT_SERVICE_NAME = "wxo-agentic-sdk"

# --- Resource attributes (attached to every span via Resource) ---
ATTR_SERVICE_NAME = "service.name"

# --- Baggage-propagated attributes (read from OTEL Baggage context) ---
BAGGAGE_TENANT_ID = "tenant.id"
BAGGAGE_AGENT_ID = "agent.id"

# --- Common span attributes (capture_input / capture_output) ---
ATTR_INPUT = "input.value"
ATTR_OUTPUT = "output.value"

# --- LLM span attributes ---
ATTR_LLM_SYSTEM = "llm.system"
ATTR_LLM_MODEL = "llm.model"
ATTR_LLM_PROVIDER = "llm.provider"
ATTR_LLM_PROMPT_TOKENS = "llm.usage.prompt_tokens"
ATTR_LLM_COMPLETION_TOKENS = "llm.usage.completion_tokens"
ATTR_LLM_TOTAL_TOKENS = "llm.usage.total_tokens"
ATTR_LLM_RESPONSE_MODEL = "llm.response.model"
ATTR_LLM_TEMPERATURE = "llm.temperature"
ATTR_LLM_MAX_TOKENS = "llm.max_tokens"
ATTR_LLM_STOP_REASON = "llm.stop_reason"

# --- Tool span attributes ---
ATTR_TOOL_NAME = "tool.name"
ATTR_TOOL_INPUT = "tool.input"
ATTR_TOOL_OUTPUT = "tool.output"

# --- Agent span attributes ---
ATTR_AGENT_NAME = "agent.name"
ATTR_AGENT_INPUT = "agent.input"
ATTR_AGENT_OUTPUT = "agent.output"
ATTR_AGENT_FRAMEWORK = "agent.framework"

# --- Session attributes ---
ATTR_SESSION_ID = "session.id"
ATTR_USER_ID = "user.id"

# --- Span kind labels (used internally, not OTEL SpanKind) ---
SPAN_KIND_GENERAL = "general"
SPAN_KIND_LLM = "llm"
SPAN_KIND_TOOL = "tool"
SPAN_KIND_AGENT = "agent"
