from ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller import (
    KnowledgeBaseController,
    parse_file,
    get_relative_file_path,
)
from ibm_watsonx_orchestrate_core.types.spec.types import SpecVersion
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import (
    ContentSourceConfig,
    ContentSourceType,
    IndexConnection,
    MilvusConnection,
    ElasticSearchConnection,
    OpenSearchConnection,
    AstraDBConnection,
    CustomSearchConnection,
)
from ibm_watsonx_orchestrate.client.base_api_client import ClientAPIException
import json
from unittest.mock import patch, mock_open, Mock
import pytest
import uuid
from unittest import mock
from pydantic import BaseModel
from pathlib import Path

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
def built_in_knowledge_base_content_with_url() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "name": "test_built_in_knowledge_base",
        "description": "Test Object for builtin knowledge_base",
        "documents": [
            { "path": "document_1.pdf", "url": "http://www.document1.com" },
            { "path": "document_2.pdf" }
        ]
    }

@pytest.fixture
def existing_built_in_knowledge_base_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "name": "existing-knowledge-base",
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

@pytest.fixture
def existing_external_knowledge_base_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "name": "existing-knowledge-base",
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

@pytest.fixture
def content_source_knowledge_base_content() -> dict:
    return {
        "spec_version": SpecVersion.V1,
        "name": "test_content_source_knowledge_base",
        "description": "Connector-backed knowledge base",
        "documents": ["document_1.pdf"],
        "content_source": {
            "type": "box",
            "app_id": "12345"
        }
    }

class MockListConnectionResponse(BaseModel):
    connection_id: str
    app_id: str

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

    def create_without_files(self, payload):
        assert payload == self.expected_payload

    def update(self, knowledge_base_id, payload):
        assert knowledge_base_id == self.expected_id
        assert payload == self.expected_payload

    def update_with_documents(self, knowledge_base_id, payload, files):
        assert knowledge_base_id == self.expected_id
        assert payload == self.expected_payload
        assert files == self.expected_files

    def update_without_files(self, knowledge_base_id, payload):
        assert knowledge_base_id == self.expected_id
        assert payload == self.expected_payload
    
    def get(self):
        return [self.fake_knowledge_base]
    
    def status(self, knowledge_base_id):
        assert knowledge_base_id == self.expected_id
        return self.fake_status

    def sync(self, knowledge_base_id):
        assert knowledge_base_id == self.expected_id

    def get_by_name(self, name, workspace_id=None):
        if self.already_existing:
            return {"name": name, "id": self.mock_id}
        return []
    
    def get_by_names(self, names):
        return [{"name": "existing-knowledge-base", "id": self.expected_id}]

    def validate_creds(self, connection_id, vector_index_type, url=None, port=None):
        pass

    
class MockConnectionClient:
    def __init__(self, get_response=[], get_by_id_response=[], get_conn_by_id_response=[], list_response=[]):
        self.get_by_id_response = get_by_id_response
        self.get_response = get_response
        self.get_conn_by_id_response = get_conn_by_id_response
        self.list_response = list_response

    def get_draft_by_app_id(self, app_id: str):
        return self.get_by_id_response
    
    def get(self):
        return self.get_response
    
    def get_draft_by_id(self, conn_id: str):
        return self.get_conn_by_id_response
    
    def list(self):
        return self.list_response

class MockConnection:
    def __init__(self, appid, connection_type):
        self.appid = appid
        self.connection_type = connection_type
        self.connection_id = "12345"

