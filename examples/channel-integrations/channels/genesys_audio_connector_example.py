import os
from ibm_watsonx_orchestrate.agent_builder.phone import GenesysAudioConnectorChannel

channel = GenesysAudioConnectorChannel(
    name="production_phone_channel",
    description="Main customer support phone channel via Genesys Audio Connector",
    security={
        "api_key": os.getenv("GENESYS_API_KEY"),
        "client_secret": os.getenv("GENESYS_CLIENT_SECRET"),
    }
)
