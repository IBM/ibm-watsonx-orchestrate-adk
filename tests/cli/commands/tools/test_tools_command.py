from ibm_watsonx_orchestrate.cli.commands.tools import tools_command
from unittest.mock import patch

def test_tool_import_call_no_params():
    with patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_command.ToolsController.import_tool") as mock:
        tools_command.tool_import(kind=None)
        mock.assert_called_once_with(
            kind=None,
            file=None,
            # skillset_id=None,
            # skill_id=None,
            # skill_operation_path=None,
            app_id=None
        )


def test_tool_import_call_python():
    with patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_command.ToolsController.import_tool") as mock:
        tools_command.tool_import(kind="python", file="test_file")
        mock.assert_called_once_with(
            kind="python",
            file="test_file",
            # skillset_id=None,
            # skill_id=None,
            # skill_operation_path=None,
            app_id=None
        )

def test_tool_import_call_openapi():
    with patch("ibm_watsonx_orchestrate.cli.commands.tools.tools_command.ToolsController.import_tool") as mock:
        tools_command.tool_import(kind="openapi", file="test_file")
        mock.assert_called_once_with(
            kind="openapi",
            file="test_file",
            # skillset_id=None,
            # skill_id=None,
            # skill_operation_path=None,
            app_id=None
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