class TestParseFile:
    def test_parse_file_yaml(self, built_in_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.yaml_safe_load") as mock_loader:
            
            mock_loader.return_value = built_in_knowledge_base_content

            parse_file("test.yaml")

            mock_file.assert_called_once_with("test.yaml", "r")
            mock_loader.assert_called_once()

    def test_parse_file_json(self, built_in_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.safe_open", mock_open()) as mock_file, \
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
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController._poll_knowledge_base_status") as poll_mock:

            expected_files =  [('files', ('document_1.pdf', 'pdf-data-1')), ('files', ('document_2.pdf', 'pdf-data-2'))]
                        
            knowledge_base = KnowledgeBase(**built_in_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            knowledge_base_json = knowledge_base.model_dump(exclude_none=True)
            knowledge_base_json["prioritize_built_in_index"] = True
            knowledge_base_json.pop("documents")

            knowledge_base_payload = { "knowledge_base": json.dumps(knowledge_base_json), "file_urls": "{}" }

            mock_client = MockClient(expected_payload=knowledge_base_payload, expected_files=expected_files)
            client_mock.return_value = mock_client
            
            # Mock the create_built_in response to return a knowledge_base ID
            mock_client.create_built_in = Mock(return_value={'knowledge_base': 'test-kb-id'})

            mock_file.side_effect = [ "pdf-data-1", "pdf-data-2" ]

            knowledge_base_controller.import_knowledge_base("my_dir/test.json", None)

            mock_file.assert_has_calls([ mock.call(Path("my_dir/document_1.pdf"), "rb"), mock.call(Path("my_dir/document_2.pdf"), "rb") ])
            
            # Verify polling was called
            poll_mock.assert_called_once_with(mock_client, 'test-kb-id', 'test_built_in_knowledge_base', False)

    def test_import_built_in_knowledge_base_with_url(self, caplog, built_in_knowledge_base_content_with_url):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController._poll_knowledge_base_status") as poll_mock:

            expected_files =  [('files', ('document_1.pdf', 'pdf-data-1')), ('files', ('document_2.pdf', 'pdf-data-2'))]
                        
            knowledge_base = KnowledgeBase(**built_in_knowledge_base_content_with_url)
            from_spec_mock.return_value = knowledge_base

            knowledge_base_json = knowledge_base.model_dump(exclude_none=True)
            knowledge_base_json["prioritize_built_in_index"] = True
            knowledge_base_json.pop("documents")

            knowledge_base_payload = { "knowledge_base": json.dumps(knowledge_base_json), "file_urls": '{"document_1.pdf": "http://www.document1.com"}' }

            mock_client = MockClient(expected_payload=knowledge_base_payload, expected_files=expected_files)
            client_mock.return_value = mock_client
            
            # Mock the create_built_in response to return a knowledge_base ID
            mock_client.create_built_in = Mock(return_value={'knowledge_base': 'test-kb-id'})

            mock_file.side_effect = [ "pdf-data-1", "pdf-data-2" ]

            knowledge_base_controller.import_knowledge_base("my_dir/test.json", None)

            mock_file.assert_has_calls([ mock.call(Path("my_dir/document_1.pdf"), "rb"), mock.call(Path("my_dir/document_2.pdf"), "rb") ])
            
            # Verify polling was called
            poll_mock.assert_called_once_with(mock_client, 'test-kb-id', 'test_built_in_knowledge_base', False)

    def test_update_built_in_knowledge_base(self, caplog, existing_built_in_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.safe_open", mock_open()) as mock_file, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController._poll_knowledge_base_status") as poll_mock:

            expected_files =  [('files', ('document_1.pdf', 'pdf-data-1')), ('files', ('document_2.pdf', 'pdf-data-2'))]
                        
            knowledge_base = KnowledgeBase(**existing_built_in_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            knowledge_base_json = knowledge_base.model_dump(exclude_none=True)
            knowledge_base_json["prioritize_built_in_index"] = True
            knowledge_base_json.pop("documents")

            knowledge_base_payload = { "knowledge_base": json.dumps(knowledge_base_json), "file_urls": "{}" }

            fakeStatus = {
                "documents": [{ "metadata" : { 'original_file_name': "document_1.pdf" } }, { "metadata" : { 'original_file_name': "document_3.pdf" } } ]
            }

            expected_id = uuid.uuid4()
            mock_client = MockClient(expected_payload=knowledge_base_payload, fake_status=fakeStatus, expected_files=expected_files, expected_id=expected_id)
            client_mock.return_value = mock_client

            mock_file.side_effect = [ "pdf-data-1", "pdf-data-2" ]

            knowledge_base_controller.import_knowledge_base("my_dir/test.json", None)

            mock_file.assert_has_calls([ mock.call(Path("my_dir/document_1.pdf"), "rb"), mock.call(Path("my_dir/document_2.pdf"), "rb") ])

            captured = caplog.text
            assert f"Document \"document_1.pdf\" already exists in knowledge base. Updating..." in captured
            assert f"Document \"document_3.pdf\" removed from knowledge base." in captured
            
            # Verify polling was called for update
            poll_mock.assert_called_once_with(mock_client, expected_id, 'existing-knowledge-base', True)


    def test_import_external_knowledge_base(self, caplog, external_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch('ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.get_connections_client') as conn_client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock:
            
            mock_response = [MockListConnectionResponse(connection_id="12345", app_id="my-app-id")]
            conn_client_mock.return_value = MockConnectionClient(list_response=mock_response)
                        
            knowledge_base = KnowledgeBase(**external_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            knowledge_base.conversational_search_tool.index_config[0].connection_id = "12345"
            knowledge_base_json = knowledge_base.model_dump(exclude_none=True)
            knowledge_base_json["prioritize_built_in_index"] = False

            knowledge_base_payload = { "knowledge_base": json.dumps(knowledge_base_json) }
            
            client_mock.return_value = MockClient(expected_payload=knowledge_base_payload)

            knowledge_base_controller.import_knowledge_base("test.json", "my-app-id")

            captured = caplog.text
            assert f"Successfully imported knowledge base 'test_external_knowledge_base'" in captured

    def test_import_external_knowledge_base_no_app_id(self, external_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock:
            
                        
            knowledge_base = KnowledgeBase(**external_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            knowledge_base_json = knowledge_base.model_dump(exclude_none=True)
            knowledge_base_json["prioritize_built_in_index"] = False

            knowledge_base_payload = { "knowledge_base": json.dumps(knowledge_base_json) }
            
            client_mock.return_value = MockClient(expected_payload=knowledge_base_payload)

            err = None
            try:
                knowledge_base_controller.import_knowledge_base("test.json", app_id=None)
            except ValueError as e:
                err = e

            assert err is not None and f"{err}" == "Must provide credentials (via --app-id) when using milvus or elastic_search."

    def test_update_external_knowledge_base(self, caplog, existing_external_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock,  \
             patch('ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.get_connections_client') as conn_client_mock,  \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock:
            
            mock_response = [MockListConnectionResponse(connection_id="12345", app_id="my-app-id")]
            conn_client_mock.return_value = MockConnectionClient(list_response=mock_response)
                        
            knowledge_base = KnowledgeBase(**existing_external_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            knowledge_base.conversational_search_tool.index_config[0].connection_id = "12345"
            knowledge_base_json = knowledge_base.model_dump(exclude_none=True)
            knowledge_base_json["prioritize_built_in_index"] = False

            knowledge_base_payload = { "knowledge_base": json.dumps(knowledge_base_json) }
            client_mock.return_value = MockClient(expected_payload=knowledge_base_payload, expected_id=uuid.uuid4())

            knowledge_base_controller.import_knowledge_base("test.json", "my-app-id")

            captured = caplog.text
            assert f"Knowledge base 'existing-knowledge-base' updated successfully" in captured
        
class TestListKnowledgeBases:
    def test_list_knowledge_bases(self, external_knowledge_base_content):    
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
            patch('ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.get_connections_client') as conn_client_mock,  \
             patch("rich.table.Table") as richTableMock, patch("rich.print") as richPrintMock:
            client_mock.return_value = MockClient(fake_knowledge_base=KnowledgeBase(**external_knowledge_base_content))
            conn_client_mock = MockConnectionClient()

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
        assert get_relative_file_path("./more/my_file.pdf", "current/dir") == Path("current/dir/more/my_file.pdf")
        assert get_relative_file_path("more/my_file.pdf", "current/dir") == Path("current/dir/more/my_file.pdf")
        assert get_relative_file_path("/more/my_file.pdf", "current/dir") == Path("/more/my_file.pdf")


class TestPollKnowledgeBaseStatus:
    """Tests for the _poll_knowledge_base_status method"""
    
    def test_poll_status_ready_immediately(self, caplog):
        """Test polling when status is ready on first check"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.return_value = {
                'built_in_index_status': 'ready',
                'built_in_index_status_msg': 'Import completed successfully'
            }
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False)
            
            # Should call status at least once
            assert mock_client.status.call_count >= 1
            mock_client.status.assert_called_with('test-kb-id')
    
    def test_poll_status_ready_after_rebuilding(self, caplog):
        """Test polling when status transitions from rebuilding to ready"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            # First call returns rebuilding, second call returns ready
            mock_client.status.side_effect = [
                {'built_in_index_status': 'rebuilding', 'built_in_index_status_msg': ''},
                {'built_in_index_status': 'ready', 'built_in_index_status_msg': 'Import completed'}
            ]
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False, poll_interval=1)
            
            # Should call status twice
            assert mock_client.status.call_count == 2
            # Should sleep at least once (for animation)
            assert sleep_mock.call_count >= 1
    
    def test_poll_status_error(self, caplog):
        """Test polling when status returns error"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.return_value = {
                'built_in_index_status': 'error',
                'built_in_index_status_msg': 'Import failed due to invalid document'
            }
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False)
            
            # Should call status at least once
            assert mock_client.status.call_count >= 1
    
    def test_poll_status_not_ready(self, caplog):
        """Test polling when status returns not_ready"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.return_value = {
                'built_in_index_status': 'not_ready',
                'built_in_index_status_msg': 'Knowledge base is not ready'
            }
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False)
            
            # Should call status at least once
            assert mock_client.status.call_count >= 1
    
    def test_poll_status_timeout(self, caplog):
        """Test polling timeout after max_wait_time"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.time") as time_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.return_value = {
                'built_in_index_status': 'rebuilding',
                'built_in_index_status_msg': ''
            }
            
            # Mock time to simulate timeout
            # The polling loop checks: start_time, current_time (elapsed check), then repeats
            # We need to provide enough time values to allow at least one status check before timeout
            time_values = [
                0,    # start_time
                0,    # first current_time (elapsed = 0, continue)
                2,    # after first poll_interval check
                5,    # next current_time (elapsed = 5, continue)
                7,    # after animation sleep
                11,   # next current_time (elapsed = 11, timeout!)
            ]
            # Add more values in case logging or other code calls time.time()
            time_values.extend([11] * 20)
            time_mock.side_effect = time_values
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(
                mock_client,
                'test-kb-id',
                'test-kb',
                False,
                poll_interval=2,
                max_wait_time=10
            )
            
            # Should have attempted to check status at least once before timeout
            assert mock_client.status.call_count >= 1
    
    def test_poll_status_update_mode(self, caplog):
        """Test polling in update mode (is_update=True)"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.return_value = {
                'built_in_index_status': 'ready',
                'built_in_index_status_msg': 'Update completed'
            }
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', True)
            
            # Should call status at least once
            assert mock_client.status.call_count >= 1
    
    def test_poll_status_client_api_exception(self, caplog):
        """Test polling when client raises ClientAPIException"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "API Error"
            mock_client.status.side_effect = ClientAPIException(response=mock_response)
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False)
            
            # Should call status once before exception
            assert mock_client.status.call_count >= 1
    
    def test_poll_status_unexpected_exception(self, caplog):
        """Test polling when an unexpected exception occurs"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.side_effect = Exception("Unexpected error")
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False)
            
            # Should call status once before exception
            assert mock_client.status.call_count >= 1
    
    def test_poll_status_multiple_transitions(self, caplog):
        """Test polling through multiple status transitions"""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            # Simulate multiple status transitions
            mock_client.status.side_effect = [
                {'built_in_index_status': 'update_pending', 'built_in_index_status_msg': ''},
                {'built_in_index_status': 'rebuilding', 'built_in_index_status_msg': ''},
                {'built_in_index_status': 'rebuilding', 'built_in_index_status_msg': ''},
                {'built_in_index_status': 'ready', 'built_in_index_status_msg': 'Completed'}
            ]
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False, poll_interval=1)
            
            # Should call status multiple times
            assert mock_client.status.call_count == 4

    def test_poll_sync_state_stable(self, caplog):
        """Test polling connector sync_state until stable."""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.side_effect = [
                {'sync_state': 'in_progress', 'sync_state_msg': 'Syncing'},
                {'sync_state': 'stable', 'sync_state_msg': 'No sync in progress.'}
            ]
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False, poll_interval=1, use_sync_state=True)
            
            assert mock_client.status.call_count == 2
            assert sleep_mock.call_count >= 1
            console_mock.print.assert_called_once_with("[green]✓[/green] Successfully synced knowledge base 'test-kb': [bold white]No sync in progress.[/bold white]")

    def test_poll_sync_state_failed(self, caplog):
        """Test polling connector sync_state failure."""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.time.sleep") as sleep_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.console") as console_mock:
            
            mock_client = Mock()
            mock_client.status.return_value = {
                'sync_state': 'failed',
                'sync_state_msg': 'Indexing failed'
            }
            
            controller = KnowledgeBaseController()
            controller._poll_knowledge_base_status(mock_client, 'test-kb-id', 'test-kb', False, use_sync_state=True)
            
            assert mock_client.status.call_count >= 1

class TestContentSourceKnowledgeBase:
    @pytest.fixture(autouse=True)
    def enable_knowledge_connectors(self, monkeypatch):
        monkeypatch.setattr(
            "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KNOWLEDGE_CONNECTORS_ENABLED",
            True,
        )

    def test_import_content_source_knowledge_base_polls_sync_state(self, content_source_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.build_connections_map", return_value={"12345": Mock(connection_id="12345")}), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=False), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController._poll_knowledge_base_status") as poll_mock:

            knowledge_base = KnowledgeBase(**content_source_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            # Expected payload reflects the post-resolution state: connection_id is
            # populated by the controller from the connections map, and app_id is
            # stripped (it is a client-side hint not known to the server).
            knowledge_base_json = knowledge_base.model_dump(exclude_none=True)
            knowledge_base_json["content_source"]["connection_id"] = "12345"
            knowledge_base_json["content_source"].pop("app_id", None)
            knowledge_base_json["prioritize_built_in_index"] = True

            mock_client_instance = MockClient(expected_payload=knowledge_base_json)
            mock_client_instance.create_without_files = Mock(return_value={'knowledge_base': mock_client_instance.expected_id})
            mock_client_instance.sync = Mock()
            client_mock.return_value = mock_client_instance

            knowledge_base_controller.import_knowledge_base("test.json", None)

            mock_client_instance.sync.assert_called_once_with(mock_client_instance.expected_id)
            poll_mock.assert_called_once_with(mock_client_instance, mock_client_instance.expected_id, 'test_content_source_knowledge_base', False, use_sync_state=True)

    def test_update_content_source_knowledge_base_with_sync_polls_sync_state(self, content_source_knowledge_base_content):
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=False), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController._poll_knowledge_base_status") as poll_mock:
            knowledge_base = KnowledgeBase(**content_source_knowledge_base_content)
            expected_id = uuid.uuid4()
            expected_payload = knowledge_base.model_dump(exclude_none=True)
            # app_id is stripped from the payload before the server call.
            expected_payload.get("content_source", {}).pop("app_id", None)
            expected_payload["prioritize_built_in_index"] = True
            mock_client_instance = MockClient(expected_payload=expected_payload, expected_id=expected_id)
            mock_client_instance.update_without_files = Mock()
            mock_client_instance.sync = Mock()
            client_mock.return_value = mock_client_instance

            controller = KnowledgeBaseController()
            controller.update_knowledge_base(expected_id, knowledge_base, Path('.'), sync=True)

            mock_client_instance.sync.assert_called_once_with(expected_id)
            poll_mock.assert_called_once_with(mock_client_instance, expected_id, 'test_content_source_knowledge_base', False, use_sync_state=True)

    def test_trigger_sync_polls_sync_state(self):
        mock_client = Mock()
        controller = KnowledgeBaseController()

        with patch.object(controller, '_poll_knowledge_base_status') as poll_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=False):
            controller._trigger_sync(mock_client, 'test-kb-id', 'test-kb')

        mock_client.sync.assert_called_once_with('test-kb-id')
        poll_mock.assert_called_once_with(mock_client, 'test-kb-id', 'test-kb', False, use_sync_state=True)

    def test_trigger_sync_logs_error_and_skips_when_local_without_flag(self, caplog):
        """Local env without --with-ingestion-from-external-source: should error and skip sync."""
        mock_client = Mock()
        controller = KnowledgeBaseController()

        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=True), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.DockerUtils.is_docker_container_running", return_value=False), \
             patch.object(controller, '_poll_knowledge_base_status') as poll_mock, \
             caplog.at_level("ERROR"):
            controller._trigger_sync(mock_client, 'test-kb-id', 'test-kb')

        mock_client.sync.assert_not_called()
        poll_mock.assert_not_called()
        assert "--with-ingestion-from-external-source" in caplog.text

    def test_trigger_sync_proceeds_when_local_with_flag(self):
        """Local env with --with-ingestion-from-external-source (container running): should sync normally."""
        mock_client = Mock()
        controller = KnowledgeBaseController()

        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=True), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.DockerUtils.is_docker_container_running", return_value=True), \
             patch.object(controller, '_poll_knowledge_base_status') as poll_mock:
            controller._trigger_sync(mock_client, 'test-kb-id', 'test-kb')

        mock_client.sync.assert_called_once_with('test-kb-id')
        poll_mock.assert_called_once_with(mock_client, 'test-kb-id', 'test-kb', False, use_sync_state=True)

    def test_import_content_source_skips_sync_when_local_without_flight_svc(self, caplog, content_source_knowledge_base_content):
        """Import of content_source KB in local env without the Flight container: sync must not be triggered."""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.build_connections_map", return_value={"12345": Mock(connection_id="conn-12345")}), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=True), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.DockerUtils.is_docker_container_running", return_value=False), \
             caplog.at_level("ERROR"):

            knowledge_base = KnowledgeBase(**content_source_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            mock_client_instance = MockClient()
            mock_client_instance.create_without_files = Mock(return_value={'knowledge_base': mock_client_instance.expected_id})
            mock_client_instance.sync = Mock()
            client_mock.return_value = mock_client_instance

            knowledge_base_controller.import_knowledge_base("test.json", None)

            mock_client_instance.sync.assert_not_called()
            assert "--with-ingestion-from-external-source" in caplog.text

    def test_update_content_source_skips_sync_when_local_without_flight_svc(self, caplog, content_source_knowledge_base_content):
        """Update of content_source KB in local env without the Flight container: sync must not be triggered."""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=True), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.DockerUtils.is_docker_container_running", return_value=False), \
             caplog.at_level("ERROR"):

            knowledge_base = KnowledgeBase(**content_source_knowledge_base_content)
            expected_id = uuid.uuid4()
            mock_client_instance = MockClient(expected_id=expected_id)
            mock_client_instance.update_without_files = Mock()
            mock_client_instance.sync = Mock()
            client_mock.return_value = mock_client_instance

            controller = KnowledgeBaseController()
            controller.update_knowledge_base(expected_id, knowledge_base, Path('.'), sync=True)

            mock_client_instance.sync.assert_not_called()
            assert "--with-ingestion-from-external-source" in caplog.text


