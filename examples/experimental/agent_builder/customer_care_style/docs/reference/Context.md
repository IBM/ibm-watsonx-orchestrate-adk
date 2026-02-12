# Context Variables Reference

This document describes the context variables available to MCP servers through Watson Orchestrate. Context variables provide information about the execution environment, user preferences, and application-specific data that tools can use to customize their behavior.

## Overview

Watson Orchestrate provides context variables through the `_meta` field in tool requests. There are three types of context:

1. **System Context** - Provided automatically by watsonx Orchestrate
2. **Channel Context** - Provided by the channel that invoked the Orchestrate API
2. **Customer Defined Context** - Provided by the application calling the Orchestrate API. Completely defined by the application.

## System Context Variables

System context variables are automatically injected by Watson Orchestrate when it calls an MCP tool which contains platform-provided information about the execution environment.

**Namespace:** `com.ibm.orchestrate/systemcontext`

```typescript
{
  _meta: {
    'com.ibm.orchestrate/systemcontext': {
      locale: 'en-US',
      thread_id: 'thread_abc123xyz789'
    }
  }
}
```

### Available System Context Variables

Here is a list of available system context variables:

| Name              | Type | Description |
| ----------------- | ------- | ------- |
| wxo_email_id      | string    | The user's email ID if WxO defined authentication using JWT was followed.
| wxo_user_name	    | string    | The user name of the user if WxO defined authentication using JWT was followed.
| wxo_tenant_id	    | string    | The tenant ID associated with this interaction.
| locale	          | string    | The user's language and regional preferences.
| thread_id	        | string    | The ID of the current thread.

#### wxo_email_id

The `wxo_email_id` field contains the email address of the user who triggered the current conversation if WxO defined authentication using JWT was followed.
**Field:** `wxo_email_id`  
**Type:** `string`  
**Format:** Valid email address  
**Always Present:** No

**Use Cases:**
- Personalizing responses based on the user's email address

#### wxo_user_name

The `wxo_user_name` field contains the user name of the user who triggered the current conversation if WxO defined authentication using JWT was followed. 
**Field:** `wxo_user_name`  
**Type:** `string`  
**Format:** Valid user name  
**Always Present:** No

**Use Cases:**
- Personalizing responses based on the user's name

#### wxo_tenant_id

The `wxo_tenant_id` field contains the WxO tenant ID associated with the current interaction. 
**Field:** `wxo_tenant_id`  
**Type:** `string`  
**Format:** Valid tenant ID  
**Always Present:** No

#### Locale

The `locale` field indicates the user's language and regional preferences. This allows tools to return localized content, format dates and numbers appropriately, and provide culturally relevant responses.

**Field:** `locale`  
**Type:** `string`  
**Format:** BCP 47 language tag (e.g., `en-US`, `fr-FR`, `es-MX`, `de-DE`)  
**Always Present:** Yes

#### Thread ID

The `thread_id` field contains a unique identifier for the current conversation thread in Watson Orchestrate. This ID remains constant throughout a single conversation and can be used for tracking, logging, or maintaining conversation-specific state across multiple MCP servers and multiple tool calls.

**Field:** `thread_id`  
**Type:** `string`  
**Format:** Unique identifier string  
**Always Present:** Yes

**Use Cases:**

- Maintaining conversation-specific caches or temporary data
- Logging and debugging conversation flows
- Storing global variables that should be shared across all MCP servers in a conversation (e.g., customer ID, authentication tokens)

## Channel Context Variables

Channel context variables are automatically injected by Watson Orchestrate channels and contain channel-provided information collected by the channel.

**Namespace:** `com.ibm.orchestrate/channelcontext`

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "{CHANNEL_TYPE}",
      <CHANNEL_TYPE>: {
          channel_specific_attribute: "value",
          channel_specific_attribute_two: "value2",
          channel_specific_attribute_three: { "key3" : "value3" }
      }
    }
  }
}
```

### Channel Specific Context

Here is a list of the current channel types supported in watsonx Orchestrate:

- slack
- sip
- genesys_bot_connector
- text_messaging (SMS)
- whatsapp
- teams
- chat
- genesys_audio_connector

The structure of a channel specific context _meta object is as follows:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "{CHANNEL_TYPE}",
      <CHANNEL_TYPE>: {
          channel_specific_attribute: "value",
          channel_specific_attribute_two: "value2",
          channel_specific_attribute_three: { "key3" : "value3" }
      }
    }
  }
}
```

