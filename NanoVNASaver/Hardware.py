#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
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
import collections
import logging
import re
from time import sleep
from typing import List

import serial

Datapoint = collections.namedtuple('Datapoint', 'freq re im')

logger = logging.getLogger(__name__)


class VNA:
    name = "VNA"

    def __init__(self, app, serialPort: serial.Serial):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        self.app: NanoVNASaver = app
        self.serial = serialPort
        self.version: Version = Version("0.0.0")

    @staticmethod
    def getVNA(app, serialPort: serial.Serial) -> 'VNA':
        logger.info("Finding correct VNA type")
        tmp_vna = VNA(app, serialPort)
        tmp_vna.flushSerialBuffers()
        firmware = tmp_vna.readFirmware()
        if firmware.find("NanoVNA-H") > 0:
            return NanoVNA_H(app, serialPort)
        if firmware.find("NanoVNA-F") > 0:
            return NanoVNA_F(app, serialPort)
        elif firmware.find("NanoVNA") > 0:
            return NanoVNA(app, serialPort)
        return InvalidVNA(app, serialPort)

    def readFrequencies(self) -> List[str]:
        pass

    def readValues11(self) -> List[str]:
        pass

    def readValues21(self) -> List[str]:
        pass

    def resetSweep(self, start: int, stop: int):
        pass

    def isValid(self):
        return False

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
                logger.exception("Exception while reading firmware data: %s", exc)
            finally:
                self.app.serialLock.release()
            return result
        else:
            logger.error("Unable to acquire serial lock to read firmware.")
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
                logger.exception("Exception while reading %s: %s", value, exc)
                return []
            finally:
                self.app.serialLock.release()
            return values[1:-1]
        else:
            logger.error("Unable to acquire serial lock to read %s", value)
            return []

    def writeSerial(self, command):
        if not self.serial.is_open:
            logger.warning("Writing without serial port being opened (%s)", command)
            return
        if self.app.serialLock.acquire():
            try:
                self.serial.write(str(command + "\r").encode('ascii'))
                self.serial.readline()
            except serial.SerialException as exc:
                logger.exception("Exception while writing to serial port (%s): %s", command, exc)
            finally:
                self.app.serialLock.release()
        return

    def setSweep(self, start, stop):
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " 101")


class InvalidVNA(VNA):
    name = "Invalid"

    def __init__(self):
        pass

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

    def readValues11(self) -> List[str]:
        return []

    def readValues21(self) -> List[str]:
        return []

    def readValues(self, value):
        return

    def flushSerialBuffers(self):
        return


class NanoVNA(VNA):
    name = "NanoVNA"

    def __init__(self, app, serialPort):
        super().__init__(app, serialPort)
        self.version = Version(self.readVersion())

        logger.debug("Testing against 0.2.0")
        if self.version.version_string.find("extended with scan") > 0:
            logger.debug("Incompatible scan command detected.")
            self.useScan = False
        elif self.version >= Version("0.2.0"):
            logger.debug("Newer than 0.2.0, using new scan command.")
            self.useScan = True
        else:
            logger.debug("Older than 0.2.0, using old sweep command.")
            self.useScan = False

    def isValid(self):
        return True

    def readFrequencies(self) -> List[str]:
        return self.readValues("frequencies")

    def readValues11(self) -> List[str]:
        return self.readValues("data 1")

    def readValues21(self) -> List[str]:
        return self.readValues("data 1")

    def resetSweep(self, start: int, stop: int):
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " 101")
        self.writeSerial("resume")

    def readVersion(self):
        logger.debug("Reading version info.")
        if not self.serial.is_open:
            return
        if self.app.serialLock.acquire():
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
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
            finally:
                self.app.serialLock.release()
        return

    def setSweep(self, start, stop):
        if self.useScan:
            self.writeSerial("scan " + str(start) + " " + str(stop) + " 101")
        else:
            self.writeSerial("sweep " + str(start) + " " + str(stop) + " 101")
            sleep(1)


class NanoVNA_H(NanoVNA):
    name = "NanoVNA-H"


class NanoVNA_F(NanoVNA):
    name = "NanoVNA-F"


class Version:
    major = 0
    minor = 0
    revision = 0
    note = ""
    version_string =""

    def __init__(self, version_string):
        self.version_string = version_string
        results = re.match(r"(.*\D+)?(\d+)\.(\d+)\.(\d+)(.*)", version_string)
        if results:
            self.major = int(results.group(2))
            self.minor = int(results.group(3))
            self.revision = int(results.group(4))
            self.note = results.group(5)
            logger.debug("Parsed version as %d.%d.%d%s", self.major, self.minor, self.revision, self.note)

    @staticmethod
    def getVersion(major: int, minor: int, revision: int, note=""):
        return Version(str(major) + "." + str(minor) + "." + str(revision) + note)

    def __gt__(self, other: "Version"):
        return self.major > other.major or self.major == other.major and self.minor > other.minor or \
               self.major == other.major and self.minor == other.minor and self.revision > other.revision

    def __lt__(self, other: "Version"):
        return other > self

    def __ge__(self, other: "Version"):
        return self > other or self == other

    def __le__(self, other: "Version"):
        return self < other or self == other

    def __eq__(self, other: "Version"):
        return self.major == other.major and self.minor == other.minor and self.revision == other.revision and \
               self.note == other.note
