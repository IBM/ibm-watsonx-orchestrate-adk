from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
import random

@tool(
    name="backupRandomNumber",
    description="Backup tool that always succeeds and returns a random number",
    permission=ToolPermission.READ_ONLY
)
def backupRandomNumber() -> int:
    """
    backupRandomNumber
    :returns: a random number between 1 and 100
    """

    # Always succeeds
    return random.randint(1, 100)