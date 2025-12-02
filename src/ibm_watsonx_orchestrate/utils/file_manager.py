import logging
from typing import Any
from charset_normalizer import from_path
import mimetypes
from pathlib import Path
from ibm_watsonx_orchestrate.utils.utils import singleton
from ibm_watsonx_orchestrate.cli.config import Config, SETTINGS_HEADER, FILE_ENCODING
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest

logger = logging.getLogger(__name__)

# Python's inbuilt mimetypes do not include yaml
YAML_MIME_TYPE = "application/yaml" 
mimetypes.add_type(YAML_MIME_TYPE, ".yaml")
mimetypes.add_type(YAML_MIME_TYPE, ".yml")

@singleton
class FileManager:
    UTF_8_ENCODING = 'utf-8'
    DEFAULT_ENCODING = UTF_8_ENCODING
    # File types where smart encoding should be used
    # If any are not found in Python's mimetype list fallback to 'text/plain' as that type is supported
    ENCODING_SUPPORTED_MIME_TYPES = {
        mimetypes.types_map.get(".json", "text/plain"),
        mimetypes.types_map.get(".js", "text/plain"),
        mimetypes.types_map.get(".txt", "text/plain"),
        mimetypes.types_map.get(".csv", "text/plain"),
        mimetypes.types_map.get(".html", "text/plain"),
        mimetypes.types_map.get(".xml", "text/plain"),
        mimetypes.types_map.get(".py", "text/plain"),
        mimetypes.types_map.get(".yaml", "text/plain"),
    }
    config = None

    def __get_config(self):
        if not self.config:
            self.config = Config()
        return self.config
    
    def __guess_encoding(self, file_path: Path) -> str:
        guesses = from_path(file_path)
        best_guess = guesses.best()
        if best_guess:
            return best_guess.encoding
        else:
            return self.DEFAULT_ENCODING
    
    def __should_set_encoding(self, file_path: Path) -> bool:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type in self.ENCODING_SUPPORTED_MIME_TYPES:
            return True
        return False

    def get_encoding(self, file_path: Path) -> str:
        cfg = self.__get_config()
        encoding = cfg.read(SETTINGS_HEADER, FILE_ENCODING)
        if encoding:
            logger.warning(f"Using user defined encoding '{encoding}'. Skipping encoding detection.")
            return encoding
        
        if not file_path.exists():
            return self.DEFAULT_ENCODING
        
        encoding = self.__guess_encoding(file_path=file_path)
        if encoding == "ascii":
            return self.UTF_8_ENCODING
        return encoding

    def open_file_encoded(    
        self,
        file_path: str | Path,
        mode: str = 'r',
        **kwargs: Any
    ):  

        if "encoding" not in kwargs and "b" not in mode:
            if not isinstance(file_path, Path):
                file_path = Path(file_path)
            if self.__should_set_encoding(file_path=file_path):
                kwargs["encoding"] = self.get_encoding(file_path=file_path)
        try:
            return open(file_path, mode, **kwargs)
        except LookupError:
            raise BadRequest(f"The encoding type '{kwargs.get('encoding')}' is not supported by Python. Please select a valid encoding type using `orchestrate settings set-encoding` or enable encoding detection by unsetting the encoding override `orchestrate settings unset-encoding`")

def safe_open(
    *args: Any,
    **kwargs: Any
):
    fm = FileManager()
    return fm.open_file_encoded(*args, **kwargs)