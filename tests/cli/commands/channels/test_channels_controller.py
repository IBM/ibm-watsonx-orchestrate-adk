from unittest import mock
from ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller import ChannelsWebchatController
from ibm_watsonx_orchestrate.cli.config import ENV_WXO_URL_OPT, ENVIRONMENTS_SECTION_HEADER

class TestChannelController:
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.ChannelsWebchatController.get_tennent_id")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.ChannelsWebchatController.get_host_url")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.ChannelsWebchatController.get_agent_id")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.ChannelsWebchatController.get_environment_id")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_local_dev")
    def test_create_webchat_embed_code(
        self,
        mock_is_local_dev_env,
        mock_get_env_id,
        mock_get_agent_id,
        mock_get_host_url,
        mock_get_tennent_id
    ):
        mock_get_tennent_id.return_value = "mocked-tenant-id"
        mock_get_host_url.return_value = "http://localhost:3000"
        mock_get_agent_id.return_value = "mocked-agent-id"
        mock_get_env_id.return_value = "mocked-env-id"
        mock_is_local_dev_env.return_value = True

        agent_name = "test-agent"
        env = "draft"

        controller = ChannelsWebchatController(agent_name, env)
        script = controller.create_webchat_embed_code()

        assert "mocked-tenant-id" in script
        assert "mocked-agent-id" in script
        assert "mocked-env-id" in script
        assert "http://localhost:3000" in script
        assert "/wxoLoader.js?embed=true" in script

    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.jwt.decode")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_local_dev")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.Config")
    def test_get_tennent_id(self, mock_config_class, mock_is_local_dev, mock_jwt_decode):
        mock_is_local_dev.return_value = True

        mock_jwt_decode.return_value = {"woTenantId": "mocked-tenant-id"}

        mock_auth_config = {
            "local": {
                "MCSP_TOKEN": "mocked.jwt.token"
            }
        }

        mock_auth_cfg_instance = mock.Mock()
        mock_auth_cfg_instance.get.return_value = mock_auth_config

        mock_config_instance = mock.Mock()
        mock_config_instance.read.return_value = "local"
        mock_config_class.side_effect = [mock_auth_cfg_instance, mock_config_instance]

        controller = ChannelsWebchatController(agent_name="test-agent", env="draft")
        tenant_id = controller.get_tennent_id()

        assert tenant_id == "mocked-tenant-id"

    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_local_dev")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.Config")
    def test_get_host_url_non_local(self, mock_config_class, mock_is_local_dev):
        mock_is_local_dev.return_value = False

        mock_config_instance = mock.Mock()
        mock_config_instance.read.return_value = "dev"

        def mock_get(section, key=None):
            if section == ENVIRONMENTS_SECTION_HEADER and key == "dev":
                return {
                    ENV_WXO_URL_OPT: "https://api.dev.something.com"
                }
            return {}

        mock_config_instance.get.side_effect = mock_get
        mock_config_class.return_value = mock_config_instance

        controller = ChannelsWebchatController(agent_name="test-agent", env="dev")
        url = controller.get_host_url()

        assert url == "https://dev.something.com"

    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_local_dev")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.Config")
    def test_get_host_url_local(self, mock_config_class, mock_is_local_dev):
        mock_is_local_dev.return_value = True

        mock_config_instance = mock.Mock()
        mock_config_instance.read.return_value = "local"
        mock_config_instance.get.return_value = {
            ENV_WXO_URL_OPT: "http://localhost:3000"
        }

        mock_config_class.return_value = mock_config_instance

        controller = ChannelsWebchatController(agent_name="test-agent", env="local")
        url = controller.get_host_url()

        assert url == "http://localhost:3000"

    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.instantiate_client")
    def test_get_agent_id(self, mock_instantiate_client):
        mock_client = mock.Mock()
        mock_client.get_draft_by_name.return_value = [{"id": "mocked-agent-id"}]
        mock_instantiate_client.return_value = mock_client

        controller = ChannelsWebchatController("test-agent", "draft")
        agent_id = controller.get_agent_id("test-agent")
        assert agent_id == "mocked-agent-id"

    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_local_dev")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.instantiate_client")
    def test_get_environment_id(self, mock_instantiate_client, mock_is_local_dev):
        mock_is_local_dev.return_value = True
        
        mock_client = mock.Mock()
        mock_client.get_draft_by_name.return_value = [{"environments": [{"name": "draft", "id": "mocked-env-id"}]}]
        mock_instantiate_client.return_value = mock_client

        controller = ChannelsWebchatController("test-agent", "draft")

        env_id = controller.get_environment_id("test-agent", "draft")
        assert env_id == "mocked-env-id"



