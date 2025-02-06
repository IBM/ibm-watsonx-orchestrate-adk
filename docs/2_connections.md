# Connections
A connection is used to represent a dependency on an external service.

## Application connections
Application dependencies, specifically, represent the credentials needed to authenticate with an external restful 
service when used in combination with openapi tools.

### Creating an application connection 
**Basic**
```bash
orchestrate connections application create --app-id my-basic-app -t basic -u username -p password
```

**Bearer token**
```bash
orchestrate connections application create --app-id my-bearer-app -t bearer --token foobar
```

**API Key**
```bash
orchestrate connections application create --app-id my-bearer-app -t bearer --api-key foobar
```

**OAuth Code Flow**
```bash
orchestrate connections application create --app-id my-bearer-app -t oauth_auth_code_flow \
    --client-id clientid \
    --client-secret supersecret \
    --well-known-url https://example.com
```

**OAuth Implicit Flow**
```bash
orchestrate connections application create --app-id my-bearer-app -t oauth_auth_implicit_flow \
  --client-id clientid \ 
  --client-secret supersecret \
  --well-known-url https://example.com
```

**OAuth Password Flow**
```bash
orchestrate connections application create --app-id my-oauth-password-app -t oauth_auth_password_flow \ 
  --client-id clientid \
  --client-secret supersecret \
  --well-known-url https://example.com \
  --username username \
  --password password
```

**OAuth Client Credentials Flow**
```bash
orchestrate connections application create --app-id my-client-credentials-app -t oauth_auth_client_credentials_flow \ 
  --client-id clientid \
  --client-secret supersecret \
  --well-known-url https://example.com
```

### Associating an application connection to an openapi tool
To associate an application connection with an openapi spec, simply reference the app-id you created in the previous step.
```bash
orchestrate tools import -k openapi -f <path to openapi spec> --app-id my-basic-app
```


### Deleting an application connection
To remove an application connection simply run the following: 
```bash
orchestrate connections application remove --app-id my-basic-app
```