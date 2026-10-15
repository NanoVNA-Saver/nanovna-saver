#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Limit lines and pass / fail testing.

Example limit file::

    {
      "name": "WiFi antenna",
      "limits": [
        {"param": "s11", "format": "logmag", "type": "upper",
         "start": 2.4e9, "stop": 2.5e9, "value": -10},
        {"param": "s21", "format": "logmag", "type": "lower",
         "start": 1e9, "stop": 2e9, "value": -1, "value_stop": -3}
      ]
    }
"""

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from .formats import TraceFormat, convert
from .sweepdata import SweepData


@dataclass
class LimitSegment:
    param: str = "s11"
    format: str = "logmag"
    type: str = "upper"  # upper: value must be <= limit, lower: >= limit
    start: float = 0.0
    stop: float = 0.0
    value: float = 0.0
    value_stop: Optional[float] = None  # sloped limit when given

    def __post_init__(self) -> None:
        if self.type not in ("upper", "lower"):
            raise ValueError(f"Limit type must be upper or lower: {self.type}")
        if self.stop < self.start:
            self.start, self.stop = self.stop, self.start
        TraceFormat(self.format)  # validate

    @property
    def trace_format(self) -> TraceFormat:
        return TraceFormat(self.format)

    def limit_at(self, freq: np.ndarray) -> np.ndarray:
        end = self.value if self.value_stop is None else self.value_stop
        if self.stop == self.start:
            return np.full_like(freq, self.value, dtype=np.float64)
        return self.value + (end - self.value) * (freq - self.start) / (
            self.stop - self.start
        )

    def describe(self) -> str:
        sign = "≤" if self.type == "upper" else "≥"
        end = "" if self.value_stop is None else f"..{self.value_stop:g}"
        return (
            f"{self.param.upper()} {self.trace_format.label} {sign}"
            f" {self.value:g}{end} {self.trace_format.unit}"
            f" ({self.start / 1e6:g}-{self.stop / 1e6:g} MHz)"
        )


@dataclass
class SegmentResult:
    segment: LimitSegment
    passed: bool
    points: int
    failed_points: int
    worst_margin: float  # >0 good, <0 violation (in format units)
    worst_freq: float
    worst_value: float
    skipped: bool = False


@dataclass
class LimitResult:
    name: str
    passed: bool
    segments: list[SegmentResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def summary(self) -> str:
        lines = [f"{self.name}: {'PASS' if self.passed else 'FAIL'}"]
        for r in self.segments:
            state = "SKIP" if r.skipped else ("pass" if r.passed else "FAIL")
            lines.append(
                f"  [{state}] {r.segment.describe()}"
                + (
                    ""
                    if r.skipped
                    else f" worst margin {r.worst_margin:+.3g}"
                    f" @ {r.worst_freq / 1e6:.6g} MHz"
                )
            )
        return "\n".join(lines)


@dataclass
class LimitSpec:
    name: str = "Limits"
    limits: list[LimitSegment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> "LimitSpec":
        return cls(
            name=raw.get("name", "Limits"),
            limits=[LimitSegment(**seg) for seg in raw.get("limits", [])],
        )

    @classmethod
    def load(cls, path: str | Path) -> "LimitSpec":
        return cls.from_dict(json.loads(Path(path).read_text("utf-8")))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "limits": [
                {k: v for k, v in asdict(s).items() if v is not None}
                for s in self.limits
            ],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), "utf-8")

    def evaluate(self, data: SweepData) -> LimitResult:
        results = [evaluate_segment(seg, data) for seg in self.limits]
        passed = all(r.passed for r in results if not r.skipped) and any(
            not r.skipped for r in results
        )
        return LimitResult(self.name, passed, results)


def evaluate_segment(seg: LimitSegment, data: SweepData) -> SegmentResult:
    values = data.param(seg.param)
    mask = (data.freq >= seg.start) & (data.freq <= seg.stop)
    if values is None or not np.any(mask):
        return SegmentResult(seg, True, 0, 0, np.inf, 0.0, 0.0, skipped=True)
    trace = convert(seg.trace_format, data.freq, values, data.z0)
    trace = np.real(trace[mask])
    freq = data.freq[mask]
    limit = seg.limit_at(freq)
    margin = limit - trace if seg.type == "upper" else trace - limit
    worst = int(np.argmin(margin))
    failed = int(np.sum(margin < 0))
    return SegmentResult(
        segment=seg,
        passed=failed == 0,
        points=len(freq),
        failed_points=failed,
        worst_margin=float(margin[worst]),
        worst_freq=float(freq[worst]),
        worst_value=float(trace[worst]),
    )


def log_result(
    path: str | Path, result: LimitResult, serial: str = "", note: str = ""
) -> None:
    """Append a test result to a CSV log"""
    path = Path(path)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new:
            writer.writerow(
                [
                    "timestamp",
                    "serial",
                    "spec",
                    "result",
                    "worst_margin",
                    "worst_freq_hz",
                    "note",
                ]
            )
        checked = [r for r in result.segments if not r.skipped]
        worst = min(checked, key=lambda r: r.worst_margin, default=None)
        writer.writerow(
            [
                result.timestamp.isoformat(timespec="seconds"),
                serial,
                result.name,
                "PASS" if result.passed else "FAIL",
                "" if worst is None else f"{worst.worst_margin:.4g}",
                "" if worst is None else f"{worst.worst_freq:.0f}",
                note,
            ]
        )
