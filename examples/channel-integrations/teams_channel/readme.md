# Microsoft Teams Channel Integration Example
This example demonstrates how to integrate a Microsoft Teams channel with wxo ADK.

## Prerequisites
1. Microsoft 365 account with Teams
2. Azure account for bot registration
3. A registered bot in Azure Bot Service

## Setup Steps
1. Create a bot registration in Azure Portal
2. Generate an app password for your bot
3. Note the Application (client) ID and Tenant ID
4. Configure the bot's messaging endpoint
5. Create/export the following environment variables:
```bash
TEAMS_APP_ID=your_application_id
TEAMS_APP_PASSWORD=your_app_password
TEAMS_TENANT_ID=your_tenant_id
```

## Running the Example
1. Ensure your environment variables are configured
2. Run the import script:
    ```bash
    ./import_all.sh
    ```
   The script will output an **event URL**
3. Set the event URL as the bot's messaging endpoint
4. Add the bot to your Teams workspace
5. Test by messaging your bot in Teams
