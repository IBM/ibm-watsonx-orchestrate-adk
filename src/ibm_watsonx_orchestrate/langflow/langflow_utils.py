import logging
import ast
import sys
from pathlib import Path
import importlib.util

from pydantic import BaseModel

from .lfx_deps import LFX_DEPENDENCIES, MODULE_DEPENDENCIES, MODULE_MAP

logger = logging.getLogger(__name__)

class LangflowComponent(BaseModel):
    id: str
    name: str
    credentials: dict
    requirements: list[str] = []

class LangflowModelSpec(BaseModel):
    version: str
    components: list[LangflowComponent]

import math
from collections import Counter

def _calculate_entropy(s):
    """
    Calculates the Shannon entropy of a string.

    Parameters:
        s (str): Input string.

    Returns:
        float: Shannon entropy value.
    """
    if not s:
        return 0.0

    freq = Counter(s)
    length = len(s)

    entropy = -sum((count / length) * math.log2(count / length) for count in freq.values())
    return entropy

def _mask_api_key(key):
    """
    Masks an API key by keeping the first 5 characters visible,
    masking the rest with asterisks, and truncating the result to a maximum of 25 characters.

    Parameters:
        key (str): The API key string.

    Returns:
        str: Masked and truncated API key.
    """
    if not isinstance(key, str):
        return key
    
    # if this is a potential real API key -- mask it
    if _calculate_entropy(key) > 4.1:
        visible_part = key[:5]
        masked_part = '*' * (len(key) - 5)
        masked_key = visible_part + masked_part

        return masked_key[:25]
    elif len(key) > 25:
        # if the key is longer than 25 characters, truncates it anyway
        return key[:22] + '...'
    
    return key

def _extract_imports(source_code) -> list[str]:
    tree = ast.parse(source_code)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # we only need the module name, not sub-module
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # we only need the module name, not sub-module
                imports.add(node.module.split('.')[0])
    return sorted(imports)



def _is_builtin_module(module_name: str) -> bool:
    underscore_module_name = f"_{module_name}"

    # Check against the list of standard modules 
    if module_name in sys.stdlib_module_names:
        return True
    
    if underscore_module_name in sys.stdlib_module_names:
        return True

    # Check against the list of built-in module names
    if module_name in sys.builtin_module_names:
        return True

    if underscore_module_name in sys.builtin_module_names:
        return True
    
    # Use importlib to find the module spec
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return False  # Module not found

    # Check if the loader is a BuiltinImporter
    return isinstance(spec.loader, importlib.machinery.BuiltinImporter)


def _find_missing_requirements(imported_modules, requirements_modules: list[str]) -> list[str]:
    """
    Compare imported modules with requirements.txt and return missing ones.

    Parameters:
        imported_modules (list): List of module names used in the code.
        requirements_file_path (str): Path to the requirements.txt file.

    Returns:
        list: Modules that are imported but not listed in requirements.txt.
    """
    def normalize_module_name(name):
        module_name = name.split('.')[0].lower()
        # sometimes the module name in pipy is different than the real name
        if module_name in MODULE_MAP:
            module_name = MODULE_MAP[module_name]
        return module_name

    # Normalize imported module names
    normalized_imports = [normalize_module_name(mod) for mod in imported_modules]

    # filter out all built-ins
    filtered_imports = [
        module for module in normalized_imports
        if _is_builtin_module(module) is False
    ]


    # pull in additional dependencies (these are usually dynamic dependencies that are not explicitly imported)
    additional_imports = []
    for module in filtered_imports:
        if module in MODULE_DEPENDENCIES:
            additional_imports.extend(MODULE_DEPENDENCIES[module])

    filtered_imports.extend(additional_imports)

    # Compare and find missing modules
    missing_modules = [
        module for module in filtered_imports
        if module not in requirements_modules
    ]

    return missing_modules



def parse_langflow_model(model) -> LangflowModelSpec:
    """
    Extracts component details and Langflow version from a Langflow JSON object.

    Parameters:
        model (dict): The Langflow JSON object.

    Returns:
        LangflowModelSpec: A LangflowModelSpec object containing the extracted version and component information.
    """
    version = model.get("last_tested_version", "Unknown")
    components = []
    data = model.get('data', {} )

    # get the list of available modules
    requirements_modules = LFX_DEPENDENCIES

    for node in data.get("nodes", []):
        node_data = node.get("data", {})
        node_info = node_data.get("node", {})
        template = node_info.get("template", {})
        code = template.get("code")
        credentials = {}

        missing_imports = []
        for field_name, field_info in template.items():
            if isinstance(field_info, dict) and field_info.get("password", False) == True:
                credentials[field_name] = _mask_api_key(field_info.get("value"))

        if code and code.get("value") != None:
            imports = _extract_imports(code.get("value"))
            if len(imports) > 0:
                missing_imports = _find_missing_requirements(imports, requirements_modules)

        component_info = LangflowComponent(name=node_info.get("display_name", "Unknown"), id=node_data.get("id", "Unknown"), 
                                           credentials=credentials, requirements=missing_imports)

        components.append(component_info)

    return LangflowModelSpec(version=version, components=components)

