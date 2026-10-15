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
"""Time domain transforms and time gating."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]

SPEED_OF_LIGHT = 299_792_458.0

# Velocity factors of common cables
VELOCITY_FACTORS: dict[str, float] = {
    "Air / ideal": 1.0,
    "RG-58 / RG-213 (solid PE)": 0.66,
    "RG-58 foam / LMR-195": 0.80,
    "LMR-400": 0.85,
    "RG-316 / RG-178 (PTFE)": 0.695,
    "Semi rigid .141 (PTFE)": 0.70,
    "RG-6 foam": 0.82,
    "Ladder line": 0.95,
    "FR-4 microstrip (approx.)": 0.55,
}

WINDOWS = {
    "rectangular": lambda n: np.ones(n),
    "hann": np.hanning,
    "blackman": np.blackman,
    "kaiser6": lambda n: np.kaiser(n, 6),
    "kaiser13": lambda n: np.kaiser(n, 13),
}


def is_uniform(freq: FloatArray, rel_tol: float = 1e-3) -> bool:
    if len(freq) < 3:
        return True
    step = np.diff(freq)
    return bool(np.max(np.abs(step - step.mean())) <= rel_tol * step.mean())


def to_uniform(
    freq: FloatArray, values: ComplexArray
) -> tuple[FloatArray, ComplexArray]:
    """Resample onto a linear frequency grid (e.g. for log sweeps)"""
    if is_uniform(freq):
        return freq, values
    grid = np.linspace(freq[0], freq[-1], len(freq))
    return grid, np.interp(grid, freq, values.real) + 1j * np.interp(
        grid, freq, values.imag
    )


@dataclass
class TimeDomain:
    time: FloatArray  # round trip time in s
    distance: FloatArray  # one way distance in m (velocity factor applied)
    impulse: FloatArray  # real impulse response
    step: FloatArray  # step response (reflection coefficient)
    impedance: FloatArray  # step response as impedance

    def peak_distance(self) -> float:
        return float(self.distance[int(np.argmax(np.abs(self.impulse)))])


def transform(  # noqa: PLR0913
    freq: FloatArray,
    s11: ComplexArray,
    window: str = "kaiser6",
    n_fft: int = 4096,
    velocity_factor: float = 1.0,
    z0: float = 50.0,
) -> TimeDomain:
    """Low pass style transform of a reflection measurement.

    The data is mirrored (Hermitian) so the impulse response is real.
    Start frequency should be low compared to the span for good step
    response results."""
    freq, s11 = to_uniform(np.asarray(freq, float), np.asarray(s11, complex))
    n = len(s11)
    if n < 2:
        raise ValueError("Need at least 2 points for a time domain transform")
    # right half of a symmetric window: full weight at DC
    win = WINDOWS[window](2 * n)[n:]
    windowed = s11 * win
    n_fft = max(n_fft, 2 * n)
    raw = np.fft.irfft(windowed, n_fft)
    # area of the impulse is the DC reflection -> step response
    step = np.cumsum(raw)
    # scale peaks to reflection coefficient for display
    impulse = raw * n_fft / (2 * np.sum(win))
    df = (freq[-1] - freq[0]) / (n - 1)
    time = np.arange(n_fft) / (n_fft * df)
    clipped = np.clip(step, -0.999999, 0.999999)
    impedance = z0 * (1 + clipped) / (1 - clipped)
    half = n_fft // 2
    distance = time * SPEED_OF_LIGHT * velocity_factor / 2
    return TimeDomain(
        time=time[:half],
        distance=distance[:half],
        impulse=impulse[:half],
        step=step[:half],
        impedance=impedance[:half],
    )


def _gate_shape(
    t: FloatArray, start: float, stop: float, edge: float
) -> FloatArray:
    """Band pass gate with raised cosine edges of width `edge`"""
    gate = np.zeros_like(t)
    inside = (t >= start) & (t <= stop)
    gate[inside] = 1.0
    if edge > 0:
        rise = (t >= start - edge) & (t < start)
        fall = (t > stop) & (t <= stop + edge)
        gate[rise] = 0.5 - 0.5 * np.cos(np.pi * (t[rise] - start + edge) / edge)
        gate[fall] = 0.5 + 0.5 * np.cos(np.pi * (t[fall] - stop) / edge)
    return gate


def time_gate(  # noqa: PLR0913
    freq: FloatArray,
    values: ComplexArray,
    start: float,
    stop: float,
    mode: str = "bandpass",
    edge: float | None = None,
) -> ComplexArray:
    """Time gate a frequency response.

    start/stop are round trip times in seconds. mode "bandpass" keeps the
    responses inside the gate, "notch" removes them. The result is on the
    original frequency points. A window is applied before the transform
    and removed afterwards to limit truncation ringing."""
    freq = np.asarray(freq, dtype=np.float64)
    values = np.asarray(values, dtype=np.complex128)
    ufreq, uvalues = to_uniform(freq, values)
    n = len(uvalues)
    if n < 4:
        return values.copy()
    df = (ufreq[-1] - ufreq[0]) / (n - 1)
    n_fft = 1 << int(np.ceil(np.log2(4 * n)))
    win = np.kaiser(n, 6)
    padded = np.zeros(n_fft, dtype=np.complex128)
    padded[:n] = uvalues * win
    td = np.fft.ifft(padded)
    t = np.arange(n_fft) / (n_fft * df)
    if edge is None:
        edge = 2.0 / (ufreq[-1] - ufreq[0])
    gate = _gate_shape(t, start, stop, edge)
    if mode == "notch":
        gate = 1 - gate
    gated = np.fft.fft(td * gate)[:n]
    # remove the window again (bounded to avoid blowing up the edges)
    gated = gated / np.maximum(win, 1e-3)
    if ufreq is freq:
        return gated
    return np.interp(freq, ufreq, gated.real) + 1j * np.interp(
        freq, ufreq, gated.imag
    )


def distance_to_time(distance: float, velocity_factor: float = 1.0) -> float:
    """Round trip time for a one way distance"""
    return 2 * distance / (SPEED_OF_LIGHT * velocity_factor)
