# Genesys Bot Connector Channel Integration Example
This example demonstrates how to integrate a Genesys Bot Connector channel with wxo ADK for text-based interactions.

## Prerequisites
1. A Genesys Cloud account with appropriate permissions to create integrations
2. OAuth credentials for Genesys Cloud API access
3. wxo ADK installed and configured (latest version recommended)
4. An active wxo environment

## Setup Steps
1. Log in to your Genesys Cloud account
2. Navigate to **Admin > Integrations**
3. Create a new **Bot Connector** integration
4. Note your **Client ID**, **Client Secret**, **Bot Connector ID**, and **Verification Token**
5. Identify your Genesys Cloud API URL (e.g., `https://api.mypurecloud.com`)
6. Create/export the following environment variables:
```bash
GENESYS_BOT_CLIENT_ID=your_client_id
GENESYS_BOT_CLIENT_SECRET=your_client_secret
GENESYS_BOT_VERIFICATION_TOKEN=your_verification_token
GENESYS_BOT_CONNECTOR_ID=your_bot_connector_id
GENESYS_API_URL=https://api.mypurecloud.com
```
**Note:** The **GENESYS_BOT_VERIFICATION_TOKEN** is the secret value you defined in the Credentials tab, associated with `x-watson-genesys-verification-token` (as key-value pair)

## Running the Example
1. Ensure your environment variables are configured
2. Run the import script to create all resources:
    ```bash
    ./import_all.sh
    ```
   This script will:
   - Import the Genesys tools (`transfer_to_human`, `end_session`)
   - Import the channel agent
   - Import the bot connector channel configuration and associate it with the agent in the **draft** environment

   The script will output an **event URL**.

3. Set the event URL in your **Genesys Bot Connector** integration configuration
4. Test by initiating a conversation through your chat interface
