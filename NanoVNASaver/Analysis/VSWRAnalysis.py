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
from NanoVNASaver.Formatting import format_complex_imp
from NanoVNASaver.RFTools import reflection_coefficient
import os
import csv

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

        for d in self.app.data11:
            data.append(d.vswr)
        # min_idx = np.argmin(data)
        #
        # logger.debug("Minimum at %d", min_idx)
        # logger.debug("Value at minimum: %f", data[min_idx])
        # logger.debug("Frequency: %d", self.app.data11[min_idx].freq)
        #
        # if self.checkbox_move_marker.isChecked():
        #     self.app.markers[0].setFrequency(str(self.app.data11[min_idx].freq))
        #     self.app.markers[0].frequencyInput.setText(str(self.app.data11[min_idx].freq))

        threshold = self.input_vswr_limit.value()
        minimums = self.find_minimums(data, threshold)

        logger.debug("Found %d sections under %f threshold",
                     len(minimums), threshold)

        results_header = self.layout.indexOf(self.results_label)
        logger.debug("Results start at %d, out of %d",
                     results_header, self.layout.rowCount())
        for i in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount() - 1)

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
                        format_frequency(self.app.data11[start].freq)))
                    self.layout.addRow(
                        "Minimum",
                        QtWidgets.QLabel(
                            f"{format_frequency(self.app.data11[lowest].freq)}"
                            f" ({round(data[lowest], 2)})"))
                    self.layout.addRow("End", QtWidgets.QLabel(
                        format_frequency(self.app.data11[end].freq)))
                    self.layout.addRow(
                        "Span",
                        QtWidgets.QLabel(
                            format_frequency(self.app.data11[end].freq -
                                             self.app.data11[start].freq)))
                    self.layout.addWidget(PeakSearchAnalysis.QHLine())
                else:
                    self.layout.addRow("Low spot", QtWidgets.QLabel(
                        format_frequency(self.app.data11[lowest].freq)))
                    self.layout.addWidget(PeakSearchAnalysis.QHLine())
            # Remove the final separator line
            self.layout.removeRow(self.layout.rowCount() - 1)
        else:
            self.layout.addRow(QtWidgets.QLabel(
                "No areas found with VSWR below " + str(round(threshold, 2)) + "."))


class ResonanceAnalysis(Analysis):
    # max_dips_shown = 3

    @classmethod
    def vswr_transformed(cls, z, ratio=49) -> float:
        refl = reflection_coefficient(z / ratio)
        mag = abs(refl)
        if mag == 1:
            return 1
        return (1 + mag) / (1 - mag)

    class QHLine(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setFrameShape(QtWidgets.QFrame.HLine)

    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QFormLayout()
        self._widget.setLayout(self.layout)
        self.input_description = QtWidgets.QLineEdit("")
        self.checkbox_move_marker = QtWidgets.QCheckBox()
        self.layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        self.layout.addRow("Description", self.input_description)
        self.layout.addRow(VSWRAnalysis.QHLine())

        self.layout.addRow(VSWRAnalysis.QHLine())

        self.results_label = QtWidgets.QLabel("<b>Results</b>")
        self.layout.addRow(self.results_label)

    def _get_data(self, index):
        my_data = {"freq": self.app.data11[index].freq,
                   "s11": self.app.data11[index].z,
                   "lambda": self.app.data11[index].wavelength,
                   "impedance": self.app.data11[index].impedance(),
                   "vswr": self.app.data11[index].vswr,
                   }
        my_data["vswr_49"] = self.vswr_transformed(
            my_data["impedance"], 49)
        my_data["vswr_4"] = self.vswr_transformed(
            my_data["impedance"], 4)
        my_data["r"] = my_data["impedance"].real
        my_data["x"] = my_data["impedance"].imag

        return my_data

    def _get_crossing(self):

        data = []
        for d in self.app.data11:
            data.append(d.phase)

        crossing = sorted(self.find_crossing_zero(data))
        return crossing

    def runAnalysis(self):
        self.results_label = QtWidgets.QLabel("<b>Results</b>")
        # max_dips_shown = self.max_dips_shown
        description = self.input_description.text()
        if description:
            filename = os.path.join("/tmp/", "{}.csv".format(description))
        else:
            filename = None

        crossing = self._get_crossing()

        logger.debug("Found %d sections ",
                     len(crossing))

        results_header = self.layout.indexOf(self.results_label)
        logger.debug("Results start at %d, out of %d",
                     results_header, self.layout.rowCount())
        for i in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount() - 1)

