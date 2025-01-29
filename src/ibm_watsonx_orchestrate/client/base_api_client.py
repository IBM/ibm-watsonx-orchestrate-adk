import requests
from abc import ABC, abstractmethod


class BaseAPIClient:

    def __init__(self, base_url: str, api_key: str = None, is_local: bool = False):
        self.base_url = base_url.rstrip("/")  # remove trailing slash
        self.api_key = api_key

        # api path can be re-written by api proxy when deployed
        # TO-DO: re-visit this when shipping to production
        self.is_local = is_local

    def _get_headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get(self, path: str, params: dict = None) -> dict:

        url = f"{self.base_url}{path}"
        response = requests.get(url, headers=self._get_headers(), params=params)
        self._check_response(response)
        return response.json()

    def _post(self, path: str, data: dict = None, files: dict = None) -> dict:

        url = f"{self.base_url}{path}"
        response = requests.post(url, headers=self._get_headers(), json=data, files=files)
        self._check_response(response)
        return response.json() if response.text else {}

    def _put(self, path: str, data: dict = None) -> dict:

        url = f"{self.base_url}{path}"
        response = requests.put(url, headers=self._get_headers(), json=data)
        self._check_response(response)
        return response.json() if response.text else {}

    def _patch(self, path: str, data: dict = None) -> dict:

        url = f"{self.base_url}{path}"
        response = requests.patch(url, headers=self._get_headers(), json=data)
        self._check_response(response)
        return response.json() if response.text else {}

    def _delete(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        response = requests.delete(url, headers=self._get_headers())
        self._check_response(response)
        return response.json() if response.text else {}

    def _check_response(self, response: requests.Response):
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise e
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