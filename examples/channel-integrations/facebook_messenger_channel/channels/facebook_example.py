import os
from ibm_watsonx_orchestrate.agent_builder.channels import FacebookChannel
from dotenv import load_dotenv
load_dotenv()

# Define the Facebook Messenger channel configuration
channel = FacebookChannel(
    name="production_facebook_channel",
    description="Main customer support Facebook Messenger channel for production environment",
    application_secret=os.getenv("FACEBOOK_APP_SECRET"),
    verification_token=os.getenv("FACEBOOK_VERIFICATION_TOKEN"),
    page_access_token=os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
)
