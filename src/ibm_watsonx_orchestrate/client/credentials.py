#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from __future__ import annotations

import os
from typing import Any


class Credentials:
    """This class encapsulate passed credentials and additional params.

    :param url: URL of the service
    :type url: str

    :param api_key: service API key used in API key authentication
    :type api_key: str, optional

    :param token: service token, used in token authentication
    :type token: str, optional

    :param verify: certificate verification flag
    :type verify: bool, optional
    """

    def __init__(
            self,
            *,
            url: str | None = None,
            iam_url: str | None = None,
            api_key: str | None = None,
            username: str | None = None,
            password: str | None = None,
            token: str | None = None,
            verify: str | bool | None = None,
            auth_type: str | None = None,
    ) -> None:
        env_credentials = Credentials._get_values_from_env_vars()
        self.url = url
        self.iam_url = iam_url
        self.api_key = api_key
        self.username = username
        self.password = password
        self.token = token
        self.local_global_token = None
        self.verify = verify
        self.auth_type = auth_type
        self._is_env_token = token is None and "token" in env_credentials

        for k, v in env_credentials.items():
            if self.__dict__.get(k) is None:
                self.__dict__[k] = v

    @staticmethod
    def from_dict(dict: dict) -> Credentials:
        creds = Credentials()
        for k, v in dict.items():
            setattr(creds, k, v)

        return creds

    @staticmethod
    def _get_values_from_env_vars() -> dict[str, Any]:
        def get_value_from_file(filename: str) -> str:
            with open(filename, "r") as f:
                return f.read()

        def get_verify_value(x: str) -> bool | str:
            if x in ["True", "False"]:
                return x == "True"
            else:
                return x

        env_vars_mapping = {
            "WXO_CLIENT_VERIFY_REQUESTS": lambda x: ("verify", get_verify_value(x)),
            "USER_ACCESS_TOKEN": lambda x: ("token", x.replace("Bearer ", "")),
            "RUNTIME_ENV_ACCESS_TOKEN_FILE": lambda x: (
                "token",
                get_value_from_file(x).replace("Bearer ", ""),
            ),
            "WXO_URL": lambda x: ("url", x),
        }

        return dict(
            [
                f(os.environ[k])
                for k, f in env_vars_mapping.items()
                if os.environ.get(k) is not None and os.environ.get(k) != ""
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        """Get dictionary from the Credentials object.

        :return: dictionary with credentials
        :rtype: dict

        **Example**

        .. code-block:: python

            from ibm_watsonx_orchestrate import Credentials

            credentials = Credentials.from_dict({
                'url': "<url>",
                'apikey': "<api_key>"
            })

            credentials_dict = credentials.to_dict()

        """
        data = dict(
            [
                (k, v)
                for k, v in self.__dict__.items()
                if v is not None and not k.startswith("_")
            ]
        )
        return data

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any | None = None) -> Any:
        return self.to_dict().get(key, default)