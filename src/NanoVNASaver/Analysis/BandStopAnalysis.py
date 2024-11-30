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
from NanoVNASaver.Analysis.BandPassAnalysis import BandPassAnalysis
from NanoVNASaver.Analysis.Base import CUTOFF_VALS

logger = logging.getLogger(__name__)


class BandStopAnalysis(BandPassAnalysis):
    def __init__(self, app):
        super().__init__(app)
        self.set_titel("Band stop filter analysis")

    def find_center(self, gains: list[float]) -> int:
        return max(enumerate(gains), key=lambda i: i[1])[0]

    def find_bounderies(
        self, gains: list[float], _: int, peak_db: float
    ) -> dict[str, int]:
        cutoff_pos = {}
        for attn in CUTOFF_VALS:
            (
                cutoff_pos[f"{attn:.1f}dB_l"],
                cutoff_pos[f"{attn:.1f}dB_r"],
            ) = At.dip_cut_offs(gains, peak_db, attn)
        return cutoff_pos
