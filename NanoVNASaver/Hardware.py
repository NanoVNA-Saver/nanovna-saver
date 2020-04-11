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
import logging
import re
import struct
import platform
from time import sleep
from typing import List, Tuple
from collections import namedtuple

import serial
import numpy as np
from PyQt5 import QtWidgets, QtGui
from serial.tools import list_ports

logger = logging.getLogger(__name__)

Device = namedtuple("Device", "vid pid name")

DEVICETYPES = (
    Device(0x0483, 0x5740, "NanoVNA"),
    Device(0x16c0, 0x0483, "AVNA"),
    Device(0x04b4, 0x0008, "NanaVNA-V2"),
)


# Get list of interfaces with VNAs connected
def get_interfaces() -> List[Tuple[str, str]]:
    return_ports = []
    for d in list_ports.comports():
        for t in DEVICETYPES:
            if d.vid == t.vid and d.pid == t.pid:
                port = d.device
                logger.info("Found %s (%04x %04x) on port %s", t.name, d.vid, d.pid, d.device)
                return_ports.append((port, port + " (" + t.name + ")"))
    return return_ports


def detect_version(serialPort: serial.Serial) -> str:
    serialPort.timeout = 0.1

    # drain any outstanding data in the serial incoming buffer
    data = "a"
    while len(data) != 0:
        data = serialPort.read(128)

    # send a \r and see what we get
    serialPort.write(b"\r")

    # will wait up to 0.1 seconds
    data = serialPort.readline().decode('ascii')

    if data == 'ch> ':
        # this is an original nanovna
        return 'nanovna'

    if data == '2':
        # this is a nanovna v2
        return 'nanovnav2'

    logger.error('Unknown VNA type: hardware responded to \r with: %s', data)
    return 'unknown'


class VNA:
    name = "VNA"
    validateInput = True
    features = []
    datapoints = 101

    def __init__(self, app: QtWidgets.QWidget, serial_port: serial.Serial):
        self.app = app
        self.serial = serial_port
        self.version: Version = Version("0.0.0")

    @staticmethod
    def getVNA(app, serial_port: serial.Serial) -> 'VNA':
        logger.info("Finding correct VNA type...")

        for retry in range(3):
            vnaType = detect_version(serial_port)
            if vnaType != "unkown":
                break

        if vnaType == 'nanovnav2':
            logger.info("Type: NanoVNA-V2")
            return NanoVNAV2(app, serial_port)

        logger.info("Finding firmware variant...")
        serial_port.timeout = 0.05
        tmp_vna = VNA(app, serial_port)
        tmp_vna.flushSerialBuffers()
        firmware = tmp_vna.readFirmware()
        if firmware.find("AVNA + Teensy") > 0:
            logger.info("Type: AVNA")
            return AVNA(app, serial_port)
        if firmware.find("NanoVNA-H") > 0:
            logger.info("Type: NanoVNA-H")
            return NanoVNA_H(app, serial_port)
        if firmware.find("NanoVNA-F") > 0:
            logger.info("Type: NanoVNA-F")
            return NanoVNA_F(app, serial_port)
        elif firmware.find("NanoVNA") > 0:
            logger.info("Type: Generic NanoVNA")
            return NanoVNA(app, serial_port)
        else:
            logger.warning("Did not recognize NanoVNA type from firmware.")
            return NanoVNA(app, serial_port)

    def readFeatures(self) -> List[str]:
        features = []
        raw_help = self.readFromCommand("help")
        logger.debug("Help command output:")
        logger.debug(raw_help)

        #  Detect features from the help command
        if "capture" in raw_help:
            features.append("Screenshots")

        return features

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
                logger.exception("Exception while reading firmware data: %s", exc)
            finally:
                self.app.serialLock.release()
            return result
        else:
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
                logger.exception("Exception while reading %s: %s", command, exc)
            finally:
                self.app.serialLock.release()
            return result
        else:
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
                logger.exception("Exception while reading %s: %s", value, exc)
                return []
            finally:
                self.app.serialLock.release()
            logger.debug("VNA done reading %s (%d values)", value, len(values)-2)
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
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " " + str(self.datapoints))


class InvalidVNA(VNA):
    name = "Invalid"
    datapoints = 0

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


