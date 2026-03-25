import uuid

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.agent_builder.tools import tool


class PatientInfo(BaseModel):
    patient_name: str = Field(..., description="Patient full name")
    patient_dob: str = Field(..., description="Patient date of birth (YYYY-MM-DD)")
    relationship: str = Field(..., description="Reporter relationship to patient (self, parent, spouse, etc.)")
    contact_phone: str = Field(..., description="Best contact phone number")
    contact_email: str = Field(..., description="Best contact email")


class ConcernDetails(BaseModel):
    concern_type: str = Field(..., description="Type of concern (care_quality, billing, wait_time, staff, other)")
    location: str = Field(..., description="Hospital location or department")
    date_of_incident: str = Field(..., description="Date of incident (YYYY-MM-DD)")
    description: str = Field(..., description="Detailed description of the concern")
    escalated: bool = Field(..., description="Whether the concern should be escalated")
    user_body: str = Field(..., description="Additional user-written details to attach")


@tool(description="Create a patient/family concern support ticket for St. Mary's Group of Hospitals.")
def create_patient_support_ticket(patient: PatientInfo, concern: ConcernDetails) -> str:
    """
    Create a support ticket for patient/family concerns.

    Args:
        patient: Patient and reporter contact details
        concern: Concern details

    Returns:
        A confirmation with a support ticket ID
    """
    support_id = f"SMH-{uuid.uuid4().hex[:10].upper()}"
    return (
        "Support ticket created successfully.\n"
        f"Support ID: {support_id}\n"
        f"Patient: {patient.patient_name} (DOB: {patient.patient_dob})\n"
        f"Relationship: {patient.relationship}\n"
        f"Contact: {patient.contact_phone} | {patient.contact_email}\n"
        f"Concern Type: {concern.concern_type}\n"
        f"Location/Dept: {concern.location}\n"
        f"Date of Incident: {concern.date_of_incident}\n"
        f"Description: {concern.description}\n"
        f"Escalated: {'Yes' if concern.escalated else 'No'}\n"
        f"User Body: {concern.user_body}"
    )
