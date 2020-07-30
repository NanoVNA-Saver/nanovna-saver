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
import platform
from struct import pack, unpack_from
from time import sleep
from typing import List

from NanoVNASaver.Hardware.Serial import Interface
from NanoVNASaver.Hardware.VNA import VNA
from NanoVNASaver.Version import Version

if platform.system() != 'Windows':
    import tty

logger = logging.getLogger(__name__)

_CMD_NOP = 0x00
_CMD_INDICATE = 0x0d
_CMD_READ = 0x10
_CMD_READ2 = 0x11
_CMD_READ4 = 0x12
_CMD_READFIFO = 0x18
_CMD_WRITE = 0x20
_CMD_WRITE2 = 0x21
_CMD_WRITE4 = 0x22
_CMD_WRITE8 = 0x23
_CMD_WRITEFIFO = 0x28

_ADDR_SWEEP_START = 0x00
_ADDR_SWEEP_STEP = 0x10
_ADDR_SWEEP_POINTS = 0x20
_ADDR_SWEEP_VALS_PER_FREQ = 0x22
_ADDR_RAW_SAMPLES_MODE = 0x26
_ADDR_VALUES_FIFO = 0x30
_ADDR_DEVICE_VARIANT = 0xf0
_ADDR_PROTOCOL_VERSION = 0xf1
_ADDR_HARDWARE_REVISION = 0xf2
_ADDR_FW_MAJOR = 0xf3
_ADDR_FW_MINOR = 0xf4

WRITE_SLEEP = 0.05

class NanoVNA_V2(VNA):
    name = "NanoVNA-V2"
    valid_datapoints = (101, 11, 51, 201, 301, 501, 1023)
    screenwidth = 320
    screenheight = 240

    def __init__(self, iface: Interface):
        super().__init__(iface)

        if platform.system() != 'Windows':
            tty.setraw(self.serial.fd)

        # reset protocol to known state
        with self.serial.lock:
            self.serial.write(pack("<Q", 0))
            sleep(WRITE_SLEEP)

        self.version = self.readVersion()
        self.firmware = self.readFirmware()

        # firmware major version of 0xff indicates dfu mode
        if self.firmware.data["major"] == 0xff:
            raise IOError('Device is in DFU mode')

        self.sweepStartHz = 200e6
        self.sweepStepHz = 1e6
        self._sweepdata = []
        self._updateSweep()

    def getCalibration(self) -> str:
        return "Unknown"

    def read_features(self):
        self.features.add("Customizable data points")
        # TODO: more than one dp per freq
        self.features.add("Multi data points")

    def readFirmware(self) -> str:
        # read register 0xf3 and 0xf4 (firmware major and minor version)
        cmd = pack("<BBBB",
                   _CMD_READ, _ADDR_FW_MAJOR,
                   _CMD_READ, _ADDR_FW_MINOR)
        with self.serial.lock:
            self.serial.write(cmd)
            sleep(WRITE_SLEEP)
            resp = self.serial.read(2)
        if len(resp) != 2:
            logger.error("Timeout reading version registers")
            return None
        return Version(f"{resp[0]}.{resp[1]}.0")

    def readFrequencies(self) -> List[int]:
        return [
            int(self.sweepStartHz + i * self.sweepStepHz)
            for i in range(self.datapoints)]

    def readValues(self, value) -> List[str]:
        # Actually grab the data only when requesting channel 0.
        # The hardware will return all channels which we will store.
        if value == "data 0":
            # reset protocol to known state
            timeout = self.serial.timeout
            with self.serial.lock:
                self.serial.write(pack("<Q", 0))
                sleep(WRITE_SLEEP)
                # cmd: write register 0x30 to clear FIFO
                self.serial.write(pack("<BBB",
                                       _CMD_WRITE, _ADDR_VALUES_FIFO, 0))
                sleep(WRITE_SLEEP)
                # clear sweepdata
                self._sweepdata = [(complex(), complex())] * self.datapoints
                pointstodo = self.datapoints
                # 8 seconds should be enough for 8k points
                self.serial.timeout = min(8.0, (pointstodo / 32) + 0.1)
                retries = 0
                while pointstodo > 0:
                    logger.info("reading values")
                    pointstoread = min(255, pointstodo)
                    # cmd: read FIFO, addr 0x30
                    self.serial.write(
                        pack("<BBB",
                             _CMD_READFIFO, _ADDR_VALUES_FIFO,
                             pointstoread))
                    sleep(WRITE_SLEEP)
                    # each value is 32 bytes
                    nBytes = pointstoread * 32

                    # serial .read() will wait for exactly nBytes bytes
                    arr = self.serial.read(nBytes)
                    if nBytes != len(arr):
                        logger.error("expected %d bytes, got %d",
                                     nBytes, len(arr))
                        retries += 1
                        if retries < 5:
                            continue
                        return []

                    freq_index = -1
                    for i in range(pointstoread):
                        (fwd_real, fwd_imag, rev0_real, rev0_imag, rev1_real,
                         rev1_imag, freq_index) = unpack_from(
                             "<iiiiiihxxxxxx", arr, i * 32)
                        fwd = complex(fwd_real, fwd_imag)
                        refl = complex(rev0_real, rev0_imag)
                        thru = complex(rev1_real, rev1_imag)
                        if i == 0:
                            logger.debug("Freq index from: %i", freq_index)
                        self._sweepdata[freq_index] = (refl / fwd, thru / fwd)
                    logger.debug("Freq index to: %i", freq_index)

                    pointstodo = pointstodo - pointstoread
            self.serial.timeout = timeout

            ret = [x[0] for x in self._sweepdata]
            ret = [str(x.real) + ' ' + str(x.imag) for x in ret]
            return ret

        if value == "data 1":
            ret = [x[1] for x in self._sweepdata]
            ret = [str(x.real) + ' ' + str(x.imag) for x in ret]
            return ret

    def resetSweep(self, start: int, stop: int):
        self.setSweep(start, stop)

    # returns device variant
    def readVersion(self) -> 'Version':
        # read register 0xf0 (device type), 0xf2 (board revision)
        cmd = b"\x10\xf0\x10\xf2"
        with self.serial.lock:
            self.serial.write(cmd)
            sleep(WRITE_SLEEP)
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
        logger.info('NanoVNAV2: set sweep start %d step %d',
                    self.sweepStartHz, self.sweepStepHz)
        self._updateSweep()
        return

    def _updateSweep(self):
        cmd = pack("<BBQ", _CMD_WRITE8,
                   _ADDR_SWEEP_START, int(self.sweepStartHz))
        cmd += pack("<BBQ", _CMD_WRITE8,
                    _ADDR_SWEEP_STEP, int(self.sweepStepHz))
        cmd += pack("<BBH", _CMD_WRITE2,
                    _ADDR_SWEEP_POINTS, self.datapoints)
        cmd += pack("<BBH", _CMD_WRITE2,
                    _ADDR_SWEEP_VALS_PER_FREQ, 1)
        with self.serial.lock:
            self.serial.write(cmd)
            sleep(WRITE_SLEEP)
