"""Tests for mock archiver data generator."""

from datetime import datetime, timedelta
import pytest

from sc_linac_physics.utils.archiver.mock import (
    MockArchiveDataHandler,
    mock_get_values_over_time_range
)
from sc_linac_physics.utils.archiver.models import ArchiveDataHandler


def test_generate_timestamps_one_minute():
    """Test timestamp generation for 1-minute range at 1 Hz."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:ADES", start, end, sample_rate_hz=1.0)
    
    # 1 minute at 1 Hz = 60 samples (plus one for end point = 61)
    assert len(mock.timestamps) >= 60
    assert len(mock.timestamps) <= 61
    
    # First timestamp should be start
    assert mock.timestamps[0] == start
    
    # Last timestamp should be close to end
    assert abs((mock.timestamps[-1] - end).total_seconds()) < 1.0


def test_generate_timestamps_custom_sample_rate():
    """Test timestamp generation with 2 Hz sample rate."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 0, 10)  # 10 seconds
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:ADES", start, end, sample_rate_hz=2.0)
    
    # 10 seconds at 2 Hz = 20 samples (plus one = 21)
    assert len(mock.timestamps) >= 20
    assert len(mock.timestamps) <= 21


def test_generate_values_gradient():
    """Test value generation for gradient PV (ADES)."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:ADES", start, end)
    
    # All values should be near 16.5 MV
    assert len(mock.values) > 0
    assert all(isinstance(v, float) for v in mock.values)
    assert all(15.0 <= v <= 18.0 for v in mock.values), "Gradient values out of realistic range"
    
    # Check average is close to base value
    avg = sum(mock.values) / len(mock.values)
    assert 16.0 <= avg <= 17.0


def test_generate_values_phase():
    """Test value generation for phase PV (PDES)."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:PDES", start, end)
    
    # All values should be near 0 degrees
    assert len(mock.values) > 0
    assert all(isinstance(v, float) for v in mock.values)
    assert all(-5.0 <= v <= 5.0 for v in mock.values), "Phase values out of realistic range"


def test_generate_values_cudstatus():
    """Test value generation for fault code PV (CUDSTATUS)."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:CUDSTATUS", start, end)
    
    # All values should be strings
    assert len(mock.values) > 0
    assert all(isinstance(v, str) for v in mock.values)
    
    # Most should be "TLC" (normal state)
    tlc_count = sum(1 for v in mock.values if v == "TLC")
    assert tlc_count > len(mock.values) * 0.8, "Expected >80% TLC values"


def test_generate_values_detune():
    """Test value generation for detune PV (DF)."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:DF", start, end)
    
    # All values should be near 0 Hz
    assert len(mock.values) > 0
    assert all(isinstance(v, float) for v in mock.values)
    assert all(-50.0 <= v <= 50.0 for v in mock.values), "Detune values out of realistic range"


def test_generate_severities():
    """Test severity generation."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:ADES", start, end)
    
    # Most severities should be 0 (no alarm)
    assert len(mock.severities) == len(mock.values)
    assert all(isinstance(s, int) for s in mock.severities)
    assert all(0 <= s <= 2 for s in mock.severities)
    
    no_alarm_count = sum(1 for s in mock.severities if s == 0)
    assert no_alarm_count > len(mock.severities) * 0.8, "Expected >80% no-alarm"


def test_generate_statuses():
    """Test status generation."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    mock = MockArchiveDataHandler("ACCL:L1B:0110:ADES", start, end)
    
    assert len(mock.statuses) == len(mock.values)
    assert all(isinstance(s, int) for s in mock.statuses)
    assert all(s in [0, 1] for s in mock.statuses)


def test_mock_get_values_over_time_range_single_pv():
    """Test mock_get_values_over_time_range with single PV."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    result = mock_get_values_over_time_range(
        pv_list=["ACCL:L1B:0110:ADES"],
        start_time=start,
        end_time=end
    )
    
    # Should return dict with one key
    assert isinstance(result, dict)
    assert len(result) == 1
    assert "ACCL:L1B:0110:ADES" in result
    
    # Value should be ArchiveDataHandler
    handler = result["ACCL:L1B:0110:ADES"]
    assert isinstance(handler, ArchiveDataHandler)
    assert handler.pv_name == "ACCL:L1B:0110:ADES"
    assert len(handler.values) > 0
    assert len(handler.timestamps) == len(handler.values)
    assert len(handler.severities) == len(handler.values)
    assert len(handler.statuses) == len(handler.values)


def test_mock_get_values_over_time_range_multiple_pvs():
    """Test mock_get_values_over_time_range with multiple PVs."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    result = mock_get_values_over_time_range(
        pv_list=[
            "ACCL:L1B:0110:ADES",
            "ACCL:L1B:0110:PDES",
            "ACCL:L1B:0110:CUDSTATUS"
        ],
        start_time=start,
        end_time=end
    )
    
    # Should return dict with three keys
    assert len(result) == 3
    assert "ACCL:L1B:0110:ADES" in result
    assert "ACCL:L1B:0110:PDES" in result
    assert "ACCL:L1B:0110:CUDSTATUS" in result
    
    # All should be ArchiveDataHandler
    for pv_name, handler in result.items():
        assert isinstance(handler, ArchiveDataHandler)
        assert handler.pv_name == pv_name
        assert len(handler.values) > 0


def test_mock_get_values_over_time_range_empty_list():
    """Test mock_get_values_over_time_range with empty PV list."""
    start = datetime(2024, 1, 15, 12, 0, 0)
    end = datetime(2024, 1, 15, 12, 1, 0)
    
    result = mock_get_values_over_time_range(
        pv_list=[],
        start_time=start,
        end_time=end
    )
    
    assert isinstance(result, dict)
    assert len(result) == 0