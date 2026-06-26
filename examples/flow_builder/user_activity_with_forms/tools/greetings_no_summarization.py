from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END
)

@flow(
    name="greetings_no_summarization",
    display_name="Greetings (No Summarization)",
    description="A simple greeting flow with agent summarization suppressed."
)
def build_greeting_flow(aflow: Flow = None) -> Flow:
    """
    Creates a simple greeting flow that demonstrates the suppress_agent_summarization flag.
    
    When suppress_agent_summarization is set to True, the agent will not generate
    summaries during flow execution, which can be useful for simple, straightforward
    flows where summarization adds unnecessary overhead.
    """
    
    # Create a user flow for the greeting
    user_flow = aflow.userflow()
    user_flow.spec.display_name = "Greeting"
    
    # Create a simple form with a display message
    greeting_form = user_flow.form(
        name="GreetingForm",
        display_name="Welcome",
        cancel_button_label="Close"
    )
    
    # Add a message output field that displays "Hello user"
    greeting_form.message_output_field(
        name="greeting_message",
        label="Welcome Message",
        message="Hello user"
    )
    
    # Connect the flow nodes
    user_flow.edge(START, greeting_form)
    user_flow.edge(greeting_form, END, button_label="Submit")
    
    # Add the user flow to the main flow sequence
    aflow.sequence(START, user_flow, END)
    
    return aflow
