import json

import numpy

import yaml
from typing import BinaryIO

# disables the automatic conversion of date-time objects to datetime objects and leaves them as strings
yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:timestamp'] = \
    yaml.constructor.SafeConstructor.yaml_constructors[u'tag:yaml.org,2002:str']

def yaml_safe_load(file : BinaryIO) -> dict:
    return yaml.safe_load(file)