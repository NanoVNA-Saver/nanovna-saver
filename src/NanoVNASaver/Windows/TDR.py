#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020, 2021 NanoVNA-Saver Authors
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
import numpy.typing as npt
from PyQt6 import QtCore, QtGui, QtWidgets
from scipy.constants import speed_of_light  # type: ignore
from scipy.signal import convolve  # type: ignore

from NanoVNASaver.Windows.Defaults import make_scrollable

logger = logging.getLogger(__name__)

CABLE_PARAMETERS = (
    ("Jelly filled (0.64)", 0.64),
    ("Polyethylene (0.66)", 0.66),
    ("PTFE (Teflon) (0.70)", 0.70),
    ("Pulp Insulation (0.72)", 0.72),
    ("Foam or Cellular PE (0.78)", 0.78),
    ("Semi-solid PE (SSPE) (0.84)", 0.84),
    ("Air (Helical spacers) (0.94)", 0.94),
    # Lots of cable types added by Larry Goga, AE5CZ
    ("RG-6/U PE 75\N{OHM SIGN} (Belden 8215) (0.66)", 0.66),
    ("RG-6/U Foam 75\N{OHM SIGN} (Belden 9290) (0.81)", 0.81),
    ("RG-8/U PE 50\N{OHM SIGN} (Belden 8237) (0.66)", 0.66),
    ("RG-8/U Foam (Belden 8214) (0.78)", 0.78),
    ("RG-8/U (Belden 9913) (0.84)", 0.84),
    # Next one added by EKZ, KC3KZ, from measurement of actual cable
    ("RG-8/U (Shireen RFC®400 Low Loss) (0.86)", 0.86),
    ("RG-8X (Belden 9258) (0.82)", 0.82),
    # Next three added by EKZ, KC3KZ, from measurement of actual cable
    ('RG-8X (Wireman "Super 8" CQ106) (0.81)', 0.81),
    ('RG-8X (Wireman "MINI-8 Lo-Loss" CQ118) (0.82)', 0.82),
    ('RG-58 (Wireman "CQ 58 Lo-Loss Flex" CQ129FF) (0.79)', 0.79),
    ("RG-11/U 75\N{OHM SIGN} Foam HDPE (Belden 9292) (0.84)", 0.84),
    ("RG-58/U 52\N{OHM SIGN} PE (Belden 9201) (0.66)", 0.66),
    ("RG-58A/U 54\N{OHM SIGN} Foam (Belden 8219) (0.73)", 0.73),
    ("RG-59A/U PE 75\N{OHM SIGN} (Belden 8241) (0.66)", 0.66),
    ("RG-59A/U Foam 75\N{OHM SIGN} (Belden 8241F) (0.78)", 0.78),
    ("RG-174 PE (Belden 8216)(0.66)", 0.66),
    ("RG-174 Foam (Belden 7805R) (0.735)", 0.735),
    ("RG-213/U PE (Belden 8267) (0.66)", 0.66),
    ("RG316 (0.695)", 0.695),
    ("RG402 (0.695)", 0.695),
    ("LMR-240 (0.84)", 0.84),
    ("LMR-240UF (0.80)", 0.80),
    ("LMR-400 (0.85)", 0.85),
    ("LMR400UF (0.83)", 0.83),
    ("Davis Bury-FLEX (0.82)", 0.82),
)

MIN_DATA_LENGHT = 2

# TODO: Let the user select whether to use high or low resolution TDR?
FFT_POINTS = 2**14


