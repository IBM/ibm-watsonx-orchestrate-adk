from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import KnowledgeBaseController, parse_file, get_relative_file_path
from ibm_watsonx_orchestrate.agent_builder.agents import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base_requests import KnowledgeBaseUpdateRequest
import json
from unittest.mock import patch, mock_open, Mock
import pytest
import uuid
from unittest import mock
from mocks.mock_base_api import MockListConnectionResponse

knowledge_base_controller = KnowledgeBaseController()

@pytest.fixture
def built_in_knowledge_base_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "name": "test_built_in_knowledge_base",
        "description": "Test Object for builtin knowledge_base",
        "documents": [
            "document_1.pdf",
            "document_2.pdf"
        ]
    }


@pytest.fixture
def external_knowledge_base_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "name": "test_external_knowledge_base",
        "description": "Watsonx Assistant Documentation",
        "conversational_search_tool": {
            "index_config": [
                {
                    "milvus": {
                        "grpc_host": "cf94d93e-65f3-40ee-8ac2-e26714aa2071.cie9agrw03kb77s3pr1g.lakehouse.appdomain.cloud",
                        "grpc_port": "30564",
                        "database": "test_db",
                        "collection": "search_wa_docs",
                        "index": "dense",
                        "embedding_model_id": "sentence-transformers/all-minilm-l12-v2",
                        "filter": "",
                        "limit": 10,
                        "field_mapping": {
                            "title": "title",
                            "body": "text"
                        }
                    }
                }
            ]
        }
    }

class MockSDKResponse:
    def __init__(self, response_obj):
        self.response_obj = response_obj

    def dumps_spec(self):
        return json.dumps(self.response_obj)

class MockClient:
    def __init__(self, expected_id=None, expected_payload=None, expected_files=None, fake_knowledge_base=None, fake_status=None, already_existing=False):
        self.fake_knowledge_base = fake_knowledge_base
        self.fake_status = fake_status
        self.already_existing = already_existing
        self.expected_payload = expected_payload
        self.expected_files = expected_files
        self.mock_id = uuid.uuid4()
        self.expected_id = expected_id if expected_id != None else self.mock_id

    def delete(self, knowledge_base_id):
        assert knowledge_base_id == self.expected_id
    
    def create(self, payload):
        assert payload == self.expected_payload

    def create_built_in(self, payload, files):
        assert payload == self.expected_payload
        assert files == self.expected_files

    def update(self, knowledge_base_id, payload):
        assert knowledge_base_id == self.expected_id
        assert payload == self.expected_payload
    
    def get(self):
        return [self.fake_knowledge_base]
    
    def status(self, knowledge_base_id):
        assert knowledge_base_id == self.expected_id
        return self.fake_status

    def get_by_name(self, name):
        if self.already_existing:
            return {"name": name, "id": self.mock_id}
        return []
class MockConnectionClient:
    def __init__(self, get_response=[], get_by_id_response=[], get_conn_by_id_response=[]):
        self.get_by_id_response = get_by_id_response
        self.get_response = get_response
        self.get_conn_by_id_response = get_conn_by_id_response

    def get_draft_by_app_id(self, app_id: str):
        return self.get_by_id_response
    
    def get(self):
        return self.get_response
    
    def get_draft_by_id(self, conn_id: str):
        return self.get_conn_by_id_response

class MockConnection:
    def __init__(self, appid, connection_type):
        self.appid = appid
        self.connection_type = connection_type
        self.connection_id = "12345"
        
