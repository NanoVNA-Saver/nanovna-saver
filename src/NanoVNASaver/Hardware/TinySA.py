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
import struct

import numpy as np
import serial
from PyQt6.QtGui import QImage, QPixmap

from NanoVNASaver.Hardware.Serial import Interface, drain_serial
from NanoVNASaver.Hardware.VNA import VNA
from NanoVNASaver.Version import Version

logger = logging.getLogger(__name__)


class TinySA(VNA):
    name = "tinySA"
    screenwidth = 320
    screenheight = 240
    valid_datapoints = (290,)

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.features = {"Screenshots"}
        logger.debug("Setting initial start,stop")
        self.start, self.stop = self._get_running_frequencies()
        self.sweep_max_freq_Hz = 950e6
        self._sweepdata = []
        self.validateInput = False

    def _get_running_frequencies(self):
        logger.debug("Reading values: frequencies")
        try:
            frequencies = super().readValues("frequencies")
            return int(frequencies[0]), int(frequencies[-1])
        except Exception as e:
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

    def _convert_data(self, image_data: bytes) -> bytes:
        rgb_data = struct.unpack(
            f">{self.screenwidth * self.screenheight}H", image_data
        )
        rgb_array = np.array(rgb_data, dtype=np.uint32)
        return (
            0xFF000000
            + ((rgb_array & 0xF800) << 8)
            + ((rgb_array & 0x07E0) << 5)
            + ((rgb_array & 0x001F) << 3)
        )

    def getScreenshot(self) -> QPixmap:
        logger.debug("Capturing screenshot...")
        if not self.connected():
            return QPixmap()
        try:
            rgba_array = self._convert_data(self._capture_data())
            image = QImage(
                rgba_array,
                self.screenwidth,
                self.screenheight,
                QImage.Format.Format_ARGB32,
            )
            logger.debug("Captured screenshot")
            return QPixmap(image)
        except serial.SerialException as exc:
            logger.exception("Exception while capturing screenshot: %s", exc)
        return QPixmap()

    def resetSweep(self, start: int, stop: int):
        return

    def setSweep(self, start, stop):
        self.start = start
        self.stop = stop
        list(self.exec_command(f"sweep {start} {stop} {self.datapoints}"))
        list(self.exec_command("trigger auto"))

    def read_frequencies(self) -> list[int]:
        logger.debug("readFrequencies")
        return [int(line).real for line in self.exec_command("frequencies")]

    def readValues(self, value) -> list[complex]:
        def conv2complex(data: str) -> complex:
            try:
                return complex(10 ** (float(data.strip()) / 20), 0.0)
            except ValueError:
                return complex(0.0, 0.0)

        logger.debug("Read: %s", value)
        if value == "data 0":
            self._sweepdata = [
                conv2complex(line) for line in self.exec_command("data 0")
            ]
        return self._sweepdata


class TinySA_Ultra(TinySA):  # noqa: N801
    name = "tinySA Ultra"
    screenwidth = 480
    screenheight = 320
    valid_datapoints = (450, 51, 101, 145, 290)
    hardware_revision = None

    def __init__(self, iface: Interface):
        super().__init__(iface)
        self.features = {"Screenshots", "Customizable data points"}
        logger.debug("Setting initial start,stop")
        self.start, self.stop = self._get_running_frequencies()
        self.sweep_max_freq_Hz = 5.4e9
        self._sweepdata = []
        self.validateInput = False
        self.version = self.read_firmware_version()
        self.hardware_revision = self.read_hardware_revision()
        # detect model versions of tinySA Ultra including ZS-405, ZS406 (Ultra+), ZS407 (Ultra+)
        if self.hardware_revision >= Version("0.5.3"):
            self.name = "tinySA Ultra+ ZS-407"
            self.sweep_max_freq_Hz = 7.3e9
        elif self.hardware_revision >= Version("0.4.6"):
            self.name = "tinySA Ultra+ ZS-406"
            self.sweep_max_freq_Hz = 5.4e9
        elif self.hardware_revision >= Version("0.4.5"):
            self.name = "tinySA Ultra ZS-405"
            self.sweep_max_freq_Hz = 5.3e9
        else:
            # version 0.3.x is for tinySA
            self.name = "tinySA"
            self.sweep_max_freq_Hz = 0.96e9

    def read_firmware_version(self) -> "Version":
        """For example, command version in TinySA returns as this
        tinySA4_v1.4-193-g6ff182b
        HW Version:V0.5.4 max2871
        """
        result = list(self.exec_command("version"))
        logger.debug("firmware version result:\n%s", result[0])
        # transform from tinySA4_v1.4-193-g6ff182b to 1.4.193
        major_minor_version, revision_version, hash = (
            result[0].split("_v")[1].split("-")
        )
        revision_version = revision_version.split("-")[0]
        return Version(major_minor_version + "." + revision_version)

    def read_hardware_revision(self) -> str:
        result = list(self.exec_command("version"))
        logger.debug("hardware version result:\n%s", result[1])
        return Version(result[1])
