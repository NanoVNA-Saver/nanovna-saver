#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
from typing import Iterator

from PyQt6 import QtGui

from NanoVNASaver.Hardware.Serial import Interface, drain_serial
from NanoVNASaver.Version import Version

logger = logging.getLogger(__name__)

DISLORD_BW = {
    10: 363,
    33: 117,
    50: 78,
    100: 39,
    200: 19,
    250: 15,
    333: 11,
    500: 7,
    1000: 3,
    2000: 1,
    4000: 0,
}
WAIT = 0.05


def _max_retries(bandwidth: int, datapoints: int) -> int:
    return round(
        20
        + 20 * (datapoints / 101)
        + (1000 / bandwidth) ** 1.30 * (datapoints / 101)
    )


class VNA:
    name = "VNA"
    valid_datapoints = (101, 51, 11)
    wait = 0.05
    SN = "NOT SUPPORTED"
    sweep_points_max = 101
    sweep_points_min = 11

    def __init__(self, iface: Interface):
        self.serial = iface
        self.version = Version("0.0.0")
        self.features = set()
        self.validateInput = False
        self.datapoints = self.valid_datapoints[0]
        self.bandwidth = 1000
        self.bw_method = "ttrftech"
        self.sweep_max_freq_Hz = None
        # [((min_freq, max_freq), [description]]. Order by increasing
        # frequency. Put default output power first.
        self.txPowerRanges = []
        if self.connected():
            self.version = self.readVersion()
            self.read_features()
            logger.debug("Features: %s", self.features)
            #  cannot read current bandwidth, so set to highest
            #  to get initial sweep fast
            if "Bandwidth" in self.features:
                self.set_bandwidth(self.get_bandwidths()[-1])

    def connect(self):
        logger.info("connect %s", self.serial)
        with self.serial.lock:
            self.serial.open()

    def disconnect(self):
        logger.info("disconnect %s", self.serial)
        with self.serial.lock:
            self.serial.close()

    def reconnect(self):
        self.disconnect()
        sleep(WAIT)
        self.connect()
        sleep(WAIT)

    def exec_command(self, command: str, wait: float = WAIT) -> Iterator[str]:
        logger.debug("exec_command(%s)", command)
        with self.serial.lock:
            drain_serial(self.serial)
            self.serial.write(f"{command}\r".encode("ascii"))
            sleep(wait)
            retries = 0
            max_retries = _max_retries(self.bandwidth, self.datapoints)
            logger.debug("Max retries: %s", max_retries)
            while True:
                line = self.serial.readline()
                line = line.decode("ascii").strip()
                if not line:
                    retries += 1
                    if retries > max_retries:
                        raise IOError("too many retries")
                    sleep(wait)
                    continue
                if line == command:  # suppress echo
                    continue
                if line.startswith("ch>"):
                    logger.debug("Needed retries: %s", retries)
                    break
                yield line

    def read_features(self):
        result = " ".join(self.exec_command("help")).split()
        logger.debug("result:\n%s", result)
        if "capture" in result:
            self.features.add("Screenshots")
        if "sn:" in result:
            self.features.add("SN")
            self.SN = self.getSerialNumber()
        if "bandwidth" in result:
            self.features.add("Bandwidth")
            result = " ".join(list(self.exec_command("bandwidth")))
            if "Hz)" in result:
                self.bw_method = "dislord"
        if len(self.valid_datapoints) > 1:
            self.features.add("Customizable data points")

    def get_bandwidths(self) -> list[int]:
        logger.debug("get bandwidths")
        if self.bw_method == "dislord":
            return list(DISLORD_BW.keys())
        result = " ".join(list(self.exec_command("bandwidth")))
        try:
            result = result.split(" {")[1].strip("}")
            return sorted([int(i) for i in result.split("|")])
        except IndexError:
            return [
                1000,
            ]

    def set_bandwidth(self, bandwidth: int):
        bw_val = (
            DISLORD_BW[bandwidth] if self.bw_method == "dislord" else bandwidth
        )
        result = " ".join(self.exec_command(f"bandwidth {bw_val}"))
        if self.bw_method == "ttrftech" and result:
            raise IOError(f"set_bandwith({bandwidth}: {result}")
        self.bandwidth = bandwidth

    def read_frequencies(self) -> list[int]:
        return [int(f.real) for f in self.readValues("frequencies")]

    def resetSweep(self, start: int, stop: int):
        pass

    def _get_running_frequencies(self) -> tuple[int, int]:
        """
        If possible, read frequencies already running
        if not return default values
        Overwrite in specific HW
        """
        return 27000000, 30000000

    def connected(self) -> bool:
        return self.serial.is_open

    def getFeatures(self) -> set[str]:
        return self.features

    def getCalibration(self) -> str:
        return " ".join(list(self.exec_command("cal")))

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

    def readValues(self, value) -> list[complex]:
        logger.debug("VNA reading %s", value)
        result = [
            complex(*map(float, s.split())) for s in self.exec_command(value)
        ]
        logger.debug("VNA done reading %s (%d values)", value, len(result))
        return result

    def readVersion(self) -> "Version":
        result = list(self.exec_command("version"))
        logger.debug("result:\n%s", result)
        return Version(result[0])

    def setSweep(self, start, stop):
        list(self.exec_command(f"sweep {start} {stop} {self.datapoints}"))

    def setTXPower(self, freq_range, power_desc):
        raise NotImplementedError()

    def getSerialNumber(self) -> str:
        return " ".join(list(self.exec_command("sn")))
