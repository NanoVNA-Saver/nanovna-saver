#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
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

from NanoVNASaver.Hardware.NanoVNA_H import NanoVNA_H
from NanoVNASaver.Hardware.Serial import Interface

logger = logging.getLogger(__name__)


class NanoVNA_H4(NanoVNA_H):
    name = "NanoVNA-H4"
    screenwidth = 480
    screenheight = 320
    valid_datapoints = (101, 11, 51, 201, 401)

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.sweep_max_freq_Hz = 1500e6
        self.sweep_method = "scan"
        if "Scan mask command" in self.features:
            self.sweep_method = "scan_mask"

    # def read_features(self):
    #     logger.debug("read_features")
    #     super().read_features()
    #     if self.readFirmware().find("DiSlord") > 0:
    #         self.features.add("Customizable data points")
    #         logger.info("VNA has 201 datapoints capability")
    #         self.valid_datapoints = (201, 11, 51,101)
