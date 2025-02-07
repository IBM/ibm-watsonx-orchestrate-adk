import logging
import jwt
import getpass
from ibm_watsonx_orchestrate.cli.config import (
    Config,
    AUTH_CONFIG_FILE_FOLDER,
    AUTH_CONFIG_FILE,
    AUTH_SECTION_HEADER,
    AUTH_MCSP_TOKEN_OPT,
    APP_SECTION_HEADER,
    APP_WXO_URL_OPT,
)
from ibm_watsonx_orchestrate.client.client import Client
from ibm_watsonx_orchestrate.client.client_errors import ClientError
from ibm_watsonx_orchestrate.client.credentials import Credentials
from threading import Lock

logger = logging.getLogger(__name__)

lock = Lock()

def decode_token(token: str, is_local: bool = False) -> dict:
    try:
        claimset = jwt.decode(token, options={"verify_signature": False})
        data = {"token": token}
        if not is_local:
            data["expiry"] = claimset["exp"]
        return data
    except jwt.DecodeError as e:
        logger.error("Invalid token format")
        raise e


def login(url: str, apikey: str = None, is_local: bool = False, ) -> None:
    cfg = Config()
    auth_cfg = Config(AUTH_CONFIG_FILE_FOLDER, AUTH_CONFIG_FILE)

    if url is None:
        cfg_url = cfg.read(APP_SECTION_HEADER, APP_WXO_URL_OPT)
        url = input(
            "Please enter WXO API url %s:" % (f"[{cfg_url}]" if cfg_url else "")
        )
        if url.strip() == "" and cfg_url is not None:
            url = cfg_url

    if apikey is None and not is_local:
        apikey = getpass.getpass("Please enter WXO API key: ")

    try:
        creds = Credentials(url=url, api_key=apikey)
        client = Client(creds)
        token = decode_token(client.token, is_local)
        with lock:
            cfg.save(
                {
                    APP_SECTION_HEADER: {APP_WXO_URL_OPT: url},
                }
            )
            auth_cfg.save(
                {
                    AUTH_SECTION_HEADER: {
                        AUTH_MCSP_TOKEN_OPT: token,
                    },
                }
            )
        logger.info("Successfully Logged In")
    except ClientError as e:
        raise ClientError(e)
