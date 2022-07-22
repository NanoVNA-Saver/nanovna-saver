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
from typing import List

from collections import OrderedDict
from NanoVNASaver.Hardware.NanoVNA import VNA
from NanoVNASaver.Hardware.Serial import Interface

logger = logging.getLogger(__name__)
valid_bandwidths = [10, 33, 100, 333, 1000]

BANDWIDTHS = OrderedDict(
    (10, 99),
    (33, 29),
    (100, 9),
    (333, 2),
    (1000, 0),
)


class NanoVNA_F(VNA):
    name = "NanoVNA-F"
    screenwidth = 800
    screenheight = 480
    valid_datapoints = (301, 201, 101, 51)

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.bandwidth = 1000
        self.sweep_max_freq_Hz = 1500e6

    def get_bandwidths(self) -> List[int]:
        return BANDWIDTHS.keys()

    def set_bandwidth(self, bandwidth: int):
        self.exec_command(f"bandwidth {BANDWIDTHS[bandwidth]}")
        self.bandwidth = bandwidth
