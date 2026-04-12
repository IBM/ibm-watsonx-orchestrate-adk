import os
from ibm_watsonx_orchestrate.agent_builder.channels import TwilioWhatsappChannel
from dotenv import load_dotenv

load_dotenv()
# Define the channel configuration
channel = TwilioWhatsappChannel(
    name="production_whatsapp_channel",
    description="Main customer support WhatsApp channel for production environment",
    account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
    twilio_authentication_token=os.getenv("TWILIO_AUTH_TOKEN"),
)