class TestKnowledgeConnectorsDisabled:
    """Tests for behaviour when KNOWLEDGE_CONNECTORS_ENABLED=False (the default)."""

    def test_import_content_source_errors_when_connectors_disabled(self, caplog, content_source_knowledge_base_content):
        """Importing a content_source KB while connectors are disabled must log an error and skip.
        get_client is patched to prevent a live HTTP call from get_by_names(), which runs before
        the per-KB guard and would otherwise attempt to reach a real server."""
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock, \
             caplog.at_level("ERROR"):

            knowledge_base = KnowledgeBase(**content_source_knowledge_base_content)
            from_spec_mock.return_value = knowledge_base

            mock_client_instance = MockClient()
            mock_client_instance.get_by_names = Mock(return_value=[])
            client_mock.return_value = mock_client_instance

            knowledge_base_controller.import_knowledge_base("test.json", None)

            assert "not currently supported" in caplog.text
            assert "KNOWLEDGE_CONNECTORS_ENABLED=true" in caplog.text

    def test_update_content_source_errors_when_connectors_disabled(self, caplog, content_source_knowledge_base_content):
        """Updating a content_source KB while connectors are disabled must log an error and return."""
        with caplog.at_level("ERROR"):
            knowledge_base = KnowledgeBase(**content_source_knowledge_base_content)
            expected_id = uuid.uuid4()

            controller = KnowledgeBaseController()
            controller.update_knowledge_base(expected_id, knowledge_base, Path('.'), sync=True)

            assert "not currently supported" in caplog.text
            assert "KNOWLEDGE_CONNECTORS_ENABLED=true" in caplog.text


