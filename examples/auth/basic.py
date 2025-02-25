from ibm_watsonx_orchestrate.client.credentials import Credentials
from ibm_watsonx_orchestrate.client.client import Client
from ibm_watsonx_orchestrate.client.tools.tool_client import ToolClient
from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator

# Set platform details.
wxo_url = "<WXO API URL>"
wxo_api_key = "<WXO API KEY>"

# ==================================
#       Authenticator Based
# ==================================

# URL for the auth server
iam_url = "https://iam.platform.saas.ibm.com"

# Set up the authenticator
authenticator = MCSPAuthenticator(apikey=wxo_api_key, url=iam_url)

tools_client = ToolClient(base_url=wxo_url, authenticator=authenticator)
tools = tools_client.get()

print(tools)

# ==================================
#           Token Based
# ==================================

# Initialize wxo client.
credentials = Credentials(url=wxo_url, api_key=wxo_api_key)
client = Client(credentials=credentials)

# Get the token
print(client.token)

# Use the token
tools_client = ToolClient(base_url=wxo_url, api_key=client.token)
tools = tools_client.get()

print(tools)
