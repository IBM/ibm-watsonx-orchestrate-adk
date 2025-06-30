
import json
import logging

from ibm_watsonx_orchestrate.utils.utils import yaml_safe_load
from .types import FlowToolBinding, ToolBinding, ToolSpec
from .base_tool import BaseTool
from .types import ToolPermission

import json

logger = logging.getLogger(__name__)


class FlowTool(BaseTool):
    def __init__(self, spec: ToolSpec):
        BaseTool.__init__(self, spec=spec)

    async def __call__(self, **kwargs):
        raise RuntimeError('Flow Tools are only available when deployed onto watson orchestrate or the watson '
                           'orchestrate-light runtime')

    @staticmethod
    def from_spec(file: str) -> 'FlowTool':
        with open(file, 'r') as f:
            if file.endswith('.yaml') or file.endswith('.yml'):
                spec = ToolSpec.model_validate(yaml_safe_load(f))
            elif file.endswith('.json'):
                spec = ToolSpec.model_validate(json.load(f))
            else:
                raise ValueError('file must end in .json, .yaml, or .yml')

        if spec.binding.openapi is None or spec.binding.openapi is None:
            raise ValueError('failed to load python tool as the tool had no openapi binding')

        return FlowTool(spec=spec)

    def __repr__(self):
        return f"FlowTool(model={self.__tool_spec__.binding.flow.model}, name='{self.__tool_spec__.name}', description='{self.__tool_spec__.description}')"

    def __str__(self):
        return self.__repr__()

    @property
    def __doc__(self):
        return self.__tool_spec__.description


def create_flow_json_tool(
        flow_model: dict,
        name: str = None,
        description: str = None,
        permission: ToolPermission = None,
        ) -> FlowTool:
    """
    Creates a flow tool from a Flow JSON model

    Here we create the basic tool spec.  The remaining properties of the tool spec
    are set by the server when the tool is registered.  The server will publish the model to the
    flow engine and generate the rest of the tool spec based on it's openAPI specification.
    """

    spec_name = name
    spec_permission = permission
    if spec_name is None:
        raise ValueError(
            f"No name provided for tool.")

    spec_description = description
    if spec_description is None:
        raise ValueError(
            f"No description provided for tool.")

    spec = ToolSpec(
        name=spec_name,
        description=spec_description,
        permission=spec_permission
    )

    spec.binding = ToolBinding(flow=FlowToolBinding(flow_id=name, model=flow_model))

    return FlowTool(spec=spec)

