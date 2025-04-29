# Tools

## Import Tools

The type of the tool that can be imported into Orchestrate can be controlled via the Tool Kind CLI argument (`-k` or `--kind`). There are broadly two types of tools which can be imported.  
- Python Tool Import _(Tool Kind CLI argument value: `python`)_
- [OpenAPI Tool Import](#openapi-tool-import) _(Tool Kind CLI argument value: `openapi`)_

Further, Python Tool imports are subdivided into two subtypes.  
- [Single file Python Tool Import](#single-file-python-tool-orchestrate-tool-import)  
- [Multi-file Python Tool Import](#multi-file-python-tool-orchestrate-tool-import)
  
_**NOTE:** Both subtypes use the same Tool Kind CLI argument value._

### Single file Python Tool Orchestrate tool import

This type of an import can be used when all the Python code that your tool needs to execute are housed in a single `.py` file. Typically, a single file import can be initiated through omitting the package root CLI argument (`--package-root` or `-r`). Setting the value of said CLI argument to an empty string or whitespace will also have the same effect. 

This section of the document describes how you can import a single file Python tool into Orchestrate. It will extract all the tools referenced in the python file passed in. 

Let's assume that the single file tool is placed in the following folder structure, relative to the root of an assumed working directory.    
```bash
─── orchestrate_tools/
    └── py/
        └── single_file_tool/ 
            └── requirements.txt
            └── source/ 
                └── sample_tool.py  
                └── requirements.txt
```

The following are the contents of `orchestrate_tools/py/single_file_tool/source/sample_tool.py`.
```python
# sample_tool.py
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


@tool(name="orchestrator_single_file_sample_tool", description="the description", permission=ToolPermission.ADMIN)
def my_tool(input: str) -> str:
    # functionality of the tool that performs some magic.
```

The following is the command that you will have to execute to import this tool.  
```bash
$ orchestrate tools import -k python \
    -f "orchestrate_tools/py/single_file_tool/source/sample_tool.py" \
    -r "orchestrate_tools/py/single_file_tool/requirements.txt"
``` 

In the above example, ... 
- `orchestrate_tools/py/single_file_tool/source/sample_tool.py` is the main entry point for the tool
- The system will use the provided `requirements.txt` file that was specified in the command. In the event that the requirements file is not provided or omitted, the system will try to resolve (/find) the file, if it exists, as a sibling of `sample_tool.py` in folder `orchestrate_tools/py/single_file_tool/`. If it's not found, the system will omit adding requirements to the artifact Zip package that's created and published during import. 
  - The system will drop any duplicate library import entries in `requirements.txt` file. 
  - The system will drop any provided `ibm-watsonx-orchestrate` library specified in the `requirements.txt` file in favor of the version that's associated with the SDK CLI tool version that's being executed. 

Additional points worth noting. 
- The system will only accept strings comprised of alphanumeric characters and underscores (`_`) in the `name` attribute of the `@tool` decorator in `sample_tool.py`.
- The system will only accept tool file names comprised of alphanumeric characters and underscores (`_`). 
     
### Multi-file Python Tool Orchestrate tool import

The example in the previous section of this document demonstrates how a single file tool can be imported into orchestrator. In the event that the tool you wish to import into orchestrator is more complex and spans several files and folders, the system allows you to provide a package root folder which houses all the files and folders your tool requires during import. 

Let's assume that the multi-file tool has the following folder structure, relative to the root of an assumed working directory.    
```bash
─── orchestrate_tools/
    └── py/
        └── multi_file_tool/ 
            └── requirements.txt
            └── source/ 
                └── tool_entry_point.py 
                └── requirements.txt
                └── sub_module/ 
                    └── sub_module_index.py
                    └── mod_utils.py
                    └── requirements.txt
                └── resources/ 
                    └── logo.png
                    └── sample_data.csv
```
The following are the contents of `orchestrate_tools/py/multi_file_tool/source/tool_entry_point.py`.  
```python
# tool_entry_point.py.py
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
# imports that reference code in "sub_module", etc.  


@tool(name="multi_file_tool_sample", description="multi file tool description", permission=ToolPermission.READ_ONLY)
def multi_file_tool_main(input: str) -> str:
    # functionality of the tool that does some magic.
```
The following example command shows you how to import a multi-file tool.  
```bash
$ orchestrate tools import \
    -k python \
    -f "orchestrate_tools/py/multi_file_tool/source/tool_entry_point.py" \
    -p "orchestrate_tools/py/multi_file_tool" \
    -r "orchestrate_tools/py/multi_file_tool/source/requirements.txt"
```
In the above example, ... 
- `orchestrate_tools/py/multi_file_tool/source/tool_entry_point.py` is the main entry point for the tool
- The system will use the provided `requirements.txt` file that was specified in the command. 
  - In the event that the requirements file is not provided or omitted, the system will try to resolve (/find) the file, if it exists, in the following two locations, in the order that they are mentioned.
    - In the folder in which the tool file (`tool_entry_point.py`) exists.
    - In the package root folder (`orchestrate_tools/py/multi_file_tool`).
  - If the `requirements.txt` file is not found, the system will omit adding requirements to the artifact Zip package that's created and published during import.
  - The system will drop any duplicate library import entries in `requirements.txt` file. 
  - The system will drop any provided `ibm-watsonx-orchestrate` library specified in the `requirements.txt` file in favor of the version that's associated with the SDK CLI tool version that's being executed. 
- The Zip file artifact will contain all folders and files that are contained within specified package root (`orchestrate_tools/py/multi_file_tool`) except for the `requirements.txt` files. The only `requirements.txt` file that will be included in the artifact Zip package will be the one that's provided in the command or, is resolved. 
- In the event that you omit the package root CLI argument from the command, the system will fall back to [single file Python tool import](#single-file-python-tool-orchestrate-tool-import).  

Additional points worth noting. 
- The system will only accept strings comprised of alphanumeric characters and underscores (`_`) in the `name` attribute of the `@tool` decorator in `tool_entry_point.py`.
- The system will only accept tool file names comprised of alphanumeric characters and underscores (`_`).
- The package root folder and the tool file path CLI arguments MUST share a common base path. 
- The path of the tool file folder relative to the package root folder, must be comprised of folder names which are only comprised of alphanumeric characters and underscores (`_`). 
  - As an example, in the event that your package root is `orchestrate_tools/py/` and the tool file is at `orchestrate_tools/py/multi_file_tool/source/tool_entry_point.py`, the path of the tool file folder relative to the package root folder will be `multi_file_tool/source/`. This path, which comprises folder names `multi_file_tool` and `source`, must only contain alphanumeric strings and underscores (`_`).
- Any whitespace like characters which prefix or suffix provided package root path will be stripped by the system. 
- A package root folder path that resolves to an empty string will make the system assume that no package root was specified. Subsequently, the system will fall back to [single file Python tool import](#single-file-python-tool-orchestrate-tool-import) in such cases.     

### OpenAPI Tool import

This will require a yaml (.yaml/.yml) or json (.json) file is passed in through the `--file` of `-f` flag. This yaml or json should be a valid OpenAPI spec for the API you wish to generate tools from.

```bash
 $ orchestrate tools import -k openapi -f <path to openapi spec>
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
