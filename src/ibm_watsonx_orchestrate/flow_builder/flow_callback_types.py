"""
Pydantic models for watsonx Orchestrate Agentic Workflow (Flow) callback events.

These models match the FlowCallbackEventPayload TypeScript interface and OpenAPI specification.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
    
class FlowCallbackEventKind(str, Enum):
    """Kind of flow callback event."""
    
    # Flow events
    ON_FLOW_START = "flow:on_flow_start"
    ON_FLOW_END = "flow:on_flow_end"
    ON_FLOW_ERROR = "flow:on_flow_error"
    ON_FLOW_ABORT = "flow:on_flow_abort"
    ON_FLOW_DELETE = "flow:on_flow_delete"
    
    # Task events
    ON_TASK_WAIT = "task:on_task_wait"  # the task is waiting for inputs before proceeding
    ON_TASK_ERROR = "task:on_task_error"
    ON_TASK_MESSAGE = "task:on_task_message"

class FlowState(str, Enum):
    """Current execution state of the flow."""

    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    DELETED = "deleted"


class ErrorDetails(BaseModel):
    """Error details for error events."""

    message: str = Field(..., description="Error message describing what went wrong")
    code: Optional[str] = Field(None, description="Optional error code for categorization")


class EventMetadata(BaseModel):
    """Event metadata including kind, timestamp, flow information, and optional task/error information."""

    id: str = Field(..., description="Unique identifier for this event instance (UUID)")
    kind: FlowCallbackEventKind = Field(..., description="Kind of flow event")
    created_at: str = Field(..., description="ISO 8601 timestamp when the event occurred")
    instance_id: str = Field(..., description="Unique identifier for this flow instance")
    flow_name: str = Field(..., description="Name of the flow")
    environment_id: str = Field(..., description="Environment ID where the flow is running")
    state: FlowState = Field(..., description="Current execution state of the flow")
    parent_instance_id: Optional[str] = Field(None, description="Parent flow instance ID (present when this is a child flow)")
    parent_flow_name: Optional[str] = Field(None, description="Parent flow name (present when this is a child flow)")
    task_id: Optional[str] = Field(None, description="Task ID (present for task-related events)")
    task_name: Optional[str] = Field(None, description="Internal task name (present for task-related events)")
    task_display_name: Optional[str] = Field(
        None, description="Human-readable task display name (present for task-related events)"
    )
    error: Optional[ErrorDetails] = Field(None, description="Error details (present for error events)")
    
    class Config:
        populate_by_name = True


class ActivityInfo(BaseModel):
    """Activity information for response items."""

    initiated_by: Optional[str] = None
    action_status: Optional[str] = None
    activity_title: Optional[str] = None


class BaseResponseItem(BaseModel):
    """Base response item for user input requests."""

    name: str = Field(..., description="Name identifier for the response item")
    activity_info: Optional[ActivityInfo] = None


class TextResponseItem(BaseResponseItem):
    """Text response item."""

    response_type: Literal["text"] = Field(default="text", description="Type of response item")
    text: str
    is_list: bool


class FileUploadResponseItem(BaseResponseItem):
    """File upload response item."""

    response_type: Literal["file_upload"] = Field(default="file_upload", description="Type of response item")
    text: str
    source: str


class FileDownloadEntry(BaseModel):
    """File download entry."""

    url: str
    text: str
    fileName: str = Field(..., alias="fileName")

    class Config:
        populate_by_name = True


class FileDownloadResponseItem(BaseResponseItem):
    """File download response item."""

    response_type: Literal["file_download"] = Field(default="file_download", description="Type of response item")
    files: List[FileDownloadEntry]


class ObjectResponseItem(BaseResponseItem):
    """Object response item containing nested response items."""

    response_type: Literal["object"] = Field(default="object", description="Type of response item")
    content: List["ResponseItem"]


class DateResponseItem(BaseResponseItem):
    """Date/datetime/time response item."""

    response_type: Literal["date", "datetime", "time"] = Field(..., description="Type of response item")
    text: str
    min: Optional[str] = None
    max: Optional[str] = None
    default: Optional[str] = None


class NumberResponseItem(BaseResponseItem):
    """Number response item."""

    response_type: Literal["number"] = Field(default="number", description="Type of response item")
    text: str
    min: Optional[str] = None
    max: Optional[str] = None
    default: Optional[str] = None


class OptionEntry(BaseModel):
    """Option entry for option response items."""

    label: str
    value: str


class OptionResponseItem(BaseResponseItem):
    """Option (select/choice) response item."""

    response_type: Literal["option"] = Field(default="option", description="Type of response item")
    text: str
    id: str
    options: List[OptionEntry]
    default: Optional[str] = None


class FormResponseItem(BaseResponseItem):
    """Form response item with JSON Schema and UI Schema."""

    response_type: Literal["forms"] = Field(default="forms", description="Type of response item")
    json_schema: Dict[str, Any]
    ui_schema: Dict[str, Any]
    form_data: Optional[Dict[str, Any]] = None
    extracted_full_choice_map: Optional[Dict[str, Dict[int, Dict[str, Any]]]] = None
    behaviours: Optional[List[Any]] = None


# Union type for all response items
ResponseItem = Union[
    TextResponseItem,
    FileUploadResponseItem,
    FileDownloadResponseItem,
    ObjectResponseItem,
    DateResponseItem,
    NumberResponseItem,
    OptionResponseItem,
    FormResponseItem,
]

# Update forward references
ObjectResponseItem.model_rebuild()


class ElicitationMetadata(BaseModel):
    """Additional metadata about the elicitation request."""

    assignee: str = Field(..., description="User ID or email of the assigned user")
    response_items: List[ResponseItem] = Field(
        ..., description="Full original ResponseItem schema array for complex input requests"
    )


class ElicitationDetails(BaseModel):
    """Elicitation details for user input (only present when state is 'input_required')."""

    mode: Literal["form"] = Field(..., description="Elicitation mode - currently only 'form' is supported")
    message: str = Field(..., description="User-facing message describing what input is needed")
    elicitationId: str = Field(
        ..., description="Unique identifier for this elicitation request (same as task_id)", alias="elicitationId"
    )
    requestedSchema: Dict[str, Any] = Field(
        ...,
        description="JSON Schema defining the structure and validation rules for requested input",
        alias="requestedSchema",
    )
    meta: ElicitationMetadata = Field(..., description="Additional metadata about the elicitation request")
    
    class Config:
        populate_by_name = True


class FlowCallbackEventPayload(BaseModel):
    """
    Complete payload for watsonx Orchestrate Agentic Workflow (Flow) callback events.

    This is a fire-and-forget callback - the handler should not return any data.
    """

    event: EventMetadata = Field(..., description="Event metadata including type, timestamp, flow information, and optional task/error information")
    output: Optional[Dict[str, Any]] = Field(None, description="Flow output data (only present when state is 'completed')")
    elicitation: Optional[ElicitationDetails] = Field(
        None, description="Elicitation details for user input (only present when state is 'input_required')"
    )


class FlowCallbackEventsPayload(BaseModel):
    """
    Payload containing an array of flow callback events.
    
    This allows batch processing of multiple events in a single request.
    """

    events: List[FlowCallbackEventPayload] = Field(..., description="Array of flow callback event payloads")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "event": {
                        "id": "flow-inst-12345_2026-04-01T16:30:00.000Z",
                        "type": "flow:on_flow_start",
                        "created_at": "2026-04-01T16:30:00.000Z",
                        "instance_id": "flow-inst-12345",
                        "flow_name": "Purchase Approval Flow",
                        "environment_id": "draft",
                        "state": "working",
                    },
                },
                {
                    "event": {
                        "id": "flow-inst-12345_2026-04-01T16:30:15.000Z",
                        "type": "task:on_task_wait",
                        "created_at": "2026-04-01T16:30:15.000Z",
                        "instance_id": "flow-inst-12345",
                        "flow_name": "Purchase Approval Flow",
                        "environment_id": "draft",
                        "state": "input_required",
                        "task_id": "task-67890",
                        "task_name": "approval_form",
                        "task_display_name": "Approval Form",
                    },
                    "elicitation": {
                        "mode": "form",
                        "message": "Please review and approve the purchase request",
                        "elicitationId": "task-67890",
                        "requestedSchema": {
                            "type": "object",
                            "properties": {
                                "approved": {"type": "boolean"},
                                "comments": {"type": "string"},
                            },
                        },
                        "meta": {
                            "assignee": "user@example.com",
                            "response_items": [
                                {
                                    "response_type": "option",
                                    "name": "approved",
                                    "text": "Approve this request?",
                                    "id": "approved",
                                    "options": [
                                        {"label": "Yes", "value": "true"},
                                        {"label": "No", "value": "false"},
                                    ],
                                }
                            ],
                        },
                    },
                },
                {
                    "event": {
                        "id": "flow-inst-12345_2026-04-01T16:35:00.000Z",
                        "type": "flow:on_flow_end",
                        "created_at": "2026-04-01T16:35:00.000Z",
                        "instance_id": "flow-inst-12345",
                        "flow_name": "Purchase Approval Flow",
                        "environment_id": "live",
                        "state": "completed",
                    },
                    "output": {
                        "result": "approved",
                        "approval_date": "2026-04-01",
                        "approver": "user@example.com",
                    },
                },
            ]
        }

