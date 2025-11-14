from unittest import mock
from ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller import ChannelsWebchatController
from ibm_watsonx_orchestrate.cli.config import ENV_WXO_URL_OPT, ENVIRONMENTS_SECTION_HEADER

class TestChannelController:
    @mock.patch("builtins.input", return_value="crn:v1:bluemix:public:resource-controller:us-south:a/mock-account-id:some-resource")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.Config.read", return_value='local')
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.Config.get", return_value='some-resource')
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.ChannelsWebchatController.get_host_url")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.ChannelsWebchatController.get_agent_id")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.ChannelsWebchatController.get_environment_id")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_local_dev", return_value=False)
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_ibm_cloud_platform", return_value=True)
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.get_environment", return_value='ibmcloud')
    def test_create_webchat_embed_code(
        self,
        mock_input,
        mock_config_read,
        mock_config_get,
        mock_get_host_url,
        mock_get_agent_id,
        mock_get_env_id,
        mock_is_local_dev,
        mock_is_ibm_cloud_platform,
        mock_get_environment,
    ):
        mock_get_host_url.return_value = "http://localhost:3000"
        mock_get_agent_id.return_value = "mocked-agent-id"
        mock_get_env_id.return_value = "mocked-env-id"

        agent_name = "test-agent"
        env = "draft"

        controller = ChannelsWebchatController(agent_name, env)
        script = controller.create_webchat_embed_code()

        assert "mock-account-id_some-resource" in script
        assert "mocked-agent-id" in script
        assert "mocked-env-id" in script
        assert "http://localhost:3000" in script

    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.Config")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_local_dev", return_value=False)
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.jwt.decode")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_ibm_cloud_platform", return_value=True)
    def test_get_tenant_id(
        self,
        mock_is_ibm_cloud_platform,
        mock_jwt_decode,
        mock_is_local_dev,
        mock_config_class,
    ):
        mock_jwt_decode.return_value = {
            "aud": "crn:v1:bluemix:public:conversation:us-south:a/123456:abcde::"
        }

        mock_auth_config = {
            "MCSP_TOKEN": "mocked.jwt.token"
        }

        mock_config = mock.Mock()
        mock_config.get.return_value = {"local": mock_auth_config}
        mock_config.read.return_value = "local"
        mock_config_class.return_value = mock_config

        controller = ChannelsWebchatController(agent_name="test-agent", env="draft")
        tenant_id = controller.get_tenant_id()

        assert tenant_id == "123456_abcde"


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
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.is_saas_env")
    @mock.patch("ibm_watsonx_orchestrate.cli.commands.channels.webchat.channels_webchat_controller.instantiate_client")
    def test_get_environment_id(self, mock_instantiate_client, mock_is_saas_env, mock_is_local_dev):
        mock_is_local_dev.return_value = True
        mock_is_saas_env.return_value = False

        mock_client = mock.Mock()
        mock_client.get_draft_by_name.return_value = [{"environments": [{"name": "draft", "id": "mocked-env-id"}]}]
        mock_instantiate_client.return_value = mock_client

        controller = ChannelsWebchatController("test-agent", "draft")

        env_id = controller.get_environment_id("test-agent", "draft")
        assert env_id == "mocked-env-id"



