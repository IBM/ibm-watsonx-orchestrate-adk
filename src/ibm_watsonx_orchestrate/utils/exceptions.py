import logging
import sys
import os

logger = logging.getLogger(__name__)

class BadRequest(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
        logger.error(message)

        # We need to exit to avoid getting 2 error messages printed
        # We don't want to exit while running tests
        # Only exit if not running in a test and no --debug
        if not self._in_test() and "--debug" not in sys.argv:
            sys.exit(1)

    def _in_test(self):
        return "PYTEST_CURRENT_TEST" in os.environ

    def __str__(self):
        return self.message

class VMLifecycleException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message
    

class ToolContextException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message

