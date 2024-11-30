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

import numpy as np
from PyQt6 import QtWidgets

# pylint: disable=import-error, no-name-in-module
from scipy.signal import find_peaks, peak_prominences

from NanoVNASaver.Analysis.Base import QHLine
from NanoVNASaver.Analysis.SimplePeakSearchAnalysis import (
    SimplePeakSearchAnalysis,
)
from NanoVNASaver.Formatting import format_frequency_short

logger = logging.getLogger(__name__)


class PeakSearchAnalysis(SimplePeakSearchAnalysis):
    def __init__(self, app):
        super().__init__(app)

        self.peak_cnt = QtWidgets.QSpinBox()
        self.peak_cnt.setValue(1)
        self.peak_cnt.setMinimum(1)
        self.peak_cnt.setMaximum(10)

        self.layout.addRow("Max number of peaks", self.peak_cnt)
        self.layout.addRow(QHLine())
        self.layout.addRow(QtWidgets.QLabel("<b>Results</b>"))
        self.results_header = self.layout.rowCount()

        self.set_titel("Peak search")

    def runAnalysis(self):
        if not self.app.data.s11:
            return
        self.reset()

        s11 = self.app.data.s11
        data, fmt_fnc = self.data_and_format()

        inverted = False
        if self.button["peak_l"].isChecked():
            inverted = True
            peaks, _ = find_peaks(
                -np.array(data), width=3, distance=3, prominence=1
            )
        else:
            self.button["peak_h"].setChecked(True)
            peaks, _ = find_peaks(data, width=3, distance=3, prominence=1)

        # Having found the peaks, get the prominence data
        for i, p in np.ndenumerate(peaks):
            logger.debug("Peak %s at %s", i, p)
        prominences = peak_prominences(data, peaks)[0]
        logger.debug("%d prominences", len(prominences))

        # Find the peaks with the most extreme values
        # Alternately, allow the user to select "most prominent"?
        count = self.peak_cnt.value()
        if count > len(prominences):
            count = len(prominences)
            self.peak_cnt.setValue(count)

        indices = np.argpartition(prominences, -count)[-count:]
        logger.debug("%d indices", len(indices))
        for i in indices:
            pos = peaks[i]
            self.layout.addRow(
                f"Freq: {format_frequency_short(s11[pos].freq)}",
                QtWidgets.QLabel(
                    f" Value: {fmt_fnc(-data[pos] if inverted else data[pos])}"
                ),
            )

        if self.button["move_marker"].isChecked():
            if count > len(self.app.markers):
                logger.warning("More peaks found than there are markers")
            for i in range(min(count, len(self.app.markers))):
                self.app.markers[i].setFrequency(
                    str(s11[peaks[indices[i]]].freq)
                )

    def reset(self):
        super().reset()
        logger.debug(
            "Results start at %d, out of %d",
            self.results_header,
            self.layout.rowCount(),
        )
        for _ in range(self.results_header, self.layout.rowCount()):
            logger.debug("deleting %s", self.layout.rowCount())
            self.layout.removeRow(self.layout.rowCount() - 1)
