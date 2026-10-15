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
"""Python API for headless measurements.

Example::

    from NanoVNASaver.engine.session import VNASession

    with VNASession("virtual:demo") as vna:      # or "COM3", "/dev/ttyACM0"
        vna.load_calibration("my.cal")
        data = vna.sweep(100e6, 900e6, points=101, segments=4)
        print(vna.check("limits.json").summary())
        data.save("dut.s1p")
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..Calibration import Calibration
from ..Hardware.Hardware import get_interface_for_port, get_interfaces, get_VNA
from ..Hardware.VNA import VNA
from ..RFTools import Datapoint
from ..Settings.Sweep import Properties, Sweep
from .acquire import correct, read_averaged_segment
from .calkit import CalKit, CalKitLibrary
from .deembed import FixtureSettings
from .limits import LimitResult, LimitSpec
from .sweepdata import SweepData

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float], None]


def list_ports() -> list[str]:
    """Detected devices as port names usable for VNASession"""
    return [str(i.port) for i in get_interfaces()]


class VNASession:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, port: str = "virtual:demo") -> None:
        self.port = port
        self.vna: Optional[VNA] = None
        self.calibration = Calibration()
        self.fixture = FixtureSettings()
        self.smoothing_pct = 0.0
        self.last_raw: Optional[SweepData] = None
        self.last: Optional[SweepData] = None
        self.lock = threading.RLock()

    # connection

    def connect(self) -> "VNASession":
        iface = get_interface_for_port(self.port)
        iface.open()
        self.vna = get_VNA(iface)
        logger.info("Connected to %s on %s", self.vna.name, self.port)
        return self

    def close(self) -> None:
        if self.vna is not None:
            try:
                self.vna.disconnect()
            except OSError as exc:
                logger.warning("Disconnect failed: %s", exc)
            self.vna = None

    def __enter__(self) -> "VNASession":
        return self.connect()

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def device(self) -> VNA:
        if self.vna is None:
            raise RuntimeError("Not connected")
        return self.vna

    def info(self) -> dict:
        vna = self.device
        return {
            "name": vna.name,
            "port": self.port,
            "serial": vna.SN,
            "firmware": str(vna.version),
            "features": sorted(vna.features),
            "points": list(vna.valid_datapoints),
            "max_frequency": vna.sweep_max_freq_hz,
        }

    # configuration

    def set_points(self, points: int) -> None:
        if points not in self.device.valid_datapoints:
            raise ValueError(
                f"{points} points not supported, use one of"
                f" {sorted(self.device.valid_datapoints)}"
            )
        self.device.datapoints = points

    def load_calibration(
        self, filename: str | Path, kit: str | CalKit = "Ideal"
    ) -> None:
        """Load a NanoVNA-Saver .cal file. kit is the name of a kit in the
        library, a path to a kit JSON file or a CalKit."""
        cal = Calibration()
        cal.load(str(filename))
        self._apply_kit(cal, kit)
        cal.calc_corrections()
        self.calibration = cal

    @staticmethod
    def _apply_kit(cal: Calibration, kit: str | CalKit) -> None:
        if isinstance(kit, str):
            path = Path(kit)
            kit = (
                CalKit.load(path)
                if path.suffix == ".json" and path.exists()
                else CalKitLibrary().get(kit)
            )
        kit.apply_to(cal.cal_element)

    # measurement

    def raw_sweep(  # noqa: PLR0913
        self,
        start: float,
        stop: float,
        points: Optional[int] = None,
        segments: int = 1,
        averages: int = 1,
        truncates: int = 0,
        logarithmic: bool = False,
        progress: Optional[ProgressCallback] = None,
    ) -> SweepData:
        """Uncorrected sweep (as measured by the device)"""
        with self.lock:
            vna = self.device
            if points is not None:
                self.set_points(points)
            sweep = Sweep(
                int(start),
                int(stop),
                vna.datapoints,
                segments,
                Properties(logarithmic=logarithmic),
            )
            freq: list[int] = []
            s11: list[complex] = []
            s21: list[complex] = []
            for i in range(sweep.segments):
                seg_start, seg_stop = sweep.get_index_range(i)
                f, v11, v21 = read_averaged_segment(
                    vna, seg_start, seg_stop, averages, truncates
                )
                freq.extend(f)
                s11.extend(v11)
                s21.extend(v21)
                if progress:
                    progress((i + 1) / sweep.segments)
            if sweep.segments > 1:
                vna.resetSweep(sweep.start, sweep.end)
            raw = SweepData(
                np.asarray(freq, dtype=np.float64),
                np.asarray(s11, dtype=np.complex128),
                np.asarray(s21, dtype=np.complex128),
            )
            self.last_raw = raw
            return raw

    def process(self, raw: SweepData) -> SweepData:
        return correct(
            raw, self.calibration, 0.0, self.fixture, self.smoothing_pct
        )

    def sweep(self, start: float, stop: float, **kwargs) -> SweepData:
        """Calibrated, fixture corrected and smoothed sweep"""
        raw = self.raw_sweep(start, stop, **kwargs)
        self.last = self.process(raw)
        return self.last

    def full_two_port(
        self,
        start: float,
        stop: float,
        reverse_prompt: Callable[[], None],
        **kwargs,
    ) -> SweepData:
        """Forward sweep, reverse_prompt() (turn the DUT around), reverse
        sweep. Returns the fully corrected 2-port data."""
        fwd = self.raw_sweep(start, stop, **kwargs)
        reverse_prompt()
        rev = self.raw_sweep(start, stop, **kwargs)
        raw = SweepData(
            fwd.freq, fwd.s11, fwd.s21, s12=rev.s21, s22=rev.s11, z0=fwd.z0
        )
        self.last = self.process(raw)
        return self.last

    def capture_standard(
        self, standard: str, start: float, stop: float, **kwargs
    ) -> None:
        """Measure a calibration standard (short, open, load, isolation,
        thru) for a scripted calibration"""
        raw = self.raw_sweep(start, stop, **kwargs)
        dps11 = raw.datapoints("s11")
        dps21 = raw.datapoints("s21")
        names: dict[str, list[tuple[str, list[Datapoint]]]] = {
            "short": [("short", dps11)],
            "open": [("open", dps11)],
            "load": [("load", dps11)],
            "isolation": [("isolation", dps21)],
            "thru": [("thrurefl", dps11), ("through", dps21)],
        }
        if standard not in names:
            raise ValueError(f"Unknown standard {standard}")
        for name, dps in names[standard]:
            self.calibration.insert(name, dps)

    def apply_calibration(self, kit: str | CalKit = "Ideal") -> None:
        self._apply_kit(self.calibration, kit)
        self.calibration.calc_corrections()

    def save_calibration(self, filename: str | Path) -> None:
        self.calibration.save(str(filename))

    def check(self, spec: LimitSpec | str | Path) -> LimitResult:
        if self.last is None:
            raise RuntimeError("No sweep to check")
        if not isinstance(spec, LimitSpec):
            spec = LimitSpec.load(spec)
        return spec.evaluate(self.last)
