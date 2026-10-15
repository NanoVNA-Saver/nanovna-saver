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
from time import monotonic

import numpy as np
import serial
from PySide6.QtGui import QPixmap

from ..utils import Version
from .Convert import get_argb32_pixmap
from .Serial import Interface, drain_serial
from .VNA import VNA, _max_retries

logger = logging.getLogger(__name__)

SCAN_MASK_ALL = 0b111  # frequency, data 0 (S11), data 1 (S21)
SCAN_MASK_BINARY = 0x80
BINARY_RECORD = np.dtype(
    [("freq", "<u4"), ("s11", "<f4", (2,)), ("s21", "<f4", (2,))]
)
SCAN_METHODS_MASK = ("scan_mask", "scan_bin")


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
        self._sweepdata = []
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
            if "scan_bin" in self.help_text.split():
                logger.debug("Using binary scan command.")
                self.features.add("Binary scan")
                self.sweep_method = "scan_bin"
        elif self.version >= Version.parse("0.2.0"):
            logger.debug("Using new scan command.")
            self.features.add("Scan command")
            self.sweep_method = "scan"

    def _scan_text(self) -> tuple[list[int], list[complex], list[complex]]:
        freqs: list[int] = []
        s11: list[complex] = []
        s21: list[complex] = []
        for line in self.exec_command(
            f"scan {self.start} {self.stop} {self.datapoints} {SCAN_MASK_ALL}"
        ):
            d = line.split()
            freqs.append(int(d[0]))
            s11.append(complex(float(d[1]), float(d[2])))
            s21.append(complex(float(d[3]), float(d[4])))
        return freqs, s11, s21

    def _read_exact(self, count: int, deadline: float) -> bytes:
        buf = bytearray()
        while len(buf) < count:
            chunk = self.serial.read(count - len(buf))
            if chunk:
                buf += chunk
            elif monotonic() > deadline:
                raise IOError(f"binary scan timeout ({len(buf)}/{count})")
        return bytes(buf)

    def _read_until(self, token: bytes, deadline: float) -> bytes:
        buf = bytearray()
        while not buf.endswith(token):
            chunk = self.serial.read(1)
            if chunk:
                buf += chunk
            elif monotonic() > deadline:
                raise IOError(f"binary scan: missing {token!r}")
        return bytes(buf)

    def _scan_binary(self) -> tuple[list[int], list[complex], list[complex]]:
        """One sweep in binary format (DiSlord firmware, scan_bin):
        uint16 mask, uint16 points, then per point
        uint32 freq, float32[2] data0, float32[2] data1"""
        cmd = f"scan_bin {self.start} {self.stop} {self.datapoints}"
        cmd += f" {SCAN_MASK_ALL}"
        timeout = 2.0 + _max_retries(self.bandwidth, self.datapoints) * 0.05
        with self.serial.lock:
            drain_serial(self.serial)
            deadline = monotonic() + timeout
            self.serial.write(f"{cmd}\r".encode("ascii"))
            self._read_until(b"\n", deadline)  # echo
            mask, points = struct.unpack("<HH", self._read_exact(4, deadline))
            if (
                mask & SCAN_MASK_ALL != SCAN_MASK_ALL
                or points != self.datapoints
            ):
                raise ValueError(f"unexpected header mask={mask} n={points}")
            payload = self._read_exact(
                points * BINARY_RECORD.itemsize, deadline
            )
            self._read_until(b"ch> ", deadline)
        rec = np.frombuffer(payload, dtype=BINARY_RECORD)
        freqs = rec["freq"].astype(np.int64)
        if len(freqs) > 1 and not np.all(np.diff(freqs) > 0):
            raise ValueError("binary scan: frequencies not ascending")
        s11 = rec["s11"][:, 0] + 1j * rec["s11"][:, 1]
        s21 = rec["s21"][:, 0] + 1j * rec["s21"][:, 1]
        return freqs.tolist(), s11.tolist(), s21.tolist()

    def _scan(self) -> tuple[list[int], list[complex], list[complex]]:
        if self.sweep_method == "scan_bin":
            try:
                return self._scan_binary()
            except (IOError, ValueError, struct.error) as exc:
                logger.warning(
                    "Binary scan failed (%s), falling back to text scan", exc
                )
                self.sweep_method = "scan_mask"
                self.features.discard("Binary scan")
                with self.serial.lock:
                    drain_serial(self.serial)
        return self._scan_text()

    def read_frequencies(self) -> list[int]:
        logger.debug("readFrequencies: %s", self.sweep_method)
        if self.sweep_method not in SCAN_METHODS_MASK:
            return super().read_frequencies()
        # A single scan delivers frequencies and both channels.
        freqs, s11, s21 = self._scan()
        self._sweepdata = list(zip(s11, s21, strict=True))
        return freqs

    def readValues(self, value) -> list[complex]:
        if self.sweep_method not in SCAN_METHODS_MASK:
            return super().readValues(value)
        logger.debug("readValue with scan mask (%s)", value)
        if value == "frequencies":
            return [complex(f) for f in self.read_frequencies()]
        if not self._sweepdata:
            _, s11, s21 = self._scan()
            self._sweepdata = list(zip(s11, s21, strict=True))
        if value == "data 1":
            result = [x[1] for x in self._sweepdata]
            self._sweepdata = []  # next read starts a new sweep
            return result
        # default to data 0
        return [x[0] for x in self._sweepdata]
