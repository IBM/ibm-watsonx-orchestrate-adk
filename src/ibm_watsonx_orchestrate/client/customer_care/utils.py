from ibm_watsonx_orchestrate_clients.customer_care.customer_care_config_client import (
    CustomerCareConfigClient,
)
from ibm_watsonx_orchestrate_clients.common.utils import instantiate_client


def get_customer_care_config_client() -> CustomerCareConfigClient:
    return instantiate_client(client=CustomerCareConfigClient)
