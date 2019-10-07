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
from time import sleep
from typing import List

import serial

Datapoint = collections.namedtuple('Datapoint', 'freq re im')

logger = logging.getLogger(__name__)


class VNA:
    def __init__(self, app, serialPort: serial.Serial):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        self.app: NanoVNASaver = app
        self.serial = serialPort

    @staticmethod
    def getVNA(app, serialPort: serial.Serial) -> 'VNA':
        logger.info("Finding correct VNA type")
        tmp_vna = VNA(app, serialPort)
        tmp_vna.flushSerialBuffers()
        firmware = tmp_vna.readFirmware()
        if firmware.find("NanoVNA") > 0:
            return NanoVNA(app, serialPort)
        return InvalidVNA(app, serialPort)

    def readFrequencies(self) -> List[str]:
        pass

    def readValues11(self) -> List[Datapoint]:
        pass

    def readValues21(self) -> List[Datapoint]:
        pass

    def flushSerialBuffers(self):
        if self.app.serialLock.acquire():
            self.serial.write(b"\r\n\r\n")
            sleep(0.1)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            sleep(0.1)
            self.app.serialLock.release()

    def readFirmware(self):
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
                while "ch>" not in data:
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

    def readValues(self, value):
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
                while "ch>" not in data:
                    data = self.serial.readline().decode('ascii')
                    result += data
                values = result.split("\r\n")
            except serial.SerialException as exc:
                logger.exception("Exception while reading %s: %s", value, exc)
                return
            finally:
                self.app.serialLock.release()
            return values[1:102]
        else:
            logger.error("Unable to acquire serial lock to read %s", value)
            return

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
            self.app.serialLock.release()
        return

    def setSweep(self, start, stop):
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " 101")


class InvalidVNA(VNA):
    def __init__(self):
        pass

    def setSweep(self, start, stop):
        return

    def writeSerial(self, command):
        return

    def readFirmware(self):
        return

    def readFrequencies(self) -> List[int]:
        return []

    def readValues11(self) -> List[Datapoint]:
        return []

    def readValues21(self) -> List[Datapoint]:
        return []

    def readValues(self, value):
        return

    def flushSerialBuffers(self):
        return


class NanoVNA(VNA):
    def __init__(self, app, serialPort):
        super().__init__(app, serialPort)

    def readFrequencies(self) -> List[str]:
        return self.readValues("frequencies")

class NanoVNA_F(NanoVNA):
    pass
