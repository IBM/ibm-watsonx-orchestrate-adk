"""
Tests for MultiTurnWidget class.

This test suite covers the MultiTurnWidget functionality including:
- Widget initialization
- State management
- Context tracking
- Lifecycle methods
- Response generation
- Widget input integration
"""

import pytest
from datetime import datetime

from ibm_watsonx_orchestrate.run.widgets import (
    MultiTurnWidget,
    TextInput,
    TextArea,
    NumberInput,
    Checkbox,
    RadioButton,
    ComboBox,
    DatePicker,
    TurnStatus,
)


class TestMultiTurnWidgetInitialization:
    """Test MultiTurnWidget initialization"""

    def test_basic_initialization(self):
        """Test basic widget initialization"""
        widget = MultiTurnWidget(
            name="test_widget",
            input=TextInput(
                name="username",
                title="Username",
                required=True
            )
        )
        
        assert widget.name == "test_widget"
        assert widget.input.name == "username"
        assert widget.response_type == "multiturn_form"
        assert widget.turn_number == 1
        assert widget.is_complete is False

    def test_auto_generated_name(self):
        """Test auto-generated widget name"""
        widget1 = MultiTurnWidget(
            input=TextInput(name="field1", title="Field 1")
        )
        widget2 = MultiTurnWidget(
            input=TextInput(name="field2", title="Field 2")
        )
        
        assert widget1.name.startswith("multiturn_")
        assert widget2.name.startswith("multiturn_")
        assert widget1.name != widget2.name

    def test_initialize_method(self):
        """Test initialize() method"""
        widget = MultiTurnWidget(
            input=TextInput(name="email", title="Email")
        )
        
        widget.initialize(session_id="test_session_123")
        
        assert widget.session_id == "test_session_123"
        assert widget.context.session_id == "test_session_123"
        assert widget.turn_number == 1
        assert widget.is_complete is False

    def test_initialize_auto_session_id(self):
        """Test initialize() with auto-generated session ID"""
        widget = MultiTurnWidget(
            input=TextInput(name="email", title="Email")
        )
        
        widget.initialize()
        
        assert widget.session_id is not None
        assert widget.session_id.startswith("session_")
        assert widget.context.session_id == widget.session_id


class TestMultiTurnWidgetStateManagement:
    """Test state management functionality"""

    def test_update_state_basic(self):
        """Test basic state update"""
        widget = MultiTurnWidget(
            input=TextInput(name="username", title="Username")
        )
        widget.initialize()
        
        initial_turn = widget.turn_number
        widget.update_state(user_input="john.doe")
        
        assert widget.turn_number == initial_turn + 1
        assert len(widget.context.turn_history) == 1
        
        last_turn = widget.context.get_last_turn()
        assert last_turn is not None
        assert last_turn.user_input == "john.doe"
        assert last_turn.status == TurnStatus.COMPLETED

    def test_update_state_with_validation_error(self):
        """Test state update with validation errors"""
        widget = MultiTurnWidget(
            input=TextInput(name="email", title="Email", required=True)
        )
        widget.initialize()
        
        widget.update_state(
            user_input="invalid-email",
            is_valid=False,
            validation_errors=["Invalid email format"]
        )
        
        last_turn = widget.context.get_last_turn()
        assert last_turn is not None
        assert last_turn.status == TurnStatus.FAILED
        assert last_turn.widget_state["is_valid"] is False
        assert "Invalid email format" in last_turn.widget_state["validation_errors"]

    def test_update_state_with_metadata(self):
        """Test state update with metadata"""
        widget = MultiTurnWidget(
            input=TextInput(name="name", title="Name")
        )
        widget.initialize()
        
        metadata = {"source": "api", "timestamp": "2024-01-01"}
        widget.update_state(
            user_input="John Doe",
            metadata=metadata
        )
        
        last_turn = widget.context.get_last_turn()
        assert last_turn is not None
        assert last_turn.metadata == metadata

    def test_multiple_state_updates(self):
        """Test multiple state updates"""
        widget = MultiTurnWidget(
            input=TextInput(name="field", title="Field")
        )
        widget.initialize()
        
        widget.update_state("value1")
        widget.update_state("value2")
        widget.update_state("value3")
        
        assert widget.turn_number == 4  # Started at 1, 3 updates
        assert len(widget.context.turn_history) == 3
        
        history = widget.context.get_history()
        assert history[0].user_input == "value1"
        assert history[1].user_input == "value2"
        assert history[2].user_input == "value3"


