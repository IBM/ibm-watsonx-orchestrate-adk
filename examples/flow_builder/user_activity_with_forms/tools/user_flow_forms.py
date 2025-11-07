

from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, UserNode, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import Assignment, UserFieldKind
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap

class Name(BaseModel):
    """
    This class represents a person's name.

    Attributes:
        name (str): The person's first name.
    """
    first_name: str = Field(default="John", description="First name")
    last_name: str = Field(default="Doe", description="Last name")

class StringListNames(BaseModel):
    listOfNames: List[Name] = Field(
        default=[{"John", "Doe"}, {"Jane", "Doe"}, {"Jean", "Doe"}],
        description="A list of string values."
    )

class FlowInput(BaseModel):
    salutations: List[str] = Field(
        default=["Mr", "Mrs"],
        description="A list of string salutations."
    )
    listOfLanguages: List[str] = Field(
        default=["java", "python", "typescript"],
        description="A list of languages."
    )
    salary_expectation: int = Field(
        default=200000,
        description="Expected salary as an integer number."
    )


@flow(
    name ="user_flow_application_form",
    display_name="Application form",
    description="Creates an application form.",
    input_schema=FlowInput,
)

def build_user_form(aflow: Flow = None) -> Flow:

    user_flow = aflow.userflow()
    user_flow.spec.display_name= "Application"
    

    user_node_with_form = user_flow.form(name="ApplicationForm", display_name="Application")
    
    data_map = DataMap()
    data_map.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.salutations"))
 
    #Salutatiom
    user_node_with_form.single_choice_input_field(name="Salutation", label="Salutation", required=True, choices=data_map, 
                                                  show_as_dropdown=True, placeholder_text="Please enter your title")
   
    #Boolean married
    user_node_with_form.boolean_input_field(name="Married", label="Married", single_checkbox = True, true_label="Married", false_label="Not married")

    #Text fiels "lastName"
    user_node_with_form.text_input_field(name="LastName", label="Last name", required=True, placeholder_text="Enter your last name", help_text="Enter last name")

    #Number widget Age"
    user_node_with_form.number_input_field(name="Age", label="Age", required=True, help_text="Enter your age")

    data_map_salary = DataMap()
    data_map_salary.add(Assignment(target_variable="self.input.default", value_expression="flow.input.salary_expectation"))
    
    #Number widget salary"
    user_node_with_form.number_input_field(name="Salary", label="Desired salary", is_integer=False, help_text="Your dream salary is here", default=data_map_salary)
  
    data_map_desired_salary = DataMap()
    data_map_desired_salary.add(Assignment(target_variable="self.input.value", value_expression="flow.input.salary_expectation"))
    
     #Field widget salary"
    user_node_with_form.field_output_field(name="acknowledge", label="Desired salary", value = data_map_desired_salary)

    data_map_list_source = DataMap()
    data_map_list_source.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.listOfLanguages"))
    
    #  #List output widget"
    user_node_with_form.list_output_field(name="strength", label="Qualification", choices=data_map_list_source)

    #List output widget"
    user_node_with_form.message_output_field(name="success", label="Successful submission", message="Application successfully completed.")
 

    # A user flow edges
    user_flow.edge(START, user_node_with_form)
    user_flow.edge(user_node_with_form, END)
    
    # add the user flow to the flow sequence to create the flow edges
    aflow.sequence(START, user_flow, END)

  
    return aflow
