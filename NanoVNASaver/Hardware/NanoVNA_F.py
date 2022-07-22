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
from PyQt5 import QtGui
from typing import List, Iterator
from collections import OrderedDict
from NanoVNASaver.Hardware.NanoVNA import VNA
from NanoVNASaver.Hardware.NanoVNA import NanoVNA
from NanoVNASaver.Hardware.Serial import Interface

logger = logging.getLogger(__name__)
#del DISLORD_BW
DISLORD_BW = OrderedDict((
    (10, 99),
    (33, 29),
    (100, 9),
    (333, 2),
    (1000, 0),
))


class NanoVNA_F(NanoVNA):
    name = "NanoVNA-F"
    screenwidth = 800
    screenheight = 480
    valid_datapoints = (301, 201, 101, 51)

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.bandwidth = 333
        self.sweep_max_freq_Hz = 1500e6
    
    def get_bandwidths(self) -> List[int]:
        logger.debug("get bandwidths")
        if self.bw_method == "dislord":
            return list(DISLORD_BW.keys())
        result = " ".join(list(self.exec_command("bandwidth")))
        try:
            result = result.split(" {")[1].strip("}")
            return sorted([int(i) for i in result.split("|")])
        except IndexError:
            return [1000, ]

    def set_bandwidth(self, bandwidth: int):
        bw_val = DISLORD_BW[bandwidth] \
            if self.bw_method == "dislord" else bandwidth
        result = " ".join(self.exec_command(f"bandwidth {bw_val}"))
        if self.bw_method == "ttrftech" and result:
            raise IOError(f"set_bandwith({bandwidth}: {result}")
        self.bandwidth = bandwidth    
    def getScreenshot(self) -> QtGui.QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.connected():
            return QtGui.QPixmap()
        try:
            rgba_array = self._capture_data()
            image = QtGui.QImage(
                rgba_array,
                self.screenwidth,
                self.screenheight,
                QtGui.QImage.Format_RGB16)
            logger.debug("Captured screenshot")
            return QtGui.QPixmap(image)
        except serial.SerialException as exc:
            logger.exception(
                "Exception while capturing screenshot: %s", exc)
        return QtGui.QPixmap()   
