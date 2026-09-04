# Testing, Debugging & Observability

## Contents
- [§1 Fast iteration loop](#1-fast-iteration-loop)
- [§2 Post-deploy verification gate](#2-post-deploy-verification-gate)
- [§3 Failure-mode table](#3-failure-mode-table)
- [§4 Programmatic flow testing](#4-programmatic-flow-testing)
- [§5 Observability & traces](#5-observability--traces)
- [§6 Pre-publish checklist](#6-pre-publish-checklist)

---

## 1. Fast iteration loop

```bash
source venv/bin/activate
./import-all.sh              # re-import overwrites by name
orchestrate agents list -v   # confirm presence + wiring
orchestrate chat start       # interactive test in the local UI
```

Scriptable single-turn test:
```bash
orchestrate chat ask -n <agent> "<prompt>" -r   # -r reasoning · -l logs · -t <thread_id>
```
> ⚠ On IBM Cloud SaaS, `chat ask` can hang in scripted use.
> Use `watsonx-orchestrate-adk:chat_with_agent` (MCP) or the runtime REST API instead.

**Snapshot a known-good definition to Git:**
```bash
# Agent → YAML (reimports directly)
orchestrate agents export -n <agent> --kind native -o agents/<agent>.yaml --agent-only

# Tool → ZIP (NOT YAML). Use underscore-only base name — dots rejected on reimport.
orchestrate tools export -n <tool> -o tools/<tool>_export.zip
# To reimport: unzip first, then: orchestrate tools import -k python -f /tmp/x/<tool>.py
```

---

## 2. Post-deploy verification gate

**Deployed ≠ verified.** Never report an agent as "done" until tested — or the human
explicitly declines.

After `./import-all.sh`, ask:
> "`<agent>` is deployed to `<env>`. Want me to smoke-test it before handover?
> I'll run 1 single-turn + 1 multi-turn test — read-only prompts." — Yes / No

If **No**: report "deployed; not tested at your request" and stop. If **Yes**:

**Step 1 — derive tests from the agent spec:**
- `starter_prompts` → ready-made prompts (best source for Turn 1)
- `description`/`instructions` → intended job and which tool should fire
- `tools` → note any `READ_WRITE` tools (avoid triggering writes)

**Step 2 — run tests:**

**Preferred — use `watsonx-orchestrate-adk:chat_with_agent` (MCP):**
```
Turn 1: chat_with_agent(agent_name=<agent>, message=<prompt>, include_reasoning=True)
        → save thread_id from response
Turn 2: chat_with_agent(agent_name=<agent>, message=<follow-up>, thread_id=<from Turn 1>, include_reasoning=True)
```
The follow-up must require context from Turn 1 — do NOT restate the entity.

**Fallback — CLI (if MCP not available):**
```bash
orchestrate chat ask -n <agent> "<prompt>" -r          # Turn 1 → note thread_id
orchestrate chat ask -n <agent> "<follow-up>" -t <thread_id> -r   # Turn 2
```
> ⚠ `chat ask` can hang on IBM Cloud SaaS — use the runtime REST API (`references/runtime-api.md §3`) if so.

**Step 3 — pass criteria (assert on behavior, not exact text):**
- No error · coherent on-topic answer
- Expected tool was invoked (visible in `-r` reasoning)
- Turn 2 uses context from Turn 1

**Step 4 — emit `TEST_REPORT.md`:**
```markdown
# Agent Verification — <agent> (<name>)
Env: <env>   LLM: <model>   Tools: <list>   Write-capable exercised? yes/no

## Test 1 — single-turn
Prompt:   "<prompt>"
Result:   PASS | FAIL
Evidence: <excerpt> · tool `<tool>` called: yes/no

## Test 2 — multi-turn
Turn 1:   "<prompt>" → <excerpt>
Turn 2:   "<follow-up>" → <excerpt>   context retained: yes/no
Result:   PASS | FAIL

## Verdict: 2/2 passed — handover-ready   (or: N/2 — <issue>)
```

Report honestly: "deployed and tested (2/2)", "deployed; test N failed — …", or
"deployed; not tested at your request."

**Step 5 — fix → re-deploy → re-test loop:**

If any test fails, do not stop. Follow this loop until all tests pass:
1. Identify root cause from `reasoning` / `include_reasoning` output
2. Fix the code (`.py`) or agent YAML (`.yaml`)
3. Re-import: `./import-all.sh` (or the specific `orchestrate tools/agents import` command)
4. Re-run the failing test(s) using `watsonx-orchestrate-adk:chat_with_agent`
5. Repeat until all pass — then emit the final `TEST_REPORT.md`

Only declare "done" when all tests pass — or the human explicitly asks you to stop.

---

## 3. Failure-mode table

| Symptom | Cause → Fix |
|---------|-------------|
| `agents import` required field error | Missing `spec_version`/`kind`/`name`/`description`, or a dependency not imported yet. |
| "cannot be used to create a native agent" | `kind` mismatch — set `kind: native`. |
| Agent ignores a tool | Weak docstring or tool not mentioned in `instructions`. Improve docstring; name the tool explicitly. |
| Agent responds plausibly but never calls the flow/tool | Agent `tools:` list is empty (`tools: []`) — it has nothing to call. Check the live spec with `orchestrate agents list -v` and verify `tools` is populated. |
| Docstring/type-hint warnings on import | **Often false positive** — fires on every Python tool; descriptions still parse. Real causes: blank line between `Args:` and `Returns:`, or missing type hints. |
| "name cannot contain spaces" | Use snake_case for tool/toolkit/agent `name`. |
| `ModuleNotFoundError` at tool runtime | Add dep to `requirements.txt`; re-import with `-r`. Never add `ibm-watsonx-orchestrate`. |
| Cross-file import error | Tool files must be self-contained — no `from .utils import x`. |
| 401/403 on a tool call | Connection not configured or wrong `app_id`. `orchestrate connections list` → re-run `set-credentials`. |
| Model not found / no default | `orchestrate models list`; set `llm:` to a listed id or run `orchestrate models config default`. |
| Flow won't compile | Signature must be `def build_<name>(aflow: Flow) -> Flow:`; `prompt` nodes need `system_prompt`; `map_*` expressions single-line. |
| Doc flow can't get uploaded file | Don't ask the agent to upload — the `docproc`/`docext` node prompts the user. Agent just invokes the flow. |
| Agent returns hallucinated content instead of flow output | Agent `instructions` say to "reformat" or "summarise" output — agent ignores the flow result and generates its own. Fix: move formatting into the flow's final `prompt` node; instruct the agent to present the result as-is. Use `suppress_agent_summarization=True` on the `@flow` decorator. |
| Final agent node produces fallback/generic response ("no actionable information") | The agent node has no `map_input` — it received an empty prompt. Script nodes (and earlier nodes) do NOT auto-pass-through to a following agent node. Fix: add `agent_node.map_input("field", "flow.<script_node_name>.output.<field>")` explicitly. |
| Coordinator LLM ignores "copy verbatim" / "preserve markdown" instructions | All `react_intrinsic`/`react_core` agents rewrite tool output — this cannot be suppressed at the coordinator level. Fix: give the coordinator a concrete markdown template in `instructions` and tell it to fill in named fields from the tool output. See `agents-tools-schemas.md §` Coordinator agent. |
| `docproc`/`docext`/`docclassifier` node fails at runtime (Developer Edition) | WDU service not started — restart server with `-d`: `orchestrate server start -d -e .env --accept-terms-and-conditions` |
| Works locally, absent in prod | Wrong active env. `orchestrate env list` → activate → re-import. |
| `No agents with the name 'X'` | Used display name. Get snake_case `name` from `orchestrate agents list -v`. |
| Need reasoning trace | `orchestrate chat ask -n <agent> "…" -r` (`-r` = reasoning, `-l` = logs). |
| Server issues | `orchestrate server logs`; `orchestrate server reset` to wipe state. |

---

## 4. Programmatic flow testing

Test the compiled flow spec after importing all Python tools (the flow engine resolves tool names
at runtime against the platform — tools must be imported first via `import-all.sh`).

> ⚠ **`@flow`-decorated functions are compiled singletons.**
> Calling `build_my_flow().compile_deploy()` a second time raises `ValueError: Flow has already been compiled`.
> Compile once in `main()` and pass the `CompiledFlow` instance into each test scenario.

```python
import asyncio
from pathlib import Path
from ibm_watsonx_orchestrate.flow_builder.flows import FlowRun
from tools.weather_flow import build_weather_flow

async def run_flow(fdef, input_data: dict, debug: bool = False):
    """Instantiate a FlowRun and await full completion. Returns output dict."""
    def noop_end(output): pass
    def noop_err(error): pass
    flow_run = FlowRun(
        flow=fdef.flow,
        deployed_flow_id=fdef.flow_id,
        on_flow_end_handler=noop_end,
        on_flow_error_handler=noop_err,
        debug=debug,
    )
    await flow_run._arun(input_data=input_data)
    return flow_run.output

async def main():
    fdef = await build_weather_flow().compile_deploy()
    fdef.dump_spec(f"{Path(__file__).parent}/generated/weather_flow.json")
    output = await run_flow(fdef, {"city": "Paris"}, debug=True)  # debug prints every node I/O
    print("Output:", output)

asyncio.run(main())
```

**Why not `fdef.invoke()` or `fdef.flow_run()`?**
- `fdef.flow_run()` — **does not exist** on `CompiledFlow`; raises `AttributeError`.
- `fdef.invoke()` — is `async` but passes `None` for `on_flow_end_handler`/`on_flow_error_handler`,
  which fails Pydantic validation on `FlowRun` (`Input should be callable`). When handlers are
  provided, `result.output` is `None` because output is delivered asynchronously after `await`
  returns; the handler receives the output **`dict`** directly, not a `FlowRun` object.
- **Correct pattern**: instantiate `FlowRun` directly with `noop` callables → `await flow_run._arun(input_data=...)`.

`debug=True` surfaces each node's input/output — pinpoints bad `map_input`/`map_output` expressions.

---

## 5. Observability & traces

```bash
# Export a specific trace (most reliable — works on SaaS)
orchestrate observability traces export --trace-id <trace_id>

# Rich JSON via AgentOps v3 (observations, latency, scores, cost)
curl -H "Authorization: Bearer $TOKEN" \
  "<instance-url>/v1/agentops-v3/traces/<trace_id>"
```
> ⚠ On IBM Cloud SaaS, `traces search --last 1h` returns 0 results even when traces exist.
> Prefer `export --trace-id`. The `trace_id` is in every
> `/v1/orchestrate/runs` response.

**Local Developer Edition logs:**
```bash
export LIMA_INSTANCE=ibm-watsonx-orchestrate
lima docker logs -f dev-edition-tools-runtime-1
lima docker logs dev-edition-wxo-tempus-runtime-1
```

---

## 6. Pre-publish checklist

- [ ] All tools have `@tool` + valid Google-style docstrings + type hints
- [ ] All flows use `build_<name>(aflow: Flow) -> Flow`, one per file
- [ ] Agent YAML has `spec_version`, `kind: native`, `name`, `description`, `instructions`, `llm`, `style`, `tools`
- [ ] Every referenced tool/KB/collaborator/connection/model is imported first
- [ ] No secrets in YAML or code; credentials set via `connections set-credentials`
- [ ] `starter_prompts` + `welcome_content` set for good UX
- [ ] Post-deploy verification gate (§2) run: 1 single-turn + 1 multi-turn pass, `TEST_REPORT.md` produced — or human explicitly declined
- [ ] Definitions exported to Git; `import-all.sh` reproduces the build cleanly
- [ ] Verified in the **production** env after `env activate`; agent `deploy`-ed
