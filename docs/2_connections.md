# Connections
A connection is used to represent a dependency on an external service.

## Structure
The a connection can be thought of as many heirarchically arranged parts.

The first is the connection itself. This is a wrapper and is used to contain the other parts and assign a common identifier that can be passed to tools and agents. See [Create a New Connection](#create-a-new-connection) for details.

The second is the configuration. Each connection can have different configurations depending on environment (draft/live). The configuration outlines shared details on the connections such as its kind (`basic`, `bearer`, `key_value`, etc.) and its type (whether the credentials are shared among the team or per member). See [Configure a Connection](#configure-a-connection) for details.

The third is the credentials. These will be the values used to authorize against the external service. For example if in the configuration you selected a kind of `basic` this would be where you pass in the username and password.
See [Set Credentials of a Connection](#set-credentials-of-a-connection) for details.

The fourth is the identity provider (IDP) credentials. These are only needed for OAuth with SSO. These are used when your external service makes use of a third party OAuth identity provider such as Microsoft or Google to generate auth tokens.
See [Set an Identity Provider](#set-an-idetity-provider) for details.

## Create a New Connection
To create a new connection the first thing you need to do is assign it an app id. This can be done with the following command where  `<my_app_id>` is a unique idenitfier to the connection.
```bash
orchestrate connections add --app-id <my_app_id>
```
 - *`--app-id` : A unique identifier used to refrence the connection

## Configure a Connection
After you have created a connection you can configure the draft and live environments. If you are working against the local instance then only `draft` is supported.
```bash
orchestrate connections configure --app-id <my_app_id> --env [draft|live] --kind <connection_kind> --type [member|team] --url <url_of_external_service>
```
- *`--app-id` : The app id of the connection you want to configure
- *`--env` : The environment you want to configure. `[draft|live]`
- *`--kind` : The kind of connection used to access the external service. `[basic|bearer|api_key|oauth_auth_on_behalf_of_flow|key_value|kv]`
- *`--type` :  The type of credentials. `--type team` will mean the credentials apply to all users, `--type member` will mean each user will have to provide their own credentials. `[member|team]`
- `--url` : The URL of the external service. This will be used as the server for OpenAPI tools and exposed for use in [Python tools](./2_tools.md)  
- `--sso` : Does OAuth require an identity provider. Required for OAuth connections kinds.
- `--idp-token-use` : Sets the token use value for identity provider request
- `--idp-token-type` : Sets the token type value for identity provider request
- `--idp-token-header` : Sets the header used in the identity provider request
- `--app-token-header` : Sets the header used in the app token server request

## Import a Connection from Spec File
Instead of doing the two previous steps, connections and configurations can be defined in a single file and imported with a single command. This is useful for reducing the amount of commands needed and enabling version control systems like git to be used to manage connections.

Below is a sample connection spec file that uses `basic` auth in draft and `oauth_auth_on_behalf_of_flow` in live
```yaml
spec_version: v1
kind: connection
app_id: my_app
environments:
    draft:
        kind: basic
        type: team
        sso: false
        server_url: https://example.com/
    live:
        kind: oauth_auth_on_behalf_of_flow
        type: member
        sso: true
        server_url: https://example.com/
        idp_config:
          header:
            content-type: application/x-www-form-urlencoded
          body:
            requested_token_use: on_behalf_of
            requested_token_type: urn:ietf:params:oauth:token-type:saml2
        app_config:
          header:
            content-type: application/x-www-form-urlencoded
```

Spec files can be imported wih the following command
```bash
orchetstrate connections import --file <path_to_file>
```
 - *`--file` : A path the the yaml connection spec definition 

## Set credentials of a Connection
**Basic**
```bash
orchestrate connections set-credentials --app-id <my_app_id> --env [draft|live] --username <username> --password <password>
```

**Bearer Token**
```bash
orchestrate connections set-credentials --app-id <my_app_id> --env [draft|live] --token <token>
```

**API Key**
```bash
orchestrate connections set-credentials --app-id <my_app_id> --env [draft|live] --api-key <api_key>
```

**OAuth On Behalf Of Flow**
```bash
orchestrate connections set-credentials --app-id <my_app_id> --env [draft|live] --client-id <client_id> --token-url <token_url> --grant-type <grant_type>
```

**Key Value**
```bash
orchestrate connections set-credentials --app-id <my_app_id> --env [draft|live] -e foo=bar -e key1=value1 -e key2=value2 ...
```

## Set an Idetity Provider
For OAuth connection types with SSO enabled, you can set the identity provider with the following.
```bash
orchestrate set-identity-provider --app-id <my_app_id> --env [draft|live] --url <idp_url> --client-id <idp_client_id> --cleint_secret <idp_client_secret> --scope <idp_scope> --grant-type <idp_grant_type>
```

## Associating a Connection to a Tool
### Associating a Connection to an OpenAPI Tool
You can add a connection to an OpenAPI tool using the following. Note that only one connection can be associated and `key_value` connections are not supported by OpenAPI tools
```bash
orchestrate tools import -k openapi -f <path to openapi spec> --app-id <my_app_id>
```

### Associating a Connection to an OpenAPI Tool
You can add a connection to a Python tool using the following. Unlike OpenAPI tools, Python tools can support multiple connections. See [Python Tools Credentials](3_python_tool_credentials.md) documentation for more details.
```bash
orchestrate tools import -k python -f <path to python file> --app-id <my_app_id_1> --app-id <my_app_id_2>
```

## Deleting a Connection
To remove a connection simply run the following command. Be aware deleting the connection will also delete all associated configurations and credentials 
```bash
orchestrate connections remove --app-id <my_app_id>
```

## Listing all application connections
To list all existing connections simply run the following: 
```bash
orchestrate connections list
```
This will display 1 or more tables corresponding to the different environments.