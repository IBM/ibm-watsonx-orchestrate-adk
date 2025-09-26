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
    return any(x.startswith("%s/" % file_path.rstrip("/")) for x in zip_file.namelist())

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
