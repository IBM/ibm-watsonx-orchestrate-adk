import json
from typing import Any, List, cast, Type
import uuid

import yaml
from pydantic import BaseModel, Field, SerializeAsAny, create_model
from ibm_watsonx_orchestrate.agent_builder.tools.types import JsonSchemaObject, ToolRequestBody, ToolResponseBody
from ibm_watsonx_orchestrate.flow_builder.types import UserForm
from ibm_watsonx_orchestrate.utils.file_manager import safe_open

from .types import DocExtConfigField, EndNodeSpec, NodeSpec, AgentNodeSpec, PromptNodeSpec, SchemaRef, ScriptNodeSpec, TimerNodeSpec, StartNodeSpec, ToolNodeSpec, UserField, UserField, UserFieldKind, UserFieldOption, UserForm, UserFormButton, UserNodeSpec, DocProcSpec, \
                    DocExtSpec, DocExtConfig, DocClassifierSpec, DecisionsNodeSpec, DocClassifierConfig

from .data_map import DataMap, DataMapSpec, Assignment

class Node(BaseModel):
    spec: SerializeAsAny[NodeSpec]
    input_map: DataMapSpec | None = None

    def __call__(self, **kwargs):
        pass

    def dump_spec(self, file: str) -> None:
        dumped = self.spec.model_dump(mode='json',
                                      exclude_unset=True, exclude_none=True, by_alias=True)
        with safe_open(file, 'w', encoding="utf-8") as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                yaml.dump(dumped, f, allow_unicode=True)
            elif file.endswith('.json'):
                json.dump(dumped, f, indent=2)
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

    def dumps_spec(self) -> str:
        dumped = self.spec.model_dump(mode='json',
                                      exclude_unset=True, exclude_none=True, by_alias=True)
        return json.dumps(dumped, indent=2)

    def __repr__(self):
        return f"Node(name='{self.spec.name}', description='{self.spec.description}')"

    def to_json(self) -> dict[str, Any]:
        model_spec = {}
        model_spec["spec"] = self.spec.to_json()
        if self.input_map is not None and self.input_map.spec:
            model_spec['input_map'] = {
                "spec": self.input_map.spec.to_json()
            }

        return model_spec
    
    def map_node_input_with_variable(self, target_input_variable: str, variable: str, default_value: str = None) -> None:
        if self.input_map and self.input_map.spec:
            maps = self.input_map.spec.maps or []
        else:
            maps = []
        
        curr_map_metadata = {
            "assignmentType": "variable"
        }

        target_variable = "self.input." + target_input_variable
        value_expression = "flow." + variable

        if default_value:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, default_value=default_value, metadata=curr_map_metadata))
        else:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, metadata=curr_map_metadata))

        node_input_map_spec = DataMap(maps=maps)
        if self.input_map and self.input_map.spec:
            self.input_map.spec = node_input_map_spec
        else:
            self.input_map = DataMapSpec(spec = node_input_map_spec)

    def map_input(self, input_variable: str, expression: str, default_value: str | None = None) -> None:
        if self.input_map and self.input_map.spec:
            maps = self.input_map.spec.maps or []
        else:
            maps = []
        
        curr_map_metadata = {
            "assignmentType": "pyExpression"
        }

        target_variable = "self.input." + input_variable
        value_expression = expression

        if default_value:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, default_value=default_value, metadata=curr_map_metadata))
        else:
            maps.append(Assignment(target_variable=target_variable, value_expression=value_expression, metadata=curr_map_metadata))

        node_input_map_spec = DataMap(maps=maps)
        if self.input_map and self.input_map.spec:
            self.input_map.spec = node_input_map_spec
        else:
            self.input_map = DataMapSpec(spec = node_input_map_spec)

    def map_node_input_with_none(self, target_input_variable: str) -> None:
        if self.input_map and self.input_map.spec:
            maps = self.input_map.spec.maps or []
        else:
            maps = []
        

        target_variable = "self.input." + target_input_variable

        maps.append(Assignment(target_variable=target_variable, value_expression=None))

        node_input_map_spec = DataMap(maps=maps)
        if self.input_map and self.input_map.spec:
            self.input_map.spec = node_input_map_spec
        else:
            self.input_map = DataMapSpec(spec = node_input_map_spec)

