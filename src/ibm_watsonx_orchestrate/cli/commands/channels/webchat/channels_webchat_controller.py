import logging
from typing import Optional
import rich
import jwt
import sys
import requests
from urllib.parse import urlparse

from ibm_watsonx_orchestrate.cli.config import Config, ENV_WXO_URL_OPT, ENV_CRN_OPT, ENVIRONMENTS_SECTION_HEADER, CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, CHAT_UI_PORT
from ibm_watsonx_orchestrate.cli.commands.channels.types import RuntimeEnvironmentType
from ibm_watsonx_orchestrate.client.utils import is_local_dev, is_ibm_cloud_platform, get_environment, get_cpd_instance_id_from_url, is_saas_env, AUTH_CONFIG_FILE_FOLDER, AUTH_SECTION_HEADER, AUTH_MCSP_TOKEN_OPT, AUTH_CONFIG_FILE

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
    
    def extract_tenant_id_from_crn(self, crn: str) -> str:
        is_ibm_cloud_env = is_ibm_cloud_platform()
        if is_ibm_cloud_env:
            try:
                parts = crn.split("a/")[1].split(":")
                account_part = parts[0]
                instance_part = parts[1]
                tenant_id = f"{account_part}_{instance_part}"
                return tenant_id
            except (IndexError, AttributeError):
                raise ValueError(f"Invalid CRN format: {crn}")
        else:
            try:
                parts = crn.split("sub/")[1].split(":")
                account_part = parts[0]
                instance_part = parts[1]
                tenant_id = f"{account_part}_{instance_part}"
                return tenant_id
            except (IndexError, AttributeError):
                raise ValueError(f"Invalid CRN format: {crn}")

        
            
    def check_crn_is_correct(self, crn: str):
        parts = crn.split("a/")[1].split(":")
        instance_part_crn = parts[1]
        cfg = Config()
        active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
        url = cfg.get(ENVIRONMENTS_SECTION_HEADER, active_env, ENV_WXO_URL_OPT)
        instance_part_url = url.rstrip("/").split("/")[-1]
        if instance_part_crn == instance_part_url:
            return True
        else:
            return False

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
        is_saas = is_saas_env()
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

    def get_tenant_id(self):
        auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)

        cfg = Config()
        active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)

        existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(active_env, {})

        existing_token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None
        token = jwt.decode(existing_token, options={"verify_signature": False})
        crn = ""
        crn = token.get('aud', None)

        tenant_id = self.extract_tenant_id_from_crn(crn)
        return tenant_id

    def get_tenant_id_local(self):
        auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)

        cfg = Config()
        active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)

        existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(active_env, {})

        existing_token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None

        token = jwt.decode(existing_token, options={"verify_signature": False})
        tenant_id = ""
        tenant_id = token.get('woTenantId', None)

        return tenant_id
    
    def get_crn(self) -> str | None:
        """
        Retrieves the CRN for the active IBM Cloud environment.
        If the CRN is already stored in the configuration it is returned directly.
        Otherwise it is fetched from the IBM Cloud Resource Controller API using the
        stored bearer token and written back to the config.
        """
        try:
            # Load the main configuration and determine the active environment
            cfg = Config()
            active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
            env_cfg: dict = cfg.get(ENVIRONMENTS_SECTION_HEADER).get(active_env, {})
            if not env_cfg or not is_ibm_cloud_platform(env_cfg.get(ENV_WXO_URL_OPT)):
                return None

            # Return the CRN if it is already present in the environment config
            crn = env_cfg.get(ENV_CRN_OPT)
            if crn:
                return crn

            # Retrieve the stored bearer token from the auth config
            auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)
            auth_section = auth_cfg.get(AUTH_SECTION_HEADER) or {}
            env_auth = auth_section.get(active_env, {})
            token = env_auth.get(AUTH_MCSP_TOKEN_OPT)
            if not token:
                logger.error("No bearer token found for the active environment.")
                return None

            # Extract the instance ID from the wxo URL
            wxo_url = env_cfg.get(ENV_WXO_URL_OPT)
            if not wxo_url:
                logger.error("Missing wxo URL in environment configuration.")
                return None
            parsed_url = urlparse(wxo_url)
            instance_id = parsed_url.path.rstrip("/").split("/")[-1]

            # Fetch CRN from IBM Cloud Resource Controller API
            rc_url = f"https://resource-controller.cloud.ibm.com/v2/resource_instances/{instance_id}"
            headers = {"authorization": f"Bearer {token}"}
            response = requests.get(rc_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            crn = data.get("id")
            if not crn or not crn.startswith("crn:v1:bluemix:public:watsonx-orchestrate"):
                logger.error("Fetched ID is not a valid Watsonx Orchestrate CRN.")
                return None

            # Persist CRN in config file
            env_cfg["crn"] = crn
            cfg.write(ENVIRONMENTS_SECTION_HEADER, active_env, env_cfg)

            return crn
        except Exception as exc:
            logger.error(f"Error retrieving CRN: {exc}")
            return None

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
        crn = None
        environment = get_environment()

        match (environment):
            case RuntimeEnvironmentType.LOCAL:
                tenant_id = self.get_tenant_id_local()

            case RuntimeEnvironmentType.CPD:
                tenant_id = get_cpd_instance_id_from_url()

            case RuntimeEnvironmentType.IBM_CLOUD:
                crn = self.get_crn() # TODO: automatically get CRN from wxO URL
                if crn is None:
                    logger.warning("Could not get CRN automatically")
                    crn = input("Please enter your CRN which can be retrieved from the IBM Cloud UI: ")
                if crn == "":
                    logger.error("You must enter your CRN for IBM Cloud instances")
                    sys.exit(1)
                is_crn_correct = self.check_crn_is_correct(crn)
                if is_crn_correct == False:
                    logger.error("Invalid CRN format provided.")
                    sys.exit(1)
                tenant_id = self.extract_tenant_id_from_crn(crn)

            case RuntimeEnvironmentType.AWS:
                tenant_id = self.get_tenant_id()

            case _:
                logger.error("Environment not recognized")
                sys.exit(1)

        host_url = self.get_host_url()
        agent_id = self.get_agent_id(self.agent_name)
        agent_env_id = self.get_environment_id(self.agent_name, self.env)

        script_path = (
            "/wxoLoader.js?embed=true"
            if environment == "local"
            else "/wxochat/wxoLoader.js?embed=true"
        )

        config_lines = [
            f'orchestrationID: "{tenant_id}"',
            f'hostURL: "{host_url}"',
            'rootElementID: "root"',
            'showLauncher: true',
        ]

        # Conditional fields for IBM Cloud
        if environment == "ibmcloud":
            config_lines.append(f'crn: "{crn}"')
            config_lines.append(f'deploymentPlatform: "ibmcloud"')

        config_lines.append(f"""chatOptions: {{
            agentId: "{agent_id}",
            agentEnvironmentId: "{agent_env_id}"
        }}""")

        config_body = ",\n                    ".join(config_lines)

        script = f"""
            <script>
                window.wxOConfiguration = {{
                    {config_body}
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

