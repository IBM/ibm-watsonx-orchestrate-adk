"""
Basic example of using MultiTurnWidget for conversational interactions.

This example demonstrates how to create a simple multi-turn widget that
collects user information across multiple conversational exchanges.

Note: MultiTurnWidget completely reuses FormInput components from FormWidget,
so any future changes to form widgets automatically apply to multi-turn flows.
"""

from ibm_watsonx_orchestrate.run.widgets import (
    MultiTurnWidget,
    TextInput,
    NumberInput,
    Checkbox,
)


def example_1_basic_text_input():
    """Example 1: Basic text input widget"""
    print("=" * 60)
    print("Example 1: Basic Text Input Widget")
    print("=" * 60)
    
    # Create a multi-turn widget for collecting username
    # Note: Title goes on the TextInput, not on MultiTurnWidget
    widget = MultiTurnWidget(
        name="username_collector",
        input=TextInput(
            name="username",
            title="Username",  # Title is on the input component
            required=True,
            placeholder="Enter your username"
        ),
        description="Please provide your username to continue"
    )
    
    # Initialize the widget
    widget.initialize(session_id="demo_session_001")
    
    # Generate response for the user
    response = widget.to_response()
    print("\n📤 Response to send to user:")
    print(f"  Response Type: {response['response_type']}")
    print(f"  Widget Name: {response['name']}")
    print(f"  Session ID: {response['session_id']}")
    print(f"  Turn Number: {response['context']['turn_number']}")
    
    # Simulate user providing input
    print("\n👤 User provides input: 'john.doe'")
    widget.update_state(user_input="john.doe", is_valid=True)
    
    # Check updated state
    print(f"\n✅ State updated:")
    print(f"  Current Turn: {widget.turn_number}")
    print(f"  Total Turns: {len(widget.context.turn_history)}")
    
    # Get summary
    summary = widget.get_summary()
    print(f"\n📊 Summary:")
    print(f"  Widget: {summary['widget_name']}")
    print(f"  Session: {summary['session_id']}")
    print(f"  Completed Turns: {summary['conversation_summary']['completed_turns']}")
    
    # Mark as complete and cleanup
    widget.mark_complete()
    widget.cleanup()
    print("\n✓ Widget interaction complete\n")


def example_2_multi_turn_conversation():
    """Example 2: Multi-turn conversation with multiple widgets"""
    print("=" * 60)
    print("Example 2: Multi-Turn Conversation")
    print("=" * 60)
    
    # Turn 1: Collect name
    print("\n--- Turn 1: Collect Name ---")
    name_widget = MultiTurnWidget(
        name="name_input",
        input=TextInput(
            name="full_name",
            title="Full Name",  # Title on the input
            required=True
        )
    )
    name_widget.initialize(session_id="registration_session")
    
    response1 = name_widget.to_response()
    print(f"📤 Asking for: {response1['json_schema']['properties']['full_name']['title']}")
    
    # User responds
    print("👤 User: 'John Doe'")
    name_widget.update_state("John Doe")
    
    # Turn 2: Collect age
    print("\n--- Turn 2: Collect Age ---")
    age_widget = MultiTurnWidget(
        name="age_input",
        input=NumberInput(
            name="age",
            title="Age",  # Title on the input
            required=True,
            minimum=18,
            maximum=120
        )
    )
    age_widget.initialize(session_id="registration_session")
    
    response2 = age_widget.to_response()
    print(f"📤 Asking for: {response2['json_schema']['properties']['age']['title']}")
    
    # User responds
    print("👤 User: 25")
    age_widget.update_state(25)
    
    # Turn 3: Collect agreement
    print("\n--- Turn 3: Collect Agreement ---")
    agree_widget = MultiTurnWidget(
        name="terms_agreement",
        input=Checkbox(
            name="agree_terms",
            title="I agree to the terms and conditions",  # Title on the input
            required=True
        )
    )
    agree_widget.initialize(session_id="registration_session")
    
    response3 = agree_widget.to_response()
    print(f"📤 Asking for: {response3['json_schema']['properties']['agree_terms']['title']}")
    
    # User responds
    print("👤 User: True")
    agree_widget.update_state(True)
    
    print("\n✓ All registration steps complete!")
    
    # Cleanup all widgets
    name_widget.cleanup()
    age_widget.cleanup()
    agree_widget.cleanup()
    print()


