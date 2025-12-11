import os
from ibm_watsonx_orchestrate.agent_builder.channels import SlackChannel, SlackTeam
from dotenv import load_dotenv

load_dotenv()
# Define the channel configuration
channel = SlackChannel(
    name="production_slack_channel",
    description="Main customer support Slack channel for production environment",
    client_id=os.getenv("SLACK_CLIENT_ID"),
    client_secret=os.getenv("SLACK_CLIENT_SECRET"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
    teams=[
        SlackTeam(
            id=os.getenv("SLACK_TEAM_ID"),  # Slack team/workspace ID
            bot_access_token=os.getenv("SLACK_BOT_TOKEN")  # Bot User OAuth Token (xoxb-...)
        )
    ]
)
