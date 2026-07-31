# Agents, Tools & Flows — Schemas and Decorators

Grounded in the ADK source (`agent_builder/agents/types.py`, `agent_builder/tools/python_tool.py`, `flow_builder`).
Current as of `ibm-watsonx-orchestrate` 2.12.x.

## Contents
- [§1 Agent YAML — `kind: native` (full schema)](#1-agent-yaml--kind-native-full-schema)
- [§2 Python Tools — `@tool` decorator](#2-python-tools--tool-decorator-full-reference)
- [§3 Flows — `@flow` decorator and node API](#3-flows--flow-decorator-and-node-api)
  - Canonical template · Node builders · Wiring/data mapping · Script node · Private schema
  - Parallel branches · Decision branch · Callbacks · Data masking · Dynamic forms
  - `foreach` · Agent node · Error branching · Agent swarm / looping · `@flow` extra params
- [§4 Document Processing (docproc) — KVP extraction](#4-document-processing-docproc--kvp-extraction)
- [§5 Document Extraction — `docext` and `docclassifier`](#5-document-extraction--aflowdocext-and-aflowdocclassifier)
- [§6 `userflow` — full field API](#6-userflow--full-field-api)
- [§7 Custom RAG tool pattern](#7-custom-rag-tool-pattern-for-unsupported-vector-stores)

---

## 1. Agent YAML — `kind: native` (full schema)

```yaml
spec_version: v1                 # REQUIRED
kind: native                     # REQUIRED
name: my_agent                   # REQUIRED — snake_case, no spaces
description: What this agent does and when to use it.   # REQUIRED (used for routing)
display_name: My Agent           # optional, UI label
instructions: |                  # the system prompt / behavior
  You are ... When the user ..., call <tool>. Be concise.
llm: watsonx/meta-llama/llama-3-3-70b-instruct   # defaults to tenant default if omitted
llm_config:                      # optional (2.11+) — per-agent decoding params
  temperature: 0
  max_tokens: 2048
  # top_p / top_k / seed / response_format / reasoning_effort + provider extensions
style: react_intrinsic           # 2.12.0 default; `default` & `react` DEPRECATED (omit to take tenant default)
                                 # other values: planner | custom | experimental_customer_care
hide_reasoning: false
tools:                           # by name; must be imported first
  - get_weather
collaborators:                   # ORCHESTRATOR pattern: other agents (by name). Import/deploy FIRST.
  - billing_agent                # wxO auto-generates chat_with_collaborator_<name> tool.
                                 # Routing driven by collaborator `description`. (live-verified 2.12.0)
                                 # Not valid for experimental_customer_care style.
knowledge_base:
  - product_docs
toolkits: []                     # only for experimental_customer_care style
guidelines:
  - display_name: Escalate
    condition: user asks for a human
    action: hand off to billing_agent
    tool: billing_agent
structured_output:               # force structured JSON replies
  type: object
  properties:
    answer: { type: string }
custom_join_tool: null           # planner style only (mutually exclusive w/ structured_output)
context_access_enabled: true
memory_enabled: true             # retain context/history across sessions
                                 # See examples/agent_builder/agentic_memory/ for a working example
is_schedulable: null             # 2.11+ — true enables recurring runs
                                 # ⚠ Must be enabled at tenant level first; YAML alone silently resets (live-verified 2.12.0)
                                 # Once enabled, internal scheduling tools are visible/deletable via ADK CLI (known issue)
restrictions: null               # 2.11+ — access restrictions
compaction_settings:             # 2.11+ — prevents context overflow in long chats
  context_compaction_enabled: true
  context_compaction_threshold: 20000
  compaction_sliding_window: 10
  large_message_threshold: 50000
  large_message_chunk_size: 30000
  large_message_target_summary: 10000
  large_message_detect_structured: true
chat_with_docs:                  # let end users upload docs in-chat (RAG over user-uploaded files)
  enabled: true
  supports_full_document: true
  # ⚠ RUNTIME (live-verified 2.12.0 SaaS): chat_with_docs ingestion is wired for the chat UI /
  # embedded web-chat upload widget. Driving it through /v1/orchestrate/runs API did NOT make
  # the agent read the uploaded file. For PROGRAMMATIC document RAG, use `knowledge_base:` instead.
  # Also: RunClient.upload_file_to_s3 has a SaaS bug — must POST to /v1/orchestrate/upload-to-s3
  # (no trailing slash), not /v1/upload-to-s3/.
starter_prompts:
  prompts:
    - id: default0
      title: Short action title
      subtitle: optional
      prompt: Example clickable prompt
      state: active
welcome_content:
  welcome_message: Welcome to My Agent
  description: One line on what it helps with
```

**Validation rules**
- `kind` must equal `native` (else `BadRequest`).
- An agent cannot list itself as a collaborator (circular reference rejected).
- `planner` style: at most one of `custom_join_tool` / `structured_output`.
- `experimental_customer_care` style: requires `groq/openai/gpt-oss-120b`; does NOT support `tools`, `knowledge_base`, `collaborators`, `guidelines`, `chat_with_docs.enabled`.
- `toolkits` rejected for non-customer-care styles (except the `scheduling_tools` schedulable-agent exception).

### External agent (`kind: external`)
A2A / external chat. Key fields: `api_url` (required), `auth_scheme` (`BEARER_TOKEN | API_KEY | NONE`),
`auth_config`, `provider` (`external_chat`, `external_chat/A2A/0.2.1`, `external_chat/A2A/0.3.0`,
`salesforce`, …), `nickname`, `app_id`/`connection_id`, `chat_params`.
Import: `orchestrate agents import -f … --app-id <conn>`.

### Assistant agent (`kind: assistant`)
Wraps a watsonx Assistant. `config` carries `assistant_id`, `crn`, `service_instance_url`,
`environment_id`, `auth_type` (`MCSP | IBM_CLOUD_IAM | ICP_IAM | BEARER_TOKEN`), `api_key`,
`authorization_url`, `connection_id`; plus top-level `nickname`, `app_id`.

### Python API (alternative to YAML)
```python
from ibm_watsonx_orchestrate.agent_builder.agents import Agent
agent = Agent(name="my_agent", description="...", instructions="...",
              llm="watsonx/meta-llama/llama-3-3-70b-instruct", tools=[get_weather])
agent.dump_spec("agents/my_agent.yaml")   # serialize for CLI import
```

---

## 2. Python Tools — `@tool` decorator (full reference)

```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
```

Full decorator signature:
```python
@tool(
    name=...,                                # defaults to function name
    description=...,                         # defaults to docstring summary (used for routing)
    permission=ToolPermission.READ_ONLY,     # READ_ONLY | WRITE_ONLY | READ_WRITE | ADMIN
    expected_credentials=[...],              # list[ExpectedCredentials]
    display_name=...,
    input_schema=..., output_schema=...,     # ToolRequestBody/ResponseBody (advanced)
    enable_dynamic_input_schema=False,
    enable_dynamic_output_schema=False,
    response_format=...,                     # 'content' | 'content_and_artifact'
)
```

### Docstring format (strict — parser fails on deviations)

```python
@tool(permission=ToolPermission.READ_WRITE)
def process_request(request_id: str, user_email: str, priority: str = "normal") -> dict:
    """
    Process a service request and create a ticket.

    Args:
        request_id (str): Unique identifier for the request.
        user_email (str): Email of the requesting user.
        priority (str): Priority level (default: normal).
    Returns:
        dict: Result dict with status and message.
    """
    ...
```

Rules:
- Summary line, then `Args:`, then `Returns:` — **no blank line between `Args:` and `Returns:`**.
- Every param and return value: type hint matching docstring type.
- Missing type hints → parser warns and defaults to `str`.

### Credentials at runtime (never as function parameters)

```python
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials
from ibm_watsonx_orchestrate.run import connections

APP_ID = "my_api"

@tool(permission=ToolPermission.READ_ONLY,
      expected_credentials=[ExpectedCredentials(app_id=APP_ID, type=ConnectionType.API_KEY_AUTH)])
def call_api(query: str) -> dict:
    """Call the external API.

    Args:
        query (str): Search text.
    Returns:
        dict: API response payload.
    """
    conn = connections.api_key_auth(APP_ID)
    headers = {"Authorization": f"Bearer {conn.api_key}"}
    # ... request logic
```

**Runtime connection accessors:**
- `connections.api_key_auth(app_id).api_key`
- `connections.basic(app_id).username` / `.password`
- `connections.bearer_token(app_id).token`
- `connections.oauth2_auth_code(app_id).access_token`

**ConnectionType values:** `API_KEY_AUTH`, `BASIC_AUTH`, `BEARER_TOKEN`, `OAUTH2_AUTH_CODE`,
`OAUTH2_PASSWORD`, `OAUTH2_CLIENT_CREDS`, `KEY_VALUE`.

### Self-containment rule
Only stdlib, common third-party (`requests`, `pydantic`, …), and `ibm_watsonx_orchestrate` imports.
**No** `from .x import y` or `from tools.shared import z`. Define every helper/Pydantic model in the same file.

### Pydantic schemas
Define as explicit classes — never `type('X', (BaseModel,), {...})` (causes "non-annotated attribute" errors):
```python
from pydantic import BaseModel, Field
class Result(BaseModel):
    status: str = Field(description="Outcome status")
    message: str = Field(description="Human-readable message")
```

---

## 3. Flows — `@flow` decorator and node API

### Canonical flow template

```python
from pydantic import BaseModel
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END

class MyInput(BaseModel):
    city: str

@flow(name="weather_flow", display_name="Weather Flow",
      description="Fetch then format weather", input_schema=MyInput)
def build_weather_flow(aflow: Flow) -> Flow:      # signature is mandatory
    fetch = aflow.tool(get_weather)
    summarize = aflow.prompt(
        name="summarize",
        system_prompt="You format weather data for users.",   # REQUIRED
        user_prompt=["Summarize: {weather}"],
        llm="groq/openai/gpt-oss-120b",
    )
    aflow.sequence(START, fetch, summarize, END)
    return aflow
```

### Node builders

| Builder | Purpose |
|---|---|
| `aflow.tool(fn)` or `aflow.tool("tool_name")` | `@tool` function or reference by name string |
| `aflow.prompt(name, system_prompt, user_prompt, llm, ...)` | LLM prompt node — `system_prompt` REQUIRED |
| `aflow.script(name, script, output_schema)` | Inline Python code block |
| `aflow.userflow(name, display_name)` | User interaction subflow |
| `aflow.agent(name, agent, message, input_schema, output_schema)` | Call another agent as a node |
| `aflow.docproc(name, task, ...)` | Legacy KVP document extraction |
| `aflow.docext(name, fields, llm, ...)` | Structured document extraction — returns `(node, OutputSchema)` |
| `aflow.docclassifier(name, classes, llm, ...)` | Document classification |
| `aflow.foreach(item_schema, output_schema)` | Loop over a list |
| `aflow.parallel_conditions(name)` | Concurrent matching branches |
| `aflow.parallel(name)` | Unconditional parallel branches |
| `aflow.conditions(name)` | First-match conditional branch |
| `aflow.branch(evaluator=...)` | Value-switch branch (`.case(val, node).default(node)`) |
| `aflow.decisions(name, rules, default_actions)` | Compact rule→action table |
| `aflow.if_else(...)` | Simple boolean branch |
| `aflow.timer(name, delay)` | Wait `delay` seconds |

### Wiring and data mapping

```python
aflow.sequence(START, n1, n2, END)              # chain nodes
aflow.edge(a, b)                                # individual edge
aflow.edge(a, b).edge(b, c)                     # fluent chaining

# Map input to a node parameter (expressions must start with `flow.`)
node.map_input("param", "flow.input.field")
node.map_input("param", "flow.input.field", default_value="fallback")

# Map output to a named flow output variable
aflow.map_output("result", "flow.<node_name>.output")
aflow.map_output("msg", "flow.get_hello_message.output")   # scalar output
```

`map_input`/`map_output` expressions are **single-line Python** — list comprehensions and inline
logic only. No defining or calling functions; flow-file functions are not available at runtime.

### Script node — `aflow.script(...)`

Access and mutate state inside script nodes:
```python
# Read flow input / prior node output
script = "flow.private.greeting = 'Hello ' + flow.input.name"

# Write to this node's output (for downstream `map_input`)
script = "self.output.message = flow.private.greeting"

# Built-in system API (available in scripts only)
# search by email → returns list of WXOUser objects
script = "flow.private.user = system.user.search_by_email('user@example.com')[0]"
```

`output_schema` on the node makes `self.output.*` typed:
```python
class Greeting(BaseModel):
    message: str

node = aflow.script(name="greet", script="self.output.message = 'Hi'", output_schema=Greeting)
```

### Private schema (flow-internal state)

Flows can carry internal state that is never exposed to callers using `private_schema`:
```python
class PrivateData(BaseModel):
    user_id: str = Field(description="Internal user ID")
    # nested objects work too
    credentials: Credentials = Field(description="Creds")

@flow(name="my_flow", input_schema=FlowInput, output_schema=FlowOut, private_schema=PrivateData)
def build_my_flow(aflow: Flow) -> Flow:
    init = aflow.script(name="init", script="""
flow.private.user_id = f"USR-{hash(flow.input.username) % 10000}"
""")
    ...
```
Access private state in scripts as `flow.private.<field>`. Not accessible via `map_input`/`map_output`.

### Parallel branches

Two variants:

**Conditional parallel** — branches run only when their expression matches; create branch nodes *on* the parallel object:
```python
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END

p = aflow.parallel_conditions(name="phase1", display_name="Phase 1")
design = p.script(name="design_work", script="flow.private.phases_completed.append('Design')")
arch   = p.script(name="arch_work",   script="flow.private.phases_completed.append('Arch')")
skip   = p.script(name="skip",        script="print('nothing to do')")

p.condition(expression="flow.private.design_needed is True", to_node=design)
p.condition(expression="flow.private.arch_needed is True",   to_node=arch)
p.condition(default=True,                                    to_node=skip)

p.sequence(design, END)
p.sequence(arch,   END)
p.sequence(skip,   END)

aflow.edge(START, p)
aflow.edge(p, next_node)
```

**Unconditional parallel** — all branches always run:
```python
p2 = aflow.parallel(evaluator=None, name="phase2", display_name="Phase 2")
sq1 = p2.script(name="squad1", script="print('squad 1 done')")
sq2 = p2.script(name="squad2", script="print('squad 2 done')")
p2.sequence(START, sq1, END)
p2.sequence(START, sq2, END)
aflow.edge(prev, p2)
aflow.edge(p2, next_node)
```

⚠ Parallel branches **pause on user interaction** — do not use with user-activity nodes inside a parallel.

Source: [`examples/flow_builder/parallel_flow/tools/parallel_flow.py`](../../examples/flow_builder/parallel_flow/tools/parallel_flow.py)

### Decision branch
```python
b = aflow.conditions(name="route")
b.condition(expression="flow.input.severity == 'high'", to_node=urgent_node)
b.condition(default=True, to_node=routine_node)
```

### Callbacks
```python
from ibm_watsonx_orchestrate.flow_builder.flow_callback_types import FlowCallbackEventKind

aflow.add_callback(
    tool="flow_callback_handler",          # name of an imported @tool
    events=[
        FlowCallbackEventKind.ON_FLOW_START,
        FlowCallbackEventKind.ON_FLOW_END,
        FlowCallbackEventKind.ON_FLOW_ERROR,
        # also: ON_TASK_WAIT, ON_TASK_ERROR, ON_TASK_MESSAGE
    ]
    # batch_interval omitted → server default; set e.g. batch_interval=30000 for 30 s
)
```
Use `"toolkit_name:tool_name"` format to reference a toolkit tool as the callback handler.

Source: [`examples/flow_builder/flow_callback/tools/example_flow_with_callbacks.py`](../../examples/flow_builder/flow_callback/tools/example_flow_with_callbacks.py)

### Data masking
```python
from ibm_watsonx_orchestrate.flow_builder.masking_utils import InputPolicy, MaskingPolicy

# Mask an input field completely
aflow.mask_property("flow.input.ssn", masking_policy=MaskingPolicy.MASK_ALL)

# Mask first 4 chars of a nested private field
aflow.mask_property("flow.private.credentials.auth_token", masking_policy=MaskingPolicy.MASK_FIRST4)

# Mask a script node output field
aflow.mask_property(f"flow.{script_node.spec.name}.output.masked_ssn",
                    masking_policy=MaskingPolicy.MASK_FIRST4)

# Mask a tool output field
aflow.mask_property(f"flow.{tool_node.spec.name}.output.api_token",
                    masking_policy=MaskingPolicy.MASK_LAST4)

# Mask a user-flow field with live typing masking
aflow.mask_property("flow.userflow_1.passport.output",
                    masking_policy=MaskingPolicy.MASK_ALL,
                    input_policy=InputPolicy.MASK_WHILE_TYPING)
```
Policies: `MASK_ALL`, `MASK_FIRST4`, `MASK_LAST4`, `MASK_VIA_REGEX` (pass `regex_config=`).
Masking applies in the chat UI, flow inspector, and observability traces.

Source: [`examples/flow_builder/masking_test_flow/tools/masking_test_flow.py`](../../examples/flow_builder/masking_test_flow/tools/masking_test_flow.py)

### Dynamic forms (`userflow().form()`)
Forms support conditional labels, visibility, and dynamically populated choices via `RuleBuilder`:
```python
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END
from ibm_watsonx_orchestrate.flow_builder.utils import RuleBuilder
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap, Assignment

uf = aflow.userflow()
form = uf.form(name="my_form", display_name="My Form", cancel_button_label="Cancel")

# Single-choice with dynamic choices from flow input
choices = DataMap()
choices.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.countries"))
form.single_choice_input_field(name="country", label="Country", choices=choices, show_as_dropdown=True)

# Change label based on another field's value
form.label_behaviour_field(
    name="label_rule", on_change_to_field="country",
    rules=[RuleBuilder.label_rule(
        field_name="country", field_value="USA",
        impacted_field="code", label_when_true="Zip code", label_when_false="Postal code",
        operator="equals")])

# Show/hide a field based on another field's value
form.visibility_behaviour_field(
    name="visibility_rule", on_change_to_field="country",
    rules=[RuleBuilder.visibility_rule(
        field_name="country", field_value="USA",
        impacted_field="city", visible_when_true=True, operator="equals")])

# Populate choices from a tool call when another field changes
form.value_source_behaviour_field(
    name="region_source", on_change_to_field="country", impacted_field="region",
    tool_name="get_states_or_provinces",
    field_mappings={"country": "parent.field.country"})

form.text_input_field(name="city", label="City", required=False)
form.file_upload_field(name="documents", label="Documents")

uf.edge(START, form)
uf.edge(form, END)
aflow.sequence(START, uf, END)
```
Source: [`examples/flow_builder/dynamic_forms/tools/user_activity_with_dynamic_forms_full.py`](../../examples/flow_builder/dynamic_forms/tools/user_activity_with_dynamic_forms_full.py)

### `foreach` — iterate over a list

```python
from ibm_watsonx_orchestrate.flow_builder.types import ForeachPolicy

# Item schema = type of each element; output_schema = aggregated result type
foreach_flow: Flow = aflow.foreach(item_schema=CustomerRecord, output_schema=Invitations) \
    .policy(kind=ForeachPolicy.SEQUENTIAL)   # or ForeachPolicy.PARALLEL

# Build nodes *on* foreach_flow (its own subflow)
send_node = foreach_flow.tool(send_invitation_email)
foreach_flow.sequence(START, send_node, END)

# Wire the foreach into the parent flow
aflow.edge(START, get_list_node)
aflow.edge(get_list_node, foreach_flow)
aflow.edge(foreach_flow, END)
```

Inside `foreach_flow`, the current item is available at `parent._current_item`.
Use `branch(evaluator="parent._current_item.field == value")` for per-item routing:
```python
# Route each tuition request to approval/denial based on grade
grade_branch = foreach_flow.branch(evaluator="parent._current_item.overall_grade.strip().upper()") \
    .case("A", approve_node) \
    .case("B", manager_node) \
    .case("C", deny_node) \
    .default(deny_node)
foreach_flow.edge(START, grade_branch)
```

Source: [`examples/flow_builder/foreach_email`](../../examples/flow_builder/foreach_email/tools/foreach_email.py) · [`examples/flow_builder/get_tuition_reimbursed`](../../examples/flow_builder/get_tuition_reimbursed/tools/get_tuition_reimbursed.py)

### Agent node — `aflow.agent(...)`

Call a named agent as a flow step (structured agent-to-agent orchestration):
```python
class CityInput(BaseModel):
    city: str

class WeatherData(BaseModel):
    temperature: float
    current_weather: str

weather_node = aflow.agent(
    name="ask_weather_agent",
    agent="weather_agent",             # name of an imported agent
    description="Get weather for city",
    message="Give real-time weather data for the provided city",
    input_schema=CityInput,
    output_schema=WeatherData
)
```
Output accessible at `flow.<name>.output.<field>`. Agents run sequentially by default; chain with `aflow.sequence(...)`.

Source: [`examples/flow_builder/collaborator_agents`](../../examples/flow_builder/collaborator_agents/tools/collaborator_agents_flow.py)

### Error branching — `NodeErrorHandlerConfig`

Handle node failures gracefully by branching to an error path instead of failing the flow:
```python
from ibm_watsonx_orchestrate.flow_builder.types import NodeErrorHandlerConfig, UserFieldKind

# Error recovery node (show a message to the user)
error_flow = aflow.userflow()
msg = error_flow.field(direction="output", name="err_msg", display_name="Error",
                       kind=UserFieldKind.Text,
                       text="Sorry, we couldn't fetch data. Please try again.")
error_flow.edge(START, msg); error_flow.edge(msg, END)

# Primary node with error handling
primary_node = aflow.tool(
    "getDogFact",
    error_handler_config=NodeErrorHandlerConfig(
        error_message="Failed to get facts",
        max_retries=0,          # 0 = branch immediately on first error
        retry_interval=1000,    # ms between retries
        on_error="branch",      # enable error branching
        error_edge_id="dog_err" # must match edge id below
    )
)

aflow.sequence(START, primary_node, END)
aflow.edge(primary_node, error_flow, id="dog_err")   # error path
aflow.edge(error_flow, END)
```

Source: [`examples/flow_builder/get_pet_facts_error_branching`](../../examples/flow_builder/get_pet_facts_error_branching/tools/get_pet_facts_error_branching.py)

### Agent swarm / looping flow

Use `conditions()` routing back to earlier nodes to implement iterative multi-agent workflows:
```python
# Each agent writes `next_agent` to private state; router reads it to pick next step
router = flow.conditions()
router.condition(expression="flow.private.final_solution != None and len(flow.private.final_solution) > 0", to_node=done_node) \
      .condition(expression="flow.private.iteration > 10", to_node=done_node) \
      .condition(expression="flow.private.next_agent == 'billing_agent'", to_node=billing_agent) \
      .condition(expression="flow.private.next_agent == 'technical_agent'", to_node=technical_agent) \
      .condition(default=True, to_node=done_node)

# Each agent's update script re-routes through the same router
flow.edge(billing_agent, update_script)
flow.edge(update_script, router)   # loop back
```

Pattern: init → router → agent → update_state_script → router → … → done.
Cap iterations with a counter in `private` to avoid infinite loops.

Source: [`examples/flow_builder/triage_workflow_agent_swarm`](../../examples/flow_builder/triage_workflow_agent_swarm/tools/triage_issue_flow.py)

### `@flow` decorator — additional parameters

```python
@flow(
    name="my_flow",
    display_name="My Flow",
    description="What the flow does",
    input_schema=MyInput,
    output_schema=MyOutput,
    private_schema=MyPrivate,
    suppress_agent_summarization=True,  # suppress LLM summary between nodes (useful for simple flows)
)
def build_my_flow(aflow: Flow) -> Flow:
    ...
    aflow.target_locales(["fr", "es", "de"])   # enable multi-language UI
    return aflow
```

### Other flow-builder features
- **Timer** — `aflow.timer(name=, delay=<seconds:int>)`

⚠ **Not implemented in 2.12** (raise `ValueError` at build): `aflow.wait_for(...)`;
`branch(evaluator=<function>)` as a callable (string evaluators work fine); Branch `MatchPolicy.ANY_MATCH`. Avoid these.

---

## 4. Document Processing (docproc) — KVP extraction

Use `DocProcKVPSchema` + `DocProcField` (not plain dicts):

```python
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocProcInput, DocProcKVPSchema, DocProcField, DocProcOutputFormat)

INVOICE_SCHEMA = DocProcKVPSchema(
    document_type="Invoice",
    document_description="A business invoice",
    additional_prompt_instructions="Extract values exactly as shown.",
    fields={
        "invoice_number": DocProcField(description="Invoice identifier", default="", example="INV-001"),
        "vendor_name":    DocProcField(description="Issuing vendor name", default="", example="ABC Inc."),
        "total_amount":   DocProcField(description="Total amount due",   default="", example="$1,234.00"),
    }
)

@flow(name="doc_flow", input_schema=DocProcInput)
def build_doc_flow(aflow: Flow) -> Flow:
    node = aflow.docproc(
        name="extract",
        task="text_extraction",
        output_format=DocProcOutputFormat.object,   # returns JSON object instead of file ref
        kvp_schemas=[INVOICE_SCHEMA],
        kvp_force_schema_name="Invoice"
    )
    node.map_input("document_ref", "flow.input.document_ref")
    aflow.sequence(START, node, END)
    return aflow
```

**KVP output structure** (when `output_format=object`):
```json
{ "key": { "semantic_label": "vendor_name" }, "value": { "raw_text": "ABC Inc." } }
```
`kvps` is a list of these objects.

**Two approaches to use KVP data:**

1. **Recommended — pass the full `kvps` array to a prompt node** (let the LLM format it):
```python
summary = aflow.prompt(
    name="format",
    system_prompt="Format the extracted invoice data for the user.",
    user_prompt=["Data: {kvps}"],
    output_schema=SummaryOutput
)
summary.map_input("kvps", "flow.extract.output.kvps")
```

2. **Inline extraction — single-line list comprehension only** (no function calls):
```python
aflow.map_output(
    "vendor_name",
    "[kvp['value']['raw_text'] for kvp in flow['extract'].output.kvps "
    "if kvp.get('key',{}).get('semantic_label') == 'vendor_name'][0]"
    " if [k for k in flow['extract'].output.kvps "
    "if k.get('key',{}).get('semantic_label')=='vendor_name'] else ''"
)
```

**Docproc notes (2.12):**
- Default extractor model is now `mistral-small` (changed in 2.12).
- Page-range extraction is supported (restrict to specific pages).
- Use structured/vision extractor for forms and tables; unstructured/text for text-heavy docs.

**Document upload rule:**
Agents **cannot** pass user-uploaded files to a flow. The `docproc` node prompts the user for the upload itself.
✅ Agent instructions: "When the user wants to process a document, immediately invoke `doc_flow`."
❌ NOT: "Ask the user to upload a document first, then pass it to the flow."

---

## 5. Document Extraction — `aflow.docext(...)` and `aflow.docclassifier(...)`

These are the **preferred** document AI nodes (post-2.12). Use `docext`/`docclassifier` instead of `docproc` for new flows.

All document AI flows use `DocumentProcessingCommonInput` as input schema:
```python
from ibm_watsonx_orchestrate.flow_builder.types import DocumentProcessingCommonInput
# DocumentProcessingCommonInput handles the file upload prompt automatically
```

### `aflow.docext(...)` — structured field extraction

Returns a tuple `(node, OutputSchema)`. Use `OutputSchema` as `input_schema` for downstream nodes.

```python
from ibm_watsonx_orchestrate.flow_builder.types import (
    DocExtConfigField, DocExtConfigTableField, DocumentProcessingCommonInput, PageRange)
from pydantic import BaseModel, Field

class ContractFields(BaseModel):
    buyer: DocExtConfigField = Field(default=DocExtConfigField(
        name="Buyer", field_name="buyer"))
    seller: DocExtConfigField = Field(default=DocExtConfigField(
        name="Seller", field_name="seller"))
    agreement_date: DocExtConfigField = Field(default=DocExtConfigField(
        name="Agreement Date", field_name="agreement_date", type="date"))
    # Table field — extracts a list of rows
    line_items: DocExtConfigTableField = Field(default=DocExtConfigTableField(
        name="Line Items", field_name="line_items",
        fields=[
            DocExtConfigField(name="Item", field_name="item", type="string"),
            DocExtConfigField(name="Qty",  field_name="quantity", type="number"),
            DocExtConfigField(name="Price",field_name="unit_price", type="number"),
        ]))

@flow(name="extract_contract", input_schema=DocumentProcessingCommonInput)
def build_extract_contract(aflow: Flow) -> Flow:
    node, _Schema = aflow.docext(
        name="contract_extractor",
        display_name="Extract Contract Fields",
        description="Extracts buyer, seller, date, and line items from a contract",
        llm="watsonx/mistralai/mistral-small-3-1-24b-instruct-2503",
        fields=ContractFields(),
        field_extraction_method="layout",   # "layout" required for tables, available_options, page_range
        enable_hw=True,                     # handwriting support
        page_range=PageRange(start=1, end=3)  # optional: restrict to specific pages
    )
    aflow.sequence(START, node, END)
    return aflow
```

**`DocExtConfigField` parameters:**
- `name` — display name
- `field_name` — key in extracted output
- `type` — `"string"` (default) | `"date"` | `"number"`
- `description` — hint for the LLM extractor
- `example_value` — example to anchor extraction
- `available_options` — constrain output to a list of valid values (reduces hallucination; requires `field_extraction_method="layout"`)

**`DocExtConfigTableField` parameters:** `name`, `field_name`, `description`, `fields` (list of `DocExtConfigField`).

### `aflow.docclassifier(...)` — document classification

```python
from ibm_watsonx_orchestrate.flow_builder.types import DocClassifierClass, DocumentProcessingCommonInput

class DocClasses(BaseModel):
    invoice: DocClassifierClass = Field(default=DocClassifierClass(class_name="invoice"))
    contract: DocClassifierClass = Field(default=DocClassifierClass(class_name="contract"))
    tax_form: DocClassifierClass = Field(default=DocClassifierClass(class_name="tax_form"))

@flow(name="classify_doc", input_schema=DocumentProcessingCommonInput)
def build_classify_doc(aflow: Flow) -> Flow:
    node = aflow.docclassifier(
        name="doc_classifier",
        display_name="Classify Document",
        description="Classifies the uploaded document",
        llm="watsonx/meta-llama/llama-4-maverick-17b-128e-instruct-fp8",
        classes=DocClasses()
    )
    aflow.sequence(START, node, END)
    return aflow
```

Output: `flow.doc_classifier.output.class_name` — the matched class name string.

### Combining classifier + extractor (branching on class)

```python
from ibm_watsonx_orchestrate.flow_builder.flows import Branch

classifier_node = build_docclassifier_node(aflow)
extractor_node, _ = build_docext_node(aflow)
legacy_proc_node = build_docproc_node(aflow)

router: Branch = aflow.conditions()
router.condition(expression="flow.doc_classifier.output.class_name.strip().lower() in ['invoice','bill_of_lading']",
                 to_node=legacy_proc_node) \
      .condition(expression="flow.doc_classifier.output.class_name.strip().lower() in ['contract','purchase_order']",
                 to_node=extractor_node) \
      .condition(default=True, to_node=extractor_node)

aflow.sequence(START, classifier_node, router)
aflow.edge(extractor_node, END)
aflow.edge(legacy_proc_node, END)
```

Source: [`examples/flow_builder/document_extractor`](../../examples/flow_builder/document_extractor/tools/document_extractor_flow.py) · [`examples/flow_builder/document_classifier`](../../examples/flow_builder/document_classifier/tools/document_classifier_flow.py) · [`examples/flow_builder/document_processing`](../../examples/flow_builder/document_processing/tools/document_processing_flow.py)

---

## 6. `userflow` — full field API

`aflow.userflow()` creates an interactive subflow where users fill forms, upload files, or review information.

### Raw fields (`userflow.field(...)`)

```python
from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind, Assignment
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap

uf = aflow.userflow(display_name="My Task")

# Text input from user
t_in = uf.field(direction="input", name="last_name", display_name="Last Name",
                kind=UserFieldKind.Text, text="Enter your last name")

# Text display to user (supports {flow.input.field} substitution)
t_out = uf.field(direction="output", name="greeting", display_name="Welcome",
                 kind=UserFieldKind.Text, text="Hello {flow.input.first_name}")

# Number input
n_in = uf.field(direction="input", name="age", display_name="Age",
                kind=UserFieldKind.Number, text="Enter your age")

# File upload
f_up = uf.field(direction="input", name="doc", display_name="Upload Document",
                kind=UserFieldKind.File)

# File download (pass value via DataMap)
dm = DataMap()
dm.add(Assignment(target_variable="self.input.value",
                  value_expression='flow["userflow_1"]["Upload Document"].output.value'))
f_dn = uf.field(direction="output", name="result", display_name="Download Result",
                kind=UserFieldKind.File, input_map=dm)

# List display
ldm = DataMap()
ldm.add(Assignment(target_variable="self.input.value", value_expression="flow.input.items"))
lst = uf.field(direction="output", name="items", display_name="Items",
               kind=UserFieldKind.List, input_map=ldm)

uf.sequence(START, t_in, t_out, n_in, f_up, f_dn, lst, END)
aflow.sequence(START, uf, END)
```

### Form fields (`userflow.form(...)`)

Forms group multiple fields with submit/cancel buttons:
```python
form = uf.form(name="AppForm", display_name="Application", cancel_button_label="Cancel")

# Text input
form.text_input_field(name="name", label="Full Name", required=True,
                      placeholder_text="Enter name", help_text="Legal name",
                      regex="^[a-zA-Z ]+$", regex_error_message="Letters only")

# Number input (with default from flow input)
dm = DataMap()
dm.add(Assignment(target_variable="self.input.default", value_expression="flow.input.salary"))
form.number_input_field(name="salary", label="Salary", is_integer=False, default=dm)

# Boolean (checkbox)
form.boolean_input_field(name="fulltime", label="Full Time", single_checkbox=True,
                         true_label="Yes", false_label="No")

# Single-choice dropdown
choices_dm = DataMap()
choices_dm.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.titles"))
form.single_choice_input_field(name="title", label="Title", choices=choices_dm, show_as_dropdown=True)

# Multi-choice (table or dropdown)
form.multi_choice_input_field(name="skills", label="Skills", choices=choices_dm,
                               show_as_dropdown=False, minItems=1, maxItems=5)

# Date / Time / DateTime input
form.date_input_field(name="start", label="Start Date", required=True)
form.datetime_input_field(name="start_time", label="Start Time", inputType=UserFieldKind.Time)
form.datetime_input_field(name="meeting", label="Meeting", inputType=UserFieldKind.DateTime)

# Date range
form.date_range_input_field(name="period", label="Period", start_date_label="From", end_date_label="To")

# User picker (select wxO users)
form.user_input_field(name="approvers", label="Approvers", required=True, multiple_users=True)

# File upload with limits
form.file_upload_field(name="docs", label="Documents", allow_multiple_files=True, file_max_size=256)

# Read-only field output (display a computed value)
val_dm = DataMap()
val_dm.add(Assignment(target_variable="self.input.value", value_expression="flow.input.computed"))
form.field_output_field(name="computed", label="Computed Value", value=val_dm)

# List output (read-only table)
form.list_output_field(name="friends", label="Friends", choices=choices_dm,
                        columns={"first_name": "First", "last_name": "Last"})

# Success message
form.message_output_field(name="ok", label="Status", message="Submitted successfully.")
```

### Custom buttons and edges

```python
# Add extra buttons
save_btn = uf.add_button("Save Draft")
review_btn = uf.add_button("Submit for Review")

# Process nodes for each button
submit_node = uf.script(name="on_submit", script='print("submitted")')
draft_node  = uf.script(name="on_draft",  script='print("draft saved")')

uf.edge(START, form)
uf.edge(form, submit_node, button_label="Submit")   # default submit button
uf.edge(submit_node, END)
uf.edge(save_btn, draft_node)   # custom button
uf.edge(draft_node, END)
```

### Task assignment — route to a different user

```python
from ibm_watsonx_orchestrate.flow_builder.types import UserAssignmentPolicy
from ibm_watsonx_orchestrate.flow_builder.flows.flow import UserFlow

init = aflow.script(name="init",
    script="flow.private.assignee = system.user.search_by_email('manager@corp.com')[0]")

uf: UserFlow = aflow.userflow()
uf.assign_to(policy=UserAssignmentPolicy.USER, assignees='flow.private.designated')
# or: uf.assign_to(policy=UserAssignmentPolicy.FLOW_INITIATOR)
```

Source: [`examples/flow_builder/user_activity`](../../examples/flow_builder/user_activity/tools/user_flow.py) · [`examples/flow_builder/user_activity_with_forms`](../../examples/flow_builder/user_activity_with_forms/tools/user_flow_forms.py) · [`examples/flow_builder/user_activity_user_assignment`](../../examples/flow_builder/user_activity_user_assignment/tools/user_flow.py)

---

## 7. Custom RAG tool pattern (for unsupported vector stores)

For Pinecone, Weaviate, Qdrant, Chroma, proprietary search, etc. — don't use a knowledge base; write a Python `@tool`:

```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import requests

class SearchQuery(BaseModel):
    query: str = Field(..., description="The search query")
    top_k: int = Field(default=5, description="Number of results to return")

class SearchResult(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="List of matching documents")

@tool(permission=ToolPermission.READ_ONLY)
def search_knowledge(query: SearchQuery) -> SearchResult:
    """Search the custom vector database.

    Args:
        query (SearchQuery): Search query and parameters.
    Returns:
        SearchResult: Matching documents from the vector store.
    """
    response = requests.post("https://my-db.com/search",
                             json={"query": query.query, "limit": query.top_k})
    matches = response.json().get("matches", [])
    return SearchResult(results=[
        {"title": m.get("metadata", {}).get("title", ""),
         "content": m.get("text", ""),
         "score": m.get("score", 0.0)} for m in matches
    ])
```

Attach to agent: `tools: [search_knowledge]`. Instruct the agent to cite sources.
