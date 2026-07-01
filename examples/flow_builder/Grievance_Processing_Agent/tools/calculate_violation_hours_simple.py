"""
Simplified Violation Hours Calculator Tool for Flow Builder Demo
This is a simplified version of compute_violation_hours for demo purposes.
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field
import re


class ViolationHoursResult(BaseModel):
    """Result schema for violation hours calculation"""
    total_hours: str = Field(
        description="Total calculated violation hours",
        default="0"
    )
    calculation_method: str = Field(
        description="Method used for calculation",
        default="standard"
    )


@tool(
    permission=ToolPermission.READ_ONLY,
    name='Calculate_Violation_Hours_Demo',
    display_name='Calculate Violation Hours (Demo)'
)
def calculate_violation_hours_simple(
    hours_text: str,
    grievance_type: str = "standard"
) -> ViolationHoursResult:
    """
    Calculate total violation hours from extracted text.
    
    This simplified version:
    - Extracts numeric values from text
    - Sums them up for most grievance types
    - For "Excessive Hours" types, subtracts 9.5 from each value >= 9.5
    
    Args:
        hours_text (str): Text containing hours (e.g., "10.5, 11.0, 9.0")
        grievance_type (str): Type of grievance (e.g., "XHN - Excessive Hours")
    
    Returns:
        ViolationHoursResult: Calculated hours and method used
    
    Examples:
        >>> calculate_violation_hours_simple("10.5, 11.0, 12.0", "XHN - Excessive Hours")
        ViolationHoursResult(total_hours="4.0", calculation_method="excessive_hours")
        
        >>> calculate_violation_hours_simple("2.5, 3.0", "SWN - Supervisor Working")
        ViolationHoursResult(total_hours="5.5", calculation_method="standard")
    """
    
    # Handle empty or N/A input
    if not hours_text or hours_text.strip().upper() in ['N/A', 'NONE', '']:
        return ViolationHoursResult(
            total_hours="0",
            calculation_method="no_data"
        )
    
    # Extract all numeric values (including decimals)
    pattern = r'[+-]?\d+(?:\.\d+)?'
    numbers = re.findall(pattern, hours_text)
    
    if not numbers:
        return ViolationHoursResult(
            total_hours="0",
            calculation_method="no_numbers_found"
        )
    
    # Convert to floats
    hours_list = [float(num) for num in numbers]
    
    # Check if this is an "Excessive Hours" grievance type
    is_excessive_hours = any(
        keyword in grievance_type.upper() 
        for keyword in ['XHN', 'XHS', 'EXCESSIVE', '9.5']
    )
    
    if is_excessive_hours:
        # For excessive hours: sum(hours - 9.5) for hours >= 9.5
        total = sum(max(0, hour - 9.5) for hour in hours_list if hour >= 9.5)
        method = "excessive_hours"
    else:
        # For other types: simple sum
        total = sum(hours_list)
        method = "standard"
    
    # Round to 2 decimal places
    total_rounded = round(total, 2)
    
    return ViolationHoursResult(
        total_hours=str(total_rounded),
        calculation_method=method
    )


# Test function (not exported as a tool)
def test_calculator():
    """Test the calculator with sample data"""
    
    test_cases = [
        ("10.5, 11.0, 12.0", "XHN - Excessive Hours", "4.0"),
        ("2.5, 3.0", "SWN - Supervisor Working", "5.5"),
        ("N/A", "PCN - Pay Claim", "0"),
        ("8.0, 9.0", "XHN - Excessive Hours", "0"),  # All under 9.5
        ("10.0, 10.5", "XHN - Excessive Hours", "1.0"),  # 0.5 + 1.0
    ]
    
    print("Testing Violation Hours Calculator:")
    print("-" * 60)
    
    for hours, gtype, expected in test_cases:
        result = calculate_violation_hours_simple(hours, gtype)
        status = "✓" if result.total_hours == expected else "✗"
        print(f"{status} Input: {hours}")
        print(f"  Type: {gtype}")
        print(f"  Expected: {expected}, Got: {result.total_hours}")
        print(f"  Method: {result.calculation_method}")
        print()


if __name__ == "__main__":
    test_calculator()

# Made with Bob
