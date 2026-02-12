import json
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
import pytest
import typer

from ibm_watsonx_orchestrate.cli.commands.observability.traces import traces_command
from ibm_watsonx_orchestrate.cli.commands.observability.traces import traces_helper
from ibm_watsonx_orchestrate.cli.commands.observability.traces.types import SortField, SortDirection
from ibm_watsonx_orchestrate.client.observability.traces.traces_client import (
    TraceSummary,
    TraceSearchResponse,
    SpansResponse,
)


class TestTracesSearch:
    """Test cases for traces search command"""

    def test_search_traces_with_all_filters(self):
        mock_response = TraceSearchResponse(
            generatedAt="2024-01-01T00:00:00.000Z",
            originalQuery={},
            traceSummaries=[
                TraceSummary(
                    traceId="trace-123",
                    startTime="2024-01-01T00:00:00.000",
                    endTime="2024-01-01T00:01:00.000",
                    durationMs=60000,
                    spanCount=5,
                    serviceNames=["wxo-server"],
                    agentNames=["TestAgent"],
                    agentIds=["agent-123"],
                    userIds=["user-123"],
                )
            ],
            totalCount=1,
        )
        mock_mapping = {
            "TestAgent": "agent-123",
            "AnotherAgent": "agent-456"
        }

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_search.return_value = mock_response
            mock_get_mapping.return_value = mock_mapping

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2024-01-01T00:00:00.000"),
                end_time=datetime.fromisoformat("2024-01-01T23:59:59.999"),
                service_names=["wxo-server"],
                agent_names=["TestAgent"],
                agent_ids=None,
                user_ids=["user-123"],
                session_ids=None,
                min_spans=1,
                max_spans=10,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                include_root_spans=False,
                limit=100,
            )

            mock_search.assert_called_once()
            mock_get_mapping.assert_called_once()
            call_args = mock_search.call_args
            filters = call_args.kwargs["filters"]
            assert filters.agent_ids is not None
            assert "agent-123" in filters.agent_ids

    def test_search_traces_minimal_params(self):
        mock_response = TraceSearchResponse(
            generatedAt="2024-01-01T00:00:00.000Z",
            originalQuery={},
            traceSummaries=[],
            totalCount=0,
        )

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search:
            mock_search.return_value = mock_response

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2024-01-01T00:00:00.000"),
                end_time=datetime.fromisoformat("2024-01-01T23:59:59.999"),
                service_names=None,
                agent_names=None,
                agent_ids=None,
                user_ids=None,
                session_ids=None,
                min_spans=None,
                max_spans=None,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                include_root_spans=False,
                limit=None,
            )

            mock_search.assert_called_once()
            call_args = mock_search.call_args
            filters = call_args.kwargs["filters"]
            assert filters.agent_ids is None


    def test_search_traces_agent_name_resolution(self):
        mock_response = TraceSearchResponse(
            generatedAt="2024-01-01T00:00:00.000Z",
            originalQuery={},
            traceSummaries=[],
            totalCount=0,
        )
        mock_mapping = {
            "TestAgent": "agent-123",
            "AnotherAgent": "agent-456"
        }

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_search.return_value = mock_response
            mock_get_mapping.return_value = mock_mapping

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2024-01-01T00:00:00.000"),
                end_time=datetime.fromisoformat("2024-01-01T23:59:59.999"),
                service_names=None,
                agent_names=["TestAgent"],
                agent_ids=None,
                user_ids=None,
                session_ids=None,
                min_spans=None,
                max_spans=None,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                include_root_spans=False,
                limit=None,
            )

            mock_search.assert_called_once()
            mock_get_mapping.assert_called_once()
            call_args = mock_search.call_args
            filters = call_args.kwargs["filters"]
            assert filters.agent_ids is not None
            assert "agent-123" in filters.agent_ids

    def test_search_traces_with_limit(self):
        mock_response = TraceSearchResponse(
            generatedAt="2024-01-01T00:00:00.000Z",
            originalQuery={},
            traceSummaries=[
                TraceSummary(
                    traceId=f"trace-{i}",
                    startTime="2024-01-01T00:00:00.000",
                    endTime="2024-01-01T00:01:00.000",
                    durationMs=60000,
                    spanCount=5,
                    serviceNames=["wxo-server"],
                    agentNames=["TestAgent"],
                    agentIds=["agent-123"],
                    userIds=["user-123"],
                )
                for i in range(20)
            ],
            totalCount=20,
        )

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search:
            mock_search.return_value = mock_response

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2024-01-01T00:00:00.000"),
                end_time=datetime.fromisoformat("2024-01-01T23:59:59.999"),
                service_names=None,
                agent_names=None,
                agent_ids=None,
                user_ids=None,
                session_ids=None,
                min_spans=None,
                max_spans=None,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                include_root_spans=False,
                limit=10,
            )

            mock_search.assert_called_once()


