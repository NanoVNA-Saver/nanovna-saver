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
import platform
from typing import List

from NanoVNASaver.Hardware.VNA import VNA, Version

if platform.system() != 'Windows':
    import tty

logger = logging.getLogger(__name__)


def _unpackSigned32(b):
    return int.from_bytes(b[0:4], 'little', signed=True)

def _unpackUnsigned16(b):
    return int.from_bytes(b[0:2], 'little', signed=False)

class NanoVNAV2(VNA):
    name = "NanoVNA-V2"
    datapoints = 255
    screenwidth = 320
    screenheight = 240

    def __init__(self, app, serialPort):
        super().__init__(app, serialPort)

        if platform.system() != 'Windows':
            tty.setraw(self.serial.fd)
        self.serial.timeout = 6 # for this much data we need a longer timeout

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
        return Version(f"{resp[0]}.{resp[1]}.0")


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

            bytesleft = self.datapoints
            while bytesleft > 0 :

                logger.info("reading values")
                bytestoread = min(255, bytesleft)
                # cmd: read FIFO, addr 0x30
                self.serial.write([0x18, 0x30, bytestoread])

                # each value is 32 bytes
                nBytes = bytestoread * 32

                # serial .read() will wait for exactly nBytes bytes
                arr = self.serial.read(nBytes)
                if nBytes != len(arr):
                    logger.error("expected %d bytes, got %d", nBytes, len(arr))
                    return []

                for i in range(bytestoread):
                    b = arr[i*32:]
                    fwd = complex(_unpackSigned32(b[0:]), _unpackSigned32(b[4:]))
                    refl = complex(_unpackSigned32(b[8:]), _unpackSigned32(b[12:]))
                    thru = complex(_unpackSigned32(b[16:]), _unpackSigned32(b[20:]))
                    freqIndex = _unpackUnsigned16(b[24:])
                    #print('freqIndex', freqIndex)
                    self.sweepData[freqIndex] = (refl / fwd, thru / fwd)

                bytesleft = bytesleft - bytestoread

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
        return Version(f"{resp[0]}.0.{resp[1]}")


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
        cmd += b"\x21\x22" + int.to_bytes(1, 2, 'little') # number of samples
        self.serial.write(cmd)
