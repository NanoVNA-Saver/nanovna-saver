#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
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
import collections
import math
from typing import List

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver.RFTools import Datapoint, RFTools


class Marker(QtCore.QObject):
    name = "Marker"
    frequency = 0
    color: QtGui.QColor = QtGui.QColor()
    location = -1

    returnloss_is_positive = False

    updated = pyqtSignal(object)

    fieldSelection = []

    class FrequencyInput(QtWidgets.QLineEdit):
        nextFrequency = -1
        previousFrequency = -1

        def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
            if a0.type() == QtCore.QEvent.KeyPress:
                if a0.key() == QtCore.Qt.Key_Up and self.nextFrequency != -1:
                    a0.accept()
                    self.setText(str(self.nextFrequency))
                    self.textEdited.emit(self.text())
                    return
                elif a0.key() == QtCore.Qt.Key_Down and self.previousFrequency != -1:
                    a0.accept()
                    self.setText(str(self.previousFrequency))
                    self.textEdited.emit(self.text())
                    return
            super().keyPressEvent(a0)

    def __init__(self, name, initialColor, frequency=""):
        super().__init__()
        self.name = name

        if frequency.isnumeric():
            self.frequency = int(frequency)
        self.frequencyInput = Marker.FrequencyInput(frequency)

        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.textEdited.connect(self.setFrequency)

        ################################################################################################################
        # Data display label
        ################################################################################################################

        self.frequency_label = QtWidgets.QLabel("")
        self.frequency_label.setMinimumWidth(100)
        self.impedance_label = QtWidgets.QLabel("")
        self.admittance_label = QtWidgets.QLabel("")
        # self.admittance_label = QtWidgets.QLabel("")
        self.parallel_r_label = QtWidgets.QLabel("")
        self.parallel_x_label = QtWidgets.QLabel("")
        self.parallel_c_label = QtWidgets.QLabel("")
        self.parallel_l_label = QtWidgets.QLabel("")
        self.returnloss_label = QtWidgets.QLabel("")
        self.returnloss_label.setMinimumWidth(80)
        self.vswr_label = QtWidgets.QLabel("")
        self.series_r_label = QtWidgets.QLabel("")
        self.series_lc_label = QtWidgets.QLabel("")
        self.inductance_label = QtWidgets.QLabel("")
        self.capacitance_label = QtWidgets.QLabel("")
        self.gain_label = QtWidgets.QLabel("")
        self.s11_phase_label = QtWidgets.QLabel("")
        self.s21_phase_label = QtWidgets.QLabel("")
        self.quality_factor_label = QtWidgets.QLabel("")

        self.fields = {"actualfreq": ("Frequency:", self.frequency_label),
                       "impedance": ("Impedance:", self.impedance_label),
                       "admittance": ("Admittance:", self.admittance_label),
                       "serr": ("Series R:", self.series_r_label),
                       "serl": ("Series L:", self.inductance_label),
                       "serc": ("Series C:", self.capacitance_label),
                       "serlc": ("Series L/C:", self.series_lc_label),
                       "parr": ("Parallel R:", self.parallel_r_label),
                       "parc": ("Parallel C:", self.parallel_c_label),
                       "parl": ("Parallel L:", self.parallel_l_label),
                       "parlc": ("Parallel L/C:", self.parallel_x_label),
                       "returnloss": ("Return loss:", self.returnloss_label),
                       "vswr": ("VSWR:", self.vswr_label),
                       "s11q": ("Quality factor:", self.quality_factor_label),
                       "s11phase": ("S11 Phase:", self.s11_phase_label),
                       "s21gain": ("S21 Gain:", self.gain_label),
                       "s21phase": ("S21 Phase:", self.s21_phase_label),
                       }

        ################################################################################################################
        # Marker control layout
        ################################################################################################################

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setFixedWidth(20)
        self.btnColorPicker.clicked.connect(lambda: self.setColor(QtWidgets.QColorDialog.getColor(self.color, options=QtWidgets.QColorDialog.ShowAlphaChannel)))
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

        # Left side
        # self.left_form.addRow("Frequency:", self.frequency_label)
        # self.left_form.addRow("Impedance:", self.impedance_label)
        # # left_form.addRow("Admittance:", self.admittance_label)
        # self.left_form.addRow("Parallel R:", self.parallel_r_label)
        # self.left_form.addRow("Parallel X:", self.parallel_x_label)
        # self.left_form.addRow("L equiv.:", self.inductance_label)
        # self.left_form.addRow("C equiv.:", self.capacitance_label)
        #
        # # Right side
        # self.right_form.addRow("Return loss:", self.returnloss_label)
        # if "vswr" in self.fieldSelection:
        #     self.right_form.addRow("VSWR:", self.vswr_label)
        #     self.vswr_label.show()
        # self.right_form.addRow("Q:", self.quality_factor_label)
        # self.right_form.addRow("S11 Phase:", self.s11_phase_label)
        # self.right_form.addRow("S21 Gain:", self.gain_label)
        # self.right_form.addRow("S21 Phase:", self.s21_phase_label)

    def setFrequency(self, frequency):
        f = RFTools.parseFrequency(frequency)
        self.frequency = max(f, 0)
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

        color_string = QtCore.QVariant(color)
        color_string.convert(QtCore.QVariant.String)
        self.group_box.setStyleSheet('QGroupBox { color: ' + color_string.value() + '};')

    def getRow(self):
        return QtWidgets.QLabel(self.name), self.layout

    def findLocation(self, data: List[Datapoint]):
        self.location = -1
        self.frequencyInput.nextFrequency = self.frequencyInput.previousFrequency = -1
        if self.frequency == 0:
            # No frequency set for this marker
            return
        if len(data) == 0:
            # Set the frequency before loading any data
            return

        min_freq = data[0].freq
        max_freq = data[len(data)-1].freq
        lower_stepsize = data[1].freq - data[0].freq
        upper_stepsize = data[len(data)-1].freq - data[len(data)-2].freq

        if self.frequency + lower_stepsize/2 < min_freq or self.frequency - upper_stepsize/2 > max_freq:
            # We are outside the bounds of the data, so we can't put in a marker
            return

        min_distance = max_freq
        for i in range(len(data)):
            if abs(data[i].freq - self.frequency) < min_distance:
                min_distance = abs(data[i].freq - self.frequency)
            else:
                # We have now started moving away from the nearest point
                self.location = i-1
                if i < len(data):
                    self.frequencyInput.nextFrequency = data[i].freq
                if (i-2) >= 0:
                    self.frequencyInput.previousFrequency = data[i-2].freq
                return
        # If we still didn't find a best spot, it was the last value
        self.location = len(data)-1
        self.frequencyInput.previousFrequency = data[len(data)-2].freq
        return

    def getGroupBox(self) -> QtWidgets.QGroupBox:
        return self.group_box
    
    def resetLabels(self):
        self.frequency_label.setText("")
        self.impedance_label.setText("")
        self.parallel_r_label.setText("")
        self.parallel_x_label.setText("")
        # self.admittance_label.setText("")
        self.vswr_label.setText("")
        self.returnloss_label.setText("")
        self.inductance_label.setText("")
        self.capacitance_label.setText("")
        self.gain_label.setText("")
        self.s11_phase_label.setText("")
        self.s21_phase_label.setText("")
        self.quality_factor_label.setText("")

    def updateLabels(self, s11data: List[Datapoint], s21data: List[Datapoint]):
        if self.location != -1:
            re50, im50 = RFTools.normalize50(s11data[self.location])
            vswr = RFTools.calculateVSWR(s11data[self.location])
            if re50 > 0:
                rp = (re50 ** 2 + im50 ** 2) / re50
                rp = round(rp, 4 - max(0, math.floor(math.log10(abs(rp)))))
                rpstr = str(rp)

                re50 = round(re50, 4 - max(0, math.floor(math.log10(abs(re50)))))
            else:
                rpstr = "-"
                re50 = 0

            if im50 != 0:
                xp = (re50 ** 2 + im50 ** 2) / im50
                xp = round(xp, 4 - max(0, math.floor(math.log10(abs(xp)))))
                xpcstr = RFTools.capacitanceEquivalent(xp, s11data[self.location].freq)
                xplstr = RFTools.inductanceEquivalent(xp, s11data[self.location].freq)
                if xp < 0:
                    xpstr = xpcstr
                    xp50str = " -j" + str(-1 * xp)
                else:
                    xpstr = xplstr
                    xp50str = " +j" + str(xp)
                xp50str += " \N{OHM SIGN}"
            else:
                xp50str = " +j ? \N{OHM SIGN}"
                xpstr = xpcstr = xplstr = "-"

            if im50 != 0:
                im50 = round(im50, 4 - max(0, math.floor(math.log10(abs(im50)))))

            if im50 < 0:
                im50str = " -j" + str(-1 * im50)
            else:
                im50str = " +j" + str(im50)
            im50str += " \N{OHM SIGN}"

            self.frequency_label.setText(RFTools.formatFrequency(s11data[self.location].freq))
            self.impedance_label.setText(str(re50) + im50str)
            self.admittance_label.setText(rpstr + xp50str)
            self.series_r_label.setText(str(re50) + " \N{OHM SIGN}")
            self.parallel_r_label.setText(rpstr + " \N{OHM SIGN}")
            self.parallel_x_label.setText(xpstr)
            if self.returnloss_is_positive:
                returnloss = -round(RFTools.gain(s11data[self.location]), 3)
            else:
                returnloss = round(RFTools.gain(s11data[self.location]), 3)
            self.returnloss_label.setText(str(returnloss) + " dB")
            capacitance = RFTools.capacitanceEquivalent(im50, s11data[self.location].freq)
            inductance = RFTools.inductanceEquivalent(im50, s11data[self.location].freq)
            self.inductance_label.setText(inductance)
            self.capacitance_label.setText(capacitance)
            self.parallel_c_label.setText(xpcstr)
            self.parallel_l_label.setText(xplstr)
            if im50 > 0:
                self.series_lc_label.setText(inductance)
            else:
                self.series_lc_label.setText(capacitance)
            vswr = round(vswr, 3)
            if vswr < 0:
                vswr = "-"
            self.vswr_label.setText(str(vswr))
            q = RFTools.qualityFactor(s11data[self.location])
            if q > 10000 or q < 0:
                q_str = "\N{INFINITY}"
            elif q > 1000:
                q_str = str(round(q, 0))
            elif q > 100:
                q_str = str(round(q, 1))
            elif q > 10:
                q_str = str(round(q, 2))
            else:
                q_str = str(round(q, 3))
            self.quality_factor_label.setText(q_str)
            self.s11_phase_label.setText(
                str(round(RFTools.phaseAngle(s11data[self.location]), 2)) + "\N{DEGREE SIGN}")
            if len(s21data) == len(s11data):
                self.gain_label.setText(str(round(RFTools.gain(s21data[self.location]), 3)) + " dB")
                self.s21_phase_label.setText(
                    str(round(RFTools.phaseAngle(s21data[self.location]), 2)) + "\N{DEGREE SIGN}")