class TestContentSourceMultiKBImport:
    @pytest.fixture(autouse=True)
    def enable_knowledge_connectors(self, monkeypatch):
        monkeypatch.setattr(
            "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KNOWLEDGE_CONNECTORS_ENABLED",
            True,
        )

    def test_multi_kb_import_cli_app_id_not_mutated_across_iterations(self, content_source_knowledge_base_content):
        """cli_app_id must stay None across iterations so KB-2 falls back to its own app_id."""
        kb1_content = {
            "spec_version": SpecVersion.V1,
            "name": "kb-one",
            "description": "first",
            "documents": ["doc.pdf"],
            "content_source": {"type": "box", "app_id": "app-kb1"},
        }
        kb2_content = {
            "spec_version": SpecVersion.V1,
            "name": "kb-two",
            "description": "second",
            "documents": ["doc.pdf"],
            "content_source": {"type": "box", "app_id": "app-kb2"},
        }

        conn_map = {
            "app-kb1": Mock(connection_id="conn-kb1"),
            "app-kb2": Mock(connection_id="conn-kb2"),
        }

        resolved_connection_ids = []

        def _create_without_files(payload):
            resolved_connection_ids.append(
                payload.get("content_source", {}).get("connection_id")
            )
            return {"knowledge_base": str(uuid.uuid4())}

        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.build_connections_map", return_value=conn_map), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=False), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController._poll_knowledge_base_status"), \
             patch("ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base.KnowledgeBase.from_spec") as from_spec_mock:

            kb1 = KnowledgeBase(**kb1_content)
            kb2 = KnowledgeBase(**kb2_content)
            from_spec_mock.side_effect = [kb1, kb2]

            mock_client_instance = MockClient()
            mock_client_instance.create_without_files = Mock(side_effect=_create_without_files)
            mock_client_instance.sync = Mock()
            client_mock.return_value = mock_client_instance

            # parse_file returns both KBs; mock it directly
            with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.parse_file", return_value=[kb1, kb2]):
                knowledge_base_controller.import_knowledge_base("test.json", app_id=None)

        # Each KB must resolve to its own connection, not the first KB's app_id
        assert resolved_connection_ids == ["conn-kb1", "conn-kb2"]


