# MCP Host Setup

One-time configuration so a coding agent can reach the two watsonx Orchestrate MCP servers.
This is host/IDE setup, not part of the `orchestrate` CLI.

## Config file

Write to `.bob/mcp.json` (Bob) or `.cursor/mcp.json` (Cursor). Replace `<VENV_PYTHON>`
(path to the Python inside your activated venv) and `<WORKING_DIR>` (your project root).

```json
{
  "mcpServers": {
    "watsonx-orchestrate-adk-docs": {
      "command": "uvx",
      "args": ["mcp-proxy", "--transport", "streamablehttp", "https://developer.watson-orchestrate.ibm.com/mcp"]
    },
    "watsonx-orchestrate-adk": {
      "command": "<VENV_PYTHON>",
      "args": ["-m", "ibm_watsonx_orchestrate_mcp_server.server"],
      "env": {"WXO_MCP_WORKING_DIRECTORY": "<WORKING_DIR>"},
      "timeout": 300000
    }
  }
}
```

- `<VENV_PYTHON>` example: `./venv/bin/python` (or the absolute path).
- `timeout` is in milliseconds; the live-platform server needs a high value for long imports.
- Call MCP tools with fully qualified names: `<ServerName>:<tool_name>`.

## The two servers

| Server | Purpose | Key tools |
|---|---|---|
| `watsonx-orchestrate-adk-docs` | Documentation search (read-only) | `search_ibm_watsonx_orchestrate_adk` (broad) · `query_docs_filesystem_…` (read a page by path, append `.mdx`) |
| `watsonx-orchestrate-adk` | Live platform control | `list/create_or_update/import/export/remove_agent` · `list/import/create/remove_tool` · `list/add/import/remove_toolkit` · `import/check_status/remove_knowledge_base` · `import/configure/set_credentials_connection` · `list/import/create_or_update_model` · `chat_with_agent` (add `thread_id` for multi-turn; `include_reasoning=True` for trace) |

> The live-platform (`adk`) import tools are a **last resort** for imports; a dependency-ordered
> `import-all.sh` script is always preferred (see main `SKILL.md` §7).
