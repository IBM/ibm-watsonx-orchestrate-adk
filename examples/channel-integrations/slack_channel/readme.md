# Slack Channel Integration Example
This example demonstrates how to integrate a Slack channel with wxo ADK.

## Prerequisites
1. A Slack workspace with admin permissions
2. A Slack app created at https://api.slack.com/apps

## Setup Steps
1. Create a Slack app in your workspace
2. Configure OAuth & Permissions and add required bot token scopes
3. Install the app to your workspace
4. Copy the required credentials (Client ID, Client Secret, Signing Secret, Bot Token, Team ID)
    - Find Team ID from the URL when you click on either "Workflow Steps" or "App Manifest" tab in your Slack App Setup Page (Team ID starts with the letter "T")
5. Create a `.env` file with the following variables:
```bash
SLACK_CLIENT_ID=your_client_id
SLACK_CLIENT_SECRET=your_client_secret
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_TEAM_ID=your_team_id
```

## Running the Example
1. Ensure your `.env` file is configured
2. Run the channel configuration script
3. Deploy your agent with the Slack channel enabled
4. Test by messaging your bot in Slack
