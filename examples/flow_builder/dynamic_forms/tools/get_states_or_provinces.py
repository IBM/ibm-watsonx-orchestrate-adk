"""
Tool: get_states_or_provinces

This tool returns a list of states (for USA) or provinces (for Canada)
based on the country parameter. It's used in the dynamic forms example
to demonstrate value-source behaviour.

This is a proper orchestrate tool that can be imported using:
  orchestrate tools import -k python -f tools/get_states_or_provinces.py
"""

from ibm_watsonx_orchestrate.agent_builder.tools.python_tool import tool


@tool(
    name="get_states_or_provinces",
    description="Get list of states or provinces based on country (USA or Canada)"
)
def get_states_or_provinces(country: str) -> list[str]:
    """
    Get list of states or provinces based on country.
    
    This is a synchronous tool that returns a list of primitives (strings).
    It does not use context variables.
    
    Args:
        country: Country name (USA or Canada)
        
    Returns:
        List of state or province names
        
    Examples:
        >>> get_states_or_provinces("USA")
        ['Alabama', 'Alaska', 'Arizona', ...]
        
        >>> get_states_or_provinces("Canada")
        ['Alberta', 'British Columbia', 'Manitoba', ...]
    """
    if country == "USA":
        return [
            "Alabama", "Alaska", "Arizona", "Arkansas", "California",
            "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
            "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
            "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
            "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri",
            "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
            "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
            "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
            "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
            "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
        ]
    elif country == "Canada":
        return [
            "Alberta", "British Columbia", "Manitoba", "New Brunswick",
            "Newfoundland and Labrador", "Northwest Territories", "Nova Scotia",
            "Nunavut", "Ontario", "Prince Edward Island", "Quebec",
            "Saskatchewan", "Yukon"
        ]
    else:
        return []


if __name__ == "__main__":
    # Test the tool
    print("Testing get_states_or_provinces tool:")
    print("\nUSA States:")
    usa_states = get_states_or_provinces("USA")
    print(f"  Count: {len(usa_states)}")
    print(f"  First 5: {usa_states[:5]}")
    
    print("\nCanada Provinces:")
    canada_provinces = get_states_or_provinces("Canada")
    print(f"  Count: {len(canada_provinces)}")
    print(f"  All: {canada_provinces}")
    
    print("\nInvalid Country:")
    invalid = get_states_or_provinces("Mexico")
    print(f"  Result: {invalid}")

