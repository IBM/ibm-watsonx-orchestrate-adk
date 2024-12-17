from __future__ import annotations
import re
import os
import sys
import shutil
import tarfile
import logging
import importlib.util
import json
import platform

import numpy
import importlib

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Type,
    Generator,
    TypeAlias,
    cast,
)
from subprocess import check_call
from packaging import version
from warnings import warn

from ibm_watsonx_orchestrate import ver, pkg_name
import ibm_watsonx_orchestrate.client._wrappers.requests as requests

from ibm_watsonx_orchestrate.client.client_errors import (
    ClientError,
    CannotInstallLibrary,
)

if TYPE_CHECKING:
    import collections
    from types import TracebackType
    from ibm_watsonx_orchestrate import Client
    from requests import Response

    PipelineType: TypeAlias = Any
    MLModelType: TypeAlias = Any

INSTANCE_DETAILS_TYPE = "instance_details_type"
PIPELINE_DETAILS_TYPE = "pipeline_details_type"
DEPLOYMENT_DETAILS_TYPE = "deployment_details_type"
EXPERIMENT_RUN_DETAILS_TYPE = "experiment_run_details_type"
MODEL_DETAILS_TYPE = "model_details_type"
DEFINITION_DETAILS_TYPE = "definition_details_type"
EXPERIMENT_DETAILS_TYPE = "experiment_details_type"
TRAINING_RUN_DETAILS_TYPE = "training_run_details_type"
FUNCTION_DETAILS_TYPE = "function_details_type"
DATA_ASSETS_DETAILS_TYPE = "data_assets_details_type"
SW_SPEC_DETAILS_TYPE = "sw_spec_details_type"
HW_SPEC_DETAILS_TYPE = "hw_spec_details_type"
RUNTIME_SPEC_DETAILS_TYPE = "runtime_spec_details_type"
LIBRARY_DETAILS_TYPE = "library_details_type"
SPACES_DETAILS_TYPE = "spaces_details_type"
MEMBER_DETAILS_TYPE = "member_details_type"
CONNECTION_DETAILS_TYPE = "connection_details_type"
PKG_EXTN_DETAILS_TYPE = "pkg_extn_details_type"
UNKNOWN_ARRAY_TYPE = "resource_type"
UNKNOWN_TYPE = "unknown_type"
SPACES_IMPORTS_DETAILS_TYPE = "spaces_imports_details_type"
SPACES_EXPORTS_DETAILS_TYPE = "spaces_exports_details_type"

SPARK_MLLIB = "mllib"
SPSS_FRAMEWORK = "spss-modeler"
TENSORFLOW_FRAMEWORK = "tensorflow"
XGBOOST_FRAMEWORK = "xgboost"
SCIKIT_LEARN_FRAMEWORK = "scikit-learn"
PMML_FRAMEWORK = "pmml"


class NumpyTypeEncoder(json.JSONEncoder):
    """Extended json.JSONEncoder to encode correctly numpy types."""

    def default(
        self, obj: numpy.integer | numpy.bool_ | numpy.floating | numpy.ndarray
    ) -> int | bool | float | list | None:
        if isinstance(obj, numpy.integer):
            return int(obj)
        elif isinstance(obj, numpy.bool_):
            return bool(obj)
        elif isinstance(obj, numpy.floating):
            return None if numpy.isnan(obj) else float(obj)
        elif isinstance(obj, numpy.ndarray):
            return obj.tolist()
        else:
            return super().default(obj)
