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
import os
import csv
import itertools
import logging

from PyQt5 import QtWidgets

from NanoVNASaver.Analysis.Base import Analysis, QHLine
from NanoVNASaver.Formatting import (
    format_frequency, format_complex_imp,
    format_frequency_short, format_resistance)
from NanoVNASaver.RFTools import reflection_coefficient

logger = logging.getLogger(__name__)


def format_resistence_neg(x):
    return format_resistance(x, allow_negative=True)


def vswr_transformed(z, ratio=49) -> float:
    refl = reflection_coefficient(z / ratio)
    mag = abs(refl)
    return 1 if mag == 1 else (1 + mag) / (1 - mag)


class ResonanceAnalysis(Analysis):

    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QFormLayout()
        self._widget.setLayout(self.layout)
        self.input_description = QtWidgets.QLineEdit("")
        self.checkbox_move_marker = QtWidgets.QCheckBox()
        self.layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        self.layout.addRow("Description", self.input_description)
        self.layout.addRow(QHLine())

        self.layout.addRow(QHLine())

        self.results_label = QtWidgets.QLabel("<b>Results</b>")
        self.layout.addRow(self.results_label)

    def _get_data(self, index):
        my_data = {"freq": self.app.data.s11[index].freq,
                   "s11": self.app.data.s11[index].z,
                   "lambda": self.app.data.s11[index].wavelength,
                   "impedance": self.app.data.s11[index].impedance(),
                   "vswr": self.app.data.s11[index].vswr,
                   }
        my_data["vswr_49"] = vswr_transformed(
            my_data["impedance"], 49)
        my_data["vswr_4"] = vswr_transformed(
            my_data["impedance"], 4)
        my_data["r"] = my_data["impedance"].real
        my_data["x"] = my_data["impedance"].imag

        return my_data

    def _get_crossing(self):
        data = [d.phase for d in self.app.data.s11]
        return sorted(self.find_crossing_zero(data))

    def runAnalysis(self):
        self.reset()
        filename = (
            os.path.join("/tmp/", f"{self.input_description.text()}.csv")
            if self.input_description.text()
            else None)

        crossing = self._get_crossing()

        logger.debug("Found %d sections ",
                     len(crossing))

        results_header = self.layout.indexOf(self.results_label)
        logger.debug("Results start at %d, out of %d",
                     results_header, self.layout.rowCount())
        for _ in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount() - 1)

        if crossing:
            extended_data = []
            for m in crossing:
                start, lowest, end = m
                my_data = self._get_data(lowest)
                s11_low = self.app.data.s11[lowest]
                extended_data.append(my_data)
                if start != end:
                    logger.debug(
                        "Section from %d to %d, lowest at %d",
                        start, end, lowest)
                    self.layout.addRow(
                        "Resonance",
                        QtWidgets.QLabel(
                            f"{format_frequency(s11_low.freq)}"
                            f" ({format_complex_imp(s11_low.impedance())})"))
                else:
                    self.layout.addRow("Resonance", QtWidgets.QLabel(
                        format_frequency(self.app.data.s11[lowest].freq)))
                    self.layout.addWidget(QHLine())
            # Remove the final separator line
            self.layout.removeRow(self.layout.rowCount() - 1)
            if filename and extended_data:
                with open(filename, 'w', encoding='utf-8', newline='') as csvfile:
                    fieldnames = extended_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    for row in extended_data:
                        writer.writerow(row)

        else:
            self.layout.addRow(QtWidgets.QLabel(
                "No resonance found"))


