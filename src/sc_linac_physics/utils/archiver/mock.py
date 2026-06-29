"""Mock archiver data generator."""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Union

from .models import ArchiverValue, ArchiveDataHandler


def _stable_seed(pv_name: str, start_time: datetime, end_time: datetime) -> int:
    key = f"{pv_name}|{start_time.isoformat()}|{end_time.isoformat()}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:8], 16)


class MockArchiveDataHandler:
    """Generates mock time-series for one PV."""

    def __init__(
        self,
        pv_name: str,
        start_time: datetime,
        end_time: datetime,
        sample_rate_hz: float = 1.0,
    ):
        self.pv_name = pv_name
        self.start_time = start_time
        self.end_time = end_time
        self.sample_rate_hz = sample_rate_hz

        self.rng = random.Random(_stable_seed(pv_name, start_time, end_time))

        self.timestamps = self._generate_timestamps()
        self.values = self._generate_values()
        self.severities = self._generate_severities()
        self.statuses = self._generate_statuses()

    def _generate_timestamps(self) -> List[datetime]:
        timestamps: List[datetime] = []
        current = self.start_time
        interval = timedelta(seconds=1.0 / self.sample_rate_hz)

        while current <= self.end_time:
            timestamps.append(current)
            current += interval

        return timestamps

    def _generate_values(self) -> List[Union[float, int, str]]:
        pv = self.pv_name

        # Gradients
        if any(k in pv for k in ("ADES", "AACT", "GDES", "GACT", "AACTMEAN")):
            return self._generate_numeric_values(base_value=16.5, noise_range=0.1)

        # Phases
        if any(k in pv for k in ("PDES", "PACT")):
            return self._generate_numeric_values(base_value=0.0, noise_range=0.5)

        # Detune/df
        if any(k in pv for k in ("DF", "DETUNE")):
            return self._generate_numeric_values(base_value=0.0, noise_range=10.0)

        # Drive level-ish
        if "SEL_ASET" in pv:
            return self._generate_numeric_values(base_value=0.0, noise_range=0.5)

        # Status/fault PVs
        if "CUDSTATUS" in pv:
            # Keep as strings for now; adjust to ints if downstream expects numeric
            return self._generate_fault_codes()

        # Default
        return self._generate_numeric_values(base_value=0.0, noise_range=0.1)

    def _generate_numeric_values(self, base_value: float, noise_range: float) -> List[float]:
        values: List[float] = []
        for i in range(len(self.timestamps)):
            noise = self.rng.uniform(-noise_range, noise_range)
            drift = i * 0.00001

            if self.rng.random() < 0.02:
                fault_spike = self.rng.uniform(-5 * noise_range, 5 * noise_range)
                v = base_value + noise + drift + fault_spike
            else:
                v = base_value + noise + drift

            values.append(v)
        return values

    def _generate_fault_codes(self) -> List[str]:
        fault_codes = ["TLC", "Quench", "FPGA Fault", "No Fault"]
        values: List[str] = []
        for _ in self.timestamps:
            if self.rng.random() < 0.9:
                values.append("TLC")
            else:
                values.append(self.rng.choice(fault_codes))
        return values

    def _generate_severities(self) -> List[int]:
        severities: List[int] = []
        for _ in self.timestamps:
            if self.rng.random() < 0.9:
                severities.append(0)
            else:
                severities.append(self.rng.choice([1, 2]))
        return severities

    def _generate_statuses(self) -> List[int]:
        statuses: List[int] = []
        for _ in self.timestamps:
            if self.rng.random() < 0.95:
                statuses.append(0)
            else:
                statuses.append(1)
        return statuses


def mock_get_values_over_time_range(
    pv_list: List[str],
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, ArchiveDataHandler]:
    """Generate mock data for multiple PVs."""
    if not pv_list:
        return {}

    result: Dict[str, ArchiveDataHandler] = {}
    for pv_name in pv_list:
        mock = MockArchiveDataHandler(pv_name, start_time, end_time)

        archiver_values = [
            ArchiverValue(value=val, timestamp=ts, severity=sev, status=stat)
            for val, ts, sev, stat in zip(
                mock.values,
                mock.timestamps,
                mock.severities,
                mock.statuses,
            )
        ]
        result[pv_name] = ArchiveDataHandler.from_archiver_values(pv_name, archiver_values)

    return result