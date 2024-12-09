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
import logging
import math

from PyQt6 import QtWidgets

import NanoVNASaver.AnalyticTools as At
from NanoVNASaver.Analysis.Base import CUTOFF_VALS, MIN_CUTOFF_DAMPING, Analysis
from NanoVNASaver.Formatting import format_frequency

logger = logging.getLogger(__name__)


class BandPassAnalysis(Analysis):
    def __init__(self, app) -> None:
        super().__init__(app)

        for label in (
            "octave_l",
            "octave_r",
            "decade_l",
            "decade_r",
            "freq_center",
            "span_3.0dB",
            "span_6.0dB",
            "q_factor",
        ):
            self.label[label] = QtWidgets.QLabel()
        for attn in CUTOFF_VALS:
            self.label[f"{attn:.1f}dB_l"] = QtWidgets.QLabel()
            self.label[f"{attn:.1f}dB_r"] = QtWidgets.QLabel()

        layout = self.layout
        layout.addRow(self.label["titel"])
        layout.addRow(
            QtWidgets.QLabel(
                f"Please place {self.app.markers[0].name}"
                f" in the filter passband."
            )
        )
        layout.addRow("Result:", self.label["result"])
        layout.addRow(QtWidgets.QLabel(""))

        layout.addRow("Center frequency:", self.label["freq_center"])
        layout.addRow("Bandwidth (-3 dB):", self.label["span_3.0dB"])
        layout.addRow("Quality factor:", self.label["q_factor"])
        layout.addRow("Bandwidth (-6 dB):", self.label["span_6.0dB"])
        layout.addRow(QtWidgets.QLabel(""))

        layout.addRow(QtWidgets.QLabel("Lower side:"))
        layout.addRow("Cutoff frequency:", self.label["3.0dB_l"])
        layout.addRow("-6 dB point:", self.label["6.0dB_l"])
        layout.addRow("-60 dB point:", self.label["60.0dB_l"])
        layout.addRow("Roll-off:", self.label["octave_l"])
        layout.addRow("Roll-off:", self.label["decade_l"])
        layout.addRow(QtWidgets.QLabel(""))

        layout.addRow(QtWidgets.QLabel("Upper side:"))
        layout.addRow("Cutoff frequency:", self.label["3.0dB_r"])
        layout.addRow("-6 dB point:", self.label["6.0dB_r"])
        layout.addRow("-60 dB point:", self.label["60.0dB_r"])
        layout.addRow("Roll-off:", self.label["octave_r"])
        layout.addRow("Roll-off:", self.label["decade_r"])

        self.set_titel("Band pass filter analysis")

    def runAnalysis(self) -> None:
        if not self.app.data.s21:
            logger.debug("No data to analyse")
            self.set_result("No data to analyse.")
            return

        self.reset()
        s21 = self.app.data.s21
        gains = [d.gain for d in s21]

        if (peak := self.find_center(gains)) < 0:
            return
        peak_db = gains[peak]
        logger.debug("Filter center pos: %d(%fdB)", peak, peak_db)

        # find passband bounderies
        cutoff_pos = self.find_bounderies(gains, peak, peak_db)
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

        self.derive_60dB(cutoff_pos, cutoff_freq)

        result = {
            "span_3.0dB": cutoff_freq["3.0dB_r"] - cutoff_freq["3.0dB_l"],
            "span_6.0dB": cutoff_freq["6.0dB_r"] - cutoff_freq["6.0dB_l"],
            "freq_center": math.sqrt(
                cutoff_freq["3.0dB_l"] * cutoff_freq["3.0dB_r"]
            ),
        }
        result["q_factor"] = result["freq_center"] / result["span_3.0dB"]

        result["octave_l"], result["decade_l"] = At.calculate_rolloff(
            s21, cutoff_pos["10.0dB_l"], cutoff_pos["20.0dB_l"]
        )
        result["octave_r"], result["decade_r"] = At.calculate_rolloff(
            s21, cutoff_pos["10.0dB_r"], cutoff_pos["20.0dB_r"]
        )

        for label, val in cutoff_freq.items():
            self.label[label].setText(
                f"{format_frequency(val)}" f" ({cutoff_gain[label]:.1f} dB)"
            )
        for label in ("freq_center", "span_3.0dB", "span_6.0dB"):
            self.label[label].setText(format_frequency(result[label]))
        self.label["q_factor"].setText(f"{result['q_factor']:.2f}")

        for label in ("octave_l", "decade_l", "octave_r", "decade_r"):
            self.label[label].setText(f"{result[label]:.3f}dB/{label[:-2]}")

        self.app.markers[0].setFrequency(f"{result['freq_center']}")
        self.app.markers[1].setFrequency(f"{cutoff_freq['3.0dB_l']}")
        self.app.markers[2].setFrequency(f"{cutoff_freq['3.0dB_r']}")

        if (
            cutoff_gain["3.0dB_l"] < MIN_CUTOFF_DAMPING
            or cutoff_gain["3.0dB_r"] < MIN_CUTOFF_DAMPING
        ):
            logger.warning(
                "Data points insufficient for true -3 dB points."
                "Cutoff gains: %fdB, %fdB",
                cutoff_gain["3.0dB_l"],
                cutoff_gain["3.0dB_r"],
            )
            self.set_result(
                f"Analysis complete ({len(s21)} points)\n"
                f"Insufficient data for analysis. Increase segment count."
            )
            return
        self.set_result(f"Analysis complete ({len(s21)} points)")

    def derive_60dB(
        self, cutoff_pos: dict[str, int], cutoff_freq: dict[str, float]
    ) -> None:
        """derive 60dB cutoff if needed an possible

        Args:
            cutoff_pos (dict[str, int])
            cutoff_freq (dict[str, float])
        """
        if (
            math.isnan(cutoff_freq["60.0dB_l"])
            and cutoff_pos["20.0dB_l"] != -1
            and cutoff_pos["10.0dB_l"] != -1
        ):
            cutoff_freq["60.0dB_l"] = cutoff_freq["10.0dB_l"] * 10 ** (
                5
                * (
                    math.log10(cutoff_pos["20.0dB_l"])
                    - math.log10(cutoff_pos["10.0dB_l"])
                )
            )
        if (
            math.isnan(cutoff_freq["60.0dB_r"])
            and cutoff_pos["20.0dB_r"] != -1
            and cutoff_pos["10.0dB_r"] != -1
        ):
            cutoff_freq["60.0dB_r"] = cutoff_freq["10.0dB_r"] * 10 ** (
                5
                * (
                    math.log10(cutoff_pos["20.0dB_r"])
                    - math.log10(cutoff_pos["10.0dB_r"])
                )
            )

    def find_center(self, gains: list[float]) -> int:
        marker = self.app.markers[0]
        if marker.location <= 0 or marker.location >= len(gains) - 1:
            logger.debug(
                "No valid location for %s (%s)", marker.name, marker.location
            )
            self.set_result(f"Please place {marker.name} in the passband.")
            return -1

        # find center of passband based on marker pos
        if (peak := At.center_from_idx(gains, marker.location)) < 0:
            self.set_result("Bandpass center not found")
            return -1
        return peak

    def find_bounderies(
        self, gains: list[float], peak: int, peak_db: float
    ) -> dict[str, int]:
        cutoff_pos = {}
        for attn in CUTOFF_VALS:
            cutoff_pos[f"{attn:.1f}dB_l"] = At.cut_off_left(
                gains, peak, peak_db, attn
            )
            cutoff_pos[f"{attn:.1f}dB_r"] = At.cut_off_right(
                gains, peak, peak_db, attn
            )
        return cutoff_pos
