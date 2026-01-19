

from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, UserNode, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import Assignment, UserFieldKind
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap

class Name(BaseModel):
    """
    This datatype represents a person's name.

    Attributes:
        name (str): The person's first name.
    """
    first_name: str = Field(default="John", description="First name")
    last_name: str = Field(default="Doe", description="Last name")

class Book(BaseModel):
    """
    This datatype represents a book.

    Attributes:
        title (str): The book's title.
        author (str): The book's author.
    """
    title: str = Field(default="Shaken", description="Book title")
    author: str = Field(default="John Grisham", description="Author")

class StringListNames(BaseModel):
    listOfNames: List[Name] = Field(
        default=[{"John", "Doe"}, {"Jane", "Doe"}, {"Jean", "Doe"}],
        description="A list of Name objects with first and last names."
    )

class MyDate(BaseModel):
    """
    This datatype represents date information.

    Attributes:
        dateStart (str): The start date.
        dateEnd (str): The end date.
        dateEvent (str): The event date.
    """
    dateStart: str = Field(default="2023-01-01", description="Start date")
    dateEnd: str = Field(default="2023-12-31", description="End date")
    dateEvent: str = Field(default="2023-06-15", description="Event date")

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

    friends: StringListNames = Field(
        default=StringListNames(
            listOfNames=[
                Name(first_name="John", last_name="Doe"),
                Name(first_name="Jane", last_name="Doe"),
                Name(first_name="Jean", last_name="Doe")
            ]
        ),
        description="A list of friends with their names."
    )
    books: List[Book] = Field(
        default=[Book()],
        description="A list of books."
    )

    event_date: MyDate = Field(
        default=MyDate(),
        description="The event date"
    ),

    listOfFruits: List[str] = Field(
        default=["apple", "oranges", "bananas"],
        description="A list of fruits."
    )

    listOfPreferredFruits: List[str] = Field(
        default=["apple", "oranges"],
        description="A list of preferred fruits."
    )

@flow(
    name ="user_flow_application_form",
    display_name="Application form",
    description="Creates a sample application form.",
    input_schema=FlowInput,
)

def build_user_form(aflow: Flow = None) -> Flow:

    user_flow = aflow.userflow()
    user_flow.spec.display_name= "Application"

    user_node_with_form = user_flow.form(name="ApplicationForm", display_name="Application")
    
    data_map = DataMap()
    data_map.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.salutations"))
 
    #Single-choice: Salutation
    user_node_with_form.single_choice_input_field(name="salutation", label="Salutation", required=True, choices=data_map, 
                                                  show_as_dropdown=True, placeholder_text="Please enter your title")
   
    #Boolean: Married
    user_node_with_form.boolean_input_field(name="married", label="Married", single_checkbox = True, true_label="Married", false_label="Not married")

    #Text: Last Name
    user_node_with_form.text_input_field(name="lastName", label="Last name", required=True, placeholder_text="Enter your name here", help_text="Enter name")

    #Number: Age
    user_node_with_form.number_input_field(name="age", label="Age", required=True, help_text="Enter your age")

    data_map_salary = DataMap()
    data_map_salary.add(Assignment(target_variable="self.input.default", value_expression="flow.input.salary_expectation"))
    
    #Number: Desired Salary
    user_node_with_form.number_input_field(name="salary", label="Desired salary", is_integer=False, help_text="Your dream salary is here", default=data_map_salary)
  
    data_map_desired_salary = DataMap()
    data_map_desired_salary.add(Assignment(target_variable="self.input.value", value_expression="flow.input.salary_expectation"))

     #Field: Projected salary
    user_node_with_form.field_output_field(name="acknowledge", label="Projected salary", value = data_map_desired_salary)

    #Date: End Date
    data_map_end_date = DataMap()
    data_map_end_date.add(Assignment(target_variable="self.input.default",value_expression="flow.input.event_date.dateEnd"))
    user_node_with_form.date_input_field(name="endDate", label="End Date", default=data_map_end_date,required=True)
  
    data_map_list_source = DataMap()
    data_map_list_source.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.listOfLanguages"))
    
    #Output List: Qualification
    user_node_with_form.list_output_field(name="strength", label="Qualification", choices=data_map_list_source)

    #Output list: Friends table
    data_map_list_friends = DataMap()
    data_map_list_friends.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.friends.listOfNames"))
    user_node_with_form.list_output_field(name="friends", label="Friends", choices=data_map_list_friends, columns={"first_name": "First", "last_name": "Last"})

    #Mult-chocice: List of fruits dowpdown primitives
    data_map_multi_choice = DataMap()
    data_map_multi_choice.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.listOfFruits"))

    data_map_multi_choice_default = DataMap()
    data_map_multi_choice_default.add(Assignment(target_variable="self.input.default", value_expression="flow.input.listOfPreferredFruits"))

    user_node_with_form.multi_choice_input_field(name="multi-choice", label="List of Fruits", required=False, choices=data_map_multi_choice, 
                                                  show_as_dropdown=True, placeholder_text="Please enter your choice", default=data_map_multi_choice_default)
    
    #Mult-chocice: Books dowpdown complex
    data_map_list_books = DataMap()
    data_map_list_books.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.books"))
    user_node_with_form.multi_choice_input_field(name="multi-choice_as_dropdown_1", label="List of Books", required=False, choices=data_map_list_books, 
                                                  show_as_dropdown=True, dropdown_item_column="title", placeholder_text="Please enter your choice")
 
    #Mult-chocice: List of names table
    data_map_list_friends_choice2 = DataMap()
    data_map_list_friends_choice2.add(Assignment(target_variable="self.input.choices", value_expression="flow.input.friends.listOfNames"))

    user_node_with_form.multi_choice_input_field(name="multi-choice_as_table", label="List of Names", required=False, choices=data_map_list_friends_choice2, 
                                                  show_as_dropdown=False, placeholder_text="Please enter your choice", columns={"first_name": "First", "last_name": "Last"} )

    #Input list: Books editable table
    data_map_list_books = DataMap()
    data_map_list_books.add(Assignment(target_variable="self.input.default", value_expression="flow.input.books"))

    user_node_with_form.list_input_field(name="books", label="Books", default=data_map_list_books, columns={"title": "Book Title", "author": "Book Author"})
    #Input list: Fuits editable table
    data_map_list_fruits = DataMap()
    data_map_list_fruits.add(Assignment(target_variable="self.input.default", value_expression="flow.input.listOfFruits"))

    user_node_with_form.list_input_field(name="Fruits", label="Preferred fruits", default=data_map_list_fruits)

    #Output Message: Successful submission
    user_node_with_form.message_output_field(name="success", label="Successful submission", message="Application successfully completed.")
 
    #Add user flow edges
    user_flow.edge(START, user_node_with_form)
    user_flow.edge(user_node_with_form, END)

    # Script to initialize friends list
    init_script = """
flow.input.friends.listOfNames = [
    {"first_name": "John", "last_name": "Doe"},
    {"first_name": "Alice", "last_name": "Smith"},
    {"first_name": "Bob", "last_name": "Johnson"}
]
flow.input.books=[
    { "title": "Shaken", "author":"John Grisham"},
    {"title": "The Client", "author":"John Grisham"},
]
flow.input.listOfFruits = ["apple", "oranges", "bananas"]
"""
    init_data = aflow.script(name="init_data", script=init_script)
    
    # add the user flow to the flow sequence to create the flow edges
    aflow.sequence(START, init_data, user_flow, END)
  
    return aflow