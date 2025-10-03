# File: src/my_framework/agents/loggerbot.py

import logging
import queue
import sys
from logging import StreamHandler

# --- Log Levels ---
# DEBUG: Detailed information, typically of interest only when diagnosing problems.
# INFO: Confirmation that things are working as expected.
# WARNING: An indication that something unexpected happened, or indicative of some problem in the near future.
# ERROR: Due to a more serious problem, the software has not been able to perform some function.
# CRITICAL: A serious error, indicating that the program itself may be unable to continue running.

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

log_queue = queue.Queue()

class QueueLogHandler(logging.Handler):
    """A custom logging handler that puts logs into a queue."""
    def __init__(self, q):
        super().__init__()
        self.queue = q

    def emit(self, record):
        self.queue.put(self.format(record))

class LoggerBot:
    """A centralized logging agent for the entire application."""
    _logger = None

    @staticmethod
    def get_logger(level="INFO"):
        if LoggerBot._logger is None:
            LoggerBot._logger = logging.getLogger("smartAIJournalistBot")
            LoggerBot._logger.setLevel(LOG_LEVELS.get(level, logging.INFO))
            
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            # Clear existing handlers to prevent duplicate logs
            if LoggerBot._logger.hasHandlers():
                LoggerBot._logger.handlers.clear()

            # Add a console handler to see logs in the terminal
            console_handler = StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            LoggerBot._logger.addHandler(console_handler)

            # Add our custom queue handler for the UI
            queue_handler = QueueLogHandler(log_queue)
            queue_handler.setFormatter(formatter)
            LoggerBot._logger.addHandler(queue_handler)
            
            LoggerBot._logger.info("LoggerBot initialized.")

        return LoggerBot._logger

logger = LoggerBot.get_logger()