#         if len(crossing) > max_dips_shown:
#             self.layout.addRow(QtWidgets.QLabel("<b>More than " + str(max_dips_shown) +
#                                                 " dips found. Lowest shown.</b>"))

#         self.crossing = crossing[:max_dips_shown]
        extended_data = []
        if len(crossing) > 0:

            for m in crossing:
                start, lowest, end = m
                my_data = self._get_data(lowest)

                extended_data.append(my_data)
                if start != end:
                    logger.debug(
                        "Section from %d to %d, lowest at %d", start, end, lowest)

                    self.layout.addRow(
                        "Resonance",
                        QtWidgets.QLabel(
                            f"{format_frequency(self.app.data11[lowest].freq)}"
                            f" ({format_complex_imp(self.app.data11[lowest].impedance())})"))
                else:
                    self.layout.addRow("Resonance", QtWidgets.QLabel(
                        format_frequency(self.app.data11[lowest].freq)))
                    self.layout.addWidget(PeakSearchAnalysis.QHLine())
            # Remove the final separator line
            self.layout.removeRow(self.layout.rowCount() - 1)
            if filename and extended_data:

                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = extended_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    for row in extended_data:
                        writer.writerow(row)

        else:
            self.layout.addRow(QtWidgets.QLabel(
                "No resonance found"))


class EFHWAnalysis(ResonanceAnalysis):
    '''
    find only resonance when HI impedance
    '''

    def reset(self):
        logger.debug("reset")
        pass

    def runAnalysis(self):
        self.results_label = QtWidgets.QLabel("<b>Results</b>")
        # max_dips_shown = self.max_dips_shown
        description = self.input_description.text()
        if description:
            filename = os.path.join("/tmp/", "{}.csv".format(description))
        else:
            filename = None

        crossing = self._get_crossing()

        data = []
        for d in self.app.data11:
            data.append(d.impedance())

        maximums = sorted(self.find_maximums(data))

        results_header = self.layout.indexOf(self.results_label)
        logger.debug("Results start at %d, out of %d",
                     results_header, self.layout.rowCount())
        for i in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount() - 1)

        extended_data = {}

        for m in crossing:
            start, lowest, end = m
            my_data = self._get_data(lowest)

            if lowest in extended_data:
                extended_data[lowest].update(my_data)
            else:
                extended_data[lowest] = my_data

        logger.debug("maximumx %s of type %s", maximums, type(maximums))
        for m in maximums:
            logger.debug("m %s of type %s", m, type(m))

            my_data = self._get_data(m)
            if m in extended_data:
                extended_data[m].update(my_data)
            else:
                extended_data[m] = my_data

        for index in sorted(extended_data.keys()):

            self.layout.addRow(
                "Resonance",
                QtWidgets.QLabel(
                    f"{format_frequency(self.app.data11[index].freq)}"
                    f" ({format_complex_imp(self.app.data11[index].impedance())})"))

        # Remove the final separator line
        self.layout.removeRow(self.layout.rowCount() - 1)
        if filename and extended_data:

            with open(filename, 'w', newline='') as csvfile:
                fieldnames = extended_data[sorted(
                    extended_data.keys())[0]].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for index in sorted(extended_data.keys()):
                    row = extended_data[index]
                    writer.writerow(row)
