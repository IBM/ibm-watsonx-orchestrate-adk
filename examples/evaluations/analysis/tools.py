from ibm_watsonx_orchestrate.agent_builder.tools import tool
from dataclasses import dataclass
from typing import Optional


@dataclass
class GetUserCountryCodeResponse:
    """Represents the response from getting a user's country code in Workday."""

    country_code: str

@tool()
def get_user_country_code(user_id: str) -> GetUserCountryCodeResponse:
    """
    Gets the ISO 3166-1 alpha-3 code of the user's country.
    Args:
        user_id: user id of the user

    Returns:
        a dictionary that includes {"country_code": ACTUAL_COUNTRYCODE}
    """
    if user_id == "11":
        return GetUserCountryCodeResponse(
            country_code="USA"
        )


@dataclass
class UpdatePreferredNameResult:
    """Represents the result of a preferred name update operation in Workday."""

    success: bool

@tool()
def update_preferred_name(
    user_id: str,
    first_name: str,
    last_name: str,
    country_code: str,
    middle_name: Optional[str] = None,
) -> UpdatePreferredNameResult:
    """
    Updates a user's preferred name in Workday.
    Args:
        user_id: user id of the user
        first_name: first name of the user
        last_name: last name of the user
        country_code: country code of the user
        middle_name: middle name of the user
    Returns:
        a dictionary of status {"success": SUCCESS_STATUS}
    """
    if user_id == "11":

        return UpdatePreferredNameResult(success=True)
