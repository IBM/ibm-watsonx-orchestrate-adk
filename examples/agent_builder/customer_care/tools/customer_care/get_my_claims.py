from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool
def get_my_claims():
    """
    Retrieve detailed information about submitted claims including claim status, submission and processing dates,
    amounts claimed and approved, provider information, and services included in the claims.

    :returns: A list of dictionaries, each containing details about a specific claim:
              - 'claimId': Unique identifier for the claim
              - 'submittedDate': Date when the claim was submitted
              - 'claimStatus': Current status of the claim (e.g., 'Processed', 'Pending', 'Rejected')
              - 'processedDate': Date when the claim was processed (null if not processed yet)
              - 'amountClaimed': Total amount claimed
              - 'amountApproved': Amount approved for reimbursement (null if pending, 0 if rejected)
              - 'rejectionReason': Reason for rejection if applicable (only present if claimStatus is 'Rejected')
              - 'provider': Provider details, either as a simple string or a dictionary with detailed provider information
              - 'services': List of services included in the claim, each with:
                  - 'serviceId': Identifier for the service
                  - 'description': Description of the service provided
                  - 'dateOfService': Date the service was provided
                  - 'amount': Amount charged for the service
    """
    claims_data = [
        {
            "claimId": "CLM1234567",
            "claimStatus": "Processed",
            "amountClaimed": 150.00,
            "amountApproved": 120.00,
            "provider": {
                "name": "Healthcare Clinic ABC",
                "providerId": "PRV001234",
                "providerType": "Clinic"
            },
            "services": [
                {"serviceId": "SVC001", "description": "General Consultation", "dateOfService": "2025-02-28", "amount": 100.00},
                {"serviceId": "SVC002", "description": "Blood Test", "dateOfService": "2025-02-28", "amount": 50.00}
            ]
        },
        {
            "claimId": "CLM7654321",
            "claimStatus": "Pending",
            "amountClaimed": 300.00,
            "amountApproved": None,
            "provider": "City Health Hospital",
            "services": [
                {"serviceId": "SVC003", "description": "X-ray Imaging", "dateOfService": "2025-02-14", "amount": 300.00}
            ]
        },
        {
            "claimId": "CLM9876543",
            "claimStatus": "Rejected",
            "amountClaimed": 200.00,
            "amountApproved": 0.00,
            "rejectionReason": "Service not covered by policy",
            "provider": "Downtown Diagnostics",
            "services": [
                {"serviceId": "SVC003", "description": "MRI Scan", "dateOfService": "2025-02-05", "amount": 200.00}
            ]
        }
    ]

    return claims_data
