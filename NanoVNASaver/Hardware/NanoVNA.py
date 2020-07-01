#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
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
from time import sleep
from typing import List

import serial
import numpy as np
from PyQt5 import QtGui

from NanoVNASaver.Hardware.Serial import drain_serial
from NanoVNASaver.Hardware.VNA import VNA, Version

logger = logging.getLogger(__name__)


class NanoVNA(VNA):
    name = "NanoVNA"
    screenwidth = 320
    screenheight = 240

    def __init__(self, app, serial_port):
        super().__init__(app, serial_port)
        self.version = Version(self.readVersion())

        logger.debug("Testing against 0.2.0")
        if self.version.version_string.find("extended with scan") > 0:
            logger.debug("Incompatible scan command detected.")
            self.features.add("Incompatible scan command")
            self.useScan = False
        elif self.version >= Version("0.2.0"):
            logger.debug("Newer than 0.2.0, using new scan command.")
            self.features.add("New scan command")
            self.useScan = True
        else:
            logger.debug("Older than 0.2.0, using old sweep command.")
            self.features.add("Original sweep method")
            self.useScan = False
        self.readFeatures()

    def isValid(self):
        return True

    def getCalibration(self) -> str:
        logger.debug("Reading calibration info.")
        if not self.serial.is_open:
            return "Not connected."
        with self.app.serialLock:
            try:
                drain_serial(self.serial)
                self.serial.write("cal\r".encode('ascii'))
                result = ""
                data = ""
                sleep(0.1)
                while "ch>" not in data:
                    data = self.serial.readline().decode('ascii')
                    result += data
                values = result.splitlines()
                return values[1]
            except serial.SerialException as exc:
                logger.exception("Exception while reading calibration info: %s", exc)
        return "Unknown"

    def getScreenshot(self) -> QtGui.QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.serial.is_open:
            return QtGui.QPixmap()
        try:
            with self.app.serialLock:
                drain_serial(self.serial)
                timeout = self.serial.timeout
                self.serial.write("capture\r".encode('ascii'))
                self.serial.timeout = 4
                self.serial.readline()
                image_data = self.serial.read(
                    self.screenwidth * self.screenheight * 2)
                self.serial.timeout = timeout
            rgb_data = struct.unpack(
                f">{self.screenwidth * self.screenheight}H",
                image_data)
            rgb_array = np.array(rgb_data, dtype=np.uint32)
            rgba_array = (0xFF000000 +
                            ((rgb_array & 0xF800) << 8) +
                            ((rgb_array & 0x07E0) << 5) +
                            ((rgb_array & 0x001F) << 3))
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

    def readFrequencies(self) -> List[str]:
        return self.readValues("frequencies")

    def resetSweep(self, start: int, stop: int):
        self.writeSerial("sweep {start} {stop} {self.datapoints}")
        self.writeSerial("resume")

    def readVersion(self):
        logger.debug("Reading version info.")
        if not self.serial.is_open:
            return ""
        try:
            with self.app.serialLock:
                drain_serial(self.serial)
                self.serial.write("version\r".encode('ascii'))
                result = ""
                data = ""
                sleep(0.1)
                while "ch>" not in data:
                    data = self.serial.readline().decode('ascii')
                    result += data
            values = result.splitlines()
            logger.debug("Found version info: %s", values[1])
            return values[1]
        except serial.SerialException as exc:
            logger.exception("Exception while reading firmware version: %s", exc)
        return ""

    def setSweep(self, start, stop):
        if self.useScan:
            self.writeSerial(f"scan {start} {stop} {self.datapoints}")
        else:
            self.writeSerial(f"sweep {start} {stop} {self.datapoints}")
            sleep(1)
