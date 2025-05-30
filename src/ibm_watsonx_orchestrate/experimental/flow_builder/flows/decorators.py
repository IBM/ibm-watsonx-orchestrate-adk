"""
A set of decorators to help define different Flow constructs.
"""

import asyncio
from functools import wraps
import logging
import inspect
from typing import Callable, Optional, Sequence
from pydantic import BaseModel
from ..types import extract_node_spec, UserNodeSpec, FlowSpec

from .flow import FlowFactory, Flow

logger = logging.getLogger(__name__)


class FlowWrapper:
    def __init__(self, func, a_model):
        self.func = func
        self.a_model = a_model
        wraps(func)(self)  # Preserve metadata

    def __call__(self, *args, **kwargs):
        result = self.func(self.a_model)
        if not isinstance(result, Flow):
            raise ValueError("Return value must be of type Flow")
        return result
    
def user(*args, name: str|None=None, description: str|None=None, owners: Sequence[str]|None = None, message: str | None = None):
    """Decorator to mark a function as a user node specification."""

    def decorator(func: Callable):
        node_spec = extract_node_spec(func, name, description)
        func.__user_spec__ = UserNodeSpec(type = "user",
                                          name = node_spec.name,
                                          display_name = node_spec.display_name,
                                          description = node_spec.description,
                                          input_schema = node_spec.input_schema,
                                          output_schema = node_spec.output_schema,
                                          output_schema_object = node_spec.output_schema_object,
                                          text=message,
                                          owners=owners)

        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.error(f"User node {name} is not supported yet.")            
            r = func(*args, **kwargs)
            return r

        return wrapper

    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    else:
        return decorator


def flow_spec(*args,
              name: Optional[str]=None,
              description: str|None=None,
              initiators: Sequence[str] = ()):
    """Decorator to mark a function as a flow specification."""

    def decorator(func: Callable):
        node_spec = extract_node_spec(func, name, description)
        a_spec = FlowSpec(type = "flow",
                             name = node_spec.name,
                             display_name = node_spec.display_name,
                             description = node_spec.description,
                             input_schema = node_spec.input_schema,
                             output_schema = node_spec.output_schema,
                             output_schema_object = node_spec.output_schema_object,
                             initiators = initiators)

        # we should also check a flow is async
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Flow must be asynchronous.")

        logger.info("Generated flow spec: %s", a_spec)
        func.__flow_spec__ = a_spec

        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info("Creating flow spec: %s", name)
            r = func(*args, **kwargs)
            logger.info("Flow spec %s returned: %s", name, r)
            return r

        return wrapper

    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    else:
        return decorator
    
def flow(*args, 
         name: Optional[str]=None, 
         display_name: Optional[str]=None,
         description: str|None=None,
         input_schema: type[BaseModel] | None = None,
         output_schema: type[BaseModel] | None = None,
         initiators: Sequence[str] = ()):
    """Decorator to mark a function as a flow model builder."""

    def decorator(func: Callable):
        """
        Decorator that takes a function as an argument and returns a wrapper function.
        The wrapper function takes a single argument of type Flow and calls the original function with the created flow as an argument.
        """

        sig = inspect.signature(func)
        if len(sig.parameters) != 1:
            raise ValueError("Only one argument is allowed")
        param = list(sig.parameters.values())[0]
        if param.annotation != Flow:
            raise ValueError("Argument must be of type Flow")
        if sig.return_annotation != Flow:
            raise ValueError("Return value must be of type Flow")
        
        node_spec = extract_node_spec(func, name, description)
        a_model = FlowFactory.create_flow(
                             name = node_spec.name,
                             display_name = display_name,
                             description = node_spec.description,
                             input_schema = input_schema,
                             output_schema = output_schema,
                             initiators = initiators)

        # logger.info("Creating flow model: %s", a_model.spec.name)

        # @wraps(func)
        # def wrapper(*args, **kwargs):
        #     result = func(a_model)
        #     if not isinstance(result, Flow):
        #         raise ValueError("Return value must be of type Flow")
        #     return result

        return FlowWrapper(func, a_model)

    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    else:
        return decorator
