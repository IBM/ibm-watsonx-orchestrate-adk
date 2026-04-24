# Voice Runtime Browser Test Application

A comprehensive web-based testing tool for voice agents that provides real-time conversation testing, call recording, and CDR (Call Detail Record) monitoring capabilities.

## Overview

This FastAPI application serves a browser-based interface for testing voice agents with three main features:

1. **Talk to Your Agent** - Interactive voice conversation testing with DTMF support
2. **Call Recording Server** - Record and playback voice conversations
3. **CDR Logs** - Monitor Call Detail Records and conversation analytics

## Quick Start

### Local Development

From the directory, run:

```bash
uvicorn app:app --host 0.0.0.0 --port 9511
```

Then open your browser to:
- **Browser UI**: `http://localhost:9511/`

**Environment Variables:**
- `PORT`: Port to run the application (default: 9511)

## Features

### 1. Talk to Your Agent

Test your voice agent in real-time through the browser interface.

**Key Capabilities:**
- **Real-time Voice Conversation**: Connect to your voice agent via WebSocket
- **DTMF Support**: Test touch-tone input using on-screen keypad or keyboard (0-9, *, #)
- **Audio Streaming**: Bidirectional audio streaming at 16kHz PCM
- **Connection Management**: Start/stop conversations with visual status indicators

**Configuration Settings:**
- Agent ID
- Environment ID
- Access Token
- Thread ID (optional)
- WebSocket URL (defaults to current host)

### 2. Call Recording Server

Record, store, and playback voice conversations for analysis and debugging.

**Recording Features:**
- **Automatic Recording**: Captures both user and agent audio streams
- **Multiple Audio Formats**:
  - `user.raw` - User audio (mono, 16kHz, 16-bit PCM)
  - `agent.raw` - Agent audio (mono, 16kHz, 16-bit PCM)
  - `interleave.raw` - Combined stereo audio (both channels mixed)
- **Metadata Tracking**: Duration, frame counts, timestamps
- **Browser Playback**: Built-in audio player with automatic PCM-to-WAV conversion
- **Recording Management**: View, browse, and delete recordings

**Recording Server URL:**
```
ws(s)://<host>/record
```

Configure your voice runtime to send recordings to this endpoint.

### 3. CDR Logs

Monitor and analyze Call Detail Records from your voice runtime.

**CDR Monitoring Features:**
- **Real-time Updates**: Auto-refresh every 5 seconds when viewing
- **Statistics Dashboard**:
  - Total reports count
  - Successful calls
  - Failed calls
  - Last received timestamp
- **Detailed Reports**: View complete CDR payloads including:
  - Transaction ID
  - Agent ID
  - Environment ID
  - Call duration
  - Turn count
  - End reason
  - Failure indicators
- **Search Capabilities**: Find reports by transaction ID or thread ID
- **Report Management**: Clear all reports or view individual details

**CDR Webhook URL:**
```
http(s)://<host>/cdr-webhook
```

Configure your voice runtime to send CDR webhooks to this endpoint.

## API Endpoints

### Voice Runtime Proxy

#### `WebSocket /v1/conversation`
Proxy endpoint that forwards browser connections to your voice runtime server.

**Query Parameters:**
- `agent_id` - Agent identifier
- `environment_id` - Environment identifier
- `access_token` - Authentication token
- `thread_id` - Thread identifier (optional)
- `target_url` - Target voice runtime WebSocket URL

**Message Types:**
- `start` - Initialize conversation
- `dtmf` - Send DTMF tone
- Binary audio frames (PCM16, 16kHz)

### Call Recording API

#### `WebSocket /record`
WebSocket endpoint for receiving call recordings from voice runtime.

**Protocol:**
- Start message with session metadata
- Binary audio frames with role, sequence, and timestamp
- Stop message with duration metadata

#### `GET /api/recordings`
List all available recordings.

**Response:**
```json
{
  "recordings": [
    {
      "id": "recording-id",
      "name": "recording-name",
      "metadata": {
        "duration_ms": 90000,
        "start_time": "2026-04-20T19:00:00.000Z",
        "user_frames": 1500,
        "agent_frames": 1200
      }
    }
  ],
  "count": 1
}
```

#### `GET /api/recordings/{recording_id}`
Get files in a specific recording.

**Response:**
```json
{
  "recording_id": "recording-id",
  "files": [
    {
      "name": "user.raw",
      "size": 480000,
      "type": "raw"
    }
  ]
}
```

#### `GET /api/recordings/{recording_id}/metadata`
Get recording metadata.

**Response:**
```json
{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "duration_ms": 90000,
  "start_time": "2026-04-20T19:00:00.000Z",
  "user_frames": 1500,
  "agent_frames": 1200
}
```

#### `GET /api/recordings/{recording_id}/audio/{role}`
Download audio for a specific role (user or agent).

**Parameters:**
- `role` - Either "user" or "agent"

**Response Headers:**
- `X-Sample-Rate: 16000`
- `X-Channels: 1`
- `X-Bit-Depth: 16`

**Response:** Raw PCM audio data (mono, 16kHz, 16-bit)

#### `GET /api/recordings/{recording_id}/audio/interleaved`
Download interleaved stereo audio (both user and agent mixed).

**Response Headers:**
- `X-Sample-Rate: 16000`
- `X-Channels: 2`
- `X-Bit-Depth: 16`
- `X-Channel-Layout: stereo (both channels mixed)`

**Response:** Raw PCM audio data (stereo, 16kHz, 16-bit)

#### `DELETE /api/recordings/{recording_id}`
Delete a specific recording and all its files.

**Response:**
```json
{
  "message": "Recording deleted successfully",
  "recording_id": "recording-id"
}
```

### CDR Logs API

#### `POST /cdr-webhook`
Webhook receiver for CDR reports from voice runtime.

**Request Body:**
```json
{
  "cdr": {
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "thread_id": "660e8400-e29b-41d4-a716-446655440001",
    "agent_id": "770e8400-e29b-41d4-a716-446655440002",
    "environment_id": "880e8400-e29b-41d4-a716-446655440003",
    "call": {
      "start_timestamp": "2026-04-20T19:00:00.000Z",
      "end_reason": "user_hangup",
      "milliseconds_elapsed": 90000
    },
    "turns": [...],
    "failure_occurred": false,
    "system_error": false
  },
  "message": "Call completed successfully"
}
```

**Response:**
```json
{
  "status": "ok",
  "id": "report-uuid"
}
```

#### `GET /api/cdr/reports`
List all CDR reports with summary information.

**Response:**
```json
[
  {
    "id": "report-uuid",
    "received_at": "2026-04-20T19:30:00.000Z",
    "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_id": "770e8400-e29b-41d4-a716-446655440002",
    "environment_id": "880e8400-e29b-41d4-a716-446655440003",
    "end_reason": "user_hangup",
    "start_timestamp": "2026-04-20T19:00:00.000Z",
    "milliseconds_elapsed": 90000,
    "turn_count": 5,
    "failure_occurred": false,
    "system_error": false,
    "message": "Call completed successfully"
  }
]
```

#### `GET /api/cdr/reports/{report_id}`
Get a specific CDR report by ID.

**Response:** Complete CDR report object

#### `GET /api/cdr/reports/by-thread/{thread_id}`
Get CDR reports by thread ID.

**Response:** Array of matching CDR reports (newest first)

#### `GET /api/cdr/reports/by-transaction/{transaction_id}`
Get CDR reports by transaction ID.

**Response:** Array of matching CDR reports (newest first)

#### `DELETE /api/cdr/reports`
Clear all CDR reports from memory.

**Response:**
```json
{
  "status": "cleared"
}
```

### Static Files

#### `GET /`
Serve the main browser UI (index.html)

#### `GET /index.html`
Serve the main browser UI

#### `GET /index.js`
Serve the JavaScript application

#### `GET /wavtools/*`
Serve WebAudio tools library

## Audio Format Specifications

### Individual Streams (user.raw, agent.raw)
- **Encoding**: PCM signed 16-bit little-endian (`pcm_s16le`)
- **Sample Rate**: 16000 Hz (16 kHz)
- **Channels**: Mono (1 channel)
- **Bit Depth**: 16-bit

### Interleaved Stream (interleave.raw)
- **Encoding**: PCM signed 16-bit little-endian (`pcm_s16le`)
- **Sample Rate**: 16000 Hz (16 kHz)
- **Channels**: Stereo (2 channels)
- **Channel Layout**: Both channels contain the same mixed audio (user + agent)
- **Bit Depth**: 16-bit

### Converting Recordings to WAV

Use FFmpeg to convert raw PCM files to WAV format:

```bash
# Convert user audio
ffmpeg -f s16le -ar 16000 -ac 1 -i user.raw user.wav

# Convert agent audio
ffmpeg -f s16le -ar 16000 -ac 1 -i agent.raw agent.wav

# Convert interleaved audio
ffmpeg -f s16le -ar 16000 -ac 2 -i interleave.raw interleave.wav
```

## Browser UI Tabs

### 1. Talk to your Agent
- Configure connection settings (Agent ID, Environment ID, Access Token)
- Start/stop voice conversations
- Use DTMF keypad for touch-tone input
- View connection status in real-time

### 2. Connection Settings
- Agent ID configuration
- Environment ID configuration
- Access Token authentication
- Thread ID (optional for conversation continuity)
- WebSocket URL (defaults to current host)

### 3. Call Recordings
- Browse all available recordings
- View recording metadata (duration, timestamps, frame counts)
- Play back user audio, agent audio, or combined audio
- Delete recordings
- Recording server URL display for configuration

### 4. CDR Logs
- Real-time CDR report monitoring
- Statistics dashboard (total, successful, failed, last received)
- Detailed report viewer with full JSON payload
- Search by transaction ID or thread ID
- Clear all reports
- CDR webhook URL display for configuration

## Storage

### Recordings
Recordings are stored in the `./tmp/` directory (relative to the application directory). Each recording creates a subdirectory containing:
- `user.raw` - User audio stream
- `agent.raw` - Agent audio stream
- `interleave.raw` - Combined stereo audio
- `metadata.json` - Recording metadata

**Note:** In IBM Code Engine, the filesystem is ephemeral. For persistent storage, integrate with IBM Cloud Object Storage or another durable storage solution.

### CDR Reports
CDR reports are stored in-memory and will be lost when the application restarts. For persistent CDR storage, integrate with a database or external logging service.

## Troubleshooting

### Cannot Connect to Voice Runtime
1. Verify the WebSocket URL is correct
2. Check that the voice runtime is running and accessible
3. Ensure the access token is valid
4. Check browser console for connection errors
5. Verify network connectivity and firewall rules

### Recording Not Working
1. Confirm the agent has voice webhooks configured
2. Confirm that the CONNECTION_MANAGER_URL is configured
3. Check that the `/record` WebSocket endpoint is accessible
4. Review application logs for recording errors

### CDR Reports Not Appearing
1. Verify the CDR webhook URL is configured in voice runtime
2. Check that the `/cdr-webhook` endpoint is accessible
3. Ensure the voice runtime is sending CDR webhooks
4. Review application logs for webhook errors
5. Try the refresh button to manually reload reports

### Audio Playback Issues
1. Ensure your browser supports the Web Audio API
2. Check that the recording files exist in the `./tmp/` directory
3. Verify the audio format is correct (16kHz, 16-bit PCM)
4. Try converting to WAV format using FFmpeg

### DTMF Not Working
1. Verify the voice runtime supports DTMF messages
2. Check that the WebSocket connection is active
3. Ensure the voice agent is configured to handle DTMF input
4. Review browser console for DTMF send errors

## Deploying Browser Changes to IBM Code Engine:
The voice testing harness can be built as a docker image, and ran on a remote platform such as IBM Code Engine. 

### Build and Verify the Image Locally:
In the directory, run the following:
```bash
docker buildx build \
  --platform linux/amd64 \
  -t agentic-webhooks \
  --load . 
```

After building the docker image, run it locally to verify before deploying:
```bash
# Run the local image
docker run -p 9511:9511 <your-image-name>

# Run interactively with shell access:
docker run -it -p 9511:9511 <your-image-name> /bin/bash

# Stop running container
docker stop <container-id-or-name>

# Tidy
docker rm <container-id-or-name>
```

Tag Image for IBM Cloud Container Registry
```bash
# Use a date structure instead of latest for clarity
docker tag agentic-webhooks {{REGISTRY_URL}}/agentic-webhooks:20260421

$ docker image ls
agentic-webhooks:latest                         d350a69a97bf        163MB             0B
{{REGISTRY_URL}}/agentic-webhooks:20260421      d350a69a97bf        163MB             0B
```


## Support

For issues, questions, or contributions, please refer to the main project repository.
