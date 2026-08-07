import re
import sys
import inspect
import logging
import requests
import importlib
import textwrap
import typing
import warnings
from copy import deepcopy
from os import path
from pathlib import Path
from types import ModuleType
from typing import Any, Annotated, Optional, List, Tuple, TypeVar, cast, get_args, get_origin, get_type_hints

import typing_extensions
import typer
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PydanticDeprecationWarning,
)
from pydantic import create_model as _create_model_base
from pydantic.fields import FieldInfo, FieldInfo as FieldInfoV2
from pydantic.v1 import BaseModel as BaseModelV1
from pydantic.v1 import create_model as _create_model_v1
from pydantic import validate_arguments
from pydantic.v1 import validate_arguments as validate_arguments_v1

from ibm_watsonx_orchestrate import __version__
from ibm_watsonx_orchestrate.client.utils import is_local_dev
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest
from ibm_watsonx_orchestrate.utils.utils import sanitize_app_id
from ibm_watsonx_orchestrate.utils.file_manager import safe_open
from ibm_watsonx_orchestrate.cli.commands.tools.types import RegistryType
from ibm_watsonx_orchestrate.agent_builder.tools.base_tool import BaseTool
from ibm_watsonx_orchestrate.agent_builder.tools.types import PythonToolKind
from ibm_watsonx_orchestrate.client.connections import get_connections_client, get_connection_type
from ibm_watsonx_orchestrate.agent_builder.connections.types import ConnectionEnvironment, ConnectionConfiguration, ConnectionPreference
from ibm_watsonx_orchestrate.cli.config import Config, PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT, \
    DEFAULT_CONFIG_FILE_CONTENT, PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT

logger = logging.getLogger(__name__)

__supported_characters_pattern = re.compile(r"^(\w|_)+$")


def get_package_root(package_root):
    return None if package_root is None or package_root.strip() == "" else package_root.strip()

def __get_package(file_path: Path, resolved_package_root: Optional[str]) -> Tuple[str, str]:
    file_path_str = str(file_path)
    if resolved_package_root:
        resolved_package_root = str(Path(resolved_package_root).absolute())
        package_path = str(Path(resolved_package_root).parent.absolute())
        package_folder = str(Path(resolved_package_root).stem)
        sys.path.append(package_path)           # allows you to resolve non relative imports relative to the root of the module
        sys.path.append(resolved_package_root)  # allows you to resolve relative imports in combination with import_module(..., package=...)
        package = file_path_str.replace(resolved_package_root, '').replace('.py', '').replace('/', '.').replace('\\', '.')
        if not path.isdir(resolved_package_root):
            raise typer.BadParameter(f"The provided package root is not a directory.")

        elif not file_path_str.startswith(str(Path(resolved_package_root))):
            print(file_path_str)
            print(str(Path(resolved_package_root)))
            raise typer.BadParameter(f"The provided tool file path does not belong to the provided package root.")

        temp_path = Path(file_path_str[len(str(Path(resolved_package_root))) + 1:])
        if any([__supported_characters_pattern.match(x) is None for x in temp_path.parts[:-1]]):
            raise typer.BadParameter(f"Path to tool file contains unsupported characters. Only alphanumeric characters and underscores are allowed. Path: \"{temp_path}\"")
    else:
        package_folder = file_path.parent
        package = file_path.stem
        sys.path.append(str(package_folder))
    
    return package, package_folder

def get_resolved_py_tool_reqs_file (tool_file, requirements_file, package_root):
    resolved_requirements_file = requirements_file if requirements_file is not None else None
    # Is there a requirements file at the same level as the tools file
    tool_sibling_reqs_file = Path(tool_file).absolute().parent.joinpath("requirements.txt")
    # Is there a requirements file at the package root
    package_root_reqs_file = Path(package_root).absolute().joinpath(
        "requirements.txt") if get_package_root(package_root) is not None else None

    if resolved_requirements_file is None:
        # first favor requirements which is sibling root. if not, fallback to the one at package root.
        if tool_sibling_reqs_file.exists():
            resolved_requirements_file = str(tool_sibling_reqs_file)

        elif package_root_reqs_file is not None and package_root_reqs_file.exists():
            resolved_requirements_file = str(package_root_reqs_file)

    return resolved_requirements_file

