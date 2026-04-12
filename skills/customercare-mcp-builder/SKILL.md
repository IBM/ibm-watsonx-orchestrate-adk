---
name: customercare-mcp-builder
description: Build MCP servers for customer care agents following Watson Orchestrate specifications. Guides agents through tool creation, transaction patterns, authentication, widgets, and context management with strict adherence to reference specifications. Use when creating customer care MCP servers.
---

# CustomerCare MCP Server Builder

This skill guides you through building production-ready MCP (Model Context Protocol) servers for customer care agents. Follow the specifications and patterns documented below exactly. All reference implementations are in `references/examples.md`.

## CRITICAL INSTRUCTIONS FOR AGENTS

### 0. Ask About Programming Language

**Before starting any implementation, ASK the user:**

"Which programming language would you like to use for this MCP server?"
- **TypeScript**
- **Python**

Both languages have complete reference implementations in `references/examples.md`. Use the chosen language to build the MCP server.

### 1. ALWAYS Provide Tool Summary First

**Before writing any code**, create a comprehensive summary of all tools to be implemented:

- List each tool with its name, purpose, and pattern type
- Identify which tools need widgets, confirmations, or chaining
- Specify authentication requirements
- Document context management needs

**Example Summary Format:**
```
Tools to Create:
1. get_account_balance - Direct Response pattern, no confirmation
2. transfer_money - Transaction pattern (two-step), confirmation widget
3. update_profile - Hybrid Response, requires authentication check
4. welcome - Welcome tool (required on ALL servers)
5. knowledge_search - RAG integration (if OpenSearch available)
```

### 2. ALWAYS Confirm Specifications Before Coding

**For EACH tool**, before writing code:

1. **Review the relevant pattern** from the Pattern Specifications section below
2. **Present the specification to the user** and ask:
   - "Should this tool use a transaction pattern with confirmation?"
   - "What widgets are needed (picker, form, confirmation)?"
   - "Should this be a direct response or hybrid response?"
3. **Reference implementation examples** in `references/examples.md`

**DO NOT assume** -- Always confirm with the user before implementing.

### 3. Welcome Tool is MANDATORY

**Every MCP server MUST have a welcome tool.** See the Welcome Tool pattern below.

**Before creating the welcome tool, ASK the user:**

1. **Authentication Method:** JWT-based auto-auth or credential verification (PIN, password)?
2. **Welcome Message:** What should it say? What tone?
3. **Target Audience:** Who are the users (customers, employees, partners)?
4. **Schema Requirements:** What user information needs to be collected?

**Reference:** See "Welcome & Authentication Tools" section in `references/examples.md`

### 4. Knowledge Tool -- Confirm OpenSearch Setup

**Before implementing knowledge/RAG functionality, ASK:**

1. "Do you have an OpenSearch instance already set up?"
2. "What indices/collections should be searched?"

If OpenSearch is NOT available, do NOT implement the knowledge tool.

**Reference:** See "Knowledge/RAG Tools" section in `references/examples.md`

### 5. Server Startup Code -- Follow Reference EXACTLY

**Copy the server entry point from `references/examples.md` exactly.** Key requirements:

- **TypeScript:** Use `@modelcontextprotocol/sdk`, `express`, `pino` with EXACT versions from `references/examples.md`
- **Python:** Use `mcp>=1.0.0`, `starlette>=0.40.0`, `uvicorn>=0.30.0` with EXACT versions from `references/examples.md`
- **MUST use `StreamableHTTPServerTransport`** (no session validation) - **DO NOT use SSE transport** SSE is not supported
- Create per-request server instances based on customer authentication state

**Folder Structure:**
```
project/
├── src/
│   ├── index.ts (or main.py + server.py)
│   ├── globalStore.ts (or global_store.py)
│   ├── localStore.ts (or local_store.py)
│   ├── logger.ts (or logger.py)
│   ├── customerDatabase.ts (or customer_database.py)
│   ├── [tool_name].ts (or [tool_name].py)
│   └── [tool_name]Service.ts (or [tool_name]_service.py)
├── package.json (or pyproject.toml)
└── .env.example
```

### 6. Widget Definitions -- NO DEVIATIONS

