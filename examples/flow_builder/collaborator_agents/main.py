import asyncio
import logging
from pathlib import Path
from examples.flow_builder.collaborator_agents.tools.collaborator_agents_flow import build_collaborator_agents_flow

logger = logging.getLogger(__name__)
def on_event_end(res):
    print(f'Flow {flow_name} completed. Result: {res}')

def on_event_error(err):
    print(f'Errors occured in flow {flow_name}. Error: {err}')

async def main():
    '''A function demonstrating how to build a flow and save it to a file.'''
    my_flow_definition = await build_collaborator_agents_flow().compile_deploy()
    global flow_name
    flow_name = my_flow_definition.flow.spec.display_name
    generated_folder = f"{Path(__file__).resolve().parent}/generated"
    my_flow_definition.dump_spec(f"{generated_folder}/city.json")
    await my_flow_definition.invoke(input_data={"city" : "Fremont"},
                    debug=True, on_flow_end_handler=on_event_end, on_flow_error_handler=on_event_error)

if __name__ == "__main__":
    asyncio.run(main())