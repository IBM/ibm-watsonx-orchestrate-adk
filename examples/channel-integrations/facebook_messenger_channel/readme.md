# Facebook Messenger Channel Integration Example
This example demonstrates how to integrate a Facebook Messenger channel with wxo ADK.

## Prerequisites
1. A Facebook account
2. A Facebook Page for your business
3. A Facebook App created at https://developers.facebook.com

## Setup Steps
1. Create a Facebook App in the Meta for Developers portal
2. Add the Messenger product to your app
3. Generate a Page Access Token for your Facebook Page
4. Configure webhooks for your Messenger integration
5. Note your App Secret and create a verification token (your own string)
6. Create a `.env` file with the following variables:
```bash
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_VERIFICATION_TOKEN=your_verification_token
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token
```

## Running the Example
1. Ensure your `.env` file is configured
2. Run the channel configuration script
3. Configure the webhook URL in your Facebook App settings
4. Deploy your agent with the Facebook Messenger channel enabled
5. Test by sending a message to your Facebook Page
