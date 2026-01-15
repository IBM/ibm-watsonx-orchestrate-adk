# Genesys Audio Connector Phone Channel Integration Example
This example demonstrates how to integrate a phone channel via Genesys Audio Connector with wxo ADK.

## Prerequisites
1. A Genesys Cloud account
2. Genesys Cloud Audio Connector integration configured
3. Appropriate permissions to create integrations

## Setup Steps
1. Log in to your Genesys Cloud account
2. Navigate to Admin > Integrations
3. Create a new Audio Connector integration
4. Generate an API Key and Client Secret (user-generated values)
5. Base-64 encode your Client Secret
6. Configure the same credentials in both Genesys Cloud integration AND this configuration
7. Create a `.env` file with the following variables:
```bash
GENESYS_API_KEY=your_api_key
GENESYS_CLIENT_SECRET=your_base64_encoded_client_secret
```

## Running the Example
1. Ensure your `.env` file is configured with base-64 encoded client secret
2. Run the channel configuration script
3. Configure the Audio Connector integration in Genesys Cloud with matching credentials
4. Deploy your agent with the phone channel enabled
5. Test by making a call through your Genesys Cloud phone number
