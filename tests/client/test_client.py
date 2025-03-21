from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client import utils
from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient
# from ibm_watsonx_orchestrate.client.agents.external_agent_client import ExternalAgentClient
# from ibm_watsonx_orchestrate.client.agents.assistant_agent_client import AssistantAgentClient


def test_native_agent_client():
    utils.DEFAULT_CONFIG_FILE_FOLDER = "tests/client/resources/"
    utils.DEFAULT_CONFIG_FILE = "config.yaml"
    utils.AUTH_CONFIG_FILE_FOLDER = "tests/client/resources/"
    utils.AUTH_CONFIG_FILE = "credentials.yaml"

    client = instantiate_client(AgentClient)
    assert client


# def test_external_agent_client():
#     utils.DEFAULT_CONFIG_FILE_FOLDER = "tests/client/resources/"
#     utils.DEFAULT_CONFIG_FILE = "config.yaml"
#     utils.AUTH_CONFIG_FILE_FOLDER = "tests/client/resources/"
#     utils.AUTH_CONFIG_FILE = "credentials.yaml"

#     client = instantiate_client(ExternalAgentClient)
#     assert client

# def test_assistant_agent_client():
#     utils.DEFAULT_CONFIG_FILE_FOLDER = "tests/client/resources/"
#     utils.DEFAULT_CONFIG_FILE = "config.yaml"
#     utils.AUTH_CONFIG_FILE_FOLDER = "tests/client/resources/"
#     utils.AUTH_CONFIG_FILE = "credentials.yaml"

#     client = instantiate_client(AssistantAgentClient)
#     assert client
