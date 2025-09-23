from typing import Optional, List
from ibm_watsonx_orchestrate.client.connections.connections_client import ConnectionsClient, ListConfigsResponse
from ibm_watsonx_orchestrate.client.connections.utils import get_connections_client
from ibm_watsonx_orchestrate_mcp_server.utils.common import silent_call

class ConnectionsHelper:
    def __init__(self, connnections_client: Optional[ConnectionsClient] = None):
        self.connections_client: ConnectionsClient | None = connnections_client
    
    def __get_connections_client(self) -> ConnectionsClient:
        if self.connections_client:
            return self.connections_client
        else:
            return silent_call(fn=get_connections_client)
    
    def get_connection_by_id(self, connection_id: str) -> ListConfigsResponse | None:
        connections_client: ConnectionsClient = self.__get_connections_client()

        connections: List[ListConfigsResponse]= silent_call(fn=connections_client.get_drafts_by_ids, conn_ids=[connection_id])

        if len(connections) == 0:
            return None
        if len(connections) > 1:
            raise Exception(f"Multiple connections found with id '{connection_id}'.")
        return connections[0]

    def get_app_id_by_connection_id(self, connection_id: str) -> str | None:
        connection: ListConfigsResponse | None = self.get_connection_by_id(connection_id)
        if not connection:
            return None
        return connection.app_id