class TestParseFile:
    def test_parse_file_yaml(self, built_in_knowledge_base_content):
        with patch("builtins.open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.yaml_safe_load") as mock_loader:
            
            mock_loader.return_value = built_in_knowledge_base_content

            parse_file("test.yaml")

            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()

    def test_parse_file_json(self, built_in_knowledge_base_content):
        with patch("builtins.open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.json.load") as mock_loader:
            
            mock_loader.return_value = built_in_knowledge_base_content

            parse_file("test.json")

            mock_file.assert_called_once_with("test.json", "r")
            mock_loader.assert_called_once()

    def test_parse_file_py(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.inspect.getmembers") as getmembers_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.importlib.import_module") as import_module_mock:

            getmembers_mock.return_value = []
            knowledge_bases = parse_file("test.py")

            import_module_mock.assert_called_with("test")
            getmembers_mock.assert_called_once()

            assert len(knowledge_bases) == 0

    def test_parse_file_invalid(self):
        with pytest.raises(ValueError) as e:
            parse_file("test.test")
            assert "file must end in .json, .yaml, .yml or .py" in str(e)

class TestImportKnowledgeBase:
    def test_import_built_in_knowledge_base(self, caplog, built_in_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock, \
             patch("builtins.open", mock_open()) as mock_file:

            expected_files =  [('files', ('document_1.pdf', 'pdf-data-1')), ('files', ('document_2.pdf', 'pdf-data-2'))]
                        
            knowledge_Base = KnowledgeBase(**built_in_knowledge_base_content)
            from_spec_mock.return_value = knowledge_Base

            knowledge_base_payload = knowledge_Base.model_dump(exclude_none=True)
            knowledge_base_payload["prioritize_built_in_index"] = True
            knowledge_base_payload.pop("documents")
            client_mock.return_value = MockClient(expected_payload=knowledge_base_payload, expected_files=expected_files)

            mock_file.side_effect = [ "pdf-data-1", "pdf-data-2" ]

            knowledge_base_controller.import_knowledge_base("my_dir/test.json", None)

            mock_file.assert_has_calls([ mock.call("my_dir/document_1.pdf", "rb"), mock.call("my_dir/document_2.pdf", "rb") ])

            captured = caplog.text
            assert f"Successfully imported knowledge base 'test_built_in_knowledge_base'" in captured


    def test_import_external_knowledge_base(self, caplog, external_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch('ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.get_connections_client') as conn_client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock:
            
            mock_response = MockListConnectionResponse(connection_id="12345")
            conn_client_mock.return_value = MockConnectionClient(get_by_id_response=mock_response)
                        
            knowledge_Base = KnowledgeBase(**external_knowledge_base_content)
            from_spec_mock.return_value = knowledge_Base

            knowledge_Base.conversational_search_tool.index_config[0].connection_id = "12345"
            knowledge_base_payload = knowledge_Base.model_dump(exclude_none=True)
            knowledge_base_payload["prioritize_built_in_index"] = False
            client_mock.return_value = MockClient(expected_payload=knowledge_base_payload)

            knowledge_base_controller.import_knowledge_base("test.json", "my-app-id")

            captured = caplog.text
            assert f"Successfully imported knowledge base 'test_external_knowledge_base'" in captured


class TestKnowledgeBaseControllerUpdateKnowledgeBase:
    def test_update_knowledge_base_with_name_and_documents(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base_requests.KnowledgeBaseUpdateRequest.from_spec") as from_spec_mock:
                        
            knowledge_base_update_req = KnowledgeBaseUpdateRequest(**{ "name" : "new_name" })
            from_spec_mock.return_value = knowledge_base_update_req

            knowledge_base_update_req.prioritize_built_in_index = True
            client_mock.return_value = MockClient(already_existing=True, expected_payload=knowledge_base_update_req.model_dump(exclude_none=True))

            knowledge_base_controller.update_knowledge_base(None, "old_name", "test.json")

            captured = caplog.text
            assert "Successfully updated knowledge base 'old_name'" in captured

    def test_update_knowledge_base_with_id(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base_requests.KnowledgeBaseUpdateRequest.from_spec") as from_spec_mock:
                        
            knowledge_base_update_req = KnowledgeBaseUpdateRequest(**{ "name" : "new_name" })
            from_spec_mock.return_value = knowledge_base_update_req

            id = uuid.uuid4()
            client_mock.return_value = MockClient(already_existing=True, expected_id=id, expected_payload=knowledge_base_update_req.model_dump(exclude_none=True))
            knowledge_base_controller.update_knowledge_base(id, None, "test.json")

            captured = caplog.text
            assert f"Successfully updated knowledge base with ID '{id}'" in captured

        
class TestListKnowledgeBases:
    def test_list_knowledge_bases(self, external_knowledge_base_content):    
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("rich.table.Table") as richTableMock, patch("rich.print") as richPrintMock:
            client_mock.return_value = MockClient(fake_knowledge_base=KnowledgeBase(**external_knowledge_base_content))

            knowledge_base_controller.list_knowledge_bases()

            richTableMock.assert_called_once()
            richPrintMock.assert_called_once()
            
    def test_list_knowledge_bases_verbose(self, external_knowledge_base_content):    
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("rich.json.JSON") as richJsonMock, patch("rich.print") as richPrintMock:
            client_mock.return_value = MockClient(fake_knowledge_base=KnowledgeBase(**external_knowledge_base_content))

            knowledge_base_controller.list_knowledge_bases(verbose=True)

            richJsonMock.assert_called_once()
            richPrintMock.assert_called_once()
        
      
class TestKnowledgeBaseControllerRemoveKnowledgeBase:
    def test_remove_knowledge_base_with_name(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock:                        
            client_mock.return_value = MockClient(already_existing=True)

            knowledge_base_controller.remove_knowledge_base(None, "old_name")

            captured = caplog.text
            assert "Successfully removed knowledge base 'old_name'" in captured

    def test_remove_knowledge_base_with_id(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock:
            id = uuid.uuid4()

            client_mock.return_value = MockClient(already_existing=True, expected_id=id)
            knowledge_base_controller.remove_knowledge_base(id, None)

            captured = caplog.text
            assert f"Successfully removed knowledge base with ID '{id}'" in captured

class TestKnowledgeBaseControllerKnowledgeBaseStatus:
    def test_knowledge_base_status_built_in(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("rich.table.Table") as RichTableMock:      
            fakeStatus = {
                "name": "Knowledge Base Name",
                "description": "Knowledge Base Description",
                "ready": True,
                "documents": [{ "metadata" : { 'original_file_name': "Document 1" } }, {} ]
            } 

            client_mock.return_value = MockClient(already_existing=True, fake_status=fakeStatus)

            mock_instance = RichTableMock.return_value
            mock_instance.add_column = Mock()
            mock_instance.add_row = Mock()

            knowledge_base_controller.knowledge_base_status(None, "old_name")

            mock_instance.add_column.assert_has_calls([ mock.call('Name', {}), mock.call('Description', {}), mock.call('Ready', {}), mock.call('Documents (2)', {}) ]) 
            mock_instance.add_row.assert_called_once_with("Knowledge Base Name", "Knowledge Base Description", 'True', "Document 1, <Unnamed File>")


    def test_external_knowledge_base_status(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("rich.table.Table") as RichTableMock:      
            fakeStatus = {
                "name": "Knowledge Base Name",
            } 

            id = uuid.uuid4()
            client_mock.return_value = MockClient(already_existing=True, expected_id=id, fake_status=fakeStatus)

            mock_instance = RichTableMock.return_value
            mock_instance.add_column = Mock()
            mock_instance.add_row = Mock()

            knowledge_base_controller.knowledge_base_status(id, None)

            mock_instance.add_column.assert_has_calls([ mock.call('Name', {}) ]) 
            mock_instance.add_row.assert_called_once_with("Knowledge Base Name")


class TestRelativeFilePath:

    def test_relative_file_path(self):
        assert get_relative_file_path("./more/my_file.pdf", "current/dir") == "current/dir/more/my_file.pdf"
        assert get_relative_file_path("more/my_file.pdf", "current/dir") == "current/dir/more/my_file.pdf"
        assert get_relative_file_path("/more/my_file.pdf", "current/dir") == "/more/my_file.pdf"
        