Widget specifications MUST be followed exactly. See Widget Types Reference below.

### 7. Final Solution Must Be Error-Free and Executable

Before presenting final solution: validate all code against the pattern specifications below, verify widget definitions match the Widget Types Reference, ensure all imports are correct, and confirm startup scripts work.

---

## Pattern Specifications

### Transactions (Two-Step Confirmation)

**When to use:** Any sensitive or irreversible operation (money transfers, payments, cancellations, profile changes).

**Pattern:**
- **Step 1 (prepare):** Model-visible tool collects inputs via widgets, then shows confirmation widget. Stores transaction details in LOCAL store.
- **Step 2 (confirm/cancel):** Hidden tool (`visibility: ['app']`) processes user's explicit confirm or cancel action.

**Key Rules:**
- Model can NEVER auto-confirm transactions
- Generate unique transaction ID per transaction
- Store details in LOCAL store (Layer 3), not global store
- Verify ownership before executing
- Clean up local variable after processing

**Naming convention:** `prepare_[action]` and `confirm_or_cancel_[action]`

**Confirm/cancel tool config:**
```typescript
config: {
  _meta: {
    ui: { visibility: ['app'] }  // Hidden from model -- only callable by UI widget
  }
}
```

**Confirmation widget schema:**
```typescript
{
  type: 'confirmation',
  title: 'Confirm Transfer',
  confirmation_text: '## Confirm\n\n**Details...**',
  on_confirm: {
    tool: 'confirm_or_cancel_[action]',
    parameters: { transactionId, action: 'confirm' },
  },
  on_cancel: {
    tool: 'confirm_or_cancel_[action]',
    parameters: { transactionId, action: 'cancel' },
  },
}
```

> **⚠ Widget-only responses:** Confirmation widgets (and other pure-widget steps like account pickers) often return **only** `_meta` with no `content` array. Your `handle_call_tool` must handle empty content gracefully — do not default to a fallback text when `_meta` is present. See `server.py` in `references/examples.md`.

### Direct Response (Tool Responses to Users)

**When to use:** Financial amounts, regulatory-required info, dates, account numbers -- anything that must be exact with zero hallucination risk.

**Pattern:** Set `annotations: { audience: ['user'] }` on content blocks. Content goes directly to user, bypassing the LLM entirely.

```typescript
return {
  content: [{
    type: 'text',
    text: `Balance: $${balance.toFixed(2)}`,
    annotations: { audience: ['user'] },
  }],
};
```

**Tradeoff:** Model does NOT see this content, so it cannot reason about it. Use hybrid response when model needs context.

### Hybrid Response

**When to use:** When you need both exact data display AND model awareness for conversation flow.

**Pattern:** Two content blocks -- one for model (`audience: ['assistant']`), one for user (`audience: ['user']`). `structuredContent` is always visible to the model.

```typescript
return {
  content: [
    { type: 'text', text: 'Payment history retrieved. Data displayed to user.', annotations: { audience: ['assistant'] } },
    { type: 'text', text: `**Payment History**\n\n${table}`, annotations: { audience: ['user'] } },
  ],
  structuredContent: paymentData,
};
```

### Tool Chaining

**When to use:** Deterministic tool-to-tool calls without LLM reasoning (e.g., locked account -> agent handoff).

**Pattern:** Return `_meta.nextTool` with tool name and arguments.

```typescript
return {
  content: [{ type: 'text', text: 'Account is locked.', annotations: { audience: ['user'] } }],
  _meta: {
    nextTool: {
      tool: 'request_agent_handoff',
      arguments: { reason: 'Locked account' },
    },
  },
};
```

**Rules:** Only for tool-to-tool chaining (not user input dependent). Client must implement depth limits (recommended: 5).

### Three-Layer Context System

MCP tools have access to three layers of context:

| Layer | Namespace | Scope | Lifetime | Use For |
|-------|-----------|-------|----------|---------|
| 1. Context Variables | `com.ibm.orchestrate/context` | Per-request | Single API call | Auth tokens (JWT), app-provided config |
| 2. Global Store | In-memory map | Per-thread | Until conversation ends | Data shared across MCP servers (customerId) |
| 3. Local Store | In-memory map | Per-thread per-server | Until thread ends | Pending transactions, workflow state |

