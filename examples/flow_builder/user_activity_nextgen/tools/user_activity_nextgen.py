"""Next-gen UserActivity example (spec_version 2.0).

A UserActivity is a single-widget user interaction inside a UserFlow. Unlike a
form, an activity holds exactly one widget and — for input widgets — pairs a
display `label` with an `agent_message` (the chat prompt that supports
`{flow.input.*}` substitutions).

Compare with the legacy single-field pattern in
examples/flow_builder/user_activity/tools/user_flow.py — that path uses
`user_flow.field(...)` and conflates label vs. prompt via `text=`. The next-gen
API mirrors the form builder pattern: create the activity, then attach one
widget with the widget-specific method (e.g. `.boolean_input_field(...)`).
"""

from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, START, END


class UserContext(BaseModel):
    """Flow inputs referenced by the activities' agent_message templates."""
    myname: str = Field(default="Jane", description="User's name for prompts")
    day_of_week: str = Field(default="Monday", description="Current day for the greeting")


@flow(
    name="next_gen_user_activity_example",
    display_name="Next-gen UserActivity example",
    description="Demonstrates single-widget UserActivity nodes with spec_version 2.0.",
    input_schema=UserContext,
)
def build(aflow: Flow = None) -> Flow:
    # `display_name` is the build-time node name shown in the flow builder.
    # `label` is what the user sees in the Chat at runtime, and it supports
    # variable substitution.
    user_flow = aflow.userflow(
        display_name="Onboarding",
        label="Welcome, {flow.input.myname}",
    )

    # Boolean input activity — renders as radio buttons in Chat.
    #   label         -> field.display_name, uiSchema["ui:title"], jsonSchema property title
    #   agent_message -> jsonSchema.description (the chat prompt)
    tos_node = user_flow.activity(name="confirm_tos", display_name="Confirmation")
    tos_node.boolean_input_field(
        name="agree",
        label="I agree",
        agent_message="I {flow.input.myname} have read the terms and conditions",
        single_checkbox=False,
        true_label="Yes",
        false_label="No",
        required=True,
    )

    # Text input activity — a follow-up free-text prompt.
    last_name_node = user_flow.activity(name="ask_last_name", display_name="Last name")
    last_name_node.text_input_field(
        name="last_name",
        label="Last name",
        agent_message="What is your last name?",
        required=True,
    )

    # Number input activity.
    age_node = user_flow.activity(name="ask_age", display_name="Age")
    age_node.number_input_field(
        name="age",
        label="Age",
        agent_message="How old are you, {flow.input.myname}?",
    )

    # Present-to-User-Message — the Text-output exception.
    #   agent_message -> field.text; no ui:title, no jsonSchema.description.
    #   Prefer `text=` in call sites since that's what the field carries.
    greet_node = user_flow.activity(name="greet_user", display_name="Greeting")
    greet_node.message_output_field(
        name="greeting",
        text="Hello {flow.input.myname}! Today is {flow.input.day_of_week}.",
    )

    user_flow.edge(START, tos_node)
    user_flow.edge(tos_node, last_name_node)
    user_flow.edge(last_name_node, age_node)
    user_flow.edge(age_node, greet_node)
    user_flow.edge(greet_node, END)

    aflow.sequence(START, user_flow, END)
    return aflow
