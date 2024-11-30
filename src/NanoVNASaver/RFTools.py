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
import cmath
import math
from typing import NamedTuple

from NanoVNASaver.SITools import Format, clamp_value

FMT_FREQ = Format()
FMT_SHORT = Format(max_nr_digits=4)
FMT_SWEEP = Format(max_nr_digits=9, allow_strip=True)


class Datapoint(NamedTuple):
    freq: int
    re: float
    im: float

    @property
    def z(self) -> complex:
        """return the s value complex number"""
        return complex(self.re, self.im)

    @property
    def phase(self) -> float:
        """return the datapoint's phase value"""
        return cmath.phase(self.z)

    @property
    def gain(self) -> float:
        mag = abs(self.z)
        return 20 * math.log10(mag) if mag > 0 else -math.inf

    @property
    def vswr(self) -> float:
        mag = abs(self.z)
        return (1 + mag) / (1 - mag) if mag < 1 else math.inf

    @property
    def wavelength(self) -> float:
        return 299792458 / self.freq if self.freq else math.inf

    def impedance(self, ref_impedance: float = 50) -> complex:
        return gamma_to_impedance(self.z, ref_impedance)

    def shuntImpedance(self, ref_impedance: float = 50) -> complex:
        try:
            return 0.5 * ref_impedance * self.z / (1 - self.z)
        except ZeroDivisionError:
            return math.inf

    def seriesImpedance(self, ref_impedance: float = 50) -> complex:
        try:
            return 2 * ref_impedance * (1 - self.z) / self.z
        except ZeroDivisionError:
            return math.inf

    def qFactor(self, ref_impedance: float = 50) -> float:
        imp = self.impedance(ref_impedance)
        return -1 if imp.real == 0.0 else abs(imp.imag / imp.real)

    def capacitiveEquivalent(self, ref_impedance: float = 50) -> float:
        return impedance_to_capacitance(
            self.impedance(ref_impedance), self.freq
        )

    def inductiveEquivalent(self, ref_impedance: float = 50) -> float:
        return impedance_to_inductance(self.impedance(ref_impedance), self.freq)


def gamma_to_impedance(gamma: complex, ref_impedance: float = 50) -> complex:
    """Calculate impedance from gamma"""
    try:
        return ((-gamma - 1) / (gamma - 1)) * ref_impedance
    except ZeroDivisionError:
        return math.inf


def groupDelay(data: list[Datapoint], index: int) -> float:
    idx0 = clamp_value(index - 1, 0, len(data) - 1)
    idx1 = clamp_value(index + 1, 0, len(data) - 1)
    delta_angle = data[idx1].phase - data[idx0].phase
    delta_freq = data[idx1].freq - data[idx0].freq
    return 0 if delta_freq == 0 else -delta_angle / math.tau / delta_freq


def impedance_to_capacitance(z: complex, freq: float) -> float:
    """Calculate capacitive equivalent for reactance"""
    if freq == 0:
        return -math.inf
    return math.inf if z.imag == 0 else -(1 / (freq * 2 * math.pi * z.imag))


def impedance_to_inductance(z: complex, freq: float) -> float:
    """Calculate inductive equivalent for reactance"""
    return 0 if freq == 0 else z.imag * 1 / (freq * 2 * math.pi)


def impedance_to_norm(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate normalized z from impedance"""
    return z / ref_impedance


def norm_to_impedance(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate impedance from normalized z"""
    return z * ref_impedance


def parallel_to_serial(z: complex) -> complex:
    """Convert parallel impedance to serial impedance equivalent"""
    z_sq_sum = z.real**2 + z.imag**2 or 10.0e-30
    return complex(z.real * z.imag**2 / z_sq_sum, z.real**2 * z.imag / z_sq_sum)


def reflection_coefficient(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate reflection coefficient for z"""
    return (z - ref_impedance) / (z + ref_impedance)


def serial_to_parallel(z: complex) -> complex:
    """Convert serial impedance to parallel impedance equivalent"""
    z_sq_sum = z.real**2 + z.imag**2
    if z.real == 0 and z.imag == 0:
        return complex(math.inf, math.inf)
    if z.imag == 0:
        return complex(z_sq_sum / z.real, math.copysign(math.inf, z_sq_sum))
    if z.real == 0:
        return complex(math.copysign(math.inf, z_sq_sum), z_sq_sum / z.imag)
    return complex(z_sq_sum / z.real, z_sq_sum / z.imag)


def corr_att_data(data: list[Datapoint], att: float) -> list[Datapoint]:
    """Correct the ratio for a given attenuation on s21 input"""
    if att <= 0:
        return data
    att = 10 ** (att / 20)
    ndata = []
    for dp in data:
        corrected = dp.z * att
        ndata.append(Datapoint(dp.freq, corrected.real, corrected.imag))
    return ndata
