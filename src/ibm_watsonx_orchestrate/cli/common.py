from enum import Enum
from rich.table import Table
import typer
import logging

logger = logging.getLogger(__name__)

class ListFormats(str, Enum):
    Table = "table"
    JSON = "json"

    def __str__(self):
        return self.value 

    def __repr__(self):
        return repr(self.value)

def rich_table_to_markdown(table: Table) -> str:
    headers = [column.header for column in table.columns]
    cols = [[cell for cell in col.cells] for col in table.columns]
    rows = list(map(list, zip(*cols)))

    # Header row
    md = "| " + " | ".join(headers) + " |\n"
    # Separator row
    md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    # # Data rows
    for row in rows:
        md += "| " + " | ".join(row) + " |\n"
    return md

def prompt_for_confirmation(resource_type: str, resource_name: str) -> bool:
    """Prompt the user for confirmation before updating an existing resource."""

    logger.info(f"Found existing {resource_type} named '{resource_name}'. Updating...")
    
    try:
        response = typer.prompt(
            f"Are you sure you want to proceed (Y/n)",
            default="Y",
            show_default=False
        )
        
        # Accept Y, y, Yes, yes, YES as confirmation
        if response.strip().lower() in ['y', 'yes', '']:
            return True
        else:
            logger.info("Operation cancelled")
            return False
            
    except (KeyboardInterrupt, EOFError):
        logger.info("\nOperation cancelled")
        return False


def check_safe_mode_and_prompt(
    safe_mode: bool,
    resource_exists: bool,
    resource_type: str,
    resource_name: str
) -> bool:
    """Check if safe mode is enabled and prompt for confirmation if needed."""
    
    # If resource doesn't exist, always proceed
    if not resource_exists:
        return True
    
    # If safe mode is enabled, prompt for confirmation
    if safe_mode:
        return prompt_for_confirmation(resource_type, resource_name)
    
    # Default behavior: proceed without prompting
    return True