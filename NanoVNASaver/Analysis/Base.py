#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
import logging
import math
from typing import Tuple

import numpy as np
import scipy
from PyQt5 import QtWidgets


logger = logging.getLogger(__name__)


class QHLine(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)


class Analysis:
    _widget = None

    @classmethod
    def find_crossing_zero(cls, data):
        """

        Find values  crossing zero
        return list of tuples (before, crossing, after)
        indicating the index of data list
        crossing is where data == 0
        or data nearest 0

        at maximum 1 value == 0
        data must not start or end with 0


        :param cls:
        :param data: list of values
        """
        my_data = np.array(data)
        zeroes = np.where(my_data == 0)[0]

        if 0 in zeroes:
            raise ValueError("Data  must non start with 0")

        if len(data) - 1 in zeroes:
            raise ValueError("Data  must non end with 0")
        crossing = [(n - 1, n, n + 1) for n in zeroes]

        for n in np.where((my_data[:-1] * my_data[1:]) < 0)[0]:
            if abs(data[n]) <= abs(data[n + 1]):
                crossing.append((n, n, n + 1))
            else:
                crossing.append((n, n + 1, n + 1))

        return crossing

    @classmethod
    def find_minimums(cls, data, threshold):
        """

        Find values above threshold
        return list of tuples (start, lowest, end)
        indicating the index of data list


        :param cls:
        :param data: list of values
        :param threshold:
        """

        minimums = []
        min_start = -1
        min_idx = -1

        min_val = threshold
        for i, d in enumerate(data):
            if d < threshold and i < len(data) - 1:
                if d < min_val:
                    min_val = d
                    min_idx = i
                if min_start == -1:
                    min_start = i
            elif min_start != -1:
                # We are above the threshold, and were in a section that was
                # below
                minimums.append((min_start, min_idx, i - 1))
                min_start = -1
                min_idx = -1
                min_val = threshold
        return minimums

    @classmethod
    def find_maximums(cls, data, threshold=None):
        """

        Find peacs


        :param cls:
        :param data: list of values
        :param threshold:
        """
        peaks, _ = scipy.signal.find_peaks(
            data, width=2, distance=3, prominence=1)

#         my_data = np.array(data)
#         maximums = argrelextrema(my_data, np.greater)[0]
        if threshold is None:
            return peaks
        return [k for k in peaks if data[k] > threshold]

    def __init__(self, app: QtWidgets.QWidget):
        self.app = app

    def widget(self) -> QtWidgets.QWidget:
        return self._widget

    def runAnalysis(self):
        pass

    def reset(self):
        pass

    def calculateRolloff(self, idx_1: int, idx_2: int) -> Tuple[float, float]:
        if idx_1 == idx_2:
            return (math.nan, math.nan)
        s21 = self.app.data.s21
        freq_1 = s21[idx_1].freq
        freq_2 = s21[idx_2].freq
        gain1 = s21[idx_1].gain
        gain2 = s21[idx_2].gain
        factor = freq_1 / freq_2 if freq_1 > freq_2 else freq_2 / freq_1
        attn = abs(gain1 - gain2)
        logger.debug("Measured points: %d Hz and %d Hz\n%fdB over %f factor",
                     freq_1, freq_2, attn, factor)
        octave_attn = attn / (math.log10(factor) / math.log10(2))
        decade_attn = attn / math.log10(factor)
        return (octave_attn, decade_attn)
