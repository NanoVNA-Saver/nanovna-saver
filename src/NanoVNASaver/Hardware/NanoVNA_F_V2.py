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

from ..utils import Version
from .Convert import get_rgb16_pixmap
from .NanoVNA import NanoVNA
from .Serial import Interface

logger = logging.getLogger(__name__)


class NanoVNA_F_V2(NanoVNA):
    name = "NanoVNA-F_V2"
    screenwidth = 800
    screenheight = 480
    valid_datapoints: tuple[int, ...] = (101, 11, 51, 201, 301)
    sweep_points_min = 11
    sweep_points_max = 301

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.sweep_max_freq_hz = 3e9
        self.version = self.read_firmware_version()
        # max datapoints reach up to 301 since version 0.5.0
        if self.version >= Version.parse("0.5.0"):
            pass
        # max datapoints reach up to 201 since version 0.2.0
        elif self.version >= Version.parse("0.2.0"):
            self.valid_datapoints = (101, 11, 51, 201)
            self.sweep_points_max = 201
        # max datapoints reach up to 101 before version 0.2.0
        else:
            self.valid_datapoints = (101, 11, 51)
            self.sweep_points_max = 101

    def getScreenshot(self) -> QPixmap:
        logger.debug("Capturing screenshot...")
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
    """
    Add missing function to fix SN display in device setting window
    Copied from _F_V3
    """

    def init_features(self) -> None:
        super().init_features()
        result = " ".join(self.exec_command("help")).lower().split()
        if "sn:" in result:
            self.features.add("SN")
            self.SN = self.getSerialNumber()


    def read_firmware_version(self) -> "Version":
        """For example, command version in NanoVNA_F_V2 and NanoVNA_F_V3
        returns as this 0.5.8
        """
        result = list(self.exec_command("version"))
        logger.debug("firmware version result:\n%s", result[0])
        return Version.parse(result[0])

    def get_features(self):
        super().get_features()
        result = " ".join(self.exec_command("help")).split()
        if "sn:" or "SN:" in result:
            self.features.add("SN")
            self.SN = self.getSerialNumber()
        return self.features    # add missing return fixes combobox not getting initialized with proper values for valid sweep points

    def getSerialNumber(self) -> str:
        return (
            " ".join(list(self.exec_command("SN")))
            if "SN:" in " ".join(self.exec_command("help")).split()
            else " ".join(list(self.exec_command("sn")))
        )
