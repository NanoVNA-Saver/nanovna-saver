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

from NanoVNASaver.RFTools import RFTools
from scipy import signal
import numpy as np

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
        logger.debug("Measured points: %d Hz and %d Hz", frequency1, frequency2)
        logger.debug("%f dB over %f factor", attenuation, frequency_factor)
        octave_attenuation = attenuation / (math.log10(frequency_factor) / math.log10(2))
        decade_attenuation = attenuation / math.log10(frequency_factor)
        return octave_attenuation, decade_attenuation


class LowPassAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout()
        self._widget.setLayout(layout)
        layout.addRow(QtWidgets.QLabel("Low pass filter analysis"))
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
        self.reset()
        pass_band_location = self.app.markers[0].location
        logger.debug("Pass band location: %d", pass_band_location)

        if len(self.app.data21) == 0:
            logger.debug("No data to analyse")
            self.result_label.setText("No data to analyse.")
            return

        if pass_band_location < 0:
            logger.debug("No location for %s", self.app.markers[0].name)
            self.result_label.setText("Please place " + self.app.markers[0].name  + " in the passband.")
            return

        pass_band_db = self.app.data21[pass_band_location].gain

        logger.debug("Initial passband gain: %d", pass_band_db)

        initial_cutoff_location = -1
        for i in range(pass_band_location, len(self.app.data21)):
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
        for i in range(0, initial_cutoff_location):
            db = self.app.data21[i].gain
            if db > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        self.app.markers[0].setFrequency(str(self.app.data21[peak_location].freq))
        self.app.markers[0].frequencyInput.setText(str(self.app.data21[peak_location].freq))

        cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, len(self.app.data21)):
            db = self.app.data21[i].gain
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                cutoff_location = i
                break

        cutoff_frequency = self.app.data21[cutoff_location].freq
        cutoff_gain = self.app.data21[cutoff_location].gain - pass_band_db
        if cutoff_gain < -4:
            logger.debug("Cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         cutoff_gain)
        logger.debug("Found true cutoff frequency at %d", cutoff_frequency)

        self.cutoff_label.setText(RFTools.formatFrequency(cutoff_frequency) +
                                  " (" + str(round(cutoff_gain, 1)) + " dB)")
        self.app.markers[1].setFrequency(str(cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(cutoff_frequency))

        six_db_location = -1
        for i in range(cutoff_location, len(self.app.data21)):
            db = self.app.data21[i].gain
            if (pass_band_db - db) > 6:
                # We found 6dB location
                six_db_location = i
                break

        if six_db_location < 0:
            self.result_label.setText("6 dB location not found.")
            return
        six_db_cutoff_frequency = self.app.data21[six_db_location].freq
        self.six_db_label.setText(RFTools.formatFrequency(six_db_cutoff_frequency))

        ten_db_location = -1
        for i in range(cutoff_location, len(self.app.data21)):
            db = self.app.data21[i].gain
            if (pass_band_db - db) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(cutoff_location, len(self.app.data21)):
            db = self.app.data21[i].gain
            if (pass_band_db - db) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(six_db_location, len(self.app.data21)):
            db = self.app.data21[i].gain
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.sixty_db_label.setText(RFTools.formatFrequency(sixty_db_cutoff_frequency))
        elif ten_db_location != -1 and twenty_db_location != -1:
            ten = self.app.data21[ten_db_location].freq
            twenty = self.app.data21[twenty_db_location].freq
            sixty_db_frequency = ten * 10 ** (5 * (math.log10(twenty) - math.log10(ten)))
            self.sixty_db_label.setText(RFTools.formatFrequency(sixty_db_frequency) + " (derived)")
        else:
            self.sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.db_per_octave_label.setText("Not calculated")
            self.db_per_decade_label.setText("Not calculated")

        self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)")


class HighPassAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout()
        self._widget.setLayout(layout)
        layout.addRow(QtWidgets.QLabel("High pass filter analysis"))
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
        self.reset()
        pass_band_location = self.app.markers[0].location
        logger.debug("Pass band location: %d", pass_band_location)

        if len(self.app.data21) == 0:
            logger.debug("No data to analyse")
            self.result_label.setText("No data to analyse.")
            return

        if pass_band_location < 0:
            logger.debug("No location for %s", self.app.markers[0].name)
            self.result_label.setText("Please place " + self.app.markers[0].name + " in the passband.")
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
            logger.debug("Cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         cutoff_gain)

        logger.debug("Found true cutoff frequency at %d", cutoff_frequency)

        self.cutoff_label.setText(RFTools.formatFrequency(cutoff_frequency) +
                                  " (" + str(round(cutoff_gain, 1)) + " dB)")
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
        self.six_db_label.setText(RFTools.formatFrequency(six_db_cutoff_frequency))

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
                self.sixty_db_label.setText(RFTools.formatFrequency(sixty_db_cutoff_frequency))
            elif ten_db_location != -1 and twenty_db_location != -1:
                ten = self.app.data21[ten_db_location].freq
                twenty = self.app.data21[twenty_db_location].freq
                sixty_db_frequency = ten * 10 ** (5 * (math.log10(twenty) - math.log10(ten)))
                self.sixty_db_label.setText(RFTools.formatFrequency(sixty_db_frequency) + " (derived)")
            else:
                self.sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.db_per_octave_label.setText("Not calculated")
            self.db_per_decade_label.setText("Not calculated")

        self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)")


class BandPassAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout()
        self._widget.setLayout(layout)
        layout.addRow(QtWidgets.QLabel("Band pass filter analysis"))
        layout.addRow(QtWidgets.QLabel("Please place " + self.app.markers[0].name + " in the filter passband."))
        self.result_label = QtWidgets.QLabel()
        self.lower_cutoff_label = QtWidgets.QLabel()
        self.lower_six_db_label = QtWidgets.QLabel()
        self.lower_sixty_db_label = QtWidgets.QLabel()
        self.lower_db_per_octave_label = QtWidgets.QLabel()
        self.lower_db_per_decade_label = QtWidgets.QLabel()
        
        self.upper_cutoff_label = QtWidgets.QLabel()
        self.upper_six_db_label = QtWidgets.QLabel()
        self.upper_sixty_db_label = QtWidgets.QLabel()
        self.upper_db_per_octave_label = QtWidgets.QLabel()
        self.upper_db_per_decade_label = QtWidgets.QLabel()
        layout.addRow("Result:", self.result_label)

        layout.addRow(QtWidgets.QLabel(""))

        self.center_frequency_label = QtWidgets.QLabel()
        self.span_label = QtWidgets.QLabel()
        self.six_db_span_label = QtWidgets.QLabel()
        self.quality_label = QtWidgets.QLabel()

        layout.addRow("Center frequency:", self.center_frequency_label)
        layout.addRow("Bandwidth (-3 dB):", self.span_label)
        layout.addRow("Quality factor:", self.quality_label)
        layout.addRow("Bandwidth (-6 dB):", self.six_db_span_label)

        layout.addRow(QtWidgets.QLabel(""))

        layout.addRow(QtWidgets.QLabel("Lower side:"))
        layout.addRow("Cutoff frequency:", self.lower_cutoff_label)
        layout.addRow("-6 dB point:", self.lower_six_db_label)
        layout.addRow("-60 dB point:", self.lower_sixty_db_label)
        layout.addRow("Roll-off:", self.lower_db_per_octave_label)
        layout.addRow("Roll-off:", self.lower_db_per_decade_label)

        layout.addRow(QtWidgets.QLabel(""))

        layout.addRow(QtWidgets.QLabel("Upper side:"))
        layout.addRow("Cutoff frequency:", self.upper_cutoff_label)
        layout.addRow("-6 dB point:", self.upper_six_db_label)
        layout.addRow("-60 dB point:", self.upper_sixty_db_label)
        layout.addRow("Roll-off:", self.upper_db_per_octave_label)
        layout.addRow("Roll-off:", self.upper_db_per_decade_label)

    def reset(self):
        self.result_label.clear()
        self.center_frequency_label.clear()
        self.span_label.clear()
        self.quality_label.clear()
        self.six_db_span_label.clear()

        self.upper_cutoff_label.clear()
        self.upper_six_db_label.clear()
        self.upper_sixty_db_label.clear()
        self.upper_db_per_octave_label.clear()
        self.upper_db_per_decade_label.clear()

        self.lower_cutoff_label.clear()
        self.lower_six_db_label.clear()
        self.lower_sixty_db_label.clear()
        self.lower_db_per_octave_label.clear()
        self.lower_db_per_decade_label.clear()

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
            self.result_label.setText("Please place " + self.app.markers[0].name  + " in the passband.")
            return

        pass_band_db = self.app.data21[pass_band_location].gain

        logger.debug("Initial passband gain: %d", pass_band_db)

        initial_lower_cutoff_location = -1
        for i in range(pass_band_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 3:
                # We found a cutoff location
                initial_lower_cutoff_location = i
                break

        if initial_lower_cutoff_location < 0:
            self.result_label.setText("Lower cutoff location not found.")
            return

        initial_lower_cutoff_frequency = self.app.data21[initial_lower_cutoff_location].freq

        logger.debug("Found initial lower cutoff frequency at %d", initial_lower_cutoff_frequency)

        initial_upper_cutoff_location = -1
        for i in range(pass_band_location, len(self.app.data21), 1):
            if (pass_band_db - self.app.data21[i].gain) > 3:
                # We found a cutoff location
                initial_upper_cutoff_location = i
                break

        if initial_upper_cutoff_location < 0:
            self.result_label.setText("Upper cutoff location not found.")
            return

        initial_upper_cutoff_frequency = self.app.data21[initial_upper_cutoff_location].freq

        logger.debug("Found initial upper cutoff frequency at %d", initial_upper_cutoff_frequency)

        peak_location = -1
        peak_db = self.app.data21[initial_lower_cutoff_location].gain
        for i in range(initial_lower_cutoff_location, initial_upper_cutoff_location, 1):
            db = self.app.data21[i].gain
            if db > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        lower_cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 3:
                # We found the cutoff location
                lower_cutoff_location = i
                break

        lower_cutoff_frequency = self.app.data21[lower_cutoff_location].freq
        lower_cutoff_gain = self.app.data21[lower_cutoff_location].gain - pass_band_db

        if lower_cutoff_gain < -4:
            logger.debug("Lower cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         lower_cutoff_gain)

        logger.debug("Found true lower cutoff frequency at %d", lower_cutoff_frequency)

        self.lower_cutoff_label.setText(RFTools.formatFrequency(lower_cutoff_frequency) +
                                        " (" + str(round(lower_cutoff_gain, 1)) + " dB)")

        self.app.markers[1].setFrequency(str(lower_cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(lower_cutoff_frequency))

        upper_cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, len(self.app.data21), 1):
            if (pass_band_db - self.app.data21[i].gain) > 3:
                # We found the cutoff location
                upper_cutoff_location = i
                break

        upper_cutoff_frequency = self.app.data21[upper_cutoff_location].freq
        upper_cutoff_gain = self.app.data21[upper_cutoff_location].gain - pass_band_db
        if upper_cutoff_gain < -4:
            logger.debug("Upper cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         upper_cutoff_gain)

        logger.debug("Found true upper cutoff frequency at %d", upper_cutoff_frequency)

        self.upper_cutoff_label.setText(RFTools.formatFrequency(upper_cutoff_frequency) +
                                        " (" + str(round(upper_cutoff_gain, 1)) + " dB)")
        self.app.markers[2].setFrequency(str(upper_cutoff_frequency))
        self.app.markers[2].frequencyInput.setText(str(upper_cutoff_frequency))

        span = upper_cutoff_frequency - lower_cutoff_frequency
        center_frequency = math.sqrt(lower_cutoff_frequency * upper_cutoff_frequency)
        q = center_frequency / span

        self.span_label.setText(RFTools.formatFrequency(span))
        self.center_frequency_label.setText(RFTools.formatFrequency(center_frequency))
        self.quality_label.setText(str(round(q, 2)))

        self.app.markers[0].setFrequency(str(round(center_frequency)))
        self.app.markers[0].frequencyInput.setText(str(round(center_frequency)))

        # Lower roll-off

        lower_six_db_location = -1
        for i in range(lower_cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 6:
                # We found 6dB location
                lower_six_db_location = i
                break

        if lower_six_db_location < 0:
            self.result_label.setText("Lower 6 dB location not found.")
            return
        lower_six_db_cutoff_frequency = self.app.data21[lower_six_db_location].freq
        self.lower_six_db_label.setText(RFTools.formatFrequency(lower_six_db_cutoff_frequency))

        ten_db_location = -1
        for i in range(lower_cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(lower_cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(lower_six_db_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            if sixty_db_location > 0:
                sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
                self.lower_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_cutoff_frequency))
            elif ten_db_location != -1 and twenty_db_location != -1:
                ten = self.app.data21[ten_db_location].freq
                twenty = self.app.data21[twenty_db_location].freq
                sixty_db_frequency = ten * 10 ** (5 * (math.log10(twenty) - math.log10(ten)))
                self.lower_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_frequency) + " (derived)")
            else:
                self.lower_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.lower_db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.lower_db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.lower_db_per_octave_label.setText("Not calculated")
            self.lower_db_per_decade_label.setText("Not calculated")

        # Upper roll-off

        upper_six_db_location = -1
        for i in range(upper_cutoff_location, len(self.app.data21), 1):
            if (pass_band_db - self.app.data21[i].gain) > 6:
                # We found 6dB location
                upper_six_db_location = i
                break

        if upper_six_db_location < 0:
            self.result_label.setText("Upper 6 dB location not found.")
            return
        upper_six_db_cutoff_frequency = self.app.data21[upper_six_db_location].freq
        self.upper_six_db_label.setText(RFTools.formatFrequency(upper_six_db_cutoff_frequency))

        six_db_span = upper_six_db_cutoff_frequency - lower_six_db_cutoff_frequency

        self.six_db_span_label.setText(RFTools.formatFrequency(six_db_span))

        ten_db_location = -1
        for i in range(upper_cutoff_location, len(self.app.data21), 1):
            if (pass_band_db - self.app.data21[i].gain) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(upper_cutoff_location, len(self.app.data21), 1):
            if (pass_band_db - self.app.data21[i].gain) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(upper_six_db_location, len(self.app.data21), 1):
            if (pass_band_db - self.app.data21[i].gain) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.upper_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_cutoff_frequency))
        elif ten_db_location != -1 and twenty_db_location != -1:
            ten = self.app.data21[ten_db_location].freq
            twenty = self.app.data21[twenty_db_location].freq
            sixty_db_frequency = ten * 10 ** (5 * (math.log10(twenty) - math.log10(ten)))
            self.upper_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_frequency) + " (derived)")
        else:
            self.upper_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.upper_db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.upper_db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.upper_db_per_octave_label.setText("Not calculated")
            self.upper_db_per_decade_label.setText("Not calculated")

        if upper_cutoff_gain < -4 or lower_cutoff_gain < -4:
            self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)\n" +
                                      "Insufficient data for analysis. Increase segment count.")
        else:
            self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)")


class BandStopAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout()
        self._widget.setLayout(layout)
        layout.addRow(QtWidgets.QLabel("Band stop filter analysis"))
        self.result_label = QtWidgets.QLabel()
        self.lower_cutoff_label = QtWidgets.QLabel()
        self.lower_six_db_label = QtWidgets.QLabel()
        self.lower_sixty_db_label = QtWidgets.QLabel()
        self.lower_db_per_octave_label = QtWidgets.QLabel()
        self.lower_db_per_decade_label = QtWidgets.QLabel()

        self.upper_cutoff_label = QtWidgets.QLabel()
        self.upper_six_db_label = QtWidgets.QLabel()
        self.upper_sixty_db_label = QtWidgets.QLabel()
        self.upper_db_per_octave_label = QtWidgets.QLabel()
        self.upper_db_per_decade_label = QtWidgets.QLabel()
        layout.addRow("Result:", self.result_label)

        layout.addRow(QtWidgets.QLabel(""))

        self.center_frequency_label = QtWidgets.QLabel()
        self.span_label = QtWidgets.QLabel()
        self.six_db_span_label = QtWidgets.QLabel()
        self.quality_label = QtWidgets.QLabel()

        layout.addRow("Center frequency:", self.center_frequency_label)
        layout.addRow("Bandwidth (-3 dB):", self.span_label)
        layout.addRow("Quality factor:", self.quality_label)
        layout.addRow("Bandwidth (-6 dB):", self.six_db_span_label)

        layout.addRow(QtWidgets.QLabel(""))

        layout.addRow(QtWidgets.QLabel("Lower side:"))
        layout.addRow("Cutoff frequency:", self.lower_cutoff_label)
        layout.addRow("-6 dB point:", self.lower_six_db_label)
        layout.addRow("-60 dB point:", self.lower_sixty_db_label)
        layout.addRow("Roll-off:", self.lower_db_per_octave_label)
        layout.addRow("Roll-off:", self.lower_db_per_decade_label)

        layout.addRow(QtWidgets.QLabel(""))

        layout.addRow(QtWidgets.QLabel("Upper side:"))
        layout.addRow("Cutoff frequency:", self.upper_cutoff_label)
        layout.addRow("-6 dB point:", self.upper_six_db_label)
        layout.addRow("-60 dB point:", self.upper_sixty_db_label)
        layout.addRow("Roll-off:", self.upper_db_per_octave_label)
        layout.addRow("Roll-off:", self.upper_db_per_decade_label)

    def reset(self):
        self.result_label.clear()
        self.span_label.clear()
        self.quality_label.clear()
        self.six_db_span_label.clear()

        self.upper_cutoff_label.clear()
        self.upper_six_db_label.clear()
        self.upper_sixty_db_label.clear()
        self.upper_db_per_octave_label.clear()
        self.upper_db_per_decade_label.clear()

        self.lower_cutoff_label.clear()
        self.lower_six_db_label.clear()
        self.lower_sixty_db_label.clear()
        self.lower_db_per_octave_label.clear()
        self.lower_db_per_decade_label.clear()

    def runAnalysis(self):
        self.reset()

        if len(self.app.data21) == 0:
            logger.debug("No data to analyse")
            self.result_label.setText("No data to analyse.")
            return

        peak_location = -1
        peak_db = self.app.data21[0].gain
        for i in range(len(self.app.data21)):
            db = self.app.data21[i].gain
            if db > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        lower_cutoff_location = -1
        pass_band_db = peak_db
        for i in range(len(self.app.data21)):
            if (pass_band_db - self.app.data21[i].gain) > 3:
                # We found the cutoff location
                lower_cutoff_location = i
                break

        lower_cutoff_frequency = self.app.data21[lower_cutoff_location].freq
        lower_cutoff_gain = self.app.data21[lower_cutoff_location].gain - pass_band_db

        if lower_cutoff_gain < -4:
            logger.debug("Lower cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         lower_cutoff_gain)

        logger.debug("Found true lower cutoff frequency at %d", lower_cutoff_frequency)

        self.lower_cutoff_label.setText(RFTools.formatFrequency(lower_cutoff_frequency) +
                                        " (" + str(round(lower_cutoff_gain, 1)) + " dB)")

        self.app.markers[1].setFrequency(str(lower_cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(lower_cutoff_frequency))

        upper_cutoff_location = -1
        for i in range(len(self.app.data21)-1, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 3:
                # We found the cutoff location
                upper_cutoff_location = i
                break

        upper_cutoff_frequency = self.app.data21[upper_cutoff_location].freq
        upper_cutoff_gain = self.app.data21[upper_cutoff_location].gain - pass_band_db
        if upper_cutoff_gain < -4:
            logger.debug("Upper cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         upper_cutoff_gain)

        logger.debug("Found true upper cutoff frequency at %d", upper_cutoff_frequency)

        self.upper_cutoff_label.setText(RFTools.formatFrequency(upper_cutoff_frequency) +
                                        " (" + str(round(upper_cutoff_gain, 1)) + " dB)")
        self.app.markers[2].setFrequency(str(upper_cutoff_frequency))
        self.app.markers[2].frequencyInput.setText(str(upper_cutoff_frequency))

        span = upper_cutoff_frequency - lower_cutoff_frequency
        center_frequency = math.sqrt(lower_cutoff_frequency * upper_cutoff_frequency)
        q = center_frequency / span

        self.span_label.setText(RFTools.formatFrequency(span))
        self.center_frequency_label.setText(RFTools.formatFrequency(center_frequency))
        self.quality_label.setText(str(round(q, 2)))

        self.app.markers[0].setFrequency(str(round(center_frequency)))
        self.app.markers[0].frequencyInput.setText(str(round(center_frequency)))

        # Lower roll-off

        lower_six_db_location = -1
        for i in range(lower_cutoff_location, len(self.app.data21)):
            if (pass_band_db - self.app.data21[i].gain) > 6:
                # We found 6dB location
                lower_six_db_location = i
                break

        if lower_six_db_location < 0:
            self.result_label.setText("Lower 6 dB location not found.")
            return
        lower_six_db_cutoff_frequency = self.app.data21[lower_six_db_location].freq
        self.lower_six_db_label.setText(RFTools.formatFrequency(lower_six_db_cutoff_frequency))

        ten_db_location = -1
        for i in range(lower_cutoff_location, len(self.app.data21)):
            if (pass_band_db - self.app.data21[i].gain) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(lower_cutoff_location, len(self.app.data21)):
            if (pass_band_db - self.app.data21[i].gain) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(lower_six_db_location, len(self.app.data21)):
            if (pass_band_db - self.app.data21[i].gain) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.lower_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_cutoff_frequency))
        elif ten_db_location != -1 and twenty_db_location != -1:
            ten = self.app.data21[ten_db_location].freq
            twenty = self.app.data21[twenty_db_location].freq
            sixty_db_frequency = ten * 10 ** (5 * (math.log10(twenty) - math.log10(ten)))
            self.lower_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_frequency) + " (derived)")
        else:
            self.lower_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.lower_db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.lower_db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.lower_db_per_octave_label.setText("Not calculated")
            self.lower_db_per_decade_label.setText("Not calculated")

        # Upper roll-off

        upper_six_db_location = -1
        for i in range(upper_cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 6:
                # We found 6dB location
                upper_six_db_location = i
                break

        if upper_six_db_location < 0:
            self.result_label.setText("Upper 6 dB location not found.")
            return
        upper_six_db_cutoff_frequency = self.app.data21[upper_six_db_location].freq
        self.upper_six_db_label.setText(RFTools.formatFrequency(upper_six_db_cutoff_frequency))

        six_db_span = upper_six_db_cutoff_frequency - lower_six_db_cutoff_frequency

        self.six_db_span_label.setText(RFTools.formatFrequency(six_db_span))

        ten_db_location = -1
        for i in range(upper_cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(upper_cutoff_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(upper_six_db_location, -1, -1):
            if (pass_band_db - self.app.data21[i].gain) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.upper_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_cutoff_frequency))
        elif ten_db_location != -1 and twenty_db_location != -1:
            ten = self.app.data21[ten_db_location].freq
            twenty = self.app.data21[twenty_db_location].freq
            sixty_db_frequency = ten * 10 ** (5 * (math.log10(twenty) - math.log10(ten)))
            self.upper_sixty_db_label.setText(RFTools.formatFrequency(sixty_db_frequency) + " (derived)")
        else:
            self.upper_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.upper_db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.upper_db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.upper_db_per_octave_label.setText("Not calculated")
            self.upper_db_per_decade_label.setText("Not calculated")

        if upper_cutoff_gain < -4 or lower_cutoff_gain < -4:
            self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)\n" +
                                      "Insufficient data for analysis. Increase segment count.")
        else:
            self.result_label.setText("Analysis complete (" + str(len(self.app.data)) + " points)")


