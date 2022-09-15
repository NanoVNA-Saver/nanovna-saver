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
import struct
from typing import List

import serial
import numpy as np
from PyQt5 import QtGui

from NanoVNASaver.Hardware.Serial import drain_serial, Interface
from NanoVNASaver.Hardware.VNA import VNA

logger = logging.getLogger(__name__)


class TinySA(VNA):
    name = "tinySA"
    screenwidth = 320
    screenheight = 240
    valid_datapoints = (290, )

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.features = {'Screenshots'}
        logger.debug("Setting initial start,stop")
        self.start, self.stop = self._get_running_frequencies()
        self.sweep_max_freq_Hz = 950e6
        self._sweepdata = []

    def _get_running_frequencies(self):

        logger.debug("Reading values: frequencies")
        try:
            frequencies = super().readValues("frequencies")
            return frequencies[0], frequencies[-1]
        except Exception as e:
            logger.warning("%s reading frequencies", e)
            logger.info("falling back to generic")

        return VNA._get_running_frequencies(self)

    def _capture_data(self) -> bytes:
        timeout = self.serial.timeout
        with self.serial.lock:
            drain_serial(self.serial)
            self.serial.write("capture\r".encode('ascii'))
            self.serial.readline()
            self.serial.timeout = 4
            image_data = self.serial.read(
                self.screenwidth * self.screenheight * 2)
            self.serial.timeout = timeout
        self.serial.timeout = timeout
        return image_data

    def _convert_data(self, image_data: bytes) -> bytes:
        rgb_data = struct.unpack(
            f">{self.screenwidth * self.screenheight}H",
            image_data)
        rgb_array = np.array(rgb_data, dtype=np.uint32)
        return (0xFF000000 +
                ((rgb_array & 0xF800) << 8) +
                ((rgb_array & 0x07E0) << 5) +
                ((rgb_array & 0x001F) << 3))

    def getScreenshot(self) -> QtGui.QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.connected():
            return QtGui.QPixmap()
        try:
            rgba_array = self._convert_data(self._capture_data())
            image = QtGui.QImage(
                rgba_array,
                self.screenwidth,
                self.screenheight,
                QtGui.QImage.Format_ARGB32)
            logger.debug("Captured screenshot")
            return QtGui.QPixmap(image)
        except serial.SerialException as exc:
            logger.exception(
                "Exception while capturing screenshot: %s", exc)
        return QtGui.QPixmap()

    def resetSweep(self, start: int, stop: int):
        return

    def setSweep(self, start, stop):
        self.start = start
        self.stop = stop
        list(self.exec_command(f"sweep {start} {stop} {self.datapoints}"))
        list(self.exec_command("trigger auto"))

    def readFrequencies(self) -> List[int]:
        logger.debug("readFrequencies")
        return [int(line) for line in self.exec_command("frequencies")]

    def readValues(self, value) -> List[str]:
        logger.debug("Read: %s", value)
        if value == "data 0":
            self._sweepdata = [f"0 {line.strip()}"
                               for line in self.exec_command("data")]
        return self._sweepdata
