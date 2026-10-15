#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
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
"""A simulated VNA for demos, training and testing without hardware.

Port names:
  virtual:demo            band pass filter DUT, realistic error model
  virtual:antenna         dual band antenna (1-port)
  virtual:ideal           filter DUT without error model / noise
  virtual:<file.s1p|s2p>  replay a Touchstone file as DUT

The connected item can be switched (short, open, load, thru, isolation,
dut) and the DUT can be reversed, so calibration and the full 2-port
procedure can be exercised exactly like on a real device.
"""

import logging
import math
from time import sleep
from typing import Optional

import numpy as np

from ..utils import Version
from .Serial import Interface
from .VNA import VNA

logger = logging.getLogger(__name__)

STANDARDS = ("dut", "short", "open", "load", "thru", "isolation")


class VirtualInterface(Interface):
    """Interface stand-in that never touches a serial port"""

    def __init__(self, source: str = "demo"):
        super().__init__("virtual", "Virtual")
        self.source = source
        self.port = f"virtual:{source}"

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    # pyserial calls these when settings change or buffers are flushed;
    # there is no port behind a virtual interface.
    def _reconfigure_port(self, *args, **kwargs) -> None:
        pass

    def reset_input_buffer(self) -> None:
        pass

    def reset_output_buffer(self) -> None:
        pass

    def read(self, size: int = 1) -> bytes:
        return b""

    def readline(self, *args, **kwargs) -> bytes:
        return b""

    def write(self, data) -> int:
        return len(data)

    def __str__(self) -> str:
        return f"Virtual VNA ({self.source})"


def _bandpass(freq: np.ndarray, f0: float, bw: float) -> tuple:
    """2nd order Butterworth band pass (lossless prototype)"""
    with np.errstate(divide="ignore", invalid="ignore"):
        p = 1j * (freq / f0 - f0 / np.maximum(freq, 1.0)) * f0 / bw
    den = p**2 + math.sqrt(2) * p + 1
    return p**2 / den, 1 / den


def demo_filter(freq: np.ndarray) -> np.ndarray:
    """(n, 2, 2) S matrix: band pass at 435 MHz, 1 dB loss, 80 ps line at
    port 2 (asymmetric so S11 != S22)"""
    s11f, s21f = _bandpass(freq, 435e6, 60e6)
    loss = 10 ** (-1.0 / 20)
    line = np.exp(-2j * math.pi * freq * 80e-12)
    delay = np.exp(-2j * math.pi * freq * 1.5e-9)
    s = np.empty((len(freq), 2, 2), dtype=np.complex128)
    s[:, 0, 0] = s11f * 0.98
    s[:, 1, 1] = s11f * 0.98 * line**2
    s[:, 1, 0] = s21f * loss * line * delay
    s[:, 0, 1] = s[:, 1, 0]
    return s


def demo_antenna(freq: np.ndarray) -> np.ndarray:
    """Dual band (145 / 435 MHz) antenna, S21 = isolation only"""
    gamma = np.zeros(len(freq), dtype=np.complex128)
    z_par = np.zeros(len(freq), dtype=np.complex128)
    omega = 2 * math.pi * np.maximum(freq, 1.0)
    for f0, r, q in ((145e6, 38.0, 12.0), (435e6, 62.0, 18.0)):
        w0 = 2 * math.pi * f0
        lval = q * r / w0
        cval = 1 / (w0**2 * lval)
        z = r + 1j * (omega * lval - 1 / (omega * cval))
        z_par = z_par + 1 / z
    zin = 1 / z_par
    gamma = (zin - 50) / (zin + 50)
    s = np.zeros((len(freq), 2, 2), dtype=np.complex128)
    s[:, 0, 0] = gamma
    s[:, 1, 1] = gamma
    return s


