from typing import List

import requests
from pydantic import BaseModel, Field
from enum import Enum

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


class ContactInformation(BaseModel):
    phone: str
    email: str


class HealthcareSpeciality(str, Enum):
    GENERAL_MEDICINE = 'General Medicine'
    CARDIOLOGY = 'Cardiology'
    PEDIATRICS = 'Pediatrics'
    ORTHOPEDICS = 'Orthopedics'
    ENT = 'Ear, Nose and Throat'
    MULTI_SPECIALTY = 'Multi-specialty'


class HealthcareProvider(BaseModel):
    provider_id: str = Field(None, description="The unique identifier of the provider")
    name: str = Field(None, description="The providers name")
    provider_type: str = Field(None, description="Type of provider, (e.g. Hospital, Clinic, Individual Practitioner)")
    specialty: HealthcareSpeciality = Field(None, description="Medical speciality, if applicable")
    address: str = Field(None, description="The address of the provider")
    contact: ContactInformation = Field(None, description="The contact information of the provider")


@tool
def search_healthcare_providers(
        location: str,
        specialty: HealthcareSpeciality = HealthcareSpeciality.GENERAL_MEDICINE
) -> List[HealthcareProvider]:
    """
    Retrieve a list of the nearest healthcare providers based on location and optional specialty. Infer the
    speciality of the location from the request.


    :param location: Geographic location to search providers in (city, state, zip code, etc.)
    :param specialty: (Optional) Medical specialty to filter providers by (Must be one of: "ENT", "General Medicine", "Cardiology", "Pediatrics", "Orthopedics", "Multi-specialty")

    :returns: A list of healthcare providers near a particular location for a given speciality
    """
    resp = requests.get(
        'https://find-provider.1sqnxi8zv3dh.us-east.codeengine.appdomain.cloud',
        params={
            'location': location,
            'speciality': specialty
        }
    )
    resp.raise_for_status()
    return resp.json()['providers']
