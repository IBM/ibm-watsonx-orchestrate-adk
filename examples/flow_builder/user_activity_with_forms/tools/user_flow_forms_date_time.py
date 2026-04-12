
from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, UserNode, START, END
)
from ibm_watsonx_orchestrate.flow_builder.types import Assignment, UserFieldKind
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap

class MyDate(BaseModel):
    """
    This datatype represents date information.

    Attributes:
        dateStart (str): The start date.
        dateEnd (str): The end date.
        dateEvent (str): The event date.
        dateSimple (str): A simple date without constraints.
        dateList (List[str]): A list of dates for multiple date selection.
    """
    dateStart: str = Field(default="2023-01-01", description="Start date")
    dateEnd: str = Field(default="2023-12-31", description="End date")
    dateEvent: str = Field(default="2023-06-15", description="Event date")
    dateSimple: str = Field(default="2023-07-01", description="Simple date")
    dateList: List[str] = Field(
        default=["2023-08-10", "2023-08-15", "2023-08-20"],
        description="List of alternative availability dates"
    )

class MyTime(BaseModel):
    """
    This datatype represents time information.

    Attributes:
        timeStart (str): The start time.
        timeEnd (str): The end time.
        timeDefaultStart (str): The default start time.
        timeDefaultEnd (str): The default end time.
        timeSimple (str): A simple time without constraints.
    """
    timeStart: str = Field(default="09:00", description="Start time")
    timeEnd: str = Field(default="17:00", description="End time")
    timeDefaultStart: str = Field(default="10:00", description="Default start time")
    timeDefaultEnd: str = Field(default="16:00", description="Default end time")
    timeSimple: str = Field(default="12:00", description="Simple time")

class MyDateTime(BaseModel):
    """
    This datatype represents datetime information.

    Attributes:
        dateTimeStart (str): The start datetime.
        dateTimeEnd (str): The end datetime.
        dateTimeEvent (str): The event datetime.
        dateTimeSimple (str): A simple datetime without constraints.
    """
    dateTimeStart: str = Field(default="2023-01-01T09:00:00", description="Start datetime")
    dateTimeEnd: str = Field(default="2023-12-31T17:00:00", description="End datetime")
    dateTimeEvent: str = Field(default="2023-06-15T14:00:00", description="Event datetime")
    dateTimeSimple: str = Field(default="2023-07-01T12:00:00", description="Simple datetime")

class FlowInputDateTime(BaseModel):
    event_date: MyDate = Field(
        default=MyDate(),
        description="The event date"
    )
    event_time: MyTime = Field(
        default=MyTime(),
        description="The event time"
    )
    event_datetime: MyDateTime = Field(
        default=MyDateTime(),
        description="The event datetime"
    )

@flow(
    name="user_flow_application_form_date_time",
    display_name="Application form date time",
    description="Creates a comprehensive form with all date, time, and datetime field variations.",
    input_schema=FlowInputDateTime,
)

