"""
Smart archiver routing wrapper.

Public API:
- get_values_over_time_range(...)
- start_mock_archiver()

Routing:
- If SC_ARCHIVER_MOCK=1 -> always mock
- If start_mock_archiver() called -> always mock
- Else if real archiver unreachable -> mock
- Else try real -> fallback to mock on ArchiverError subclasses
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, List

import logging
from .models import ArchiveDataHandler, ArchiverValue
from .mock import mock_get_values_over_time_range
from .client import (
    real_get_values_over_time_range,
    is_archiver_available,
    ArchiverConnectionError,
    ArchiverTimeoutError,
    ArchiverError,
)

__all__ = [
    "ArchiveDataHandler",
    "ArchiverValue",
    "ArchiverError",
    "ArchiverTimeoutError",
    "ArchiverConnectionError",
    "start_mock_archiver",
    "get_values_over_time_range",
    # Expose these for test patching / debug:
    "is_archiver_available",
    "real_get_values_over_time_range",
]

_mock_archiver_enabled = False


def start_mock_archiver() -> None:
    """Enable mock archiver mode (e.g., called by sc-sim)."""
    global _mock_archiver_enabled
    _mock_archiver_enabled = True


def _should_force_mock() -> bool:
    if os.getenv("SC_ARCHIVER_MOCK") == "1":
        return True
    if _mock_archiver_enabled:
        return True
    return False

logger = logging.getLogger(__name__)

def get_values_over_time_range(
    pv_list: List[str],
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, ArchiveDataHandler]:
    """
    Get historical PV data over a time range.

    Returns:
        Dict[pv_name, ArchiveDataHandler]
    """
    if not pv_list:
        return {}

    if _should_force_mock():
        logger.debug("Using mock archiver (forced mode)")
        return mock_get_values_over_time_range(pv_list, start_time, end_time)

    # Quick connectivity check (patched in tests)
    if not is_archiver_available():
        logger.debug("Archiver unavailable, using mock")
        return mock_get_values_over_time_range(pv_list, start_time, end_time)

    try:
        logger.debug("Fetching from real archiver")
        return real_get_values_over_time_range(pv_list, start_time, end_time)
    except (ArchiverConnectionError, ArchiverTimeoutError, ArchiverError) as e:
        # In auto mode, fallback to mock if anything archiver-related fails
        logger.warning(f"Real archiver failed: {e}, falling back to mock")
        return mock_get_values_over_time_range(pv_list, start_time, end_time)