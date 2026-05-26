"""File-based logger. One main run log plus per-scraper error logs."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from config import LOG_DIR

_RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
_MAIN_LOG_PATH = LOG_DIR / f"run_{_RUN_TS}.log"


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to the per-run main log + stdout."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    fh = logging.FileHandler(_MAIN_LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    return logger


def get_scraper_error_logger(scraper_name: str) -> logging.Logger:
    """Per-scraper error log file. Use for site-specific failures."""
    logger = logging.getLogger(f"scraper.{scraper_name}.errors")
    if logger.handlers:
        return logger
    logger.setLevel(logging.WARNING)
    path = LOG_DIR / f"{scraper_name}_{_RUN_TS}.log"
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    logger.propagate = False
    return logger
