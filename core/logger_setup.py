# video_jukebox/core/logger_setup.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(settings_manager):
    log_directory = settings_manager.get("log_directory", "logs")
    if not os.path.exists(log_directory):
        try:
            os.makedirs(log_directory)
        except OSError as e:
            print(f"Error creating log directory {log_directory}: {e}")
            # Fallback to current directory if creation fails
            log_directory = "." 

    log_file = os.path.join(log_directory, "video_jukebox.log")

    logger = logging.getLogger("VideoJukebox")
    logger.setLevel(logging.INFO) # Set default level

    # Prevent duplicate handlers if setup_logging is called multiple times (e.g. in tests)
    if logger.hasHandlers():
        logger.handlers.clear()

    # File Handler (Rotating)
    # Rotates when log file reaches 1MB, keeps up to 5 backup logs
    fh = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
    fh.setLevel(logging.INFO)

    # Console Handler (optional, for debugging)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG) # Show more detailed logs on console during dev

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    # logger.addHandler(ch) # Uncomment for console output during development

    logger.info("Logging initialized.")
    return logger