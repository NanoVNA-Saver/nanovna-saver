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
from typing import Callable, List
import itertools as it

import numpy as np
import scipy


def zero_crossings(data: List[float]) -> List[int]:
    """find zero crossings

    Args:
        data (List[float]): data list execute

    Returns:
        List[int]: sorted indices of zero crossing points
    """
    if not data:
        return []

    np_data = np.array(data)

    # start with real zeros (ignore first and last element)
    real_zeros = [n for n in np.where(np_data == 0.0)[0] if
                  n not in {0, np_data.size - 1}]
    # now multipy elements to find change in signess
    crossings = [
        n if abs(np_data[n]) < abs(np_data[n + 1]) else n + 1
        for n in np.where((np_data[:-1] * np_data[1:]) < 0.0)[0]
    ]
    return sorted(real_zeros + crossings)


def maxima(data: List[float], threshold: float = 0.0) -> List[int]:
    """maxima

    Args:
        data (List[float]): data list to execute

    Returns:
        List[int]: indices of maxima
    """
    peaks, _ = scipy.signal.find_peaks(
        data, width=2, distance=3, prominence=1)
    return [
        i for i in peaks if data[i] > threshold
    ] if threshold else peaks


def minima(data: List[float], threshold: float = 0.0) -> List[int]:
    """minima

    Args:
        data (List[float]): data list to execute

    Returns:
        List[int]: indices of minima
    """
    bottoms, _ = scipy.signal.find_peaks(
        -np.array(data), width=2, distance=3, prominence=1)
    return [
        i for i in bottoms if data[i] < threshold
    ] if threshold else bottoms


def take_from_center(data: List[float],
                     center: int,
                     predicate: Callable) -> List[int]:
    """take_from_center

    Args:
        data (List[float]): data list to execute
        center (int): index of a center position
        predicate (Callable): predicate on which elements to take
            from center. (e.g. lambda i: i[1] < threshold)

    Returns:
        List[int]: indices of element matching predicate left
                   and right from center
    """
    lower = list(reversed(
        [i for i, _ in
         it.takewhile(predicate,
                      reversed(list(enumerate(data[:center]))))]))
    upper = [i for i, _ in
             it.takewhile(predicate, enumerate(data[center:], center))]
    return lower + upper
