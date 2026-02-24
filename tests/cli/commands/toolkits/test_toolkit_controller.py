from unittest.mock import patch, MagicMock, mock_open
from ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller import ToolkitController, ToolkitKind, get_connection_id
from ibm_watsonx_orchestrate.agent_builder.toolkits.types import RemoteMcpModel, LocalMcpModel, ToolkitSource, Language, ToolkitTransportKind, ToolkitSpec
from ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit import BaseToolkit
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionSecurityScheme
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.agent_builder.agents import SpecVersion
from typing import List
from typer import BadParameter
from pathlib import Path
import pytest

class MockConnectionConfig:
    def __init__(self, security_scheme: ConnectionSecurityScheme):
        self.security_scheme = security_scheme

class MockConnectionGetReponse:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id

class MockListConfigResponse:
    def __init__(self, connection_id: str, app_id: str):
        self.connection_id = connection_id
        self.app_id = app_id

class MockConnectionClient:
    def __init__(
            self,
            get_config_draft_res: MockConnectionConfig | None = None,
            get_config_live_res: MockConnectionConfig | None = None,
            get_res: MockConnectionGetReponse | None = None,
            list_res: List[MockListConfigResponse] = []
        ):
        self.get_config_draft_res = get_config_draft_res
        self.get_config_live_res = get_config_live_res
        self.get_res = get_res
        self.list_res = list_res

    def get_config(self, app_id: str, env: str) -> MockConnectionConfig:
        if env == 'draft':
            return self.get_config_draft_res
        elif env == 'live':
            return self.get_config_live_res
    
    def get(self, app_id: str) -> MockConnectionGetReponse:
        return self.get_res
    
    def list(self) -> List[MockListConfigResponse]:
        return self.list_res

class MockToolkitsClient(MagicMock):
    def __init__(self,
            get_draft_res: List[dict] = [],
            create_res: dict | None = None,
            list_tools_res: List[str] = [],
            get_res: List[dict] = [],
            *args,
            **kwargs
        ):
        super().__init__(*args, **kwargs)
        self.get_draft_res = get_draft_res
        self.create_res = create_res
        self.list_tools_res = list_tools_res
        self.get_res = get_res

        self.create_toolkit = MagicMock()
        self.upload = MagicMock()
        self.delete = MagicMock()

    def get_draft_by_name(self, toolkit_name: str) -> List[dict] | None:
        return  self.get_draft_res
    
    def list_tools(self, zip_file_path: str, command: str, args: List[str]) -> str:
        return self.list_tools_res
    
    def get(self):
        return self.get_res

