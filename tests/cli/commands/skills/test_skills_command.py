import pytest
import typer
from unittest.mock import patch, MagicMock

from ibm_watsonx_orchestrate.cli.commands.skills import skills_command


@pytest.fixture(autouse=True)
def mock_instantiate_client():
    """Prevent SkillsController.__init__ from hitting a real environment."""
    with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_controller.instantiate_client") as mock:
        client = MagicMock()
        client.base_url = "http://localhost:4321"
        client.verify = True
        client._get_headers.return_value = {}
        mock.return_value = client
        yield mock


class TestValidateSkillIdentifier:
    def test_neither_id_nor_name_raises(self):
        with pytest.raises(typer.Exit):
            skills_command._validate_skill_identifier(None, None)

    def test_both_id_and_name_raises(self):
        with pytest.raises(typer.Exit):
            skills_command._validate_skill_identifier("id-123", "my-skill")

    def test_id_only_passes(self):
        skills_command._validate_skill_identifier("id-123", None)

    def test_name_only_passes(self):
        skills_command._validate_skill_identifier(None, "my-skill")


class TestImportSkillCmd:
    def test_import_single_file(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.import_skill") as mock:
            skills_command.import_skill_cmd(file="path/to/SKILL.md")
            mock.assert_called_once_with(file="path/to/SKILL.md", workspace_id=None)

    def test_import_directory(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.import_skill_directory") as mock:
            skills_command.import_skill_cmd(directory="path/to/skills/")
            mock.assert_called_once_with(
                directory="path/to/skills/",
                recursive=False,
                workspace_id=None,
                upsert=False,
            )

    def test_import_directory_recursive_upsert(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.import_skill_directory") as mock:
            skills_command.import_skill_cmd(directory="path/to/skills/", recursive=True, upsert=True)
            mock.assert_called_once_with(
                directory="path/to/skills/",
                recursive=True,
                workspace_id=None,
                upsert=True,
            )

    def test_no_file_or_dir_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.import_skill_cmd()

    def test_both_file_and_dir_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.import_skill_cmd(file="SKILL.md", directory="skills/")

    def test_recursive_without_dir_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.import_skill_cmd(file="SKILL.md", recursive=True)


class TestUpdateSkillCmd:
    def test_update_by_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.update_skill") as mock:
            skills_command.update_skill_cmd(file="SKILL.md", skill_id="abc-123")
            mock.assert_called_once_with(skill_id="abc-123", skill_name=None, file="SKILL.md")

    def test_update_by_name(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.update_skill") as mock:
            skills_command.update_skill_cmd(file="SKILL.md", skill_name="my-skill")
            mock.assert_called_once_with(skill_id=None, skill_name="my-skill", file="SKILL.md")

    def test_no_identifier_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.update_skill_cmd(file="SKILL.md")

    def test_both_identifiers_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.update_skill_cmd(file="SKILL.md", skill_id="abc", skill_name="my-skill")


class TestListSkillsCmd:
    def test_list_defaults(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.list_skills") as mock:
            skills_command.list_skills_cmd()
            mock.assert_called_once_with(workspace_id=None, verbose=False)

    def test_list_verbose(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.list_skills") as mock:
            skills_command.list_skills_cmd(verbose=True)
            mock.assert_called_once_with(workspace_id=None, verbose=True)

    def test_list_with_workspace(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.list_skills") as mock:
            skills_command.list_skills_cmd(workspace_id="ws-123")
            mock.assert_called_once_with(workspace_id="ws-123", verbose=False)


class TestRemoveSkillCmd:
    def test_remove_by_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.remove_skill") as mock:
            skills_command.remove_skill_cmd(skill_id="abc-123")
            mock.assert_called_once_with(skill_id="abc-123", skill_name=None)

    def test_remove_by_name(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.remove_skill") as mock:
            skills_command.remove_skill_cmd(skill_name="my-skill")
            mock.assert_called_once_with(skill_id=None, skill_name="my-skill")

    def test_no_identifier_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.remove_skill_cmd()

    def test_both_identifiers_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.remove_skill_cmd(skill_id="abc", skill_name="my-skill")


class TestExportSkillCmd:
    def test_export_by_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.export_skill") as mock:
            skills_command.export_skill_cmd(output="./out/", skill_id="abc-123")
            mock.assert_called_once_with(output_path="./out/", skill_id="abc-123", skill_name=None)

    def test_export_by_name(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.export_skill") as mock:
            skills_command.export_skill_cmd(output="./out/", skill_name="my-skill")
            mock.assert_called_once_with(output_path="./out/", skill_id=None, skill_name="my-skill")

    def test_no_identifier_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.export_skill_cmd(output="./out/")

    def test_both_identifiers_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.export_skill_cmd(output="./out/", skill_id="abc", skill_name="my-skill")


class TestGetSkillCmd:
    def test_get_by_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.show_skill") as mock:
            skills_command.get_skill_cmd(skill_id="abc-123")
            mock.assert_called_once_with(skill_id="abc-123", skill_name=None)

    def test_get_by_name(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.show_skill") as mock:
            skills_command.get_skill_cmd(skill_name="my-skill")
            mock.assert_called_once_with(skill_id=None, skill_name="my-skill")

    def test_no_identifier_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.get_skill_cmd()

    def test_both_identifiers_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.get_skill_cmd(skill_id="abc", skill_name="my-skill")


class TestUploadScriptCmd:
    def test_upload_by_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.upload_script") as mock:
            skills_command.upload_script_cmd(file="validate.py", skill_id="abc-123")
            mock.assert_called_once_with(
                skill_id="abc-123", skill_name=None,
                script_file="validate.py", script_path=None,
            )

    def test_upload_by_name_with_path(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.upload_script") as mock:
            skills_command.upload_script_cmd(
                file="validate.py", skill_name="my-skill",
                script_path="scripts/validate.py",
            )
            mock.assert_called_once_with(
                skill_id=None, skill_name="my-skill",
                script_file="validate.py", script_path="scripts/validate.py",
            )

    def test_no_identifier_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.upload_script_cmd(file="validate.py")

    def test_both_identifiers_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.upload_script_cmd(file="validate.py", skill_id="abc", skill_name="my-skill")


class TestUploadReferenceCmd:
    def test_upload_by_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.upload_reference") as mock:
            skills_command.upload_reference_cmd(file="REFERENCE.md", skill_id="abc-123")
            mock.assert_called_once_with(
                skill_id="abc-123", skill_name=None,
                reference_file="REFERENCE.md", reference_path=None,
            )

    def test_upload_by_name(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.skills.skills_command.SkillsController.upload_reference") as mock:
            skills_command.upload_reference_cmd(file="policy.pdf", skill_name="my-skill")
            mock.assert_called_once_with(
                skill_id=None, skill_name="my-skill",
                reference_file="policy.pdf", reference_path=None,
            )

    def test_no_identifier_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.upload_reference_cmd(file="REFERENCE.md")

    def test_both_identifiers_raises(self):
        with pytest.raises(typer.Exit):
            skills_command.upload_reference_cmd(file="REFERENCE.md", skill_id="abc", skill_name="my-skill")
