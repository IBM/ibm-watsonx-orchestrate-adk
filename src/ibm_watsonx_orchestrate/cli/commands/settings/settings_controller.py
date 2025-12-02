import logging
from ibm_watsonx_orchestrate.cli.config import USE_NATIVE_DOCKER, Config, SETTINGS_HEADER, FILE_ENCODING

logger = logging.getLogger(__name__)

class SettingsController:
    config = None

    def __get_config(self) -> Config:
        if not self.config:
            self.config = Config()
        return self.config

    def set_encoding(self, encoding: str):
        cfg = self.__get_config()

        cfg.write(SETTINGS_HEADER, FILE_ENCODING, encoding)

        logger.info(f"Successfully set encoding type override '{encoding}'")

    
    def unset_encoding(self):
        cfg = self.__get_config()
        current_encoding = cfg.read(SETTINGS_HEADER, FILE_ENCODING)
        if current_encoding:
            cfg.delete(SETTINGS_HEADER, FILE_ENCODING)
            logger.info(f"Successfully unset encoding type override '{current_encoding}'")
        else:
            logger.error("No encoding type override found thus no change has been made")

    def set_docker_host(self, native: bool = False):
        cfg = self.__get_config()
        cfg.write(SETTINGS_HEADER, USE_NATIVE_DOCKER, native)
        logger.info(f"Docker host set to '{'user managed' if native else 'orchestrate'}'")