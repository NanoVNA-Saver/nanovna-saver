#  NanoVNASaver
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019.  Rune B. Broberg
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
import re
from time import sleep
from typing import List

import serial
from PyQt5 import QtWidgets, QtGui

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
        self.datapoints = self._datapoints[0]

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
        if self.app.serialLock.acquire():
            self.serial.write(b"\r\n\r\n")
            sleep(0.1)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            sleep(0.1)
            self.app.serialLock.release()

    def readFirmware(self) -> str:
        if self.app.serialLock.acquire():
            result = ""
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
                self.serial.write("info\r".encode('ascii'))
                result = ""
                data = ""
                sleep(0.01)
                while data != "ch> ":
                    data = self.serial.readline().decode('ascii')
                    result += data
            except serial.SerialException as exc:
                logger.exception(
                    "Exception while reading firmware data: %s", exc)
            finally:
                self.app.serialLock.release()
            return result
        logger.error("Unable to acquire serial lock to read firmware.")
        return ""

    def readFromCommand(self, command) -> str:
        if self.app.serialLock.acquire():
            result = ""
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
                self.serial.write((command + "\r").encode('ascii'))
                result = ""
                data = ""
                sleep(0.01)
                while data != "ch> ":
                    data = self.serial.readline().decode('ascii')
                    result += data
            except serial.SerialException as exc:
                logger.exception(
                    "Exception while reading %s: %s", command, exc)
            finally:
                self.app.serialLock.release()
            return result
        logger.error("Unable to acquire serial lock to read %s", command)
        return ""

    def readValues(self, value) -> List[str]:
        logger.debug("VNA reading %s", value)
        if self.app.serialLock.acquire():
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
                #  Then send the command to read data
                self.serial.write(str(value + "\r").encode('ascii'))
                result = ""
                data = ""
                sleep(0.05)
                while data != "ch> ":
                    data = self.serial.readline().decode('ascii')
                    result += data
                values = result.split("\r\n")
            except serial.SerialException as exc:
                logger.exception(
                    "Exception while reading %s: %s", value, exc)
                return []
            finally:
                self.app.serialLock.release()
            logger.debug(
                "VNA done reading %s (%d values)",
                value, len(values)-2)
            return values[1:-1]
        logger.error("Unable to acquire serial lock to read %s", value)
        return []

    def writeSerial(self, command):
        if not self.serial.is_open:
            logger.warning("Writing without serial port being opened (%s)",
                           command)
            return
        if self.app.serialLock.acquire():
            try:
                self.serial.write(str(command + "\r").encode('ascii'))
                self.serial.readline()
            except serial.SerialException as exc:
                logger.exception(
                    "Exception while writing to serial port (%s): %s",
                    command, exc)
            finally:
                self.app.serialLock.release()
        return

    def setSweep(self, start, stop):
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " " + str(self.datapoints))

# TODO: should be dropped and the serial part should be a connection class which handles
#       unconnected devices


class InvalidVNA(VNA):
    name = "Invalid"
    _datapoints = (0, )

    def __init__(self, app: QtWidgets.QWidget, serial_port: serial.Serial):
        super().__init__(app, serial_port)

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


# TODO: should go to Settings.py and be generalized
class Version:
    major = 0
    minor = 0
    revision = 0
    note = ""
    version_string = ""

    def __init__(self, version_string):
        self.version_string = version_string
        results = re.match(
            r"(.*\s+)?(\d+)\.(\d+)\.(\d+)(.*)",
            version_string)
        if results:
            self.major = int(results.group(2))
            self.minor = int(results.group(3))
            self.revision = int(results.group(4))
            self.note = results.group(5)
            logger.debug(
                "Parsed version as \"%d.%d.%d%s\"",
                self.major, self.minor, self.revision, self.note)

    def __gt__(self, other: "Version") -> bool:
        if self.major > other.major:
            return True
        if self.major < other.major:
            return False
        if self.minor > other.minor:
            return True
        if self.minor < other.minor:
            return False
        if self.revision > other.revision:
            return True
        return False

    def __lt__(self, other: "Version") -> bool:
        return other > self

    def __ge__(self, other: "Version") -> bool:
        return self > other or self == other

    def __le__(self, other: "Version") -> bool:
        return self < other or self == other

    def __eq__(self, other: "Version") -> bool:
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.revision == other.revision and
            self.note == other.note)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.revision}{self.note}"
