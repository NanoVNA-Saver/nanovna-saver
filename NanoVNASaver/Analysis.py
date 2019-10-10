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

    def calculateRolloff(self, location1, location2):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        frequency1 = self.app.data21[location1].freq
        frequency2 = self.app.data21[location2].freq
        gain1 = NanoVNASaver.gain(self.app.data21[location1])
        gain2 = NanoVNASaver.gain(self.app.data21[location2])
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
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
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
        self.app.markers[0].frequencyInput.setText(str(self.app.data21[peak_location].freq))

        cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                cutoff_location = i
                break

        cutoff_frequency = self.app.data21[cutoff_location].freq
        cutoff_gain = NanoVNASaver.gain(self.app.data21[cutoff_location]) - pass_band_db
        if cutoff_gain < -4:
            logger.debug("Cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         cutoff_gain)
        logger.debug("Found true cutoff frequency at %d", cutoff_frequency)

        self.cutoff_label.setText(NanoVNASaver.formatFrequency(cutoff_frequency) +
                                  " (" + str(round(cutoff_gain, 1)) + " dB)")
        self.app.markers[1].setFrequency(str(cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(cutoff_frequency))

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

        ten_db_location = -1
        for i in range(cutoff_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(cutoff_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(six_db_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency))
        else:
            # # We derive 60 dB instead
            # factor = 10 * (-54 / decade_attenuation)
            # sixty_db_cutoff_frequency = round(six_db_cutoff_frequency + six_db_cutoff_frequency * factor)
            # self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency) + " (derived)")
            self.sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0:
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
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
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

        pass_band_db = NanoVNASaver.gain(self.app.data21[pass_band_location])

        logger.debug("Initial passband gain: %d", pass_band_db)

        initial_cutoff_location = -1
        for i in range(pass_band_location, -1, -1):
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
        for i in range(len(self.app.data21) - 1, initial_cutoff_location - 1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if db > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        self.app.markers[0].setFrequency(str(self.app.data21[peak_location].freq))
        self.app.markers[0].frequencyInput.setText(str(self.app.data21[peak_location].freq))

        cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                cutoff_location = i
                break

        cutoff_frequency = self.app.data21[cutoff_location].freq
        cutoff_gain = NanoVNASaver.gain(self.app.data21[cutoff_location]) - pass_band_db
        if cutoff_gain < -4:
            logger.debug("Cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         cutoff_gain)

        logger.debug("Found true cutoff frequency at %d", cutoff_frequency)

        self.cutoff_label.setText(NanoVNASaver.formatFrequency(cutoff_frequency) +
                                  " (" + str(round(cutoff_gain, 1)) + " dB)")
        self.app.markers[1].setFrequency(str(cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(cutoff_frequency))

        six_db_location = -1
        for i in range(cutoff_location, -1, -1):
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

        ten_db_location = -1
        for i in range(cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(six_db_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency))
        else:
            # # We derive 60 dB instead
            # factor = 10 * (-54 / decade_attenuation)
            # sixty_db_cutoff_frequency = round(six_db_cutoff_frequency + six_db_cutoff_frequency * factor)
            # self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency) + " (derived)")
            self.sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0:
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
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
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

        pass_band_db = NanoVNASaver.gain(self.app.data21[pass_band_location])

        logger.debug("Initial passband gain: %d", pass_band_db)

        initial_lower_cutoff_location = -1
        for i in range(pass_band_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
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
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found a cutoff location
                initial_upper_cutoff_location = i
                break

        if initial_upper_cutoff_location < 0:
            self.result_label.setText("Upper cutoff location not found.")
            return

        initial_upper_cutoff_frequency = self.app.data21[initial_upper_cutoff_location].freq

        logger.debug("Found initial upper cutoff frequency at %d", initial_upper_cutoff_frequency)

        peak_location = -1
        peak_db = NanoVNASaver.gain(self.app.data21[initial_lower_cutoff_location])
        for i in range(initial_lower_cutoff_location, initial_upper_cutoff_location, 1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if db > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        lower_cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                lower_cutoff_location = i
                break

        lower_cutoff_frequency = self.app.data21[lower_cutoff_location].freq
        lower_cutoff_gain = NanoVNASaver.gain(self.app.data21[lower_cutoff_location]) - pass_band_db

        if lower_cutoff_gain < -4:
            logger.debug("Lower cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         lower_cutoff_gain)

        logger.debug("Found true lower cutoff frequency at %d", lower_cutoff_frequency)

        self.lower_cutoff_label.setText(NanoVNASaver.formatFrequency(lower_cutoff_frequency) +
                                        " (" + str(round(lower_cutoff_gain, 1)) + " dB)")

        self.app.markers[1].setFrequency(str(lower_cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(lower_cutoff_frequency))

        upper_cutoff_location = -1
        pass_band_db = peak_db
        for i in range(peak_location, len(self.app.data21), 1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                upper_cutoff_location = i
                break

        upper_cutoff_frequency = self.app.data21[upper_cutoff_location].freq
        upper_cutoff_gain = NanoVNASaver.gain(self.app.data21[upper_cutoff_location]) - pass_band_db
        if upper_cutoff_gain < -4:
            logger.debug("Upper cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         upper_cutoff_gain)

        logger.debug("Found true upper cutoff frequency at %d", upper_cutoff_frequency)

        self.upper_cutoff_label.setText(NanoVNASaver.formatFrequency(upper_cutoff_frequency) +
                                        " (" + str(round(upper_cutoff_gain, 1)) + " dB)")
        self.app.markers[2].setFrequency(str(upper_cutoff_frequency))
        self.app.markers[2].frequencyInput.setText(str(upper_cutoff_frequency))

        span = upper_cutoff_frequency - lower_cutoff_frequency
        center_frequency = math.sqrt(lower_cutoff_frequency * upper_cutoff_frequency)
        q = center_frequency / span

        self.span_label.setText(NanoVNASaver.formatFrequency(span))
        self.center_frequency_label.setText(NanoVNASaver.formatFrequency(center_frequency))
        self.quality_label.setText(str(round(q, 2)))

        self.app.markers[0].setFrequency(str(round(center_frequency)))
        self.app.markers[0].frequencyInput.setText(str(round(center_frequency)))

        # Lower roll-off

        lower_six_db_location = -1
        for i in range(lower_cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 6:
                # We found 6dB location
                lower_six_db_location = i
                break

        if lower_six_db_location < 0:
            self.result_label.setText("Lower 6 dB location not found.")
            return
        lower_six_db_cutoff_frequency = self.app.data21[lower_six_db_location].freq
        self.lower_six_db_label.setText(NanoVNASaver.formatFrequency(lower_six_db_cutoff_frequency))

        ten_db_location = -1
        for i in range(lower_cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(lower_cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(lower_six_db_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.lower_sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency))
        else:
            # # We derive 60 dB instead
            # factor = 10 * (-54 / decade_attenuation)
            # sixty_db_cutoff_frequency = round(six_db_cutoff_frequency + six_db_cutoff_frequency * factor)
            # self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency) + " (derived)")
            self.lower_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.lower_db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.lower_db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.lower_db_per_octave_label.setText("Not calculated")
            self.lower_db_per_decade_label.setText("Not calculated")

        # Upper roll-off

        upper_six_db_location = -1
        for i in range(upper_cutoff_location, len(self.app.data21), 1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 6:
                # We found 6dB location
                upper_six_db_location = i
                break

        if upper_six_db_location < 0:
            self.result_label.setText("Upper 6 dB location not found.")
            return
        upper_six_db_cutoff_frequency = self.app.data21[upper_six_db_location].freq
        self.upper_six_db_label.setText(NanoVNASaver.formatFrequency(upper_six_db_cutoff_frequency))

        six_db_span = upper_six_db_cutoff_frequency - lower_six_db_cutoff_frequency

        self.six_db_span_label.setText(NanoVNASaver.formatFrequency(six_db_span))

        ten_db_location = -1
        for i in range(upper_cutoff_location, len(self.app.data21), 1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(upper_cutoff_location, len(self.app.data21), 1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(upper_six_db_location, len(self.app.data21), 1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.upper_sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency))
        else:
            # # We derive 60 dB instead
            # factor = 10 * (-54 / decade_attenuation)
            # sixty_db_cutoff_frequency = round(six_db_cutoff_frequency + six_db_cutoff_frequency * factor)
            # self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency) + " (derived)")
            self.upper_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0:
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
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        self.reset()

        if len(self.app.data21) == 0:
            logger.debug("No data to analyse")
            self.result_label.setText("No data to analyse.")
            return

        peak_location = -1
        peak_db = NanoVNASaver.gain(self.app.data21[0])
        for i in range(len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if db > peak_db:
                peak_db = db
                peak_location = i

        logger.debug("Found peak of %f at %d", peak_db, self.app.data[peak_location].freq)

        lower_cutoff_location = -1
        pass_band_db = peak_db
        for i in range(len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                lower_cutoff_location = i
                break

        lower_cutoff_frequency = self.app.data21[lower_cutoff_location].freq
        lower_cutoff_gain = NanoVNASaver.gain(self.app.data21[lower_cutoff_location]) - pass_band_db

        if lower_cutoff_gain < -4:
            logger.debug("Lower cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         lower_cutoff_gain)

        logger.debug("Found true lower cutoff frequency at %d", lower_cutoff_frequency)

        self.lower_cutoff_label.setText(NanoVNASaver.formatFrequency(lower_cutoff_frequency) +
                                        " (" + str(round(lower_cutoff_gain, 1)) + " dB)")

        self.app.markers[1].setFrequency(str(lower_cutoff_frequency))
        self.app.markers[1].frequencyInput.setText(str(lower_cutoff_frequency))

        upper_cutoff_location = -1
        for i in range(len(self.app.data21)-1, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 3:
                # We found the cutoff location
                upper_cutoff_location = i
                break

        upper_cutoff_frequency = self.app.data21[upper_cutoff_location].freq
        upper_cutoff_gain = NanoVNASaver.gain(self.app.data21[upper_cutoff_location]) - pass_band_db
        if upper_cutoff_gain < -4:
            logger.debug("Upper cutoff frequency found at %f dB - insufficient data points for true -3 dB point.",
                         upper_cutoff_gain)

        logger.debug("Found true upper cutoff frequency at %d", upper_cutoff_frequency)

        self.upper_cutoff_label.setText(NanoVNASaver.formatFrequency(upper_cutoff_frequency) +
                                        " (" + str(round(upper_cutoff_gain, 1)) + " dB)")
        self.app.markers[2].setFrequency(str(upper_cutoff_frequency))
        self.app.markers[2].frequencyInput.setText(str(upper_cutoff_frequency))

        span = upper_cutoff_frequency - lower_cutoff_frequency
        center_frequency = math.sqrt(lower_cutoff_frequency * upper_cutoff_frequency)
        q = center_frequency / span

        self.span_label.setText(NanoVNASaver.formatFrequency(span))
        self.center_frequency_label.setText(NanoVNASaver.formatFrequency(center_frequency))
        self.quality_label.setText(str(round(q, 2)))

        self.app.markers[0].setFrequency(str(round(center_frequency)))
        self.app.markers[0].frequencyInput.setText(str(round(center_frequency)))

        # Lower roll-off

        lower_six_db_location = -1
        for i in range(lower_cutoff_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 6:
                # We found 6dB location
                lower_six_db_location = i
                break

        if lower_six_db_location < 0:
            self.result_label.setText("Lower 6 dB location not found.")
            return
        lower_six_db_cutoff_frequency = self.app.data21[lower_six_db_location].freq
        self.lower_six_db_label.setText(NanoVNASaver.formatFrequency(lower_six_db_cutoff_frequency))

        ten_db_location = -1
        for i in range(lower_cutoff_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(lower_cutoff_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(lower_six_db_location, len(self.app.data21)):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.lower_sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency))
        else:
            # # We derive 60 dB instead
            # factor = 10 * (-54 / decade_attenuation)
            # sixty_db_cutoff_frequency = round(six_db_cutoff_frequency + six_db_cutoff_frequency * factor)
            # self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency) + " (derived)")
            self.lower_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0:
            octave_attenuation, decade_attenuation = self.calculateRolloff(ten_db_location, twenty_db_location)
            self.lower_db_per_octave_label.setText(str(round(octave_attenuation, 3)) + " dB / octave")
            self.lower_db_per_decade_label.setText(str(round(decade_attenuation, 3)) + " dB / decade")
        else:
            self.lower_db_per_octave_label.setText("Not calculated")
            self.lower_db_per_decade_label.setText("Not calculated")

        # Upper roll-off

        upper_six_db_location = -1
        for i in range(upper_cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 6:
                # We found 6dB location
                upper_six_db_location = i
                break

        if upper_six_db_location < 0:
            self.result_label.setText("Upper 6 dB location not found.")
            return
        upper_six_db_cutoff_frequency = self.app.data21[upper_six_db_location].freq
        self.upper_six_db_label.setText(NanoVNASaver.formatFrequency(upper_six_db_cutoff_frequency))

        six_db_span = upper_six_db_cutoff_frequency - lower_six_db_cutoff_frequency

        self.six_db_span_label.setText(NanoVNASaver.formatFrequency(six_db_span))

        ten_db_location = -1
        for i in range(upper_cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 10:
                # We found 6dB location
                ten_db_location = i
                break

        twenty_db_location = -1
        for i in range(upper_cutoff_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 20:
                # We found 6dB location
                twenty_db_location = i
                break

        sixty_db_location = -1
        for i in range(upper_six_db_location, -1, -1):
            db = NanoVNASaver.gain(self.app.data21[i])
            if (pass_band_db - db) > 60:
                # We found 60dB location! Wow.
                sixty_db_location = i
                break

        if sixty_db_location > 0:
            sixty_db_cutoff_frequency = self.app.data21[sixty_db_location].freq
            self.upper_sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency))
        else:
            # # We derive 60 dB instead
            # factor = 10 * (-54 / decade_attenuation)
            # sixty_db_cutoff_frequency = round(six_db_cutoff_frequency + six_db_cutoff_frequency * factor)
            # self.sixty_db_label.setText(NanoVNASaver.formatFrequency(sixty_db_cutoff_frequency) + " (derived)")
            self.upper_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0:
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
