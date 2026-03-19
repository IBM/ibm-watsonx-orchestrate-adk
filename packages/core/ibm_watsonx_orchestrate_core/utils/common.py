import re
import zipfile
import yaml
from typing import BinaryIO, Any, Tuple

# disables the automatic conversion of date-time objects to datetime objects and leaves them as strings
yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:timestamp'] = \
    yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:str']

def yaml_safe_load(file : BinaryIO) -> dict:
    return yaml.safe_load(file)

def sanitize_app_id(app_id: str) -> str:
    sanitize_pattern = re.compile(r"[^a-zA-Z0-9]+")
    return re.sub(sanitize_pattern,'_', app_id)

def sanitize_catalog_label(label: str) -> str:
    sanitize_pattern = re.compile(r"[^a-zA-Z0-9]+")
    return re.sub(sanitize_pattern,'_', label)

def check_file_in_zip(file_path: str, zip_file: zipfile.ZipFile) -> bool:
    name_list = zip_file.namelist()
    return any(x.startswith("%s/" % file_path.rstrip("/")) for x in name_list) or file_path in name_list

def parse_bool_safe (value, fallback = False) -> bool:
    if value is not None:
        if isinstance(value, bool):
            return value

        elif isinstance(value, str):
            value = value.lower().strip()
            if value in ("yes", "true", "t", "1"):
                return True

            elif value in ("no", "false", "f", "0"):
                return False

        elif value in (0, 1):
            return parse_bool_safe(str(value), fallback)

    return fallback

def parse_bool_safe_and_get_raw_val (value, fallback: bool = False) -> Tuple[bool, Any | None]:
    if value is not None:
        if isinstance(value, bool):
            return value, None

        elif isinstance(value, str):
            value_str = value.lower().strip()
            if value_str in ("yes", "true", "t", "1"):
                return True, None

            elif value_str in ("no", "false", "f", "0"):
                return False, None

        elif value in (0, 1):
            return parse_bool_safe_and_get_raw_val(str(value), fallback)

    return fallback, value

def parse_int_safe (value, base: int = 10, fallback: int | None = None) -> int:
    if value is not None:
        if isinstance(value, int):
            return value

        elif isinstance(value, float):
            return int(value)

        elif isinstance(value, str):
            value = value.strip()

            try:
                return int(value, base)

            except ValueError as ex:
                pass

    return fallback

def parse_string_safe(value: any, override_empty_to_none: bool = False,
                      force_default_to_empty: bool = False) -> str | None:
    if value is not None and isinstance(value, str):
        value = value.strip()

        if value == "" and parse_bool_safe(value=override_empty_to_none, fallback=False):
            value = None

        return value

    return "" if parse_bool_safe(value=force_default_to_empty, fallback=False) else None

def singleton(cls):
    instances = {}

    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return getinstance