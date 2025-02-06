from ibm_watsonx_orchestrate.cli.commands.tools import tools_command
from unittest.mock import patch

def test_tool_import_call_no_params():
    with patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_command.ToolsController.import_tool") as mock:
        tools_command.tool_import(kind=None)
        mock.assert_called_once_with(
            kind=None,
            file=None,
            app_id=None,
            requirements_file=None,
        )


def test_tool_import_call_python():
    with patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_command.ToolsController.import_tool") as mock:
        tools_command.tool_import(kind="python", file="test_file", requirements_file="tests/cli/resources/python_samples/requirements.txt")
        mock.assert_called_once_with(
            kind="python",
            file="test_file",
            app_id=None,
            requirements_file="tests/cli/resources/python_samples/requirements.txt"
        )

def test_tool_import_call_openapi():
    with patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_command.ToolsController.import_tool") as mock:
        tools_command.tool_import(kind="openapi", file="test_file")
        mock.assert_called_once_with(
            kind="openapi",
            file="test_file",
            app_id=None,
            requirements_file=None,
        )


# def test_tool_import_call_skill():
#     with patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_command.tools_controller.import_tool") as mock:
#         tools_command.tool_import(
#             kind="skill",
#             skillset_id="fake_skill_set_id",
#             skill_id="fake_skill_id",
#             skill_operation_path="fake_path",
#             app_id=None
#         )
#         mock.assert_called_once_with(
#             kind="skill",
#             file=None,
#             skillset_id="fake_skill_set_id",
#             skill_id="fake_skill_id",
#             skill_operation_path="fake_path",
#             app_id=None
#         )

def test_tool_remove():
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.remove_tool"
    ) as mock:
        tools_command.remove_tool(
            name="test_tool",
        )

        mock.assert_called_once_with(
            name="test_tool",
        )

def test_list_tools_non_verbose():
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.list_tools"
    ) as mock:
        tools_command.list_tools()

        mock.assert_called_once_with(
            verbose=False
        )

def testlist_tools_verbose():
    with patch(
        "ibm_watsonx_orchestrate.cli.commands.tools.tools_controller.ToolsController.list_tools"
    ) as mock:
        tools_command.list_tools(verbose=True)

        mock.assert_called_once_with(
            verbose=True
        )
