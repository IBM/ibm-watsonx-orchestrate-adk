import os
import json
import logging
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
import requests
from abc import ABC, abstractmethod
from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator
from typing_extensions import List
from contextlib import contextmanager
from ibm_watsonx_orchestrate.client.retry_handler import retry_with_backoff

logger = logging.getLogger(__name__)

@contextmanager
def ssl_handler():
    try:
        yield
    except requests.exceptions.SSLError as e:
        error_message = str(e)
        if "self-signed certificate in certificate chain" in error_message:
            reason = "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain"
        else:
            reason = error_message
        raise BadRequest(f"SSL handshake failed for request '{e.request.path_url}'. Reason: '{reason}'")


class ClientAPIException(requests.HTTPError):

    def __init__(self, *args, request=..., response=...):
        super().__init__(*args, request=request, response=response)

    def __repr__(self):
        status = self.response.status_code
        resp = self.response.text
        try:
            resp = json.dumps(resp).get('detail', None)
        except:
            pass
        return f"ClientAPIException(status_code={status}, message={resp})"

    def __str__(self):
        return self.__repr__()


class BaseAPIClient:
    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False, verify: str = None, authenticator: MCSPAuthenticator = None, max_retries: int = None, retry_interval: int = None, timeout: int = None):
        self.base_url = base_url.rstrip("/")  # remove trailing slash
        self.api_key = api_key
        self.authenticator = authenticator

        # api path can be re-written by api proxy when deployed
        # TO-DO: re-visit this when shipping to production
        self.is_local = is_local
        self.verify = verify
        
        # Retry and timeout configuration with environment variable support
        # Read from environment if not provided
        if max_retries is None:
            try:
                self.max_retries = int(os.environ.get('ADK_MAX_RETRIES', '3'))
            except ValueError:
                logger.warning(f"Invalid ADK_MAX_RETRIES value: {os.environ.get('ADK_MAX_RETRIES')}. Using default: 3")
                self.max_retries = 3
        else:
            self.max_retries = max_retries
            
        if retry_interval is None:
            try:
                self.retry_interval = int(os.environ.get('ADK_RETRY_INTERVAL', '1000'))
            except ValueError:
                logger.warning(f"Invalid ADK_RETRY_INTERVAL value: {os.environ.get('ADK_RETRY_INTERVAL')}. Using default: 1000")
                self.retry_interval = 1000
        else:
            self.retry_interval = retry_interval
            
        if timeout is None:
            try:
                self.timeout = int(os.environ.get('ADK_TIMEOUT', '300'))  # Default 5 minutes
            except ValueError:
                logger.warning(f"Invalid ADK_TIMEOUT value: {os.environ.get('ADK_TIMEOUT')}. Using default: 300")
                self.timeout = 300
        else:
            self.timeout = timeout

        if not self.is_local:
            self.base_url = f"{self.base_url}/v1/orchestrate"
        else:
            self.base_url = f"{self.base_url}/v1"

    def _get_headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.authenticator:
            headers["Authorization"] = f"Bearer {self.authenticator.token_manager.get_token()}"
        return headers

    @retry_with_backoff()
    def _get(self, path: str, params: dict = None, data=None, return_raw=False) -> dict:
        url = f"{self.base_url}{path}"
        logger.debug(f"GET {path}")
        with ssl_handler():
            response = requests.get(url, headers=self._get_headers(), params=params, data=data, verify=self.verify, timeout=self.timeout)
        self._check_response(response)
        if not return_raw:
            return response.json()
        else:
            return response

    @retry_with_backoff()
    def _post(self, path: str, data: dict = None, files: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        logger.debug(f"POST {path}")
        # Debug log payload for flow-related endpoints to aid formalization issues
        try:
            if isinstance(data, dict) and "/flows/" in path:
                sample_keys = list(data.keys())
                logger.info(f"POST payload keys for {path}: {sample_keys}")
        except Exception:
            pass
        with ssl_handler():
            response = requests.post(url, headers=self._get_headers(), json=data, files=files, verify=self.verify, timeout=self.timeout)
        self._check_response(response)
        # For flow runs, log top-level keys of response to verify mapping
        try:
            if "/flows/" in path and response.text:
                body = response.json()
                if isinstance(body, dict):
                    logger.info(f"Response keys for {path}: {list(body.keys())}")
        except Exception:
            pass
        return response.json() if response.text else {}
    
    @retry_with_backoff()
    def _post_nd_json(self, path: str, data: dict = None, files: dict = None) -> List[dict]:
        url = f"{self.base_url}{path}"
        logger.debug(f"POST (nd-json) {path}")
        with ssl_handler():
            response = requests.post(url, headers=self._get_headers(), json=data, files=files, timeout=self.timeout)
        self._check_response(response)

        res = []
        if response.text:
            for line in response.text.splitlines():
                res.append(json.loads(line))
        return res
    
    @retry_with_backoff()
    def _post_form_data(self, path: str, data: dict = None, files: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        logger.debug(f"POST (form-data) {path}")
        with ssl_handler():
            # Use data argument instead of json so data is encoded as application/x-www-form-urlencoded
            response = requests.post(url, headers=self._get_headers(), data=data, files=files, verify=self.verify, timeout=self.timeout)
        self._check_response(response)
        return response.json() if response.text else {}

    @retry_with_backoff()
    def _put(self, path: str, data: dict = None) -> dict:

        url = f"{self.base_url}{path}"
        logger.debug(f"PUT {path}")
        with ssl_handler():
            response = requests.put(url, headers=self._get_headers(), json=data, verify=self.verify, timeout=self.timeout)
        self._check_response(response)
        return response.json() if response.text else {}

    @retry_with_backoff()
    def _patch(self, path: str, data: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        logger.debug(f"PATCH {path}")
        with ssl_handler():
            response = requests.patch(url, headers=self._get_headers(), json=data, verify=self.verify, timeout=self.timeout)
        self._check_response(response)
        return response.json() if response.text else {}
    
    @retry_with_backoff()
    def _patch_form_data(self, path: str, data: dict = None, files = None) -> dict:
        url = f"{self.base_url}{path}"
        logger.debug(f"PATCH (form-data) {path}")
        with ssl_handler():
            response = requests.patch(url, headers=self._get_headers(), data=data, files=files, verify=self.verify, timeout=self.timeout)
        self._check_response(response)
        return response.json() if response.text else {}

    @retry_with_backoff()
    def _delete(self, path: str, data=None) -> dict:
        url = f"{self.base_url}{path}"
        logger.debug(f"DELETE {path}")
        with ssl_handler():
            response = requests.delete(url, headers=self._get_headers(), json=data, verify=self.verify, timeout=self.timeout)
        self._check_response(response)
        return response.json() if response.text else {}

    def _check_response(self, response: requests.Response):
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Log error details for debugging
            status_code = e.response.status_code
            error_body = e.response.text[:500] if e.response.text else "No response body"  # Truncate long responses
            logger.error(f"HTTP {status_code} error: {error_body}")
            raise ClientAPIException(request=e.request, response=e.response)

    @abstractmethod
    def create(self, *args, **kwargs):
        raise NotImplementedError("create method of the client must be implemented")

    @abstractmethod
    def delete(self, *args, **kwargs):
        raise NotImplementedError("delete method of the client must be implemented")

    @abstractmethod
    def update(self, *args, **kwargs):
        raise NotImplementedError("update method of the client must be implemented")

    @abstractmethod
    def get(self, *args, **kwargs):
        raise NotImplementedError("get method of the client must be implemented")