**Accessing context variables:**
```typescript
// TypeScript (McpServer high-level SDK) -- extra is passed automatically
const jwtToken = extra?._meta?.['com.ibm.orchestrate/context']?.jwtToken;
const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;
const locale = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.locale;
```
```python
# Python (low-level Server SDK) -- extract _meta from request context, NOT function parameters
ctx = server.request_context
extra = {}
if ctx and ctx.meta:
    extra['_meta'] = ctx.meta.model_dump()

jwt_token = extra.get('_meta', {}).get('com.ibm.orchestrate/context', {}).get('jwtToken')
thread_id = extra.get('_meta', {}).get('com.ibm.orchestrate/systemcontext', {}).get('thread_id')
locale = extra.get('_meta', {}).get('com.ibm.orchestrate/systemcontext', {}).get('locale')
```

> **⚠ Python low-level SDK:** When using the low-level `Server` class (not `McpServer`), `_meta` is **not** passed as a function parameter to `@server.call_tool()` handlers. You **must** read it from `server.request_context.meta.model_dump()`. Passing `_meta` as a handler parameter will silently be `None`, causing thread_id lookups to fail. See `server.py` in `references/examples.md` for the correct pattern.

**Critical:** NEVER trust the model to provide authentication data. Always inject customerId from the store or extract from JWT.

### Unique Tools Per User

**Pattern:** Create per-request MCP server instances with only the tools relevant to a customer's products/entitlements.

- Unauthenticated users: only welcome + handoff tools
- After auth: register product-specific tools based on customer profile
- Must declare `resources` capability and handle empty resources list
- Use `registerToolsWithCustomerId` wrapper to inject customerId from global store

See `references/examples.md` Section 2 (Server Core Infrastructure) for the complete implementation.

### Welcome Tool

**Requirements:**
- `_meta.welcomeTool: true` designates automatic invocation at thread start
- Must be `visibility: ['app']` (hidden from model)
- Empty `inputSchema` (no required arguments)
- Only ONE welcome tool invoked per thread, even across multiple servers
- Should execute quickly

**After successful auth, signal tool refresh:**
```typescript
return {
  content: [{ type: 'text', text: 'Verified!', annotations: { audience: ['user'] } }],
  _meta: { refreshThreadCapabilities: threadId },
};
```

This triggers ALL MCP servers to refresh their tool/resources lists for the thread.

### Authentication

**Two approaches:**

1. **Client Authentication (recommended):** JWT passed via context variables. Tool extracts and uses directly.
2. **Agent Authentication (voice/IVR):** PIN verification in-agent, stores customerId in global store, triggers `refreshThreadCapabilities`.

**After successful auth:**
1. Store customerId in global store: `setGlobalVariable(threadId, 'customerId', profile.customerId)`
2. Return `_meta: { refreshThreadCapabilities: threadId }`
3. Client refreshes tool lists from ALL MCP servers
4. Servers check for customerId and return authenticated tools

### Agent Handoff

**Pattern:** Two-step user-controlled handoff:
1. Present options (realtime or callback) via options widget
2. Process choice -- for realtime, use `transfer_to_live_agent` extension

**Extension schema:**
```typescript
_meta: {
  'com.ibm.orchestrate/extensions': {
    transfer_to_live_agent: {
      message_to_human_agent: "Context for the agent...",
      agent_available: "Please wait while I connect you.",
      agent_unavailable: "No agents online. Try again later.",
    }
  }
}
```

### Knowledge/RAG Integration

- Conditional registration: only when `OPENSEARCH_PASSWORD` env var is set
- Returns both formatted text and `structuredContent`
- Configurable field mappings and query bodies via environment variables
- Uses neural/semantic search by default

### Localization

- Model auto-localizes content that passes through it
- You MUST manually localize content with `audience: ['user']` and all widget text
- Access locale: `_meta['com.ibm.orchestrate/systemcontext'].locale` (BCP 47 format)
- Always fallback to `en-US`
- Use template-based localization with `{placeholder}` syntax

---

## Technical Reference

### Model Visibility

**Content visibility:**