class StartNode(Node):
    def __repr__(self):
        return f"StartNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> StartNodeSpec:
        return cast(StartNodeSpec, self.spec)

class EndNode(Node):
    def __repr__(self):
        return f"EndNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> EndNodeSpec:
        return cast(EndNodeSpec, self.spec)
    
class ToolNode(Node):
    def __repr__(self):
        return f"ToolNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> ToolNodeSpec:
        return cast(ToolNodeSpec, self.spec)
    

class ScriptNode(Node):
    def __repr__(self):
        return f"ScriptNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> ScriptNodeSpec:
        return cast(ScriptNodeSpec, self.spec)
    
    def updateScript(self, script: str):
        '''Update the script of a script node'''
        self.spec.fn = script

class UserNode(Node):
    def __repr__(self):
        return f"UserNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> UserNodeSpec:
        return cast(UserNodeSpec, self.spec)

    def field(self,
              name: str,
              kind: UserFieldKind = UserFieldKind.Text,
              display_name: str | None = None,
              text: str | None = None,
              direction: str | None = None,
              input_map: DataMap | DataMapSpec| None = None,
              input_schema: ToolRequestBody | SchemaRef | None = None,
              output_schema: ToolResponseBody | SchemaRef | None = None) -> UserField:
        return self.get_spec().field(name=name,
                                     kind=kind,
                                     display_name=display_name,
                                     text=text,
                                     direction=direction,
                                     input_map=input_map,
                                     input_schema=input_schema,
                                     output_schema=output_schema)

    def form(self,
            name: str,
            display_name: str | None = None,
            instructions: str | None = None,
            submit_button_label: str | None = "Submit",
            cancel_button_label: str | None = None) -> UserForm :
        """
        Creates or retrieves a form in the user node and configures its buttons.

        Args:
            name: The internal name of the form.
            display_name: Optional display name for the form.
            instructions: Optional instructions text for the form.
            submit_button_label: Label for the submit button. Defaults to "Submit".
            cancel_button_label: Optional label for the cancel button. If None, the cancel button is hidden.

        Returns:
            UserForm: The created or retrieved form object.
        """
        user_form: UserForm = self.get_spec().get_or_create_form(name=name,
                                display_name=display_name,
                                instructions=instructions
                                )
        
        if user_form:
            user_form.buttons[0].display_name = submit_button_label

            if (cancel_button_label) :
                user_form.buttons[1].display_name = cancel_button_label
            else: 
                user_form.buttons[1].visible = False

        return user_form

    def add_field_to_form(self, name: str, field: UserField) -> None:
        user_form = self.get_spec().form
        if user_form:
            user_form.add_or_replace_field(name, field)
        else:
            raise ValueError("Form not found")

    def text_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            single_line: bool = True,
            placeholder_text: str| None = None,
            help_text: str | None = None,
            default: Any| None=None,
    ) -> UserField:
        """
        Creates a text input field in the form.
        
        The field can be configured as a single-line input or a multi-line text area.

        Args:
            name: The internal name of the field.
            label: Optional display label for the field.
            required: Whether the field is required. Defaults to False.
            single_line: Whether the field should be a single line input. If False, creates a multi-line text area. Defaults to True.
            placeholder_text: Optional placeholder text for the field.
            help_text: Optional help text for the field.
            default: Optional default value for the field, passed as DataMap.

        Returns:
            UserField: The created text input field.
            
        Raises:
            ValueError: If the form has not been created. Call form() method first.
        """
        if self.get_spec().form is None:
            raise ValueError("Form has not been created. Please call the form() method before adding fields.")
        
        return self.get_spec().form.text_input_field(
            name=name,
            label=label,
            required=required,
            single_line=single_line,
            placeholder_text=placeholder_text,
            help_text=help_text,
            input_map=default,
    )
    def boolean_input_field(
            self,
            name: str,
            label: str | None = None,
            single_checkbox: bool = True,
            default: Any| None=None,
            true_label: str = "True",
            false_label: str = "False"
        ) -> UserField:
        """
        Creates a boolean input field in the form.
        
        The field can be rendered as a checkbox or radio buttons.

        Args:
            name: The internal name of the field.
            label: Optional display label for the field.
            single_checkbox: Whether to display as a single checkbox. If False, displays as radio buttons. Defaults to True.
            default: Optional default value for the field, passed as input_map to the underlying implementation.
            true_label: Label for the true option. Defaults to "True".
            false_label: Label for the false option. Defaults to "False".

        Returns:
            UserField: The created boolean input field.
            
        Raises:
            ValueError: If the form has not been created. Call form() method first.
        """
        if self.get_spec().form is None:
            raise ValueError("Form has not been created. Please call the form() method before adding fields.")
        
        return self.get_spec().form.boolean_input_field(
            name=name,
            label=label,
            single_checkbox=single_checkbox,
            true_label=true_label,
            false_label=false_label,
            input_map=default
        )
    def date_range_input_field(self,
                                name: str,
                                label: str | None = None,
                                required: bool = False,
                                start_date_label: str | None = None,
                                end_date_label: str | None = None,
                                default_start: Any| None = None,
                                default_end: Any| None = None
        ) -> UserField:
            """
            Creates a date range input field in the form with start and end date pickers.

            Args:
                name: The internal name of the field.
                label: Optional display label for the field.
                required: Whether the field is required. Defaults to False.
                start_date_label: Optional label for the start date field.
                end_date_label: Optional label for the end date field.
                default_start: Optional default value for the start date, passed as DataMap.
                default_end: Optional default value for the end date, passed as DataMap.

            Returns:
                UserField: The created date range input field.
                
            Raises:
                ValueError: If the form has not been created. Call form() method first.
            """
            if self.get_spec().form is None:
                raise ValueError("Form has not been created. Please call the form() method before adding fields.")
            
            return self.get_spec().form.date_range_input_field(
                name = name,
                label = label,
                required = required,
                start_date_label = start_date_label,
                end_date_label = end_date_label,
                default_start = default_start,
                default_end = default_end
            )
    def date_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            default: Any| None=None,
    ) -> UserField:
         """
         Creates a date input field in the form.

         Args:
             name: The internal name of the field.
             label: Optional display label for the field.
             required: Whether the field is required. Defaults to False.
             default: Optional default value for the field, passed as DataMap.

         Returns:
             UserField: The created date input field.
             
         Raises:
             ValueError: If the form has not been created. Call form() method first.
         """
         if self.get_spec().form is None:
             raise ValueError("Form has not been created. Please call the form() method before adding fields.")
         
         return self.get_spec().form.date_input_field(
                name = name,
                label = label,
                required = required,
                initial_value = default,
            )
    def number_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            is_integer: bool = True,
            help_text: str | None = None,
            default: Any| None=None,
            minimum: Any | None=None,
            maximum: Any | None=None

    ) -> UserField:
         """
         Creates a number input field in the form.

         Args:
             name: The internal name of the field.
             label: Optional display label for the field.
             required: Whether the field is required. Defaults to False.
             is_integer: Whether the field should accept only integers. If False, accepts decimal numbers. Defaults to True.
             help_text: Optional help text for the field.
             default: Optional default value for the field, passed as DataMap.
             minimum: Optional minimum allowed value, passed as DataMap.
             maximum: Optional maximum allowed value, passed as DataMap.

         Returns:
             UserField: The created number input field.
             
         Raises:
             ValueError: If the form has not been created. Call form() method first.
         """
         if self.get_spec().form is None:
             raise ValueError("Form has not been created. Please call the form() method before adding fields.")
         
         return self.get_spec().form.number_input_field(
                name = name,
                label = label,
                required = required,
                is_integer = is_integer,
                help_text= help_text,
                initial_value=default,
                minimum_value= minimum,
                maximum_value= maximum
            )
    def file_upload_field(
            self,
            name: str,
            label: str | None = None,
            instructions: str | None = None,
            required: bool = False,
            allow_multiple_files: bool = False,
            file_max_size: int=10,
            supported_file_types : List[str] | None = None,

    ) -> UserField:
            """
            Creates a file upload field in the form.

            Args:
                name: The internal name of the field.
                label: Optional display label for the field.
                instructions: Optional instructions for the file upload.
                required: Whether the field is required. Defaults to False.
                allow_multiple_files: Whether multiple files can be uploaded. Defaults to False.
                file_max_size: Maximum file size in MB. Defaults to 10.
                supported_file_types: Optional list of supported file extensions (e.g., ["pdf", "docx"]).

            Returns:
                UserField: The created file upload field.
                
            Raises:
                ValueError: If the form has not been created. Call form() method first.
            """
            if self.get_spec().form is None:
                raise ValueError("Form has not been created. Please call the form() method before adding fields.")
            
            return self.get_spec().form.file_upload_field(
                name = name,
                label = label,
                instructions=instructions,
                required = required,
                allow_multiple_files=allow_multiple_files,
                file_max_size=file_max_size,
                supported_file_types = supported_file_types,
            )
    def message_output_field(
            self,
            name: str,
            label: str | None = None,
            message: str | None = None
        ) -> UserField:
            """
            Creates a message output field in the form to display static text.

            Args:
                name: The internal name of the field.
                label: Optional display label for the field.
                message: The message text to display.

            Returns:
                UserField: The created message output field.
                
            Raises:
                ValueError: If the form has not been created. Call form() method first.
            """
            if self.get_spec().form is None:
                raise ValueError("Form has not been created. Please call the form() method before adding fields.")
            
            return self.get_spec().form.message_output_field(
                    name = name,
                    label = label,
                    message = message
                )
    def field_output_field(
            self,
            name: str,
            label: str | None = None,
            value: Any | None = None
        ) -> UserField:
            """
            Creates a field output field in the form to display dynamic values.

            Args:
                name: The internal name of the field.
                label: Optional display label for the field.
                value: The value to display in the field, passed as DataMap.

            Returns:
                UserField: The created field output field.
                
            Raises:
                ValueError: If the form has not been created. Call form() method first.
            """
            if self.get_spec().form is None:
                raise ValueError("Form has not been created. Please call the form() method before adding fields.")
            
            return self.get_spec().form.field_output_field(
                        name = name,
                        label = label,
                        source = value
                )
    def list_output_field(
            self,
            name: str,
            label: str | None = None,
            choices: Any | None = None,
            columns: dict[str, str] | None = None
    ) -> UserField:
         """
         Creates a list output field in the form to display tabular data.

         Args:
             name: The internal name of the field.
             label: Optional display label for the field.
             choices: The list of items to display, passed in a DataMap.
             columns: Optional mapping of source property names to table column labels. When present, only those columns will be displayed.

         Returns:
             UserField: The created list output field.
             
         Raises:
             ValueError: If the form has not been created. Call form() method first.
         """
         if self.get_spec().form is None:
             raise ValueError("Form has not been created. Please call the form() method before adding fields.")
         
         return self.get_spec().form.list_output_field(
                        name = name,
                        label = label,
                        source = choices,
                        columns=columns
                )
    
    def list_input_field(
            self,
            name: str,
            label: str | None = None,
            isRowAddable: bool = True,
            isRowDeletable: bool= True,
            default: Any | None = None,
            columns: dict[str, str] | None = None
    ) -> UserField:
         """
         Creates a list input field in the form to display tabular data.

         Args:
             name: The internal name of the field.
             label: Optional display label for the field.
             default: The list of items to display, passed in a DataMap.
             columns: Optional mapping of source property names to table column labels. When present, only those columns will be displayed.

         Returns:
             UserField: The created list input field.
             
         Raises:
             ValueError: If the form has not been created. Call form() method first.
         """
         if self.get_spec().form is None:
             raise ValueError("Form has not been created. Please call the form() method before adding fields.")
         
         return self.get_spec().form.list_input_field(
                        name = name,
                        label = label,
                        isRowAddable = isRowAddable,
                        isRowDeletable = isRowDeletable,
                        default = default,
                        columns=columns
                )
    def file_download_field(
            self,
            name: str,
            label: str | None = None,
            value: Any | None = None,
    ) -> UserField:
         """
         Creates a file download field in the form.

         Args:
             name: The internal name of the field.
             label: Optional display label for the field.
             value: The file to be downloaded, passed as DataMap.

         Returns:
             UserField: The created file download field.
             
         Raises:
             ValueError: If the form has not been created. Call form() method first.
         """
         if self.get_spec().form is None:
             raise ValueError("Form has not been created. Please call the form() method before adding fields.")
         if value is None : 
             raise ValueError("A file to donwload is required.") 
         
         return self.get_spec().form.file_download_field(
                        name = name,
                        label = label,
                        source_file = value
                )
    def single_choice_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            choices: Any| None=None,
            show_as_dropdown: bool = True,
            dropdown_item_column: str | None = None,
            placeholder_text: str | None = None,
            default: Any | None = None,
            columns: dict[str, str]| None = None,

    ) -> UserField:
        """
        Creates a single-choice input field in the form (dropdown or radio buttons).
        
        This method delegates to the choice_input_field method with isMultiSelect=False (default).

        Args:
            name: The internal name of the field.
            label: Optional display label for the field.
            required: Whether the field is required. Defaults to False.
            choices: The list of available choices, passed as DataMap.
            show_as_dropdown: Whether to display as a dropdown. If False, displays as radio buttons. Defaults to True.
            dropdown_item_column: Optional column name to use for display text in dropdown.
            placeholder_text: Optional placeholder text for the dropdown.
            default: Optional default selected value, passed as DataMap.
            columns: Optional mapping of source property names to display labels for complex choice objects.

        Returns:
            UserField: The created single-choice input field.
            
        Raises:
            ValueError: If the form has not been created. Call form() method first.
        """
        if self.get_spec().form is None:
            raise ValueError("Form has not been created. Please call the form() method before adding fields.")
        
        return self.get_spec().form.choice_input_field(
                        name = name,
                        label = label,
                        required = required,
                        source = choices,
                        show_as_dropdown = show_as_dropdown,
                        dropdown_item_column = dropdown_item_column,
                        placeholder_text = placeholder_text,
                        initial_value = default,
                        columns = columns
                )
    def multi_choice_input_field(
            self,
            name: str,
            label: str | None = None,
            required: bool = False,
            choices: Any| None=None,
            show_as_dropdown: bool = True,
            dropdown_item_column: str | None = None,
            placeholder_text: str | None = None,
            default: Any | None = None,
            columns: dict[str, str]| None = None

    ) -> UserField:
        """
        Creates a multi-choice input field in the form (multi-select dropdown or checkboxes).
        
        This method delegates to the choice_input_field method with isMultiSelect=True.

        Args:
            name: The internal name of the field.
            label: Optional display label for the field.
            required: Whether the field is required. Defaults to False.
            choices: The list of available choices, passed as DataMap.
            show_as_dropdown: Whether to display as a dropdown. If False, displays as checkboxes. Defaults to True.
            dropdown_item_column: Optional column name to use for display text in dropdown.
            placeholder_text: Optional placeholder text for the dropdown.
            default: Optional default selected values, passed as DataMap.
            columns: Optional mapping of source property names to display labels for complex choice objects.

        Returns:
            UserField: The created multi-choice input field.
            
        Raises:
            ValueError: If the form has not been created. Call form() method first.
        """
        if self.get_spec().form is None:
            raise ValueError("Form has not been created. Please call the form() method before adding fields.")
        
        return self.get_spec().form.choice_input_field(
                        name = name,
                        label = label,
                        required= required,
                        source = choices,
                        show_as_dropdown = show_as_dropdown,
                        dropdown_item_column = dropdown_item_column,
                        placeholder_text = placeholder_text,
                        initial_value = default,
                        columns = columns,
                        isMultiSelect=True
                ) 