class TestConnectorKBExport:
    """Tests for knowledge_base_export() with connector (content_source) KBs."""

    @pytest.fixture(autouse=True)
    def enable_knowledge_connectors(self, monkeypatch):
        monkeypatch.setattr(
            "ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KNOWLEDGE_CONNECTORS_ENABLED",
            True,
        )

    def _make_kb(self, connection_id: str) -> KnowledgeBase:
        """Return a minimal connector KB whose content_source has a resolved connection_id."""
        kb = KnowledgeBase(
            name="my-connector-kb",
            description="box connector",
            content_source=ContentSourceConfig(
                type=ContentSourceType.box,
                connection_id=connection_id,
            ),
            documents=["doc.pdf"],
        )
        kb.spec_version = None
        return kb

    def test_export_writes_app_id_not_connection_id(self, tmp_path):
        """Exported content_source spec must carry app_id and no connection_id."""
        kb = self._make_kb("conn-abc")

        conn = Mock()
        conn.app_id = "my-app-id"

        output_yaml = tmp_path / "kb.yaml"

        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_knowledge_base", return_value=kb), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_id", return_value="some-id"), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.build_connections_map", return_value={"conn-abc": conn}):

            client_mock.return_value = Mock()
            controller = KnowledgeBaseController()
            controller.knowledge_base_export(output_path=str(output_yaml))

        import yaml as _yaml
        spec = _yaml.safe_load(output_yaml.read_text())
        cs = spec.get("content_source", {})
        assert cs.get("app_id") == "my-app-id", "app_id must be written to the spec"
        assert "connection_id" not in cs, "connection_id must not appear in the exported spec"

    def test_export_then_import_roundtrip(self, tmp_path):
        """A spec exported by knowledge_base_export() must be importable without errors."""
        kb = self._make_kb("conn-abc")

        conn = Mock()
        conn.app_id = "my-app-id"
        conn.connection_id = "conn-abc"

        output_yaml = tmp_path / "kb.yaml"

        # --- Export ---
        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client"), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_knowledge_base", return_value=kb), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_id", return_value="some-id"), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.build_connections_map", return_value={"conn-abc": conn}):

            controller = KnowledgeBaseController()
            controller.knowledge_base_export(output_path=str(output_yaml))

        import yaml as _yaml
        spec = _yaml.safe_load(output_yaml.read_text())
        # Confirm the exported spec has app_id (not connection_id) in content_source
        assert spec["content_source"].get("app_id") == "my-app-id"
        assert "connection_id" not in spec["content_source"]

        # --- Import from the exported YAML ---
        # build_connections_map keyed by app_id (as used during import)
        import_conn_map = {"my-app-id": Mock(connection_id="conn-abc")}
        created_payloads = []

        def _create_without_files(payload):
            created_payloads.append(payload)
            return {"knowledge_base": str(uuid.uuid4())}

        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client") as client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.build_connections_map", return_value=import_conn_map), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.is_local_dev", return_value=False), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController._poll_knowledge_base_status"):

            mock_client = MockClient()
            mock_client.create_without_files = Mock(side_effect=_create_without_files)
            mock_client.sync = Mock()
            client_mock.return_value = mock_client

            controller2 = KnowledgeBaseController()
            controller2.import_knowledge_base(str(output_yaml), app_id=None)

        # Exactly one KB should have been created
        assert len(created_payloads) == 1
        # The resolved connection_id must appear in the posted payload
        cs_payload = created_payloads[0].get("content_source", {})
        assert cs_payload.get("connection_id") == "conn-abc", \
            "import must resolve app_id → connection_id and include it in the payload"

    def test_export_unknown_connection_warns_and_preserves_connection_id(self, tmp_path, caplog):
        """When the connection cannot be resolved, a warning is logged and the
        runtime connection_id is left as-is (best-effort export)."""
        kb = self._make_kb("conn-unknown")

        output_yaml = tmp_path / "kb.yaml"

        with patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_client"), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_knowledge_base", return_value=kb), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.KnowledgeBaseController.get_id", return_value="some-id"), \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.build_connections_map", return_value={}), \
             caplog.at_level("WARNING"):

            controller = KnowledgeBaseController()
            controller.knowledge_base_export(output_path=str(output_yaml))

        assert "not found" in caplog.text or "unable to resolve" in caplog.text


