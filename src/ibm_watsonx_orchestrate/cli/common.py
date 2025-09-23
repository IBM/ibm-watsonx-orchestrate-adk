from enum import Enum
from rich.table import Table

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