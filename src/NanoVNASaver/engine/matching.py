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
"""Lossless L-network matching (Pozar, Microwave Engineering 5.1)."""

import math
from dataclasses import dataclass


@dataclass
class Component:
    kind: str  # "L" or "C"
    value: float  # H or F
    reactance: float  # Ohm at design frequency

    def __str__(self) -> str:
        unit = "H" if self.kind == "L" else "F"
        return f"{self.kind} = {_eng(self.value)}{unit}"


@dataclass
class LNetwork:
    """topology:
    "shunt-series": shunt element at the load, series element towards
                    the source
    "series-shunt": series element at the load, shunt element at the
                    source side"""

    topology: str
    series: Component
    shunt: Component

    def describe(self) -> str:
        if self.topology == "shunt-series":
            return (
                f"Source ── series {self.series} ──┬── Load\n"
                f"                          shunt {self.shunt}"
            )
        return (
            f"Source ──┬── series {self.series} ── Load\n  shunt {self.shunt}"
        )


def _eng(value: float) -> str:
    if value == 0 or not math.isfinite(value):
        return f"{value:g} "
    exp = int(math.floor(math.log10(abs(value)) / 3) * 3)
    exp = max(min(exp, 12), -15)
    prefixes = {
        -15: "f",
        -12: "p",
        -9: "n",
        -6: "µ",
        -3: "m",
        0: "",
        3: "k",
        6: "M",
        9: "G",
        12: "T",
    }
    return f"{value / 10**exp:.4g} {prefixes[exp]}"


def _series(x: float, freq: float) -> Component:
    omega = 2 * math.pi * freq
    if x >= 0:
        return Component("L", x / omega, x)
    return Component("C", -1 / (omega * x), x)


def _shunt(b: float, freq: float) -> Component:
    """Shunt element from susceptance B"""
    omega = 2 * math.pi * freq
    if b >= 0:
        return Component("C", b / omega, -1 / b if b else math.inf)
    return Component("L", -1 / (omega * b), -1 / b)


def l_networks(zl: complex, freq: float, z0: float = 50.0) -> list[LNetwork]:
    """All L-network solutions matching load zl to z0 at freq"""
    rl, xl = zl.real, zl.imag
    if rl <= 0 or freq <= 0:
        return []
    solutions: list[LNetwork] = []
    if rl >= z0:
        # shunt element next to the load
        root = math.sqrt(rl / z0) * math.sqrt(rl**2 + xl**2 - z0 * rl)
        for sign in (1, -1):
            b = (xl + sign * root) / (rl**2 + xl**2)
            if b == 0:
                continue
            x = 1 / b + xl * z0 / rl - z0 / (b * rl)
            solutions.append(
                LNetwork("shunt-series", _series(x, freq), _shunt(b, freq))
            )
    if rl < z0 or not solutions:
        # series element next to the load
        root = math.sqrt(max(rl * (z0 - rl), 0.0))
        for sign in (1, -1):
            x = sign * root - xl
            b = sign * math.sqrt(max((z0 - rl) / rl, 0.0)) / z0
            if b == 0:
                continue
            solutions.append(
                LNetwork("series-shunt", _series(x, freq), _shunt(b, freq))
            )
    return solutions


def input_impedance(net: LNetwork, zl: complex) -> complex:
    """Impedance seen from the source (used for verification)"""
    jx = 1j * net.series.reactance
    yb = 1 / (1j * net.shunt.reactance)  # shunt admittance jB
    if net.topology == "shunt-series":
        z = 1 / (1 / zl + yb)
        return z + jx
    z = zl + jx
    return 1 / (1 / z + yb)
