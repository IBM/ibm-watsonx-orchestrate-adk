from enum import Enum

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
import requests

class Plan(str, Enum):
    HDHP = 'HDHP'
    HDHP_Plus = 'HDHP Plus'
    PPO = 'PPO'


@tool
def get_healthcare_benefits(plan: Plan, in_network: bool | None = None):
    """
    Retrieve a comprehensive list of health benefits data, organized by coverage type and plan variant.
    This data outlines details such as annual deductibles, out-of-pocket maximums, and various co-pays
    or percentages for medical services under different network plans (HDHP, HDHP Plus, and PPO).

    :param plan: Which plan the user is currently on, can be one of "HDHP", "HDHP Plus", or "PPO". If not provided all plans will be returned.
    :param in_network: Whether the user wants coverage for in network or out of network. If not provided both will be returned.
    :returns: A list of dictionaries, where each dictionary contains:
              - 'Coverage': A description of the coverage type (e.g., 'Preventive Services')
              - 'HDHP (In-Network)': The cost/percentage coverage for an in-network HDHP plan
              - 'HDHP (Out-of-Network)': The cost/percentage coverage for an out-of-network HDHP plan
              - 'HDHP Plus (In-Network)': The cost/percentage coverage for an in-network HDHP Plus plan
              - 'HDHP Plus (Out-of-Network)': The cost/percentage coverage for an out-of-network HDHP Plus plan
              - 'PPO (In-Network)': The cost/percentage coverage for an in-network PPO plan
              - 'PPO (Out-of-Network)': The cost/percentage coverage for an out-of-network PPO plan
    """
    resp = requests.get(
        'https://get-benefits-data.1sqnxi8zv3dh.us-east.codeengine.appdomain.cloud/',
        params={
            'plan': plan,
            'in_network': in_network
        }
    )
    resp.raise_for_status()
    return resp.json()['benefits']