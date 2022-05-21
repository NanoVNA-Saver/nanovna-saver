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
import math
import cmath
from typing import List, NamedTuple

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
        """ return the s value complex number """
        return complex(self.re, self.im)

    @property
    def phase(self) -> float:
        """ return the datapoint's phase value """
        return cmath.phase(self.z)

    @property
    def gain(self) -> float:
        mag = abs(self.z)
        if mag > 0:
            return 20 * math.log10(mag)
        return -math.inf

    @property
    def vswr(self) -> float:
        mag = abs(self.z)
        if mag >= 1:
            return math.inf
        return (1 + mag) / (1 - mag)

    @property
    def wavelength(self) -> float:
        return 299792458 / self.freq

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
        if imp.real == 0.0:
            return -1
        return abs(imp.imag / imp.real)

    def capacitiveEquivalent(self, ref_impedance: float = 50) -> float:
        return impedance_to_capacitance(self.impedance(ref_impedance), self.freq)

    def inductiveEquivalent(self, ref_impedance: float = 50) -> float:
        return impedance_to_inductance(self.impedance(ref_impedance), self.freq)


def gamma_to_impedance(gamma: complex, ref_impedance: float = 50) -> complex:
    """Calculate impedance from gamma"""
    try:
        return ((-gamma - 1) / (gamma - 1)) * ref_impedance
    except ZeroDivisionError:
        return math.inf


def groupDelay(data: List[Datapoint], index: int) -> float:
    idx0 = clamp_value(index - 1, 0, len(data) - 1)
    idx1 = clamp_value(index + 1, 0, len(data) - 1)
    delta_angle = data[idx1].phase - data[idx0].phase
    delta_freq = data[idx1].freq - data[idx0].freq
    if delta_freq == 0:
        return 0
    return -delta_angle / math.tau / delta_freq


def impedance_to_capacitance(z: complex, freq: float) -> float:
    """Calculate capacitive equivalent for reactance"""
    if freq == 0:
        return -math.inf
    if z.imag == 0:
        return math.inf
    return -(1 / (freq * 2 * math.pi * z.imag))


def impedance_to_inductance(z: complex, freq: float) -> float:
    """Calculate inductive equivalent for reactance"""
    if freq == 0:
        return 0
    return z.imag * 1 / (freq * 2 * math.pi)


