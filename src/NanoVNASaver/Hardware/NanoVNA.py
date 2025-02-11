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

import serial
from PySide6.QtGui import QPixmap

from ..utils import Version
from .Convert import get_argb32_pixmap
from .Serial import Interface, drain_serial
from .VNA import VNA

logger = logging.getLogger(__name__)


class NanoVNA(VNA):
    name = "NanoVNA"
    screenwidth = 320
    screenheight = 240

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.sweep_method = "sweep"
        self.init_features()
        logger.debug("Setting initial start,stop")
        self.start, self.stop = self._get_running_frequencies()
        self.sweep_max_freq_hz = 300e6
        self._sweepdata: list[tuple[complex, complex]] = []

    def _get_running_frequencies(self):
        logger.debug("Reading values: frequencies")
        try:
            frequencies = super().readValues("frequencies")
            return int(frequencies[0].real), int(frequencies[-1].real)
        except serial.SerialException as e:
            logger.warning("%s reading frequencies", e)
            logger.info("falling back to generic")

        return VNA._get_running_frequencies(self)

    def _capture_data(self) -> bytes:
        timeout = self.serial.timeout
        with self.serial.lock:
            drain_serial(self.serial)
            self.serial.write("capture\r".encode("ascii"))
            self.serial.readline()
            self.serial.timeout = 4
            image_data = self.serial.read(
                self.screenwidth * self.screenheight * 2
            )
            self.serial.timeout = timeout
        self.serial.timeout = timeout
        return image_data

    def getScreenshot(self) -> QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.connected():
            return QPixmap()
        try:
            logger.debug("Captured screenshot")
            return get_argb32_pixmap(
                self._capture_data(), self.screenwidth, self.screenheight
            )
        except serial.SerialException as exc:
            logger.exception("Exception while capturing screenshot: %s", exc)
        return QPixmap()

    def resetSweep(self, start: int, stop: int):
        list(self.exec_command(f"sweep {start} {stop} {self.datapoints}"))
        list(self.exec_command("resume"))

    def setSweep(self, start, stop):
        self.start = start
        self.stop = stop
        if self.sweep_method == "sweep":
            list(self.exec_command(f"sweep {start} {stop} {self.datapoints}"))
        elif self.sweep_method == "scan":
            list(self.exec_command(f"scan {start} {stop} {self.datapoints}"))

    def init_features(self) -> None:
        super().init_features()
        if self.version >= Version.parse("0.7.1"):
            logger.debug("Using scan mask command.")
            self.features.add("Scan mask command")
            self.sweep_method = "scan_mask"
        elif self.version >= Version.parse("0.2.0"):
            logger.debug("Using new scan command.")
            self.features.add("Scan command")
            self.sweep_method = "scan"

    def read_frequencies(self) -> list[int]:
        logger.debug("readFrequencies: %s", self.sweep_method)
        if self.sweep_method != "scan_mask":
            return super().read_frequencies()
        return [
            int(line)
            for line in self.exec_command(
                f"scan {self.start} {self.stop} {self.datapoints} 0b001"
            )
        ]

    def readValues(self, value) -> list[complex]:
        if self.sweep_method != "scan_mask":
            return super().readValues(value)
        logger.debug("readValue with scan mask (%s)", value)
        # Actually grab the data only when requesting channel 0.
        # The hardware will return all channels which we will store.
        if value == "data 0":
            self._sweepdata = []
            for line in self.exec_command(
                f"scan {self.start} {self.stop} {self.datapoints} 0b110"
            ):
                d = list(map(float, line.split()))
                self._sweepdata.append(
                    (complex(d[0], d[1]), complex(d[2], d[3]))
                )
        if value == "data 1":
            return [x[1] for x in self._sweepdata]
        # default to data 0
        return [x[0] for x in self._sweepdata]
