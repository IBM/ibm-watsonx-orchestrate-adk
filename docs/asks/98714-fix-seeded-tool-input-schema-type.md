# Ask: Fix missing `type` field in seeded `example_document_processing_flow` tool definition

**Issue:** [wo-tracker#98714](https://github.ibm.com/WatsonOrchestrate/wo-tracker/issues/98714)  
**ADK PR:** [bugfix/builtin-tool-list-export-errors](https://github.ibm.com/WatsonOrchestrate/wxo-clients/tree/bugfix/builtin-tool-list-export-errors)  
**Squad:** Doc Processing  
**To:** @Vinaysheel.Wagh, @mahernan  
**Severity:** Sev-2 / regression — affects every new tenant on first `orchestrate tools list` / `orchestrate agents list`

---

## Background

The Document Processing team introduced a seeded OOTB sample agent and flow tool
(`example_document_processing_flow`) that is automatically provisioned into every new tenant
via the `wxo-server-db_schema_job` DB migration image (first shipped in
`sample-doc-proc-agent-phase-2-15455`, ADK commit `893d1dd4c`).

This is a great feature for onboarding. However the tool definition stored by the schema job
has an incomplete `input_schema` — the JSON Schema `type` field is absent:

```json
"input_schema": {
    "properties": {
        "document_path": { "type": "string", "description": "Path or URL to the document to process" },
        "extraction_options": { "type": "object", "description": "Optional extraction configuration" }
    },
    "required": ["document_path"]
}
```

A well-formed JSON Schema object **must** include `"type": "object"` at the root level.
The missing field caused the ADK CLI to raise a Pydantic `ValidationError` for every tenant
on the most basic commands.

---

## Impact

| Command | Symptom on every new tenant |
|---|---|
| `orchestrate tools list` | `[ERROR] - 1 validation error for ToolSpec input_schema.type Field required` |
| `orchestrate agents list` | Same error (resolves tool IDs during listing) |
| `orchestrate tools export -n example_document_processing_flow` | `ClientAPIException(status_code=500)` crash |

Because the tool is seeded at tenant creation, **all new tenants on AWS preprod (post mcsp_v2
migration) hit this immediately** — before creating a single user-authored tool or agent.

---

## Root cause

The schema migration that inserts the tool record omits `"type": "object"` from `input_schema`.
The source is in the `wxo-server` / `wxo-server-db_schema_job` image, in the SQL or seed data
that creates the `example_document_processing_flow` tool.

Feature branch reference: `feat-sample-doc-proc-agent-ootb-flow-15297`,
`sample-doc-proc-agent-phase-2-15455`

---

## The ask

In the `wxo-server` / schema job source, add `"type": "object"` to the `input_schema` of the
seeded `example_document_processing_flow` tool:

```json
"input_schema": {
    "type": "object",
    "properties": {
        "document_path": { "type": "string", "description": "Path or URL to the document to process" },
        "extraction_options": { "type": "object", "description": "Optional extraction configuration" }
    },
    "required": ["document_path"]
}
```

The same fix should be applied to any other seeded tool definitions that may have the same
omission (e.g. any companion agent spec stored alongside this tool).

If the tool record is stored in existing tenant DBs (already-provisioned tenants), a follow-up
data migration may be needed to patch the stored `input_schema` for those tenants too.

---

## ADK-side workaround (already merged)

As a client-side resilience measure, `ToolRequestBody.type` has been made optional with a
default of `'object'` in `packages/core/ibm_watsonx_orchestrate_core/types/tools/types.py`.
A `WARNING` is now emitted whenever a tool is deserialized without `type`, so the gap remains
visible in logs.

**This is a temporary workaround.** Once the server-side seed data is corrected, the intent is
to revisit making `type` required again, restoring the stricter validation.

The warning currently looks like:

```
[WARNING] ToolRequestBody deserialized without a 'type' field — defaulting to 'object'.
The tool definition stored on the server is missing 'type' in its input_schema
and should be corrected. See wo-tracker#98714.
```

---

## How to verify the fix

After the schema job is updated, on a freshly provisioned tenant:

```bash
orchestrate tools list
# ✅ No [WARNING] about missing 'type' for example_document_processing_flow

orchestrate agents list --kind native
# ✅ DocProcessing agent listed cleanly

orchestrate tools export -n example_document_processing_flow -o out.zip
# ✅ Either exports successfully OR skips with a clear message (if no zip artifact intended)
```
