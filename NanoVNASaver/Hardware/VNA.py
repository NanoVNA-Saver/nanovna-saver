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
from typing import List, Iterator

from PyQt5 import QtGui

from NanoVNASaver.Settings import Version
from NanoVNASaver.Hardware.Serial import Interface, drain_serial

logger = logging.getLogger(__name__)


class VNA:
    name = "VNA"
    valid_datapoints = (101, )

    def __init__(self, iface: Interface):
        self.serial = iface
        self.version = Version("0.0.0")
        self.features = set()
        self.validateInput = True
        self.datapoints = self.valid_datapoints[0]
        if self.connected():
            self.version = self.readVersion()
            self.read_features()

    def exec_command(self, command: str, wait: float = 0.05) -> Iterator[str]:
        logger.debug("exec_command(%s)", command)
        with self.serial.lock:
            drain_serial(self.serial)
            self.serial.write(f"{command}\r".encode('ascii'))
            sleep(wait)
            retries = 0
            while True:
                line = self.serial.readline()
                line = line.decode("ascii").strip()
                if not line:
                    retries += 1
                    logger.debug("Retry nr: %s", retries)
                    if retries > 10:
                        raise IOError("too many retries")
                    sleep(0.1)
                    continue
                if line == command:  # suppress echo
                    continue
                if line.startswith("ch>"):
                    break
                yield line

    def read_features(self):
        result = "\n".join(list(self.exec_command("help")))
        logger.debug("result:\n%s", result)
        if "capture" in result:
            self.features.add("Screenshots")
        if len(self.valid_datapoints) > 1:
            self.features.add("Customizable data points")

    def readFrequencies(self) -> List[int]:
        return [int(f) for f in self.readValues("frequencies")]

    def resetSweep(self, start: int, stop: int):
        pass

    def connected(self) -> bool:
        return self.serial.is_open

    def getFeatures(self) -> List[str]:
        return self.features

    def getCalibration(self) -> str:
        return list(self.exec_command("cal"))[0]

    def getScreenshot(self) -> QtGui.QPixmap:
        return QtGui.QPixmap()

    def flushSerialBuffers(self):
        if not self.connected():
            return
        with self.serial.lock:
            self.serial.write("\r\n\r\n".encode("ascii"))
            sleep(0.1)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            sleep(0.1)

    def readFirmware(self) -> str:
        result = "\n".join(list(self.exec_command("info")))
        logger.debug("result:\n%s", result)
        return result

    def readValues(self, value) -> List[str]:
        logger.debug("VNA reading %s", value)
        result = list(self.exec_command(value))
        logger.debug("VNA done reading %s (%d values)",
                     value, len(result))
        return result

    def readVersion(self) -> 'Version':
        result = list(self.exec_command("version"))
        logger.debug("result:\n%s", result)
        return Version(result[0])

    def setSweep(self, start, stop):
        list(self.exec_command(f"sweep {start} {stop} {self.datapoints}"))
