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
"""Trace processing: smoothing, running averaging, group delay."""

import math
from typing import Optional

import numpy as np
import numpy.typing as npt
from scipy.ndimage import uniform_filter1d

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]


def smoothing_window(n_points: int, aperture_pct: float) -> int:
    """Number of points (odd, >= 1) for a smoothing aperture given in
    percent of the span, like on bench top VNAs."""
    if aperture_pct <= 0 or n_points < 3:
        return 1
    width = round(n_points * aperture_pct / 100.0)
    width = max(1, min(width, n_points))
    if width % 2 == 0:
        width -= 1
    return max(width, 1)


def smooth(values: ComplexArray, aperture_pct: float) -> ComplexArray:
    """Moving average across frequency on the complex values.

    Smoothing the complex values keeps magnitude, phase and Smith views
    consistent. Edges use the nearest value for padding."""
    values = np.asarray(values, dtype=np.complex128)
    width = smoothing_window(len(values), aperture_pct)
    if width <= 1:
        return values.copy()
    re = uniform_filter1d(values.real, size=width, mode="nearest")
    im = uniform_filter1d(values.imag, size=width, mode="nearest")
    return re + 1j * im


class RunningAverage:
    """Exponential running average for continuous sweeps.

    The first `count` sweeps are averaged uniformly, after that every
    new sweep is weighted with 1/count (same behaviour as the averaging
    of bench top VNAs)."""

    def __init__(self, count: int = 1) -> None:
        self.count = max(1, int(count))
        self.n = 0
        self._avg: Optional[ComplexArray] = None

    def reset(self) -> None:
        self.n = 0
        self._avg = None

    def set_count(self, count: int) -> None:
        count = max(1, int(count))
        if count != self.count:
            self.count = count
            self.reset()

    @property
    def value(self) -> Optional[ComplexArray]:
        return self._avg

    def add(self, values: ComplexArray) -> ComplexArray:
        values = np.asarray(values, dtype=np.complex128)
        if self._avg is None or self._avg.shape != values.shape:
            self.n = 1
            self._avg = values.copy()
            return self._avg.copy()
        self.n = min(self.n + 1, self.count)
        self._avg = self._avg + (values - self._avg) / self.n
        return self._avg.copy()


class SegmentRunningAverage:
    """Running average for a sweep that is acquired in segments.

    Every segment keeps its own counter, so the average stays correct
    when the sweep is updated piece by piece."""

    def __init__(self, count: int = 1) -> None:
        self.count = max(1, int(count))
        self._segments: dict[int, RunningAverage] = {}

    def reset(self) -> None:
        self._segments = {}

    def set_count(self, count: int) -> None:
        count = max(1, int(count))
        if count != self.count:
            self.count = count
            self.reset()

    def add(self, segment: int, values: ComplexArray) -> ComplexArray:
        avg = self._segments.setdefault(segment, RunningAverage(self.count))
        return avg.add(values)

    @property
    def n(self) -> int:
        """Number of sweeps currently in the average (minimum over all
        segments)"""
        if not self._segments:
            return 0
        return min(a.n for a in self._segments.values())


def unwrap_phase(values: ComplexArray) -> FloatArray:
    """Unwrapped phase in radians"""
    return np.unwrap(np.angle(np.asarray(values, dtype=np.complex128)))


def group_delay(
    freq: FloatArray, values: ComplexArray, aperture_points: int = 1
) -> FloatArray:
    """Group delay in seconds, -dphi/domega over +-aperture points."""
    freq = np.asarray(freq, dtype=np.float64)
    n = len(freq)
    if n < 2:
        return np.zeros(n)
    phase = unwrap_phase(values)
    a = max(1, int(aperture_points))
    idx = np.arange(n)
    lo = np.clip(idx - a, 0, n - 1)
    hi = np.clip(idx + a, 0, n - 1)
    df = freq[hi] - freq[lo]
    dphi = phase[hi] - phase[lo]
    with np.errstate(divide="ignore", invalid="ignore"):
        gd = np.where(df != 0, -dphi / (2 * math.pi * df), 0.0)
    return gd


def group_delay_aperture_points(n_points: int, aperture_pct: float) -> int:
    """Half aperture in points for a group delay aperture in percent of
    the span."""
    if aperture_pct <= 0:
        return 1
    return max(1, round(n_points * aperture_pct / 200.0))
