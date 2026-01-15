# Genesys Bot Connector Channel Integration Example
This example demonstrates how to integrate a Genesys Bot Connector channel with wxo ADK for text-based interactions.

## Prerequisites
1. A Genesys Cloud account
2. Genesys Cloud Bot Connector integration configured
3. OAuth credentials for Genesys Cloud API access

## Setup Steps
1. Log in to your Genesys Cloud account
2. Navigate to Admin > Integrations
3. Create a new Bot Connector integration
4. Create an OAuth client in Genesys Cloud for API access
5. Note your Client ID, Client Secret, Bot Connector ID, and Verification Token
6. Identify your Genesys Cloud API URL (e.g., https://api.mypurecloud.com)
7. Create a `.env` file with the following variables:
```bash
GENESYS_BOT_CLIENT_ID=your_client_id
GENESYS_BOT_CLIENT_SECRET=your_client_secret
GENESYS_BOT_VERIFICATION_TOKEN=your_verification_token
GENESYS_BOT_CONNECTOR_ID=your_bot_connector_id
GENESYS_API_URL=https://api.mypurecloud.com
```

## Running the Example
1. Ensure your `.env` file is configured
2. Run the channel configuration script
3. Configure the Bot Connector in Genesys Cloud
4. Deploy your agent with the Genesys Bot Connector channel enabled
5. Test by initiating a conversation through your Genesys Cloud chat interface
