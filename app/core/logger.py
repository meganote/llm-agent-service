import logging
import os
import sys
from pathlib import Path

from asgi_correlation_id.context import correlation_id
from loguru import logger


class Logger:
    def __init__(
        self,
        env: str = "dev",
        dir: str = "logs",
        retention: str = "30 days",
        rotation: str = "00:00",
    ):
        self.env = env
        self.dir = Path(dir)
        self.retention = retention
        self.rotation = rotation

        self.format = "{time:YYYY-MM-DD HH:mm:ss.SSS} [{correlation_id}] | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        self.dir.mkdir(exist_ok=True)
        self.configure()
        # self._intercept_handler()

    def configure(self) -> None:
        logger.remove()

        if self.env == "dev":
            self._add_console_handler()

        else:
            self._add_file_handler()

    def get_logger(self):
        return logger

    def _correlation_id_filter(self, record):
        record["correlation_id"] = correlation_id.get()
        return record["correlation_id"]

    def _add_console_handler(self) -> None:
        logger.add(
            sink=sys.stdout,
            format=self.format,
            level="DEBUG",
            filter=self._correlation_id_filter,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    def _add_file_handler(self) -> None:
        logger.add(
            sink=self.dir / "app_{time:YYYY-MM-DD}.log",
            format=self.format,
            rotation="00:00",
            retention="30 days",
            level="INFO",
            filter=self._correlation_id_filter,
            enqueue=True,
            diagnose=False,
        )

    def _intercept_handler(self) -> None:
        class InterceptHandler(logging.Handler):
            def emit(self, record: logging.LogRecord):
                # Get corresponding Loguru level
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                # Find caller to get correct stack depth
                frame, depth = logging.currentframe(), 2
                while frame.f_back and frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1

                logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )

        logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)

        for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logging.getLogger(name).handlers = []
            logging.getLogger(name).propagate = True


logger = Logger(
    env=os.getenv("ENV", "dev"),
    dir=os.getenv("LOG_DIR", "logs"),
    retention=os.getenv("LOG_RETENTION", "30 days"),
).get_logger()