class TestMultiTurnWidgetContext:
    """Test context tracking functionality"""

    def test_get_context(self):
        """Test get_context() method"""
        widget = MultiTurnWidget(
            name="test_widget",
            input=TextInput(name="field", title="Field")
        )
        widget.initialize(session_id="session_123")
        
        context = widget.get_context()
        
        assert context["session_id"] == "session_123"
        assert context["widget_name"] == "test_widget"
        assert context["turn_number"] == 1
        assert context["is_complete"] is False
        assert "conversation_id" in context

    def test_set_context(self):
        """Test set_context() method"""
        widget = MultiTurnWidget(
            input=TextInput(name="field", title="Field")
        )
        widget.initialize()
        
        new_context = {
            "turn_number": 5,
            "is_complete": True,
            "session_id": "new_session"
        }
        widget.set_context(new_context)
        
        assert widget.turn_number == 5
        assert widget.is_complete is True
        assert widget.session_id == "new_session"

    def test_context_history_tracking(self):
        """Test context tracks turn history"""
        widget = MultiTurnWidget(
            input=TextInput(name="field", title="Field")
        )
        widget.initialize()
        
        widget.update_state("input1")
        widget.update_state("input2")
        
        context = widget.get_context()
        assert len(context["turn_history"]) == 2
        assert context["turn_history"][0]["user_input"] == "input1"
        assert context["turn_history"][1]["user_input"] == "input2"


class TestMultiTurnWidgetLifecycle:
    """Test lifecycle methods"""

    def test_mark_complete(self):
        """Test mark_complete() method"""
        widget = MultiTurnWidget(
            input=TextInput(name="field", title="Field")
        )
        widget.initialize()
        
        assert widget.is_complete is False
        assert widget.context.is_active is True
        
        widget.mark_complete()
        
        assert widget.is_complete is True
        assert widget.context.is_active is False

    def test_cleanup_without_delete(self):
        """Test cleanup() without deleting state"""
        widget = MultiTurnWidget(
            input=TextInput(name="field", title="Field")
        )
        widget.initialize()
        widget.update_state("test_value")
        
        widget.cleanup(delete_state=False)
        
        assert widget.is_complete is True
        # State should still exist
        assert widget.session_id is not None
        assert widget.state_manager.exists(widget.session_id)

    def test_cleanup_with_delete(self):
        """Test cleanup() with state deletion"""
        widget = MultiTurnWidget(
            input=TextInput(name="field", title="Field")
        )
        widget.initialize()
        widget.update_state("test_value")
        
        session_id = widget.session_id
        assert session_id is not None
        widget.cleanup(delete_state=True)
        
        assert widget.is_complete is True
        # State should be deleted
        assert not widget.state_manager.exists(session_id)


class TestMultiTurnWidgetResponse:
    """Test response generation"""

    def test_to_response_basic(self):
        """Test basic response generation"""
        widget = MultiTurnWidget(
            name="email_widget",
            input=TextInput(
                name="email",
                title="Email Address",
                required=True,
                placeholder="user@example.com"
            ),
            title="Contact Information",
            description="Please provide your email"
        )
        widget.initialize(session_id="session_123")
        
        response = widget.to_response()
        
        assert response["response_type"] == "multiturn_form"
        assert response["name"] == "email_widget"
        assert response["session_id"] == "session_123"
        
        # Check JSON schema
        assert "json_schema" in response
        assert response["json_schema"]["type"] == "object"
        assert response["json_schema"]["title"] == "Contact Information"
        assert response["json_schema"]["description"] == "Please provide your email"
        assert "email" in response["json_schema"]["properties"]
        assert response["json_schema"]["required"] == ["email"]
        
        # Check UI schema
        assert "ui_schema" in response
        assert "email" in response["ui_schema"]
        assert response["ui_schema"]["email"]["ui:widget"] == "TextWidget"
        
        # Check context
        assert "context" in response
        assert response["context"]["turn_number"] == 1
        assert response["context"]["is_complete"] is False

    def test_to_response_with_default_value(self):
        """Test response with default value"""
        widget = MultiTurnWidget(
            input=TextInput(
                name="username",
                title="Username",
                default_value="john.doe"
            )
        )
        widget.initialize()
        
        response = widget.to_response()
        
        assert "form_data" in response
        assert response["form_data"]["username"] == "john.doe"

    def test_model_dump_returns_response(self):
        """Test model_dump() returns response structure"""
        widget = MultiTurnWidget(
            input=TextInput(name="field", title="Field")
        )
        widget.initialize()
        
        dumped = widget.model_dump()
        response = widget.to_response()
        
        assert dumped == response
        assert dumped["response_type"] == "multiturn_form"


