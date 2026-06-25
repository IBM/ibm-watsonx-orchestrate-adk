import json
import pytest
from unittest.mock import patch
from datetime import datetime

import typer

from ibm_watsonx_orchestrate.cli.commands.observability.traces import traces_command
from ibm_watsonx_orchestrate.cli.commands.observability.traces import traces_helper
from ibm_watsonx_orchestrate.cli.commands.observability.traces.types import SortField, SortDirection
from ibm_watsonx_orchestrate.client.observability.traces.traces_client import (
    TraceSummary,
    TraceSearchResponse,
    ObservationsExportResponse,
    Observation,
)

# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

TRACE_ID = "2d195388b09db2db586475cc763e4fb0"
AGENT_ID = "28b3d783-8e38-4ad6-8073-acf4529e7128"
AGENT_NAME = "pet_agent"
USER_ID = "f242eadf-0dc9-4eae-b2d7-65b09b4b4b16"
SESSION_ID = "4758dfd3-c2f5-499e-9323-7497975435c5"

_COMMON_METADATA = {
    "attributes": {
        "workspace.id": "00000000-0000-0000-0000-000000000001",
        "agent.id": AGENT_ID,
        "agent.name": AGENT_NAME,
        "thread.id": SESSION_ID,
        "conversation.id": "df79d926-e274-4f2a-bc2a-0450dd7efef4",
    },
    "resourceAttributes": {
        "telemetry.sdk.language": "python",
        "telemetry.sdk.name": "opentelemetry",
        "telemetry.sdk.version": "1.33.1",
        "service.name": "wxo-server",
    },
    "scope": {"name": "wxo-langgraph", "attributes": {}},
}

MOCK_OBSERVATIONS = [
    Observation(
        id="b64fb1082220674a",
        traceId=TRACE_ID,
        type="CHAIN",
        name="answer",
        startTime="2026-06-20T21:15:40.037Z",
        endTime="2026-06-20T21:15:40.045Z",
        model=None,
        input={"current_agent": AGENT_NAME, "agent_display_name": AGENT_NAME},
        output="Here's a fun fact about Milo and Otis.",
        metadata=_COMMON_METADATA,
        usage={"unit": "TOKENS", "input": 0, "output": 0, "total": 0},
    ),
    Observation(
        id="d9d81dff12cf2e74",
        traceId=TRACE_ID,
        type="SPAN",
        name="answer.task",
        startTime="2026-06-20T21:15:39.982Z",
        endTime="2026-06-20T21:15:40.044Z",
        model=None,
        input={"kwargs": {"name": "answer"}},
        output={"outputs": {"messages": [{"role": "assistant", "content": "Fun fact."}]}},
        metadata=_COMMON_METADATA,
        usage={"unit": "TOKENS", "input": 0, "output": 0, "total": 0},
    ),
    Observation(
        id="ff6308a55335b9ab",
        traceId=TRACE_ID,
        type="GENERATION",
        name="WatsonxChatModel.chat",
        startTime="2026-06-20T21:15:39.617Z",
        endTime="2026-06-20T21:15:39.968Z",
        model="openai/gpt-oss-120b",
        input=[
            {"role": "user", "content": "Tell me a fact about the cat and dog from milo and otis"},
            {"role": "tool", "content": '{"facts": ["Siamese cats have heat-sensitive coats."]}'},
        ],
        output=[{"role": "assistant", "content": "Here's a fun fact about Milo and Otis."}],
        metadata={
            **_COMMON_METADATA,
            "attributes": {
                **_COMMON_METADATA["attributes"],
                "gen_ai.request.model": "openai/gpt-oss-120b",
                "gen_ai.response.model": "openai/gpt-oss-120b",
                "gen_ai.usage.prompt_tokens": "367",
                "gen_ai.usage.completion_tokens": "96",
            },
        },
        usage={"unit": "TOKENS", "input": 367, "output": 96, "total": 463},
    ),
]

MOCK_OBS_RESPONSE = ObservationsExportResponse(
    observations=MOCK_OBSERVATIONS,
    totalCount=3,
)

MOCK_JSON_STR = json.dumps({
    "observations": [o.model_dump() for o in MOCK_OBSERVATIONS],
    "total_count": 3,
    "exported_at": "2026-06-25T12:01:04.581359Z",
    "format": "observations",
    "trace_id": TRACE_ID,
})


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------