class AVNA(VNA):
    name = "AVNA"
    datapoints = 101

    def __init__(self, app, serial_port):
        super().__init__(app, serial_port)
        self.version = Version(self.readVersion())

        self.features = []
        self.features.append("Customizable data points")

    def isValid(self):
        return True

    def getCalibration(self) -> str:
        logger.debug("Reading calibration info.")
        if not self.serial.is_open:
            return "Not connected."
        if self.app.serialLock.acquire():
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
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
            finally:
                self.app.serialLock.release()
        return "Unknown"

    def readFrequencies(self) -> List[str]:
        return self.readValues("frequencies")

    def readValues11(self) -> List[str]:
        return self.readValues("data 0")

    def readValues21(self) -> List[str]:
        return self.readValues("data 1")

    def resetSweep(self, start: int, stop: int):
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " " + str(self.datapoints))
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
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " " + str(self.datapoints))
        sleep(1)


class NanoVNA(VNA):
    name = "NanoVNA"
    datapoints = 101
    screenwidth = 320
    screenheight = 240

    def __init__(self, app, serial_port):
        super().__init__(app, serial_port)
        self.version = Version(self.readVersion())

        self.features = []

        logger.debug("Testing against 0.2.0")
        if self.version.version_string.find("extended with scan") > 0:
            logger.debug("Incompatible scan command detected.")
            self.features.append("Incompatible scan command")
            self.useScan = False
        elif self.version >= Version("0.2.0"):
            logger.debug("Newer than 0.2.0, using new scan command.")
            self.features.append("New scan command")
            self.useScan = True
        else:
            logger.debug("Older than 0.2.0, using old sweep command.")
            self.features.append("Original sweep method")
            self.useScan = False
        self.features.extend(self.readFeatures())

    def isValid(self):
        return True

    def getCalibration(self) -> str:
        logger.debug("Reading calibration info.")
        if not self.serial.is_open:
            return "Not connected."
        if self.app.serialLock.acquire():
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
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
            finally:
                self.app.serialLock.release()
        return "Unknown"

    def getScreenshot(self) -> QtGui.QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.serial.is_open:
            return QtGui.QPixmap()
        if self.app.serialLock.acquire():
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
                self.serial.write("capture\r".encode('ascii'))
                timeout = self.serial.timeout
                self.serial.timeout = 4
                self.serial.readline()
                image_data = self.serial.read(self.screenwidth * self.screenheight * 2)
                self.serial.timeout = timeout
                rgb_data = struct.unpack(">" + str(self.screenwidth * self.screenheight) + "H", image_data)
                rgb_array = np.array(rgb_data, dtype=np.uint32)
                rgba_array = (0xFF000000 +
                              ((rgb_array & 0xF800) << 8) +
                              ((rgb_array & 0x07E0) << 5) +
                              ((rgb_array & 0x001F) << 3))
                image = QtGui.QImage(rgba_array, self.screenwidth, self.screenheight, QtGui.QImage.Format_ARGB32)
                logger.debug("Captured screenshot")
                return QtGui.QPixmap(image)
            except serial.SerialException as exc:
                logger.exception("Exception while capturing screenshot: %s", exc)
            finally:
                self.app.serialLock.release()
        return QtGui.QPixmap()

    def readFrequencies(self) -> List[str]:
        return self.readValues("frequencies")

    def readValues11(self) -> List[str]:
        return self.readValues("data 0")

    def readValues21(self) -> List[str]:
        return self.readValues("data 1")

    def resetSweep(self, start: int, stop: int):
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " " + str(self.datapoints))
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
            self.writeSerial("scan " + str(start) + " " + str(stop) + " " + str(self.datapoints))
        else:
            self.writeSerial("sweep " + str(start) + " " + str(stop) + " " + str(self.datapoints))
            sleep(1)


class NanoVNA_H(NanoVNA):
    name = "NanoVNA-H"


class NanoVNA_H4(NanoVNA):
    name = "NanoVNA-H4"
    screenwidth = 640
    screenheight = 240


