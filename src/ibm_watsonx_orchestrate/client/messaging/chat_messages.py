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


class ChatMessages(WXOResource):
    """Work with messages created in AI Agent's chat"""

    def __init__(self, client: Client) -> None:
        WXOResource.__init__(self, __name__, client)

    def get_messages_in_thread(self, thread_id: str | None = None, **kwargs: Any) -> List:
        """Get list of message pertaining to a thread.

        :param thread_id: unique ID of the thread
        :type thread_id: str

        :return:list of message pertaining to a thread.
        :rtype:
            - **list**

        **Example**

        .. code-block:: python

            script_details = client.chat_messages.get_messages_in_thread(thread_id)

        """

        url = (
            self._client.service_instance._href_definitions.get_messages_in_thread_href(
                thread_id
            )
        )

        response = requests.get(
            url,
            headers=self._client._get_headers(),
        )
        return self._handle_response(200, "Getting messages in a thread", response)
