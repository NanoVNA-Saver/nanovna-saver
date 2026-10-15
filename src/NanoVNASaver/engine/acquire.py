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
"""Reading raw sweep data from a device (shared by GUI and headless)."""

import logging
from time import sleep
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np
import numpy.typing as npt

from ..Calibration import Calibration
from .deembed import FixtureSettings, apply_fixture
from .dsp import smooth
from .sweepdata import SweepData

if TYPE_CHECKING:
    from ..Hardware.VNA import VNA

logger = logging.getLogger(__name__)

VALUE_MAX: float = 9.5
RETRIES_RECONNECT: int = 5
RETRIES_MAX: int = 10

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]


class SweepStoppedError(Exception):
    """Raised when a sweep is stopped during averaging"""


def truncate(values: list[list[complex]], count: int) -> list[list[complex]]:
    """truncate drops extrema from data list if averaging is active"""
    keep = len(values) - count
    logger.debug("Truncating from %d values to %d", len(values), keep)
    if count < 1 or keep < 1:
        logger.info("Not doing illegal truncate")
        return values
    truncated = []
    for valueset in np.swapaxes(values, 0, 1).tolist():
        avg = complex(np.average(valueset))

        def cmp_fn(v: complex, avg=avg) -> float:
            return float(abs(avg - v))

        truncated.append(sorted(valueset, key=cmp_fn)[:keep])
    return np.swapaxes(truncated, 0, 1).tolist()


def read_data(vna: "VNA", data: str) -> list[complex]:
    logger.debug("Reading %s", data)
    retries = RETRIES_MAX
    while retries:
        retries -= 1
        try:
            result = vna.readValues(data)
            logger.debug("Read %d values", len(result))
            if vna.validateInput and any(abs(v) > VALUE_MAX for v in result):
                logger.error("Got a non plausible data: (%s)", data)
            else:
                return result
        except ValueError as exc:
            logger.exception("An exception occurred reading %s: %s", data, exc)
        logger.error("Re-reading %s", data)
        sleep(0.2)
        vna.reconnect()

    logger.critical(
        "Tried and failed to read %s %s times. Giving up.", data, RETRIES_MAX
    )
    raise IOError(
        f"Failed reading {data} {RETRIES_MAX} times.\n"
        f"Data outside expected valid ranges,"
        f" or in an unexpected format.\n\n"
        f"You can disable data validation on the"
        f"device settings screen."
    )


def read_segment(
    vna: "VNA", start: int, stop: int
) -> tuple[list[int], list[complex], list[complex]]:
    logger.debug("Setting sweep range to %d to %d", start, stop)
    vna.setSweep(start, stop)
    frequencies = vna.read_frequencies()
    logger.debug("Read %s frequencies", len(frequencies))
    values11 = read_data(vna, "data 0")
    values21 = read_data(vna, "data 1")
    if not len(frequencies) == len(values11) == len(values21):
        logger.info("No valid data during this run")
        return [], [], []
    return frequencies, values11, values21


def read_averaged_segment(  # noqa: PLR0913
    vna: "VNA",
    start: int,
    stop: int,
    averages: int = 1,
    truncates: int = 0,
    should_stop: Callable[[], bool] = lambda: False,
    on_progress: Optional[Callable[[], None]] = None,
) -> tuple[list[int], list[complex], list[complex]]:
    logger.info(
        "Reading from %d to %d. Averaging %d values", start, stop, averages
    )
    freq: list[int] = []
    values11: list[list[complex]] = []
    values21: list[list[complex]] = []

    for i in range(averages):
        if should_stop():
            logger.debug("Stopping averaging as signalled.")
            if averages == 1:
                break
            logger.warning("Stop during average. Discarding sweep result.")
            raise SweepStoppedError()
        logger.debug("Reading average no %d / %d", i + 1, averages)
        retries = RETRIES_RECONNECT
        tmp_11: list[complex] = []
        tmp_21: list[complex] = []
        while retries and not tmp_11:
            if retries < RETRIES_RECONNECT:
                logger.warning("retry readSegment(%s,%s)", start, stop)
                sleep(0.5)
            retries -= 1
            freq, tmp_11, tmp_21 = read_segment(vna, start, stop)

        if not tmp_11:
            raise IOError("Invalid data during sweep")

        values11.append(tmp_11)
        values21.append(tmp_21)
        if on_progress:
            on_progress()

    if not values11:
        if should_stop():
            raise SweepStoppedError()
        raise IOError("Invalid data during sweep")

    if truncates > 0 and averages > 1:
        logger.debug("Truncating %d values by %d", len(values11), truncates)
        values11 = truncate(values11, truncates)
        values21 = truncate(values21, truncates)

    return (
        freq,
        np.average(values11, axis=0).tolist(),
        np.average(values21, axis=0).tolist(),
    )


def correct(
    raw: SweepData,
    calibration: Optional[Calibration] = None,
    offset_delay: float = 0.0,
    fixture: Optional[FixtureSettings] = None,
    smoothing_pct: float = 0.0,
) -> SweepData:
    """Raw data -> calibrated, fixture removed, smoothed data"""
    out = raw.copy()
    if calibration is not None and calibration.isCalculated:
        if calibration.isValid1Port():
            out.s11 = calibration.correct11_array(raw.freq, raw.s11)
        if calibration.isValid2Port():
            out.s21 = calibration.correct21_array(raw.freq, raw.s21, raw.s11)
            if raw.is_full_two_port:
                out.s11, out.s21, out.s12, out.s22 = (
                    calibration.correct_two_port_array(
                        raw.freq, raw.s11, raw.s21, raw.s12, raw.s22
                    )
                )
    if offset_delay != 0.0:
        out = _legacy_offset_delay(out, offset_delay)
    if fixture is not None:
        out = apply_fixture(out, fixture)
    if smoothing_pct > 0:
        for name in ("s11", "s21", "s12", "s22"):
            values = out.param(name)
            if values is not None:
                setattr(out, name, smooth(values, smoothing_pct))
    return out


def _legacy_offset_delay(data: SweepData, delay: float) -> SweepData:
    """The offset delay of the calibration window (same convention as
    Calibration.correct_delay)"""
    reflect = np.exp(-2j * np.pi * data.freq * delay * 2)
    trans = np.exp(-2j * np.pi * data.freq * delay)
    out = data.copy()
    out.s11 = data.s11 * reflect
    out.s21 = data.s21 * trans
    if data.s22 is not None:
        out.s22 = data.s22 * reflect
    if data.s12 is not None:
        out.s12 = data.s12 * trans
    return out
