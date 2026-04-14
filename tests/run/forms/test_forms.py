"""
Tests for form widgets 

This test suite covers all 11 Phase 1 form widgets to ensure they:
1. Generate correct ui_schema structure
2. Generate correct json_schema structure
3. Handle default values properly
4. Validate required fields
"""

from datetime import date
from ibm_watsonx_orchestrate.run.widgets.forms import (
    FormWidget,
    TextInput,
    TextArea,
    RadioButton,
    Checkbox,
    ComboBox,
    NumberInput,
    DatePicker,
    DateRangePicker,
    FileUpload,
    FileDownload,
    Table,
    TableHeader,
)


class TestTextInput:
    """
    Test TextInput widget
    
    Why: Ensures single-line text input generates correct structure
    Covers: Basic text input, placeholders, default values, required fields
    """
    
    def test_basic_text_input(self):
        """Test basic TextInput without optional fields"""
        widget = TextInput(name="username", title="Username")
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        form_data = widget.to_form_data()
        
        assert ui_schema["ui:widget"] == "TextWidget"
        assert json_schema["type"] == "string"
        assert json_schema["title"] == "Username"
        assert form_data is None
    
    def test_text_input_with_placeholder(self):
        """Test TextInput with placeholder"""
        widget = TextInput(
            name="email",
            title="Email",
            placeholder="user@example.com"
        )
        
        ui_schema = widget.to_ui_schema()
        assert ui_schema["ui:placeholder"] == "user@example.com"
    
    def test_text_input_with_default(self):
        """Test TextInput with default value"""
        widget = TextInput(
            name="name",
            title="Name",
            default_value="John Doe"
        )
        
        form_data = widget.to_form_data()
        assert form_data == "John Doe"


class TestTextArea:
    """
    Test TextArea widget
    
    Why: Ensures multi-line text input generates correct structure
    Covers: Text area, placeholders, default values, autofocus
    """
    
    def test_basic_text_area(self):
        """Test basic TextArea"""
        widget = TextArea(name="description", title="Description")
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "TextareaWidget"
        assert json_schema["type"] == "string"
    
    def test_text_area_with_autofocus(self):
        """Test TextArea with autofocus"""
        widget = TextArea(
            name="comment",
            title="Comment",
            autofocus=True
        )
        
        ui_schema = widget.to_ui_schema()
        assert ui_schema["ui:autofocus"] is True


