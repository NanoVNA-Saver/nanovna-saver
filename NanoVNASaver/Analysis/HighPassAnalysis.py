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

from NanoVNASaver.Analysis import Analysis
from NanoVNASaver.Formatting import format_frequency

logger = logging.getLogger(__name__)


class HighPassAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout()
        self._widget.setLayout(layout)
        layout.addRow(QtWidgets.QLabel("High pass filter analysis"))
        layout.addRow(QtWidgets.QLabel(
            f"Please place {self.app.markers[0].name} in the filter passband."))
        self.result_label = QtWidgets.QLabel()
        self.cutoff_label = QtWidgets.QLabel()
        self.six_db_label = QtWidgets.QLabel()
        self.sixty_db_label = QtWidgets.QLabel()
        self.db_per_octave_label = QtWidgets.QLabel()
        self.db_per_decade_label = QtWidgets.QLabel()
        layout.addRow("Result:", self.result_label)
        layout.addRow("Cutoff frequency:", self.cutoff_label)
        layout.addRow("-6 dB point:", self.six_db_label)
        layout.addRow("-60 dB point:", self.sixty_db_label)
        layout.addRow("Roll-off:", self.db_per_octave_label)
        layout.addRow("Roll-off:", self.db_per_decade_label)

    def reset(self):
        self.result_label.clear()
        self.cutoff_label.clear()
        self.six_db_label.clear()
        self.sixty_db_label.clear()
        self.db_per_octave_label.clear()
        self.db_per_decade_label.clear()

    def runAnalysis(self):
        self.reset()
        pass_band_location = self.app.markers[0].location
        logger.debug("Pass band location: %d", pass_band_location)

        if len(self.app.data21) == 0:
            logger.debug("No data to analyse")
            self.result_label.setText("No data to analyse.")
            return

        if pass_band_location < 0:
            logger.debug("No location for %s", self.app.markers[0].name)
            self.result_label.setText(
                f"Please place {self.app.markers[0].name } in the passband.")
            return

        pass_band_db = self.app.data21[pass_band_location].gain

        logger.debug("Initial passband gain: %d", pass_band_db)

        initial_cutoff_location = -1
        for i in range(pass_band_location, -1, -1):
            db = self.app.data21[i].gain
            if (pass_band_db - db) > 3:
                # We found a cutoff location
                initial_cutoff_location = i
                break

        if initial_cutoff_location < 0:
            self.result_label.setText("Cutoff location not found.")
            return

        initial_cutoff_frequency = self.app.data21[initial_cutoff_location].freq

        logger.debug("Found initial cutoff frequency at %d", initial_cutoff_frequency)

        peak_location = -1
        peak_db = self.app.data21[initial_cutoff_location].gain
        for i in range(len(self.app.data21) - 1, initial_cutoff_location - 1, -1):
            if self.app.data21[i].gain > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        self.app.markers[0].setFrequency(str(self.app.data21[peak_location].freq))
        self.app.markers[0].frequencyInput.setText(str(self.app.data21[peak_location].freq))

        cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 3:
                # We found the cutoff location
                cutoff_location = i
                break

        cutoff_frequency = self.app.data21[cutoff_location].freq
        cutoff_gain = self.app.data21[cutoff_location].gain - pass_band_db
        if cutoff_gain < -4:
            logger.debug("Cutoff frequency found at %f dB"
                         " - insufficient data points for true -3 dB point.",
                         cutoff_gain)
        logger.debug("Found true cutoff frequency at %d", cutoff_frequency)

        self.cutoff_label.setText(
            f"{format_frequency(cutoff_frequency)}"
            f" {round(cutoff_gain, 1)} dB)")
        self.app.markers[1].setFrequency(str(cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(cutoff_frequency))

        six_db_location = -1
        for i in range(cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 6:
                # We found 6dB location
                six_db_location = i
                break

        if six_db_location < 0:
            self.result_label.setText("6 dB location not found.")
            return
        six_db_cutoff_frequency = self.app.data21[six_db_location].freq
        self.six_db_label.setText(
            format_frequency(six_db_cutoff_frequency))

        ten_db_location = -1
        for i in range(cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(six_db_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            if sixty_db_location > 0:
                sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
                self.sixty_db_label.setText(
                    format_frequency(sixty_db_cutoff_frequency))
            elif ten_db_location != -1 and twenty_db_location != -1:
                ten = self.app.data21[ten_db_location].freq
                twenty = self.app.data21[twenty_db_location].freq
                sixty_db_frequency = ten * 10 ** (5 * (math.log10(twenty) - math.log10(ten)))
                self.sixty_db_label.setText(
                    f"{format_frequency(sixty_db_frequency)} (derived)")
            else:
                self.sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(
                ten_db_location, twenty_db_location)
            self.db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.db_per_octave_label.setText("Not calculated")
            self.db_per_decade_label.setText("Not calculated")

        self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)")
