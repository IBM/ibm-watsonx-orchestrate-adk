# Twilio WhatsApp Channel Integration Example
This example demonstrates how to integrate a WhatsApp channel via Twilio with wxo ADK.

## Prerequisites
1. A Twilio account at https://www.twilio.com
2. WhatsApp Business API access through Twilio
3. An approved WhatsApp sender

## Setup Steps
1. Sign up for a Twilio account
2. Enable WhatsApp integration in your Twilio Console
3. Complete WhatsApp sender verification process
4. Locate your Account SID and Auth Token in the Twilio Console
5. Create a `.env` file with the following variables:
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
```

## Running the Example
1. Ensure your `.env` file is configured
2. Run the channel configuration script
3. Configure the webhook URL in Twilio WhatsApp settings
4. Test by sending a WhatsApp message to your Twilio WhatsApp account
