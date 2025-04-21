import logging
import logging
import rich
import jwt

from ibm_watsonx_orchestrate.cli.config import Config, ENV_WXO_URL_OPT, ENVIRONMENTS_SECTION_HEADER, CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, CHAT_UI_PORT
from ibm_watsonx_orchestrate.client.utils import is_local_dev, AUTH_CONFIG_FILE_FOLDER, AUTH_SECTION_HEADER, AUTH_MCSP_TOKEN_OPT, AUTH_CONFIG_FILE

from ibm_watsonx_orchestrate.client.agents.agent_client import AgentClient

from ibm_watsonx_orchestrate.client.utils import instantiate_client

logger = logging.getLogger(__name__)

class ChannelsWebchatController:
    def __init__(self, agent_name: str, env: str):
        self.agent_name = agent_name
        self.env = env

    def get_native_client(self):
        self.native_client = instantiate_client(AgentClient)
        return self.native_client


    def get_agent_id(self, agent_name: str):
        native_client = self.get_native_client()
        existing_native_agents = native_client.get_draft_by_name(agent_name)

        if not existing_native_agents:
            logger.error(f"No agent found with the name '{agent_name}'")
            exit(1)
        agent_id = existing_native_agents[0]['id']
        return agent_id

    def get_environment_id(self, agent_name: str, env: str):
        native_client = self.get_native_client()
        existing_native_agents = native_client.get_draft_by_name(agent_name)

        if not existing_native_agents:
            raise ValueError(f"No agent found with the name '{agent_name}'")

        agent = existing_native_agents[0]
        agent_environments = agent.get("environments", [])

        is_local = is_local_dev()
        target_env = env or 'draft'

        if is_local:
            if env == 'live':
                logger.warning('Live environments do not exist for Local env, defaulting to draft.')
            target_env = 'draft'

        filtered_environments = [e for e in agent_environments if e.get("name") == target_env]

        if not filtered_environments:
            if env == 'live':
                logger.error(f'This agent does not exist in the {env} environment. You need to deploy it to {env} before you can embed the agent')
            exit(1)

        return filtered_environments[0].get("id")


    def get_tennent_id(self):
        auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)

        cfg = Config()
        active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
        is_local = is_local_dev()

        existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(active_env, {})

        existing_token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None

        token = jwt.decode(existing_token, options={"verify_signature": False})
        tenant_id = ""
        if is_local:
            tenant_id = token.get('woTenantId', None)
        else:
            tenant_id = token.get('tenantId', None)

        return tenant_id

    def get_host_url(self):
        cfg = Config()
        active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
        env_cfg = cfg.get(ENVIRONMENTS_SECTION_HEADER, active_env)
        url = env_cfg.get(ENV_WXO_URL_OPT)
        is_local = is_local_dev(url=url)
        if is_local:
            url_parts = url.split(":")
            url_parts[-1] = CHAT_UI_PORT
            url = ":".join(url_parts)
            return url
        else:
            if url.startswith("https://api."):
                url = url.replace("https://api.", "https://", 1)
            cleaned_url = url.split(".com")[0] + ".com"

            return cleaned_url

            
    def create_webchat_embed_code(self):
        tenant_id = self.get_tennent_id()
        host_url = self.get_host_url()
        agent_id = self.get_agent_id(self.agent_name)
        agent_env_id = self.get_environment_id(self.agent_name, self.env)

        is_local = is_local_dev()
        script_path = (
            "/wxoLoader.js?embed=true"
            if is_local
            else "/wxochat/wxoLoader.js?embed=true"
        )

        script = f"""
            <script>
                window.wxOConfiguration = {{
                    orchestrationID: "{tenant_id}",
                    hostURL: "{host_url}",
                    rootElementID: "root",
                    showLauncher: true,
                    chatOptions: {{
                        agentId: "{agent_id}",
                        agentEnvironmentId: "{agent_env_id}"
                    }},
                }};

                setTimeout(function () {{
                    const script = document.createElement('script');
                    script.src = `${{window.wxOConfiguration.hostURL}}{script_path}`;
                    script.addEventListener('load', function () {{
                    wxoLoader.init();
                    }});
                    document.head.appendChild(script);
                }}, 0);
            </script>
        """ 

        rich.print(script)
        return script

