from ibm_watsonx_orchestrate.cli.commands.knowledge_bases import knowledge_bases_command
from unittest.mock import patch

class TestKnowledgeBaseImport:
    def test_knowledge_base_import(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.import_knowledge_base") as import_mock:
            knowledge_bases_command.knowledge_base_import(file="test.yaml")
            import_mock.assert_called_once_with(
                file="test.yaml", app_id=None
            )

    def test_knowledge_base_import_with_app_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.import_knowledge_base") as import_mock:
            knowledge_bases_command.knowledge_base_import(file="test.yaml", app_id="app-id")
            import_mock.assert_called_once_with(
                file="test.yaml", app_id="app-id"
            )

class TestKnowledgeBasePatch:
    def test_knowledge_base_patch(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.update_knowledge_base") as update_mock:
            knowledge_bases_command.knowledge_base_patch(file="test.yaml", id="1234")
            update_mock.assert_called_once_with(id="1234", name=None, file="test.yaml")

class TestKnowledgeBaseList:
    def test_knowledge_base_list_knowledge_bases_non_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.list_knowledge_bases"
        ) as mock:
            knowledge_bases_command.list_knowledge_bases()

            mock.assert_called_once_with(verbose=False )

    def test_knowledge_base_list_knowledge_bases_verbose(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.list_knowledge_bases"
        ) as mock:
            knowledge_bases_command.list_knowledge_bases(verbose=True)

            mock.assert_called_once_with(verbose=True)

class TestKnowledgeBaseStatus:
    def test_knowledge_base_status(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.knowledge_base_status"
        ) as mock:
            knowledge_bases_command.knowledge_base_status(
                name="test_knowledge_base"
            )

            mock.assert_called_once_with(  id=None, name="test_knowledge_base")

class TestKnowledgeBaseDelete:
    def test_knowledge_base_remove(self):
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.remove_knowledge_base"
        ) as mock:
            knowledge_bases_command.remove_knowledge_base(name="test_knowledge_base"
            )

            mock.assert_called_once_with(id=None, name="test_knowledge_base")
