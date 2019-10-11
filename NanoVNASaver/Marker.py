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

    returnloss_is_positive = False

    updated = pyqtSignal()

    def __init__(self, name, initialColor, frequency=""):
        super().__init__()
        self.name = name

        if frequency.isnumeric():
            self.frequency = int(frequency)
        self.frequencyInput = QtWidgets.QLineEdit(frequency)
        self.frequencyInput.setProperty("cssClass", "marker_label")
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.textEdited.connect(lambda: self.setFrequency(self.frequencyInput.text()))

        ################################################################################################################
        # Data display label
        ################################################################################################################

        self.frequency_label = QtWidgets.QLabel("")
        self.frequency_label.setMinimumWidth(100)
        self.frequency_label.setProperty("cssClass", "frequency_label")
        self.impedance_label = QtWidgets.QLabel("")
        self.impedance_label.setProperty("cssClass", "impedance_label")
        # self.admittance_label = QtWidgets.QLabel("")
        self.parallel_r_label = QtWidgets.QLabel("")
        self.parallel_r_label.setProperty("cssClass", "parallel_r_label")
        self.parallel_x_label = QtWidgets.QLabel("")
        self.parallel_x_label.setProperty("cssClass", "parallel_x_label")
        self.returnloss_label = QtWidgets.QLabel("")
        self.returnloss_label.setProperty("cssClass", "returnloss_label")
        self.returnloss_label.setMinimumWidth(80)
        self.vswr_label = QtWidgets.QLabel("")
        self.vswr_label.setProperty("cssClass", "vswr_label")
        self.inductance_label = QtWidgets.QLabel("")
        self.inductance_label.setProperty("cssClass", "inductance_label")
        self.capacitance_label = QtWidgets.QLabel("")
        self.capacitance_label.setProperty("cssClass", "capacitance_label")
        self.gain_label = QtWidgets.QLabel("")
        self.gain_label.setProperty("cssClass", "gain_label")
        self.s11_phase_label = QtWidgets.QLabel("")
        self.s11_phase_label.setProperty("cssClass", "s11_phase_label")
        self.s21_phase_label = QtWidgets.QLabel("")
        self.s21_phase_label.setProperty("cssClass", "s21_phase_label")
        self.quality_factor_label = QtWidgets.QLabel("")
        self.quality_factor_label.setProperty("cssClass", "quality_factor_label")

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
        self.group_box.setProperty("cssClass", self.name.replace(" ", "-"))
        box_layout = QtWidgets.QHBoxLayout(self.group_box)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)

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

        min_freq = data[0].freq
        max_freq = data[len(data)-1].freq
        stepsize = data[1].freq - data[0].freq

        if self.frequency + stepsize/2 < min_freq or self.frequency - stepsize/2 > max_freq:
            return

        for i in range(len(data)):
            if abs(data[i].freq - self.frequency) <= (stepsize/2):
                self.location = i
                return

        # No position found, but we are within the span
        min_distance = max_freq
        for i in range(len(data)):
            if abs(data[i].freq - self.frequency) < min_distance:
                min_distance = abs(data[i].freq - self.frequency)
            else:
                # We have now started moving away from the nearest point
                self.location = i-1
                return
        # If we still didn't find a best spot, it was the last value
        self.location = len(data)-1
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
            if re50 > 0:
                rp = (re50 ** 2 + im50 ** 2) / re50
                rp = round(rp, 4 - max(0, math.floor(math.log10(abs(rp)))))
                rpstr = str(rp) + " \N{OHM SIGN}"

                re50 = round(re50, 4 - max(0, math.floor(math.log10(abs(re50)))))
            else:
                rpstr = "- \N{OHM SIGN}"
                re50 = 0

            if im50 != 0:
                xp = (re50 ** 2 + im50 ** 2) / im50
                xp = round(xp, 4 - max(0, math.floor(math.log10(abs(xp)))))
                if xp < 0:
                    xpstr = NanoVNASaver.capacitanceEquivalent(xp, s11data[self.location].freq)
                else:
                    xpstr = NanoVNASaver.inductanceEquivalent(xp, s11data[self.location].freq)
            else:
                xpstr = "-"

            if im50 != 0:
                im50 = round(im50, 4 - max(0, math.floor(math.log10(abs(im50)))))

            if im50 < 0:
                im50str = " -j" + str(-1 * im50)
            else:
                im50str = " +j" + str(im50)
            im50str += " \N{OHM SIGN}"

            self.frequency_label.setText(NanoVNASaver.formatFrequency(s11data[self.location].freq))
            self.impedance_label.setText(str(re50) + im50str)
            self.parallel_r_label.setText(rpstr)
            self.parallel_x_label.setText(xpstr)
            if self.returnloss_is_positive:
                returnloss = -round(NanoVNASaver.gain(s11data[self.location]), 3)
            else:
                returnloss = round(NanoVNASaver.gain(s11data[self.location]), 3)
            self.returnloss_label.setText(str(returnloss) + " dB")
            capacitance = NanoVNASaver.capacitanceEquivalent(im50, s11data[self.location].freq)
            inductance = NanoVNASaver.inductanceEquivalent(im50, s11data[self.location].freq)
            self.inductance_label.setText(inductance)
            self.capacitance_label.setText(capacitance)
            vswr = round(vswr, 3)
            if vswr < 0:
                vswr = "-"
            self.vswr_label.setText(str(vswr))
            q = NanoVNASaver.qualifyFactor(s11data[self.location])
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
                str(round(PhaseChart.angle(s11data[self.location]), 2)) + "\N{DEGREE SIGN}")
            if len(s21data) == len(s11data):
                _, _, vswr = NanoVNASaver.vswr(s21data[self.location])
                self.gain_label.setText(str(round(NanoVNASaver.gain(s21data[self.location]), 3)) + " dB")
                self.s21_phase_label.setText(
                    str(round(PhaseChart.angle(s21data[self.location]), 2)) + "\N{DEGREE SIGN}")
