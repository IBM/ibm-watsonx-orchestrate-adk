# SIP Phone Channel Integration Example
This example demonstrates how to integrate a phone channel via SIP Trunk with wxo ADK.

## Prerequisites
1. A SIP trunk provider account with appropriate credentials
2. wxo ADK installed and configured (latest version recommended)
3. An active wxo environment

## Setup Steps
1. Configure your SIP trunk provider
2. Note your SIP phone number
3. Update the `your_sip_number` variable in `import_all.sh` with your SIP phone number
4. Update the security credentials (`username`, `password`) and `fallback_sip_uri` in `phone/sip_trunk_phone_config.yaml`
5. Update the voice configuration (`voice/voice_example.yaml`) with your Speech-to-Text and Text-to-Speech provider details

## Running the Example
1. Ensure your configurations are set up properly
2. Run the import script to create all resources:
    ```bash
    ./import_all.sh
    ```
   This script will:
   - Import the voice configuration
   - Import the channel agent
   - Import the SIP phone channel configuration
   - Add the phone number and associate it with the agent in the **draft** environment

   The script will output a **SIP URI** (starting with `sips:`).

3. Configure your SIP trunk provider to route calls to the SIP URI
4. Test by making a call to your SIP phone number
