from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
import random

class RandomNumberError(Exception):
    """Custom exception for random number generation errors."""
    pass

@tool(
    name="randomNumber",
    description="Used for testing error condition by raising an exception for a given percentage of tries",
    permission=ToolPermission.READ_ONLY
)
def randomFailure(percentageFailure: float) -> int:
    """
    randomFailure
    :param percentageFailure: The failure rate between 0 and 1.
    :returns: a random number between 1 and 100
    """

    randomNumber = random.random();

    if randomNumber < percentageFailure:
        raise RandomNumberError("An error occurred during random number generation.")
    
    # Otherwise return a random integer between 1 and 10
    return int(randomNumber * 100)