class TDRWindow(QtWidgets.QWidget):
    updated = QtCore.pyqtSignal()

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.td: npt.NDArray[np.complex128]
        self.windowed_s11: npt.NDArray[np.complex128]
        self.distance_axis: npt.NDArray[np.float64]
        self.step_response_Z: npt.NDArray[np.float64]

        self.setWindowTitle("TDR")
        self.setWindowIcon(self.app.icon)

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        layout = QtWidgets.QFormLayout()
        make_scrollable(self, layout)

        dropdown_layout = QtWidgets.QHBoxLayout()

        self.tdr_velocity_dropdown = QtWidgets.QComboBox()
        for cable_name, velocity in CABLE_PARAMETERS:
            self.tdr_velocity_dropdown.addItem(cable_name, velocity)
        self.tdr_velocity_dropdown.insertSeparator(
            self.tdr_velocity_dropdown.count()
        )
        self.tdr_velocity_dropdown.addItem("Custom", -1)
        self.tdr_velocity_dropdown.setCurrentIndex(1)  # Default to PE (0.66)
        self.tdr_velocity_dropdown.currentIndexChanged.connect(self.updateTDR)

        dropdown_layout.addWidget(self.tdr_velocity_dropdown)

        self.format_dropdown = QtWidgets.QComboBox()
        self.format_dropdown.addItem("|Z| (lowpass)")
        self.format_dropdown.addItem("S11 (lowpass)")
        self.format_dropdown.addItem("VSWR (lowpass)")
        self.format_dropdown.addItem("Refl (lowpass)")
        self.format_dropdown.addItem("Refl (bandpass)")

        self.format_dropdown.currentIndexChanged.connect(self.updateFormat)

        dropdown_layout.addWidget(self.format_dropdown)

        layout.addRow(dropdown_layout)

        self.tdr_velocity_input = QtWidgets.QLineEdit()
        self.tdr_velocity_input.setDisabled(True)
        self.tdr_velocity_input.setText("0.66")
        self.tdr_velocity_input.textChanged.connect(self.app.dataUpdated)
        layout.addRow("Velocity factor", self.tdr_velocity_input)

        self.tdr_result_label = QtWidgets.QLabel()
        layout.addRow("Estimated cable length:", self.tdr_result_label)
        layout.addRow(self.app.tdr_chart)

    def updateFormat(self):
        self.app.tdr_chart.resetDisplayLimits()
        self.updateTDR()

    def updateTDR(self):
        if len(self.app.data.s11) < MIN_DATA_LENGHT:
            return

        TDR_format = self.format_dropdown.currentText()

        if self.tdr_velocity_dropdown.currentData() == -1:
            self.tdr_velocity_input.setDisabled(False)
        else:
            self.tdr_velocity_input.setDisabled(True)
            self.tdr_velocity_input.setText(
                str(self.tdr_velocity_dropdown.currentData())
            )

        try:
            v = float(self.tdr_velocity_input.text())
        except ValueError:
            return

        step_size = self.app.data.s11[1].freq - self.app.data.s11[0].freq
        if step_size == 0:
            self.tdr_result_label.setText("")
            logger.info("Cannot compute cable length at 0 span")
            return

        s11 = np.array([complex(d.re, d.im) for d in self.app.data.s11])

        # In lowpass mode, the frequency is measured down to DC. Because the
        # impulse response is real, we can flip over the frequency data so
        # the output of the IFFT is a real signal.
        #
        # In bandpass mode, the low frequency information is missing, so we
        # can't flip the frequency data. We need to keep everything complex.
        # We are only able to determine the magnitude of the impulse
        # response in this mode.
        if "lowpass" in TDR_format:
            s11 = np.fft.fftshift(
                # Include negative frequencies
                np.concatenate([s11, np.conj(s11[-1:0:-1])])
            )

        self.windowed_s11 = np.blackman(len(s11)) * s11

        if "lowpass" in TDR_format:
            td = self._tdr_lowpass(TDR_format, s11)
        else:
            td = np.abs(np.fft.ifft(self.windowed_s11, FFT_POINTS))
            # Convolving with a step function is unnecessary, we can only get
            # the magnitude of impulse response
            if TDR_format == "Refl (bandpass)":
                self.step_response_Z = td * FFT_POINTS / len(s11) * 1 / 0.42

        time_axis = np.linspace(0, 1 / step_size, FFT_POINTS)
        self.distance_axis = time_axis * v * speed_of_light
        # peak = np.max(td)
        # We should check that this is an actual *peak*, and not just
        # a vague maximum
        index_peak = np.argmax(td)

        cable_len = round(self.distance_axis[index_peak] / 2, 3)
        feet = math.floor(cable_len / 0.3048)
        inches = round(((cable_len / 0.3048) - feet) * 12, 1)

        self.tdr_result_label.setText(f"{cable_len}m ({feet}ft {inches}in)")
        self.app.tdr_result_label.setText(f"{cable_len}m")
        self.td = list(td)
        self.updated.emit()

    def _tdr_lowpass(self, tdr_format, s11) -> np.ndarray:
        pad_points = (FFT_POINTS - len(self.windowed_s11)) // 2
        self.windowed_s11 = np.pad(
            self.windowed_s11, [pad_points + 1, pad_points]
        )  # Pad array to length FFT_POINTS
        self.windowed_s11 = np.fft.ifftshift(self.windowed_s11)

        td = np.fft.ifft(self.windowed_s11)
        step = np.ones(FFT_POINTS)
        step_response = convolve(td, step)
        step_response_rev = convolve(td[::-1], step)

        # This fixes the issue with the impedance being wrong when the
        # length is zero
        step_response = step_response + step_response_rev

        # calculate step response based on the format that the user selected
        step_Z = 50 * (1 + step_response) / (1 - step_response)
        step_refl_coefficient = np.abs((step_Z - 50) / (step_Z + 50))
        if tdr_format == "|Z| (lowpass)":
            self.step_response_Z = np.abs(step_Z)
            return td
        if tdr_format == "S11 (lowpass)":
            self.step_response_Z = 20 * np.log10(step_refl_coefficient)
            return td
        if tdr_format == "VSWR (lowpass)":
            self.step_response_Z = np.abs(
                (1 + step_refl_coefficient) / (1 - step_refl_coefficient)
            )
            return td
        if tdr_format == "Refl (lowpass)":
            # The 1/0.42 is the Amplitude Correction Factor for the
            # Blackman window. 0.42 is the average amplitude of the
            # window across its range.
            self.step_response_Z = np.real(
                td * FFT_POINTS / len(s11) * 1 / 0.42
            )
        return td
