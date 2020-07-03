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
from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.Settings import Version
from NanoVNASaver.Hardware.Serial import drain_serial

logger = logging.getLogger(__name__)


class VNA:
    name = "VNA"
    _datapoints = (101, )

    def __init__(self, app: QtWidgets.QWidget, serial_port: serial.Serial):
        self.app = app
        self.serial = serial_port
        self.version: Version = Version("0.0.0")
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
        return "Unknown"

    def getScreenshot(self) -> QtGui.QPixmap:
        return QtGui.QPixmap()

    def flushSerialBuffers(self):
        with self.app.serialLock:
            self.serial.write("\r\n\r\n".encode("ascii"))
            sleep(0.1)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            sleep(0.1)

    def readFirmware(self) -> str:
        try:
            with self.app.serialLock:
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
            with self.app.serialLock:
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
            with self.app.serialLock:
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

    def writeSerial(self, command):
        if not self.serial.is_open:
            logger.warning("Writing without serial port being opened (%s)",
                           command)
            return
        with self.app.serialLock:
            try:
                self.serial.write(f"{command}\r".encode('ascii'))
                self.serial.readline()
            except serial.SerialException as exc:
                logger.exception(
                    "Exception while writing to serial port (%s): %s",
                    command, exc)

    def setSweep(self, start, stop):
        self.writeSerial(f"sweep {start} {stop} {self.datapoints}")


# TODO: should be dropped and the serial part should be a connection class
#       which handles unconnected devices
class InvalidVNA(VNA):
    name = "Invalid"
    _datapoints = (0, )

    def setSweep(self, start, stop):
        return

    def resetSweep(self, start, stop):
        return

    def writeSerial(self, command):
        return

    def readFirmware(self):
        return

    def readFrequencies(self) -> List[int]:
        return []

    def readValues(self, value):
        return

    def flushSerialBuffers(self):
        return
