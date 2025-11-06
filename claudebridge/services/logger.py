"""
Centralized logging for ClaudeBridge using loguru library
Sets 3 levels: INFO, DEBUG, TRACE
Configured via DEBUG environment variable with default depending if prod or dev build
"""

# TODO: Add option to switch to logfmt
# FIX: Bad coloring of logger

import os
import sys

from loguru import logger

logger.remove()

LOG_LEVEL = os.getenv("DEBUG", "debug").upper()

LEVEL_MAP = {"INFO": "INFO", "DEBUG": "DEBUG", "TRACE": "TRACE"}

log_level = LEVEL_MAP.get(LOG_LEVEL, "DEBUG")

logger.level("INFO", icon="ℹ️", color="<white><bg #2563eb>")
logger.level("DEBUG", icon="🔍", color="<white><bg #9333ea>")
logger.level("TRACE", icon="🔬", color="<white><bg #06b6d4>")

# colorized handler with dramatic formatting
logger.add(
    sys.stdout,
    colorize=True,
    format=(
        "<bg #000000><white>🕐 {time:YYYY-MM-DD HH:mm:ss}</white></bg #000000> | "
        "<level>{level.icon} {level: <8}</level> | "
        "<bg #f97316><white>📄 {name}:{function}:{line}</white></bg #f97316> - "
        "{message}"
    ),
    level=log_level,
    serialize=False,
)

__all__ = ["logger"]