class SimplePeakSearchAnalysis(Analysis):
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

        self.rbtn_data_s21_gain.setChecked(True)

        self.rbtn_peak_group = QtWidgets.QButtonGroup()
        self.rbtn_peak_positive = QtWidgets.QRadioButton("Highest value")
        self.rbtn_peak_negative = QtWidgets.QRadioButton("Lowest value")
        self.rbtn_peak_group.addButton(self.rbtn_peak_positive)
        self.rbtn_peak_group.addButton(self.rbtn_peak_negative)

        self.rbtn_peak_positive.setChecked(True)

        self.checkbox_move_marker = QtWidgets.QCheckBox()

        outer_layout.addRow(QtWidgets.QLabel("<b>Settings</b>"))
        outer_layout.addRow("Data source", self.rbtn_data_vswr)
        outer_layout.addRow("", self.rbtn_data_resistance)
        outer_layout.addRow("", self.rbtn_data_reactance)
        outer_layout.addRow("", self.rbtn_data_s21_gain)
        outer_layout.addRow(PeakSearchAnalysis.QHLine())
        outer_layout.addRow("Peak type", self.rbtn_peak_positive)
        outer_layout.addRow("", self.rbtn_peak_negative)
        outer_layout.addRow(PeakSearchAnalysis.QHLine())
        outer_layout.addRow("Move marker to peak", self.checkbox_move_marker)
        outer_layout.addRow(PeakSearchAnalysis.QHLine())

        outer_layout.addRow(QtWidgets.QLabel("<b>Results</b>"))

        self.peak_frequency = QtWidgets.QLabel()
        self.peak_value = QtWidgets.QLabel()

        outer_layout.addRow("Peak frequency:", self.peak_frequency)
        outer_layout.addRow("Peak value:", self.peak_value)

    def runAnalysis(self):
        if self.rbtn_data_vswr.isChecked():
            suffix = ""
            data = []
            for d in self.app.data:
                data.append(d.vswr)
        elif self.rbtn_data_resistance.isChecked():
            suffix = " \N{OHM SIGN}"
            data = []
            for d in self.app.data:
                data.append(d.impedance().real)
        elif self.rbtn_data_reactance.isChecked():
            suffix = " \N{OHM SIGN}"
            data = []
            for d in self.app.data:
                data.append(d.impedance().imag)
        elif self.rbtn_data_s21_gain.isChecked():
            suffix = " dB"
            data = []
            for d in self.app.data21:
                data.append(d.gain)
        else:
            logger.warning("Searching for peaks on unknown data")
            return

        if len(data) == 0:
            return

        if self.rbtn_peak_positive.isChecked():
            idx_peak = np.argmax(data)
        elif self.rbtn_peak_negative.isChecked():
            idx_peak = np.argmin(data)
        else:
            logger.warning("Searching for peaks, but neither looking at positive nor negative?")  # Both is not yet in
            return

        self.peak_frequency.setText(RFTools.formatFrequency(self.app.data[idx_peak].freq))
        self.peak_value.setText(str(round(data[idx_peak], 3)) + suffix)

        if self.checkbox_move_marker.isChecked() and len(self.app.markers) >= 1:
            self.app.markers[0].setFrequency(str(self.app.data[idx_peak].freq))
            self.app.markers[0].frequencyInput.setText(RFTools.formatFrequency(self.app.data[idx_peak].freq))


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
            logger.warning("Searching for peaks, but neither looking at positive nor negative?")  # Both is not yet in
            return

        # Having found the peaks, get the prominence data

        for p in peaks:
            logger.debug("Peak at %d", p)
        prominences, left_bases, right_bases = signal.peak_prominences(data, peaks)
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
                self.app.markers[i].setFrequency(str(self.app.data[peaks[indices[i]]].freq))
                self.app.markers[i].frequencyInput.setText(str(self.app.data[peaks[indices[i]]].freq))

        max_val = -10**10
        max_idx = -1
        for p in peaks:
            if data[p] > max_val:
                max_val = data[p]
                max_idx = p

        logger.debug("Max peak at %d, value %f", max_idx, max_val)

    def reset(self):
        pass


