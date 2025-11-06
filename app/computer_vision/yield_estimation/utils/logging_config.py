"""
Logging Configuration for Yield Estimation
==========================================

This module sets up a standardized, application-wide logging system. A consistent
logging format and configuration are crucial for debugging, monitoring, and
auditing the behavior of the complex yield estimation pipeline.

Key Features:
-------------
1.  **Standardized Format**:
    -   All log messages are formatted to include a timestamp, log level, logger
      name, and the message itself. This consistency makes logs easy to parse
      and analyze, whether by a human or an automated system like the ELK stack.

2.  **Multiple Handlers**:
    -   **Console Handler**: Logs messages to `sys.stdout`. This is useful for
      real-time monitoring during development and interactive sessions. It can
      be configured to display different log levels (e.g., INFO, DEBUG).
    -   **File Handler**: Logs messages to a file (`yield_estimation.log`). This
      is essential for production environments, as it provides a persistent
      record of events.
    -   **RotatingFileHandler**: The file handler is configured to rotate logs
      once they reach a certain size, preventing log files from growing
      indefinitely and consuming excessive disk space. It keeps a configurable
      number of backup log files.

3.  **Centralized Configuration**:
    -   The `setup_logging` function provides a single point of entry to
      configure the root logger for the entire application.
    -   It respects the `LOG_LEVEL` defined in the main `Settings` object,
      allowing the verbosity of the logs to be controlled globally.

4.  **Ease of Use**:
    -   Once `setup_logging` is called at the application's entry point (e.g.,
      in `main.py` or the API startup event), any module can get a logger
      instance by simply calling `logging.getLogger(__name__)`. This logger
      will automatically inherit the configuration of the root logger.

Example Usage:
--------------
```python
# In the main entry point of the application
from app.computer_vision.yield_estimation.utils.logging_config import setup_logging
from app.computer_vision.yield_estimation.utils.config import get_settings

settings = get_settings()
setup_logging(log_level=settings.log_level)

# In any other module
import logging
logger = logging.getLogger(__name__)

logger.info("This is an informational message.")
logger.error("This is an error message.")
```
This setup ensures that all parts of the application contribute to a unified and
manageable stream of log data.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Literal

# --- Constants ---
LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_PATH = "logs/yield_estimation.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# --- Global State ---
_is_configured = False

def setup_logging(log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"):
    """
    Configures the root logger for the application.

    This function should be called once at the start of the application.
    It sets up handlers for logging to both the console and a rotating file.

    Args:
        log_level (str): The minimum log level to capture (e.g., "INFO", "DEBUG").
    """
    global _is_configured
    if _is_configured:
        logging.getLogger(__name__).warning("Logging is already configured. Skipping setup.")
        return

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # --- Rotating File Handler ---
    try:
        # Ensure the log directory exists
        import os
        log_dir = os.path.dirname(LOG_FILE_PATH)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    except (IOError, PermissionError) as e:
        root_logger.error(f"Failed to configure file logger at '{LOG_FILE_PATH}': {e}")

    # Mark as configured
    _is_configured = True
    root_logger.info(f"Logging configured successfully. Level: {log_level}, File: '{LOG_FILE_PATH}'")


# --- Example Usage ---
if __name__ == "__main__":
    print("--- Logging Configuration Demo ---")

    # 1. Setup logging with INFO level
    print("\n[1. Setting up logging with level INFO]")
    setup_logging(log_level="INFO")

    # 2. Get loggers for different modules
    logger_main = logging.getLogger("main_app")
    logger_data = logging.getLogger("data_processing")
    logger_model = logging.getLogger("model.training")

    # 3. Log messages from different levels
    print("\n[2. Logging messages... Check console and 'logs/yield_estimation.log']")
    logger_main.debug("This is a debug message. It should NOT appear.")
    logger_main.info("Application starting up.")
    logger_data.info("Starting to process batch #1.")
    logger_model.warning("Learning rate seems high. Consider adjusting.")
    logger_data.error("Failed to read file: 'data/raw/image_001.tif'. File not found.")
    
    # 4. Test reconfiguration guard
    print("\n[3. Attempting to re-configure logging...]")
    setup_logging(log_level="DEBUG") # Should print a warning and not re-configure.

    # 5. Test that the level is still INFO
    logger_main.debug("This second debug message should also NOT appear.")
    
    print("\n--- Logging Demo Finished ---")
    print("Please inspect the 'logs/yield_estimation.log' file to see the file output.")