The Customer Context variables that are passed to the tools for each of these channels are defined below.

#### Slack Customer Context

| Name    | Type | Description |
| -------- | ------- | ------- |
| team_id  |string    | The unique identifier of the Slack team.
| channel_id | string     | The unique identifier of the Slack channel.
| enterprise_id    | string    | The unique identifier for the Slack organization.
| user_id    | string    | The unique identifier for the Slack user.
| user_email | string | The email address of the Slack user.
| custom_fields | object | The user's profile custom fields.

Example Slack context:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "slack",
      slack: {
        team_id:"T02F3KE542J",
        channel_id:"C4K3KTTRD",
        user_id:"U09C27WKXSQ",
        enterprise_id: "IBM",
        user_email: "example@ibm.com",
        custom_fields: { "Xf09F0ABCD": {'value': 'example custom field1', 'alt': ''}}
      }
    }
  }
}
```

#### SIP Customer Context

| Name    | Type | Description |
| -------- | ------- | ------- |
| call_id  |string    | The SIP call ID associated with the phone call.
| agent_phone_number | string     | The phone number associated with with the watsonx Agent end of the call.
| custom_invite_headers    | Object    | A user-defined array of key/value pairs containing SIP headers from the SIP INVITE request.
| user_phone_number	    | string    | The phone number from which the customer's call originated.
| request_uri	    | string    | The inbound SIP request URI that initiated the phone call.
| from_uri	    | string    | The URI from the From header of the SIP request.
| to_uri	    | string    | The URI from the To header of the SIP request.

Example SIP context:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "sip",
      sip: {
        call_id: "Aob2-2743-5678-1234",
        agent_phone_number:"+18885556789",
        custom_invite_headers: {
            custom-header1: "123",
            custom-header2: "456"
        },
        user_phone_number:"+18595553456",
        request_uri:"sips:+18885557777@public.voip.`us-east.assistant.watson.cloud.ibm.com",
        from_uri:"sips:+18565558576@twilio.com",
        to_uri:"sips:+18885557777@public.voip.us-east.assistant.watson.cloud.ibm.com"
      }
    }
  }
}
```

#### Genesys BOT Connector Customer Context

| Name    | Type | Description |
| -------- | ------- | ------- |
| bot_session_id | string     | This is the id of the session. This id will be used for an entire conversation with the bot (a series of back and forth between the bot and the user until the bot has fulfilled its intent).
| conversation_id	    | string    | This is Genesys Cloud id for the conversation that launched this bot. This can be used for debugging or other data tracking efforts.
| parameters	    | Map    | This is a map of string-string key, value pairs containing optional fields that can be passed down to the bot for custom behavior, tracking, etc
 
Example Genesys BOT Connector context:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "genesys_bot_connector",
      genesys_bot_connector: {
        bot_session_id:"462064bd-820f-4806-a04b-8bdc915dba3e",
        conversation_id:"31408724-1e03-44ca-a698-31da56dd08f4",
        parameters : {
          parameter1: "value1",
          parameter2: "value2"
        }
      }
    }
  }
}
```

#### Text Messaging (SMS) Customer Customer Context

| Name    | Type | Description |
| -------- | ------- | ------- |
| agent_phone_number | string     | The phone number associated with with the watsonx Agent end of the conversation.
| user_phone_number	    | string    | The phone number from which the customer's SMS message originated.
 