| Content Type | Model Sees? | User Sees? | Notes |
|---|---|---|---|
| `content` (no audience annotation) | Yes | Yes | Standard behavior for tool responses |
| `content` with `audience: ['user']` | No | Yes | Goes directly to user, bypasses LLM |
| `content` with `audience: ['assistant']` | Yes | No | Provides context to model without showing user |
| `structuredContent` | Yes | Yes | Always visible to model — use for data model should see and reason about |
| `_meta` | Never | Never | Hidden from model — use for widgets, internal data, extensions |

**Tool visibility:**

| Tool Configuration | Model Can See/Call? |
|---|---|
| No `_meta.ui.visibility` | Yes |
| `_meta.ui.visibility: ['app']` | No -- only callable by system/widgets |

### Widget Types Reference

Tools declare widget support via `_meta.ui.resourceUri: "ui://ibm.com/orchestrate/widget"`. Widgets are returned in `_meta['com.ibm.orchestrate/widget']`.

**ConfirmationWidget:**
```typescript
{
  type: 'confirmation',
  title: string,
  confirmation_text?: string,  // Supports markdown
  on_confirm: { tool: string, parameters: { [key: string]: unknown } },
  on_cancel: { tool: string, parameters: { [key: string]: unknown } },
}
```

**DatetimeWidget:**
```typescript
{
  type: 'datetime',
  collection_type: 'date' | 'time' | 'datetime',
  title: string,
  description?: string,
  min_datetime?: string,  // YYYY-MM-DD for date, hh:mm for time
  max_datetime?: string,
  on_event: { tool: string, parameters: { [key: string]: unknown }, map_input_to: string },
}
```

**NumberWidget:**
```typescript
{
  type: 'number',
  collection_type: 'integer' | 'currency' | 'percentage' | 'decimal' | 'phone' | 'zip_code',
  title?: string,
  description?: string,
  min_number?: number,
  max_number?: number,
  min_digits?: number,
  max_digits?: number,
  on_event: { tool: string, parameters: { [key: string]: unknown }, map_input_to: string },
}
```

> **⚠ Type coercion:** Number widgets send values as integers (e.g., `1234`). If comparing against a string field (like a PIN stored as `"1234"`), you **must** cast to string first: `pin = str(args.get("pin", ""))` in Python or `String(pin)` in TypeScript. Mismatched types will silently fail equality checks.

**OptionsWidget:**
```typescript
{
  type: 'options',
  title: string,
  description: string,              // ⚠ Required by DCA client validation
  is_multi_selection?: boolean,
  options: Array<{ label: string, value: string, description?: string,
    on_event?: { tool: string, parameters: object } }>,  // Per-option events
  on_event: Array<{ event_type: 'message' | 'tool', option_value: string, tool?: string, parameters?: object, map_input_to?: string }>,
  // OR simplified form:
  on_event: { tool: string, parameters: object, map_input_to: string },
}
```

> **⚠ Required fields:** The `description` field is **required** by the DCA client's Pydantic validation — omitting it causes a server-side crash. Options can also carry per-option `on_event` callbacks for different actions per choice (e.g., "retry" vs "speak with agent").

**TextWidget:**
```typescript
{
  type: 'text',
  collection_type: 'text' | 'regex',
  title: string,
  description?: string,
  regex_expression?: string,
  on_event: { tool: string, parameters: { [key: string]: unknown }, map_input_to: string },
}
```

### Annotations Reference

Content block annotations modify rendering behavior via `_meta['com.ibm.orchestrate/annotations']`:

**PauseAnnotation:** `{ pause: { delay: 1000 } }` -- millisecond delay before rendering

**SpeechAnnotation:**
```typescript
{
  speech: {
    disable_speech_barge_in?: boolean,
    disable_dtmf_barge_in?: boolean,
    disable_speech_to_text?: boolean,
    text_to_speech_config?: { voice?: string, [key: string]: unknown },
  }
}
```

**Media content** via `resource_link`:
```typescript
{ type: 'resource_link', resource: { uri: "https://example.com/audio.mp3", mimeType: "audio/mpeg", text: "Description" }, annotations: { audience: ["user"] } }
```

### Context Variables Reference

Three namespaces:

