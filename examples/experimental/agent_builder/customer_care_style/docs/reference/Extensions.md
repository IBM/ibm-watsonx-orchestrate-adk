# Extensions Reference

This document provides a reference for the supported extensions in IBM watsonx Orchestrate. Extensions provide a way for tools to signal the client to take some immediate action. One example of an extension is to transfer the user to a live agent.

All Extensions use the same component (`com.ibm.orchestrate/extensions`) which takes the form of a dictionary with one or more optional extensions.

## Extensions Schema

Extensions are defined in the `_meta` section (outside the content array) of a tool's response using the `com.ibm.orchestrate/extensions` component. Extensions have a specific structure where each extension type has its own interface. There are a number of pre-existing extension types supported natively by the watsonx Orchestrate platform. These are defined below.

### Extension Metadata Interface

The `_meta` section of a tool result contains extension configuration using the `com.ibm.orchestrate/extensions` key:

```typescript
interface Extensions {
  'com.ibm.orchestrate/extensions': {
    transfer_to_channel?: TransferToChannelExtension;
    transfer_to_live_agent?: TransferToLiveAgentExtension;
    end_interaction?: EndInteractionExtension;
    speech_to_text?: SpeechToTextExtension;
    text_to_speech?: TextToSpeechExtension;
  };
}
```

---

## TransferToChannelExtension

Transfers the conversation from one channel to another (e.g., from WhatsApp to web chat).

### Use Cases

- Moving conversation to a richer interface
- Transferring to a channel with more capabilities
- Continuing conversation on a different platform

NOTE: This extension is currently only supported by the phone channel but may eventually support other channels.

### Interface

```typescript
interface TransferToChannelExtension {
  message_to_user: string;
  transfer_info: {
    target: {
      chat: {
        url: string;
      };
    };
  };
}
```

### Fields

| Field                      | Description                                                                          |
| -------------------------- | ------------------------------------------------------------------------------------ |
| `message_to_user`          | Message displayed to user about the transfer                                         |
| `transfer_info`            | Transfer configuration object                                                        |
| `transfer_info.target`     | Target channel configuration                                                         |
| `transfer_info.target.chat`| Chat channel configuration with URL                                                  |

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "I can't collect this information over the phone.",
      annotations: {audience: ["user"]},
    }
  ],
  _meta: {
    'com.ibm.orchestrate/extensions': {
      transfer_to_channel: {
        message_to_user: 'Let me transfer you to web chat for a better experience.',
        transfer_info: {
          target: {
            chat: {
              url: 'https://example.com/webchat'
            }
          }
        }
      }
    }
  }
};
```

### Channel Adaptation

- **All other channels** Ignored
- **Phone/SMS:** Provides target chat URL. For phone, sends the URL to SMS if an SMS channel is configured.

---

## TransferToLiveAgentExtension

Initiates a transfer to a human agent with conditional fields based on channel type including messaging based on agent availability, SIP endpoints, etc..

### Use Cases

- User explicitly requests to speak with a human agent
- Complex issues that require human intervention
- Escalation scenarios
- Situations where automated assistance is insufficient

### Interface

```typescript
interface TransferToLiveAgentExtension {
  message_to_human_agent: string;
  agent_available: string;
  agent_unavailable: string;
  transfer_metadata?: {
    [key: string]: string;
  };
  service_desk_info?: {
    sip?: {
      uri: string;
      transfer_method?: 'refer' | 'hangup';
      transfer_target_header?: string;
      transfer_headers?: Array<{
        name: string;
        value: string;
      }>;
      transfer_headers_send_method?: 'custom_header' | 'contact_header' | 'refer_to_header';
    };
  };
}
```

### Fields

| Field                       | Description                                                        |
| --------------------------- | ------------------------------------------------------------------ |
| `message_to_human_agent`    | Context message passed to the human agent about the user's request |
| `agent_available`   | Message displayed to user while connecting to an available agent   |
| `agent_unavailable` | Message displayed to user when no agents are online                |
| `transfer_metadata` | Optional metadata that can be passed to the live agent during the transfer |
| `service_desk_info` | Information that is used by the channel for transfer routing.                    |

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "I'm transfering you to a live agent.",
      annotations: {audience: ["user"]},
    }
  ],
  _meta: {
    'com.ibm.orchestrate/extensions': {
      transfer_to_live_agent: {
        message_to_human_agent: "User asked to speak to an agent.",
        agent_available: "Please wait while I connect you to an agent.",
        agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later.",
        transfer_metadata: {
          caller_id: "1234567890",
        }
      }
    }
  }
};
```

### Channel Adaptation

`service_desk_info` will be different for each channel. This section includes examples for each channel. The supported values under service_desk_info are `sip`, `zendesk` and `salesforce`. 

#### SIP Phone

For SIP Phone integrations, the `service_desk_info` object should contain the target service desk configuration with SIP-specific parameters. When `transfer_metadata` is defined, the values are converted into a single SIP `User-to-User` header which is HEX encoded. `transfer_headers` can be used to override this behavior and define exactly how to send the metadata in the SIP REFER message.

