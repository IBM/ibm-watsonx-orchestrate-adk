# Toolkits

Only node based MCP server is tested currently

## Import Toolkits

Flags

   * `--kind` / `-k`             is the kind of toolkit you want to import. Currently only `mcp` is supported.
   * `--name` / `-n`             is the name of the toolkit you want to create.
   * `--description`             is the description of the toolkit.
   * `--package-root` / `-p`     is the root directory of the MCP server package.
   * `--command`                 is the command to start the MCP server. Can be a string (e.g. `'node dist/index.js --transport stdio'`) or a JSON-style list (e.g. `'["node", "dist/index.js", "--transport", "stdio"]'`).
   * `--tools` / `-t`            is a comma-separated list of tools to import, or `*` to import all tools. e.g. `--tools="tool_1,tool_2"`
   * `--app-id` / `-a`           is the app ID to associate with this toolkit. Only `key_value` connections are supported.

Examples:

Use all (denoted by the `*`) Tools for my Toolkit:
```bash
orchestrate toolkits import \
     --kind mcp \
     --name toolkit_name \
     --description "helps you talk to the manager" \
     --package-root /path/to/folder \
     --command '["node", "dist/index.js", "--transport", "stdio"]' \
     --tools "*" \
     --app-id "my_app_id" 
```

Command as string instead of JSON-style list
```bash
orchestrate toolkits import \
     --kind mcp \
     --name toolkit_name \
     --description "helps you talk to the manager" \
     --package-root /path/to/folder \
     --command "node dist/index.js --transport stdio" \
     --tools "*" \
     --app-id "my_app_id" 
```

Manually insert list of tools
```bash
orchestrate toolkits import \
     --kind mcp \
     --name toolkit_name \
     --description "helps you talk to the manager" \
     --package-root /path/to/folder \
     --command "node dist/index.js --transport stdio" \
     --tools "list-repositories, get-user" \
     --app-id "my_app_id" 
```

If no tools are provided, we will fetch them from the MCP server for you
```bash
orchestrate toolkits import \
     --kind mcp \
     --name toolkit_name \
     --description "helps you talk to the manager" \
     --package-root /path/to/folder \
     --command "node dist/index.js --transport stdio" \
     --app-id "my_app_id" 
```


## Remove Toolkit
To remove an existing toolkit simply run the following: 
```bash
orchestrate toolkit remove --n my-toolkit-name
```