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

from PyQt5 import QtWidgets
from scipy import signal
import numpy as np

from NanoVNASaver.Analysis import Analysis


logger = logging.getLogger(__name__)


class PeakSearchAnalysis(Analysis):
    class QHLine(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setFrameShape(QtWidgets.QFrame.HLine)

    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()
        outer_layout = QtWidgets.QFormLayout()
        self._widget.setLayout(outer_layout)

        self.rbtn_data_group = QtWidgets.QButtonGroup()
        self.rbtn_data_vswr = QtWidgets.QRadioButton("VSWR")
        self.rbtn_data_resistance = QtWidgets.QRadioButton("Resistance")
        self.rbtn_data_reactance = QtWidgets.QRadioButton("Reactance")
        self.rbtn_data_s21_gain = QtWidgets.QRadioButton("S21 Gain")
        self.rbtn_data_group.addButton(self.rbtn_data_vswr)
        self.rbtn_data_group.addButton(self.rbtn_data_resistance)
        self.rbtn_data_group.addButton(self.rbtn_data_reactance)
        self.rbtn_data_group.addButton(self.rbtn_data_s21_gain)

        self.rbtn_data_vswr.setChecked(True)

        self.rbtn_peak_group = QtWidgets.QButtonGroup()
        self.rbtn_peak_positive = QtWidgets.QRadioButton("Positive")
        self.rbtn_peak_negative = QtWidgets.QRadioButton("Negative")
        self.rbtn_peak_both = QtWidgets.QRadioButton("Both")
        self.rbtn_peak_group.addButton(self.rbtn_peak_positive)
        self.rbtn_peak_group.addButton(self.rbtn_peak_negative)
        self.rbtn_peak_group.addButton(self.rbtn_peak_both)

        self.rbtn_peak_positive.setChecked(True)

        self.input_number_of_peaks = QtWidgets.QSpinBox()
        self.input_number_of_peaks.setValue(1)
        self.input_number_of_peaks.setMinimum(1)
        self.input_number_of_peaks.setMaximum(10)

        self.checkbox_move_markers = QtWidgets.QCheckBox()

        outer_layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        outer_layout.addRow("Data source", self.rbtn_data_vswr)
        outer_layout.addRow("", self.rbtn_data_resistance)
        outer_layout.addRow("", self.rbtn_data_reactance)
        outer_layout.addRow("", self.rbtn_data_s21_gain)
        outer_layout.addRow(PeakSearchAnalysis.QHLine())
        outer_layout.addRow("Peak type", self.rbtn_peak_positive)
        outer_layout.addRow("", self.rbtn_peak_negative)
        # outer_layout.addRow("", self.rbtn_peak_both)
        outer_layout.addRow(PeakSearchAnalysis.QHLine())
        outer_layout.addRow("Max number of peaks", self.input_number_of_peaks)
        outer_layout.addRow("Move markers", self.checkbox_move_markers)
        outer_layout.addRow(PeakSearchAnalysis.QHLine())

        outer_layout.addRow(QtWidgets.QLabel("<b>Results</b>"))

    def runAnalysis(self):
        count = self.input_number_of_peaks.value()
        if self.rbtn_data_vswr.isChecked():
            data = []
            for d in self.app.data:
                data.append(d.vswr)
        elif self.rbtn_data_s21_gain.isChecked():
            data = []
            for d in self.app.data21:
                data.append(d.gain)
        else:
            logger.warning("Searching for peaks on unknown data")
            return

        if self.rbtn_peak_positive.isChecked():
            peaks, _ = signal.find_peaks(data, width=3, distance=3, prominence=1)
        elif self.rbtn_peak_negative.isChecked():
            peaks, _ = signal.find_peaks(np.array(data)*-1, width=3, distance=3, prominence=1)
        # elif self.rbtn_peak_both.isChecked():
        #     peaks_max, _ = signal.find_peaks(data, width=3, distance=3, prominence=1)
        #     peaks_min, _ = signal.find_peaks(np.array(data)*-1, width=3, distance=3, prominence=1)
        #     peaks = np.concatenate((peaks_max, peaks_min))
        else:
            # Both is not yet in
            logger.warning(
                "Searching for peaks,"
                " but neither looking at positive nor negative?")
            return

        # Having found the peaks, get the prominence data

        for p in peaks:
            logger.debug("Peak at %d", p)
        prominences = signal.peak_prominences(data, peaks)[0]
        logger.debug("%d prominences", len(prominences))

        # Find the peaks with the most extreme values
        # Alternately, allow the user to select "most prominent"?
        indices = np.argpartition(prominences, -count)[-count:]
        logger.debug("%d indices", len(indices))
        for i in indices:
            logger.debug("Index %d", i)
            logger.debug("Prominence %f", prominences[i])
            logger.debug("Index in sweep %d", peaks[i])
            logger.debug("Frequency %d", self.app.data[peaks[i]].freq)
            logger.debug("Value %f", data[peaks[i]])

        if self.checkbox_move_markers:
            if count > len(self.app.markers):
                logger.warning("More peaks found than there are markers")
            for i in range(min(count, len(self.app.markers))):
                self.app.markers[i].setFrequency(
                    str(self.app.data[peaks[indices[i]]].freq))
                self.app.markers[i].frequencyInput.setText(
                    str(self.app.data[peaks[indices[i]]].freq))

        max_val = -10**10
        max_idx = -1
        for p in peaks:
            if data[p] > max_val:
                max_val = data[p]
                max_idx = p

        logger.debug("Max peak at %d, value %f", max_idx, max_val)

    def reset(self):
        pass
