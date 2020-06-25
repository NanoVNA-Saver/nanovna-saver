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

from NanoVNASaver.Formatting import format_frequency

from NanoVNASaver.Analysis import Analysis

logger = logging.getLogger(__name__)


class BandPassAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self._widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout()
        self._widget.setLayout(layout)
        layout.addRow(QtWidgets.QLabel("Band pass filter analysis"))
        layout.addRow(
            QtWidgets.QLabel(
                f"Please place {self.app.markers[0].name} in the filter passband."))
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
            self.result_label.setText(
                f"Please place {self.app.markers[0].name} in the passband.")
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
            logger.debug("Lower cutoff frequency found at %f dB"
                         " - insufficient data points for true -3 dB point.",
                         lower_cutoff_gain)
        logger.debug("Found true lower cutoff frequency at %d", lower_cutoff_frequency)

        self.lower_cutoff_label.setText(
            f"{format_frequency(lower_cutoff_frequency)}"
            f" ({round(lower_cutoff_gain, 1)} dB)")

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
            logger.debug("Upper cutoff frequency found at %f dB"
                         " - insufficient data points for true -3 dB point.",
                         upper_cutoff_gain)

        logger.debug("Found true upper cutoff frequency at %d", upper_cutoff_frequency)

        self.upper_cutoff_label.setText(
            f"{format_frequency(upper_cutoff_frequency)}"
            f" ({round(upper_cutoff_gain, 1)} dB)")
        self.app.markers[2].setFrequency(str(upper_cutoff_frequency))
        self.app.markers[2].frequencyInput.setText(str(upper_cutoff_frequency))

        span = upper_cutoff_frequency - lower_cutoff_frequency
        center_frequency = math.sqrt(
            lower_cutoff_frequency * upper_cutoff_frequency)
        q = center_frequency / span

        self.span_label.setText(format_frequency(span))
        self.center_frequency_label.setText(
            format_frequency(center_frequency))
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
        self.lower_six_db_label.setText(
            format_frequency(lower_six_db_cutoff_frequency))

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
                self.lower_sixty_db_label.setText(
                    format_frequency(sixty_db_cutoff_frequency))
            elif ten_db_location != -1 and twenty_db_location != -1:
                ten = self.app.data21[ten_db_location].freq
                twenty = self.app.data21[twenty_db_location].freq
                sixty_db_frequency = ten * \
                    10 ** (5 * (math.log10(twenty) - math.log10(ten)))
                self.lower_sixty_db_label.setText(
                    f"{format_frequency(sixty_db_frequency)} (derived)")
            else:
                self.lower_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(
                ten_db_location, twenty_db_location)
            self.lower_db_per_octave_label.setText(
                str(round(octave_attenuation, 3)) + " dB / octave")
            self.lower_db_per_decade_label.setText(
                str(round(decade_attenuation, 3)) + " dB / decade")
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
        self.upper_six_db_label.setText(
            format_frequency(upper_six_db_cutoff_frequency))

        six_db_span = upper_six_db_cutoff_frequency - lower_six_db_cutoff_frequency

        self.six_db_span_label.setText(
            format_frequency(six_db_span))

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
            self.upper_sixty_db_label.setText(
                format_frequency(sixty_db_cutoff_frequency))
        elif ten_db_location != -1 and twenty_db_location != -1:
            ten = self.app.data21[ten_db_location].freq
            twenty = self.app.data21[twenty_db_location].freq
            sixty_db_frequency = ten * \
                10 ** (5 * (math.log10(twenty) - math.log10(ten)))
            self.upper_sixty_db_label.setText(
                f"{format_frequency(sixty_db_frequency)} (derived)")
        else:
            self.upper_sixty_db_label.setText("Not calculated")

        if ten_db_location > 0 and twenty_db_location > 0 and ten_db_location != twenty_db_location:
            octave_attenuation, decade_attenuation = self.calculateRolloff(
                ten_db_location, twenty_db_location)
            self.upper_db_per_octave_label.setText(
                f"{round(octave_attenuation, 3)} dB / octave")
            self.upper_db_per_decade_label.setText(
                f"{round(decade_attenuation, 3)} dB / decade")
        else:
            self.upper_db_per_octave_label.setText("Not calculated")
            self.upper_db_per_decade_label.setText("Not calculated")

        if upper_cutoff_gain < -4 or lower_cutoff_gain < -4:
            self.result_label.setText(
                f"Analysis complete ({len(self.app.data)} points)\n"
                f"Insufficient data for analysis. Increase segment count.")
        else:
            self.result_label.setText(
                f"Analysis complete ({len(self.app.data)} points)")