class TestTracesExport:
    """Test cases for traces export command"""

    def test_export_trace_success(self):
        mock_spans_response = SpansResponse(
            traceData={
                "resourceSpans": [
                    {
                        "resource": {"attributes": []},
                        "scopeSpans": [
                            {
                                "scope": {"name": "test", "version": "1.0"},
                                "spans": [
                                    {
                                        "traceId": "trace-123",
                                        "spanId": "span-123",
                                        "name": "test-span",
                                        "kind": "SPAN_KIND_INTERNAL",
                                        "startTimeUnixNano": "1234567890000000000",
                                        "endTimeUnixNano": "1234567891000000000",
                                        "attributes": [
                                            {
                                                "key": "agent.name",
                                                "value": {"stringValue": "TestAgent"},
                                            }
                                        ],
                                        "events": [],
                                        "status": {"code": "STATUS_CODE_OK"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            totalCount=1,
        )
        mock_json_str = json.dumps({"traceData": "test"})

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.export_trace_to_json"
        ) as mock_export:
            mock_export.return_value = (mock_spans_response, mock_json_str)

            traces_command.export_trace(
                trace_id="1234567890abcdef1234567890abcdef", output=None, pretty=True
            )

            mock_export.assert_called_once_with(
                trace_id="1234567890abcdef1234567890abcdef",
                output_file=None,
                pretty=True,
            )

    def test_export_trace_with_output_file(self, tmp_path):
        """Test trace export with output file"""
        output_file = tmp_path / "trace.json"
        mock_spans_response = SpansResponse(
            traceData={
                "resourceSpans": [
                    {
                        "resource": {"attributes": []},
                        "scopeSpans": [
                            {
                                "scope": {"name": "test", "version": "1.0"},
                                "spans": [
                                    {
                                        "traceId": "trace-123",
                                        "spanId": "span-123",
                                        "name": "test-span",
                                        "kind": "SPAN_KIND_INTERNAL",
                                        "startTimeUnixNano": "1234567890000000000",
                                        "endTimeUnixNano": "1234567891000000000",
                                        "attributes": [],
                                        "events": [],
                                        "status": {"code": "STATUS_CODE_OK"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            totalCount=1,
        )
        mock_json_str = json.dumps({"traceData": "test"})

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.export_trace_to_json"
        ) as mock_export:
            mock_export.return_value = (mock_spans_response, mock_json_str)

            traces_command.export_trace(
                trace_id="1234567890abcdef1234567890abcdef",
                output=str(output_file),
                pretty=True,
            )

            mock_export.assert_called_once()

    def test_export_trace_invalid_trace_id(self):
        """Test export with invalid trace ID format"""
        with pytest.raises(typer.Exit):
            traces_command.export_trace(
                trace_id="invalid", output=None, pretty=True
            )


class TestTracesCommandHelpers:
    """Test helper functions that map agent names to ids in traces command"""

    def test_resolve_agent_names_to_ids_with_names_only(self):
        mock_mapping = {
            "TestAgent": "agent-123",
            "AnotherAgent": "agent-456"
        }

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_get_mapping.return_value = mock_mapping

            result = traces_helper.resolve_agent_names_to_ids(
                agent_names=["TestAgent"], agent_ids=None
            )
            mock_get_mapping.assert_called_once()
            assert result == ["agent-123"]

    def test_resolve_agent_names_to_ids_with_ids_only(self):
        """Test resolving with only IDs provided (no resolution needed)"""
        result = traces_helper.resolve_agent_names_to_ids(
            agent_names=None, agent_ids=["agent-789"]
        )
        assert result == ["agent-789"]

    def test_resolve_agent_names_to_ids_merge_id_with_new_name(self):
        mock_mapping = {
            "TestAgent": "agent-123",
            "AnotherAgent": "agent-456"
        }

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_get_mapping.return_value = mock_mapping

            result = traces_helper.resolve_agent_names_to_ids(
                agent_names=["TestAgent"], agent_ids=["agent-123", "agent-789"]
            )
            # Should contain both resolved ID and provided IDs, deduplicated
            mock_get_mapping.assert_called_once()
            assert result is not None
            assert result == ["agent-123", "agent-789"]

    def test_resolve_agent_names_to_ids_with_unknown_name(self):
        """Test resolving with unknown agent name"""
        mock_mapping = {
            "TestAgent": "agent-123"
        }

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_get_mapping.return_value = mock_mapping

            result = traces_helper.resolve_agent_names_to_ids(
                agent_names=["UnknownAgent"], agent_ids=None
            )
            mock_get_mapping.assert_called_once()
            assert result is None

    def test_resolve_agent_names_to_ids_with_none(self):
        """Test resolving with no names or IDs"""
        result = traces_helper.resolve_agent_names_to_ids(
            agent_names=None, agent_ids=None
        )
        assert result is None