def get_requirement_lines (requirements_file, remove_trailing_newlines=True, exclude_ibm_watsonx_orchestrate=True):
    requirements = []

    if requirements_file is not None:
        with safe_open(requirements_file, 'r') as fp:
            requirements = fp.readlines()

    if remove_trailing_newlines is True:
        requirements = [x.strip() for x in requirements]

    if exclude_ibm_watsonx_orchestrate:
        # Remove mentions of main adk package (or clients/core sub package)
        # Allow ibm-watsonx-orchestrate-sdk
        requirements = [x for x in requirements if (not x.startswith("ibm-watsonx-orchestrate") or x.startswith("ibm-watsonx-orchestrate-sdk"))]
    requirements = list(dict.fromkeys(requirements))

    return requirements

def get_requirements(tool_file: str, requirements_file: Optional[str] = None, package_root: Optional[str] = None, log_requirements_path: bool = True, requirements_file_required: bool = True) -> List[str]:
    resolved_requirements_file = get_resolved_py_tool_reqs_file(tool_file=tool_file, requirements_file=requirements_file,
                                                                package_root=package_root)

    if resolved_requirements_file is not None and log_requirements_path:
        logger.info(f"Using requirement file: \"{resolved_requirements_file}\"")

    if resolved_requirements_file is not None:
        try:
            requirements = get_requirement_lines(resolved_requirements_file)
        
        except FileNotFoundError as e:
            if requirements_file_required:
                raise typer.BadParameter(f"Failed to read file {resolved_requirements_file} {e}")
            else:
                pass
        except Exception as e:
            raise typer.BadParameter(f"Failed to read file {resolved_requirements_file} {e}")
    
        return requirements
    return []

def get_connection_environments() -> List[ConnectionEnvironment]:
    if is_local_dev():
        return [ConnectionEnvironment.DRAFT]
    else:
        return [env.value for env in ConnectionEnvironment]

def __get_connection_configs(app_id: str) -> List[ConnectionConfiguration]:
    client = get_connections_client()
    connection_configs = []
    for env in ConnectionEnvironment:
        try:
            config = client.get_config(app_id=app_id,env=env)
            if not config:
                continue
            else:
                connection_configs.append( config.as_config() )
        except:
            logger.error(f"Unable to get {env.value.lower()} configs for connection '{app_id}'")

    return connection_configs

def check_plugin_connection(app_id: List[str]):
    app_ids = []
    connections_client = get_connections_client()
    connections = connections_client.get_draft_by_app_ids(app_id)

    for conn in connections:
        if isinstance(conn, tuple) and len(conn) == 2:
            key, value = conn
            if key == "app_id":
                app_ids.append(value)

    for app_id_check in app_ids:
        conn_configs = __get_connection_configs(app_id_check)
        for conn_config in conn_configs:
            if conn_config.preference == ConnectionPreference.MEMBER:
                logger.error(f"{conn_config.app_id} connection has type of Member. Connection types for Plugin Tools must be Team and not Member")
                sys.exit(1)

def __get_connection_id(app_id: str) -> str:
    connections_client = get_connections_client()
    connection_id = None
    if app_id is not None:
        connection = connections_client.get(app_id=app_id)
        if  not connection:
            logger.error(f"No connection exists with the app-id '{app_id}'")
            exit(1)
        connection_id = connection.connection_id
    return connection_id

def __parse_app_ids(app_ids: List[str]) -> dict[str,str]:
    app_id_dict = {}
    for app_id in app_ids:
        # Split on = but not on \=
        split_pattern = re.compile(r"(?<!\\)=")
        split_id = re.split(split_pattern, app_id)
        split_id = [x.replace("\\=", "=") for x in split_id]
        if len(split_id) == 2:
            runtime_id, local_id = split_id
        elif len(split_id) == 1:
            runtime_id = split_id[0]
            local_id = split_id[0]
        else:
            raise typer.BadParameter(f"The provided --app-id '{app_id}' is not valid. This is likely caused by having mutliple equal signs, please use '\\=' to represent a literal '=' character")

        if not len(runtime_id.strip()) or not len(local_id.strip()):
            raise typer.BadParameter(f"The provided --app-id '{app_id}' is not valid. --app-id cannot be empty or whitespace")

        runtime_id = sanitize_app_id(runtime_id)
        app_id_dict[runtime_id] = __get_connection_id(local_id)

    return app_id_dict

