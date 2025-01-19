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

import serial
from PyQt6.QtGui import QImage, QPixmap

from NanoVNASaver.Hardware.NanoVNA import NanoVNA
from NanoVNASaver.Hardware.Serial import Interface

logger = logging.getLogger(__name__)


class NanoVNA_F_V3(NanoVNA):
    name = "NanoVNA-F_V3"
    screenwidth = 800
    screenheight = 480
    valid_datapoints = (101, 11, 51, 201, 301, 401, 501, 601, 701, 801)
    sweep_points_min = 11
    sweep_points_max = 801

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.sweep_max_freq_Hz = 6.3e9

    def getScreenshot(self) -> QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.connected():
            return QPixmap()
        try:
            rgba_array = self._capture_data()
            image = QImage(
                rgba_array,
                self.screenwidth,
                self.screenheight,
                QImage.Format.Format_RGB16,
            )
            logger.debug("Captured screenshot")
            return QPixmap(image)
        except serial.SerialException as exc:
            logger.exception("Exception while capturing screenshot: %s", exc)
        return QPixmap()

    def read_features(self):
        super().read_features()
        result = " ".join(self.exec_command("help")).split()
        if "sn:" or "SN:" in result:
            self.features.add("SN")
            self.SN = self.getSerialNumber()

    def getSerialNumber(self) -> str:
        return (
            " ".join(list(self.exec_command("SN")))
            if "SN:" in " ".join(self.exec_command("help")).split()
            else " ".join(list(self.exec_command("sn")))
        )
