# Twilio SMS Channel Integration Example
This example demonstrates how to integrate a Twilio SMS channel with wxo ADK.

## Prerequisites
1. A Twilio account at https://www.twilio.com
2. A Twilio phone number capable of sending/receiving SMS

## Setup Steps
1. Sign up for a Twilio account
2. Purchase or configure a Twilio phone number
3. Locate your Account SID and Auth Token in the Twilio Console
4. Create/export the following environment variables:
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
```
5. Update the `phone_number` in `twilio_sms_example.yaml` with your Twilio number

## Running the Example
1. Ensure your environment variables are configured
2. Update the phone number in the channel configuration
3. Run the import script:
    ```bash
    ./import_all.sh
    ```
   The script will output an **event URL**.
4. Set the event URL as the webhook URL in the **Twilio Console**
5. Test by sending an SMS to your Twilio number
