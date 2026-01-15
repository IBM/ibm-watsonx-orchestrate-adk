
from ibm_watsonx_orchestrate.client.langflow.langflow_base_client import BaseLangflowClient


class LangflowFlowsClient(BaseLangflowClient):
  def __init__(self,*args,**kwargs):
    super().__init__(*args, **kwargs)

  # POST /v1/flows/                       |   Create a flow
  def create(self, data):
    return self._post("/v1/flows/", self.base_url, data=data)
    
  # GET /v1/flows/                        |   List flows (supports pagination and filters)
  def get(self):
    return self._get("/v1/flows/?remove_example_flows=true")

  # GET /v1/flows/{flow_id}               |   Read a flow by ID.
  def get_flow_by_id(self, flow_id: str):
    return self._get(f"/v1/flows/{flow_id}")

  # PATCH /v1/flows/{flow_id}             |   Update a flow.
  def update(self, flow_id: str, data: dict):
    return self._patch(f"/v1/flows/{flow_id}", data=data)
  
  # DELETE /v1/flows/{flow_id}            |   Delete a flow.
  def delete(self, flow_id: str):
    return self._delete(f"/v1/flows/{flow_id}")


  ##  Other available endpoints  ##

  # GET /v1/flows/public_flow/{flow_id}   |   Read a public flow by ID.
  # POST /v1/flows/batch/                 |   Create multiple flows.
  # POST /v1/flows/upload/                |   Import flows from a JSON file.
  # DELETE /v1/flows/                     |   Delete multiple flows by IDs.
  # POST /v1/flows/download/              |   Export flows to a ZIP file.
  # GET /v1/flows/basic_examples/         |   List basic example flows.
