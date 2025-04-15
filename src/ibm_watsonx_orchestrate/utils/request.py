import logging
import sys

logger = logging.getLogger(__name__)

class BadRequest(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
        logger.error(message)

        if "--debug" not in sys.argv:
            sys.exit(1)

    def __str__(self):
        return self.message