def __validate_python_connections(tool: BaseTool):
    if not tool.expected_credentials:
        return

    connections_client = get_connections_client()
    connections = tool.__tool_spec__.binding.python.connections

    provided_connections = list(connections.keys()) if connections else []
    imported_connections_list = connections_client.list()
    imported_connections = {}
    for conn in imported_connections_list:
        conn_id = conn.connection_id
        conn_env = conn.environment
        if conn_id in imported_connections:
            imported_connections[conn_id][conn_env] = conn
        else:
            imported_connections[conn_id] = {conn_env: conn}

    validation_failed = False

    existing_sanatized_expected_tool_app_ids = set()

    for expected_cred in tool.expected_credentials:

        expected_tool_app_id = expected_cred.app_id
        if isinstance(expected_cred.type, List):
            expected_tool_conn_types = expected_cred.type
        else:
            expected_tool_conn_types = [expected_cred.type]

        sanatized_expected_tool_app_id = sanitize_app_id(expected_tool_app_id)
        if sanatized_expected_tool_app_id in existing_sanatized_expected_tool_app_ids:
            logger.error(f"Duplicate App ID found '{expected_tool_app_id}'. Multiple expected app ids in the tool '{tool.__tool_spec__.name}' collide after sanaitization to '{sanatized_expected_tool_app_id}'. Please rename the offending app id in your tool.")
            sys.exit(1)
        existing_sanatized_expected_tool_app_ids.add(sanatized_expected_tool_app_id)

        if sanatized_expected_tool_app_id not in provided_connections:
            logger.error(f"The tool '{tool.__tool_spec__.name}' requires an app-id '{expected_tool_app_id}'. Please use the `--app-id` flag to provide the required app-id")
            sys.exit(1)

        if not connections:
            continue
            
        connection_id = connections.get(sanatized_expected_tool_app_id)
        imported_connection = imported_connections.get(connection_id)

        if connection_id and not imported_connection:
            logger.error(f"The expected connection id '{connection_id}' does not match any known connection. This is likely caused by the connection being deleted. Please rec-reate the connection and re-import the tool")
            validation_failed = True
        
        environments = get_connection_environments()

        for conn_environment in environments:
            conn = imported_connection.get(conn_environment)
            conn_identifier = conn.app_id if conn is not None else connection_id
            if conn is None or conn.security_scheme is None:
                message = f"Connection '{conn_identifier}' is not configured in the '{conn_environment}' environment."
                if conn_environment == ConnectionEnvironment.DRAFT:
                    logger.error(message)
                    sys.exit(1)
                else:
                    logger.warning(message + " If you deploy this tool without setting the live configuration the tool will error during execution.")
                continue

            imported_connection_auth_type = get_connection_type(security_scheme=conn.security_scheme, auth_type=conn.auth_type)

            if conn and len(expected_tool_conn_types) and imported_connection_auth_type not in expected_tool_conn_types:
                logger.error(f"The app-id '{conn.app_id}' is of type '{imported_connection_auth_type.value}' in the '{conn_environment}' environment. The tool '{tool.__tool_spec__.name}' accepts connections of the following types '{', '.join(expected_tool_conn_types)}'. Use `orchestrate connections list` to view current connections and use `orchestrate connections add` to create the relevent connection")
                validation_failed = True

    if validation_failed:
        exit(1)

