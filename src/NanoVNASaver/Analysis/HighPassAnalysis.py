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
import math

from PyQt6 import QtWidgets

import NanoVNASaver.AnalyticTools as At
from NanoVNASaver.Analysis.Base import CUTOFF_VALS, MIN_CUTOFF_DAMPING, Analysis
from NanoVNASaver.Formatting import format_frequency

logger = logging.getLogger(__name__)


class HighPassAnalysis(Analysis):
    def __init__(self, app):
        super().__init__(app)

        self.label["octave"] = QtWidgets.QLabel()
        self.label["decade"] = QtWidgets.QLabel()
        for attn in CUTOFF_VALS:
            self.label[f"{attn:.1f}dB"] = QtWidgets.QLabel()
            self.label[f"{attn:.1f}dB"] = QtWidgets.QLabel()

        layout = self.layout
        layout.addRow(self.label["titel"])
        layout.addRow(
            QtWidgets.QLabel(
                f"Please place {self.app.markers[0].name}"
                f" in the filter passband."
            )
        )
        layout.addRow("Result:", self.label["result"])
        layout.addRow("Cutoff frequency:", self.label["3.0dB"])
        layout.addRow("-6 dB point:", self.label["6.0dB"])
        layout.addRow("-60 dB point:", self.label["60.0dB"])
        layout.addRow("Roll-off:", self.label["octave"])
        layout.addRow("Roll-off:", self.label["decade"])

        self.set_titel("Highpass analysis")

    def runAnalysis(self):
        if not self.app.data.s21:
            logger.debug("No data to analyse")
            self.set_result("No data to analyse.")
            return

        self.reset()
        s21 = self.app.data.s21
        gains = [d.gain for d in s21]

        if (peak := self.find_level(gains)) < 0:
            return
        peak_db = gains[peak]
        logger.debug("Passband position: %d(%fdB)", peak, peak_db)

        cutoff_pos = self.find_cutoffs(gains, peak, peak_db)
        cutoff_freq = {
            att: s21[val].freq if val >= 0 else math.nan
            for att, val in cutoff_pos.items()
        }
        cutoff_gain = {
            att: gains[val] if val >= 0 else math.nan
            for att, val in cutoff_pos.items()
        }
        logger.debug("Cuttoff frequencies: %s", cutoff_freq)
        logger.debug("Cuttoff gains: %s", cutoff_gain)

        octave, decade = At.calculate_rolloff(
            s21, cutoff_pos["10.0dB"], cutoff_pos["20.0dB"]
        )

        if cutoff_gain["3.0dB"] < MIN_CUTOFF_DAMPING:
            logger.debug(
                "Cutoff frequency found at %f dB"
                " - insufficient data points for true -3 dB point.",
                cutoff_gain,
            )
        logger.debug("Found true cutoff frequency at %d", cutoff_freq["3.0dB"])

        for label, val in cutoff_freq.items():
            self.label[label].setText(
                f"{format_frequency(val)}" f" ({cutoff_gain[label]:.1f} dB)"
            )

        self.label["octave"].setText(f"{octave:.3f}dB/octave")
        self.label["decade"].setText(f"{decade:.3f}dB/decade")

        self.app.markers[0].setFrequency(str(s21[peak].freq))
        self.app.markers[1].setFrequency(str(cutoff_freq["3.0dB"]))
        self.app.markers[2].setFrequency(str(cutoff_freq["6.0dB"]))

        self.set_result(f"Analysis complete ({len(s21)}) points)")

    def find_level(self, gains: list[float]) -> int:
        marker = self.app.markers[0]
        logger.debug("Pass band location: %d", marker.location)
        if marker.location < 0:
            self.set_result(f"Please place {marker.name} in the passband.")
            return -1
        return At.center_from_idx(gains, marker.location)

    def find_cutoffs(
        self, gains: list[float], peak: int, peak_db: float
    ) -> dict[str, int]:
        return {
            f"{attn:.1f}dB": At.cut_off_left(gains, peak, peak_db, attn)
            for attn in CUTOFF_VALS
        }
