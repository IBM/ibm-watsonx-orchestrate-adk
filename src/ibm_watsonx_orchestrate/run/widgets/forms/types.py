from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union, Literal
from datetime import date
from abc import ABC, abstractmethod
import uuid


class FormInput(BaseModel, ABC):
    """Base class for all form input types.

    Supported Phase 1 form widgets:
        - TextInput                     — single-line text box
        - TextArea                      — multi-line text area
        - RadioButton                   — radio button group (single select)
        - Checkbox                      — boolean checkbox (Yes/No)
        - ComboBox                      — single-select combo box with search
        - NumberInput                   — number input with +/- stepper
        - DatePicker                    — single date picker
        - DateRangePicker               — date range picker
        - FileUpload                    — file upload widget
        - FileDownload                  — file download widget
        - Table                         — data table (single or multi select)
    """

    name: str
    title: str
    required: bool = False
    description: Optional[str] = None

    @abstractmethod
    def to_ui_schema(self) -> Dict[str, Any]:
        """Convert to UI Schema format"""
        pass

    @abstractmethod
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format"""
        pass

    @abstractmethod
    def to_form_data(self) -> Any:
        """Convert to form data format (if has default value)"""
        pass


# ---------------------------------------------------------------------------
# i. Text box & Text area
# ---------------------------------------------------------------------------

class TextInput(FormInput):
    """Single-line text input"""
    placeholder: Optional[str] = None
    default_value: Optional[str] = None

    def to_ui_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"ui:widget": "TextWidget"}
        if self.placeholder:
            schema["ui:placeholder"] = self.placeholder
        return schema

    def to_json_schema(self) -> Dict[str, Any]:
        return {"type": "string", "title": self.title}

    def to_form_data(self) -> Optional[str]:
        return self.default_value


class TextArea(FormInput):
    """Multi-line text input"""
    placeholder: Optional[str] = None
    default_value: Optional[str] = None
    autofocus: bool = False

    def to_ui_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"ui:widget": "TextareaWidget"}
        if self.placeholder:
            schema["ui:placeholder"] = self.placeholder
        if self.autofocus:
            schema["ui:autofocus"] = True
        return schema

    def to_json_schema(self) -> Dict[str, Any]:
        return {"type": "string", "title": self.title}

    def to_form_data(self) -> Optional[str]:
        return self.default_value


# ---------------------------------------------------------------------------
# ii. Radio button
# ---------------------------------------------------------------------------

class RadioButton(FormInput):
    """Radio button group — single selection"""
    options: List[str]
    option_labels: Optional[List[str]] = None
    default_value: Optional[str] = None

    def to_ui_schema(self) -> Dict[str, Any]:
        return {"ui:widget": "RadioWidget"}

    def to_json_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {
            "type": "string",
            "title": self.title,
            "enum": self.options,
        }
        if self.option_labels:
            schema["enumNames"] = self.option_labels
        return schema

    def to_form_data(self) -> Optional[str]:
        return self.default_value


# ---------------------------------------------------------------------------
# iii. Boolean input — Checkbox
# ---------------------------------------------------------------------------

class Checkbox(FormInput):
    """Boolean checkbox (Yes/No)"""
    default_value: Optional[bool] = None

    def to_ui_schema(self) -> Dict[str, Any]:
        return {"ui:widget": "CheckboxWidget"}

    def to_json_schema(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "type": "boolean",
            "oneOf": [
                {"const": True, "title": "Yes"},
                {"const": False, "title": "No"},
            ],
        }

    def to_form_data(self) -> Optional[bool]:
        return self.default_value


# ---------------------------------------------------------------------------
# iv. Combo box — Single select with search
# ---------------------------------------------------------------------------

class ComboBox(FormInput):
    """Single-select combo box with type-ahead search"""
    options: List[str]
    option_labels: Optional[List[str]] = None
    default_value: Optional[str] = None

    def to_ui_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"ui:widget": "ComboboxWidget"}
        if self.option_labels:
            schema["ui:enumNames"] = self.option_labels
        return schema

    def to_json_schema(self) -> Dict[str, Any]:
        return {"title": self.title, "enum": self.options}

    def to_form_data(self) -> Optional[str]:
        return self.default_value


# ---------------------------------------------------------------------------
# v. Tables — View only, Single select, Multi select
# ---------------------------------------------------------------------------

class TableHeader(BaseModel):
    """Table column header definition"""
    key: str
    header: str


class Table(FormInput):
    """Data table widget.

    ``table_type`` controls the selection mode:
        - ``"dataTable"`` — view-only (no row selection)
        - ``"single"``    — single-row selection
        - ``"multi"``     — multi-row selection

    Each row in ``data`` must include a ``rowId`` key.
    """
    headers: List[TableHeader]
    table_type: Literal["dataTable", "single", "multi"] = "dataTable"
    is_sortable: bool = True
    is_searchable: bool = True
    default_row_size: int = 10
    max_items: Optional[int] = None
    min_items: Optional[int] = None
    data: Optional[List[Dict[str, Any]]] = None

    def to_ui_schema(self) -> Dict[str, Any]:
        return {"ui:widget": "Table", "ui:title": self.title}

    def to_json_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {
            "type": "array",
            "headers": [{"key": h.key, "header": h.header} for h in self.headers],
            "items": {},
            "tableType": self.table_type,
            "isSortable": self.is_sortable,
            "isSearchable": self.is_searchable,
            "defaultRowSize": self.default_row_size,
        }
        if self.max_items is not None:
            schema["maxItems"] = self.max_items
        if self.min_items is not None:
            schema["minItems"] = self.min_items
        return schema

    def to_form_data(self) -> Optional[List[Dict[str, Any]]]:
        return self.data


# ---------------------------------------------------------------------------
# vi. Number input (with +/- button)
# ---------------------------------------------------------------------------

class NumberInput(FormInput):
    """Number input with optional +/- stepper and range validation"""
    default_value: Optional[Union[int, float]] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    multiple_of: Optional[Union[int, float]] = None

    def to_ui_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"ui:widget": "NumberWidget", "ui:title": self.title}
        if self.description:
            schema["ui:description"] = self.description
        return schema

    def to_json_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"type": "integer", "title": self.title}
        if self.default_value is not None:
            schema["default"] = self.default_value
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.multiple_of is not None:
            schema["multipleOf"] = self.multiple_of
        return schema

    def to_form_data(self) -> Optional[Union[int, float]]:
        return self.default_value


# ---------------------------------------------------------------------------
# vii. Date picker — single select and date range
# ---------------------------------------------------------------------------

class DatePicker(FormInput):
    """Single date picker"""
    default_value: Optional[date] = None
    date_format: str = "YYYY-MM-DD"

    def to_ui_schema(self) -> Dict[str, Any]:
        return {"ui:widget": "DateWidget", "format": self.date_format}

    def to_json_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {
            "title": self.title,
            "type": "string",
            "format": "date",
        }
        if self.default_value:
            schema["default"] = self.default_value.isoformat()
        return schema

    def to_form_data(self) -> Optional[str]:
        return self.default_value.isoformat() if self.default_value else None


class DateRangePicker(FormInput):
    """Date range picker with separate start and end date fields"""
    start_label: str = "Start Date"
    end_label: str = "End Date"
    default_start: Optional[date] = None
    default_end: Optional[date] = None
    date_format: str = "YYYY-MM-DD"
    placeholder: Optional[str] = None

    def to_ui_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {
            "ui:widget": "DateWidget",
            "ui:options": {"range": True},
            "ui:start_label": self.start_label,
            "ui:end_label": self.end_label,
            "format": self.date_format,
        }
        if self.placeholder:
            schema["ui:placeholder"] = self.placeholder
        return schema

    def to_json_schema(self) -> Dict[str, Any]:
        return {
            "type": "array",
            "items": {"type": "string", "format": "date"},
            "title": self.title,
        }

    def to_form_data(self) -> Optional[List[str]]:
        if self.default_start and self.default_end:
            return [
                self.default_start.isoformat(),
                self.default_end.isoformat(),
            ]
        return None


# ---------------------------------------------------------------------------
# viii. File upload and File download
# ---------------------------------------------------------------------------

class FileUpload(FormInput):
    """File upload widget"""
    upload_button_label: Optional[str] = None
    file_max_size: Optional[int] = None  # in MB
    file_types: Optional[List[str]] = None  # e.g. [".csv", ".doc"]
    multi: bool = False
    max_items: Optional[int] = None
    min_items: Optional[int] = None
    default_files: Optional[List[Dict[str, str]]] = None  # [{"fileName": "abc.csv", "url": "https://..."}]

    def to_ui_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"ui:widget": "FileUpload"}
        if self.upload_button_label:
            schema["ui:upload_button_label"] = self.upload_button_label
        return schema

    def to_json_schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {
            "type": "array",
            "title": self.title,
            "items": {},
            "multi": self.multi,
        }
        if self.description:
            schema["description"] = self.description
        if self.file_max_size is not None:
            schema["file_max_size"] = self.file_max_size
        if self.file_types:
            schema["file_types"] = self.file_types
        if self.max_items is not None:
            schema["maxItems"] = self.max_items
        if self.min_items is not None:
            schema["minItems"] = self.min_items
        return schema

    def to_form_data(self) -> Optional[List[Dict[str, str]]]:
        return self.default_files


class FileDownload(FormInput):
    """File download widget — for tool response / output use only"""
    file_id: str
    file_url: str
    file_name: str

    def to_ui_schema(self) -> Dict[str, Any]:
        return {"ui:title": self.title, "ui:widget": "FileDownloadWidget"}

    def to_json_schema(self) -> Dict[str, Any]:
        return {
            "type": "string",
            "files": {
                "id": self.file_id,
                "url": self.file_url,
                "fileName": self.file_name,
            },
        }

    def to_form_data(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Top-level Form builder
# ---------------------------------------------------------------------------

class FormWidget(BaseModel):
    """Dynamic form widget that assembles the multiple FormInput fields into a
    complete wxO form response.

    The serialised output (via ``model_dump()``) contains the three sections
    expected by the wxO runtime:

    - ``response_type`` — always ``"forms"``
    - ``name``          — unique form identifier (auto-generated if not provided)
    - ``ui_schema``     — controls widget rendering and layout
    - ``json_schema``   — defines data types and validation rules
    - ``form_data``     — carries default / pre-filled values
    """

    name: str = Field(default_factory=lambda: f"form_{uuid.uuid4()}")
    title: str
    description: Optional[str] = None
    submit_text: str = "Submit"
    cancel_text: Optional[str] = None
    inputs: List[FormInput]
    response_type: str = "forms"

    def _build_ui_schema(self) -> Dict[str, Any]:
        """Build complete UI schema from inputs"""
        ui_schema: Dict[str, Any] = {
            "ui:order": [inp.name for inp in self.inputs],
            "ui:submitButtonOptions": {
                "submitText": self.submit_text,
            },
        }

        if self.cancel_text is not None:
            ui_schema["ui:cancelButtonOptions"] = {
                "showCancel": True,
                "cancelText": self.cancel_text,
            }
        else:
            ui_schema["ui:cancelButtonOptions"] = {"showCancel": False}

        for inp in self.inputs:
            ui_schema[inp.name] = inp.to_ui_schema()

        return ui_schema

    def _build_json_schema(self) -> Dict[str, Any]:
        """Build complete JSON schema from inputs"""
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for inp in self.inputs:
            properties[inp.name] = inp.to_json_schema()
            if inp.required:
                required.append(inp.name)

        schema: Dict[str, Any] = {
            "type": "object",
            "title": self.title,
            "required": required,
            "properties": properties,
            "additionalProperties": False,
        }

        if self.description:
            schema["description"] = self.description

        return schema

    def _build_form_data(self) -> Dict[str, Any]:
        """Build form data from inputs with default values"""
        form_data: Dict[str, Any] = {}

        for inp in self.inputs:
            data = inp.to_form_data()
            if data is not None:
                form_data[inp.name] = data

        return form_data

    def model_dump(self, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
        """Override Pydantic's model_dump to return the correct form structure"""
        return {
            "response_type": self.response_type,
            "name": self.name,
            "ui_schema": self._build_ui_schema(),
            "json_schema": self._build_json_schema(),
            "form_data": self._build_form_data(),
        }

    def dict(self, **kwargs) -> Dict[str, Any]:  # type: ignore[override]
        """Override Pydantic v1 dict() for backward compatibility"""
        return self.model_dump(**kwargs)



