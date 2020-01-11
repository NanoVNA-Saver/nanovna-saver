#  NanoVNASaver
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019.  Rune B. Broberg
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
from typing import List

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver import RFTools
from NanoVNASaver.Formatting import format_frequency, format_capacitance, format_inductance, format_complex_imp, \
    format_resistance, format_vswr, format_phase, format_q_factor, format_gain, format_group_delay

from NanoVNASaver.Inputs import MarkerFrequencyInputWidget as FrequencyInput


class Marker(QtCore.QObject):
    name = "Marker"
    frequency = 0
    color: QtGui.QColor = QtGui.QColor()
    coloredText = True
    location = -1

    returnloss_is_positive = False

    updated = pyqtSignal(object)

    fieldSelection = []

    def __init__(self, name, initialColor, frequency=""):
        super().__init__()
        self.name = name

        self.frequency = RFTools.RFTools.parseFrequency(frequency)

        self.frequencyInput = FrequencyInput()
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.textEdited.connect(self.setFrequency)

        ################################################################################################################
        # Data display labels
        ################################################################################################################

        self.frequency_label = QtWidgets.QLabel("")
        self.frequency_label.setMinimumWidth(100)
        self.impedance_label = QtWidgets.QLabel("")
        self.admittance_label = QtWidgets.QLabel("")
        self.parallel_r_label = QtWidgets.QLabel("")
        self.parallel_x_label = QtWidgets.QLabel("")
        self.parallel_c_label = QtWidgets.QLabel("")
        self.parallel_l_label = QtWidgets.QLabel("")
        self.returnloss_label = QtWidgets.QLabel("")
        self.returnloss_label.setMinimumWidth(80)
        self.vswr_label = QtWidgets.QLabel("")
        self.series_r_label = QtWidgets.QLabel("")
        self.series_x_label = QtWidgets.QLabel("")
        self.inductance_label = QtWidgets.QLabel("")
        self.capacitance_label = QtWidgets.QLabel("")
        self.gain_label = QtWidgets.QLabel("")
        self.s11_phase_label = QtWidgets.QLabel("")
        self.s21_phase_label = QtWidgets.QLabel("")
        self.s11_group_delay_label = QtWidgets.QLabel("")
        self.s21_group_delay_label = QtWidgets.QLabel("")
        self.s11_polar_label = QtWidgets.QLabel("")
        self.s21_polar_label = QtWidgets.QLabel("")
        self.quality_factor_label = QtWidgets.QLabel("")

        self.fields = {
            "actualfreq": ("Frequency:", self.frequency_label),
            "impedance": ("Impedance:", self.impedance_label),
            "admittance": ("Admittance:", self.admittance_label),
            "s11polar": ("S11 Polar:", self.s11_polar_label),
            "s21polar": ("S21 Polar:", self.s21_polar_label),
            "serr": ("Series R:", self.series_r_label),
            "serl": ("Series L:", self.inductance_label),
            "serc": ("Series C:", self.capacitance_label),
            "serlc": ("Series X:", self.series_x_label),
            "parr": ("Parallel R:", self.parallel_r_label),
            "parc": ("Parallel C:", self.parallel_c_label),
            "parl": ("Parallel L:", self.parallel_l_label),
            "parlc": ("Parallel X:", self.parallel_x_label),
            "returnloss": ("Return loss:", self.returnloss_label),
            "vswr": ("VSWR:", self.vswr_label),
            "s11q": ("Quality factor:", self.quality_factor_label),
            "s11phase": ("S11 Phase:", self.s11_phase_label),
            "s11groupdelay": ("S11 Group Delay:", self.s11_group_delay_label),
            "s21gain": ("S21 Gain:", self.gain_label),
            "s21phase": ("S21 Phase:", self.s21_phase_label),
            "s21groupdelay": ("S21 Group Delay:", self.s21_group_delay_label),
        }

        ###############################################################
        # Marker control layout
        ###############################################################

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setFixedWidth(20)
        self.btnColorPicker.clicked.connect(
            lambda: self.setColor(QtWidgets.QColorDialog.getColor(
                self.color, options=QtWidgets.QColorDialog.ShowAlphaChannel))
        )
        self.isMouseControlledRadioButton = QtWidgets.QRadioButton()

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.frequencyInput)
        self.layout.addWidget(self.btnColorPicker)
        self.layout.addWidget(self.isMouseControlledRadioButton)

        ################################################################################################################
        # Data display layout
        ################################################################################################################

        self.group_box = QtWidgets.QGroupBox(self.name)
        self.group_box.setMaximumWidth(340)
        box_layout = QtWidgets.QHBoxLayout(self.group_box)

        self.setColor(initialColor)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)

        self.left_form = QtWidgets.QFormLayout()
        self.right_form = QtWidgets.QFormLayout()
        box_layout.addLayout(self.left_form)
        box_layout.addWidget(line)
        box_layout.addLayout(self.right_form)

        self.buildForm()

    def _size_str(self) -> str:
        return str(self.group_box.font().pointSize())

    def setScale(self, scale):
        self.group_box.setMaximumWidth(int(340 * scale))
        self.frequency_label.setMinimumWidth(int(100 * scale))
        self.returnloss_label.setMinimumWidth(int(80 * scale))
        if self.coloredText:
            color_string = QtCore.QVariant(self.color)
            color_string.convert(QtCore.QVariant.String)
            self.group_box.setStyleSheet(
                f"QGroupBox {{ color: {color_string.value()}; "
                f"font-size: {self._size_str()}}};"
            )
        else:
            self.group_box.setStyleSheet(
                f"QGroupBox {{ font-size: {self._size_str()}}};"
            )

    def buildForm(self):
        while self.left_form.count() > 0:
            old_row = self.left_form.takeRow(0)
            old_row.fieldItem.widget().hide()
            old_row.labelItem.widget().hide()

        while self.right_form.count() > 0:
            old_row = self.right_form.takeRow(0)
            old_row.fieldItem.widget().hide()
            old_row.labelItem.widget().hide()

        if len(self.fieldSelection) <= 3:
            for field in self.fieldSelection:
                if field in self.fields:
                    label, value = self.fields[field]
                    self.left_form.addRow(label, value)
                    value.show()
        else:
            left_half = math.ceil(len(self.fieldSelection)/2)
            right_half = len(self.fieldSelection)
            for i in range(left_half):
                field = self.fieldSelection[i]
                if field in self.fields:
                    label, value = self.fields[field]
                    self.left_form.addRow(label, value)
                    value.show()
            for i in range(left_half, right_half):
                field = self.fieldSelection[i]
                if field in self.fields:
                    label, value = self.fields[field]
                    self.right_form.addRow(label, value)
                    value.show()

    def setFrequency(self, frequency):
        self.frequency = RFTools.RFTools.parseFrequency(frequency)
        self.updated.emit(self)

    def setFieldSelection(self, fields):
        self.fieldSelection: List[str] = fields.copy()
        self.buildForm()

    def setColor(self, color):
        if color.isValid():
            self.color = color
            p = self.btnColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, self.color)
            self.btnColorPicker.setPalette(p)
        if self.coloredText:
            color_string = QtCore.QVariant(color)
            color_string.convert(QtCore.QVariant.String)
            self.group_box.setStyleSheet(
                f"QGroupBox {{ color: {color_string.value()}; "
                f"font-size: {self._size_str()}}};"
            )
        else:
            self.group_box.setStyleSheet(
                f"QGroupBox {{ font-size: {self._size_str()}}};"
            )

    def setColoredText(self, colored_text):
        self.coloredText = colored_text
        self.setColor(self.color)

    def getRow(self):
        return QtWidgets.QLabel(self.name), self.layout

    def findLocation(self, data: List[RFTools.Datapoint]):
        self.location = -1
        self.frequencyInput.nextFrequency = -1
        self.frequencyInput.previousFrequency = -1
        if self.frequency <= 0:
            # No frequency set for this marker
            return
        datasize = len(data)
        if datasize == 0:
            # Set the frequency before loading any data
            return

        min_freq = data[0].freq
        max_freq = data[-1].freq
        lower_stepsize = data[1].freq - data[0].freq
        upper_stepsize = data[-1].freq - data[-2].freq

        # We are outside the bounds of the data, so we can't put in a marker
        if self.frequency + lower_stepsize/2 < min_freq or self.frequency - upper_stepsize/2 > max_freq:
            return

        min_distance = max_freq
        for i, item in enumerate(data):
            if abs(item.freq - self.frequency) <= min_distance:
                min_distance = abs(item.freq - self.frequency)
            else:
                # We have now started moving away from the nearest point
                self.location = i-1
                if i < datasize:
                    self.frequencyInput.nextFrequency = item.freq
                if (i-2) >= 0:
                    self.frequencyInput.previousFrequency = data[i-2].freq
                return
        # If we still didn't find a best spot, it was the last value
        self.location = datasize - 1
        self.frequencyInput.previousFrequency = data[-2].freq

    def getGroupBox(self) -> QtWidgets.QGroupBox:
        return self.group_box

    def resetLabels(self):
        self.frequency_label.setText("")
        self.impedance_label.setText("")
        self.admittance_label.setText("")
        self.s11_polar_label.setText("")
        self.s21_polar_label.setText("")
        self.parallel_r_label.setText("")
        self.parallel_x_label.setText("")
        self.parallel_l_label.setText("")
        self.parallel_c_label.setText("")
        self.series_x_label.setText("")
        self.series_r_label.setText("")
        self.inductance_label.setText("")
        self.capacitance_label.setText("")
        self.vswr_label.setText("")
        self.returnloss_label.setText("")
        self.gain_label.setText("")
        self.s11_phase_label.setText("")
        self.s21_phase_label.setText("")
        self.s11_group_delay_label.setText("")
        self.s21_group_delay_label.setText("")
        self.quality_factor_label.setText("")

    def updateLabels(self,
                     s11data: List[RFTools.Datapoint],
                     s21data: List[RFTools.Datapoint]):
        if self.location == -1:
            return
        s11 = s11data[self.location]

        imp = s11.impedance()
        cap_str = format_capacitance(RFTools.impedance_to_capacitance(imp, s11.freq))
        ind_str = format_inductance(RFTools.impedance_to_inductance(imp, s11.freq))

        imp_p = RFTools.serial_to_parallel(imp)
        cap_p_str = format_capacitance(RFTools.impedance_to_capacitance(imp_p, s11.freq))
        ind_p_str = format_inductance(RFTools.impedance_to_inductance(imp_p, s11.freq))

        if imp.imag < 0:
            x_str = cap_str
        else:
            x_str = ind_str

        if imp_p.imag < 0:
            x_p_str = cap_p_str
        else:
            x_p_str = ind_p_str

        self.frequency_label.setText(format_frequency(s11.freq))

        self.impedance_label.setText(format_complex_imp(imp))
        self.series_r_label.setText(format_resistance(imp.real))
        self.series_x_label.setText(x_str)
        self.capacitance_label.setText(cap_str)
        self.inductance_label.setText(ind_str)

        self.admittance_label.setText(format_complex_imp(imp_p))
        self.parallel_r_label.setText(format_resistance(imp_p.real))
        self.parallel_x_label.setText(x_p_str)
        self.parallel_c_label.setText(cap_p_str)
        self.parallel_l_label.setText(ind_p_str)

        self.vswr_label.setText(format_vswr(s11.vswr))
        self.s11_phase_label.setText(format_phase(s11.phase))
        self.quality_factor_label.setText(format_q_factor(s11.qFactor()))

        self.returnloss_label.setText(format_gain(s11.gain, self.returnloss_is_positive))
        self.s11_group_delay_label.setText(format_group_delay(RFTools.groupDelay(s11data, self.location)))

        self.s11_polar_label.setText(str(round(abs(s11.z), 2)) + "∠" + format_phase(s11.phase))

        if len(s21data) == len(s11data):

            s21 = s21data[self.location]

            self.s21_phase_label.setText(format_phase(s21.phase))
            self.gain_label.setText(format_gain(s21.gain))
            self.s21_group_delay_label.setText(format_group_delay(RFTools.groupDelay(s21data, self.location) / 2))
            self.s21_polar_label.setText(str(round(abs(s21.z), 2)) + "∠" + format_phase(s21.phase))

