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
"""Fixture removal: port extension, S2P de-embedding and reference
impedance renormalisation."""

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import numpy.typing as npt

from .sweepdata import SweepData

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]
SMatrix = npt.NDArray[np.complex128]  # shape (n, 2, 2)

LOSS_REF_FREQ = 1e9


@dataclass
class PortExtension:
    """Electrical delay and loss of a cable / fixture in front of a port.

    delay: one way delay in seconds (positive removes a cable)
    loss_db: one way loss in dB at 1 GHz, scaled with sqrt(f) (skin effect)
    """

    delay: float = 0.0
    loss_db: float = 0.0

    @property
    def active(self) -> bool:
        return self.delay != 0.0 or self.loss_db != 0.0

    def factor(self, freq: FloatArray) -> ComplexArray:
        """One way correction factor (multiply to remove the extension)"""
        freq = np.asarray(freq, dtype=np.float64)
        loss = self.loss_db * np.sqrt(np.abs(freq) / LOSS_REF_FREQ)
        return 10 ** (loss / 20) * np.exp(2j * math.pi * freq * self.delay)


@dataclass
class FixtureSettings:
    """Everything that sits between the calibration plane and the DUT"""

    port1: PortExtension = field(default_factory=PortExtension)
    port2: PortExtension = field(default_factory=PortExtension)
    fixture1: Optional[SweepData] = None  # 2-port at port 1 (VNA -> DUT)
    fixture2: Optional[SweepData] = None  # 2-port at port 2 (DUT -> VNA)
    z0: complex = 50.0

    @property
    def active(self) -> bool:
        return (
            self.port1.active
            or self.port2.active
            or self.fixture1 is not None
            or self.fixture2 is not None
            or self.z0 != 50.0
        )

    def apply(self, data: SweepData) -> SweepData:
        return apply_fixture(data, self)


def apply_port_extension(
    data: SweepData, port1: PortExtension, port2: PortExtension
) -> SweepData:
    out = data.copy()
    f1 = port1.factor(data.freq)
    f2 = port2.factor(data.freq)
    out.s11 = data.s11 * f1 * f1
    out.s21 = data.s21 * f1 * f2
    if data.s12 is not None:
        out.s12 = data.s12 * f1 * f2
    if data.s22 is not None:
        out.s22 = data.s22 * f2 * f2
    return out


def auto_port_extension(
    freq: FloatArray, s11: ComplexArray, standard: str = "open"
) -> PortExtension:
    """Fit delay and loss of a port extension from a measured open or
    short at the end of the fixture. The fitted values make the standard
    look ideal (flat phase, 0 dB)."""
    freq = np.asarray(freq, dtype=np.float64)
    s11 = np.asarray(s11, dtype=np.complex128)
    if len(freq) < 2:
        return PortExtension()
    if standard == "short":
        s11 = -s11
    phase = np.unwrap(np.angle(s11))
    # phase = -4 pi f tau (+ k*2pi). Fit slope with offset.
    slope, _ = np.polyfit(freq, phase, 1)
    delay = -slope / (4 * math.pi)
    # |G| dB = -2 * L0 * sqrt(f / 1GHz) -> least squares through origin
    x = np.sqrt(freq / LOSS_REF_FREQ)
    y = 20 * np.log10(np.maximum(np.abs(s11), 1e-12))
    denom = float(np.sum(x * x))
    loss = -float(np.sum(x * y)) / (2 * denom) if denom > 0 else 0.0
    return PortExtension(delay=float(delay), loss_db=max(loss, 0.0))


# Conversions between S and T parameters (n, 2, 2)


def s2t(s: SMatrix) -> SMatrix:
    s11, s12, s21, s22 = s[:, 0, 0], s[:, 0, 1], s[:, 1, 0], s[:, 1, 1]
    t = np.empty_like(s)
    t[:, 0, 0] = -(s11 * s22 - s12 * s21) / s21
    t[:, 0, 1] = s11 / s21
    t[:, 1, 0] = -s22 / s21
    t[:, 1, 1] = 1 / s21
    return t


def t2s(t: SMatrix) -> SMatrix:
    t11, t12, t21, t22 = t[:, 0, 0], t[:, 0, 1], t[:, 1, 0], t[:, 1, 1]
    s = np.empty_like(t)
    s[:, 0, 0] = t12 / t22
    s[:, 0, 1] = (t11 * t22 - t12 * t21) / t22
    s[:, 1, 0] = 1 / t22
    s[:, 1, 1] = -t21 / t22
    return s