def __get_python_tools_from_file(
        module: ModuleType,
        package: str,
        file_name: str,
        package_root: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        connections: Optional[List[str]] = None
    ) -> List[BaseTool]:
    tools = []

    for _, obj in inspect.getmembers(module):
        if not isinstance(obj, BaseTool):
            continue
            

        # Plugin tool - if it was given an app-id
        if obj.kind in [PythonToolKind.AGENTPREINVOKE, PythonToolKind.AGENTPOSTINVOKE]:
            if connections and len(connections):
                check_plugin_connection(connections)
            if obj.kind == PythonToolKind.AGENTPREINVOKE:
                obj.__tool_spec__.binding.python.type = PythonToolKind.AGENTPREINVOKE
            elif obj.kind == PythonToolKind.AGENTPOSTINVOKE:
                obj.__tool_spec__.binding.python.type = PythonToolKind.AGENTPOSTINVOKE

        obj.__tool_spec__.binding.python.requirements = requirements

        if __supported_characters_pattern.match(obj.__tool_spec__.name) is None:
            raise typer.BadParameter(f"Tool name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Name: \"{obj.__tool_spec__.name}\"")

        elif package_root is None:
            fn = obj.__tool_spec__.binding.python.function.split(":")[-1]
            obj.__tool_spec__.binding.python.function = f"{file_name.replace('.py', '')}:{fn}"

        else:
            pkg = package[1:]
            fn = obj.__tool_spec__.binding.python.function.split(":")[-1]
            obj.__tool_spec__.binding.python.function = f"{pkg}:{fn}"

        if connections and len(connections):
            obj.__tool_spec__.binding.python.connections = __parse_app_ids(connections)

        __validate_python_connections(obj)
        tools.append(obj)
    
    return tools

def extract_python_tools(file: str, requirements_file: Optional[str] = None, app_ids: Optional[List[str]] = None, package_root: Optional[str] = None, log_requirements_path: bool = True, requirements_file_required: bool = True) -> List[BaseTool]:
    try:

        # standard file import
        file_path = Path(file).absolute()

        if file_path.is_dir():
            raise typer.BadParameter(f"Provided tool file path is not a file.")

        elif file_path.is_symlink():
            raise typer.BadParameter(f"Symbolic links are not supported for tool file path.")

        file_name = file_path.stem

        if __supported_characters_pattern.match(file_name) is None:
            raise typer.BadParameter(f"File name contains unsupported characters. Only alphanumeric characters and underscores are allowed. Filename: \"{file_name}\"")

        resolved_package_root = get_package_root(package_root)
        package, package_folder = __get_package(file_path, resolved_package_root)

        module = importlib.import_module(package, package=package_folder)

        # Clean up sys.path
        if resolved_package_root:
            del sys.path[-1]
        del sys.path[-1]


    except typer.BadParameter as ex:
        raise ex

    except Exception as e:
        raise typer.BadParameter(f"Failed to load python module from file {file}: {e}")

    requirements = get_requirements(tool_file=file, requirements_file=requirements_file,
                                                                package_root=resolved_package_root, log_requirements_path=log_requirements_path, requirements_file_required=requirements_file_required)

    tools = __get_python_tools_from_file(
        module=module,
        package=package,
        file_name=file_name,
        package_root=resolved_package_root,
        requirements=requirements,
        connections=app_ids
    )

    return tools

def __get_whl_in_registry(registry_url: str, version: str) -> str| None:
    orchestrate_links = requests.get(registry_url).text
    wheel_files = [x.group(1) for x in re.finditer( r'href="(.*\.whl).*"', orchestrate_links)]
    wheel_file = next(filter(lambda x: f"{version}-py3-none-any.whl" in x, wheel_files), None)
    return wheel_file

