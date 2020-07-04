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
import numpy as np

from NanoVNASaver.Analysis import Analysis, PeakSearchAnalysis
from NanoVNASaver.Formatting import format_frequency

logger = logging.getLogger(__name__)


class VSWRAnalysis(Analysis):
    max_dips_shown = 3
    vswr_limit_value = 1.5
    
    class QHLine(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setFrameShape(QtWidgets.QFrame.HLine)

    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QFormLayout()
        self._widget.setLayout(self.layout)

        self.input_vswr_limit = QtWidgets.QDoubleSpinBox()
        self.input_vswr_limit.setValue(self.vswr_limit_value)
        self.input_vswr_limit.setSingleStep(0.1)
        self.input_vswr_limit.setMinimum(1)
        self.input_vswr_limit.setMaximum(25)
        self.input_vswr_limit.setDecimals(2)

        self.checkbox_move_marker = QtWidgets.QCheckBox()
        self.layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        self.layout.addRow("VSWR limit", self.input_vswr_limit)
        self.layout.addRow(VSWRAnalysis.QHLine())

        self.results_label = QtWidgets.QLabel("<b>Results</b>")
        self.layout.addRow(self.results_label)

    def runAnalysis(self):
        max_dips_shown = self.max_dips_shown
        data = []
        for d in self.app.data:
            data.append(d.vswr)
        # min_idx = np.argmin(data)
        #
        # logger.debug("Minimum at %d", min_idx)
        # logger.debug("Value at minimum: %f", data[min_idx])
        # logger.debug("Frequency: %d", self.app.data[min_idx].freq)
        #
        # if self.checkbox_move_marker.isChecked():
        #     self.app.markers[0].setFrequency(str(self.app.data[min_idx].freq))
        #     self.app.markers[0].frequencyInput.setText(str(self.app.data[min_idx].freq))

        minimums = []
        min_start = -1
        min_idx = -1
        threshold = self.input_vswr_limit.value()
        min_val = threshold
        for i, d in enumerate(data):
            if d < threshold and i < len(data)-1:
                if d < min_val:
                    min_val = d
                    min_idx = i
                if min_start == -1:
                    min_start = i
            elif min_start != -1:
                # We are above the threshold, and were in a section that was below
                minimums.append((min_start, min_idx, i-1))
                min_start = -1
                min_idx = -1
                min_val = threshold

        logger.debug("Found %d sections under %f threshold", len(minimums), threshold)

        results_header = self.layout.indexOf(self.results_label)
        logger.debug("Results start at %d, out of %d", results_header, self.layout.rowCount())
        for i in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount()-1)

        if len(minimums) > max_dips_shown:
            self.layout.addRow(QtWidgets.QLabel("<b>More than " + str(max_dips_shown) +
                                                " dips found. Lowest shown.</b>"))
            dips = []
            for m in minimums:
                start, lowest, end = m
                dips.append(data[lowest])

            best_dips = []
            for i in range(max_dips_shown):
                min_idx = np.argmin(dips)
                best_dips.append(minimums[min_idx])
                dips.remove(dips[min_idx])
                minimums.remove(minimums[min_idx])
            minimums = best_dips
        self.minimums = minimums
        if len(minimums) > 0:
            for m in minimums:
                start, lowest, end = m
                if start != end:
                    logger.debug(
                        "Section from %d to %d, lowest at %d", start, end, lowest)
                    self.layout.addRow("Start", QtWidgets.QLabel(
                        format_frequency(self.app.data[start].freq)))
                    self.layout.addRow(
                        "Minimum",
                        QtWidgets.QLabel(
                            f"{format_frequency(self.app.data[lowest].freq)}"
                            f" ({round(data[lowest], 2)})"))
                    self.layout.addRow("End", QtWidgets.QLabel(
                        format_frequency(self.app.data[end].freq)))
                    self.layout.addRow(
                        "Span",
                        QtWidgets.QLabel(
                            format_frequency(self.app.data[end].freq -
                                             self.app.data[start].freq)))
                    self.layout.addWidget(PeakSearchAnalysis.QHLine())
                else:
                    self.layout.addRow("Low spot", QtWidgets.QLabel(
                        format_frequency(self.app.data[lowest].freq)))
                    self.layout.addWidget(PeakSearchAnalysis.QHLine())
            # Remove the final separator line
            self.layout.removeRow(self.layout.rowCount()-1)
        else:
            self.layout.addRow(QtWidgets.QLabel(
                "No areas found with VSWR below " + str(round(threshold, 2)) + "."))