Example Text Messaging context:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "text_messaging",
      text_messaging: {
        user_phone_number:"+18595553456",
        agent_phone_number:"+18885556789"
      }
    }
  }
}
```

 #### WhatsApp Customer Context

| Name    | Type | Description |
| -------- | ------- | ------- |
| agent_phone_number | string     | The phone number associated with with the watsonx Agent end of the conversation.
| user_phone_number	    | string    | The phone number from which the customer's WhatsApp message originated.
| user_name	    | string    | The WhatsApp profile name
 
Example WhatsApp context:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "whatsapp",
      whatsapp: {
        user_phone_number:"+18595553456",
        agent_phone_number:"+18885556789",
        user_name:"foo"
      }
    }
  }
}
```

#### Teams Customer Context

| Name    | Type | Description |
| -------- | ------- | ------- |
| conversation_id | string     | The unique identifier of the Microsoft Teams conversation.
| user_name | string     | The name of the user who is interacting with the agent through the channel.
| user_aadObjectId | string     | The Azure Active Directory (AAD) object ID of the user who is interacting with the agent through the channel.

Example Teams context:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/channelcontext': {
      channel_type: "teams",
      teams: {
        conversation_id:"a:1ATy08jyGkPGy2QdKIrGZL5u_o6fIUVDRKeIZtkIUAkQDC23FC9S97f18i-UNl-eISAfDWqoQeTbregvSE8jK0LNy6h9VssNcN3CsGG9guMiUB0EeSqxnnEFpAVzbkayR",
        user_name:"foo",
        user_aadObjectId:"12345678-9abc-def0-1234-56789abcde"
      }
    }
  }
}
```

## Application Defined Context Variables

Customer context variables are provided by the application that calls the watsonx Orchestrate API. These variables allow the calling application to pass custom data that should be available to all tools in the conversation.

**Namespace:** `com.ibm.orchestrate/context`

```typescript
{
  _meta: {
    'com.ibm.orchestrate/context': {
      jwtToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
      customField: 'custom-value'
    }
  }
}
```

### Characteristics

- **Application-Controlled:** The calling application determines what context variables to include
- **Flexible Schema:** Any JSON-serializable data can be passed
- **Always Available:** Context variables are included in every tool call within the conversation
- **Read-Only:** Tools receive these variables but cannot modify them

### Common Use Cases

#### Authentication Tokens

Pass JWT tokens or other authentication credentials that tools need to access backend services:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/context': {
      jwtToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
      apiKey: 'sk-...'
    }
  }
}
```

#### Tenant/Organization Context

For multi-tenant applications, pass tenant or organization identifiers:

```typescript
{
  _meta: {
    'com.ibm.orchestrate/context': {
      appTenantId: 'acme-corp',
      organizationId: 'org-456'
    }
  }
}
```

## Accessing Context Variables

Context variables are accessed by including `_meta` as a parameter in your tool handler function. This provides type-safe access to both system and customer context:

```typescript
handler: async ({
  customerId, // Injected by your application
  _meta, // Contains system and customer context
}: {
  customerId: string;
  _meta?: {
    'com.ibm.orchestrate/systemcontext'?: {
      locale?: string;
      thread_id?: string;
    };
    'com.ibm.orchestrate/channelcontext'?: {
        channel_type: "text_messaging",
        text_messaging: {
          user_phone_number:"+18595553456",
          agent_phone_number:"+18885556789"
        }
    };
    'com.ibm.orchestrate/context'?: {
      jwtToken?: string;
      appTenantId?: string;
      [key: string]: any; // Allow any custom context variables
    };
  };
}) => {
  // Access system context with fallbacks
  const locale = _meta?.['com.ibm.orchestrate/systemcontext']?.locale || 'en-US';
  const threadId = _meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

  // Access channel context with fallbacks
  const channelType = _meta?.['com.ibm.orchestrate/channelcontext']?.channel_type;
  const userPhoneNumber = _meta?.['com.ibm.orchestrate/channelcontext']?.text_messaging?.user_phone_number;
  const agentPhoneNumber = _meta?.['com.ibm.orchestrate/channelcontext']?.text_messaging?.agent_phone_number;

  // Access customer context
  const jwtToken = _meta?.['com.ibm.orchestrate/context']?.jwtToken;
  const appTenantId = _meta?.['com.ibm.orchestrate/context']?.tenantId;

  // Use context in tool logic
  // ...
};
```
