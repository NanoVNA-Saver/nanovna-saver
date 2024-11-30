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

import NanoVNASaver.AnalyticTools as At
from NanoVNASaver.Analysis.Base import CUTOFF_VALS
from NanoVNASaver.Analysis.HighPassAnalysis import HighPassAnalysis

logger = logging.getLogger(__name__)


class LowPassAnalysis(HighPassAnalysis):
    def __init__(self, app):
        super().__init__(app)

        self.set_titel("Lowpass filter analysis")

    def find_cutoffs(
        self, gains: list[float], peak: int, peak_db: float
    ) -> dict[str, int]:
        return {
            f"{attn:.1f}dB": At.cut_off_right(gains, peak, peak_db, attn)
            for attn in CUTOFF_VALS
        }
