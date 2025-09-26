import logging
import rich
import jwt
import getpass
import sys

from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.cli.config import (
    Config,
    AUTH_CONFIG_FILE_FOLDER,
    AUTH_CONFIG_FILE,
    AUTH_SECTION_HEADER,
    AUTH_MCSP_TOKEN_OPT,
    AUTH_MCSP_TOKEN_EXPIRY_OPT,
    CONTEXT_ACTIVE_ENV_OPT,
    CONTEXT_SECTION_HEADER,
    ENV_WXO_URL_OPT,
    ENV_IAM_URL_OPT,
    ENVIRONMENTS_SECTION_HEADER,
    PROTECTED_ENV_NAME,
    ENV_AUTH_TYPE, PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT,
    BYPASS_SSL, VERIFY,
    DEFAULT_CONFIG_FILE_CONTENT, PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT
)
from ibm_watsonx_orchestrate.client.client import Client
from ibm_watsonx_orchestrate.client.client_errors import ClientError
from ibm_watsonx_orchestrate.client.knowledge_bases.knowledge_base_client import KnowledgeBaseClient, ClientAPIException
from ibm_watsonx_orchestrate.client.credentials import Credentials
from threading import Lock
from ibm_watsonx_orchestrate.client.utils import is_local_dev, check_token_validity, is_cpd_env
from ibm_watsonx_orchestrate.cli.commands.environment.types import EnvironmentAuthType

logger = logging.getLogger(__name__)

lock = Lock()

def _decode_token(token: str, is_local: bool = False) -> dict:
    try:
        claimset = jwt.decode(token, options={"verify_signature": False})
        data = {AUTH_MCSP_TOKEN_OPT: token}
        if not is_local:
            data[AUTH_MCSP_TOKEN_EXPIRY_OPT] = claimset["exp"]
        return data
    except jwt.DecodeError as e:
        logger.error("Invalid token format")
        raise e


def _validate_token_functionality(token: str, url: str) -> None:
    '''
    Validates a token by making a request to GET /agents

    Args: 
        token: A JWT token
        url: WXO instance URL
    '''
    is_cpd = is_cpd_env(url)
    if is_cpd is True:
        knowledge_base_client = KnowledgeBaseClient(base_url=url, api_key=token, is_local=is_local_dev(url), verify=False)
    else:
        knowledge_base_client = KnowledgeBaseClient(base_url=url, api_key=token, is_local=is_local_dev(url))
    knowledge_base_client.api_key = token

    try:
        knowledge_base_client.get()
    except ClientAPIException as e:
        if e.response.status_code >= 400:
            reason = e.response.reason
            logger.error(f"Failed to authenticate to provided instance '{url}'. Reason: '{reason}'. Please ensure provider URL and API key are valid.")
            sys.exit(1)
        raise e


def _login(name: str, apikey: str = None, username: str = None, password: str = None) -> None:
    cfg = Config()
    auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)

    env_cfg = cfg.get(ENVIRONMENTS_SECTION_HEADER, name)
    url = env_cfg.get(ENV_WXO_URL_OPT)
    iam_url = env_cfg.get(ENV_IAM_URL_OPT)
    is_local = name == PROTECTED_ENV_NAME or is_local_dev(url=url)
    try:
        auth_type = cfg.get(ENVIRONMENTS_SECTION_HEADER, name, ENV_AUTH_TYPE)
    except (KeyError, AttributeError):
        auth_type = None

    username = username
    apikey = apikey
    password = password

    if is_cpd_env(url):
        if username is None:
            username = getpass.getpass("Please enter CPD Username: ")

        if not apikey and not password:
            apikey = getpass.getpass("Enter CPD API key (or leave blank to use password): ")
        if not apikey and not password:
            password = getpass.getpass("Enter CPD password (or leave blank if you used API key): ")

        if apikey and password:
            logger.error("For CPD, please use either an Apikey or a Password but not both.")
            sys.exit(1)

        if not apikey and not password:
            logger.error("For CPD, you must provide either an API key or a password.")
            sys.exit(1)
    

    if not apikey and not password and not is_local and auth_type != "cpd":
        apikey = getpass.getpass("Please enter WXO API key: ")

    try:
        creds = Credentials(
            url=url, 
            api_key=apikey, 
            username=username, 
            password=password, 
            iam_url=iam_url, 
            auth_type=auth_type
        )
        client = Client(creds)
        token = _decode_token(client.token, is_local)
        _validate_token_functionality(token=token.get(AUTH_MCSP_TOKEN_OPT), url=url)
        with lock:
            auth_cfg.save(
                {
                    AUTH_SECTION_HEADER: {
                        name: token
                    },
                }
            )
    except ClientError as e:
        raise ClientError(e)

