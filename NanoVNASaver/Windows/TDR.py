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
import logging
import math

import numpy as np
import scipy.signal as signal
from PyQt5 import QtWidgets, QtCore


logger = logging.getLogger(__name__)


class TDRWindow(QtWidgets.QWidget):
    updated = QtCore.pyqtSignal()

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.td = []
        self.distance_axis = []
        self.step_response = []
        self.step_response_Z = []

        self.setWindowTitle("TDR")
        self.setWindowIcon(self.app.icon)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.tdr_velocity_dropdown = QtWidgets.QComboBox()
        self.tdr_velocity_dropdown.addItem("Jelly filled (0.64)", 0.64)
        self.tdr_velocity_dropdown.addItem("Polyethylene (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("PTFE (Teflon) (0.70)", 0.70)
        self.tdr_velocity_dropdown.addItem("Pulp Insulation (0.72)", 0.72)
        self.tdr_velocity_dropdown.addItem("Foam or Cellular PE (0.78)", 0.78)
        self.tdr_velocity_dropdown.addItem("Semi-solid PE (SSPE) (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("Air (Helical spacers) (0.94)", 0.94)
        self.tdr_velocity_dropdown.insertSeparator(self.tdr_velocity_dropdown.count())
        # Lots of cable types added by Larry Goga, AE5CZ
        self.tdr_velocity_dropdown.addItem("RG-6/U PE 75\N{OHM SIGN} (Belden 8215) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-6/U Foam 75\N{OHM SIGN} (Belden 9290) (0.81)", 0.81)
        self.tdr_velocity_dropdown.addItem("RG-8/U PE 50\N{OHM SIGN} (Belden 8237) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-8/U Foam (Belden 8214) (0.78)", 0.78)
        self.tdr_velocity_dropdown.addItem("RG-8/U (Belden 9913) (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("RG-8X (Belden 9258) (0.82)", 0.82)
        self.tdr_velocity_dropdown.addItem(
            "RG-11/U 75\N{OHM SIGN} Foam HDPE (Belden 9292) (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("RG-58/U 52\N{OHM SIGN} PE (Belden 9201) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem(
            "RG-58A/U 54\N{OHM SIGN} Foam (Belden 8219) (0.73)", 0.73)
        self.tdr_velocity_dropdown.addItem("RG-59A/U PE 75\N{OHM SIGN} (Belden 8241) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem(
            "RG-59A/U Foam 75\N{OHM SIGN} (Belden 8241F) (0.78)", 0.78)
        self.tdr_velocity_dropdown.addItem("RG-174 PE (Belden 8216)(0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-174 Foam (Belden 7805R) (0.735)", 0.735)
        self.tdr_velocity_dropdown.addItem("RG-213/U PE (Belden 8267) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG316 (0.695)", 0.695)
        self.tdr_velocity_dropdown.addItem("RG402 (0.695)", 0.695)
        self.tdr_velocity_dropdown.addItem("LMR-240 (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("LMR-240UF (0.80)", 0.80)
        self.tdr_velocity_dropdown.addItem("LMR-400 (0.85)", 0.85)
        self.tdr_velocity_dropdown.addItem("LMR400UF (0.83)", 0.83)
        self.tdr_velocity_dropdown.addItem("Davis Bury-FLEX (0.82)", 0.82)
        self.tdr_velocity_dropdown.insertSeparator(self.tdr_velocity_dropdown.count())
        self.tdr_velocity_dropdown.addItem("Custom", -1)

        self.tdr_velocity_dropdown.setCurrentIndex(1)  # Default to PE (0.66)

        self.tdr_velocity_dropdown.currentIndexChanged.connect(self.updateTDR)

        layout.addRow(self.tdr_velocity_dropdown)

        self.tdr_velocity_input = QtWidgets.QLineEdit()
        self.tdr_velocity_input.setDisabled(True)
        self.tdr_velocity_input.setText("0.66")
        self.tdr_velocity_input.textChanged.connect(self.app.dataUpdated)

        layout.addRow("Velocity factor", self.tdr_velocity_input)

        self.tdr_result_label = QtWidgets.QLabel()
        layout.addRow("Estimated cable length:", self.tdr_result_label)

        layout.addRow(self.app.tdr_chart)

    def updateTDR(self):
        c = 299792458
        # TODO: Let the user select whether to use high or low resolution TDR?
        FFT_POINTS = 2**14

        if len(self.app.data) < 2:
            return

        if self.tdr_velocity_dropdown.currentData() == -1:
            self.tdr_velocity_input.setDisabled(False)
        else:
            self.tdr_velocity_input.setDisabled(True)
            self.tdr_velocity_input.setText(str(self.tdr_velocity_dropdown.currentData()))

        try:
            v = float(self.tdr_velocity_input.text())
        except ValueError:
            return

        step_size = self.app.data[1].freq - self.app.data[0].freq
        if step_size == 0:
            self.tdr_result_label.setText("")
            logger.info("Cannot compute cable length at 0 span")
            return

        s11 = []
        for d in self.app.data:
            s11.append(np.complex(d.re, d.im))

        window = np.blackman(len(self.app.data))

        windowed_s11 = window * s11
        self.td = np.abs(np.fft.ifft(windowed_s11, FFT_POINTS))
        step = np.ones(FFT_POINTS)
        self.step_response = signal.convolve(self.td, step)

        self.step_response_Z = 50 * (1 + self.step_response) / (1 - self.step_response)

        time_axis = np.linspace(0, 1/step_size, FFT_POINTS)
        self.distance_axis = time_axis * v * c
        # peak = np.max(td)
        #  We should check that this is an actual *peak*, and not just a vague maximum
        index_peak = np.argmax(self.td)

        cable_len = round(self.distance_axis[index_peak]/2, 3)
        feet = math.floor(cable_len / 0.3048)
        inches = round(((cable_len / 0.3048) - feet)*12, 1)

        self.tdr_result_label.setText(f"{cable_len}m ({feet}ft {inches}in)")
        self.app.tdr_result_label.setText(str(cable_len) + " m")
        self.updated.emit()