class TestGetConnectionId:
    mock_app_id = "test_app_id"
    mock_conn_id = "123456789abc"
    
    @pytest.mark.parametrize(
            "security_scheme",
            [
                ConnectionSecurityScheme.KEY_VALUE,
                ConnectionSecurityScheme.BASIC_AUTH,
                ConnectionSecurityScheme.API_KEY_AUTH,
                ConnectionSecurityScheme.BEARER_TOKEN,
                ConnectionSecurityScheme.OAUTH2,
            ]
    )
    def test_get_connection_id(self, security_scheme):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connections_client") as mock_get_connections_client:
            mock_config_response = MockConnectionConfig(security_scheme=security_scheme)
            mock_get_conn_response = MockConnectionGetReponse(connection_id=self.mock_conn_id)
            mock_connections_client = MockConnectionClient(
                get_config_draft_res=mock_config_response,
                get_config_live_res=mock_config_response,
                get_res=mock_get_conn_response
            )
            mock_get_connections_client.return_value = mock_connections_client

            result = get_connection_id(self.mock_app_id)
        
        assert result == self.mock_conn_id

    def test_get_connection_id_no_connection(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connections_client") as mock_get_connections_client:
            mock_config_response = MockConnectionConfig(security_scheme=ConnectionSecurityScheme.KEY_VALUE)
            mock_get_conn_response = None
            mock_connections_client = MockConnectionClient(
                get_config_draft_res=mock_config_response,
                get_config_live_res=mock_config_response,
                get_res=mock_get_conn_response
            )
            mock_get_connections_client.return_value = mock_connections_client

            with pytest.raises(SystemExit):
                get_connection_id(self.mock_app_id)
    

class TestToolkitControllerGetClient:
    def test_get_client_single(self):
        mock_client = MagicMock()
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client", return_value=mock_client):
            tc = ToolkitController()
            assert tc.client is None
            client = tc.get_client()
        
        assert tc.client == client
        assert tc.client != None
    
    def test_get_client_multiple(self):
        mock_client = MagicMock()
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client", return_value=mock_client):
            tc = ToolkitController()
            assert tc.client is None
            client1 = tc.get_client()
            client2 = tc.get_client()
        
        assert tc.client == client1
        assert tc.client == client2
        assert client1 == client2
        assert tc.client != None

class TestToolkitControllerCreateToolkit:
    mock_conn_id = "123456789abc"
    mock_name = "test_toolkit"
    mock_description = "test_description"
    mock_file = "test_file"

    def test_create_toolkit_local_files_command_json_list(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command='["node", "dist/index.js", "--transport", "stdio"]',
            tools="*",
            app_id=["test_conn"]
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file

    def test_create_toolkit_local_files_command_string(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="node dist/index.js --transport stdio",
            tools="*",
            app_id=["test_conn"]
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file
    
    def test_create_toolkit_local_files_command_json(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="{\"test\":\"123\"}",
            tools="*",
            app_id=["test_conn"]
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "{\"test\":\"123\"}"
        assert spec.mcp.args == []
        assert spec.mcp.package_root == self.mock_file
        
    def test_create_toolkit_local_files_string_app_id(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="node dist/index.js --transport stdio",
            tools="*",
            app_id="test_conn"
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file
    
    def test_create_toolkit_local_files_no_connections(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="node dist/index.js --transport stdio",
            tools="*"
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == {}
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file
    
    def test_create_toolkit_local_files_single_tool(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="node dist/index.js --transport stdio",
            tools="mock_tool",
            app_id=["test_conn"]
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["mock_tool"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file

    def test_create_toolkit_local_files_multi_tools(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="node dist/index.js --transport stdio",
            tools="mock_tool1, mock_tool2",
            app_id=["test_conn"]
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["mock_tool1", "mock_tool2"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file

    def test_create_toolkit_local_files_no_tools(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="node dist/index.js --transport stdio",
            app_id=["test_conn"]
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == None
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file
        
    def test_create_toolkit_local_files_empty_tool(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package_root=self.mock_file,
            command="node dist/index.js --transport stdio",
            app_id=["test_conn"],
            tools=""
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == None
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.FILES
        assert spec.mcp.command == "node"
        assert spec.mcp.args == ["dist/index.js", "--transport", "stdio"]
        assert spec.mcp.package_root == self.mock_file


    def test_create_toolkit_local_registry_with_command(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            command="dummy_command -y mock_package",
            app_id=["test_conn"],
            tools="*"
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.PUBLIC_REGISTRY
        assert spec.mcp.command == "dummy_command"
        assert spec.mcp.args == ["-y", "mock_package"]
        assert spec.mcp.package == None
    
    def test_create_toolkit_local_registry_with_package(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package="mock_package",
            language=Language.NODE,
            app_id=["test_conn"],
            tools="*"
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.PUBLIC_REGISTRY
        assert spec.mcp.command == "npx"
        assert spec.mcp.args == ["-y", "mock_package"]
        assert spec.mcp.package == "mock_package"
    
    def test_create_toolkit_local_registry_with_package_python(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package="mock_package",
            language=Language.PYTHON,
            app_id=["test_conn"],
            tools="*"
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.PUBLIC_REGISTRY
        assert spec.mcp.command == "python"
        assert spec.mcp.args == ["-m", "mock_package"]
        assert spec.mcp.package == "mock_package"
    
    def test_create_toolkit_local_registry_with_command_override(self):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            package="mock_package",
            language=Language.NODE,
            command = "dummy_command -y mock_package",
            app_id=["test_conn"],
            tools="*"
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, LocalMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.source == ToolkitSource.PUBLIC_REGISTRY
        assert spec.mcp.command == "dummy_command"
        assert spec.mcp.args == ["-y", "mock_package"]
        assert spec.mcp.package == "mock_package"

    @pytest.mark.parametrize(
        "transport",
        [
            ToolkitTransportKind.STREAMABLE_HTTP,
            ToolkitTransportKind.SSE
        ]
    )
    def test_create_toolkit_remote(self, transport):
        tc = ToolkitController()
        toolkit = tc.create_toolkit(
            kind=ToolkitKind.MCP,
            name=self.mock_name,
            description=self.mock_description,
            url="mock_url",
            transport=transport,
            app_id=["test_conn"],
            tools="*"
        )
        
        spec = toolkit.__toolkit_spec__

        assert spec.name == self.mock_name
        assert spec.description == self.mock_description
        assert isinstance(spec.mcp, RemoteMcpModel)
        assert spec.mcp.tools == ["*"]
        assert spec.mcp.connections == ["test_conn"]
        assert spec.mcp.server_url == "mock_url"
        assert spec.mcp.transport == transport
    
    def test_create_toolkit_local_registry_missing_language(self):
        tc = ToolkitController()
        with pytest.raises(BadRequest) as e:
            tc.create_toolkit(
                kind=ToolkitKind.MCP,
                name=self.mock_name,
                description=self.mock_description,
                package="mock_package",
                app_id=["test_conn"],
                tools="*"
            )
        
        assert "Unable to infer start up command" in str(e)
    
    def test_create_toolkit_no_package_or_command(self):
        tc = ToolkitController()
        with pytest.raises(BadRequest) as e:
            tc.create_toolkit(
                kind=ToolkitKind.MCP,
                name=self.mock_name,
                description=self.mock_description,
                app_id=["test_conn"],
                tools="*"
            )
        
        assert "You must provide either 'package', 'package-root' or 'command'." in str(e)

    def test_create_toolkit_local_files_missing_command(self):
        tc = ToolkitController()
        with pytest.raises(BadRequest) as e:
            tc.create_toolkit(
                kind=ToolkitKind.MCP,
                name=self.mock_name,
                description=self.mock_description,
                package_root=self.mock_file,
                tools="*",
                app_id=["test_conn"]
            )
        
        assert "Error: 'command' must be provided when 'package-root' is specified." in str(e)
    
    def test_create_toolkit_local_package_and_package_root(self):
        tc = ToolkitController()
        with pytest.raises(BadRequest) as e:
            tc.create_toolkit(
                kind=ToolkitKind.MCP,
                name=self.mock_name,
                description=self.mock_description,
                package_root=self.mock_file,
                package="dummy_package",
                language=Language.NODE,
                tools="*",
                app_id=["test_conn"]
            )
        
        assert "Please choose either 'package-root' or 'package' but not both." in str(e)

    @pytest.mark.parametrize(
        "transport",
        [
            ToolkitTransportKind.STREAMABLE_HTTP,
            ToolkitTransportKind.SSE
        ]
    )
    def test_create_toolkit_remote_missing_url(self, transport):
        tc = ToolkitController()

        with pytest.raises(BadRequest) as e:
            tc.create_toolkit(
                kind=ToolkitKind.MCP,
                name=self.mock_name,
                description=self.mock_description,
                transport=transport,
                app_id=["test_conn"],
                tools="*"
            )
        
        assert "Both 'url' and 'transport' must be provided together for remote MCP." in str(e)
    
    def test_create_toolkit_remote_missing_transport(self):
        tc = ToolkitController()

        with pytest.raises(BadRequest) as e:
            tc.create_toolkit(
                kind=ToolkitKind.MCP,
                name=self.mock_name,
                description=self.mock_description,
                url="test_url",
                app_id=["test_conn"],
                tools="*"
            )
        
        assert "Both 'url' and 'transport' must be provided together for remote MCP." in str(e)
    
    def test_create_toolkit_remote_forbidden_options(self):
        tc = ToolkitController()

        with pytest.raises(BadRequest) as e:
            tc.create_toolkit(
                kind=ToolkitKind.MCP,
                name=self.mock_name,
                description=self.mock_description,
                url="test_url",
                app_id=["test_conn"],
                transport=ToolkitTransportKind.STREAMABLE_HTTP,
                package="mock_package",
                package_root=self.mock_file,
                language=Language.NODE,
                command="dummy_command",
                tools="*"
            )
        
        assert "When using 'url' and 'transport' for a remote MCP, you cannot specify" in str(e)

class TestToolkitControllerPublishOrUpdateToolkits:
    mock_conn_id = "123456789abc"
    mock_app_id = "123456789abc"
    mock_name = "test_toolkit"
    mock_description = "test_description"
    mock_file = "test_file"
    mock_command = "dummy_command"
    mock_url = "mock_server"
    mock_id = "987654321def"

    local_files_toolkit_mcp_spec = LocalMcpModel(
        tools=["*"],
        connections={mock_app_id},
        source=ToolkitSource.FILES,
        command="dummy_command",
        args=["arg1", "arg2"],
        package_root=mock_file
    )

    local_registry_toolkit_mcp_spec = LocalMcpModel(
        tools=["*"],
        connections={mock_app_id},
        source=ToolkitSource.PUBLIC_REGISTRY,
        command="dummy_command",
        args=["arg1", "arg2"],
        package="mock_package"
    )

    remote_toolkit_mcp_spec = RemoteMcpModel(
        tools=["*"],
        connections={mock_app_id},
        server_url=mock_url,
        transport=ToolkitTransportKind.STREAMABLE_HTTP
    )

    @pytest.mark.parametrize(
            "mcp_spec",
            [
                local_files_toolkit_mcp_spec,
                local_registry_toolkit_mcp_spec,
                remote_toolkit_mcp_spec
            ]
    )
    def test_publish_or_update_toolkits(self, mcp_spec):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isdir") as mock_is_dir, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_is_dir.return_value = True
            mock_client = MockToolkitsClient(create_res={"id": self.mock_id})
            mock_get_client.return_value = mock_client

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            tc = ToolkitController()
            tc.publish_or_update_toolkits([toolkit])

            expected_payload = {
                "name": self.mock_name,
                "description": self.mock_description,
                "mcp": mcp_spec.model_dump(exclude_none=True)
            }

            mock_client.create_toolkit.assert_called_once_with(expected_payload)
    
    def test_publish_or_update_toolkits_with_zip(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isfile") as mock_isfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.zipfile.is_zipfile") as mock_is_zipfile, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_isfile.return_value = True
            mock_is_zipfile.return_value = True
            mock_client = MockToolkitsClient(create_res={"id": self.mock_id})
            mock_get_client.return_value = mock_client

            mcp_spec = self.local_files_toolkit_mcp_spec.model_copy()
            mcp_spec.package_root = mcp_spec.package_root + ".zip"

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            tc = ToolkitController()
            tc.publish_or_update_toolkits([toolkit])

            expected_payload = {
                "name": self.mock_name,
                "description": self.mock_description,
                "mcp": mcp_spec.model_dump(exclude_none=True)
            }

            mock_client.create_toolkit.assert_called_once_with(expected_payload)
    
    def test_publish_or_update_toolkits_local_no_tools(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isdir") as mock_is_dir, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_is_dir.return_value = True
            mock_client = MockToolkitsClient(
                create_res={"id": self.mock_id},
                list_tools_res=["mock_tool_1", "mock_tool_2"]
            )
            mock_get_client.return_value = mock_client

            mcp_spec = self.local_files_toolkit_mcp_spec.model_copy()
            mcp_spec.tools = None

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            tc = ToolkitController()
            tc.publish_or_update_toolkits([toolkit])

            expected_payload = {
                "name": self.mock_name,
                "description": self.mock_description,
                "mcp": mcp_spec.model_dump(exclude_none=True)
            }

            mock_client.create_toolkit.assert_called_once_with(expected_payload)
    
    def test_publish_or_update_toolkits_remote_no_tools(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isdir") as mock_is_dir, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_is_dir.return_value = True
            mock_client = MockToolkitsClient(
                create_res={"id": self.mock_id}
            )
            mock_get_client.return_value = mock_client

            mcp_spec = self.remote_toolkit_mcp_spec.model_copy()
            mcp_spec.tools = None

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            tc = ToolkitController()
            tc.publish_or_update_toolkits([toolkit])

            expected_payload = {
                "name": self.mock_name,
                "description": self.mock_description,
                "mcp": mcp_spec.model_dump(exclude_none=True)
            }

            mock_client.create_toolkit.assert_called_once_with(expected_payload)
    
    def test_publish_or_update_toolkits_update(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client:
            mock_get_client.return_value = MockToolkitsClient(
                get_draft_res=[{"id": self.mock_id}]
            )
            
            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=self.local_files_toolkit_mcp_spec
                )
            )

            with pytest.raises(SystemExit):
                tc = ToolkitController()
                tc.publish_or_update_toolkits([toolkit])
        
        captured = caplog.text

        assert "Existing toolkit found with name" in str(captured)
    
    def test_publish_or_update_toolkits_local_invalid_folder(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_get_client.return_value = MockToolkitsClient()
            
            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=self.local_files_toolkit_mcp_spec
                )
            )

            with pytest.raises(SystemExit):
                tc = ToolkitController()
                tc.publish_or_update_toolkits([toolkit])
        
        captured = caplog.text

        assert "Unable to find a valid directory or zip file" in str(captured)
    
    def test_publish_or_update_toolkits_alias_app_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isdir") as mock_is_dir, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_is_dir.return_value = True
            mock_client = MockToolkitsClient(
                create_res={"id": self.mock_id},
                list_tools_res=["mock_tool_1", "mock_tool_2"]
            )
            mock_get_client.return_value = mock_client

            mcp_spec = self.local_files_toolkit_mcp_spec.model_copy()
            mcp_spec.connections = ["test_conn=test_conn1"]

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            tc = ToolkitController()
            tc.publish_or_update_toolkits([toolkit])

            expected_payload = {
                "name": self.mock_name,
                "description": self.mock_description,
                "mcp": mcp_spec.model_dump(exclude_none=True)
            }

            mock_client.create_toolkit.assert_called_once_with(expected_payload)
            assert mcp_spec.connections == {"test_conn": self.mock_conn_id}

    def test_publish_or_update_toolkits_sanitize_app_id(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isdir") as mock_is_dir, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_is_dir.return_value = True
            mock_client = MockToolkitsClient(
                create_res={"id": self.mock_id},
                list_tools_res=["mock_tool_1", "mock_tool_2"]
            )
            mock_get_client.return_value = mock_client

            mcp_spec = self.local_files_toolkit_mcp_spec.model_copy()
            mcp_spec.connections = ["test-conn"]

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            tc = ToolkitController()
            tc.publish_or_update_toolkits([toolkit])

            expected_payload = {
                "name": self.mock_name,
                "description": self.mock_description,
                "mcp": mcp_spec.model_dump(exclude_none=True)
            }
            mock_client.create_toolkit.assert_called_once_with(expected_payload)
            assert mcp_spec.connections == {"test_conn": self.mock_conn_id}
    
    def test_publish_or_update_toolkits_invalid_app_id_multiple_equals(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isdir") as mock_is_dir, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_is_dir.return_value = True

            mcp_spec = self.local_files_toolkit_mcp_spec.model_copy()
            mcp_spec.connections = ["test-conn=test_conn=123"]

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            with pytest.raises(BadParameter) as e:
                tc = ToolkitController()
                tc.publish_or_update_toolkits([toolkit])
            
            assert "This is likely caused by having mutliple equal signs" in str(e)
    
    def test_publish_or_update_toolkits_invalid_app_id_empty(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.os.path.isdir") as mock_is_dir, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connection_id") as mock_get_connection_id:
            mock_get_connection_id.return_value = self.mock_conn_id
            mock_is_dir.return_value = True

            mcp_spec = self.local_files_toolkit_mcp_spec.model_copy()
            mcp_spec.connections = ["test-conn="]

            toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=mcp_spec
                )
            )

            with pytest.raises(BadParameter) as e:
                tc = ToolkitController()
                tc.publish_or_update_toolkits([toolkit])
            
            assert "app-id cannot be empty or whitespace" in str(e)

class TestToolkitControllerRemoveToolkit:
    mock_name = "mock_name"
    mock_id = "987654321def"
    def test_remove_toolkit(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client:
            mock_get_client.return_value = MockToolkitsClient(
                get_draft_res=[{"id": self.mock_id}]
            )

            tc = ToolkitController()
            tc.remove_toolkit(name=self.mock_name)

    def test_remove_toolkit_multiple_candidates(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client:
            mock_get_client.return_value = MockToolkitsClient(
                get_draft_res=[{"id": self.mock_id},{"id": self.mock_id}]
            )

            tc = ToolkitController()
            with pytest.raises(SystemExit):
                tc.remove_toolkit(name=self.mock_name)
        
        captured = caplog.text
        assert "Multiple existing toolkits found with name" in str(captured)

    def test_remove_toolkit_no_candidates(self, caplog):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client:
            mock_get_client.return_value = MockToolkitsClient(
                get_draft_res=[]
            )

            tc = ToolkitController()
            tc.remove_toolkit(name=self.mock_name)
        
        captured = caplog.text
        assert "No toolkit named" in str(captured)

class TestToolkitControllerListToolkits:
    mock_name = "mock_name"
    mock_id = "987654321def"
    mock_description = "mock_description"

    def test_list_toolkits(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.instantiate_client") as mock_instantiate_client, \
            patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.get_connections_client") as mock_get_connections_client:

            mock_instantiate_client.return_value = MagicMock(
                get_drafts_by_ids=MagicMock(return_value=[
                    {"id": "123456789abc", "name": "tool_1"},
                    {"id": "987654321def", "name": "tool_2"}
                ])
            )

            mock_get_connections_client.return_value = MockConnectionClient(
                list_res=[
                    MockListConfigResponse(connection_id= "123456789abc", app_id= "app_1"),
                    MockListConfigResponse(connection_id= "987654321def", app_id= "app_2")
                ]
            )

            mock_get_client.return_value = MockToolkitsClient(
                get_res=[{
                    "name": self.mock_name,
                    "id": self.mock_id,
                    "description": self.mock_description,
                    "tools": ["123456789abc", "987654321def"],
                    "mcp": RemoteMcpModel(
                        server_url="mock_url",
                        transport=ToolkitTransportKind.STREAMABLE_HTTP,
                        connections={"app_1": "123456789abc", "app_2": "987654321def"}
                    )
                }]
            )

            tc = ToolkitController()
            tc.list_toolkits()

    def test_list_toolkits_verbose(self):
        with patch("ibm_watsonx_orchestrate.cli.commands.toolkit.toolkit_controller.ToolkitController.get_client") as mock_get_client:

            mock_get_client.return_value = MockToolkitsClient(
                get_res=[{
                    "name": self.mock_name,
                    "id": self.mock_id,
                    "description": self.mock_description,
                    "tools": ["123456789abc", "987654321def"],
                    "mcp": RemoteMcpModel(
                        server_url="mock_url",
                        transport=ToolkitTransportKind.STREAMABLE_HTTP,
                        connections={"app_1": "123456789abc", "app_2": "987654321def"}
                    )
                }]
            )

            tc = ToolkitController()
            tc.list_toolkits(verbose=True)

class TestToolkitControllerImportToolkit:
    mock_name = "test_name"
    mock_description = "test_description"

    def test_import_toolkit_yaml(self):
        with patch.object(Path, "exists", return_value=True), \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.safe_open", mock_open()) as mock_safe_open, \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.yaml_safe_load") as mock_yaml_loader:

            mock_tool_content = {
                "spec_version": SpecVersion.V1,
                "name": self.mock_name,
                "description": self.mock_description,
                "package": "test_pacakge",
                "language": Language.NODE,
                "connections": ["test_app"]
            }

            mock_yaml_loader.return_value = mock_tool_content
            tc = ToolkitController()
            result = tc.import_toolkit("test_file.yaml")

            assert len(result) == 1
            assert isinstance(result[0], BaseToolkit)
            spec = result[0].__toolkit_spec__
            assert spec.name == self.mock_name
            assert spec.description == self.mock_description
            assert isinstance(spec.mcp, LocalMcpModel)
            assert spec.mcp.connections == ["test_app"]
            mock_safe_open.assert_called_once_with(Path("test_file.yaml"), "r")
            mock_yaml_loader.assert_called_once()

    def test_import_toolkit_json(self):
        with patch.object(Path, "exists", return_value=True), \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.safe_open", mock_open()) as mock_safe_open, \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.json.load") as mock_json_loader:

            mock_tool_content = {
                "spec_version": SpecVersion.V1,
                "name": self.mock_name,
                "description": self.mock_description,
                "package": "test_pacakge",
                "language": Language.NODE,
                "connections": ["test_app"]
            }

            mock_json_loader.return_value = mock_tool_content
            tc = ToolkitController()
            result = tc.import_toolkit("test_file.json")

            assert len(result) == 1
            assert isinstance(result[0], BaseToolkit)
            spec = result[0].__toolkit_spec__
            assert spec.name == self.mock_name
            assert spec.description == self.mock_description
            assert isinstance(spec.mcp, LocalMcpModel)
            assert spec.mcp.connections == ["test_app"]
            mock_safe_open.assert_called_once_with(Path("test_file.json"), "r")
            mock_json_loader.assert_called_once()

    def test_import_toolkit_python(self):
        with patch.object(Path, "exists", return_value=True), \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.inspect.getmembers") as mock_get_members, \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.importlib.import_module") as mock_import_module:
            
            mock_toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=LocalMcpModel(
                        package="test_package",
                        source=ToolkitSource.PUBLIC_REGISTRY,
                        command="npx",
                        connections=["test_app"]
                    )
                )
            )
            mock_toolkits = [("toolkit", mock_toolkit)]

            mock_get_members.return_value = mock_toolkits
            tc = ToolkitController()
            result = tc.import_toolkit("test_file.py")

            assert len(result) == 1
            assert isinstance(result[0], BaseToolkit)
            spec = result[0].__toolkit_spec__
            assert spec.name == self.mock_name
            assert spec.description == self.mock_description
            assert isinstance(spec.mcp, LocalMcpModel)
            assert spec.mcp.connections == ["test_app"]
            mock_get_members.assert_called_once()
            mock_import_module.assert_called_once()

    def test_import_toolkit_invalid_file_type(self):
        with patch.object(Path, "exists", return_value=True), \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.safe_open", mock_open()) as mock_safe_open:
            
            with pytest.raises(BadRequest) as e:
                tc = ToolkitController()
                tc.import_toolkit("test_file.txt")
            
            assert "file must end in .json, .yaml, or .yml" in str(e)
            mock_safe_open.assert_called_once()

    def test_import_toolkit_not_found(self):
        with patch.object(Path, "exists", return_value=False):
            
            with pytest.raises(FileNotFoundError) as e:
                tc = ToolkitController()
                tc.import_toolkit("test_file.yaml")
            
            assert "does not exist" in str(e)

    def test_import_toolkit_yaml_with_app_id(self):
        with patch.object(Path, "exists", return_value=True), \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.safe_open", mock_open()) as mock_safe_open, \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.yaml_safe_load") as mock_yaml_loader:

            mock_tool_content = {
                "spec_version": SpecVersion.V1,
                "name": self.mock_name,
                "description": self.mock_description,
                "package": "test_pacakge",
                "language": Language.NODE,
                "connections": ["test_app1"]
            }

            mock_yaml_loader.return_value = mock_tool_content
            tc = ToolkitController()
            result = tc.import_toolkit("test_file.yaml", ["test_app"])

            assert len(result) == 1
            assert isinstance(result[0], BaseToolkit)
            spec = result[0].__toolkit_spec__
            assert spec.name == self.mock_name
            assert spec.description == self.mock_description
            assert isinstance(spec.mcp, LocalMcpModel)
            assert spec.mcp.connections == ["test_app"]
            mock_safe_open.assert_called_once_with(Path("test_file.yaml"), "r")
            mock_yaml_loader.assert_called_once()

    def test_import_toolkit_python_with_app_id(self):
        with patch.object(Path, "exists", return_value=True), \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.inspect.getmembers") as mock_get_members, \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.importlib.import_module") as mock_import_module:
            
            mock_toolkit = BaseToolkit(
                spec=ToolkitSpec(
                    name=self.mock_name,
                    description=self.mock_description,
                    mcp=LocalMcpModel(
                        package="test_package",
                        source=ToolkitSource.PUBLIC_REGISTRY,
                        command="npx",
                        connections=["test_app1"]
                    )
                )
            )
            mock_toolkits = [("toolkit", mock_toolkit)]

            mock_get_members.return_value = mock_toolkits
            tc = ToolkitController()
            result = tc.import_toolkit("test_file.py", "test_app")

            assert len(result) == 1
            assert isinstance(result[0], BaseToolkit)
            spec = result[0].__toolkit_spec__
            assert spec.name == self.mock_name
            assert spec.description == self.mock_description
            assert isinstance(spec.mcp, LocalMcpModel)
            assert spec.mcp.connections == ["test_app"]
            mock_get_members.assert_called_once()
            mock_import_module.assert_called_once()

    def test_import_toolkit_missing_spec_version(self):
        with patch.object(Path, "exists", return_value=True), \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.safe_open", mock_open()) as mock_safe_open, \
            patch("ibm_watsonx_orchestrate.agent_builder.toolkits.base_toolkit.yaml_safe_load") as mock_yaml_loader:

            mock_tool_content = {
                "name": self.mock_name,
                "description": self.mock_description,
                "package": "test_pacakge",
                "language": Language.NODE,
                "connections": ["test_app1"]
            }

            mock_yaml_loader.return_value = mock_tool_content

            with pytest.raises(BadRequest) as e:
                tc = ToolkitController()
                tc.import_toolkit("test_file.yaml", ["test_app"])

            assert "Field 'spec_version' not provided" in str(e)
