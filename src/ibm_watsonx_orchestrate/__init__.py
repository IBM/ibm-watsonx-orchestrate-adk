#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

pkg_name = "ibm-watsonx-orchestrate"

__version__ = "1.0.0"



try:
    from importlib.metadata import version

    ver = version(pkg_name)

except (ModuleNotFoundError, AttributeError):
    from importlib_metadata import version as imp_lib_ver

    ver = imp_lib_ver(pkg_name)

from ibm_watsonx_orchestrate.client.client import Client
from ibm_watsonx_orchestrate.utils.logging.logger import setup_logging

Client.version = ver
__version__ = ver
setup_logging()

