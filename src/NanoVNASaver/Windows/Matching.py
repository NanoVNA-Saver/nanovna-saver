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
"""L-network matching helper."""

import logging
from typing import TYPE_CHECKING

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from ..engine.matching import l_networks
from ..Formatting import format_complex_imp, format_frequency, parse_frequency
from ..RFTools import gamma_to_impedance, reference_impedance
from .Defaults import make_scrollable
from .ui import get_window_icon

if TYPE_CHECKING:
    from ..NanoVNASaver.NanoVNASaver import NanoVNASaver as vna_app

logger = logging.getLogger(__name__)


class MatchingWindow(QtWidgets.QWidget):
    def __init__(self, app: "vna_app"):
        super().__init__()
        self.app = app
        self.setWindowTitle("Matching network (L-network)")
        self.setWindowIcon(get_window_icon())
        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)
        layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, layout)

        form = QtWidgets.QFormLayout()
        self.freq_input = QtWidgets.QLineEdit()
        self.freq_input.setPlaceholderText("e.g. 435M")
        self.freq_input.editingFinished.connect(self.calculate)
        btn_marker = QtWidgets.QPushButton("Use marker 1")
        btn_marker.clicked.connect(self.use_marker)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.freq_input)
        row.addWidget(btn_marker)
        form.addRow("Frequency", row)
        self.manual = QtWidgets.QCheckBox("Enter load impedance manually")
        self.manual.toggled.connect(self.calculate)
        self.r_input = QtWidgets.QDoubleSpinBox()
        self.r_input.setRange(0.001, 1e6)
        self.r_input.setValue(25.0)
        self.x_input = QtWidgets.QDoubleSpinBox()
        self.x_input.setRange(-1e6, 1e6)
        self.x_input.setValue(-30.0)
        self.r_input.valueChanged.connect(self.calculate)
        self.x_input.valueChanged.connect(self.calculate)
        form.addRow(self.manual)
        form.addRow("R load (Ω)", self.r_input)
        form.addRow("X load (Ω)", self.x_input)
        layout.addLayout(form)

        self.load_label = QtWidgets.QLabel()
        layout.addWidget(self.load_label)
        self.result = QtWidgets.QPlainTextEdit()
        self.result.setReadOnly(True)
        font = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.FixedFont
        )
        self.result.setFont(font)
        self.result.setMinimumSize(520, 300)
        layout.addWidget(self.result)

    def use_marker(self) -> None:
        if not self.app.markers:
            return
        freq = self.app.markers[0].freq
        if freq:
            self.freq_input.setText(format_frequency(freq))
            self.calculate()

    def _load_impedance(self, freq: float) -> complex | None:
        if self.manual.isChecked():
            return complex(self.r_input.value(), self.x_input.value())
        s11 = self.app.data.s11
        if len(s11) < 2:
            return None
        f = np.array([d.freq for d in s11], dtype=float)
        if freq < f[0] or freq > f[-1]:
            return None
        z = np.array([d.z for d in s11])
        gamma = np.interp(freq, f, z.real) + 1j * np.interp(freq, f, z.imag)
        return gamma_to_impedance(complex(gamma))

    def calculate(self) -> None:
        freq = parse_frequency(self.freq_input.text())
        if freq <= 0:
            self.result.setPlainText("Enter a frequency.")
            return
        zl = self._load_impedance(freq)
        if zl is None:
            self.result.setPlainText("Frequency outside of the sweep data.")
            return
        z0 = reference_impedance()
        self.load_label.setText(
            f"Load at {format_frequency(freq)}: {format_complex_imp(zl)}"
            f"  →  match to {z0:g} Ω"
        )
        if zl.real <= 0:
            self.result.setPlainText("Load has no resistive part.")
            return
        nets = l_networks(zl, freq, z0)
        if not nets:
            self.result.setPlainText("Load is already matched.")
            return
        text = []
        for i, net in enumerate(nets, 1):
            text.append(f"Solution {i} ({net.topology})")
            text.append(f"  series: {net.series}")
            text.append(f"  shunt : {net.shunt}")
            text.append("  " + net.describe().replace("\n", "\n  "))
            text.append("")
        self.result.setPlainText("\n".join(text))
