# Tools

## Import Tools
#### `orchestrate tools import`
This command allows a user to import tools into the WXO platform
There are 2 kinds of tool imports, the kind is specified with the `--kind` or `-k` flags
  1. `-k python`

     This will require a python (.py) file is passed in through the `--file` of `-f` flag. It will extract all the tools referenced in the python file passed in. This includes all functions with the `@tool` decorator and all tools imported into the file.
     ```python
     #test_tool.py
     from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


     @tool(name="myName", description="the description", permission=ToolPermission.ADMIN)
     def my_tool(input: str) -> str:
        #functionality of the tool

     ```
     ```bash
     orchestrate tools import -k python -f /test_tool.py

     {
        "name": "myName",
        "description": "the description",
        "permission": "ADMIN",
        "input_schema": {
           "type": "object",
           "properties": {
              "input": {
              "type": "string",
              "title": "Input"
              }
           },
           "required": [
              "input"
           ]
        },
        "output_schema": {
           "type": "string"
        },
        "binding": {
           "python": {
              "function": "tests.cli.resources.python_samples.tool_w_metadata:my_tool"
           }
        }
     }
     ``` 
  2. `-k openapi`
     This will require a yaml (.yaml/.yml) or json (.json) file is passed in through the `--file` of `-f` flag. This yaml or json should be a valid OpenAPI spec for the API you wish to generate tools from.

 ```bash
 orchestrate tools import -k openapi -f <path to openapi spec>
```

## Remove Tool
To remove an existing tool simply run the following: 
```bash
orchestrate tools remove --name my-tool-name
```

## List Tools
To list all tools simply run the following: 
```bash
orchestrate tools list
```