class AgentNode(Node):
    def __repr__(self):
        return f"AgentNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> AgentNodeSpec:
        return cast(AgentNodeSpec, self.spec)

class PromptNode(Node):
    def __repr__(self):
        return f"PromptNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> PromptNodeSpec:
        return cast(PromptNodeSpec, self.spec)
    
class DocProcNode(Node):
    def __repr__(self):
        return f"DocProcNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DocProcSpec:
        return cast(DocProcSpec, self.spec)
    
class DocClassifierNode(Node):
    def __repr__(self):
        return f"DocClassifierNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DocClassifierSpec:
        return cast(DocClassifierSpec, self.spec)

    @staticmethod
    def generate_config(llm: str, input_classes: type[BaseModel], min_confidence: float) -> DocClassifierConfig:
        return DocClassifierConfig(llm=llm, classes=input_classes.__dict__.values(), min_confidence=min_confidence)
    
class TimerNode(Node):
    def __repr__(self):
        return f"TimerNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> TimerNodeSpec:
        return cast(TimerNodeSpec, self.spec)
    
class DocExtNode(Node):
    def __repr__(self):
        return f"DocExtNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DocExtSpec:
        return cast(DocExtSpec, self.spec)
    
    @staticmethod
    def generate_config(llm: str, fields: type[BaseModel], field_extraction_method: str) -> DocExtConfig:
        return DocExtConfig(llm=llm, fields=fields.__dict__.values(), field_extraction_method=field_extraction_method)
    
    @staticmethod
    def _create_table_field_definition(name: str, value: dict) -> tuple:
        """Create field definition for table-type fields.
        
        Args:
            name: The field name for the table.
            value: Dictionary containing 'name' and 'fields' keys.
            
        Returns:
            A tuple of (field_type, Field) for the table field definition.
        """
        table_row_fields = {}
        for table_field in value["fields"]:
            row_field_kwargs = {
                "title": table_field['name'],
                "description": f"Extracted value for {table_field['name']}"
            }
            table_row_fields[table_field['field_name']] = (str, Field(**row_field_kwargs))
        
        TableRowModel = create_model(f"{name}_row", **table_row_fields)
        
        field_kwargs = {
            "title": value['name'],
            "description": f"Extracted value for {value['name']}",
        }
        return (list[TableRowModel], Field(**field_kwargs))

    @staticmethod
    def _create_regular_field_definition(value: dict) -> tuple:
        """Create field definition for regular (non-table) fields.
        
        Args:
            value: Dictionary containing 'type' and 'name' keys.
            
        Returns:
            A tuple of (field_type, Field) for the regular field definition.
        """
        json_type = "string" if value["type"] == "date" else value["type"]
        
        field_kwargs = {
            "title": value['name'],
            "description": f"Extracted value for {value['name']}",
            "json_schema_extra": {"type": json_type}
        }

        if value["type"] == "date":
            field_kwargs["json_schema_extra"]["format"] = "date"
        
        return (str, Field(**field_kwargs))

    @staticmethod
    def generate_docext_field_value_model(fields: BaseModel) -> type[BaseModel]:
        """Generate a Pydantic model for document extraction field values.
        
        Creates a dynamic model with fields based on the input schema, handling
        both regular fields and table-type fields (which become lists of nested models).
        
        Args:
            fields: A Pydantic BaseModel instance containing field definitions with 'type',
                    'name', and optionally 'fields' (for table types).
        
        Returns:
            A dynamically created Pydantic model class named 'DocExtFieldValue'.
        """
        field_definitions = {}

        for name, value in fields.model_dump().items():
            if value["type"] == "table" and "fields" in value:
                field_definitions[name] = DocExtNode._create_table_field_definition(name, value)
            else:
                field_definitions[name] = DocExtNode._create_regular_field_definition(value)

        return create_model("DocExtFieldValue", **field_definitions)
    
class DecisionsNode(Node):
    def __repr__(self):
        return f"DecisionsNode(name='{self.spec.name}', description='{self.spec.description}')"

    def get_spec(self) -> DecisionsNodeSpec:
        return cast(DecisionsNodeSpec, self.spec)
    
class NodeInstance(BaseModel):
    node: Node
    id: str # unique id of this task instance
    flow: Any # the flow this task belongs to

    def __init__(self, **kwargs): # type: ignore
        super().__init__(**kwargs)
        self.id = uuid.uuid4().hex
