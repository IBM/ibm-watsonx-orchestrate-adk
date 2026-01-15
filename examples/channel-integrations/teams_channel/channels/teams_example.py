import os
from ibm_watsonx_orchestrate.agent_builder.channels import TeamsChannel
from dotenv import load_dotenv
load_dotenv()

channel = TeamsChannel(
    name="production_teams_channel",
    description="Main customer support Microsoft Teams channel for production environment",
    app_password=os.getenv("TEAMS_APP_PASSWORD"),
    app_id=os.getenv("TEAMS_APP_ID"),
    teams_tenant_id=os.getenv("TEAMS_TENANT_ID")
)