class VSWRAnalysis(Analysis):
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
        self.input_vswr_limit.setValue(1.5)
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
        max_dips_shown = 3
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
        for i in range(len(data)):
            d = data[i]
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

        if len(minimums) > 0:
            for m in minimums:
                start, lowest, end = m
                if start != end:
                    logger.debug("Section from %d to %d, lowest at %d", start, end, lowest)
                    self.layout.addRow("Start", QtWidgets.QLabel(RFTools.formatFrequency(self.app.data[start].freq)))
                    self.layout.addRow("Minimum", QtWidgets.QLabel(RFTools.formatFrequency(self.app.data[lowest].freq) +
                                                                   " (" + str(round(data[lowest], 2)) + ")"))
                    self.layout.addRow("End", QtWidgets.QLabel(RFTools.formatFrequency(self.app.data[end].freq)))
                    self.layout.addRow("Span", QtWidgets.QLabel(RFTools.formatFrequency(self.app.data[end].freq -\
                                                                                        self.app.data[start].freq)))
                    self.layout.addWidget(PeakSearchAnalysis.QHLine())
                else:
                    self.layout.addRow("Low spot", QtWidgets.QLabel(RFTools.formatFrequency(self.app.data[lowest].freq)))
                    self.layout.addWidget(PeakSearchAnalysis.QHLine())
            self.layout.removeRow(self.layout.rowCount()-1)  # Remove the final separator line
        else:
            self.layout.addRow(QtWidgets.QLabel("No areas found with VSWR below " + str(round(threshold, 2)) + "."))
