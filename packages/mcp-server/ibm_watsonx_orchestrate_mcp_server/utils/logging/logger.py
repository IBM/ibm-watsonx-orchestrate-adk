import logging
import logging.config
import os
import yaml
from enum import Enum

class LogColors(str, Enum):
    INFO = "\033[0;36m" #cyan
    DEBUG = "\033[0;35m" #magenta
    WARNING = "\033[0;33m" #yellow
    ERROR = "\033[0;31m" #red
    RESET = "\033[0;0m"


def setup_logging(debug=False):
    """Setup logging configuration
    
    Args:
        debug (bool, optional): Whether to enable debug logging. Defaults to False.
    """
    config_path = os.path.join(os.path.dirname(__file__), "log_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Adjust root logger level based on debug parameter
    if not debug:
        # Set console handler to INFO level if debug is False
        for _, handler in config.get('handlers', {}).items():
            if handler.get('class') == 'logging.StreamHandler':
                handler['level'] = 'INFO'
    
    logging.config.dictConfig(config)

     # Add log colors
    logging.addLevelName( logging.INFO, LogColors.INFO + f"[{logging.getLevelName(logging.INFO)}]" + LogColors.RESET)
    logging.addLevelName( logging.DEBUG, LogColors.DEBUG + f"[{logging.getLevelName(logging.DEBUG)}]" + LogColors.RESET)
    logging.addLevelName( logging.WARNING, LogColors.WARNING + f"[{logging.getLevelName(logging.WARNING)}]" + LogColors.RESET)
    logging.addLevelName( logging.ERROR, LogColors.ERROR + f"[{logging.getLevelName(logging.ERROR)}]" + LogColors.RESET)