def cascade(*networks: SMatrix) -> SMatrix:
    t = s2t(networks[0])
    for net in networks[1:]:
        t = t @ s2t(net)
    return t2s(t)


def _fixture_matrix(fixture: SweepData, freq: FloatArray) -> SMatrix:
    """Fixture S matrix interpolated to the measurement frequencies"""
    s = fixture.s_matrix()
    out = np.empty((len(freq), 2, 2), dtype=np.complex128)
    for i in range(2):
        for j in range(2):
            v = s[:, i, j]
            out[:, i, j] = np.interp(freq, fixture.freq, v.real) + 1j * (
                np.interp(freq, fixture.freq, v.imag)
            )
    return out


def deembed_one_port(s11m: ComplexArray, fixture: SMatrix) -> ComplexArray:
    """Remove a 2-port fixture (port 1 at the VNA) from a reflection"""
    f11, f12 = fixture[:, 0, 0], fixture[:, 0, 1]
    f21, f22 = fixture[:, 1, 0], fixture[:, 1, 1]
    d = s11m - f11
    return d / (f12 * f21 + f22 * d)


def deembed_two_port(
    measured: SMatrix,
    fixture1: Optional[SMatrix] = None,
    fixture2: Optional[SMatrix] = None,
) -> SMatrix:
    """T_dut = inv(T_fix1) T_meas inv(T_fix2). fixture2 is oriented with
    port 1 towards the DUT and port 2 towards the VNA port 2."""
    t = s2t(measured)
    if fixture1 is not None:
        t = np.linalg.inv(s2t(fixture1)) @ t
    if fixture2 is not None:
        t = t @ np.linalg.inv(s2t(fixture2))
    return t2s(t)


def renormalize_one_port(
    gamma: ComplexArray, z0_old: complex, z0_new: complex
) -> ComplexArray:
    """Power wave renormalisation of a reflection coefficient"""
    gamma = np.asarray(gamma, dtype=np.complex128)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = z0_old * (1 + gamma) / (1 - gamma)
        return (z - np.conj(z0_new)) / (z + z0_new)


def renormalize_two_port(
    s: SMatrix, z0_old: complex, z0_new: complex
) -> SMatrix:
    """Power wave renormalisation of a 2-port S matrix. z0_old must be
    real (VNA reference), z0_new may be complex."""
    eye = np.eye(2, dtype=np.complex128)
    z = z0_old * (eye + s) @ np.linalg.inv(eye - s)
    g = np.diag([z0_new, z0_new]).astype(np.complex128)
    f = np.diag([1 / (2 * math.sqrt(abs(np.real(z0_new))))] * 2).astype(
        np.complex128
    )
    return f @ (z - np.conj(g)) @ np.linalg.inv(z + g) @ np.linalg.inv(f)


def apply_fixture(data: SweepData, settings: FixtureSettings) -> SweepData:
    """Apply port extension, de-embedding and Z0 renormalisation"""
    if not settings.active or len(data) == 0:
        return data
    out = apply_port_extension(data, settings.port1, settings.port2)
    freq = out.freq
    f1 = (
        _fixture_matrix(settings.fixture1, freq)
        if settings.fixture1 is not None
        else None
    )
    f2 = (
        _fixture_matrix(settings.fixture2, freq)
        if settings.fixture2 is not None
        else None
    )
    if out.is_full_two_port and (f1 is not None or f2 is not None):
        s = deembed_two_port(out.s_matrix(), f1, f2)
        out = SweepData.from_s_matrix(freq, s, out.z0)
    elif f1 is not None:
        # forward only: S11 de-embedded exactly, S21 approximately
        # (ignores mismatch between fixture 2 and DUT)
        out.s11 = deembed_one_port(out.s11, f1)
        out.s21 = out.s21 / f1[:, 1, 0]
        if f2 is not None:
            out.s21 = out.s21 / f2[:, 1, 0]
    elif f2 is not None:
        out.s21 = out.s21 / f2[:, 1, 0]
    if settings.z0 != out.z0:
        if out.is_full_two_port:
            s = renormalize_two_port(out.s_matrix(), out.z0, settings.z0)
            out = SweepData.from_s_matrix(freq, s, out.z0)
        else:
            out.s11 = renormalize_one_port(out.s11, out.z0, settings.z0)
        out.z0 = float(np.real(settings.z0))
    return out