def build_user_form_date_time(aflow: Flow = None) -> Flow:

    user_flow = aflow.userflow()
    user_flow.spec.display_name = "Date Time Application"

    # Create form with default submit button and visible cancel button
    user_node_with_form = user_flow.form(
        name="DateTimeForm",
        display_name="Comprehensive Date and Time Form",
        cancel_button_label="Cancel"
    )
    
    # ========== DATE FIELDS ==========
    
    # 1. Date WITHOUT Range Limit: Simple Date
    data_map_simple_date = DataMap()
    data_map_simple_date.add(Assignment(target_variable="self.input.default", value_expression="flow.input.event_date.dateSimple"))
    user_node_with_form.date_input_field(
        name="Casual day off",
        label="Casual day off",
        default=data_map_simple_date,
        required=False
    )
    
    # 2. Date WITH Range Limit: Event Date with min/max constraints
    data_map_date_default = DataMap()
    data_map_date_default.add(Assignment(target_variable="self.input.default", value_expression="flow.input.event_date.dateEvent"))
    
    data_map_range_start = DataMap()
    data_map_range_start.add(Assignment(target_variable="self.input.min_date", value_expression="flow.input.event_date.dateStart"))
    
    data_map_range_end = DataMap()
    data_map_range_end.add(Assignment(target_variable="self.input.max_date", value_expression="flow.input.event_date.dateEnd"))
    
    user_node_with_form.date_input_field(
        name="Employee vacation",
        label="Employee vacation",
        default=data_map_date_default,
        min_date=data_map_range_start,
        max_date=data_map_range_end,
        required=True
    )
    
    # 2b. Date Field with Multiple Dates (with default value)
    data_map_multiple_dates = DataMap()
    data_map_multiple_dates.add(Assignment(target_variable="self.input.default", value_expression="flow.input.event_date.dateList"))
    
    user_node_with_form.date_input_field(
        name="Alternative availability dates",
        label="Alternative availability dates",
        default=data_map_multiple_dates,
        min_date=data_map_range_start,
        max_date=data_map_range_end,
        multiple_dates=True
    )
    
    # ========== TIME FIELDS ==========
    
    # 3. Time WITHOUT Range Limit: Simple Time
    data_map_simple_time = DataMap()
    data_map_simple_time.add(Assignment(target_variable="self.input.default", value_expression="flow.input.event_time.timeSimple"))
    user_node_with_form.datetime_input_field(
        name="Lunch time",
        label="Lunch time",
        inputType=UserFieldKind.Time,
        default=data_map_simple_time,
        required=False
    )
    
    # 4. Time WITH Range Limit: Time with min/max constraints
    data_map_time_default = DataMap()
    data_map_time_default.add(Assignment(target_variable="self.input.default", value_expression="flow.input.event_time.timeDefaultStart"))
    
    data_map_time_range_start = DataMap()
    data_map_time_range_start.add(Assignment(target_variable="self.input.min_time", value_expression="flow.input.event_time.timeStart"))
    
    data_map_time_range_end = DataMap()
    data_map_time_range_end.add(Assignment(target_variable="self.input.max_time", value_expression="flow.input.event_time.timeEnd"))
    
    user_node_with_form.datetime_input_field(
        name="Login time",
        label="Login time",
        inputType=UserFieldKind.Time,
        default=data_map_time_default,
        min_time=data_map_time_range_start,
        max_time=data_map_time_range_end,
        required=True
    )
    
    # ========== DATETIME FIELDS ==========
    
    # 5. DateTime WITHOUT Range Limit: Simple DateTime
    data_map_simple_datetime = DataMap()
    data_map_simple_datetime.add(Assignment(target_variable="self.input.default", value_expression="flow.input.event_datetime.dateTimeSimple"))
    user_node_with_form.datetime_input_field(
        name="Release Cutoff",
        label="Release Cutoff",
        inputType=UserFieldKind.DateTime,
        default=data_map_simple_datetime,
        required=False
    )
    
    # 6. DateTime WITH Range Limit: DateTime with min/max constraints
    data_map_datetime_default = DataMap()
    data_map_datetime_default.add(Assignment(target_variable="self.input.default", value_expression="flow.input.event_datetime.dateTimeEvent"))
    
    data_map_datetime_range_start = DataMap()
    data_map_datetime_range_start.add(Assignment(target_variable="self.input.min_time", value_expression="flow.input.event_datetime.dateTimeStart"))
    
    data_map_datetime_range_end = DataMap()
    data_map_datetime_range_end.add(Assignment(target_variable="self.input.max_time", value_expression="flow.input.event_datetime.dateTimeEnd"))
    
    user_node_with_form.datetime_input_field(
        name="Project submission period",
        label="Project submission period",
        inputType=UserFieldKind.DateTime,
        default=data_map_datetime_default,
        min_time=data_map_datetime_range_start,
        max_time=data_map_datetime_range_end,
        required=True
    )
    
    # ========== DATE RANGE FIELDS ==========
    
    # 7. Date Range: Start and End Dates
    data_map_date_range_start = DataMap()
    data_map_date_range_start.add(Assignment(target_variable="self.input.default_start", value_expression="flow.input.event_date.dateStart"))
    
    data_map_date_range_end = DataMap()
    data_map_date_range_end.add(Assignment(target_variable="self.input.default_end", value_expression="flow.input.event_date.dateEnd"))
    
    data_map_min_date = DataMap()
    data_map_min_date.add(Assignment(target_variable="self.input.min_date", value_expression="flow.input.event_date.dateStart"))
    
    data_map_max_date = DataMap()
    data_map_max_date.add(Assignment(target_variable="self.input.max_date", value_expression="flow.input.event_date.dateEnd"))
    
    user_node_with_form.date_range_input_field(
        name="Employee probation period",
        label="Employee probation",
        required=True,
        start_date_label="Start Date",
        end_date_label="End Date",
        default_start=data_map_date_range_start,
        default_end=data_map_date_range_end,
        min_date=data_map_min_date,
        max_date=data_map_max_date
    )
    
    # ========== TIME RANGE FIELDS ==========
    
    # 8. Time Range: Working Hours with start and end times
    data_map_time_range_start = DataMap()
    data_map_time_range_start.add(Assignment(target_variable="self.input.default_start", value_expression="flow.input.event_time.timeDefaultStart"))
    
    data_map_time_range_end = DataMap()
    data_map_time_range_end.add(Assignment(target_variable="self.input.default_end", value_expression="flow.input.event_time.timeDefaultEnd"))
    
    data_map_min_time = DataMap()
    data_map_min_time.add(Assignment(target_variable="self.input.min_time", value_expression="flow.input.event_time.timeStart"))
    
    data_map_max_time = DataMap()
    data_map_max_time.add(Assignment(target_variable="self.input.max_time", value_expression="flow.input.event_time.timeEnd"))
    
    user_node_with_form.datetime_range_input_field(
        name="Working Shift",
        label="Working Hours",
        required=True,
        start_date_label="Start Time",
        end_date_label="End Time",
        default_start=data_map_time_range_start,
        default_end=data_map_time_range_end,
        min_time=data_map_min_time,
        max_time=data_map_max_time
    )
    
    # Create a single submit node
    submit_node = user_flow.script(
        name="process_submit",
        script='print("Processing submission with all date/time fields...")'
    )

    # Connect nodes using the edge API
    user_flow.edge(START, user_node_with_form)
    
    # Connect default "Submit" button
    user_flow.edge(user_node_with_form, submit_node, button_label="Submit")
    user_flow.edge(submit_node, END)
    
    # Connect "Cancel" button to end the flow
    user_flow.edge(user_node_with_form, END, button_label="Cancel")

    # Script to initialize date, time, and datetime data
    init_script = """
# Date fields
flow.input.event_date.dateStart = "2023-01-01"
flow.input.event_date.dateEnd = "2023-12-31"
flow.input.event_date.dateEvent = "2023-06-15"
flow.input.event_date.dateSimple = "2023-07-01"

# Time fields
flow.input.event_time.timeStart = "09:00"
flow.input.event_time.timeEnd = "17:00"
flow.input.event_time.timeDefaultStart = "10:00"
flow.input.event_time.timeDefaultEnd = "16:00"
flow.input.event_time.timeSimple = "12:00"

# DateTime fields
flow.input.event_datetime.dateTimeStart = "2023-01-01T09:00:00"
flow.input.event_datetime.dateTimeEnd = "2023-12-31T17:00:00"
flow.input.event_datetime.dateTimeEvent = "2023-06-15T14:00:00"
flow.input.event_datetime.dateTimeSimple = "2023-07-01T12:00:00"
"""
    init_data = aflow.script(name="init_data", script=init_script)
    
    # add the user flow to the flow sequence to create the flow edges
    aflow.sequence(START, init_data, user_flow, END)
  
    return aflow

# Made with Bob