class TestTracesSearch:
    """Test cases for traces search command"""

    def test_search_traces_with_all_filters(self):
        mock_response = TraceSearchResponse(
            generatedAt="2026-06-20T21:15:40.000Z",
            originalQuery={},
            traceSummaries=[
                TraceSummary(
                    traceId=TRACE_ID,
                    startTime="2026-06-20T21:15:39.617Z",
                    endTime="2026-06-20T21:15:40.045Z",
                    durationMs=428.0,
                    agentNames=[AGENT_NAME],
                    agentIds=[AGENT_ID],
                    userIds=[USER_ID],
                    sessionIds=[SESSION_ID],
                )
            ],
            totalCount=1,
        )
        mock_mapping = {AGENT_NAME: AGENT_ID, "another_agent": "agent-456"}

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.get_container_env_var"
        ) as mock_get_env:
            mock_search.return_value = mock_response
            mock_get_mapping.return_value = mock_mapping
            mock_get_env.return_value = "test-api-key"

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2026-06-20T21:00:00.000"),
                end_time=datetime.fromisoformat("2026-06-20T22:00:00.000"),
                service_names=["wxo-server"],
                agent_names=[AGENT_NAME],
                agent_ids=None,
                user_ids=[USER_ID],
                session_ids=None,
                min_spans=1,
                max_spans=10,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                limit=100,
            )

            mock_search.assert_called_once()
            mock_get_mapping.assert_called_once()
            filters = mock_search.call_args.kwargs["filters"]
            assert filters.agent_ids is not None
            assert AGENT_ID in filters.agent_ids

    def test_search_traces_minimal_params(self):
        mock_response = TraceSearchResponse(
            generatedAt="2026-06-20T21:15:40.000Z",
            originalQuery={},
            traceSummaries=[],
            totalCount=0,
        )

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.get_container_env_var"
        ) as mock_get_env:
            mock_search.return_value = mock_response
            mock_get_env.return_value = "test-api-key"

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2026-06-20T21:00:00.000"),
                end_time=datetime.fromisoformat("2026-06-20T22:00:00.000"),
                service_names=None,
                agent_names=None,
                agent_ids=None,
                user_ids=None,
                session_ids=None,
                min_spans=None,
                max_spans=None,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                limit=100,
            )

            mock_search.assert_called_once()
            filters = mock_search.call_args.kwargs["filters"]
            assert filters.agent_ids is None

    def test_search_traces_agent_name_resolution(self):
        mock_response = TraceSearchResponse(
            generatedAt="2026-06-20T21:15:40.000Z",
            originalQuery={},
            traceSummaries=[],
            totalCount=0,
        )
        mock_mapping = {AGENT_NAME: AGENT_ID, "another_agent": "agent-456"}

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.get_container_env_var"
        ) as mock_get_env:
            mock_search.return_value = mock_response
            mock_get_mapping.return_value = mock_mapping
            mock_get_env.return_value = "test-api-key"

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2026-06-20T21:00:00.000"),
                end_time=datetime.fromisoformat("2026-06-20T22:00:00.000"),
                service_names=None,
                agent_names=[AGENT_NAME],
                agent_ids=None,
                user_ids=None,
                session_ids=None,
                min_spans=None,
                max_spans=None,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                limit=100,
            )

            mock_search.assert_called_once()
            mock_get_mapping.assert_called_once()
            filters = mock_search.call_args.kwargs["filters"]
            assert filters.agent_ids is not None
            assert AGENT_ID in filters.agent_ids

    def test_search_traces_with_limit(self):
        mock_response = TraceSearchResponse(
            generatedAt="2026-06-20T21:15:40.000Z",
            originalQuery={},
            traceSummaries=[
                TraceSummary(
                    traceId=f"2d195388b09db2db586475cc763e4f{i:02x}",
                    startTime="2026-06-20T21:15:39.617Z",
                    endTime="2026-06-20T21:15:40.045Z",
                    durationMs=428.0,
                    agentNames=[AGENT_NAME],
                    agentIds=[AGENT_ID],
                    userIds=[USER_ID],
                )
                for i in range(20)
            ],
            totalCount=20,
        )

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.search_traces"
        ) as mock_search, patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.get_container_env_var"
        ) as mock_get_env:
            mock_search.return_value = mock_response
            mock_get_env.return_value = "test-api-key"

            traces_command.search_traces(
                start_time=datetime.fromisoformat("2026-06-20T21:00:00.000"),
                end_time=datetime.fromisoformat("2026-06-20T22:00:00.000"),
                service_names=None,
                agent_names=None,
                agent_ids=None,
                user_ids=None,
                session_ids=None,
                min_spans=None,
                max_spans=None,
                sort_field=SortField.START_TIME,
                sort_direction=SortDirection.DESC,
                limit=10,
            )

            mock_search.assert_called_once()


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

