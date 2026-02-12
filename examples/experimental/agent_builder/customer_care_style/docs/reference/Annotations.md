# Annotations Reference

This document provides a reference for the supported content block annotations in IBM watsonx Orchestrate. Annotations provide a way for tools to modify the way a specific content block will be rendered on the channel.

All Annotations use the same component (`com.ibm.orchestrate/annotations`) which takes the form of a dictionary with one or more optional annotations.

## Annotations Schema

Annotations are defined in the `_meta` section of a content block included in a tool result using the `com.ibm.orchestrate/annotations` component. Annotations have a specific structure where each annotation type has its own interface. There are a number of pre-existing annotation types supported natively by the watsonx Orchestrate platform. These are defined below.

### Annotation Metadata Interface

The `_meta` section of a content block contains annotation configuration using the `com.ibm.orchestrate/annotations` key:

```typescript
interface Annotations {
  'com.ibm.orchestrate/annotations': {
    pause?: PauseAnnotation;
    speech?: SpeechAnnotation;
  };
}
```

---

## PauseAnnotation

Add a pause prior to rendering the associated content block.

### Use Cases

- Adding pauses with voice agents before playing back content
- Inserting pauses in chat to make interactions more natural
- Creating timing delays for better user experience

### Interface

```typescript
interface PauseAnnotation {
  delay: number;
}
```

### Fields

| Field   | Description                              |
| ------- | ---------------------------------------- |
| `delay` | The pause time delay in milliseconds     |

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "Does this make sense?",
      annotations: {audience: ["user"]},
      _meta: {
        'com.ibm.orchestrate/annotations': {
          pause: {
            delay: 1000
          }
        }
      }
    }
  ]
};
```

### Channel Adaptation

- **Phone:** Inserts pause before playing audio
- **All other channels:** Inserts delay before displaying content

---

## SpeechAnnotation

Modifies the speech behavior of a content block when rendered on a voice channel.

### Use Cases

- Changing voice characteristics for specific content
- Adjusting speech rate or pitch
- Configuring voice output settings per content block
- Enabling or disabling barge-in for specific messages

### Interface

```typescript
interface SpeechAnnotation {
  disable_speech_barge_in?: boolean;
  disable_dtmf_barge_in?: boolean;
  disable_speech_to_text?: boolean;
  text_to_speech_config?: {
    [key: string]: unknown;
  };
}
```

### Fields

| Field                      | Description                                                                                      |
| -------------------------- | ------------------------------------------------------------------------------------------------ |
| `disable_speech_barge_in`  | (Optional) While this content block is being played back, disable speech barge-in                |
| `disable_dtmf_barge_in`    | (Optional) While this content block is being played back, disable DTMF barge-in                  |
| `disable_speech_to_text`   | (Optional) While this content block is being played back, disable speech-to-text                 |
| `text_to_speech_config`    | (Optional) Configuration parameters for text-to-speech based on the configured speech model      |

### Example

```typescript
return {
  content: [
    { 
      type: 'text', 
      text: "Para servicio en español, presione 1.",
      annotations: {audience: ["user"]},
      _meta: {
        'com.ibm.orchestrate/annotations': {
          speech: {
            disable_speech_barge_in: true,
            disable_dtmf_barge_in: true,
            disable_speech_to_text: true,
            text_to_speech_config: {
              voice: "es-ES_LauraV3Voice"
            }
          }
        }
      }
    }
  ]
};
```

### Channel Adaptation

- **Phone/Voice:** Applies settings to the content block being played back to the voice user
- **All other channels:** Not applicable (voice channels only)

---

## Media Content (Audio, Image, Video)

There may be cases where a tool needs to deliver a URL that points to an audio, image or video file to render on the channel. While MCP content blocks do support audio and image content types, at the moment, those types require Base64 encoded media content to be delivered in the content block. When the tool is delivering the content block to the user with a URL instead of the Base64 encoded data, the tool should use a `resource_link` type content block instead.

### Use Cases

- Displaying a video from a URL on the associated user channel
- Rendering audio or loading an audio player to playback audio from a URL
- Displaying an image from a URL on the associated user channel

### Audio Example

```typescript
return {
  content: [
    {
      type: 'resource_link',
      resource: {
        uri: "https://www.example.com/audio/sample.mp3",
        mimeType: "audio/mpeg",
        text: "Audio recording of customer service call"
      },
      annotations: {audience: ["user"]}
    }
  ]
};
```

### Image Example

```typescript
return {
  content: [
    {
      type: 'resource_link',
      resource: {
        uri: "https://www.example.com/images/product.jpg",
        mimeType: "image/jpeg",
        text: "Product image"
      },
      annotations: {audience: ["user"]}
    }
  ]
};
```

### Video Example

```typescript
return {
  content: [
    {
      type: 'resource_link',
      resource: {
        uri: "https://www.example.com/videos/tutorial.mp4",
        mimeType: "video/mp4",
        text: "Tutorial video"
      },
      annotations: {audience: ["user"]}
    }
  ]
};
```

### Channel Adaptation

- **Phone/Voice:** Plays audio content; images and videos not supported
- **Web/Mobile:** Displays images, plays audio/video with appropriate players
- **SMS:** Sends media links where supported by the carrier

---
