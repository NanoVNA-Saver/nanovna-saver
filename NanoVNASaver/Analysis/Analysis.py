#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
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

from PyQt5 import QtWidgets

logger = logging.getLogger(__name__)


class Analysis:
    _widget = None

    @classmethod
    def find_minimums(cls, data, threshold):
        '''

        Find values above threshold
        return list of tuples (start, lowest, end)
        indicating the index of data list


        :param cls:
        :param data: list of values
        :param threshold:
        '''

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

    def __init__(self, app: QtWidgets.QWidget):
        self.app = app

    def widget(self) -> QtWidgets.QWidget:
        return self._widget

    def runAnalysis(self):
        pass

    def reset(self):
        pass

    def calculateRolloff(self, location1, location2):
        if location1 == location2:
            return 0, 0
        frequency1 = self.app.data21[location1].freq
        frequency2 = self.app.data21[location2].freq
        gain1 = self.app.data21[location1].gain
        gain2 = self.app.data21[location2].gain
        frequency_factor = frequency2 / frequency1
        if frequency_factor < 1:
            frequency_factor = 1 / frequency_factor
        attenuation = abs(gain1 - gain2)
        logger.debug("Measured points: %d Hz and %d Hz",
                     frequency1, frequency2)
        logger.debug("%f dB over %f factor", attenuation, frequency_factor)
        octave_attenuation = attenuation / \
            (math.log10(frequency_factor) / math.log10(2))
        decade_attenuation = attenuation / math.log10(frequency_factor)
        return octave_attenuation, decade_attenuation
