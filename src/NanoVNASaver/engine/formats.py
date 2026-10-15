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
"""Conversion of complex S-parameters to display formats."""

import math
from enum import Enum

import numpy as np
import numpy.typing as npt

from .dsp import group_delay, unwrap_phase

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]

TINY = 1e-15


class TraceFormat(Enum):
    LOGMAG = "logmag"
    LINMAG = "linmag"
    PHASE = "phase"
    UNWRAPPED_PHASE = "uphase"
    GROUP_DELAY = "gdelay"
    VSWR = "vswr"
    REAL = "real"
    IMAG = "imag"
    RESISTANCE = "r"
    REACTANCE = "x"
    Z_MAG = "zmag"
    SERIES_L = "serl"
    SERIES_C = "serc"
    Q = "q"
    SMITH = "smith"
    POLAR = "polar"

    @property
    def label(self) -> str:
        return FORMAT_LABELS[self][0]

    @property
    def unit(self) -> str:
        return FORMAT_LABELS[self][1]

    @property
    def is_complex_plane(self) -> bool:
        return self in (TraceFormat.SMITH, TraceFormat.POLAR)


FORMAT_LABELS: dict[TraceFormat, tuple[str, str]] = {
    TraceFormat.LOGMAG: ("Log Mag", "dB"),
    TraceFormat.LINMAG: ("Lin Mag", "U"),
    TraceFormat.PHASE: ("Phase", "°"),
    TraceFormat.UNWRAPPED_PHASE: ("Unwrapped Phase", "°"),
    TraceFormat.GROUP_DELAY: ("Group Delay", "s"),
    TraceFormat.VSWR: ("VSWR", ""),
    TraceFormat.REAL: ("Real", "U"),
    TraceFormat.IMAG: ("Imaginary", "U"),
    TraceFormat.RESISTANCE: ("Resistance R", "Ω"),
    TraceFormat.REACTANCE: ("Reactance X", "Ω"),
    TraceFormat.Z_MAG: ("|Z|", "Ω"),
    TraceFormat.SERIES_L: ("Series L", "H"),
    TraceFormat.SERIES_C: ("Series C", "F"),
    TraceFormat.Q: ("Q factor", ""),
    TraceFormat.SMITH: ("Smith", ""),
    TraceFormat.POLAR: ("Polar", ""),
}


def gamma_to_z(values: ComplexArray, z0: float = 50.0) -> ComplexArray:
    values = np.asarray(values, dtype=np.complex128)
    with np.errstate(divide="ignore", invalid="ignore"):
        return z0 * (1 + values) / (1 - values)


def z_to_gamma(z: ComplexArray, z0: float = 50.0) -> ComplexArray:
    z = np.asarray(z, dtype=np.complex128)
    return (z - z0) / (z + z0)


def logmag(values: ComplexArray) -> FloatArray:
    return 20 * np.log10(np.maximum(np.abs(values), TINY))


def vswr(values: ComplexArray) -> FloatArray:
    mag = np.abs(values)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(mag < 1, (1 + mag) / (1 - mag), np.inf)


def convert(
    fmt: TraceFormat,
    freq: FloatArray,
    values: ComplexArray,
    z0: float = 50.0,
    gd_aperture: int = 1,
) -> FloatArray:
    """Real valued trace in the requested format.

    Smith and polar formats return the complex values unchanged (as a
    complex array) for the caller to plot."""
    values = np.asarray(values, dtype=np.complex128)
    freq = np.asarray(freq, dtype=np.float64)
    if fmt is TraceFormat.LOGMAG:
        return logmag(values)
    if fmt is TraceFormat.LINMAG:
        return np.abs(values)
    if fmt is TraceFormat.PHASE:
        return np.degrees(np.angle(values))
    if fmt is TraceFormat.UNWRAPPED_PHASE:
        return np.degrees(unwrap_phase(values))
    if fmt is TraceFormat.GROUP_DELAY:
        return group_delay(freq, values, gd_aperture)
    if fmt is TraceFormat.VSWR:
        return vswr(values)
    if fmt is TraceFormat.REAL:
        return values.real.copy()
    if fmt is TraceFormat.IMAG:
        return values.imag.copy()
    if fmt.is_complex_plane:
        return values  # type: ignore[return-value]
    z = gamma_to_z(values, z0)
    if fmt is TraceFormat.RESISTANCE:
        return z.real
    if fmt is TraceFormat.REACTANCE:
        return z.imag
    if fmt is TraceFormat.Z_MAG:
        return np.abs(z)
    omega = 2 * math.pi * freq
    with np.errstate(divide="ignore", invalid="ignore"):
        if fmt is TraceFormat.SERIES_L:
            return np.where(omega > 0, z.imag / omega, 0.0)
        if fmt is TraceFormat.SERIES_C:
            return np.where(
                (omega > 0) & (z.imag != 0), -1 / (omega * z.imag), np.inf
            )
        if fmt is TraceFormat.Q:
            return np.where(z.real != 0, np.abs(z.imag / z.real), np.inf)
    raise ValueError(f"Unknown format {fmt}")
