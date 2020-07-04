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
from time import sleep
from typing import List

import serial
from PyQt5 import QtGui

from NanoVNASaver.Settings import Version
from NanoVNASaver.Hardware.Serial import Interface, drain_serial

logger = logging.getLogger(__name__)


class VNA:
    name = "VNA"
    _datapoints = (101, )

    def __init__(self, iface: Interface):
        self.serial = iface
        self.version = Version("0.0.0")
        self.features = set()
        self.validateInput = True
        self.datapoints = VNA._datapoints[0]

    def readFeatures(self) -> List[str]:
        raw_help = self.readFromCommand("help")
        logger.debug("Help command output:")
        logger.debug(raw_help)

        #  Detect features from the help command
        if "capture" in raw_help:
            self.features.add("Screenshots")
        if len(self._datapoints) > 1:
            self.features.add("Customizable data points")

        return self.features

    # TODO: check return types
    def readFrequencies(self) -> List[int]:
        return []

    def resetSweep(self, start: int, stop: int):
        pass

    def isValid(self):
        return False

    def isDFU(self):
        return False

    def getFeatures(self) -> List[str]:
        return self.features

    def getCalibration(self) -> str:
        logger.debug("Reading calibration info.")
        if not self.serial.is_open:
            return "Not connected."
        with self.serial.lock:
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
        return QtGui.QPixmap()

    def flushSerialBuffers(self):
        with self.serial.lock:
            self.serial.write("\r\n\r\n".encode("ascii"))
            sleep(0.1)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            sleep(0.1)

    def readFirmware(self) -> str:
        try:
            with self.serial.lock:
                drain_serial(self.serial)
                self.serial.write("info\r".encode('ascii'))
                result = ""
                data = ""
                sleep(0.01)
                while data != "ch> ":
                    data = self.serial.readline().decode('ascii')
                    result += data
            return result
        except serial.SerialException as exc:
            logger.exception(
                "Exception while reading firmware data: %s", exc)
        return ""

    def readFromCommand(self, command) -> str:
        try:
            with self.serial.lock:
                drain_serial(self.serial)
                self.serial.write(f"{command}\r".encode('ascii'))
                result = ""
                data = ""
                sleep(0.01)
                while data != "ch> ":
                    data = self.serial.readline().decode('ascii')
                    result += data
            return result
        except serial.SerialException as exc:
            logger.exception(
                "Exception while reading %s: %s", command, exc)
        return ""

    def readValues(self, value) -> List[str]:
        logger.debug("VNA reading %s", value)
        try:
            with self.serial.lock:
                drain_serial(self.serial)
                self.serial.write(f"{value}\r".encode('ascii'))
                result = ""
                data = ""
                sleep(0.05)
                while data != "ch> ":
                    data = self.serial.readline().decode('ascii')
                    result += data
            values = result.split("\r\n")
            logger.debug(
                "VNA done reading %s (%d values)",
                value, len(values)-2)
            return values[1:-1]
        except serial.SerialException as exc:
            logger.exception(
                "Exception while reading %s: %s", value, exc)
        return []

    def readVersion(self) -> str:
        logger.debug("Reading version info.")
        if not self.serial.is_open:
            return ""
        try:
            with self.serial.lock:
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



    def writeSerial(self, command):
        if not self.serial.is_open:
            logger.warning("Writing without serial port being opened (%s)",
                           command)
            return
        with self.serial.lock:
            try:
                self.serial.write(f"{command}\r".encode('ascii'))
                self.serial.readline()
            except serial.SerialException as exc:
                logger.exception(
                    "Exception while writing to serial port (%s): %s",
                    command, exc)

    def setSweep(self, start, stop):
        self.writeSerial(f"sweep {start} {stop} {self.datapoints}")
