import json

import requests
from abc import ABC, abstractmethod
from ibm_cloud_sdk_core.authenticators import MCSPAuthenticator


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
    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False, verify: str = None, authenticator: MCSPAuthenticator = None):
        self.base_url = base_url.rstrip("/")  # remove trailing slash
        self.api_key = api_key
        self.authenticator = authenticator

        # api path can be re-written by api proxy when deployed
        # TO-DO: re-visit this when shipping to production
        self.is_local = is_local
        self.verify = verify

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

    def _get(self, path: str, params: dict = None, data=None, return_raw=False) -> dict:
        url = f"{self.base_url}{path}"
        response = requests.get(url, headers=self._get_headers(), params=params, data=data, verify=self.verify)
        self._check_response(response)
        if not return_raw:
            return response.json()
        else:
            return response

    def _post(self, path: str, data: dict = None, files: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        response = requests.post(url, headers=self._get_headers(), json=data, files=files, verify=self.verify)
        self._check_response(response)
        return response.json() if response.text else {}
    
    def _post_form_data(self, path: str, data: dict = None, files: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        # Use data argument instead of json so data is encoded as application/x-www-form-urlencoded
        response = requests.post(url, headers=self._get_headers(), data=data, files=files, verify=self.verify)
        self._check_response(response)
        return response.json() if response.text else {}

    def _put(self, path: str, data: dict = None) -> dict:

        url = f"{self.base_url}{path}"
        response = requests.put(url, headers=self._get_headers(), json=data, verify=self.verify)
        self._check_response(response)
        return response.json() if response.text else {}

    def _patch(self, path: str, data: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        response = requests.patch(url, headers=self._get_headers(), json=data, verify=self.verify)
        self._check_response(response)
        return response.json() if response.text else {}
    
    def _patch_form_data(self, path: str, data: dict = None, files = None) -> dict:
        url = f"{self.base_url}{path}"
        response = requests.patch(url, headers=self._get_headers(), data=data, files=files, verify=self.verify)
        self._check_response(response)
        return response.json() if response.text else {}

    def _delete(self, path: str, data=None) -> dict:
        url = f"{self.base_url}{path}"
        response = requests.delete(url, headers=self._get_headers(), json=data, verify=self.verify)
        self._check_response(response)
        return response.json() if response.text else {}

    def _check_response(self, response: requests.Response):
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
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