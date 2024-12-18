#logger.py 

import logging
from colorama import Fore, Style, init

# Suppress unnecessary logs from specific modules
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

# Initialize colorama for cross-platform support
init(autoreset=True)

# Define updated color codes for different log levels
LOG_COLORS = {
    logging.DEBUG: Fore.LIGHTBLUE_EX,          # Debug messages in light blue
    logging.INFO: Fore.LIGHTGREEN_EX,         # Info messages in light green
    logging.WARNING: Fore.LIGHTYELLOW_EX,     # Warnings in light yellow
    logging.ERROR: Fore.LIGHTRED_EX,          # Errors in light red
    logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,  # Critical errors in bright magenta
}

class SimpleColorFormatter(logging.Formatter):
    """
    A custom logging formatter to add colors based on log levels.
    """
    def __init__(self, fmt=None, datefmt="%Y-%m-%d %H:%M:%S", style='%'):
        # Default log format if none is provided
        if not fmt:
            fmt = "%(asctime)s - %(levelname)s - %(message)s"
        super().__init__(fmt, datefmt, style)

    def format(self, record):
        """
        Format the log message by adding color to the log level name.
        
        Args:
            record (logging.LogRecord): The log record containing log details.

        Returns:
            str: The formatted log message with colorized log level.
        """
        # Apply the color to the log level
        log_color = LOG_COLORS.get(record.levelno, "")
        levelname_colored = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        record.levelname = levelname_colored  # Update the record's level name
        return super().format(record)

def get_logger(name="AppLogger", level=logging.DEBUG):
    """
    Create and configure a logger with colored output for terminal logs.

    Args:
        name (str): The name of the logger.
        level (int): The logging level (e.g., DEBUG, INFO, WARNING).

    Returns:
        logging.Logger: A logger instance configured with colored output.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)  # Set the logging level

    # Avoid adding multiple handlers to the logger
    if not logger.handlers:
        # Create a console handler for terminal output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Set the custom formatter for colorized logs
        formatter = SimpleColorFormatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(console_handler)

    return logger

# Example usage
if __name__ == "__main__":
    # Initialize logger
    logger = get_logger("ExampleLogger", level=logging.DEBUG)

    # Log messages at different levels
    logger.debug("This is a debug message.")          # Light blue
    logger.info("This is an info message.")           # Light green
    logger.warning("This is a warning message.")      # Light yellow
    logger.error("This is an error message.")         # Light red
    logger.critical("This is a critical message.")    # Bright magenta