def get_formated_requirements_lines(requirement_file: Optional[str] = None) -> List[str]:
    version = __version__

    cfg = Config()
    registry_type = cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TYPE_OPT) or DEFAULT_CONFIG_FILE_CONTENT[PYTHON_REGISTRY_HEADER][PYTHON_REGISTRY_TYPE_OPT]
    skip_version_check = cfg.read(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT) or DEFAULT_CONFIG_FILE_CONTENT[PYTHON_REGISTRY_HEADER][PYTHON_REGISTRY_SKIP_VERSION_CHECK_OPT]

    requirements = []
    if requirement_file is not None:
        exclude_ibm_watsonx_orchestrate = not registry_type == RegistryType.SKIP
        requirements = get_requirement_lines(requirements_file=requirement_file, remove_trailing_newlines=False, exclude_ibm_watsonx_orchestrate=exclude_ibm_watsonx_orchestrate)

    # Ensure there is a newline at the end of the file
    if len(requirements) > 0 and not requirements[-1].endswith("\n"):
        requirements[-1] = requirements[-1]+"\n"

    if registry_type == RegistryType.LOCAL:
        logger.warning(f"Using a local registry which is for development purposes only")
        requirements.append(f"/packages/ibm_watsonx_orchestrate-0.6.0-py3-none-any.whl\n")
    elif registry_type == RegistryType.PYPI:
        if not skip_version_check:
            wheel_file = __get_whl_in_registry(registry_url='https://pypi.org/simple/ibm-watsonx-orchestrate', version=version)
            if not wheel_file:
                logger.error(f"Could not find ibm-watsonx-orchestrate@{version} on https://pypi.org/project/ibm-watsonx-orchestrate")
                exit(1)
        requirements.append(f"ibm-watsonx-orchestrate=={version}\n")
    elif registry_type == RegistryType.TESTPYPI:
        override_version = cfg.get(PYTHON_REGISTRY_HEADER, PYTHON_REGISTRY_TEST_PACKAGE_VERSION_OVERRIDE_OPT) or version
        wheel_file = __get_whl_in_registry(registry_url='https://test.pypi.org/simple/ibm-watsonx-orchestrate', version=override_version)
        if not wheel_file:
            logger.error(f"Could not find ibm-watsonx-orchestrate@{override_version} on https://test.pypi.org/project/ibm-watsonx-orchestrate")
            exit(1)
        requirements.append(f"ibm-watsonx-orchestrate @ {wheel_file}\n")
    elif registry_type == RegistryType.SKIP: # Skip automatically adding the ADK as a dependency
        if requirements:
            logger.warning("Skipping adding 'ibm-watsonx-orchestrate' to tool requirements. Please ensure the requirements.txt contains the correct package.")
        else:
            BadRequest("Cannot skip addition of 'ibm-watsonx-orchestrate' to tool requirements. Please provide a 'requirements.txt' file or use 'orchestrate env acticate <env_name> --registry pypi'")
    else:
        logger.error(f"Unrecognized registry type provided to orchestrate env activate local --registry <registry>")
        exit(1)

    requirements = list(dict.fromkeys(requirements))
    return requirements


def _retrieve_ref(path: str, schema: dict[str, Any]) -> list[Any] | dict[Any, Any]:
    components = path.split("/")
    if components[0] != "#":
        raise ValueError(
            "ref paths are expected to be URI fragments, meaning they should start with #."
        )
    out: list[Any] | dict[Any, Any] = schema
    for component in components[1:]:
        if component in out:
            if isinstance(out, list):
                raise KeyError(f"Reference '{path}' not found.")
            out = out[component]
        elif component.isdigit():
            index = int(component)
            if (isinstance(out, list) and 0 <= index < len(out)) or (
                isinstance(out, dict) and index in out
            ):
                out = out[index]
            else:
                raise KeyError(f"Reference '{path}' not found.")
        else:
            raise KeyError(f"Reference '{path}' not found.")
    return deepcopy(out)


