#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019.  Rune B. Broberg
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

    def __init__(self, app):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        self.app: NanoVNASaver = app

    def widget(self) -> QtWidgets.QWidget:
        return self._widget

    def runAnalysis(self):
        pass

    def reset(self):
        pass


class LowPassAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout()
        self._widget.setLayout(layout)
        layout.addRow(QtWidgets.QLabel("Please place " + self.app.markers[0].name + " in the filter passband."))
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
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        self.reset()
        pass_band_location = self.app.markers[0].location
        logger.debug("Pass band location: %d", pass_band_location)
        if pass_band_location < 0:
            logger.debug("No location for %s", self.app.markers[0].name)
            return

        if len(self.app.data21) == 0:
            logger.debug("No data to analyse")
            return

        pass_band_db = NanoVNASaver.gain(self.app.data21[pass_band_location])

        logger.debug("Initial passband gain: %d", pass_band_db)

        initial_cutoff_location = -1
        for i in range(pass_band_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
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
        peak_db = NanoVNASaver.gain(self.app.data21[initial_cutoff_location])
        for i in range(0, initial_cutoff_location):
            db = NanoVNASaver.gain(self.app.data21[i])
            if db > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        self.app.markers[0].setFrequency(str(self.app.data21[peak_location].freq))

        cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                cutoff_location = i
                break

        cutoff_frequency = self.app.data21[cutoff_location].freq

        logger.debug("Found true cutoff frequency at %d", cutoff_frequency)

        self.cutoff_label.setText(NanoVNASaver.formatFrequency(cutoff_frequency))
        self.app.markers[1].setFrequency(str(cutoff_frequency))

        six_db_location = -1
        for i in range(cutoff_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 6:
                # We found 6dB location
                six_db_location = i
                break

        if six_db_location < 0:
            self.result_label.setText("6 dB location not found.")
            return
        six_db_cutoff_frequency = self.app.data21[six_db_location].freq
        self.six_db_label.setText(NanoVNASaver.formatFrequency(six_db_cutoff_frequency))

        six_db_attenuation = NanoVNASaver.gain(self.app.data21[six_db_location])
        max_attenuation = NanoVNASaver.gain(self.app.data21[len(self.app.data21) - 1])
        frequency_factor = self.app.data21[len(self.app.data21) - 1].freq / six_db_cutoff_frequency
        attenuation = (max_attenuation - six_db_attenuation)
        logger.debug("Measured points: %d Hz and %d Hz", six_db_cutoff_frequency, self.app.data21[len(self.app.data21) - 1].freq)
        logger.debug("%d dB over %f factor", attenuation, frequency_factor)
        octave_attenuation = attenuation / (math.log10(frequency_factor) / math.log10(2))
        self.db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
        decade_attenuation = attenuation / math.log10(frequency_factor)
        self.db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")

        sixty_db_location = -1
        for i in range(six_db_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location < 0:
            # # We derive 60 dB instead
            # factor = 10 * (-54 / decade_attenuation)
            # sixty_db_cutoff_frequency = round(six_db_cutoff_frequency + six_db_cutoff_frequency * factor)
            # self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency) + " (derived)")
            self.sixty_db_label.setText("Not calculated")

        else:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency))

        self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)")
