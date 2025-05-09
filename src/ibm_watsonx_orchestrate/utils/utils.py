import re
import zipfile
import yaml
from typing import BinaryIO

# disables the automatic conversion of date-time objects to datetime objects and leaves them as strings
yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:timestamp'] = \
    yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:str']

def yaml_safe_load(file : BinaryIO) -> dict:
    return yaml.safe_load(file)

def sanatize_app_id(app_id: str) -> str:
    sanatize_pattern = re.compile(r"[^a-zA-Z0-9]+")
    return re.sub(sanatize_pattern,'_', app_id)

def check_file_in_zip(file_path: str, zip_file: zipfile.ZipFile) -> bool:
    return any(x.startswith("%s/" % file_path.rstrip("/")) for x in zip_file.namelist())