1. **System Context** (`com.ibm.orchestrate/systemcontext`): `thread_id` (always present), `locale` (BCP 47, always present), `wxo_email_id`, `wxo_user_name`, `wxo_tenant_id`

2. **Channel Context** (`com.ibm.orchestrate/channelcontext`): `channel_type` + channel-specific attributes. Supported: slack, sip, genesys_bot_connector, text_messaging, whatsapp, teams, chat, genesys_audio_connector

3. **Application Context** (`com.ibm.orchestrate/context`): App-provided custom fields (e.g., `jwtToken`, `telephoneNumber`). Flexible schema, always available.

### Extensions Reference

Extensions in `_meta['com.ibm.orchestrate/extensions']` signal client actions:

- **`transfer_to_live_agent`**: `{ message_to_human_agent, agent_available, agent_unavailable }`
- **`transfer_to_channel`**: `{ message_to_user, transfer_info: { target: { chat: { url } } } }`
- **`end_interaction`**: `{}` -- ends the conversation
- **`speech_to_text`** / **`text_to_speech`**: `{ command_info: { type, parameters? } }`

### Specification Changes

**`refreshThreadCapabilities`:** When any MCP server returns `_meta.refreshThreadCapabilities: threadId`, the client refreshes `tools/list` and `resources/list` from ALL MCP servers for that thread. Critical for auth state changes.

**Multiple Widgets Per Tool:** Tools can declare `_meta.ui.resourceUris: string[]` (array) and dynamically select which widget via `_meta.ui.resourceUri` in the response. Response `resourceUri` MUST be in the declared array.

**Tool Chaining Metadata:** `_meta.nextTool: { tool: string, arguments?: Record<string, any> }`. Client must validate arguments, implement depth limits (5), and detect circular chains.

**Welcome Tool Metadata:** `_meta.welcomeTool: true` on tool registration. One per server max. One invoked per thread. Must work without required arguments.

---

## Workflow for Building an MCP Server

### Step 1: Choose Programming Language
1. **Ask the user:** "Which programming language would you like to use: TypeScript or Python?"
2. Use the chosen language consistently throughout the entire project
3. Reference the appropriate examples from `references/examples.md`

### Step 2: Gather Requirements
1. Ask about the domain and use case
2. Identify required tools and their purposes
3. Determine authentication requirements
4. Check for OpenSearch/knowledge integration needs

### Step 3: Create Tool Summary
1. List all tools with their pattern types (direct response, hybrid, transaction, etc.)
2. Identify widget requirements for each tool
3. Document context management needs
4. Present summary to user for confirmation

### Step 4: Design Welcome Tool
1. Ask authentication questions (see section 3 above)
2. Confirm welcome message and tone
3. Define schema and validation rules
4. Implement based on `references/examples.md` reference

### Step 5: Implement Each Tool
1. Review the relevant pattern specification above
2. Present specification to user
3. Confirm transaction pattern and widgets
4. Implement following `references/examples.md` reference
5. Validate against specifications

### Step 6: Implement Server Core
1. Copy server startup code from `references/examples.md`
2. Use EXACT dependency versions from `references/examples.md`
3. Maintain folder structure
4. Configure logging (optional) and context management

### Step 7: Add Knowledge Tool (if needed)
1. Confirm OpenSearch availability
2. Copy implementation from `references/examples.md`
3. Update only configuration (endpoint, credentials, index names)

### Step 8: Final Validation
1. Review all code against pattern specifications
2. Verify widget definitions match Widget Types Reference
3. Ensure all imports are correct
4. Confirm installation instructions work

## Critical Reminders

- **ALWAYS** ask about programming language preference first (TypeScript or Python)
- **ALWAYS** provide tool summary first
- **ALWAYS** confirm specifications before coding
- **ALWAYS** ask about welcome tool requirements
- **ALWAYS** confirm OpenSearch setup for knowledge tools
- **ALWAYS** use exact server implementation from `references/examples.md`
- **ALWAYS** validate against pattern specifications
- **NEVER** deviate from widget schemas
- **NEVER** modify dependency versions
- **NEVER** assume -- always ask the user

## License
MIT License - See individual server directories for complete license information.