class NanoVNA_F(NanoVNA):
    name = "NanoVNA-F"
    screenwidth = 800
    screenheight = 480

    def getScreenshot(self) -> QtGui.QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.serial.is_open:
            return QtGui.QPixmap()
        if self.app.serialLock.acquire():
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
                self.serial.write("capture\r".encode('ascii'))
                timeout = self.serial.timeout
                self.serial.timeout = 4
                self.serial.readline()
                image_data = self.serial.read(self.screenwidth * self.screenheight * 2)
                self.serial.timeout = timeout
                rgb_data = struct.unpack("<" + str(self.screenwidth * self.screenheight) + "H", image_data)
                rgb_array = np.array(rgb_data, dtype=np.uint32)
                rgba_array = (0xFF000000 +
                              ((rgb_array & 0xF800) << 8) +  # G?!
                              ((rgb_array & 0x07E0) >> 3) +  # B
                              ((rgb_array & 0x001F) << 11))  # G

                # logger.debug("Value yellow: %s", hex(rgb_array[10*400+36]))  # This ought to be yellow
                # logger.debug("Value white: %s", hex(rgb_array[50*400+261]))  # This ought to be white
                # logger.debug("Value cyan: %s", hex(rgb_array[10*400+252]))  # This ought to be cyan
                #
                # rgba_array = (0xFF000000 + ((rgb_array & 0x001F) << 11))  # Exclusively green?
                # rgba_array[10*400+36] = 0xFFFF0000
                # rgba_array[50*400+261] = 0xFFFF0000
                # rgba_array[10*400+252] = 0xFFFF0000

                # At this point, the RGBA array is structured as 4 small images:
                # 13
                # 24
                # each of which represents the pixels in a differently structured larger image:
                # 12
                # 34
                # Let us unwrap.

                unwrapped_array = np.empty(self.screenwidth*self.screenheight, dtype=np.uint32)
                for y in range(self.screenheight//2):
                    for x in range(self.screenwidth//2):
                        unwrapped_array[2 * x + 2 * y * self.screenwidth] = rgba_array[x + y * self.screenwidth]
                        unwrapped_array[(2 * x) + 1 + 2 * y * self.screenwidth] = \
                            rgba_array[x + (self.screenheight//2 + y) * self.screenwidth]
                        unwrapped_array[2 * x + (2 * y + 1) * self.screenwidth] = \
                            rgba_array[x + self.screenwidth//2 + y * self.screenwidth]
                        unwrapped_array[(2 * x) + 1 + (2 * y + 1) * self.screenwidth] = \
                            rgba_array[x + self.screenwidth//2 + (self.screenheight//2 + y) * self.screenwidth]

                image = QtGui.QImage(unwrapped_array, self.screenwidth, self.screenheight, QtGui.QImage.Format_ARGB32)
                logger.debug("Captured screenshot")
                return QtGui.QPixmap(image)
            except serial.SerialException as exc:
                logger.exception("Exception while capturing screenshot: %s", exc)
            finally:
                self.app.serialLock.release()
        return QtGui.QPixmap()


def _unpackSigned32(b):
    return int.from_bytes(b[0:4], 'little', signed=True)

def _unpackUnsigned16(b):
    return int.from_bytes(b[0:2], 'little', signed=False)

class NanoVNAV2(VNA):
    name = "NanoVNA-V2"
    datapoints = 101
    screenwidth = 320
    screenheight = 240

    def __init__(self, app, serialPort):
        super().__init__(app, serialPort)

        if platform.system() != 'Windows':
            import tty
            tty.setraw(self.serial.fd)
        self.serial.timeout = 3

        # reset protocol to known state
        self.serial.write([0, 0, 0, 0, 0, 0, 0, 0])

        self.version = self.readVersion()
        self.firmware = self.readFirmware()

        # firmware major version of 0xff indicates dfu mode
        if self.firmware.major == 0xff:
            self._isDFU = True
            return

        self._isDFU = False
        self.sweepStartHz = 200e6
        self.sweepStepHz = 1e6
        self.sweepData = [(0, 0)] * self.datapoints
        self._updateSweep()


    def isValid(self):
        if self.isDFU():
            return False
        return True

    def isDFU(self):
        return self._isDFU

    def checkValid(self):
        if self.isDFU():
            raise IOError('Device is in DFU mode')

    def readFirmware(self) -> str:
        # read register 0xf3 and 0xf4 (firmware major and minor version)
        cmd = b"\x10\xf3\x10\xf4"
        self.serial.write(cmd)

        resp = self.serial.read(2)
        if len(resp) != 2:
            logger.error("Timeout reading version registers")
            return None
        return Version.getVersion(major=resp[0], minor=resp[1], revision=0)

    def readFrequencies(self) -> List[str]:
        self.checkValid()
        freqs = [self.sweepStartHz + i*self.sweepStepHz for i in range(self.datapoints)]
        return [str(int(f)) for f in freqs]


    def readValues(self, value) -> List[str]:
        self.checkValid()

        # Actually grab the data only when requesting channel 0.
        # The hardware will return all channels which we will store.
        if value == "data 0":
            # reset protocol to known state
            self.serial.write([0, 0, 0, 0, 0, 0, 0, 0])

            # cmd: write register 0x30 to clear FIFO
            self.serial.write([0x20, 0x30, 0x00])

            # cmd: read FIFO, addr 0x30
            self.serial.write([0x18, 0x30, self.datapoints])

            # each value is 32 bytes
            nBytes = self.datapoints * 32

            # serial .read() will wait for exactly nBytes bytes
            arr = self.serial.read(nBytes)
            if nBytes != len(arr):
                logger.error("expected %d bytes, got %d", nBytes, len(arr))
                return []

            for i in range(self.datapoints):
                b = arr[i*32:]
                fwd = complex(_unpackSigned32(b[0:]), _unpackSigned32(b[4:]))
                refl = complex(_unpackSigned32(b[8:]), _unpackSigned32(b[12:]))
                thru = complex(_unpackSigned32(b[16:]), _unpackSigned32(b[20:]))
                freqIndex = _unpackUnsigned16(b[24:])
                #print('freqIndex', freqIndex)
                self.sweepData[freqIndex] = (refl / fwd, thru / fwd)

            ret = [x[0] for x in self.sweepData]
            ret = [str(x.real) + ' ' + str(x.imag) for x in ret]
            return ret

        if value == "data 1":
            ret = [x[1] for x in self.sweepData]
            ret = [str(x.real) + ' ' + str(x.imag) for x in ret]
            return ret

    def readValues11(self) -> List[str]:
        return self.readValues("data 0")

    def readValues21(self) -> List[str]:
        return self.readValues("data 1")

    def resetSweep(self, start: int, stop: int):
        self.setSweep(start, stop)
        return

    # returns device variant
    def readVersion(self):
        # read register 0xf0 (device type), 0xf2 (board revision)
        cmd = b"\x10\xf0\x10\xf2"
        self.serial.write(cmd)

        resp = self.serial.read(2)
        if len(resp) != 2:
            logger.error("Timeout reading version registers")
            return None
        return Version.getVersion(major=resp[0], minor=0, revision=resp[1])

    def setSweep(self, start, stop):
        step = (stop - start) / (self.datapoints - 1)
        if start == self.sweepStartHz and step == self.sweepStepHz:
            return
        self.sweepStartHz = start
        self.sweepStepHz = step
        logger.info('NanoVNAV2: set sweep start %d step %d', self.sweepStartHz, self.sweepStepHz)
        self._updateSweep()
        return

    def _updateSweep(self):
        self.checkValid()

        cmd = b"\x23\x00" + int.to_bytes(int(self.sweepStartHz), 8, 'little')
        cmd += b"\x23\x10" + int.to_bytes(int(self.sweepStepHz), 8, 'little')
        cmd += b"\x21\x20" + int.to_bytes(int(self.datapoints), 2, 'little')
        self.serial.write(cmd)



class Version:
    major = 0
    minor = 0
    revision = 0
    note = ""
    version_string = ""

    def __init__(self, version_string):
        self.version_string = version_string
        results = re.match(r"(.*\s+)?(\d+)\.(\d+)\.(\d+)(.*)", version_string)
        if results:
            self.major = int(results.group(2))
            self.minor = int(results.group(3))
            self.revision = int(results.group(4))
            self.note = results.group(5)
            logger.debug("Parsed version as \"%d.%d.%d%s\"", self.major, self.minor, self.revision, self.note)

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

    def __str__(self):
        return str(self.major) + "." + str(self.minor) + "." + str(self.revision) + str(self.note)
