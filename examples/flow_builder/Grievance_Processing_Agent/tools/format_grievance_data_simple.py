"""
Simplified Data Formatter Tool for Flow Builder Demo
This tool formats extracted grievance data for better readability.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field
from typing import Optional


class FormattedGrievanceData(BaseModel):
    """Result schema for formatted grievance data"""
    formatted_summary: str = Field(
        description="Formatted summary of the grievance",
        default=""
    )
    key_details: str = Field(
        description="Key details extracted and formatted",
        default=""
    )
    status: str = Field(
        description="Processing status",
        default="success"
    )


@tool(
    permission=ToolPermission.READ_ONLY,
    name='Format_Grievance_Data_Demo',
    display_name='Format Grievance Data (Demo)'
)
def format_grievance_data_simple(
    grievance_text: str = "",
    adjustment_requested: str = "",
    case_no: str = "",
    name: str = "",
    date_filed: str = "",
    grievance_type: str = ""
) -> FormattedGrievanceData:
    """
    Format extracted grievance data into a readable summary.
    
    This simplified tool takes extracted fields and creates:
    - A formatted summary combining all information
    - Key details section highlighting important data
    
    Args:
        grievance_text (str): The main grievance description
        adjustment_requested (str): Settlement or adjustment requested
        case_no (str): Case or grievance number
        name (str): Employee name
        date_filed (str): Date the grievance was filed
        grievance_type (str): Classified type of grievance
    
    Returns:
        FormattedGrievanceData: Formatted summary and key details
    
    Example:
        >>> format_grievance_data_simple(
        ...     grievance_text="Supervisor worked during my shift",
        ...     adjustment_requested="Pay for 2 hours",
        ...     case_no="2024-001",
        ...     name="John Doe",
        ...     date_filed="01/15/2024",
        ...     grievance_type="Supervisor Working"
        ... )
    """
    
    # Build formatted summary
    summary_parts = []
    
    # Header
    if case_no:
        summary_parts.append(f"📋 GRIEVANCE CASE: {case_no}")
    else:
        summary_parts.append("📋 GRIEVANCE CASE: [No case number]")
    
    summary_parts.append("=" * 50)
    
    # Employee info
    if name:
        summary_parts.append(f"👤 Employee: {name}")
    
    if date_filed:
        summary_parts.append(f"📅 Date Filed: {date_filed}")
    
    if grievance_type:
        summary_parts.append(f"🏷️  Type: {grievance_type}")
    
    summary_parts.append("")  # Blank line
    
    # Grievance description
    if grievance_text and grievance_text.strip():
        summary_parts.append("📝 GRIEVANCE:")
        summary_parts.append(grievance_text.strip())
        summary_parts.append("")
    
    # Adjustment requested
    if adjustment_requested and adjustment_requested.strip():
        summary_parts.append("⚖️  ADJUSTMENT REQUESTED:")
        summary_parts.append(adjustment_requested.strip())
    
    formatted_summary = "\n".join(summary_parts)
    
    # Build key details (compact format)
    key_details_parts = []
    
    if name:
        key_details_parts.append(f"Employee: {name}")
    
    if case_no:
        key_details_parts.append(f"Case: {case_no}")
    
    if date_filed:
        key_details_parts.append(f"Filed: {date_filed}")
    
    if grievance_type:
        key_details_parts.append(f"Type: {grievance_type}")
    
    key_details = " | ".join(key_details_parts) if key_details_parts else "No details available"
    
    # Determine status
    status = "success"
    if not grievance_text or not grievance_text.strip():
        status = "warning_no_grievance_text"
    
    return FormattedGrievanceData(
        formatted_summary=formatted_summary,
        key_details=key_details,
        status=status
    )


# Test function (not exported as a tool)
def test_formatter():
    """Test the formatter with sample data"""
    
    print("Testing Grievance Data Formatter:")
    print("-" * 60)
    
    result = format_grievance_data_simple(
        grievance_text="Supervisor John Smith worked on the loading dock for 2 hours during my scheduled shift on January 10, 2024.",
        adjustment_requested="Pay me for 2 hours at double time rate as per contract Article 3.7",
        case_no="2024-SWN-001",
        name="Jane Doe",
        date_filed="01/15/2024",
        grievance_type="SWN - Supervisor Working"
    )
    
    print("FORMATTED SUMMARY:")
    print(result.formatted_summary)
    print("\n" + "-" * 60)
    print("KEY DETAILS:")
    print(result.key_details)
    print("\n" + "-" * 60)
    print(f"STATUS: {result.status}")


if __name__ == "__main__":
    test_formatter()

# Made with Bob
