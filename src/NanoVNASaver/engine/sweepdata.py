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
"""Array based container for one sweep (up to a full 2-port S matrix)."""

from dataclasses import dataclass, field, replace
from typing import Optional

import numpy as np
import numpy.typing as npt

from ..RFTools import Datapoint
from ..Touchstone import Touchstone

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]

PARAMS = ("s11", "s21", "s12", "s22")


def to_complex(data: list[Datapoint]) -> ComplexArray:
    return np.array([complex(d.re, d.im) for d in data], dtype=np.complex128)


def to_freq(data: list[Datapoint]) -> FloatArray:
    return np.array([d.freq for d in data], dtype=np.float64)


def to_datapoints(freq: FloatArray, values: ComplexArray) -> list[Datapoint]:
    return [
        Datapoint(int(f), re, im)
        for f, re, im in zip(
            freq.tolist(),
            values.real.tolist(),
            values.imag.tolist(),
            strict=True,
        )
    ]


@dataclass
class SweepData:
    """One sweep. s12 / s22 are only present after a full 2-port
    measurement (forward + reverse)."""

    freq: FloatArray = field(default_factory=lambda: np.zeros(0))
    s11: ComplexArray = field(
        default_factory=lambda: np.zeros(0, dtype=np.complex128)
    )
    s21: ComplexArray = field(
        default_factory=lambda: np.zeros(0, dtype=np.complex128)
    )
    s12: Optional[ComplexArray] = None
    s22: Optional[ComplexArray] = None
    z0: float = 50.0

    def __len__(self) -> int:
        return len(self.freq)

    @property
    def is_full_two_port(self) -> bool:
        return self.s12 is not None and self.s22 is not None

    def param(self, name: str) -> Optional[ComplexArray]:
        if name not in PARAMS:
            raise KeyError(name)
        return getattr(self, name)

    def copy(self) -> "SweepData":
        return replace(
            self,
            freq=self.freq.copy(),
            s11=self.s11.copy(),
            s21=self.s21.copy(),
            s12=None if self.s12 is None else self.s12.copy(),
            s22=None if self.s22 is None else self.s22.copy(),
        )

    def s_matrix(self) -> npt.NDArray[np.complex128]:
        """(n, 2, 2) S matrix. Missing reverse data is taken from the
        forward data assuming a reciprocal, symmetric DUT."""
        n = len(self.freq)
        s = np.empty((n, 2, 2), dtype=np.complex128)
        s[:, 0, 0] = self.s11
        s[:, 1, 0] = self.s21
        s[:, 0, 1] = self.s12 if self.s12 is not None else self.s21
        s[:, 1, 1] = self.s22 if self.s22 is not None else self.s11
        return s

    @classmethod
    def from_s_matrix(
        cls, freq: FloatArray, s: npt.NDArray[np.complex128], z0: float = 50.0
    ) -> "SweepData":
        return cls(
            freq=np.asarray(freq, dtype=np.float64),
            s11=s[:, 0, 0].copy(),
            s21=s[:, 1, 0].copy(),
            s12=s[:, 0, 1].copy(),
            s22=s[:, 1, 1].copy(),
            z0=z0,
        )

    @classmethod
    def from_datapoints(
        cls,
        s11: list[Datapoint],
        s21: Optional[list[Datapoint]] = None,
        s12: Optional[list[Datapoint]] = None,
        s22: Optional[list[Datapoint]] = None,
    ) -> "SweepData":
        freq = to_freq(s11)
        n = len(freq)

        def opt(data: Optional[list[Datapoint]]) -> Optional[ComplexArray]:
            if not data or len(data) != n:
                return None
            return to_complex(data)

        s21_arr = opt(s21)
        return cls(
            freq=freq,
            s11=to_complex(s11),
            s21=(
                s21_arr
                if s21_arr is not None
                else np.zeros(n, dtype=np.complex128)
            ),
            s12=opt(s12),
            s22=opt(s22),
        )

    @classmethod
    def from_touchstone(cls, ts: Touchstone) -> "SweepData":
        data = cls.from_datapoints(ts.s11, ts.s21, ts.s12, ts.s22)
        data.z0 = float(ts.r)
        return data

    @classmethod
    def load(cls, filename: str) -> "SweepData":
        ts = Touchstone(filename)
        ts.load()
        if not ts.s11:
            raise ValueError(f"No data in {filename}")
        return cls.from_touchstone(ts)

    def datapoints(self, name: str) -> list[Datapoint]:
        values = self.param(name)
        if values is None:
            return []
        return to_datapoints(self.freq, values)

    def to_touchstone(self, filename: str = "") -> Touchstone:
        ts = Touchstone(filename)
        ts.opts.resistance = round(self.z0)
        ts.sdata[0] = self.datapoints("s11")
        ts.sdata[1] = self.datapoints("s21")
        ts.sdata[2] = self.datapoints("s12")
        ts.sdata[3] = self.datapoints("s22")
        return ts

    def save(self, filename: str) -> None:
        """Save as .s1p or .s2p depending on the file extension.
        A .s2p file of a forward only sweep gets zero reverse data."""
        ts = self.to_touchstone(filename)
        if filename.lower().endswith(".s1p"):
            ts.save(1)
            return
        if not ts.sdata[2]:
            ts.sdata[2] = to_datapoints(self.freq, np.zeros_like(self.s11))
        if not ts.sdata[3]:
            ts.sdata[3] = to_datapoints(self.freq, np.zeros_like(self.s11))
        ts.save(4)