class TestRadioButton:
    """
    Test RadioButton widget
    
    Why: Ensures radio button group generates correct single-select structure
    Covers: Options, labels, default selection
    """
    
    def test_radio_button_basic(self):
        """Test RadioButton with options"""
        widget = RadioButton(
            name="plan",
            title="Select Plan",
            options=["basic", "pro", "enterprise"]
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "RadioWidget"
        assert json_schema["type"] == "string"
        assert json_schema["enum"] == ["basic", "pro", "enterprise"]
    
    def test_radio_button_with_labels(self):
        """Test RadioButton with custom labels"""
        widget = RadioButton(
            name="plan",
            title="Select Plan",
            options=["basic", "pro"],
            option_labels=["Basic ($10)", "Pro ($25)"]
        )
        
        json_schema = widget.to_json_schema()
        assert json_schema["enumNames"] == ["Basic ($10)", "Pro ($25)"]
    
    def test_radio_button_with_default(self):
        """Test RadioButton with default selection"""
        widget = RadioButton(
            name="plan",
            title="Select Plan",
            options=["basic", "pro"],
            default_value="basic"
        )
        
        form_data = widget.to_form_data()
        assert form_data == "basic"


class TestCheckbox:
    """
    Test Checkbox widget
    
    Why: Ensures boolean checkbox
    Covers: Boolean type, oneOf structure, default value
    """
    
    def test_checkbox_structure(self):
        """Test Checkbox generates correct boolean structure"""
        widget = Checkbox(
            name="agree",
            title="I agree to terms"
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "CheckboxWidget"
        assert json_schema["type"] == "boolean"
        assert "oneOf" in json_schema
        assert json_schema["oneOf"][0]["const"] is True
        assert json_schema["oneOf"][1]["const"] is False
    
    def test_checkbox_default_value(self):
        """Test Checkbox with default value"""
        widget = Checkbox(
            name="subscribe",
            title="Subscribe",
            default_value=True
        )
        
        form_data = widget.to_form_data()
        assert form_data is True


class TestComboBox:
    """
    Test ComboBox widget
    
    Why: Ensures searchable dropdown generates correct structure
    Covers: Options, labels, default selection
    """
    
    def test_combobox_basic(self):
        """Test ComboBox with options"""
        widget = ComboBox(
            name="country",
            title="Country",
            options=["US", "UK", "CA"]
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "ComboboxWidget"
        assert json_schema["enum"] == ["US", "UK", "CA"]
    
    def test_combobox_with_labels(self):
        """Test ComboBox with custom labels"""
        widget = ComboBox(
            name="country",
            title="Country",
            options=["US", "UK"],
            option_labels=["United States", "United Kingdom"]
        )
        
        ui_schema = widget.to_ui_schema()
        assert ui_schema["ui:enumNames"] == ["United States", "United Kingdom"]


class TestNumberInput:
    """
    Test NumberInput widget
    
    Why: Ensures number input with validation generates correct structure
    Covers: Default value, min/max, multipleOf
    """
    
    def test_number_input_basic(self):
        """Test NumberInput basic structure"""
        widget = NumberInput(
            name="quantity",
            title="Quantity"
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "NumberWidget"
        assert json_schema["type"] == "integer"
    
    def test_number_input_with_constraints(self):
        """Test NumberInput with min/max/multipleOf"""
        widget = NumberInput(
            name="quantity",
            title="Quantity",
            default_value=10,
            minimum=1,
            maximum=100,
            multiple_of=5
        )
        
        json_schema = widget.to_json_schema()
        assert json_schema["default"] == 10
        assert json_schema["minimum"] == 1
        assert json_schema["maximum"] == 100
        assert json_schema["multipleOf"] == 5


class TestDatePicker:
    """
    Test DatePicker widget
    
    Why: Ensures single date picker generates correct structure
    Covers: Date format, default value
    """
    
    def test_date_picker_basic(self):
        """Test DatePicker basic structure"""
        widget = DatePicker(
            name="start_date",
            title="Start Date"
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "DateWidget"
        assert json_schema["type"] == "string"
        assert json_schema["format"] == "date"
    
    def test_date_picker_with_default(self):
        """Test DatePicker with default date"""
        widget = DatePicker(
            name="start_date",
            title="Start Date",
            default_value=date(2025, 1, 15)
        )
        
        json_schema = widget.to_json_schema()
        form_data = widget.to_form_data()
        
        assert json_schema["default"] == "2025-01-15"
        assert form_data == "2025-01-15"


class TestDateRangePicker:
    """
    Test DateRangePicker widget
    
    Why: Ensures date range picker generates correct array structure
    Covers: Range option, start/end labels, default dates
    """
    
    def test_date_range_picker_basic(self):
        """Test DateRangePicker basic structure"""
        widget = DateRangePicker(
            name="date_range",
            title="Date Range"
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "DateWidget"
        assert ui_schema["ui:options"]["range"] is True
        assert json_schema["type"] == "array"
        assert json_schema["items"]["format"] == "date"
    
    def test_date_range_picker_with_defaults(self):
        """Test DateRangePicker with default dates"""
        widget = DateRangePicker(
            name="date_range",
            title="Date Range",
            default_start=date(2025, 1, 1),
            default_end=date(2025, 12, 31)
        )
        
        form_data = widget.to_form_data()
        assert form_data == ["2025-01-01", "2025-12-31"]


class TestFileUpload:
    """
    Test FileUpload widget
    
    Why: Ensures file upload generates correct structure with constraints
    Covers: File types, max size, multi-upload, min/max items
    """
    
    def test_file_upload_basic(self):
        """Test FileUpload basic structure"""
        widget = FileUpload(
            name="documents",
            title="Upload Documents"
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "FileUpload"
        assert json_schema["type"] == "array"
        assert json_schema["multi"] is False
    
    def test_file_upload_with_constraints(self):
        """Test FileUpload with file type and size constraints"""
        widget = FileUpload(
            name="documents",
            title="Upload Documents",
            file_types=[".pdf", ".doc"],
            file_max_size=10,
            multi=True,
            max_items=5,
            min_items=1
        )
        
        json_schema = widget.to_json_schema()
        assert json_schema["file_types"] == [".pdf", ".doc"]
        assert json_schema["file_max_size"] == 10
        assert json_schema["multi"] is True
        assert json_schema["maxItems"] == 5
        assert json_schema["minItems"] == 1


class TestFileDownload:
    """
    Test FileDownload widget
    
    Why: Ensures file download generates correct structure
    Covers: File ID, URL, filename
    """
    
    def test_file_download_structure(self):
        """Test FileDownload structure"""
        widget = FileDownload(
            name="report",
            title="Download Report",
            file_id="report_123",
            file_url="https://example.com/report.pdf",
            file_name="report.pdf"
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "FileDownloadWidget"
        assert json_schema["type"] == "string"
        assert json_schema["files"]["id"] == "report_123"
        assert json_schema["files"]["url"] == "https://example.com/report.pdf"
        assert json_schema["files"]["fileName"] == "report.pdf"


class TestTable:
    """
    Test Table widget
    
    Why: Ensures table generates correct structure with headers and data
    Covers: Headers, table types, sorting, searching, min/max items
    """
    
    def test_table_basic(self):
        """Test Table basic structure"""
        widget = Table(
            name="employees",
            title="Employees",
            headers=[
                TableHeader(key="id", header="ID"),
                TableHeader(key="name", header="Name")
            ]
        )
        
        ui_schema = widget.to_ui_schema()
        json_schema = widget.to_json_schema()
        
        assert ui_schema["ui:widget"] == "Table"
        assert json_schema["type"] == "array"
        assert len(json_schema["headers"]) == 2
        assert json_schema["tableType"] == "dataTable"
    
    def test_table_with_selection(self):
        """Test Table with multi-select"""
        widget = Table(
            name="employees",
            title="Employees",
            headers=[TableHeader(key="id", header="ID")],
            table_type="multi",
            max_items=10,
            min_items=1
        )
        
        json_schema = widget.to_json_schema()
        assert json_schema["tableType"] == "multi"
        assert json_schema["maxItems"] == 10
        assert json_schema["minItems"] == 1
    
    def test_table_with_data(self):
        """Test Table with default data"""
        widget = Table(
            name="employees",
            title="Employees",
            headers=[TableHeader(key="id", header="ID")],
            data=[{"id": "E001"}, {"id": "E002"}]
        )
        
        form_data = widget.to_form_data()
        assert len(form_data) == 2
        assert form_data[0]["id"] == "E001"


class TestFormWidget:
    """
    Test FormWidget container
    
    Why: Ensures FormWidget correctly assembles multiple inputs
    Covers: Multiple inputs, required fields, submit/cancel buttons, complete output structure
    """
    
    def test_form_widget_basic(self):
        """Test FormWidget with single input"""
        form = FormWidget(
            title="Test Form",
            inputs=[
                TextInput(name="name", title="Name", required=True)
            ]
        )
        
        output = form.model_dump()
        
        assert output["response_type"] == "forms"
        assert output["json_schema"]["title"] == "Test Form"
        assert "name" in output["json_schema"]["required"]
        assert "name" in output["ui_schema"]
    
    def test_form_widget_multiple_inputs(self):
        """Test FormWidget with multiple different widget types"""
        form = FormWidget(
            title="Registration Form",
            description="Complete registration",
            submit_text="Register",
            cancel_text="Cancel",
            inputs=[
                TextInput(name="email", title="Email", required=True),
                Checkbox(name="agree", title="I agree", required=True),
                NumberInput(name="age", title="Age")
            ]
        )
        
        output = form.model_dump()
        
        assert len(output["json_schema"]["properties"]) == 3
        assert len(output["json_schema"]["required"]) == 2
        assert output["ui_schema"]["ui:submitButtonOptions"]["submitText"] == "Register"
        assert output["ui_schema"]["ui:cancelButtonOptions"]["showCancel"] is True
    
    def test_form_widget_with_defaults(self):
        """Test FormWidget with default values"""
        form = FormWidget(
            title="Test Form",
            inputs=[
                TextInput(name="name", title="Name", default_value="John"),
                NumberInput(name="age", title="Age", default_value=25)
            ]
        )
        
        output = form.model_dump()
        
        assert output["form_data"]["name"] == "John"
        assert output["form_data"]["age"] == 25
    
    def test_form_widget_auto_generated_name(self):
        """Test FormWidget generates unique name if not provided"""
        form1 = FormWidget(title="Form 1", inputs=[])
        form2 = FormWidget(title="Form 2", inputs=[])
        
        output1 = form1.model_dump()
        output2 = form2.model_dump()
        
        assert output1["name"] != output2["name"]
        assert output1["name"].startswith("form_")
        assert output2["name"].startswith("form_")
