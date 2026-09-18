"""Structured logging configuration (RNF-24) with structlog."""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging; observability events emit JSON via structlog."""
    root = logging.getLogger()
    if root.handlers:
        return

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            timestamper,
        ],
    )
    console_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(console_formatter)
    root.addHandler(handler)
    root.setLevel(level)

    observability_logger = logging.getLogger("observability.chat_llm")
    observability_logger.handlers.clear()
    obs_handler = logging.StreamHandler(sys.stdout)
    obs_handler.setFormatter(json_formatter)
    observability_logger.addHandler(obs_handler)
    observability_logger.propagate = False
    observability_logger.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