def activate(name: str, apikey: str=None, username: str=None, password: str=None, registry: RegistryType=None, test_package_version_override=None, skip_version_check=None) -> None:
    cfg = Config()
    auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)
    env_cfg = cfg.read(ENVIRONMENTS_SECTION_HEADER, name)
    url = cfg.get(ENVIRONMENTS_SECTION_HEADER, name, ENV_WXO_URL_OPT)
    is_local = is_local_dev(url)

    if not env_cfg:
        logger.error(f"Environment '{name}' does not exist. Please create it with `orchestrate env add`")
        return
    elif not env_cfg.get(ENV_WXO_URL_OPT):
        logger.error(f"Environment '{name}' is misconfigured. Please re-create it with `orchestrate env add`")
        return

    existing_auth_config = auth_cfg.get(AUTH_SECTION_HEADER).get(name, {})
    existing_token = existing_auth_config.get(AUTH_MCSP_TOKEN_OPT) if existing_auth_config else None

    if not check_token_validity(existing_token) or is_local:
        _login(name=name, apikey=apikey, username=username, password=password)

    with lock:
        cfg.write(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, name)
        if registry is not None:
            cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, str(registry))
            cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT, test_package_version_override)
        elif cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT) is None:
            cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, DEFAULT_CONFIG_FILE_CONTENT[PYTHON_REGISTRY_HEADER][PYTHON_REGISTRY_TYPE_OPT])
            cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT, test_package_version_override)
        if skip_version_check is not None:
            cfg.write(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT, skip_version_check)

    logger.info(f"Environment '{name}' is now active")
    is_cpd = is_cpd_env(url)
    if is_cpd:
        logger.warning("Support for CPD clusters is currently an early access preview")

def add(name: str, url: str, should_activate: bool=False, iam_url: str=None, type: EnvironmentAuthType=None, insecure: bool=None, verify: str=None) -> None:
    if name == PROTECTED_ENV_NAME:
        logger.error(f"The name '{PROTECTED_ENV_NAME}' is a reserved environment name. Please select a different name or use `orchestrate env activate {PROTECTED_ENV_NAME}` to swap to '{PROTECTED_ENV_NAME}'")
        return

    cfg = Config()
    existing_env_cfg = cfg.read(ENVIRONMENTS_SECTION_HEADER, name)
    if existing_env_cfg:
        logger.info(f"Existing environment with name '{name}' found.")
        update_response = input(f"Would you like to update the environment '{name}'? (Y/n)")
        if update_response.lower() == "n":
            logger.info(f"No changes made to environments")
            return
    with lock:
        cfg.write(ENVIRONMENTS_SECTION_HEADER, name, {ENV_WXO_URL_OPT: url})
        if iam_url:
            cfg.write(ENVIRONMENTS_SECTION_HEADER, name, {ENV_IAM_URL_OPT: iam_url})
        if type:
            cfg.write(ENVIRONMENTS_SECTION_HEADER, name, {ENV_AUTH_TYPE: str(type)})
        if insecure:
            cfg.write(ENVIRONMENTS_SECTION_HEADER, name, {BYPASS_SSL: insecure})
            cfg.write(ENVIRONMENTS_SECTION_HEADER, name, {VERIFY: 'None'})
        if verify:
            cfg.write(ENVIRONMENTS_SECTION_HEADER, name, {VERIFY: verify})
            cfg.write(ENVIRONMENTS_SECTION_HEADER, name, {BYPASS_SSL: False})
        

    logger.info(f"Environment '{name}' has been created")
    if should_activate:
        activate(name)

def remove(name: str) -> None:
    if name == PROTECTED_ENV_NAME:
        logger.error(f"The environment '{PROTECTED_ENV_NAME}' is a default environment and cannot be removed.")
        return

    cfg = Config()
    auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)
    active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
    existing_env_cfg = cfg.read(ENVIRONMENTS_SECTION_HEADER, name)
    existing_auth_env_cfg = auth_cfg.read(AUTH_SECTION_HEADER, name)

    if not existing_env_cfg:
        logger.info(f"No environment named '{name}' exists")
        return

    if name == active_env:
        remove_confirmation = input(f"The environment '{name}' is currently active, are you sure you wish to remove it? (y/N)")
        if remove_confirmation.lower() != 'y':
            logger.info("No changes made to environments")
            return
        cfg.write(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT, None)

    cfg.delete(ENVIRONMENTS_SECTION_HEADER, name)
    if existing_auth_env_cfg:
        auth_cfg.delete(AUTH_SECTION_HEADER, name)
    logger.info(f"Successfully removed environment '{name}'")

def list_envs() -> None:
    cfg = Config()
    active_env = cfg.read(CONTEXT_SECTION_HEADER, CONTEXT_ACTIVE_ENV_OPT)
    envs = cfg.get(ENVIRONMENTS_SECTION_HEADER)

    table = rich.table.Table(
        show_header=False,
        box=None
    )
    columns = ["Environment", "Url", ""]
    for col in columns:
        table.add_column(col)

    # Make order active first followed alphabetically
    env_names = []
    if active_env:
        env_names.append(active_env)
    else:
        logger.warning("No active environment is currently set. Use `orchestrate env activate` to set one")
    envs_keys = list(envs.keys())
    if active_env in envs_keys: envs_keys.remove(active_env)
    envs_keys.sort()
    env_names += envs_keys

    for env in env_names:
        active_tag = "[green](active)[/green]" if env == active_env else ""
        table.add_row(env, envs.get(env, {}).get(ENV_WXO_URL_OPT, "N/A"), active_tag)
    
    console = rich.console.Console()
    console.print(table)