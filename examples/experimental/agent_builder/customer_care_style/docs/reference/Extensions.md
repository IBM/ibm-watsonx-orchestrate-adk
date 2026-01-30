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
    channel_transfer?: ChannelTransferExtension;
    connect_to_agent?: ConnectToAgentExtension;
    end_interaction?: EndInteractionExtension;
    speech_to_text?: SpeechToTextExtension;
    text_to_speech?: TextToSpeechExtension;
  };
}
```

---

## ChannelTransferExtension

Transfers the conversation from one channel to another (e.g., from WhatsApp to web chat).

### Use Cases

- Moving conversation to a richer interface
- Transferring to a channel with more capabilities
- Continuing conversation on a different platform

NOTE: This extension is currently only supported by the phone channel but may eventually support other channels.

### Interface

```typescript
interface ChannelTransferExtension {
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
      channel_transfer: {
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

## ConnectToAgentExtension

Initiates a transfer to a human agent with conditional fields based on channel type including messaging based on agent availability, SIP endpoints, etc..

### Use Cases

- User explicitly requests to speak with a human agent
- Complex issues that require human intervention
- Escalation scenarios
- Situations where automated assistance is insufficient

### Interface

```typescript
interface ConnectToAgentExtension {
  message_to_human_agent: string;
  agent_available: string;
  agent_unavailable: string;
  transfer_info?: {
    target?: {
      service_desk?: {
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
| `transfer_info`             | (Optional) Information that is used by the channel for routing the transfer.                    |

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
      connect_to_agent: {
        message_to_human_agent: "User asked to speak to an agent.",
        agent_available: "Please wait while I connect you to an agent.",
        agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later."
      }
    }
  }
};
```

### Channel Adaptation

`transfer_info` will be different for each channel. This section includes examples for each channel.

#### SIP Phone

For SIP Phone integrations, the `transfer_info` object should contain the target service desk configuration with SIP-specific parameters.

| Field | Description |
| ----- | ----------- |
| `transfer_info.target.service_desk.sip.uri` | The SIP or telephone URI to transfer the call to, such as `sip:12345556789\\@myhost.com` or `tel:+18005551234` |
| `transfer_info.target.service_desk.sip.transfer_method` | (Optional) Determines how to transfer the call: `refer`: The call is transferred by sending a SIP REFER request (default). `hangup`: The call is transferred by sending a SIP BYE request. |
| `transfer_info.target.service_desk.sip.transfer_target_header` | (Optional) The SIP header that contains the transfer target when a BYE request is used for transferring the call. Defaults to `Transfer-Target`. This option is supported only in the `hangup` method. |
| `transfer_info.target.service_desk.sip.transfer_headers` | (Optional) A list of custom header field name-value pairs to be added to a transfer request. |
| `service_desk.sip.transfer_headers_send_method` | (Optional) The method by which the SIP transfer headers are sent. `custom_header`: Sends the transfer headers as part of the SIP message (default). `contact_header`: Sends the transfer headers in the Contact header. This option is not supported in the hangup method. `refer_to_header`: Sends the transfer headers in the Refer-To header. This option is not supported in the hangup method. |

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
      connect_to_agent: {
        message_to_human_agent: "User asked to speak to an agent.",
        agent_available: "Please wait while I connect you to an agent.",
        agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later.",
        transfer_info: {
          target: {
            service_desk: {
              sip: {
                uri: "sip:+18005551234@myhost.com",
                transfer_headers: [
                  {
                    name: "Customer-Header1",
                    value: "Some-Custom-Info"
                  }
                ]
              }
            }
          }
        }
      }
    }
  }
};
```

#### Genesys Audio Connector
TBD

#### Genesys BOT Connector
TBD

#### WhatsApp
TBD

#### Zendesk
TBD

#### Salesforce
TBD

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
| `command_info.parameters` | (Optional) Configuration parameters for speech recognition                                      |

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
| `command_info.parameters` | (Optional) Configuration parameters for text-to-speech                                          |

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
