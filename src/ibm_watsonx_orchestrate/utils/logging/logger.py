import logging
import logging.config
from importlib import resources
import yaml

def setup_logging():
    config_file = str(resources.files("ibm_watsonx_orchestrate.utils.logging").joinpath("logging.yaml"))
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    logging.config.dictConfig(config)