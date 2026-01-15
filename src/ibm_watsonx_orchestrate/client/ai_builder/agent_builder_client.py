from ibm_watsonx_orchestrate.client.base_api_client import BaseWXOClient


class AgentBuilderClient(BaseWXOClient):
    """
    Client to handle CRUD operations for Conversational Prompt Engineering Service
    """

    def __init__(self, *args, **kwargs):
        self.chat_id = None
        super().__init__(*args, **kwargs)
        self.base_url = kwargs.get("base_url", self.base_url)

    def _get_headers(self) -> dict:
        headers = super()._get_headers()
        headers["chat_id"] = self.chat_id

        return headers

    def _get_chat_model_name_or_default(self, chat_nodel_name):
        if chat_nodel_name:
            return chat_nodel_name
        return 'watsonx/meta-llama/llama-3-3-70b-instruct'

    def submit_chat(self, chat_llm: str |None, user_message: str | None = None,
                                         agent_id:str | None = None) -> dict:

        payload = {
           "thread_id": self.chat_id,
            "agent_id":agent_id,
            "message": {
              "role": "user",
              "content": user_message,
             "additional_properties": {}
            },
            "context": {},
            "additional_parameters":{
                "llm_model_id": chat_llm,
                "run_mode": "CLI"
            }
          }


        response = self._post_nd_json("/v1/orchestrate/agent/architect/runs?stream=true&multiple_content=false", data=payload)
        response_content = [x for x in response if 'event' in x and x['event'] == 'message.created'][0]['data']
        self.chat_id = response_content['thread_id']
        return {'conversation_state':
                   response_content['message']['additional_properties']['architect_conversational_state'],
                   'formatted_message': response_content['message'],
                    'agent_id':response_content['agent_id'] if 'agent_id' in response_content and response_content['agent_id'] != '' else None,
               }


    def healthcheck(self):
        self._get("/v1/health/ready")