class TestTracesExport:
    """Test cases for traces export command"""

    def test_export_trace_stdout(self):
        """Export to stdout: controller is called with the right args."""
        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.export_trace_to_json"
        ) as mock_export:
            mock_export.return_value = (MOCK_OBS_RESPONSE, MOCK_JSON_STR)

            traces_command.export_trace(trace_id=TRACE_ID, output=None, pretty=True)

            mock_export.assert_called_once_with(
                trace_id=TRACE_ID,
                output_file=None,
                pretty=True,
            )

    def test_export_trace_to_file(self, tmp_path):
        """Export to a .json file: controller is called with the output path."""
        output_file = tmp_path / "trace.json"

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.export_trace_to_json"
        ) as mock_export:
            mock_export.return_value = (MOCK_OBS_RESPONSE, MOCK_JSON_STR)

            traces_command.export_trace(
                trace_id=TRACE_ID,
                output=str(output_file),
                pretty=True,
            )

            mock_export.assert_called_once()

    def test_export_trace_all_observation_types_present(self):
        """Mock data covers all three observation types returned by the API."""
        types = {o.type for o in MOCK_OBS_RESPONSE.observations}
        assert types == {"CHAIN", "SPAN", "GENERATION"}

    def test_export_trace_generation_has_token_usage(self):
        """GENERATION observation carries model name and token usage."""
        gen = next(o for o in MOCK_OBS_RESPONSE.observations if o.type == "GENERATION")
        assert gen.model == "openai/gpt-oss-120b"
        assert gen.usage["input"] == 367
        assert gen.usage["output"] == 96
        assert gen.usage["total"] == 463

    def test_export_trace_metadata_carries_agent_info(self):
        """Every observation's metadata attributes include agent name and ID."""
        for obs in MOCK_OBS_RESPONSE.observations:
            attrs = obs.metadata["attributes"]
            assert attrs["agent.name"] == AGENT_NAME
            assert attrs["agent.id"] == AGENT_ID

    def test_export_trace_invalid_trace_id(self):
        """A trace ID shorter than 32 characters must exit with an error."""
        with pytest.raises(typer.Exit):
            traces_command.export_trace(trace_id="invalid", output=None, pretty=True)

    def test_export_trace_non_json_output_extension(self, tmp_path):
        """A non-.json output path is rejected and the call falls back to stdout."""
        bad_output = str(tmp_path / "trace.csv")

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_controller.TracesController.export_trace_to_json"
        ) as mock_export:
            mock_export.return_value = (MOCK_OBS_RESPONSE, MOCK_JSON_STR)

            traces_command.export_trace(
                trace_id=TRACE_ID,
                output=bad_output,
                pretty=True,
            )

            _, kwargs = mock_export.call_args
            assert kwargs["output_file"] is None


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestTracesCommandHelpers:
    """Test helper functions that map agent names to IDs in the traces command"""

    def test_resolve_agent_names_to_ids_with_names_only(self):
        mock_mapping = {AGENT_NAME: AGENT_ID, "another_agent": "agent-456"}

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_get_mapping.return_value = mock_mapping

            result = traces_helper.resolve_agent_names_to_ids(
                agent_names=[AGENT_NAME], agent_ids=None
            )
            mock_get_mapping.assert_called_once()
            assert result == [AGENT_ID]

    def test_resolve_agent_names_to_ids_with_ids_only(self):
        """IDs passed directly are returned as-is without an API call."""
        result = traces_helper.resolve_agent_names_to_ids(
            agent_names=None, agent_ids=[AGENT_ID]
        )
        assert result == [AGENT_ID]

    def test_resolve_agent_names_to_ids_merge_id_with_new_name(self):
        """Names are resolved and merged with existing IDs, with no duplicates."""
        mock_mapping = {AGENT_NAME: AGENT_ID, "another_agent": "agent-456"}

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_get_mapping.return_value = mock_mapping

            result = traces_helper.resolve_agent_names_to_ids(
                agent_names=[AGENT_NAME],
                agent_ids=[AGENT_ID, "agent-789"],
            )
            mock_get_mapping.assert_called_once()
            assert result is not None
            assert result.count(AGENT_ID) == 1  # no duplicate
            assert "agent-789" in result

    def test_resolve_agent_names_to_ids_with_unknown_name(self):
        """An unrecognised agent name produces no ID and returns None."""
        mock_mapping = {AGENT_NAME: AGENT_ID}

        with patch(
            "ibm_watsonx_orchestrate.cli.commands.observability.traces.traces_helper.get_agent_name_to_id_mapping"
        ) as mock_get_mapping:
            mock_get_mapping.return_value = mock_mapping

            result = traces_helper.resolve_agent_names_to_ids(
                agent_names=["nonexistent_agent"], agent_ids=None
            )
            mock_get_mapping.assert_called_once()
            assert result is None

    def test_resolve_agent_names_to_ids_with_none(self):
        """No names and no IDs returns None."""
        result = traces_helper.resolve_agent_names_to_ids(
            agent_names=None, agent_ids=None
        )
        assert result is None