def impedance_to_norm(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate normalized z from impedance"""
    return z / ref_impedance


def norm_to_impedance(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate impedance from normalized z"""
    return z * ref_impedance


def parallel_to_serial(z: complex) -> complex:
    """Convert parallel impedance to serial impedance equivalent"""
    z_sq_sum = z.real ** 2 + z.imag ** 2
    # TODO: Fix divide by zero
    return complex(z.real * z.imag ** 2 / z_sq_sum,
                   z.real ** 2 * z.imag / z_sq_sum)


def reflection_coefficient(z: complex, ref_impedance: float = 50) -> complex:
    """Calculate reflection coefficient for z"""
    return (z - ref_impedance) / (z + ref_impedance)


def serial_to_parallel(z: complex) -> complex:
    """Convert serial impedance to parallel impedance equivalent"""
    z_sq_sum = z.real ** 2 + z.imag ** 2
    if z.real == 0 and z.imag == 0:
        return complex(math.inf, math.inf)
    # only possible if real and imag == 0, therefor commented out
    # if z_sq_sum == 0:
    #     return complex(0, 0)
    if z.imag == 0:
        return complex(z_sq_sum / z.real, math.copysign(math.inf, z_sq_sum))
    if z.real == 0:
        return complex(math.copysign(math.inf, z_sq_sum), z_sq_sum / z.imag)
    return complex(z_sq_sum / z.real, z_sq_sum / z.imag)


def corr_att_data(data: List[Datapoint], att: float) -> List[Datapoint]:
    """Correct the ratio for a given attenuation on s21 input"""
    if att <= 0:
        return data
    att = 10**(att / 20)
    ndata = []
    for dp in data:
        corrected = dp.z * att
        ndata.append(Datapoint(dp.freq, corrected.real, corrected.imag))
    return ndata

def match_calc_string_value_with_prefix(val,unit):
    buf = ""
    prefix = ""
    if val < 0:
        val = -val
        buf = '-'
    if val < 1e-12:
        prefix = 'f'
        val *= 1e15
    elif val < 1e-9:
        prefix = 'p'
        val *= 1e12
    elif val < 1e-6:
        prefix = 'n'
        val *= 1e9
    elif val < 1e-3:
        prefix = 'µ'
        val *= 1e6
    elif val < 1:
        prefix = 'm'
        val *= 1e3
    elif val < 1e3:
        prefix = 0
    elif val < 1e6:
        prefix = 'k'
        val /= 1e3
    elif val < 1e9:
        prefix = 'M'
        val /= 1e6
    else:
        prefix = 'G'
        val /= 1e9

    if val < 10:
        buf = buf + "%.2f"%val
    elif val < 100:
        buf = buf + "%.1f"%val
    else :
        buf = buf + "%d"%int(val)

    if prefix!="":
        buf = buf + " %s"%prefix
    if unit!="":
        buf = buf+unit
    return buf

def match_calc_ComponentString (freq, X):
    if math.isnan(X) or X==0:
        return ""
    if X < 0:
        X = -1.0 / X; 
        type = 'F'
    else:
        type = 'H'
    val = X / (2 * math.pi * freq)
    return match_calc_string_value_with_prefix(val,type)

def match_calc_swr(re, im) :
	x = math.sqrt(re*re + im*im)
	if x > 1:
		return float('inf')
	return (1 + x)/(1 - x)

def match_calc_lc_match_quadratic_equation(a, b, c):
    x = [0.0, 0.0]
    d = (b * b) - (4.0 * a * c)
    if d < 0:
        x[0] = x[1] = 0.0
        return x
    sd = math.sqrt(d)
    a2 = 2.0 * a
    x[0] = (-b + sd) / a2
    x[1] = (-b - sd) / a2
    return x

def match_calc_lc_match_calc_hi(R0, RL, XL):

    a = R0 - RL
    b = 2.0 * XL * R0
    c = R0 * ((XL * XL) + (RL * RL))
    xp=match_calc_lc_match_quadratic_equation(a, b, c)

    RL1 = -XL * xp[0]
    XL1 =  RL * xp[0]
    RL2 =  RL + 0.0
    XL2 =  XL + xp[0]
    xs1  = ((RL1 * XL2) - (RL2 * XL1)) / ((RL2 * RL2) + (XL2 * XL2));
    xps1 = 0.0
    xpl1 = xp[0]

    RL3 = -XL * xp[1]
    XL3 =  RL * xp[1]
    RL4 =  RL + 0.0
    XL4 =  XL + xp[1]
    xs2  = ((RL3 * XL4) - (RL4 * XL3)) / ((RL4 * RL4) + (XL4 * XL4))
    xps2 = 0.0
    xpl2 = xp[1]
    return [(xpl1, xs1, xps1), (xpl2, xs2, xps2)]

def match_calc_lc_match_calc_lo(R0, RL, XL):

    a = 1.0
    b = 2.0 * XL
    c = (RL * RL) + (XL * XL) - (R0 * RL)
    xs=match_calc_lc_match_quadratic_equation(a, b, c)

    RL1 = RL  + 0.0
    XL1 = XL  + xs[0]
    RL3 = RL1 * R0
    XL3 = XL1 * R0
    RL5 = RL1 - R0
    XL5 = XL1 - 0.0
    xs1  = xs[0]
    xps1 = ((RL5 * XL3) - (RL3 * XL5)) / ((RL5 * RL5) + (XL5 * XL5))
    xpl1 = 0.0

    RL2 = RL  + 0.0
    XL2 = XL  + xs[1]
    RL4 = RL2 * R0
    XL4 = XL2 * R0
    RL6 = RL2 - R0
    XL6 = XL2 - 0.0
    xs2  = xs[1]
    xps2 = ((RL6 * XL4) - (RL4 * XL6)) / ((RL6 * RL6) + (XL6 * XL6))
    xpl2 = 0.0
    return [(xpl1, xs1, xps1), (xpl2, xs2, xps2)]


def match_calc_lc_match_calc(RL, XL):

    R0 = 50
    if RL < 0.5 :
        return [(-1, -1, -1)]

    q_factor = XL / RL
    vswr = match_calc_swr(RL,XL)
    if vswr <= 1.1 or q_factor >= 100 :
        return [(0,0,0)]

    if (RL * 1.1) > R0  and RL < (R0 * 1.1):
        return [(0, -XL, 0)]

    if RL >= R0:
        return match_calc_lc_match_calc_hi(R0, RL, XL)

    x1=match_calc_lc_match_calc_lo(R0, RL, XL)
    if (RL + (XL * q_factor)) <= R0:
        return x1

    return x1 + match_calc_lc_match_calc_hi(R0, RL, XL)

def match_calc_ConcatenateResults(freq, sol):
    txt = ''
    i=0
    for s in sol:
        i = i+1
        xpl, xs, xps = s
        txt = txt + "ZLSh=%s\r\n"%match_calc_ComponentString (freq, xpl)
        txt = txt + "ZSer=%s\r\n"%match_calc_ComponentString (freq, xs)
        if i==len(sol):
            txt = txt + "ZSSh=%s"%match_calc_ComponentString (freq, xps)
        else:
            txt = txt + "ZSSh=%s\r\n\r\n"%match_calc_ComponentString (freq, xps)
    return txt