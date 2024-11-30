#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
from PyQt6 import QtCore

from NanoVNASaver import RFTools
from NanoVNASaver.Formatting import (
    format_capacitance,
    format_complex_adm,
    format_complex_imp,
    format_frequency_space,
    format_gain,
    format_group_delay,
    format_inductance,
    format_magnitude,
    format_phase,
    format_q_factor,
    format_resistance,
    format_vswr,
    format_wavelength,
)
from NanoVNASaver.Marker.Widget import Marker


class DeltaMarker(Marker):
    def __init__(self, name: str = "", qsettings: QtCore.QSettings = None):
        super().__init__(name, qsettings)
        self.marker_a = None
        self.marker_b = None

    def set_markers(self, marker_a: Marker, marker_b: Marker):
        self.marker_a = marker_a
        self.marker_b = marker_b
        self.name = f"Delta {marker_b.name} - {marker_a.name}"
        self.group_box.setTitle(self.name)

    def updateLabels(self):  # pylint: disable=arguments-differ
        a = self.marker_a
        b = self.marker_b
        s11_a = a.s11[1]
        s11_b = b.s11[1]

        imp_a = s11_a.impedance()
        imp_b = s11_b.impedance()
        imp = imp_b - imp_a

        cap_str = format_capacitance(
            RFTools.impedance_to_capacitance(imp_b, s11_b.freq)
            - RFTools.impedance_to_capacitance(imp_a, s11_a.freq)
        )
        ind_str = format_inductance(
            RFTools.impedance_to_inductance(imp_b, s11_b.freq)
            - RFTools.impedance_to_inductance(imp_a, s11_a.freq)
        )

        imp_p_a = RFTools.serial_to_parallel(imp_a)
        imp_p_b = RFTools.serial_to_parallel(imp_b)
        imp_p = imp_p_b - imp_p_a

        cap_p_str = format_capacitance(
            RFTools.impedance_to_capacitance(imp_p_b, s11_b.freq)
            - RFTools.impedance_to_capacitance(imp_p_a, s11_a.freq)
        )
        ind_p_str = format_inductance(
            RFTools.impedance_to_inductance(imp_p_b, s11_b.freq)
            - RFTools.impedance_to_inductance(imp_p_a, s11_a.freq)
        )

        x_str = cap_str if imp.imag < 0 else ind_str
        x_p_str = cap_p_str if imp_p.imag < 0 else ind_p_str

        self.label["actualfreq"].setText(
            format_frequency_space(s11_b.freq - s11_a.freq)
        )
        self.label["lambda"].setText(
            format_wavelength(s11_b.wavelength - s11_a.wavelength)
        )
        self.label["admittance"].setText(format_complex_adm(imp_p, True))
        self.label["impedance"].setText(format_complex_imp(imp, True))

        self.label["parc"].setText(cap_p_str)
        self.label["parl"].setText(ind_p_str)
        self.label["parlc"].setText(x_p_str)

        self.label["parr"].setText(format_resistance(imp_p.real, True))
        self.label["returnloss"].setText(
            format_gain(s11_b.gain - s11_a.gain, self.returnloss_is_positive)
        )
        self.label["s11groupdelay"].setText(
            format_group_delay(
                RFTools.groupDelay(b.s11, 1) - RFTools.groupDelay(a.s11, 1)
            )
        )

        self.label["s11mag"].setText(
            format_magnitude(abs(s11_b.z) - abs(s11_a.z))
        )
        self.label["s11phase"].setText(format_phase(s11_b.phase - s11_a.phase))
        self.label["s11polar"].setText(
            f"{round(abs(s11_b.z) - abs(s11_a.z), 2)}∠"
            f"{format_phase(s11_b.phase - s11_a.phase)}"
        )
        self.label["s11q"].setText(
            format_q_factor(s11_b.qFactor() - s11_a.qFactor(), True)
        )
        self.label["s11z"].setText(format_resistance(abs(imp)))
        self.label["serc"].setText(cap_str)
        self.label["serl"].setText(ind_str)
        self.label["serlc"].setText(x_str)
        self.label["serr"].setText(format_resistance(imp.real, True))
        self.label["vswr"].setText(format_vswr(s11_b.vswr - s11_a.vswr))

        if len(a.s21) == len(a.s11):
            s21_a = a.s21[1]
            s21_b = b.s21[1]
            self.label["s21gain"].setText(format_gain(s21_b.gain - s21_a.gain))
            self.label["s21groupdelay"].setText(
                format_group_delay(
                    (
                        RFTools.groupDelay(b.s21, 1)
                        - RFTools.groupDelay(a.s21, 1)
                    )
                    / 2
                )
            )
            self.label["s21mag"].setText(
                format_magnitude(abs(s21_b.z) - abs(s21_a.z))
            )
            self.label["s21phase"].setText(
                format_phase(s21_b.phase - s21_a.phase)
            )
            self.label["s21polar"].setText(
                f"{round(abs(s21_b.z) - abs(s21_a.z), 2)}∠"
                f"{format_phase(s21_b.phase - s21_a.phase)}"
            )
