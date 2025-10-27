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
from PySide6.QtGui import QPixmap

from .Convert import get_rgb16_pixmap
from .NanoVNA import NanoVNA
from .Serial import Interface

logger = logging.getLogger(__name__)


class SV4401A(NanoVNA):
    name = "SV4401A"
    screenwidth = 1024
    screenheight = 600
    valid_datapoints: tuple[int, ...] = (
        501,
        101,
        1001,
    )
    sweep_points_min = 101
    sweep_points_max = 1001

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.sweep_max_freq_hz = 4.4e9

    def init_features(self) -> None:
        super().init_features()
        self.features.remove("Scan mask command")
        self.features.add("Scan command")
        self.sweep_method = "scan"

    def getScreenshot(self) -> QPixmap:
        logger.debug("Capturing screenshot...")
        self.serial.timeout = 8
        if not self.connected():
            return QPixmap()
        try:
            logger.debug("Captured screenshot")
            return get_rgb16_pixmap(
                self._capture_data(), self.screenwidth, self.screenheight
            )
        except serial.SerialException as exc:
            logger.exception("Exception while capturing screenshot: %s", exc)
        return QPixmap()

    def setSweep(self, start, stop):
        self.start = start
        self.stop = stop
        list(self.exec_command(f"scan {start} {stop} {self.datapoints}"))
