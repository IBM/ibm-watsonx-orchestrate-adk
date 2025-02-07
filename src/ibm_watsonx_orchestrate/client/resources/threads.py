#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

from __future__ import annotations
from typing import Any, TYPE_CHECKING, List

import ibm_watsonx_orchestrate.client._wrappers.requests as requests
from ibm_watsonx_orchestrate.client.resources.wxo_resource import WXOResource
from ibm_watsonx_orchestrate.client.client_errors import (
    ClientError,
    ApiRequestFailure,
    ForbiddenActionForGitBasedProject,
)


if TYPE_CHECKING:
    from ibm_watsonx_orchestrate.client import Client
    from pandas import DataFrame


class Threads(WXOResource):
    """Work with Threads in the AI Agent chat."""


    def __init__(self, client: Client) -> None:
        WXOResource.__init__(self, __name__, client)

    def list(self) -> List:
        """Get list of threads created by the current user

        :return: List of threads 
        :rtype:
            - **list** 

        **Example**

        .. code-block:: python

            messages = client.threads.list()

        """

        url = (
            self._client.service_instance._href_definitions.get_list_threads_href()
        )

        response = requests.get(
            url,
            headers=self._client._get_headers(),
        )
        return self._handle_response(200, "Getting messages in a thread", response)
