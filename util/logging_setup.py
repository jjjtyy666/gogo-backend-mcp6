import logging
import os
import sys
from typing import Optional

__all__ = ["configure_logging", "get_logger"]

_DEFAULT_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
_configured = False


def configure_logging(level: Optional[str] = None, fmt: Optional[str] = None) -> None:
    """Configure the root logger only once (console handler)."""
    global _configured
    if _configured:
        return
    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, resolved_level, logging.INFO),
        format=fmt or _DEFAULT_FORMAT,
        stream=sys.stdout,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-specific logger after ensuring configuration."""
    configure_logging()
    return logging.getLogger(name)

