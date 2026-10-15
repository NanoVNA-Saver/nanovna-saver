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
"""Marker search functions working on real valued traces."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import numpy.typing as npt
from scipy.signal import find_peaks

FloatArray = npt.NDArray[np.float64]


def search_min(y: FloatArray) -> int:
    return int(np.nanargmin(y))


def search_max(y: FloatArray) -> int:
    return int(np.nanargmax(y))


def _crossing(freq: FloatArray, y: FloatArray, i: int, target: float) -> float:
    """Interpolated frequency of the crossing between point i and i+1"""
    y0, y1 = y[i], y[i + 1]
    if y1 == y0:
        return float(freq[i])
    return float(freq[i] + (target - y0) * (freq[i + 1] - freq[i]) / (y1 - y0))


def search_target(
    freq: FloatArray,
    y: FloatArray,
    target: float,
    start_index: int = 0,
    direction: int = 1,
) -> Optional[float]:
    """Next frequency where the trace crosses target, searching from
    start_index in direction (+1 right, -1 left)."""
    s = np.sign(y - target)
    n = len(y)
    rng = (
        range(max(start_index, 0), n - 1)
        if direction > 0
        else range(min(start_index, n - 1) - 1, -1, -1)
    )
    for i in rng:
        if s[i] == 0:
            return float(freq[i])
        if s[i] != s[i + 1]:
            return _crossing(freq, y, i, target)
    return None


@dataclass
class BandwidthResult:
    center: float
    low: float
    high: float
    bandwidth: float
    q: float
    peak_index: int
    peak_value: float
    level: float


def search_bandwidth(
    freq: FloatArray, y: FloatArray, delta_db: float = -3.0, notch: bool = False
) -> Optional[BandwidthResult]:
    """Bandwidth around the maximum (filter) or minimum (notch,
    resonator). For a peak delta_db is negative (e.g. -3 dB), for a notch
    the level is peak + |delta_db|."""
    if len(y) < 3:
        return None
    idx = search_min(y) if notch else search_max(y)
    level = y[idx] + (abs(delta_db) if notch else -abs(delta_db))
    low = search_target(freq, y, level, idx, -1)
    high = search_target(freq, y, level, idx, 1)
    if low is None or high is None:
        return None
    bw = high - low
    center = float(np.sqrt(low * high)) if low > 0 else (low + high) / 2
    return BandwidthResult(
        center=center,
        low=low,
        high=high,
        bandwidth=bw,
        q=center / bw if bw > 0 else float("inf"),
        peak_index=idx,
        peak_value=float(y[idx]),
        level=float(level),
    )


def search_peaks(
    y: FloatArray, prominence: float = 3.0, minima: bool = False
) -> list[int]:
    """Indices of peaks (or minima) sorted by prominence"""
    data = -y if minima else y
    peaks, props = find_peaks(data, prominence=prominence)
    order = np.argsort(props["prominences"])[::-1]
    return [int(p) for p in peaks[order]]


def next_peak(
    y: FloatArray, current: int, direction: int, minima: bool = False
) -> Optional[int]:
    """Next local peak left (-1) or right (+1) of the current index"""
    peaks, _ = find_peaks(-y if minima else y)
    if direction > 0:
        right = peaks[peaks > current]
        return int(right[0]) if len(right) else None
    left = peaks[peaks < current]
    return int(left[-1]) if len(left) else None
