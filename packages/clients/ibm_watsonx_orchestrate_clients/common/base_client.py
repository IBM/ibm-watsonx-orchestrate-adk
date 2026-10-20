import json
import os
import requests
import warnings
from abc import abstractmethod
from contextlib import contextmanager

from typing_extensions import List
from ibm_cloud_sdk_core.authenticators import Authenticator
from urllib3.exceptions import InsecureRequestWarning

from ibm_watsonx_orchestrate_core.utils.exceptions import BadRequest

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
        if self.response is None:
            return f"ClientAPIException(message={requests.HTTPError.__str__(self)!r})"
        status = self.response.status_code
        resp = self.response.text
        try:
            resp = json.dumps(resp).get('detail', None)
        except:
            pass
        return f"ClientAPIException(status_code={status}, message={resp})"

    def __str__(self):
        return self.__repr__()


class ResourceQuotaExceededError(ClientAPIException):
    """A persistent tenant resource quota rejected a create operation."""

    def __init__(self, *, request, response, detail: dict, body: dict):
        """Initialize the error from a structured resource-quota response."""
        super().__init__(request=request, response=response)
        self.resource = detail.get("resource")
        self.current = detail.get("current")
        self.requested = detail.get("requested")
        self.limit = detail.get("limit")
        self.quota_message = detail.get("message") or "Tenant resource quota exceeded."
        self.status_code = response.status_code
        self.original_body = body

    def __repr__(self):
        """Return a detailed representation of the quota error."""
        return (
            "ResourceQuotaExceededError("
            f"status_code={self.status_code}, resource={self.resource!r}, "
            f"current={self.current!r}, requested={self.requested!r}, "
            f"limit={self.limit!r}, message={self.quota_message!r})"
        )

    def __str__(self):
        """Return the human-readable quota message."""
        return self.quota_message


def _response_json(response: requests.Response) -> dict | None:
    """Return a JSON object response, or ``None`` when one is unavailable."""
    try:
        body = response.json()
    except (ValueError, TypeError):
        return None
    return body if isinstance(body, dict) else None


def format_client_api_error(error: ClientAPIException) -> str:
    """Return a safe, readable CLI message for a client HTTP failure."""
    if isinstance(error, ResourceQuotaExceededError):
        return (
            f"{error.quota_message} "
            f"[resource={error.resource}, current={error.current}, "
            f"requested={error.requested}, limit={error.limit}]"
        )

    response = getattr(error, "response", None)
    if response is None:
        return requests.HTTPError.__str__(error)

    body = _response_json(response)
    if body is not None:
        detail = body.get("detail")
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("code")
            return str(message) if message else str(detail)
        if detail is not None:
            return str(detail)
        for key in ("message", "error"):
            if body.get(key) is not None:
                return str(body[key])
    return response.text or str(error)


class BaseAPIClient:
    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False, verify: str = None, authenticator: Authenticator = None):
        self.base_url = base_url.rstrip("/")  # remove trailing slash
        self.api_key = api_key
        self.authenticator = authenticator
        self.verify = verify
        self._session = requests.Session()

    def _is_debug_mode(self) -> bool:
        log_level = str(os.environ.get("LOG_LEVEL") or "").strip().lower()
        return log_level == "debug"

    def _should_suppress_insecure_request_warning(self) -> bool:
        return self.verify is False and not self._is_debug_mode()

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"

        request_kwargs = {
            "headers": self._get_headers(),
            "verify": self.verify,
            **kwargs,
        }

        with ssl_handler():
            if self._should_suppress_insecure_request_warning():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", InsecureRequestWarning)
                    return self._session.request(method, url, **request_kwargs)
            return self._session.request(method, url, **request_kwargs)

    def _get_headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.authenticator:
            headers["Authorization"] = f"Bearer {self.authenticator.token_manager.get_token()}"
        return headers

    def _get(self, path: str, params: dict = None, data=None, return_raw=False) -> dict:
        response = self._request("GET", path, params=params, data=data)
        self._check_response(response)
        if not return_raw:
            return response.json()
        else:
            return response

    def _post(self, path: str, data: dict = None, files: dict = None) -> dict:
        response = self._request("POST", path, json=data, files=files)
        self._check_response(response)
        return response.json() if response.text else {}
    
    def _post_nd_json(self, path: str, data: dict = None, files: dict = None) -> List[dict]:
        response = self._request("POST", path, json=data, files=files)
        self._check_response(response)

        res = []
        if response.text:
            for line in response.text.splitlines():
                res.append(json.loads(line))
        return res
    
    def _post_form_data(self, path: str, data: dict = None, files: dict = None) -> dict:
        response = self._request("POST", path, data=data, files=files)
        self._check_response(response)
        return response.json() if response.text else {}

    def _put(self, path: str, data: dict = None) -> dict:
        response = self._request("PUT", path, json=data)
        self._check_response(response)
        return response.json() if response.text else {}

    def _patch(self, path: str, data: dict = None) -> dict:
        response = self._request("PATCH", path, json=data)
        self._check_response(response)
        return response.json() if response.text else {}
    
    def _patch_form_data(self, path: str, data: dict = None, files = None) -> dict:
        response = self._request("PATCH", path, data=data, files=files)
        self._check_response(response)
        return response.json() if response.text else {}

    def _delete(self, path: str, data=None) -> dict:
        response = self._request("DELETE", path, json=data)
        self._check_response(response)
        return response.json() if response.text else {}

    def _check_response(self, response: requests.Response):
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            body = _response_json(e.response)
            detail = body.get("detail") if body is not None else None
            if (
                e.response.status_code == 429
                and isinstance(detail, dict)
                and detail.get("code") == "RESOURCE_QUOTA_EXCEEDED"
            ):
                raise ResourceQuotaExceededError(
                    request=e.request,
                    response=e.response,
                    detail=detail,
                    body=body,
                ) from e
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
    

class BaseWXOClient(BaseAPIClient):
    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False, verify: str = None, authenticator: Authenticator = None):
        super().__init__(base_url=base_url, api_key=api_key, verify=verify, authenticator=authenticator) 
        
        self.is_local = is_local       
        
        if not self.is_local:
            self.base_url = f"{self.base_url}/v1/orchestrate"
        else:
            self.base_url = f"{self.base_url}/v1"
            