def _process_dict_properties(
    properties: dict[str, Any],
    full_schema: dict[str, Any],
    processed_refs: set[str],
    skip_keys: list[str],
    *,
    shallow_refs: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in properties.items():
        if key in skip_keys:
            result[key] = deepcopy(value)
        elif isinstance(value, (dict, list)):
            result[key] = _dereference_refs_helper(
                value, full_schema, processed_refs, skip_keys, shallow_refs=shallow_refs
            )
        else:
            result[key] = value
    return result


def _dereference_refs_helper(
    obj: Any,
    full_schema: dict[str, Any],
    processed_refs: set[str] | None,
    skip_keys: list[str],
    *,
    shallow_refs: bool,
) -> Any:
    if processed_refs is None:
        processed_refs = set()

    if isinstance(obj, dict) and "$ref" in obj:
        ref_path = obj["$ref"]
        additional_properties = {k: v for k, v in obj.items() if k != "$ref"}

        if ref_path in processed_refs:
            return _process_dict_properties(
                additional_properties, full_schema, processed_refs, skip_keys, shallow_refs=shallow_refs
            )

        processed_refs.add(ref_path)
        referenced_object = deepcopy(_retrieve_ref(ref_path, full_schema))
        resolved_reference = _dereference_refs_helper(
            referenced_object, full_schema, processed_refs, skip_keys, shallow_refs=shallow_refs
        )
        processed_refs.remove(ref_path)

        if not additional_properties:
            return resolved_reference

        merged_result: dict[str, Any] = {}
        if isinstance(resolved_reference, dict):
            merged_result.update(resolved_reference)
        processed_additional = _process_dict_properties(
            additional_properties, full_schema, processed_refs, skip_keys, shallow_refs=shallow_refs
        )
        merged_result.update(processed_additional)
        return merged_result

    if isinstance(obj, dict):
        return _process_dict_properties(
            obj, full_schema, processed_refs, skip_keys, shallow_refs=shallow_refs
        )

    if isinstance(obj, list):
        return [
            _dereference_refs_helper(item, full_schema, processed_refs, skip_keys, shallow_refs=shallow_refs)
            for item in obj
        ]

    return obj


def dereference_refs(
    schema_obj: dict[str, Any],
    *,
    full_schema: dict[str, Any] | None = None,
    skip_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve and inline JSON Schema ``$ref`` references in a schema object."""
    full = full_schema or schema_obj
    keys_to_skip = list(skip_keys) if skip_keys is not None else ["$defs"]
    shallow = skip_keys is None
    return cast(
        "dict[str, Any]",
        _dereference_refs_helper(schema_obj, full, None, keys_to_skip, shallow_refs=shallow),
    )


_FILTERED_ARGS = ("run_manager", "callbacks")
_MIN_DOCSTRING_BLOCKS = 2

_TypeBaseModel = type[BaseModel] | type[BaseModelV1]


class _SchemaConfig:
    """Configuration for Pydantic models generated from function signatures."""
    extra: str = "forbid"
    arbitrary_types_allowed: bool = True


def _is_annotated_type(typ: type[Any]) -> bool:
    return get_origin(typ) in {typing.Annotated, typing_extensions.Annotated}


def _get_annotation_description(arg_type: type) -> str | None:
    if _is_annotated_type(arg_type):
        annotated_args = get_args(arg_type)
        for annotation in annotated_args[1:]:
            if isinstance(annotation, str):
                return annotation
            if isinstance(annotation, FieldInfo) and annotation.description:
                return annotation.description
    return None


def _parse_google_docstring(
    docstring: str | None,
    args: list[str],
    *,
    error_on_invalid_docstring: bool = False,
) -> tuple[str, dict[str, str]]:
    if docstring:
        docstring_blocks = docstring.split("\n\n")
        if error_on_invalid_docstring:
            filtered_annotations = {
                arg for arg in args
                if arg not in {"run_manager", "callbacks", "runtime", "return"}
            }
            if filtered_annotations and (
                len(docstring_blocks) < _MIN_DOCSTRING_BLOCKS
                or not any(block.startswith("Args:") for block in docstring_blocks[1:])
            ):
                raise ValueError("Found invalid Google-Style docstring.")
        descriptors = []
        args_block = None
        past_descriptors = False
        for block in docstring_blocks:
            if block.startswith("Args:"):
                args_block = block
                break
            if block.startswith(("Returns:", "Example:")):
                past_descriptors = True
            elif not past_descriptors:
                descriptors.append(block)
        description = " ".join(descriptors).strip()
    else:
        if error_on_invalid_docstring:
            raise ValueError("Found invalid Google-Style docstring.")
        description = ""
        args_block = None

    arg_descriptions: dict[str, str] = {}
    if args_block:
        arg = None
        for line in args_block.split("\n")[1:]:
            if ":" in line:
                arg, desc = line.split(":", maxsplit=1)
                arg = arg.strip()
                arg_name, _, annotations_ = arg.partition(" ")
                if annotations_.startswith("(") and annotations_.endswith(")"):
                    arg = arg_name
                arg_descriptions[arg] = desc.strip()
            elif arg:
                arg_descriptions[arg] += " " + line.strip()
    return description, arg_descriptions


def _parse_python_function_docstring(
    function: Any,
    annotations: dict[str, Any],
    *,
    error_on_invalid_docstring: bool = False,
) -> tuple[str, dict[str, str]]:
    docstring = inspect.getdoc(function)
    return _parse_google_docstring(
        docstring,
        list(annotations),
        error_on_invalid_docstring=error_on_invalid_docstring,
    )


def _validate_docstring_args_against_annotations(
    arg_descriptions: dict[str, str], annotations: dict[str, Any]
) -> None:
    for docstring_arg in arg_descriptions:
        if docstring_arg not in annotations:
            raise ValueError(f"Arg {docstring_arg} in docstring not found in function signature.")


def _infer_arg_descriptions(
    fn: Any,
    *,
    parse_docstring: bool = False,
    error_on_invalid_docstring: bool = False,
) -> tuple[str, dict[str, str]]:
    annotations = get_type_hints(fn, include_extras=True)
    if parse_docstring:
        description, arg_descriptions = _parse_python_function_docstring(
            fn, annotations, error_on_invalid_docstring=error_on_invalid_docstring
        )
    else:
        description = inspect.getdoc(fn) or ""
        arg_descriptions = {}
    if parse_docstring:
        _validate_docstring_args_against_annotations(arg_descriptions, annotations)
    for arg, arg_type in annotations.items():
        if arg in arg_descriptions:
            continue
        if desc := _get_annotation_description(arg_type):
            arg_descriptions[arg] = desc
    return description, arg_descriptions


def _is_pydantic_v1_annotation(annotation: Any) -> bool:
    try:
        return issubclass(annotation, BaseModelV1)
    except TypeError:
        return False


def _is_pydantic_v2_annotation(annotation: Any) -> bool:
    try:
        return issubclass(annotation, BaseModel)
    except TypeError:
        return False


def _function_annotations_are_pydantic_v1(sig: inspect.Signature, func: Any) -> bool:
    any_v1 = any(
        _is_pydantic_v1_annotation(p.annotation) for p in sig.parameters.values()
    )
    any_v2 = any(
        _is_pydantic_v2_annotation(p.annotation) for p in sig.parameters.values()
    )
    if any_v1 and any_v2:
        raise NotImplementedError(
            f"Function {func} contains a mix of Pydantic v1 and v2 annotations. "
            "Only one version of Pydantic annotations per function is supported."
        )
    return any_v1 and not any_v2


def _create_subset_model_v1(
    name: str,
    model: type[BaseModelV1],
    field_names: list[str],
    *,
    descriptions: dict[str, str] | None = None,
    fn_description: str | None = None,
) -> type[BaseModelV1]:
    fields = {}
    for field_name in field_names:
        field = model.__fields__[field_name]
        t = (
            field.outer_type_
            if field.required and not field.allow_none
            else field.outer_type_ | None
        )
        if descriptions and field_name in descriptions:
            field.field_info.description = descriptions[field_name]
        fields[field_name] = (t, field.field_info)
    rtn = cast("type[BaseModelV1]", _create_model_v1(name, **fields))
    rtn.__doc__ = textwrap.dedent(fn_description or model.__doc__ or "")
    return rtn


def _create_subset_model_v2(
    name: str,
    model: type[BaseModel],
    field_names: list[str],
    *,
    descriptions: dict[str, str] | None = None,
    fn_description: str | None = None,
) -> type[BaseModel]:
    descriptions_ = descriptions or {}
    fields = {}
    for field_name in field_names:
        field = model.model_fields[field_name]
        description = descriptions_.get(field_name, field.description)
        field_kwargs: dict[str, Any] = {"description": description}
        if field.default_factory is not None:
            field_kwargs["default_factory"] = field.default_factory
        else:
            field_kwargs["default"] = field.default
        field_info = FieldInfoV2(**field_kwargs)
        if field.metadata:
            field_info.metadata = field.metadata
        fields[field_name] = (field.annotation, field_info)
    rtn = cast(
        "type[BaseModel]",
        _create_model_base(name, **fields, __config__=ConfigDict(arbitrary_types_allowed=True)),
    )
    selected_annotations = [
        (n, annotation)
        for n, annotation in model.__annotations__.items()
        if n in field_names
    ]
    rtn.__annotations__ = dict(selected_annotations)
    rtn.__doc__ = textwrap.dedent(fn_description or model.__doc__ or "")
    return rtn


def _create_subset_model(
    name: str,
    model: _TypeBaseModel,
    field_names: list[str],
    *,
    descriptions: dict[str, str] | None = None,
    fn_description: str | None = None,
) -> _TypeBaseModel:
    if issubclass(model, BaseModelV1):
        return _create_subset_model_v1(
            name, model, field_names, descriptions=descriptions, fn_description=fn_description
        )
    return _create_subset_model_v2(
        name, model, field_names, descriptions=descriptions, fn_description=fn_description
    )


def _get_fields(model: type[BaseModel] | type[BaseModelV1]) -> dict[str, Any]:
    if not isinstance(model, type):
        model = type(model)
    if issubclass(model, BaseModel):
        return model.model_fields
    if issubclass(model, BaseModelV1):
        return model.__fields__
    raise TypeError(f"Expected a Pydantic model. Got {model}")


class _InjectedToolArg:
    """Marker for tool arguments that are injected at runtime and excluded from schema."""


def _is_directly_injected_arg_type(type_: Any) -> bool:
    return (
        isinstance(type_, type) and issubclass(type_, _InjectedToolArg)
    ) or (
        (origin := get_origin(type_)) is not None
        and isinstance(origin, type)
        and issubclass(origin, _InjectedToolArg)
    )


def _is_injected_arg_type(type_: Any, injected_type: type | None = None) -> bool:
    if injected_type is None:
        if _is_directly_injected_arg_type(type_):
            return True
        injected_type = _InjectedToolArg
    return any(
        isinstance(arg, injected_type)
        or (isinstance(arg, type) and issubclass(arg, injected_type))
        for arg in get_args(type_)[1:]
    )


def create_schema_from_function(
    model_name: str,
    func: Any,
    *,
    filter_args: list[str] | None = None,
    parse_docstring: bool = False,
    error_on_invalid_docstring: bool = False,
    include_injected: bool = True,
) -> _TypeBaseModel:
    """Create a Pydantic schema from a function's signature."""
    sig = inspect.signature(func)

    if _function_annotations_are_pydantic_v1(sig, func):
        validated = validate_arguments_v1(func, config=_SchemaConfig)
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=PydanticDeprecationWarning)
            validated = validate_arguments(func, config=_SchemaConfig)

    in_class = bool(func.__qualname__ and "." in func.__qualname__)

    has_args = False
    has_kwargs = False
    for param in sig.parameters.values():
        if param.kind == param.VAR_POSITIONAL:
            has_args = True
        elif param.kind == param.VAR_KEYWORD:
            has_kwargs = True

    inferred_model = validated.model

    if filter_args:
        filter_args_ = filter_args
    else:
        existing_params: list[str] = list(sig.parameters.keys())
        if existing_params and existing_params[0] in {"self", "cls"} and in_class:
            filter_args_ = [existing_params[0], *list(_FILTERED_ARGS)]
        else:
            filter_args_ = list(_FILTERED_ARGS)

        for existing_param in existing_params:
            if not include_injected and _is_injected_arg_type(
                sig.parameters[existing_param].annotation
            ):
                filter_args_.append(existing_param)

    description, arg_descriptions = _infer_arg_descriptions(
        func,
        parse_docstring=parse_docstring,
        error_on_invalid_docstring=error_on_invalid_docstring,
    )

    valid_properties = []
    for field in _get_fields(inferred_model):
        if not has_args and field == "args":
            continue
        if not has_kwargs and field == "kwargs":
            continue
        if field == "v__duplicate_kwargs":
            continue
        if field not in filter_args_:
            valid_properties.append(field)

    return _create_subset_model(
        model_name,
        inferred_model,
        list(valid_properties),
        descriptions=arg_descriptions,
        fn_description=description,
    )