# ---------------------------------------------------------------------------
# Helpers shared by the validation tests
# ---------------------------------------------------------------------------

def _make_mock_response(text: str | None, status_code: int = 400):
    """Build a minimal requests.Response-like mock for ClientAPIException."""
    resp = Mock()
    resp.status_code = status_code
    resp.text = text
    return resp


def _make_client_api_exception(response_text: str | None = None, status_code: int = 400) -> ClientAPIException:
    resp = _make_mock_response(response_text, status_code)
    exc = ClientAPIException(response=resp)
    return exc


# ---------------------------------------------------------------------------
# Unit tests for _validate_connection_creds
# ---------------------------------------------------------------------------

class TestValidateConnectionCreds:
    """Unit tests for KnowledgeBaseController._validate_connection_creds."""

    def _controller_with_mock_client(self, validate_side_effect=None):
        """Return a controller whose KB client's validate_creds is a mock."""
        controller = KnowledgeBaseController()
        mock_client = Mock()
        if validate_side_effect is not None:
            mock_client.validate_creds.side_effect = validate_side_effect
        controller.client = mock_client
        return controller, mock_client

    # ------------------------------------------------------------------
    # get_vector_index_type helper
    # ------------------------------------------------------------------

    def test_get_vector_index_type_milvus(self):
        index_config = IndexConnection(
            connection_id="conn-1",
            milvus=MilvusConnection(grpc_host="host", grpc_port="30564", collection="col", database="db"),
        )
        assert KnowledgeBaseController.get_vector_index_type(index_config) == "milvus"

    def test_get_vector_index_type_elastic_search(self):
        index_config = IndexConnection(
            connection_id="conn-1",
            elastic_search=ElasticSearchConnection(url="https://es.example.com", index="idx"),
        )
        assert KnowledgeBaseController.get_vector_index_type(index_config) == "elastic_search"

    def test_get_vector_index_type_open_search(self):
        index_config = IndexConnection(
            connection_id="conn-1",
            open_search=OpenSearchConnection(url="https://os.example.com", index="idx"),
        )
        assert KnowledgeBaseController.get_vector_index_type(index_config) == "open_search"

    def test_get_vector_index_type_astradb(self):
        index_config = IndexConnection(
            connection_id="conn-1",
            astradb=AstraDBConnection(api_endpoint="https://astra.example.com", data_type="vector"),
        )
        assert KnowledgeBaseController.get_vector_index_type(index_config) == "astradb"

    def test_get_vector_index_type_custom_search(self):
        index_config = IndexConnection(
            connection_id="conn-1",
            custom_search=CustomSearchConnection(url="https://custom.example.com"),
        )
        assert KnowledgeBaseController.get_vector_index_type(index_config) == "custom_search"

    def test_get_vector_index_type_none_when_no_connection_type_set(self):
        # connection_id present but no recognised connection type field set
        index_config = IndexConnection(connection_id="conn-1")
        assert KnowledgeBaseController.get_vector_index_type(index_config) is None

    # ------------------------------------------------------------------
    # get_url_and_port_from_index_config helper
    # ------------------------------------------------------------------

    def test_get_url_and_port_milvus(self):
        index_config = IndexConnection(
            milvus=MilvusConnection(grpc_host="milvus.host", grpc_port="30564", collection="col", database="db"),
        )
        url, port = KnowledgeBaseController.get_url_and_port_from_index_config(index_config)
        assert url == "milvus.host"
        assert port == "30564"

    def test_get_url_and_port_elastic_search(self):
        index_config = IndexConnection(
            elastic_search=ElasticSearchConnection(url="https://es.example.com", port="9200", index="idx"),
        )
        url, port = KnowledgeBaseController.get_url_and_port_from_index_config(index_config)
        assert url == "https://es.example.com"
        assert port == "9200"

    def test_get_url_and_port_open_search(self):
        index_config = IndexConnection(
            open_search=OpenSearchConnection(url="https://os.example.com", port="31871", index="idx"),
        )
        url, port = KnowledgeBaseController.get_url_and_port_from_index_config(index_config)
        assert url == "https://os.example.com"
        assert port == "31871"

    def test_get_url_and_port_custom_search(self):
        index_config = IndexConnection(
            custom_search=CustomSearchConnection(url="https://custom.example.com"),
        )
        url, port = KnowledgeBaseController.get_url_and_port_from_index_config(index_config)
        assert url == "https://custom.example.com"
        assert port is None

    def test_get_url_and_port_astradb(self):
        index_config = IndexConnection(
            astradb=AstraDBConnection(api_endpoint="https://astra.example.com", port="443", data_type="vector"),
        )
        url, port = KnowledgeBaseController.get_url_and_port_from_index_config(index_config)
        assert url == "https://astra.example.com"
        assert port == "443"

    def test_get_url_and_port_no_connection_type(self):
        index_config = IndexConnection()
        url, port = KnowledgeBaseController.get_url_and_port_from_index_config(index_config)
        assert url is None
        assert port is None

    # ------------------------------------------------------------------
    # _validate_connection_creds: skipped paths
    # ------------------------------------------------------------------

    def test_validate_skipped_when_no_connection_id(self):
        """_validate_connection_creds returns immediately when connection_id is absent."""
        controller, mock_client = self._controller_with_mock_client()
        index_config = IndexConnection(
            milvus=MilvusConnection(grpc_host="h", grpc_port="p", collection="c", database="d"),
        )  # no connection_id
        controller._validate_connection_creds(index_config)
        mock_client.validate_creds.assert_not_called()

    def test_validate_skipped_when_vector_index_type_is_none(self):
        """_validate_connection_creds returns immediately when no recognised connection type is set."""
        controller, mock_client = self._controller_with_mock_client()
        # Has a connection_id but no milvus/elastic/etc field populated
        index_config = IndexConnection(connection_id="conn-1")
        controller._validate_connection_creds(index_config)
        mock_client.validate_creds.assert_not_called()

    # ------------------------------------------------------------------
    # _validate_connection_creds: successful call
    # ------------------------------------------------------------------

    def test_validate_succeeds_and_calls_client(self):
        """Happy path: validate_creds is called with the right arguments."""
        controller, mock_client = self._controller_with_mock_client()
        index_config = IndexConnection(
            connection_id="conn-42",
            milvus=MilvusConnection(grpc_host="milvus.host", grpc_port="30564", collection="col", database="db"),
        )
        controller._validate_connection_creds(index_config)  # must not raise
        mock_client.validate_creds.assert_called_once_with(
            connection_id="conn-42",
            vector_index_type="milvus",
            url="milvus.host",
            port="30564",
        )

    # ------------------------------------------------------------------
    # _validate_connection_creds: ClientAPIException → ValueError
    # ------------------------------------------------------------------

    def test_validate_raises_value_error_on_api_exception_with_json_detail(self):
        """ClientAPIException with a JSON body containing 'detail' raises ValueError using that message."""
        body = json.dumps({"detail": "invalid token"})
        exc = _make_client_api_exception(response_text=body)
        controller, _ = self._controller_with_mock_client(validate_side_effect=exc)
        index_config = IndexConnection(
            connection_id="conn-1",
            milvus=MilvusConnection(grpc_host="h", grpc_port="p", collection="c", database="d"),
        )
        with pytest.raises(ValueError, match="invalid token"):
            controller._validate_connection_creds(index_config)

    def test_validate_raises_value_error_on_api_exception_with_plain_text_body(self):
        """ClientAPIException with a plain-text (non-JSON) body uses a generic error message."""
        exc = _make_client_api_exception(response_text="Forbidden")
        controller, _ = self._controller_with_mock_client(validate_side_effect=exc)
        index_config = IndexConnection(
            connection_id="conn-1",
            open_search=OpenSearchConnection(url="https://os.example.com", index="idx"),
        )
        with pytest.raises(ValueError, match="Unexpected server error"):
            controller._validate_connection_creds(index_config)

    def test_validate_raises_value_error_on_api_exception_with_malformed_json_body(self):
        """ClientAPIException whose body looks like JSON but isn't valid uses a generic error message."""
        exc = _make_client_api_exception(response_text="{not valid json")
        controller, _ = self._controller_with_mock_client(validate_side_effect=exc)
        index_config = IndexConnection(
            connection_id="conn-1",
            elastic_search=ElasticSearchConnection(url="https://es.example.com", index="idx"),
        )
        with pytest.raises(ValueError, match="Unexpected server error"):
            controller._validate_connection_creds(index_config)

    def test_validate_raises_value_error_on_api_exception_with_no_response_body(self):
        """ClientAPIException with an empty response body still raises a ValueError."""
        exc = _make_client_api_exception(response_text=None)
        controller, _ = self._controller_with_mock_client(validate_side_effect=exc)
        index_config = IndexConnection(
            connection_id="conn-1",
            custom_search=CustomSearchConnection(url="https://custom.example.com"),
        )
        with pytest.raises(ValueError, match=r"Connection credential validation failed"):
            controller._validate_connection_creds(index_config)

    def test_validate_raises_value_error_on_api_exception_with_empty_string_body(self):
        """ClientAPIException with an empty-string body (falsy) still raises a ValueError."""
        exc = _make_client_api_exception(response_text="")
        controller, _ = self._controller_with_mock_client(validate_side_effect=exc)
        index_config = IndexConnection(
            connection_id="conn-1",
            astradb=AstraDBConnection(api_endpoint="https://astra.example.com", data_type="vector"),
        )
        with pytest.raises(ValueError, match=r"Connection credential validation failed"):
            controller._validate_connection_creds(index_config)


