import logging
import logging.config
from importlib import resources
import yaml
from enum import Enum

class LogColors(str, Enum):
    INFO = "\033[0;36m" #cyan
    DEBUG = "\033[0;35m" #magenta
    WARNING = "\033[0;33m" #yellow
    ERROR = "\033[0;31m" #red
    RESET = "\033[0;0m"

# Track if logging has been configured
_logging_configured = False

def setup_logging():
    global _logging_configured
    
    # Only configure logging once
    if _logging_configured:
        return
    
    config_file = str(resources.files("ibm_watsonx_orchestrate_core.utils.logging").joinpath("logging.yaml"))
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    logging.config.dictConfig(config)

    # Add log colors - use the original level names to avoid nesting
    logging.addLevelName( logging.INFO, LogColors.INFO + f"[{logging.getLevelName(logging.INFO)}]" + LogColors.RESET)
    logging.addLevelName( logging.DEBUG, LogColors.DEBUG + f"[{logging.getLevelName(logging.DEBUG)}]" + LogColors.RESET)
    logging.addLevelName( logging.WARNING, LogColors.WARNING + f"[{logging.getLevelName(logging.WARNING)}]" + LogColors.RESET)
    logging.addLevelName( logging.ERROR, LogColors.ERROR + f"[{logging.getLevelName(logging.ERROR)}]" + LogColors.RESET)
    
    _logging_configured = True