import copy
import logging
from typing import Any, cast

from ibm_watsonx_orchestrate.client.client_errors import NoCredentialsProvided, ClientError
from ibm_watsonx_orchestrate.client.credentials import Credentials
from ibm_watsonx_orchestrate.client.service_instance import ServiceInstance
from ibm_watsonx_orchestrate.client.local_service_instance import LocalServiceInstance
from ibm_watsonx_orchestrate.client.utils import is_local_dev


class Client:
    """The main class of ibm_watsonx_orchestrate. The very heart of the module. Client contains objects that manage the service reasources.

    To explore how to use Client, refer to:
     - :ref:`Setup<setup>` - to check correct initialization of Client for a specific environment.
     - :ref:`Core<core>` - to explore core properties of an Client object.

    :param url: URL of the service
    :type url: str

    :param credentials: credentials used to connect with the service
    :type credentials: Credentials

    **Example**

    .. code-block:: python

        from ibm_watsonx_orchestrate import Client, Credentials

        credentials = Credentials(
            url = "<url>",
            api_key = "<api_key>"
        )

        client = Client(credentials, space_id="<space_id>")

        client.models.list()
        client.deployments.get_details()

        client.set.default_project("<project_id>")

        ...

    """

    def __init__(
        self,
        credentials: Credentials | None = None,
        **kwargs: Any,
    ) -> None:
        if credentials is None:
            raise TypeError("Client() missing 1 required argument: 'credentials'")

        self.credentials = copy.deepcopy(credentials)

        self.token: str | None = None
        if credentials is None:
            raise NoCredentialsProvided()
        if self.credentials.url is None:
            raise ClientError("No URL Provided")
        if not self.credentials.url.startswith("https://"):
            if not is_local_dev(self.credentials.url):
                raise ClientError("Invalid URL Format. URL must start stil 'https://'")
        if self.credentials.url[-1] == "/":
            self.credentials.url = self.credentials.url.rstrip("/")

        if not is_local_dev(self.credentials.url):
            self.service_instance: ServiceInstance = ServiceInstance(self)
        else:
            self.service_instance: LocalServiceInstance = LocalServiceInstance(self)