class TestMultiTurnWidgetWithDifferentInputs:
    """Test MultiTurnWidget with different input types"""

    def test_with_textarea(self):
        """Test with TextArea input"""
        widget = MultiTurnWidget(
            input=TextArea(
                name="description",
                title="Description",
                placeholder="Enter description"
            )
        )
        widget.initialize()
        
        response = widget.to_response()
        assert response["ui_schema"]["description"]["ui:widget"] == "TextareaWidget"

    def test_with_number_input(self):
        """Test with NumberInput"""
        widget = MultiTurnWidget(
            input=NumberInput(
                name="age",
                title="Age",
                minimum=0,
                maximum=120
            )
        )
        widget.initialize()
        
        response = widget.to_response()
        assert response["json_schema"]["properties"]["age"]["type"] == "integer"
        assert response["json_schema"]["properties"]["age"]["minimum"] == 0
        assert response["json_schema"]["properties"]["age"]["maximum"] == 120

    def test_with_checkbox(self):
        """Test with Checkbox input"""
        widget = MultiTurnWidget(
            input=Checkbox(
                name="agree",
                title="I agree to terms",
                default_value=False
            )
        )
        widget.initialize()
        
        response = widget.to_response()
        assert response["json_schema"]["properties"]["agree"]["type"] == "boolean"
        assert response["form_data"]["agree"] is False

    def test_with_radio_button(self):
        """Test with RadioButton input"""
        widget = MultiTurnWidget(
            input=RadioButton(
                name="choice",
                title="Select option",
                options=["option1", "option2", "option3"],
                default_value="option1"
            )
        )
        widget.initialize()
        
        response = widget.to_response()
        assert response["json_schema"]["properties"]["choice"]["enum"] == [
            "option1", "option2", "option3"
        ]
        assert response["form_data"]["choice"] == "option1"

    def test_with_combobox(self):
        """Test with ComboBox input"""
        widget = MultiTurnWidget(
            input=ComboBox(
                name="country",
                title="Country",
                options=["USA", "Canada", "Mexico"]
            )
        )
        widget.initialize()
        
        response = widget.to_response()
        assert response["ui_schema"]["country"]["ui:widget"] == "ComboboxWidget"
        assert response["json_schema"]["properties"]["country"]["enum"] == [
            "USA", "Canada", "Mexico"
        ]

    def test_with_date_picker(self):
        """Test with DatePicker input"""
        from datetime import date
        
        widget = MultiTurnWidget(
            input=DatePicker(
                name="birthdate",
                title="Birth Date",
                default_value=date(1990, 1, 1)
            )
        )
        widget.initialize()
        
        response = widget.to_response()
        assert response["json_schema"]["properties"]["birthdate"]["format"] == "date"
        assert response["form_data"]["birthdate"] == "1990-01-01"


class TestMultiTurnWidgetSummary:
    """Test summary functionality"""

    def test_get_summary(self):
        """Test get_summary() method"""
        widget = MultiTurnWidget(
            name="test_widget",
            input=TextInput(name="field", title="Field")
        )
        widget.initialize(session_id="session_123")
        
        widget.update_state("value1")
        widget.update_state("value2")
        
        summary = widget.get_summary()
        
        assert summary["widget_name"] == "test_widget"
        assert summary["input_name"] == "field"
        assert summary["session_id"] == "session_123"
        assert summary["current_turn"] == 3  # Started at 1, 2 updates
        assert summary["is_complete"] is False
        assert "conversation_summary" in summary
        assert summary["conversation_summary"]["total_turns"] == 2

# Made with Bob
