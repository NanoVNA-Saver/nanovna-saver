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
from typing import List

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver import RFTools
from NanoVNASaver.Formatting import (
    format_capacitance,
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
    parse_frequency,
)
from NanoVNASaver.Inputs import MarkerFrequencyInputWidget as FrequencyInput
from NanoVNASaver.Marker.Values import TYPES, Value, default_label_ids

COLORS = (
    QtGui.QColor(QtCore.Qt.darkGray),
    QtGui.QColor(255, 0, 0),
    QtGui.QColor(0, 255, 0),
    QtGui.QColor(0, 0, 255),
    QtGui.QColor(0, 255, 255),
    QtGui.QColor(255, 0, 255),
    QtGui.QColor(255, 255, 0),
)


class MarkerLabel(QtWidgets.QLabel):
    def __init__(self, name):
        super().__init__("")
        self.name = name


class Marker(QtCore.QObject, Value):
    _instances = 0
    color: QtGui.QColor = QtGui.QColor()
    coloredText = True
    location = -1
    returnloss_is_positive = False
    updated = pyqtSignal(object)
    active_labels = []

    @classmethod
    def count(cls):
        return cls._instances

    def __init__(self, name: str = "", qsettings: QtCore.QSettings = None):
        super().__init__()
        self.name = name
        self.qsettings = qsettings
        self.name = name
        self.color = QtGui.QColor()
        self.index = 0

        if self.qsettings:
            Marker._instances += 1
            Marker.active_labels = self.qsettings.value(
                "MarkerFields", defaultValue=default_label_ids())
            self.index = Marker._instances

        if not self.name:
            self.name = f"Marker {Marker._instances}"

#        self.freq = RFTools.RFTools.parseFrequency(frequency)

        self.frequencyInput = FrequencyInput()
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.textEdited.connect(self.setFrequency)

        ###############################################################
        # Data display labels
        ###############################################################

        self.label = {}
        for l in TYPES:
            self.label[l.label_id] = MarkerLabel(l.name)
        self.label['actualfreq'].setMinimumWidth(100)
        self.label['returnloss'].setMinimumWidth(80)

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

        ###############################################################
        # Data display layout
        ###############################################################

        self.group_box = QtWidgets.QGroupBox(self.name)
        self.group_box.setMaximumWidth(340)
        box_layout = QtWidgets.QHBoxLayout(self.group_box)

        try:
            self.setColor(
                self.qsettings.value(
                    f"Marker{self.count()}Color", COLORS[self.count()]))
        except AttributeError:  # happens when qsettings == None
            self.setColor(COLORS[1])
        except IndexError:
            self.setColor(COLORS[0])

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)

        # line only if more then 3 selected
        self.left_form = QtWidgets.QFormLayout()
        self.right_form = QtWidgets.QFormLayout()
        box_layout.addLayout(self.left_form)
        box_layout.addWidget(line)
        box_layout.addLayout(self.right_form)

        self.buildForm()

    def __del__(self):
        if self.qsettings:
            Marker._instances -= 1

    def _add_active_labels(self, label_id, form):
        if label_id in self.label:
            form.addRow(
                f"{self.label[label_id].name}:", self.label[label_id])
            self.label[label_id].show()

    def _size_str(self) -> str:
        return str(self.group_box.font().pointSize())

    def update_settings(self):
        self.qsettings.setValue(f"Marker{self.index}Color", self.color)

    def setScale(self, scale):
        self.group_box.setMaximumWidth(int(340 * scale))
        self.label['actualfreq'].setMinimumWidth(int(100 * scale))
        self.label['actualfreq'].setMinimumWidth(int(100 * scale))
        self.label['returnloss'].setMinimumWidth(int(80 * scale))
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

        if len(self.active_labels) <= 3:
            for label_id in self.active_labels:
                self._add_active_labels(label_id, self.left_form)
        else:
            left_half = math.ceil(len(self.active_labels)/2)
            right_half = len(self.active_labels)
            for i in range(left_half):
                label_id = self.active_labels[i]
                self._add_active_labels(label_id, self.left_form)
            for i in range(left_half, right_half):
                label_id = self.active_labels[i]
                self._add_active_labels(label_id, self.right_form)

    def setFrequency(self, frequency):
        self.freq = parse_frequency(frequency)
        self.updated.emit(self)

    def setFieldSelection(self, fields):
        self.active_labels = fields[:]
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
        datasize = len(data)
        if datasize == 0:
            # Set the frequency before loading any data
            return

        min_freq = data[0].freq
        max_freq = data[-1].freq
        lower_stepsize = data[1].freq - data[0].freq
        upper_stepsize = data[-1].freq - data[-2].freq

        # We are outside the bounds of the data, so we can't put in a marker
        if (self.freq + lower_stepsize/2 < min_freq or
                self.freq - upper_stepsize/2 > max_freq):
            return

        min_distance = max_freq
        for i, item in enumerate(data):
            if abs(item.freq - self.freq) <= min_distance:
                min_distance = abs(item.freq - self.freq)
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
        for v in self.label.values():
            v.setText("")

    def updateLabels(self,
                     s11data: List[RFTools.Datapoint],
                     s21data: List[RFTools.Datapoint]):
        try:
            s11 = s11data[self.location]
        except IndexError:
            self.location = 0
            return

        self.store(self.location, s11data, s21data)

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

        self.label['actualfreq'].setText(format_frequency_space(s11.freq))
        self.label['admittance'].setText(format_complex_imp(imp_p))
        self.label['impedance'].setText(format_complex_imp(imp))
        self.label['parc'].setText(cap_p_str)
        self.label['parl'].setText(ind_p_str)
        self.label['parlc'].setText(x_p_str)
        self.label['parr'].setText(format_resistance(imp_p.real))
        self.label['returnloss'].setText(
            format_gain(s11.gain, self.returnloss_is_positive))
        self.label['s11groupdelay'].setText(
            format_group_delay(RFTools.groupDelay(s11data, self.location)))
        self.label['s11mag'].setText(format_magnitude(abs(s11.z)))
        self.label['s11phase'].setText(format_phase(s11.phase))
        self.label['s11polar'].setText(
            str(round(abs(s11.z), 2)) + "∠" + format_phase(s11.phase))
        self.label['s11q'].setText(format_q_factor(s11.qFactor()))
        self.label['s11z'].setText(format_resistance(abs(imp)))
        self.label['serc'].setText(cap_str)
        self.label['serl'].setText(ind_str)
        self.label['serlc'].setText(x_str)
        self.label['serr'].setText(format_resistance(imp.real))
        self.label['vswr'].setText(format_vswr(s11.vswr))

        if len(s21data) == len(s11data):
            s21 = s21data[self.location]
            self.label['s21gain'].setText(format_gain(s21.gain))
            self.label['s21groupdelay'].setText(
                format_group_delay(RFTools.groupDelay(s21data, self.location) / 2))
            self.label['s21mag'].setText(format_magnitude(abs(s21.z)))
            self.label['s21phase'].setText(format_phase(s21.phase))
            self.label['s21polar'].setText(
                str(round(abs(s21.z), 2)) + "∠" + format_phase(s21.phase))
