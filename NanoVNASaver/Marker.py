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

Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class Marker(QtCore.QObject):
    name = "Marker"
    frequency = 0
    color = QtGui.QColor()
    location = -1

    updated = pyqtSignal()

    def __init__(self, name, initialColor, frequency=""):
        super().__init__()
        self.name = name

        if frequency.isnumeric():
            self.frequency = int(frequency)
        self.frequencyInput = QtWidgets.QLineEdit(frequency)
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.textEdited.connect(lambda: self.setFrequency(self.frequencyInput.text()))

        ################################################################################################################
        # Data display label
        ################################################################################################################

        self.frequency_label = QtWidgets.QLabel("")
        self.frequency_label.setMinimumWidth(100)
        self.impedance_label = QtWidgets.QLabel("")
        # self.admittance_label = QtWidgets.QLabel("")
        self.parallel_r_label = QtWidgets.QLabel("")
        self.parallel_x_label = QtWidgets.QLabel("")
        self.returnloss_label = QtWidgets.QLabel("")
        self.returnloss_label.setMinimumWidth(80)
        self.vswr_label = QtWidgets.QLabel("")
        self.inductance_label = QtWidgets.QLabel("")
        self.capacitance_label = QtWidgets.QLabel("")
        self.gain_label = QtWidgets.QLabel("")
        self.s11_phase_label = QtWidgets.QLabel("")
        self.s21_phase_label = QtWidgets.QLabel("")
        self.quality_factor_label = QtWidgets.QLabel("")

        ################################################################################################################
        # Marker control layout
        ################################################################################################################

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setFixedWidth(20)
        self.setColor(initialColor)
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
        box_layout = QtWidgets.QHBoxLayout(self.group_box)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)
        #line.setFrameShadow(QtWidgets.QFrame.Sunken)

        left_form = QtWidgets.QFormLayout()
        right_form = QtWidgets.QFormLayout()
        box_layout.addLayout(left_form)
        box_layout.addWidget(line)
        box_layout.addLayout(right_form)

        # Left side
        left_form.addRow("Frequency:", self.frequency_label)
        left_form.addRow("Impedance:", self.impedance_label)
        # left_form.addRow("Admittance:", self.admittance_label)
        left_form.addRow("Parallel R:", self.parallel_r_label)
        left_form.addRow("Parallel X:", self.parallel_x_label)
        left_form.addRow("L equiv.:", self.inductance_label)
        left_form.addRow("C equiv.:", self.capacitance_label)

        # Right side
        right_form.addRow("Return loss:", self.returnloss_label)
        right_form.addRow("VSWR:", self.vswr_label)
        right_form.addRow("Q:", self.quality_factor_label)
        right_form.addRow("S11 Phase:", self.s11_phase_label)
        right_form.addRow("S21 Gain:", self.gain_label)
        right_form.addRow("S21 Phase:", self.s21_phase_label)

    def setFrequency(self, frequency):
        from .NanoVNASaver import NanoVNASaver
        f = NanoVNASaver.parseFrequency(frequency)
        if f > 0:
            self.frequency = f
            self.updated.emit()
        else:
            self.frequency = 0
            self.updated.emit()
            return

    def setColor(self, color):
        if color.isValid():
            self.color = color
            p = self.btnColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, self.color)
            self.btnColorPicker.setPalette(p)

    def getRow(self):
        return QtWidgets.QLabel(self.name), self.layout

    def findLocation(self, data: List[Datapoint]):
        self.location = -1
        if self.frequency == 0:
            # No frequency set for this marker
            return
        if len(data) == 0:
            # Set the frequency before loading any data
            return

        stepsize = data[1].freq-data[0].freq
        for i in range(len(data)):
            if abs(data[i].freq-self.frequency) <= (stepsize/2):
                self.location = i
                return

    def getGroupBox(self):
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
        from NanoVNASaver.Chart import PhaseChart
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        if self.location != -1:
            im50, re50, vswr = NanoVNASaver.vswr(s11data[self.location])
            rp = (re50 ** 2 + im50 ** 2) / re50
            xp = (re50 ** 2 + im50 ** 2) / im50
            re50 = round(re50, 4 - max(0, math.floor(math.log10(abs(re50)))))
            rp = round(rp, 4 - max(0, math.floor(math.log10(abs(rp)))))
            im50 = round(im50, 4 - max(0, math.floor(math.log10(abs(im50)))))
            xp = round(xp, 4 - max(0, math.floor(math.log10(abs(xp)))))
            if im50 < 0:
                im50str = " -j" + str(-1 * im50)
            else:
                im50str = " +j" + str(im50)
            im50str += " \N{OHM SIGN}"

            if xp < 0:
                xpstr = NanoVNASaver.capacitanceEquivalent(xp, s11data[self.location].freq)
            else:
                xpstr = NanoVNASaver.inductanceEquivalent(xp, s11data[self.location].freq)

            self.frequency_label.setText(NanoVNASaver.formatFrequency(s11data[self.location].freq))
            self.impedance_label.setText(str(re50) + im50str)
            self.parallel_r_label.setText(str(rp) + " \N{OHM SIGN}")
            self.parallel_x_label.setText(xpstr)
            self.returnloss_label.setText(str(round(20 * math.log10((vswr - 1) / (vswr + 1)), 3)) + " dB")
            capacitance = NanoVNASaver.capacitanceEquivalent(im50, s11data[self.location].freq)
            inductance = NanoVNASaver.inductanceEquivalent(im50, s11data[self.location].freq)
            self.inductance_label.setText(inductance)
            self.capacitance_label.setText(capacitance)
            vswr = round(vswr, 3)
            if vswr < 0:
                vswr = "-"
            self.vswr_label.setText(str(vswr))
            self.quality_factor_label.setText(str(round(NanoVNASaver.qualifyFactor(s11data[self.location]), 1)))
            self.s11_phase_label.setText(
                str(round(PhaseChart.angle(s11data[self.location]), 2)) + "\N{DEGREE SIGN}")
            if len(s21data) == len(s11data):
                _, _, vswr = NanoVNASaver.vswr(s21data[self.location])
                self.gain_label.setText(str(round(20 * math.log10((vswr - 1) / (vswr + 1)), 3)) + " dB")
                self.s21_phase_label.setText(
                    str(round(PhaseChart.angle(s21data[self.location]), 2)) + "\N{DEGREE SIGN}")
