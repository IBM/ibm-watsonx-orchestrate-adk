from ibm_watsonx_orchestrate.agent_builder.channels import WebchatChannel

# Define the channel configuration
# This variable MUST be named 'channel'
channel = WebchatChannel(
    name="main_webchat_channel",
    description="Primary webchat channel for customer interactions"
)
