import io
import logging
from typing import Any, Callable
from contextlib import redirect_stdout, redirect_stderr, ExitStack


# Add this at the module level to store original logger states
_original_logger_states = {}

def __save_all_logger_states():
    """Save the original state of all loggers."""
    global _original_logger_states
    _original_logger_states = {}
    
    # Save state for named loggers
    for name, logger in logging.root.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            _original_logger_states[name] = {
                'level': logger.level,
                'handlers': list(logger.handlers),  # Make a copy of the handlers list
                'propagate': logger.propagate
            }
    
    # Save state for root logger
    root_logger = logging.getLogger()
    _original_logger_states['root'] = {
        'level': root_logger.level,
        'handlers': list(root_logger.handlers)  # Root logger doesn't have propagate
    }

def __reset_all_loggers():
    """Reset all loggers to their original state."""
    global _original_logger_states
    
    # Reset named loggers
    for name, logger in logging.root.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            # Clear current handlers
            logger.handlers.clear()
            
            # Restore original state if we have it
            if name in _original_logger_states:
                state = _original_logger_states[name]
                logger.setLevel(state['level'])
                for handler in state['handlers']:
                    logger.addHandler(handler)
                logger.propagate = state['propagate']
            else:
                # Default behavior if we don't have saved state
                logger.propagate = True
    
    # Reset root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Restore original root logger state
    if 'root' in _original_logger_states:
        state = _original_logger_states['root']
        root_logger.setLevel(state['level'])
        for handler in state['handlers']:
            root_logger.addHandler(handler)



def silent_call(fn: Callable, *args, suppress_stdout: bool = True,
               suppress_stderr: bool = False, suppress_logging: bool = True, **kwargs) -> Any:
    """
    Call a function silently, suppressing stdout and/or stderr output.
    
    Args:
        fn: The function to call
        *args: Positional arguments to pass to the function
        suppress_stdout: Whether to suppress stdout (default: True)
        suppress_stderr: Whether to suppress stderr (default: False)
        suppress_logging: Whether to suppress logging output (default: True)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The return value of the called function
    """
    with ExitStack() as stack:
        null_stream = io.StringIO()
        
        if suppress_stdout:
            stack.enter_context(redirect_stdout(null_stream))
        if suppress_stderr:
            stack.enter_context(redirect_stderr(null_stream))
        
        if suppress_logging:
            # Save original logger states before modifying
            __save_all_logger_states()
            
            stream_handler = logging.StreamHandler(null_stream)

            # Patch all known loggers
            for name, logger in logging.root.manager.loggerDict.items():
                if isinstance(logger, logging.Logger):
                    logger.handlers.clear()
                    logger.addHandler(stream_handler)
                    logger.propagate = False            

        try:
            return fn(*args, **kwargs)
        except SystemExit:
            raise Exception(f"{null_stream.getvalue()}")
        finally:
            if suppress_logging:
                __reset_all_loggers()