class ErrorModel:
    """Smooth, frequency dependent 12-term (forward) error model"""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def terms(self, freq: np.ndarray) -> dict[str, np.ndarray]:
        w = 2 * math.pi * freq
        if not self.enabled:
            one = np.ones(len(freq), dtype=np.complex128)
            zero = np.zeros(len(freq), dtype=np.complex128)
            return {
                "e00": zero,
                "e11": zero,
                "e10e01": one,
                "e22": zero,
                "e10e32": one,
                "e30": zero,
            }
        loss = 10 ** (-0.4 * np.sqrt(freq / 1e9) / 20)
        return {
            "e00": 0.03 * np.exp(-1j * w * 0.3e-9) + 0.01,
            "e11": 0.06 * np.exp(-1j * w * 0.5e-9),
            "e10e01": 0.92 * loss**2 * np.exp(-2j * w * 0.4e-9),
            "e22": 0.05 * np.exp(-1j * w * 0.7e-9),
            "e10e32": 0.85 * loss * np.exp(-1j * w * 1.2e-9),
            "e30": np.full(len(freq), 2e-4 + 1e-4j),
        }

    def measure(
        self, freq: np.ndarray, s: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        t = self.terms(freq)
        s11, s21 = s[:, 0, 0], s[:, 1, 0]
        s12, s22 = s[:, 0, 1], s[:, 1, 1]
        ds = s11 * s22 - s21 * s12
        den = 1 - t["e11"] * s11 - t["e22"] * s22 + t["e11"] * t["e22"] * ds
        s11m = t["e00"] + t["e10e01"] * (s11 - t["e22"] * ds) / den
        s21m = t["e30"] + t["e10e32"] * s21 / den
        return s11m, s21m


class VirtualVNA(VNA):
    name = "Virtual VNA"
    valid_datapoints = (101, 201, 401, 801, 1001, 51, 11)
    sweep_points_max = 1001
    sweep_points_min = 11
    sweep_max_freq_hz = 6e9

    def __init__(self, iface: Interface):
        source = getattr(iface, "source", "demo")
        self.source = source
        self.standard = "dut"
        self.reversed = False
        self.noise = 0.0 if source == "ideal" else 1.5e-3
        self.errors = ErrorModel(enabled=source != "ideal")
        self.sweep_delay_per_point = 0.0 if source == "ideal" else 20e-6
        self._file_freq: Optional[np.ndarray] = None
        self._file_s: Optional[np.ndarray] = None
        self._rng = np.random.default_rng()
        if source not in ("demo", "antenna", "ideal"):
            self._load_file(source)
        super().__init__(iface)
        self.start = 1_000_000
        self.stop = 900_000_000
        self._cache: tuple[np.ndarray, np.ndarray] | None = None

    def _load_file(self, filename: str) -> None:
        # imported here to keep the hardware layer free of engine imports
        from ..engine.sweepdata import SweepData

        data = SweepData.load(filename)
        self._file_freq = data.freq
        self._file_s = data.s_matrix()
        logger.info("Virtual VNA replays %s (%d points)", filename, len(data))

    def read_fw_version(self) -> Version:
        return Version.parse("1.0.0")

    def init_features(self) -> None:
        self.features.add("Customizable data points")
        self.features.add("Virtual")

    def getSerialNumber(self) -> str:
        return f"VIRTUAL-{self.source}"

    def readFirmware(self) -> str:
        return (
            "Virtual VNA\n"
            f"Source: {self.source}\n"
            f"Connected: {self.standard}"
            f"{' (reversed)' if self.reversed else ''}"
        )

    def set_standard(self, standard: str) -> None:
        if standard not in STANDARDS:
            raise ValueError(f"Unknown standard {standard}")
        self.standard = standard

    def setSweep(self, start, stop):
        self.start, self.stop = int(start), int(stop)
        self._cache = None

    def resetSweep(self, start: int, stop: int):
        self.setSweep(start, stop)

    def frequencies(self) -> np.ndarray:
        return np.round(np.linspace(self.start, self.stop, self.datapoints))

    def _dut(self, freq: np.ndarray) -> np.ndarray:
        if self._file_s is not None and self._file_freq is not None:
            s = np.empty((len(freq), 2, 2), dtype=np.complex128)
            for i in range(2):
                for j in range(2):
                    v = self._file_s[:, i, j]
                    s[:, i, j] = np.interp(
                        freq, self._file_freq, v.real
                    ) + 1j * np.interp(freq, self._file_freq, v.imag)
            return s
        if self.source == "antenna":
            return demo_antenna(freq)
        return demo_filter(freq)

    def _connected(self, freq: np.ndarray) -> np.ndarray:
        n = len(freq)
        s = np.zeros((n, 2, 2), dtype=np.complex128)
        if self.standard == "dut":
            s = self._dut(freq)
            if self.reversed:
                s = s[:, ::-1, ::-1].copy()
            return s
        if self.standard == "short":
            s[:, 0, 0] = -1
        elif self.standard == "open":
            s[:, 0, 0] = 1
        elif self.standard == "thru":
            s[:, 1, 0] = s[:, 0, 1] = 1
        # load / isolation: all zero (matched terminations)
        return s

    def _measure(self) -> tuple[np.ndarray, np.ndarray]:
        if self._cache is None:
            freq = self.frequencies()
            s11m, s21m = self.errors.measure(freq, self._connected(freq))
            if self.noise > 0:
                n = len(freq)
                s11m = s11m + self.noise * (
                    self._rng.normal(size=n) + 1j * self._rng.normal(size=n)
                )
                s21m = s21m + self.noise * (
                    self._rng.normal(size=n) + 1j * self._rng.normal(size=n)
                )
            if self.sweep_delay_per_point:
                sleep(self.sweep_delay_per_point * len(freq))
            self._cache = (s11m, s21m)
        return self._cache

    def read_frequencies(self) -> list[int]:
        self._cache = None  # every frequency read starts a new sweep
        return [int(f) for f in self.frequencies()]

    def readValues(self, value) -> list[complex]:
        if value == "frequencies":
            return [complex(f) for f in self.frequencies()]
        s11m, s21m = self._measure()
        if value == "data 0":
            return s11m.tolist()
        if value == "data 1":
            result = s21m.tolist()
            self._cache = None
            return result
        raise ValueError(f"Unknown value {value}")

    def flushSerialBuffers(self):
        pass

    def reconnect(self):
        pass
