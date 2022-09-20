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

from PyQt5 import QtWidgets
import scipy
import numpy as np

from NanoVNASaver.Analysis.Base import QHLine
from NanoVNASaver.Analysis.SimplePeakSearchAnalysis import (
    SimplePeakSearchAnalysis)

from NanoVNASaver.Formatting import format_vswr
from NanoVNASaver.Formatting import format_gain
from NanoVNASaver.Formatting import format_resistance
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

        self.set_titel('Peak search')

    def runAnalysis(self):
        if not self.app.data.s11:
            return
        self.reset()

        s11 = self.app.data.s11
        s21 = self.app.data.s21

        if not s21:
            self.button['gain'].setEnabled(False)
            if self.button['gain'].isChecked():
                self.button['vswr'].setChecked(True)
        else:
            self.button['gain'].setEnabled(True)

        count = self.peak_cnt.value()
        if self.button['vswr'].isChecked():
            fn = format_vswr
            data = [d.vswr for d in s11]
        elif self.button['gain'].isChecked():
            fn = format_gain
            data = [d.gain for d in s21]
        elif self.button['resistance'].isChecked():
            fn = format_resistance
            data = [d.impedance().real for d in s11]
        elif self.button['reactance'].isChecked():
            fn = format_resistance
            data = [d.impedance().imag for d in s11]
        else:
            logger.warning("Searching for peaks on unknown data")
            return

        sign = 1
        if self.button['peak_h'].isChecked():
            peaks, _ = scipy.signal.find_peaks(
                data, width=3, distance=3, prominence=1)
        elif self.button['peak_l'].isChecked():
            sign = -1
            data = [x * sign for x in data]
            peaks, _ = scipy.signal.find_peaks(
                data, width=3, distance=3, prominence=1)
        else:
            # Both is not yet in
            logger.warning(
                "Searching for peaks,"
                " but neither looking at positive nor negative?")
            return

        # Having found the peaks, get the prominence data

        for i, p in np.ndenumerate(peaks):
            logger.debug("Peak %i at %d", i, p)
        prominences = scipy.signal.peak_prominences(data, peaks)[0]
        logger.debug("%d prominences", len(prominences))

        # Find the peaks with the most extreme values
        # Alternately, allow the user to select "most prominent"?
        indices = np.argpartition(prominences, -count)[-count:]
        logger.debug("%d indices", len(indices))
        for i in indices:
            logger.debug("Index %d", i)
            logger.debug("Prominence %f", prominences[i])
            logger.debug("Index in sweep %d", peaks[i])
            logger.debug("Frequency %d", s11[peaks[i]].freq)
            logger.debug("Value %f", sign * data[peaks[i]])
            self.layout.addRow(
                f"Freq"
                f" {format_frequency_short(s11[peaks[i]].freq)}",
                QtWidgets.QLabel(f" value {fn(sign * data[peaks[i]])}"
                                 ))

        if self.button['move_marker'].isChecked():
            if count > len(self.app.markers):
                logger.warning("More peaks found than there are markers")
            for i in range(min(count, len(self.app.markers))):
                self.app.markers[i].setFrequency(
                    str(s11[peaks[indices[i]]].freq))

        max_val = -10**10
        max_idx = -1
        for p in peaks:
            if data[p] > max_val:
                max_val = data[p]
                max_idx = p

        logger.debug("Max peak at %d, value %f", max_idx, max_val)

    def reset(self):
        logger.debug("Reset analysis")

        logger.debug("Results start at %d, out of %d",
                     self.results_header, self.layout.rowCount())
        for _ in range(self.results_header, self.layout.rowCount()):
            logger.debug("deleting %s", self.layout.rowCount())
            self.layout.removeRow(self.layout.rowCount() - 1)
