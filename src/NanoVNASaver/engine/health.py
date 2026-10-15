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
"""Calibration health checks."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Optional

import numpy as np

from ..Calibration import Calibration
from .formats import logmag

DEFAULT_MAX_AGE = timedelta(hours=8)


class Severity(IntEnum):
    OK = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


@dataclass
class Issue:
    severity: Severity
    message: str


@dataclass
class HealthReport:
    issues: list[Issue] = field(default_factory=list)

    @property
    def severity(self) -> Severity:
        return max((i.severity for i in self.issues), default=Severity.OK)

    def add(self, severity: Severity, message: str) -> None:
        self.issues.append(Issue(severity, message))

    def summary(self) -> str:
        if not self.issues:
            return "Calibration OK"
        return "\n".join(
            f"[{i.severity.name}] {i.message}" for i in self.issues
        )


def check_calibration(
    cal: Calibration,
    sweep_freq: Optional[np.ndarray] = None,
    now: Optional[datetime] = None,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> HealthReport:
    report = HealthReport()
    if not cal.isCalculated:
        report.add(
            Severity.WARNING,
            "No application calibration active (device calibration used)",
        )
        return report
    now = now or datetime.now()
    if cal.created is not None:
        age = now - cal.created
        if age > max_age:
            hours = age.total_seconds() / 3600
            report.add(
                Severity.WARNING,
                f"Calibration is {hours:.1f} h old. Temperature drift and"
                " cable movement degrade accuracy - recalibrate.",
            )
    f_min, f_max = cal.freq_range()
    if sweep_freq is not None and len(sweep_freq):
        s_min, s_max = float(np.min(sweep_freq)), float(np.max(sweep_freq))
        if s_min < f_min or s_max > f_max:
            report.add(
                Severity.ERROR,
                f"Sweep {s_min / 1e6:.6g}-{s_max / 1e6:.6g} MHz exceeds the"
                f" calibrated range {f_min / 1e6:.6g}-{f_max / 1e6:.6g} MHz."
                " Values outside are extrapolated and wrong.",
            )
        inside = (sweep_freq >= f_min) & (sweep_freq <= f_max)
        n_sweep = int(np.sum(inside))
        if cal.size() < n_sweep / 2:
            report.add(
                Severity.INFO,
                f"Calibration has {cal.size()} points, sweep {n_sweep}."
                " Error terms are interpolated; calibrate with the"
                " measurement settings for best accuracy.",
            )
    if not cal.isValid2Port():
        report.add(
            Severity.INFO,
            "1-port calibration only: S21 is uncorrected for tracking.",
        )
    return report


@dataclass
class VerifyResult:
    standard: str
    passed: bool
    worst: float
    message: str


def verify_standard(
    s11_corrected: np.ndarray, standard: str = "load"
) -> VerifyResult:
    """Verify a corrected measurement of a known standard.

    load: return loss must be better than 30 dB (warn below 20 dB)
    open/short: |S11| must be within 0.5 dB of 0 dB"""
    s11 = np.asarray(s11_corrected, dtype=np.complex128)
    if len(s11) == 0:
        return VerifyResult(standard, False, np.nan, "No data")
    db = logmag(s11)
    if standard == "load":
        worst = float(np.max(db))
        passed = worst < -30
        level = "good" if passed else ("marginal" if worst < -20 else "bad")
        return VerifyResult(
            standard,
            passed,
            worst,
            f"Load verification {level}: worst return loss {-worst:.1f} dB"
            " (expect > 30 dB)",
        )
    worst = float(np.max(np.abs(db)))
    passed = worst < 0.5
    return VerifyResult(
        standard,
        passed,
        worst,
        f"{standard.capitalize()} verification"
        f" {'good' if passed else 'bad'}: |S11| deviates up to"
        f" {worst:.2f} dB from 0 dB (expect < 0.5 dB)",
    )
