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


def setup_logging():
    config_file = str(resources.files("ibm_watsonx_orchestrate.utils.logging").joinpath("logging.yaml"))
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    logging.config.dictConfig(config)

    # Add log colors
    logging.addLevelName( logging.INFO, LogColors.INFO + f"[{logging.getLevelName(logging.INFO)}]" + LogColors.RESET)
    logging.addLevelName( logging.DEBUG, LogColors.DEBUG + f"[{logging.getLevelName(logging.DEBUG)}]" + LogColors.RESET)
    logging.addLevelName( logging.WARNING, LogColors.WARNING + f"[{logging.getLevelName(logging.WARNING)}]" + LogColors.RESET)
    logging.addLevelName( logging.ERROR, LogColors.ERROR + f"[{logging.getLevelName(logging.ERROR)}]" + LogColors.RESET)