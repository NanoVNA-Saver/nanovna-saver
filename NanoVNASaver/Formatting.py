#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
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
import math
from numbers import Number

from NanoVNASaver import SITools

FMT_FREQ = SITools.Format()
FMT_FREQ_SHORT = SITools.Format(max_nr_digits=4)
FMT_FREQ_SPACE = SITools.Format(space_str=" ")
FMT_FREQ_SWEEP = SITools.Format(max_nr_digits=9, allow_strip=True)
FMT_FREQ_INPUTS = SITools.Format(
    max_nr_digits=10, allow_strip=True,
    printable_min=0, unprintable_under="- ")
FMT_Q_FACTOR = SITools.Format(
    max_nr_digits=4, assume_infinity=False,
    min_offset=0, max_offset=0, allow_strip=True)
FMT_GROUP_DELAY = SITools.Format(max_nr_digits=5, space_str=" ")
FMT_REACT = SITools.Format(max_nr_digits=5, space_str=" ", allow_strip=True)
FMT_COMPLEX = SITools.Format(max_nr_digits=3, allow_strip=True,
                             printable_min=0, unprintable_under="- ")
FMT_PARSE = SITools.Format(parse_sloppy_unit=True, parse_sloppy_kilo=True,
                           parse_clamp_min=0)


def format_frequency(freq: Number) -> str:
    return str(SITools.Value(freq, "Hz", FMT_FREQ))


def format_frequency_inputs(freq: float) -> str:
    return str(SITools.Value(freq, "Hz", FMT_FREQ_INPUTS))


def format_frequency_short(freq: Number) -> str:
    return str(SITools.Value(freq, "Hz", FMT_FREQ_SHORT))


def format_frequency_space(freq: float, fmt=FMT_FREQ_SPACE) -> str:
    return str(SITools.Value(freq, "Hz", fmt))


def format_frequency_sweep(freq: Number) -> str:
    return str(SITools.Value(freq, "Hz", FMT_FREQ_SWEEP))


def format_gain(val: float, invert: bool = False) -> str:
    if invert:
        val = -val
    return f"{val:.3f} dB"


def format_q_factor(val: float) -> str:
    if val < 0 or val > 10000.0:
        return "\N{INFINITY}"
    return str(SITools.Value(val, fmt=FMT_Q_FACTOR))


def format_vswr(val: float) -> str:
    return f"{val:.3f}"


def format_magnitude(val: float) -> str:
    return f"{val:.3f}"


def format_resistance(val: float) -> str:
    if val < 0:
        return "- \N{OHM SIGN}"
    return str(SITools.Value(val, "\N{OHM SIGN}", FMT_REACT))


def format_capacitance(val: float, allow_negative: bool = True) -> str:
    if not allow_negative and val < 0:
        return "- pF"
    return str(SITools.Value(val, "F", FMT_REACT))


def format_inductance(val: float, allow_negative: bool = True) -> str:
    if not allow_negative and val < 0:
        return "- nH"
    return str(SITools.Value(val, "H", FMT_REACT))


def format_group_delay(val: float) -> str:
    return str(SITools.Value(val, "s", FMT_GROUP_DELAY))


def format_phase(val: float) -> str:
    return f"{math.degrees(val):.2f}\N{DEGREE SIGN}"


def format_complex_imp(z: complex) -> str:
    re = SITools.Value(z.real, fmt=FMT_COMPLEX)
    im = SITools.Value(abs(z.imag), fmt=FMT_COMPLEX)
    return f"{re}{'-' if z.imag < 0 else '+'}j{im} \N{OHM SIGN}"


def parse_frequency(freq: str) -> int:
    try:
        return int(SITools.Value(freq, "Hz", FMT_PARSE))
    except (ValueError, IndexError):
        return -1
