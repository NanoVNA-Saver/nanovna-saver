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


class NanoVNA_F_V2(NanoVNA):
    name = "NanoVNA-F_V2"
    screenwidth = 800
    screenheight = 480

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.sweep_max_freq_Hz = 3e9

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
