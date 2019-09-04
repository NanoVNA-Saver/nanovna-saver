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
from PyQt5 import QtWidgets
from typing import List
import numpy as np

Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class CalibrationWindow(QtWidgets.QWidget):
    def __init__(self, app):
        super().__init__()

        from NanoVNASaver import NanoVNASaver

        self.app: NanoVNASaver = app

        self.setMinimumSize(300, 300)
        self.setWindowTitle("Calibration")
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        calibration_status_group = QtWidgets.QGroupBox("Active calibration")
        calibration_status_layout = QtWidgets.QFormLayout()
        self.calibration_status_label = QtWidgets.QLabel("Device calibration")
        calibration_status_layout.addRow("Calibration active: ", self.calibration_status_label)
        calibration_status_group.setLayout(calibration_status_layout)
        layout.addWidget(calibration_status_group)

        calibration_control_group = QtWidgets.QGroupBox("Calibrate")
        calibration_control_layout = QtWidgets.QFormLayout(calibration_control_group)
        btn_cal_short = QtWidgets.QPushButton("Short")
        btn_cal_short.clicked.connect(self.saveShort)
        self.cal_short_label = QtWidgets.QLabel("Uncalibrated")
        
        btn_cal_open = QtWidgets.QPushButton("Open")
        btn_cal_open.clicked.connect(self.saveOpen)
        self.cal_open_label = QtWidgets.QLabel("Uncalibrated")
        
        btn_cal_load = QtWidgets.QPushButton("Load")
        btn_cal_load.clicked.connect(self.saveLoad)
        self.cal_load_label = QtWidgets.QLabel("Uncalibrated")

        btn_cal_through = QtWidgets.QPushButton("Through")
        btn_cal_through.clicked.connect(self.saveThrough)
        #btn_cal_through.setDisabled(True)
        self.cal_through_label = QtWidgets.QLabel("Uncalibrated")

        btn_cal_isolation = QtWidgets.QPushButton("Isolation")
        btn_cal_isolation.clicked.connect(self.saveIsolation)
        #btn_cal_isolation.setDisabled(True)
        self.cal_isolation_label = QtWidgets.QLabel("Uncalibrated")

        calibration_control_layout.addRow(btn_cal_short, self.cal_short_label)
        calibration_control_layout.addRow(btn_cal_open, self.cal_open_label)
        calibration_control_layout.addRow(btn_cal_load, self.cal_load_label)
        calibration_control_layout.addRow(btn_cal_through, self.cal_through_label)
        calibration_control_layout.addRow(btn_cal_isolation, self.cal_isolation_label)

        calibration_control_layout.addRow(QtWidgets.QLabel(""))

        btn_apply = QtWidgets.QPushButton("Apply")
        calibration_control_layout.addRow(btn_apply)
        btn_apply.clicked.connect(self.calculate)

        btn_reset = QtWidgets.QPushButton("Reset")
        calibration_control_layout.addRow(btn_reset)
        btn_reset.clicked.connect(self.reset)

        layout.addWidget(calibration_control_group)

    def saveShort(self):
        self.app.calibration.s11short = self.app.data
        self.cal_short_label.setText("Calibrated")

    def saveOpen(self):
        self.app.calibration.s11open = self.app.data
        self.cal_open_label.setText("Calibrated")

    def saveLoad(self):
        self.app.calibration.s11load = self.app.data
        self.cal_load_label.setText("Calibrated")

    def saveIsolation(self):
        self.app.calibration.s21isolation = self.app.data21
        self.cal_isolation_label.setText("Calibrated")

    def saveThrough(self):
        self.app.calibration.s21through = self.app.data21
        self.cal_through_label.setText("Calibrated")

    def reset(self):
        self.app.calibration = Calibration()
        self.cal_short_label.setText("Uncalibrated")
        self.cal_open_label.setText("Uncalibrated")
        self.cal_load_label.setText("Uncalibrated")
        self.calibration_status_label.setText("Device calibration")

    def calculate(self):
        if self.app.calibration.calculateCorrections():
            self.calibration_status_label.setText("Application calibration")

class Calibration:
    s11short: List[Datapoint] = []
    s11open: List[Datapoint] = []
    s11load: List[Datapoint] = []
    s21through: List[Datapoint] = []
    s21isolation: List[Datapoint] = []

    frequencies = []

    # 1-port
    e00 = []    # Directivity
    e11 = []    # Port match
    deltaE = [] # Tracking

    # 2-port
    e30 = []    # Port match
    e10e32 = [] # Transmission

    shortIdeal = np.complex(-1, 0)
    openIdeal  = np.complex(1, 0)
    loadIdeal  = np.complex(0, 0)

    isCalculated = False

    def isValid2Port(self):
        return len(self.s21through) > 0 and len(self.s21isolation) > 0 and self.isValid1Port()

    def isValid1Port(self):
        return len(self.s11short) > 0 and len(self.s11open) > 0 and len(self.s11load) > 0

    def calculateCorrections(self):
        if not self.isValid1Port():
            return False
        self.frequencies = [int] * len(self.s11short)
        self.e00 = [np.complex] * len(self.s11short)
        self.e11 = [np.complex] * len(self.s11short)
        self.deltaE = [np.complex] * len(self.s11short)
        self.e30 = [np.complex] * len(self.s11short)
        self.e10e32 = [np.complex] * len(self.s11short)
        for i in range(len(self.s11short)):
            self.frequencies[i] = self.s11short[i].freq

            g1 = self.shortIdeal
            g2 = self.openIdeal
            g3 = self.loadIdeal

            gm1 = np.complex(self.s11short[i].re, self.s11short[i].im)
            gm2 = np.complex(self.s11open[i].re, self.s11open[i].im)
            gm3 = np.complex(self.s11load[i].re, self.s11load[i].im)

            denominator = g1*(g2-g3)*gm1 + g2*g3*gm2 - g2*g3*gm3 - (g2*gm2-g3*gm3)*g1
            self.e00[i] = - ((g2*gm3 - g3*gm3)*g1*gm2 - (g2*g3*gm2 - g2*g3*gm3 - (g3*gm2 - g2*gm3)*g1)*gm1) / denominator
            self.e11[i] = ((g2-g3)*gm1-g1*(gm2-gm3)+g3*gm2-g2*gm3) / denominator
            self.deltaE[i] = - ((g1*(gm2-gm3)-g2*gm2+g3*gm3)*gm1+(g2*gm3-g3*gm3)*gm2) / denominator

            if self.isValid2Port():
                self.e30[i] = np.complex(self.s21isolation[i].re, self.s21isolation[i].im)
                s21m = np.complex(self.s21through[i].re, self.s21through[i].im)
                self.e10e32[i] = (s21m - self.e30[i]) * (1 - (self.e11[i]*self.e11[i]))

        self.isCalculated = True
        return self.isCalculated

    def correct11(self, re, im, freq):
        s11m = np.complex(re, im)
        distance = 10**10
        index = 0
        for i in range(len(self.s11short)):
            if abs(self.s11short[i].freq - freq) < distance:
                index = i
                distance = abs(self.s11short[i].freq - freq)

        s11 = (s11m - self.e00[index]) / ((s11m * self.e11[index]) - self.deltaE[index])
        return s11.real, s11.imag

    def correct21(self, re, im, freq):
        s21m = np.complex(re, im)
        distance = 10**10
        index = 0
        for i in range(len(self.s21through)):
            if abs(self.s21through[i].freq - freq) < distance:
                index = i
                distance = abs(self.s21through[i].freq - freq)
        s21 = (s21m - self.e30[index]) / self.e10e32[index]
        return s21.real, s21.imag
