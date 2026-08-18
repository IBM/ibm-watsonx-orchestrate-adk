# Configure Voice Webhook (CDR)

## Overview

This guide explains how to:

- Generate an API key and token
- Retrieve your instance URL and agent ID
- Configure and run the webhook setup script

-----

## 1. Get API Key and Instance URL

1. Sign in to your watsonx Orchestrate instance
1. Click your profile icon (top-right)
1. Select **Settings**
1. Open the **API details** tab
1. Copy the **Service instance URL**
1. Click **Generate API key** and copy it

-----

## 2. Generate Bearer Token

Run:

```bash
curl -X POST 'https://iam.cloud.ibm.com/identity/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey=YOUR_API_KEY'
```

Replace `YOUR_API_KEY` with your API key.

Example response:

```json
{
  "access_token": "<token>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

Copy the `access_token` value.

-----

## 3. Get Your Agent ID

1. Open your watsonx Orchestrate instance
1. Navigate to your agent
1. Copy the agent ID from the browser URL

-----

## 4. Update Script Configuration

Edit `voice_webhook_setup.sh` and fill in the four required fields at the top:

```bash
BASE_URL="<Service instance URL>/v1/orchestrate"
AGENT_ID="<agent ID>"
WEBHOOK_URL="<your webhook endpoint URL>"
JWT_TOKEN="<access_token from step 2>"
```

The script will exit with an error if any of these are left empty.

### Webhook Types

The script is configured for the **Call Detail Record** webhook by default. To configure a different webhook type, update `WEBHOOK_TYPE` and `APP_ID` at the top of the script accordingly:

|Webhook Type        |App ID                            |Description                     |
|--------------------|----------------------------------|--------------------------------|
|`call_detail_record`|`voice-webhook-call-detail-record`|Call Detail Record webhook      |
|`audio_file`        |`voice-webhook-audio-file`        |Audio attestation webhook       |
|`audio_stream`      |`voice-webhook-audio-stream`      |Audio stream / recording webhook|

### Authentication Types

The script uses **basic auth** by default. To use a different auth type, update both the `security_scheme` field in the configuration and the `runtime_credentials` structure in the script.

**`basic_auth`** (default)

`"security_scheme": "basic_auth"`

```json
{
  "username": "<username>",
  "password": "<password>"
}
```

**`api_key_auth`**

`"security_scheme": "api_key_auth"`

```json
{
  "apikey": "<your-api-key-value>"
}
```

**`bearer_token`**

`"security_scheme": "bearer_token"`

```json
{
  "token": "<your-bearer-token-value>"
}
```

-----

## 5. Run the Script

For draft environment (default):

```bash
bash voice_webhook_setup.sh
```

For live environment:

```bash
bash voice_webhook_setup.sh --env live
```

### Updating an Existing Webhook

If you've already run the script once and need to change the webhook URL, auth type, or credentials, use `--update`:

```bash
bash voice_webhook_setup.sh --env live --update
```

In update mode, the script:

- Updates the existing configuration (webhook URL, security scheme) using the values at the top of the script
- Updates the runtime credentials, creating them if they don't already exist
- Confirms the webhook is attached to the agent, attaching it only if it isn't already

If `--update` is specified but no existing configuration is found for the webhook type, the script exits with an error rather than creating a new one. Use the script without `--update` for first-time setup.

-----

## Notes

- The bearer token expires after 1 hour. Re-generate if you get 401 errors.
- The script is idempotent - safe to re-run. Existing configuration, runtime credentials, and webhook attachments are detected and skipped.
- Use `--update` to modify an existing webhook's configuration or credentials rather than re-running first-time setup.
- Ensure your webhook endpoint is reachable before running.
