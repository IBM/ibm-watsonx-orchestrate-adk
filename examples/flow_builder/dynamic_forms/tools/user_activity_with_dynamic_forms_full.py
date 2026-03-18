
from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, UserNode, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import Assignment
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap
from ibm_watsonx_orchestrate.flow_builder.utils import RuleBuilder


class FlowInput(BaseModel):
    """Input schema for the flow."""
    countries: List[str] = Field(
        default=["USA", "Canada"],
        description="A list of available countries."
    )
    usa_states: List[str] = Field(
        default=["California", "Texas", "New York", "Florida"],
        description="A list of US states."
    )
    canada_provinces: List[str] = Field(
        default=["Ontario", "Quebec", "British Columbia", "Alberta"],
        description="A list of Canadian provinces."
    )
    default_country: str = Field(
        default="USA",
        description="Default country selection."
    )
    default_region: str = Field(
        default="California",
        description="Default region selection."
    )


@flow(
    name="user_activity_with_dynamic_forms_full",
    display_name="Dynamic Form - A simple example",
    description="Demonstrates dynamic form behaviours",
    input_schema=FlowInput,
)
def build_dynamic_form_full(aflow: Flow = None) -> Flow:
    
    # Create user flow
    user_flow = aflow.userflow()
    user_flow.spec.display_name = "Example dynamic form"
    
    # Create form node
    form_node = user_flow.form(
        name="dynamic_form", 
        display_name="Dynamic form example",
        cancel_button_label="Cancel")
    
    #FIELD 1: Country
    country_choices = DataMap()
    country_choices.add(Assignment(
        target_variable="self.input.choices",
        value_expression="flow.input.countries"
    ))
    
    country_default = DataMap()
    country_default.add(Assignment(
        target_variable="self.input.default",
        value_expression="flow.input.default_country"
    ))
    
    form_node.single_choice_input_field(
        name="country",
        label="Country",
        required=False,
        choices=country_choices,
        default=country_default,
        show_as_dropdown=True,
        placeholder_text="Select an option"
    )
    
    #FIELD 2: Visibility Behaviour
    # Controls city and url fields
    form_node.visibility_behaviour_field(
        name="visibility_behaviour",
        on_change_to_field="country",
        rules=[
            RuleBuilder.visibility_rule(
                field_name="country",
                field_value="USA",
                impacted_field="city",
                visible_when_true=True,
                operator="equals"
            ),
            RuleBuilder.visibility_rule(
                field_name="country",
                field_value="Canada",
                impacted_field="url",
                visible_when_true=True,
                operator="equals"
            )
        ],
        display_name="Visibility rule"
    )
    
    # FIELD 3: Label Behaviour
    # Controls code, region, and documents field labels
    form_node.label_behaviour_field(
        name="label_behaviour",
        on_change_to_field="country",
        rules=[
            RuleBuilder.label_rule(
                field_name="country",
                field_value="USA",
                impacted_field="code",
                label_when_true="Zip code",
                label_when_false="Postal code",
                operator="equals"
            ),
            RuleBuilder.label_rule(
                field_name="country",
                field_value="USA",
                impacted_field="region",
                label_when_true="State",
                label_when_false="Province",
                operator="equals"
            ),
            RuleBuilder.label_rule(
                field_name="country",
                field_value="USA",
                impacted_field="documents",
                label_when_true="US W-2 Form",
                label_when_false="Canadian T4 Form",
                operator="equals"
            )
        ],
        display_name="Label rule"
    )
    
    # FIELD 4: Value-Source Behaviour
    # Populates region field options from tool
    form_node.value_source_behaviour_field(
        name="value_source_behaviour",
        on_change_to_field="country",
        impacted_field="region",
        tool_name="get_states_or_provinces",
        tool_id="9f0ecb53-dbd9-4e41-be46-29c8d47d6df8",
        field_mappings={
            "country": "parent.field.country"
        },
        display_name="ProgSelect"
    )
    
    # FIELD 5: Region
    region_choices = DataMap()
    region_choices.add(Assignment(
        target_variable="self.input.choices",
        value_expression='',
        has_no_value=True
    ))
    region_choices.add(Assignment(
        target_variable="self.input.display_text",
        value_expression='',
        has_no_value=True
    ))
    region_choices.add(Assignment(
        target_variable="self.input.display_items",
        value_expression='',
        has_no_value=True
    ))
    
    form_node.single_choice_input_field(
        name="region",
        label="Region",
        required=False,
        choices=region_choices,
        show_as_dropdown=True,
        placeholder_text="Select an option"
    )
    
    # FIELD 6: Code
    form_node.text_input_field(
        name="code",
        label="Code",
        required=False
    )
    
    # FIELD 7: City
    form_node.text_input_field(
        name="city",
        label="City",
        required=False
    )
    
    # FIELD 8: Documents
    form_node.file_upload_field(
        name="documents",
        label="Documents"
    )
    
    # FIELD 9: URL
    form_node.text_input_field(
        name="url",
        label="URL",
        required=False
    )
    
    # Add edges
    user_flow.edge(START, form_node)
    user_flow.edge(form_node, END)
    
    # Script to initialize input data
    init_script = """
# Initialize countries list
flow.input.countries = ["USA", "Canada"]

# Initialize US states
flow.input.usa_states = ["California", "Texas", "New York", "Florida", "Illinois", "Pennsylvania"]

# Initialize Canadian provinces
flow.input.canada_provinces = ["Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba", "Saskatchewan"]

# Set default selections
flow.input.default_country = "USA"
flow.input.default_region = "California"
"""
    init_data = aflow.script(name="init_data", script=init_script)
    
    # Add user flow to main flow with initialization
    aflow.sequence(START, init_data, user_flow, END)
    
    return aflow