# ---------------------------------------------------------------------------
# Integration-style tests: validation failure propagation on create / update
# ---------------------------------------------------------------------------

class TestValidationFailurePropagation:
    """Verify that a ValueError from _validate_connection_creds is caught at
    both call-sites (import_knowledge_base / update_knowledge_base) and that
    the KB is skipped / the update aborts gracefully."""

    # Fixture data: external KB with a milvus index and a connection_id already set
    @pytest.fixture
    def kb_with_connection(self):
        return {
            "spec_version": SpecVersion.V1,
            "name": "test_external_kb",
            "description": "desc",
            "conversational_search_tool": {
                "index_config": [
                    {
                        "connection_id": "conn-bad",
                        "milvus": {
                            "grpc_host": "cf94d93e.example.com",
                            "grpc_port": "30564",
                            "database": "db",
                            "collection": "col",
                            "embedding_model_id": "sentence-transformers/all-minilm-l12-v2",
                        },
                    }
                ]
            },
        }

    def test_import_logs_error_and_skips_kb_on_validation_failure(self, caplog, kb_with_connection):
        """import_knowledge_base: bad creds → logger.error, KB creation skipped."""
        controller = KnowledgeBaseController()
        kb = KnowledgeBase(**kb_with_connection)

        with patch.object(controller, "get_client") as get_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.parse_file",
                   return_value=[kb]):

            mock_client = Mock()
            mock_client.get_by_names.return_value = []  # KB doesn't exist yet → create path
            mock_client.validate_creds.side_effect = _make_client_api_exception(
                response_text=json.dumps({"detail": "bad credentials"})
            )
            get_client_mock.return_value = mock_client

            controller.import_knowledge_base("test.yaml", app_id=None)

        assert "bad credentials" in caplog.text
        mock_client.create.assert_not_called()
        mock_client.create_built_in.assert_not_called()

    def test_import_logs_error_and_skips_kb_on_validation_failure_update_path(self, caplog, kb_with_connection):
        """import_knowledge_base: existing KB with bad creds → logger.error, update skipped."""
        controller = KnowledgeBaseController()
        kb = KnowledgeBase(**kb_with_connection)
        existing_id = uuid.uuid4()

        with patch.object(controller, "get_client") as get_client_mock, \
             patch("ibm_watsonx_orchestrate.cli.commands.knowledge_bases.knowledge_bases_controller.parse_file",
                   return_value=[kb]):

            mock_client = Mock()
            # Pretend the KB already exists so the update branch is taken
            mock_client.get_by_names.return_value = [{"name": kb.name, "id": existing_id, "workspace_id": None}]
            mock_client.validate_creds.side_effect = _make_client_api_exception(
                response_text=json.dumps({"detail": "bad credentials"})
            )
            get_client_mock.return_value = mock_client

            controller.import_knowledge_base("test.yaml", app_id=None)

        assert "bad credentials" in caplog.text
        mock_client.update.assert_not_called()
        mock_client.update_with_documents.assert_not_called()

    def test_update_knowledge_base_logs_error_and_returns_on_validation_failure(self, caplog, kb_with_connection):
        """update_knowledge_base: bad creds → logger.error, no update call made."""
        controller = KnowledgeBaseController()
        kb = KnowledgeBase(**kb_with_connection)
        kb_id = uuid.uuid4()

        with patch.object(controller, "get_client") as get_client_mock:
            mock_client = Mock()
            mock_client.validate_creds.side_effect = _make_client_api_exception(
                response_text=json.dumps({"detail": "invalid api key"})
            )
            get_client_mock.return_value = mock_client

            controller.update_knowledge_base(kb_id, kb=kb, file_dir=Path("/tmp"))

        assert "invalid api key" in caplog.text
        mock_client.update.assert_not_called()
        mock_client.update_with_documents.assert_not_called()
        mock_client.status.assert_not_called()