def example_3_validation_and_error_handling():
    """Example 3: Validation and error handling"""
    print("=" * 60)
    print("Example 3: Validation and Error Handling")
    print("=" * 60)
    
    widget = MultiTurnWidget(
        name="email_input",
        input=TextInput(
            name="email",
            title="Email Address",  # Title on the input
            required=True,
            placeholder="user@example.com"
        )
    )
    widget.initialize()
    
    # First attempt - invalid email
    print("\n--- Attempt 1: Invalid Email ---")
    print("👤 User: 'invalid-email'")
    widget.update_state(
        user_input="invalid-email",
        is_valid=False,
        validation_errors=["Invalid email format"]
    )
    
    last_turn = widget.context.get_last_turn()
    if last_turn:
        print(f"❌ Validation failed: {last_turn.widget_state['validation_errors']}")
        print(f"   Turn status: {last_turn.status}")
    
    # Second attempt - valid email
    print("\n--- Attempt 2: Valid Email ---")
    print("👤 User: 'user@example.com'")
    widget.update_state(
        user_input="user@example.com",
        is_valid=True
    )
    
    last_turn = widget.context.get_last_turn()
    if last_turn:
        print(f"✅ Validation passed!")
        print(f"   Turn status: {last_turn.status}")
        print(f"   Value: {last_turn.user_input}")
    
    # Show history
    print(f"\n📜 Conversation History:")
    for i, turn in enumerate(widget.context.turn_history, 1):
        print(f"   Turn {i}: {turn.user_input} - {turn.status}")
    
    widget.cleanup()
    print()


def example_4_context_and_state_management():
    """Example 4: Context and state management"""
    print("=" * 60)
    print("Example 4: Context and State Management")
    print("=" * 60)
    
    widget = MultiTurnWidget(
        name="preference_input",
        input=TextInput(
            name="preference",
            title="Your Preference"
        )
    )
    widget.initialize(session_id="context_demo")
    
    # Add multiple turns with metadata
    print("\n--- Adding turns with metadata ---")
    
    widget.update_state(
        user_input="option1",
        metadata={"source": "web", "timestamp": "2024-01-01T10:00:00"}
    )
    print("✓ Turn 1 added with metadata")
    
    widget.update_state(
        user_input="option2",
        metadata={"source": "mobile", "timestamp": "2024-01-01T10:05:00"}
    )
    print("✓ Turn 2 added with metadata")
    
    # Get context
    print("\n📋 Current Context:")
    context = widget.get_context()
    print(f"   Conversation ID: {context['conversation_id']}")
    print(f"   Session ID: {context['session_id']}")
    print(f"   Current Turn: {context['turn_number']}")
    print(f"   Total History: {len(context['turn_history'])} turns")
    
    # Show turn history with metadata
    print("\n📜 Turn History with Metadata:")
    for turn_data in context['turn_history']:
        print(f"   Turn {turn_data['turn_number']}:")
        print(f"     Input: {turn_data['user_input']}")
        print(f"     Metadata: {turn_data['metadata']}")
    
    widget.cleanup()
    print()


def example_5_response_format_validation():
    """Example 5: Validate response format against Arch.Guide"""
    print("=" * 60)
    print("Example 5: Response Format Validation")
    print("=" * 60)
    
    widget = MultiTurnWidget(
        name="demo_widget",
        input=TextInput(
            name="demo_field",
            title="Demo Field",  # Title on the input
            required=True,
            placeholder="Enter value"
        ),
        description="This is a demo multi-turn form"
    )
    widget.initialize(session_id="validation_session")
    
    response = widget.to_response()
    
    print("\n✓ Validating response structure:")
    
    # Check required fields
    required_fields = [
        "response_type",
        "name",
        "json_schema",
        "ui_schema",
        "form_data",
        "session_id",
        "context"
    ]
    
    for field in required_fields:
        if field in response:
            print(f"  ✓ {field}: present")
        else:
            print(f"  ✗ {field}: MISSING")
    
    # Validate response_type
    if response["response_type"] == "multiturn_form":
        print(f"\n✓ response_type is correct: '{response['response_type']}'")
    else:
        print(f"\n✗ response_type is incorrect: '{response['response_type']}'")
    
    # Validate JSON schema structure
    print("\n✓ JSON Schema structure:")
    json_schema = response["json_schema"]
    print(f"  - type: {json_schema.get('type')}")
    print(f"  - title: {json_schema.get('title')}")
    print(f"  - description: {json_schema.get('description')}")
    print(f"  - properties: {list(json_schema.get('properties', {}).keys())}")
    print(f"  - required: {json_schema.get('required', [])}")
    
    # Validate UI schema structure
    print("\n✓ UI Schema structure:")
    ui_schema = response["ui_schema"]
    for field_name, field_ui in ui_schema.items():
        print(f"  - {field_name}: widget={field_ui.get('ui:widget')}")
    
    # Validate context
    print("\n✓ Context structure:")
    context = response["context"]
    print(f"  - conversation_id: {context.get('conversation_id')}")
    print(f"  - turn_number: {context.get('turn_number')}")
    print(f"  - is_complete: {context.get('is_complete')}")
    
    widget.cleanup()
    print("\n✓ Response format validation complete\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MultiTurnWidget Examples")
    print("=" * 60 + "\n")
    
    # Run all examples
    example_1_basic_text_input()
    example_2_multi_turn_conversation()
    example_3_validation_and_error_handling()
    example_4_context_and_state_management()
    example_5_response_format_validation()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")

# Made with Bob
