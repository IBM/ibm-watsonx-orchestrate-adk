from ibm_watsonx_orchestrate.cli.commands.channels.types import ChannelType
import rich
import rich.table

def list_channels():
    table = rich.table.Table(show_header=True, header_style="bold white", show_lines=True)
    columns = ["Channel"]
    for col in columns:
        table.add_column(col)

    for channel in ChannelType.__members__.values():

        table.add_row(channel)

        console = rich.console.Console()
        console.print(table)