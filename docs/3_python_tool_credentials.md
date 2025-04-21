# Python Tool Credentials
## Overview
A common feature needed by users is the ability to access credentials/custom secret values during the runtime of their Python tools. Examples may include needing an API key for some library or servive that their code relies on.

This can be achieved through the use of `connections`, which allow you to set up credentials and values which will be exposed during the Python tool's execution with needing to hard code the values and risk exposing secrets.

This guide will detail
* How to create connections for Python tools
* How to set up your Python tools to use connections
* How to import Python tools that use connections
* Some common errors and how to troubleshoot them

## Connection Creation
Connections for Python tools can be created the same as OpenAPI connections (See [2_connections.md](2_connections.md)) The big things to note are the `--app-id` (**Note:** the `--app-id` does not need to be the same as the `app_id` used in the Python tool. See [Importing a Python Tool with Credentials](#importing-a-python-tool-with-credentials)) and the `--kind` as these will be needed to access the data from the Python tool.

The 2 major differences between connections for Python tools and connections for OpenAPI tools are
* Python tools can have multiple associated app-ids (thus multiple connections)
* Python tools support the `key_value` type

### Key Value Type

The `key_value` type is a unique type exclusive to Python tools. It allows the user to pass in any data they want in the form of key value pairs. These will be exposed in the Python tool as a dictionary with the dictionary key mapping to the string to the left of the equals and the value mapping to the string to the right of the equals.

```bash
orchestrate conncetions add --app-id my_key_value
orchestrate connections configure --app-id my_key_value --env draft --type team --kind key_value
orchestrate connections set-credentials --app-id my_key_value --env draft -e key1=value1 -e key2=value2
```

When accessed in the tool the following will return a dictionary

```python
{
    'key1': 'value1',
    'key2': 'value2'
}
```

## Python Tool Definition
For this doc lets imagine we have the Python tool below. This tool is required to make an api call to `sample-api.com` (Not a real endpoint) which needs an api key to authenticate.

```python
import requests
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(
    permission=ToolPermission.READ_ONLY
)
def my_sample_tool() -> str:
    """
    A tool which takes 2 params and passes them to an api
    """

    url = "https://sample-api.com/"
    headers = {
        "Authorization": <my_api_key>
    }
    response = requests.get(url, headers=headers)
    return response

```
The core problem `connections` seek to address is "How can the tool get an api key, without including it directly in the code?" The way the SDK answers this is using `ibm_watsonx_orchestrate.run.connections` which gives us access to the `connections` we created in the previous step. Using this we can rewrite our tool as the following.

```python
import requests
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections

@tool(
    permission=ToolPermission.READ_ONLY
)
def my_sample_tool() -> str:
    """
    A tool which takes 2 params and passes them to an api
    """

    url = "https://sample-api.com/"
    conn = connections.api_key_auth(<my_connection_app_id>)
    headers = {
        "Authorization": conn.api_key
    }
    response = requests.get(url, headers=headers)
    return response
```

The key change is the inclusion of `connections.api_key_auth(<my_connection_app_id>)`. This line gets the connection of type `api_key` with the `app_id` provided.

There are other types of connections (See [2_connections.md](./2_connections.md)) and they can all be accessed using the following:
* `basic` - `conn = connections.basic_auth(<app_id>)`
    * `conn.username`
    * `conn.password`
    * `conn.url`
* `bearer` - `conn = connections.bearer_token(<app_id>)`
    * `conn.token`
    * `conn.url`
* `api_key` - `conn = connections.api_key_auth(<app_id>)`
    * `conn.api_key`
    * `conn.url`
* `oauth_auth_on_behalf_of_flow` - `conn = connections.oauth2_on_behalf_of(<app_id>)`
    * `conn.access_token`
    * `conn.url`
* `key_value` - `conn = connections.key_value(<app_id>)`
    * returns a user defined dictionary (See [key value section](#key-value-type))

An optional (but recommended) step is to use the `expected_credentials` option of the `@tool` decorator. This option allows you to define the connections and types that the tool requires and adds a validation step when someone tries to import the tool. Adding this to out previous example would look something like this:

```python
import requests
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

@tool(
    permission=ToolPermission.READ_ONLY,
    expected_credentials=[{
        "app_id": <my_connection_app_id>,
        "type": ConnectionType.API_KEY_AUTH
        }]
)
def my_sample_tool() -> str:
    """
    A tool which takes 2 params and passes them to an api
    """

    url = "https://sample-api.com/"
    conn = connections.api_key_auth(<my_connection_app_id>)
    headers = {
        "Authorization": conn.api_key
    }
    response = requests.get(url, headers=headers)
    return response
```

You can pass in a list of dictionaries specifying the `app_id` and `type` of connection that the tool requires. Or you can pass in just a list of strings if you only want to validate connection name.

Additionally, if your Python tool can support multiple kinds of auth you can provide a list to the `type` option. Then the connections.get_connection_type can be used to determine which kind of auth has been provided through that connection.

```python
import requests
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

@tool(
    permission=ToolPermission.READ_ONLY,
    expected_credentials=[{
        "app_id": <my_connection_app_id>,
        "type": [ConnectionType.BASIC, ConnectionType.API_KEY_AUTH]
        }]
)
def my_sample_tool() -> str:
    """
    A tool which takes 2 params and passes them to an api
    """

    url = "https://sample-api.com/"
    if connections.get_connection_type("darragh-creds") == ConnectionType.BASIC_AUTH:
        conn = connections.basic_auth(<my_connection_app_id>)
        auth_header = f"Basic {conn.username}:{conn.password}"
    else:
        conn = connections.api_key_auth(<my_connection_app_id>)
        auth_header = f"Bearer {conn.api_key}"
    headers = {
        "Authorization": auth_header
    }
    response = requests.get(url, headers=headers)
    return response
```

## Importing a Python Tool with Credentials
Once you have your connections and tool created you can import it into WxO with the following

```bash
orchestrate tools import -k python -f <path to file> --app-id my_app_id1 --app-id my_python_app_id=my_app_id2
```

In the above example we see a Python tool being imported with 2 app ids. The first is a simple app-id 'my_app_id1', importing this way means that your connection is named 'my_app_id1' and that your Python tool is looking for 'my_app_id1'. In cases where you need the connection to have a different app id than what the Python tools uses you can use the second style of app id. In the above example we can see 'my_python_app_id=my_app_id2' this will be accessible in the Python tool as 'my_python_app_id'
```python
    conn = connections.basic_auth("my_python_app_id")
```
and it will expose the content of the connection 'my_app_id2'
```bash
orchestrate connections set-credentials --app-id my_app_id2 --env draft --username my_username --password my_password
```

## Troubleshooting Tips
There are many error messages that may occur when importing a Python tool with credentials (especially one with `expected_credentials`). Most serve to help guide the user in how to properly define their connections to work with their Python tool.

### No `app-id` given
If no app-id is passed into a tool that has `expected_credentials` you will see the following error
```bash
[ERROR] - The tool 'my_sample_tool' requires an app-id 'my_app_id'. Please use the `--app-id` flag to provide the required app-id
```

To fix this be sure to pass in the --app-id flag when importing the tool and make sure the name is correct
```bash
orchestrate tools import -k python -f <path to file> --app-id my_app_id
```

### No connection exists
If you try to pass in a connection that doesn't exist you will see the following
```bash
[ERROR] - No connection exists with the app-id 'my_app_id'
```

To fix this be sure you create the connection before importing the tool

```bash
orchestrate connections add create --app-id my_sample_tool
```

### Type Mismatch
If you specify an app id on a connection that is of a different type than what the tool specifies in `expected_credentials` you will see the following 

```bash
[ERROR] - The app-id 'my_app_id' is of type 'basic_auth'. The tool 'my_sample_tool' expects this connection to be of type 'api_key_auth'. Use `orchestrate connections list` to view current connections and use `orchestrate connections add` to create or update the relevent connection
```

To fix this remove the existing connection with that name and re-create it with the correct type. Or if that connection is used by a different tool that requires that type, create a new connection with a different name (my_app_id_2) and the correct type. Then import using an alias

```bash
orchestrate tools import -k python -f <path to file> --app-id my_app_id=my_app_id_2
```