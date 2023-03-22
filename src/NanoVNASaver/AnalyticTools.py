#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020 Rune B. Broberg
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
import itertools as it
import math
from typing import Callable

import numpy as np

# pylint: disable=import-error, no-name-in-module
from scipy.signal import find_peaks

from NanoVNASaver.RFTools import Datapoint


def zero_crossings(data: list[float]) -> list[int]:
    """find zero crossings

    Args:
        data (list[float]): data list execute

    Returns:
        list[int]: sorted indices of zero crossing points
    """
    if not data:
        return []

    np_data = np.array(data)

    # start with real zeros (ignore first and last element)
    real_zeros = [
        n for n in np.where(np_data == 0.0)[0] if n not in {0, np_data.size - 1}
    ]
    # now multipy elements to find change in signess
    crossings = [
        n if abs(np_data[n]) < abs(np_data[n + 1]) else n + 1
        for n in np.where((np_data[:-1] * np_data[1:]) < 0.0)[0]
    ]
    return sorted(real_zeros + crossings)


def maxima(data: list[float], threshold: float = 0.0) -> list[int]:
    """maxima

    Args:
        data (list[float]): data list to execute

    Returns:
        list[int]: indices of maxima
    """
    peaks = find_peaks(data, width=2, distance=3, prominence=1)[0].tolist()
    return [i for i in peaks if data[i] > threshold] if threshold else peaks


def minima(data: list[float], threshold: float = 0.0) -> list[int]:
    """minima

    Args:
        data (list[float]): data list to execute

    Returns:
        list[int]: indices of minima
    """
    bottoms = find_peaks(-np.array(data), width=2, distance=3, prominence=1)[
        0
    ].tolist()
    return [i for i in bottoms if data[i] < threshold] if threshold else bottoms


def take_from_idx(
    data: list[float], idx: int, predicate: Callable
) -> list[int]:
    """take_from_center

    Args:
        data (list[float]): data list to execute
        idx (int): index of a start position
        predicate (Callable): predicate on which elements to take
            from center. (e.g. lambda i: i[1] < threshold)

    Returns:
        list[int]: indices of element matching predicate left
                   and right from index
    """
    lower = list(
        reversed(
            [
                i
                for i, _ in it.takewhile(
                    predicate, reversed(list(enumerate(data[:idx])))
                )
            ]
        )
    )
    upper = [i for i, _ in it.takewhile(predicate, enumerate(data[idx:], idx))]
    return lower + upper


def center_from_idx(gains: list[float], idx: int, delta: float = 3.0) -> int:
    """find maximum from index postion of gains in a attn dB gain span

    Args:
        gains (list[float]): gain values
        idx (int): start position to search from
        delta (float, optional): max gain delta from start. Defaults to 3.0.

    Returns:
        int: position of highest gain from start in range (-1 if no data)
    """
    peak_db = gains[idx]
    rng = take_from_idx(gains, idx, lambda i: abs(peak_db - i[1]) < delta)
    return max(rng, key=lambda i: gains[i]) if rng else -1


def cut_off_left(
    gains: list[float], idx: int, peak_gain: float, attn: float = 3.0
) -> int:
    """find first position in list where gain in attn lower then peak
    left from index

    Args:
        gains (list[float]): gain values
        idx (int): start position to search from
        peak_gain (float): reference gain value
        attn (float, optional): attenuation to search position for.
                                Defaults to 3.0.

    Returns:
        int: position of attenuation point. (-1 if no data)
    """
    return next(
        (i for i in range(idx, -1, -1) if (peak_gain - gains[i]) > attn), -1
    )


def cut_off_right(
    gains: list[float], idx: int, peak_gain: float, attn: float = 3.0
) -> int:
    """find first position in list where gain in attn lower then peak
    right from index

    Args:
        gains (list[float]): gain values
        idx (int): start position to search from
        peak_gain (float): reference gain value
        attn (float, optional): attenuation to search position for.
                                Defaults to 3.0.

    Returns:
        int: position of attenuation point. (-1 if no data)
    """

    return next(
        (i for i in range(idx, len(gains)) if (peak_gain - gains[i]) > attn), -1
    )


def dip_cut_offs(
    gains: list[float], peak_gain: float, attn: float = 3.0
) -> tuple[int, int]:
    rng = np.where(np.array(gains) < (peak_gain - attn))[0].tolist()
    return (rng[0], rng[-1]) if rng else (math.nan, math.nan)


def calculate_rolloff(
    s21: list[Datapoint], idx_1: int, idx_2: int
) -> tuple[float, float]:
    if idx_1 == idx_2:
        return (math.nan, math.nan)
    freq_1, freq_2 = s21[idx_1].freq, s21[idx_2].freq
    gain_1, gain_2 = s21[idx_1].gain, s21[idx_2].gain
    factor = freq_1 / freq_2 if freq_1 > freq_2 else freq_2 / freq_1
    attn = abs(gain_1 - gain_2)
    decade_attn = attn / math.log10(factor)
    octave_attn = decade_attn * math.log10(2)
    return (octave_attn, decade_attn)
