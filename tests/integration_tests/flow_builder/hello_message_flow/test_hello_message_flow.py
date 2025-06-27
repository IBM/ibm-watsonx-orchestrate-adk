# import pytest
# from pydantic_core import ValidationError
# from unittest.mock import patch, mock_open
# from ibm_watsonx_orchestrate.agent_builder.agents import Agent, SpecVersion, AgentKind, AgentStyle
# from ibm_watsonx_orchestrate.agent_builder.agents.types import DEFAULT_LLM
# import subprocess
# from tests.integration_tests.flow_builder.hello_message_flow.tools.hello_message_flow import build_hello_message_flow
# import asyncio
# import pytest_asyncio
# from pathlib import Path
# import os

# flow = None

# @pytest.fixture(scope="class")
# def import_hello_message_flow_all():
#     script_path = os.path.realpath(__file__)
#     parent_dir_path = os.path.dirname(script_path)
#     print("Importing all the tools and agents for hello message flow.")
#     result = subprocess.run([f"{parent_dir_path}/import-all.sh"], capture_output=True, text=True)
#     print(result.stdout)

# @pytest.mark.usefixtures("import_hello_message_flow_all")
# class TestHelloMessageFlow():
    
#     @pytest.mark.asyncio
#     async def test_hello_message_flow(self):
#         def on_flow_end(result):
#             assert "hello_message_flow" in self.flow.name
#             assert "John Doe" in result
        
#         def on_flow_error(error):
#             print("Test hello message flow failed.")

#         hello_message_flow = await build_hello_message_flow().compile_deploy()
#         generated_folder = f"{Path(__file__).resolve().parent}/generated"

#         global flow
#         flow = await hello_message_flow.invoke({"first_name": "John", "last_name": "Doe"}, on_flow_end_handler=on_flow_end, on_flow_error_handler=on_flow_error)
