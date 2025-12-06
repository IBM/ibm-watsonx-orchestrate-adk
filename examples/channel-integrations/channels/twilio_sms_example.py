import os
from ibm_watsonx_orchestrate.agent_builder.channels import TwilioSMSChannel

# Define the channel configuration
channel = TwilioSMSChannel(
    name="production_sms_channel",
    description="Main customer support SMS channel for production environment",
    account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
    twilio_authentication_token=os.getenv("TWILIO_AUTH_TOKEN"),
    phone_number="+1234567890"
)
