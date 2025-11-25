import os
from ibm_watsonx_orchestrate.agent_builder.channels import GenesysBotConnectorChannel
from dotenv import load_dotenv

# Define the channel configuration
channel = GenesysBotConnectorChannel(
    name="production_genesys_bot_channel",
    description="Main Genesys Bot Connector for text-based customer interactions",
    client_id=os.getenv("GENESYS_BOT_CLIENT_ID"),
    client_secret=os.getenv("GENESYS_BOT_CLIENT_SECRET"),
    verification_token=os.getenv("GENESYS_BOT_VERIFICATION_TOKEN"),
    bot_connector_id=os.getenv("GENESYS_BOT_CONNECTOR_ID"),
    api_url=os.getenv("GENESYS_API_URL", "https://api.mypurecloud.com"),
)
