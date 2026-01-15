import os
from ibm_watsonx_orchestrate.agent_builder.phone import GenesysAudioConnectorChannel
from dotenv import load_dotenv
load_dotenv()

# Both API Key and Client Secret are user-generated values (not obtained from Genesys Cloud).
# The same values must be configured in both: This configuration file AND Audio Connector integration credentials tab
# The Client Secret must be base-64 encoded. The API Key has no encoding restrictions.

channel = GenesysAudioConnectorChannel(
    name="production_phone_channel",
    description="Main customer support phone channel via Genesys Audio Connector",
    security={
        "api_key": os.getenv("GENESYS_API_KEY"),
        "client_secret": os.getenv("GENESYS_CLIENT_SECRET"),
    }
)