| Field | Description |
| ----- | ----------- |
| `service_desk_info.sip.uri` | The SIP or telephone URI to transfer the call to, such as `sip:12345556789\\@myhost.com` or `tel:+18005551234` |
| `service_desk_info.sip.transfer_method` | Determines how to transfer the call: `refer`: The call is transferred by sending a SIP REFER request (default). `hangup`: The call is transferred by sending a SIP BYE request. |
| `service_desk_info.sip.transfer_target_header` | The SIP header that contains the transfer target when a BYE request is used for transferring the call. Defaults to `Transfer-Target`. This option is supported only in the `hangup` method. |
|`service_desk_info.sip.transfer_headers` | A list of custom header field name-value pairs to be added to a transfer request. When defined this overrides transfer_metadata. In other words, transfer_metadata is not used when this is defined.|
| `service_desk_info.sip.transfer_headers_send_method` | The method by which the SIP transfer headers are sent. `custom_header`: Sends the transfer headers as part of the SIP message (default). `contact_header`: Sends the transfer headers in the Contact header. This option is not supported in the hangup method. `refer_to_header`: Sends the transfer headers in the Refer-To header. This option is not supported in the hangup method. |

##### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "I'm transfering you to a live agent.",
      annotations: {audience: ["user"]},
    }
  ],
  _meta: {
    'com.ibm.orchestrate/extensions': {
      transfer_to_live_agent: {
        message_to_human_agent: "User asked to speak to an agent.",
        agent_available: "Please wait while I connect you to an agent.",
        agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later.",
        service_desk_info: {
          sip: {
            uri: "sip:+18005551234@myhost.com"
          }
        }
      }
    }
  }
};
```

#### Zendesk
For Zendesk integrations, the `service_desk_info` object should contain the target service desk configuration with Zendesk-specific parameters. 

| Field | Description |
| ----- | ----------- |
| `zendesk.department` | A valid department from your Zendesk account. Not required |


#### Salesforce
For Salesforce integrations, the `service_desk_info` object should contain the target service desk configuration with Salesforce-specific parameters. 

| Field | Description |
| ----- | ----------- |
| `salesforce.button_id` | A valid button ID from your Salesforce deployment. Not required |


---

## EndInteractionExtension

Ends the current conversation session.

### Use Cases

- Tool explicitly ending an interaction on the user's behalf
- Hanging up a call from the agent side.

### Interface

```typescript
interface EndInteractionExtension {
  // This extension has no fields
}
```

### Fields

There are currently no fields for this extension.

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "It was nice talking to you. Goodbye!",
      annotations: {audience: ["user"]},
    }
  ],
  _meta: {
    'com.ibm.orchestrate/extensions': {
      end_interaction: {}
    }
  }
};
```

### Channel Adaptation

- **Phone:** Hangs up the call. Note that this 
- **Web/Mobile:** Closes the chat session
- **SMS:** Ends the conversation thread

---

## SpeechToTextExtension

Configures speech recognition settings for the life of the interaction for any voice related integration.

### Use Cases

- Adjusting speech recognition parameters
- Changing the speech to text model
- Configuring the use of a custom language model
- Optimizing voice recognition noise filtering

### Interface

```typescript
interface SpeechToTextExtension {
  command_info: {
    type: string;
    parameters?: {
      [key: string]: unknown;
    };
  };
}
```

### Fields

| Field | Description  |
|------- | ---- |
| `command_info`            | Object containing speech-to-text configuration                                       |
| `command_info.type`       | Command type (e.g., `"configure"`)                                                   |
| `command_info.parameters` | Configuration parameters for speech recognition                                      |

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "Hi there, how can I help you today?",
      annotations: {audience: ["user"]},
    }
  ],
  _meta: {
    'com.ibm.orchestrate/extensions': {
      speech_to_text: {
        command_info: {
          type: 'configure',
          parameters: {
            narrowband_recognize: {
              model: 'en-US_NarrowbandModel',
              smart_formatting: true
            }
          }
        }
      }
    }
  }
};
```

### Channel Adaptation

- **Phone:** Applies speech recognition configuration
- **All other channels:** Not applicable (phone integration only)

---

## TextToSpeechExtension

Configures text-to-speech settings for the life of the user interaction for voice output.

### Use Cases

- Changing voice characteristics
- Adjusting speech rate or pitch
- Configuring voice output settings
- Enabling or disabling barge-in

### Interface

```typescript
interface TextToSpeechExtension {
  command_info: {
    type: string;
    parameters?: {
      [key: string]: unknown;
    };
  };
}
```

### Fields

| Field                     | Description                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `command_info`            | Object containing text-to-speech configuration                                       |
| `command_info.type`       | Command type (e.g., `"configure"`, `"disable_barge_in"`, `"enable_barge_in"`)       |
| `command_info.parameters` | Configuration parameters for text-to-speech                                          |

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "Hola María, ¿cómo estás hoy?",
      annotations: {audience: ["user"]},
    }
  ],
  _meta: {
    'com.ibm.orchestrate/extensions': {
      text_to_speech: {
        command_info: {
          type: 'configure',
          parameters: {
            voice: 'es-LA_SofiaV3Voice'
          }
        }
      }
    }
  }
};
```

### Channel Adaptation

- **Phone/Voice:** Applies text-to-speech configuration
- **All other channels:** Not applicable (voice channels only)

---