class EFHWAnalysis(ResonanceAnalysis):
    """
    find only resonance when HI impedance
    """
    old_data = []

    def reset(self):
        logger.debug("reset")

    def runAnalysis(self):
        self.reset()
        if description := self.input_description.text():
            filename = os.path.join("/tmp/", f"{description}.csv")
        else:
            filename = None
        crossing = self._get_crossing()
        data = [d.impedance().real for d in self.app.data.s11]
        maximums = sorted(self.find_maximums(data, threshold=500))
        results_header = self.layout.indexOf(self.results_label)
        logger.debug("Results start at %d, out of %d",
                     results_header, self.layout.rowCount())

        for _ in range(results_header, self.layout.rowCount()):
            self.layout.removeRow(self.layout.rowCount() - 1)
        extended_data = {}
        both = []
        tolerance = 2
        for i, (low, _, high) in itertools.product(maximums, crossing):
            if low - tolerance <= i <= high + tolerance:
                both.append(i)
                continue
            if low > i:
                continue
        if both:
            logger.info("%i crossing HW", len(both))
            logger.info(crossing)
            logger.info(maximums)
            logger.info(both)
            for m in both:
                my_data = self._get_data(m)
                if m in extended_data:
                    extended_data[m].update(my_data)
                else:
                    extended_data[m] = my_data
            for i in range(min(len(both), len(self.app.markers))):
                self.app.markers[i].setFrequency(
                    str(self.app.data.s11[both[i]].freq))
                self.app.markers[i].frequencyInput.setText(
                    str(self.app.data.s11[both[i]].freq))

        else:
            logger.info("TO DO: find near data")
            for _, lowest, _ in crossing:
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
        fields = [("freq", format_frequency_short),
                  ("r", format_resistence_neg), ("lambda", lambda x: round(x, 2))]

        if self.old_data:
            diff = self.compare(
                self.old_data[-1], extended_data, fields=fields)
        else:
            diff = self.compare({}, extended_data, fields=fields)
        self.old_data.append(extended_data)
        for i, index in enumerate(sorted(extended_data.keys())):
            s11_idx = self.app.data.s11[index]
            self.layout.addRow(
                f"{format_frequency_short(s11_idx.freq)}",
                QtWidgets.QLabel(
                    f" ({diff[i]['freq']})"
                    f" {format_complex_imp(s11_idx.impedance())}"
                    f" ({diff[i]['r']}) {diff[i]['lambda']} m"))

        if filename and extended_data:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = extended_data[sorted(
                    extended_data.keys())[0]].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for index in sorted(extended_data.keys()):
                    row = extended_data[index]
                    writer.writerow(row)

    def compare(self, old, new, fields=None):
        """
        Compare data to help changes

        NB
        must be same sweep
        ( same index must be same frequence )
        :param old:
        :param new:
        """
        fields = fields or [("freq", str), ]

        def no_compare():

            return {k: "-" for k, _ in fields}

        old_idx = sorted(old.keys())
        # 'odict_keys' object is not subscriptable
        new_idx = sorted(new.keys())
        diff = {}
        i_max = min(len(old_idx), len(new_idx))
        i_tot = max(len(old_idx), len(new_idx))

        if i_max == i_tot:
            logger.debug("may be the same antenna ... analyzing")

        else:
            logger.warning("resonances changed from %s to %s",
                           len(old_idx), len(new_idx))

            logger.debug("Trying to compare only first %s resonances", i_max)

        split = 0
        max_delta_f = 1000000  # 1M
        for i, k in enumerate(new_idx):
            my_diff = {}

            logger.info("Risonance %s at %s", i,
                        format_frequency(new[k]["freq"]))

            if len(old_idx) <= i + split:
                diff[i] = no_compare()
                continue

            delta_f = new[k]["freq"] - old[old_idx[i + split]]["freq"]
            if abs(delta_f) < max_delta_f:
                logger.debug("can compare")

            else:
                logger.debug("can't compare, %s is too much ",
                             format_frequency(delta_f))
                if delta_f > 0:

                    logger.debug("possible missing band, ")
                    if len(old_idx) > (i + split + 1):
                        if (abs(new[k]["freq"] -
                                old[old_idx[i + split + 1]]["freq"]) <
                                max_delta_f):
                            logger.debug("new is missing band, compare next ")
                            split += 1
                        # FIXME: manage 2 or more band missing ?!?
                        else:
                            logger.debug("new band, non compare ")
                            diff[i] = no_compare()
                            continue
                else:
                    logger.debug("new band, non compare ")
                    diff[i] = no_compare()

                    split -= 1
                    continue

            for d, fn in fields:
                my_diff[d] = fn(new[k][d] - old[old_idx[i + split]][d])
                logger.info("Delta %s =  %s", d,
                            my_diff[d])

            diff[i] = my_diff

        for i in range(i_max, i_tot):
            # add missing in old ... if any

            diff[i] = no_compare()

        return diff
