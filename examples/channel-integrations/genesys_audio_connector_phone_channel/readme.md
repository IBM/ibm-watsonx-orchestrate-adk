# Genesys Audio Connector Phone Channel Integration Example
This example demonstrates how to integrate a phone channel via Genesys Audio Connector with wxo ADK.

## Prerequisites
1. A Genesys Cloud account with appropriate permissions to create integrations
2. wxo ADK installed and configured (latest version recommended)
3. An active wxo environment

## Setup Steps
1. Log in to your Genesys Cloud account
2. Navigate to **Admin > Integrations**
3. Create a new **Audio Connector** integration
4. Generate an **API Key** and **Client Secret** (both are user-generated values, not obtained from Genesys)
5. Base-64 encode your Client Secret
6. Create/export the following environment variables:
```bash
GENESYS_API_KEY=your_api_key
GENESYS_CLIENT_SECRET=your_base64_encoded_client_secret
```
   **Note:** If you leave the credentials blank in your configuration, the ADK will automatically fill them from these environment variables.

7. Configure your Genesys Cloud Audio Connector integration using the same credentials (in the Credentials tab)

## Running the Example
1. Ensure your environment variables are configured with the base-64 encoded client secret
2. Ensure the voice-configuration (`voice_example.yaml`) is set up properly
3. Run the import script to create all resources:
    ```bash
    ./import_all.sh
    ```
   This script will:
   - Import the Genesys tools (`transfer_to_human`, `end_session`)
   - Import the voice configuration
   - Import the channel agent
   - Import the phone channel configuration
   - Attach the phone channel to the agent in the **draft** environment

   The script will output an **event URL** (starting with `wss://`) and connector ID.

4. Set the event URL in your **Genesys Audio Connector** integration configuration and Connector ID in the inbound call flow.
5. Test by making a call through your Genesys Cloud phone number
