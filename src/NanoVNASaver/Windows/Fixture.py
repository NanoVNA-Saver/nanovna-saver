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
"""Port extension, fixture de-embedding and reference impedance."""

import logging
import math
from typing import TYPE_CHECKING, Optional

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from ..engine.acquire import correct
from ..engine.deembed import (
    FixtureSettings,
    PortExtension,
    auto_port_extension,
)
from ..engine.sweepdata import SweepData
from ..engine.tdr import SPEED_OF_LIGHT
from ..RFTools import set_reference_impedance
from .Defaults import make_scrollable
from .ui import get_window_icon

if TYPE_CHECKING:
    from ..NanoVNASaver.NanoVNASaver import NanoVNASaver as vna_app

logger = logging.getLogger(__name__)


class _PortGroup(QtWidgets.QGroupBox):
    changed = QtCore.Signal()

    def __init__(self, title: str) -> None:
        super().__init__(title)
        form = QtWidgets.QFormLayout(self)
        self.delay = QtWidgets.QDoubleSpinBox()
        self.delay.setRange(-1e6, 1e6)
        self.delay.setDecimals(2)
        self.delay.setSuffix(" ps")
        self.loss = QtWidgets.QDoubleSpinBox()
        self.loss.setRange(0.0, 30.0)
        self.loss.setDecimals(3)
        self.loss.setSingleStep(0.05)
        self.loss.setSuffix(" dB @1GHz")
        self.length = QtWidgets.QLabel()
        form.addRow("Delay (one way)", self.delay)
        form.addRow("Loss (one way, √f)", self.loss)
        form.addRow("Equivalent length", self.length)
        self.buttons = QtWidgets.QHBoxLayout()
        form.addRow(self.buttons)
        self.delay.valueChanged.connect(self._changed)
        self.loss.valueChanged.connect(self._changed)
        self._changed()

    def add_button(self, text: str, slot) -> None:
        btn = QtWidgets.QPushButton(text)
        btn.clicked.connect(slot)
        self.buttons.addWidget(btn)

    def _changed(self) -> None:
        delay = self.delay.value() * 1e-12
        air = delay * SPEED_OF_LIGHT * 1000
        self.length.setText(
            f"{air:.1f} mm in air, {air * 0.66:.1f} mm PE (VF 0.66)"
        )
        self.changed.emit()

    def extension(self) -> PortExtension:
        return PortExtension(self.delay.value() * 1e-12, self.loss.value())

    def set_extension(self, ext: PortExtension) -> None:
        self.blockSignals(True)
        self.delay.setValue(ext.delay * 1e12)
        self.loss.setValue(ext.loss_db)
        self.blockSignals(False)
        self._changed()


class FixtureWindow(QtWidgets.QWidget):
    def __init__(self, app: "vna_app"):
        super().__init__()
        self.app = app
        self.setWindowTitle("Fixture, port extension & reference impedance")
        self.setWindowIcon(get_window_icon())
        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, layout)

        self.enabled = QtWidgets.QCheckBox("Apply fixture corrections")
        self.enabled.setChecked(True)
        self.enabled.toggled.connect(self.apply)
        layout.addWidget(self.enabled)

        info = QtWidgets.QLabel(
            "Port extension moves the reference plane past cables or test"
            " fixtures after calibration. Auto fits delay and loss from a"
            " measurement of an open or short at the end of the fixture"
            " (port 1) or of a through connection (port 2)."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.port1 = _PortGroup("Port 1 extension")
        self.port1.add_button("Auto (open)", lambda: self.auto_port1("open"))
        self.port1.add_button("Auto (short)", lambda: self.auto_port1("short"))
        self.port1.add_button(
            "Zero", lambda: self.port1.set_extension(PortExtension())
        )
        self.port2 = _PortGroup("Port 2 extension")
        self.port2.add_button("Auto (thru, S21)", self.auto_port2)
        self.port2.add_button(
            "Zero", lambda: self.port2.set_extension(PortExtension())
        )
        self.port1.changed.connect(self.apply)
        self.port2.changed.connect(self.apply)
        layout.addWidget(self.port1)
        layout.addWidget(self.port2)

        layout.addWidget(self.deembed_box())
        layout.addWidget(self.z0_box())
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.fixture1: Optional[SweepData] = None
        self.fixture2: Optional[SweepData] = None

    def deembed_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("De-embedding (2-port fixture files)")
        grid = QtWidgets.QGridLayout(box)
        self.fixture1_label = QtWidgets.QLabel("none")
        self.fixture2_label = QtWidgets.QLabel("none")
        self.flip2 = QtWidgets.QCheckBox(
            "Port 2 file measured VNA→DUT (flip it)"
        )
        self.flip2.setChecked(True)
        self.flip2.toggled.connect(self.apply)
        for row, (label, name) in enumerate(
            ((self.fixture1_label, "1"), (self.fixture2_label, "2"))
        ):
            grid.addWidget(QtWidgets.QLabel(f"Port {name}:"), row, 0)
            grid.addWidget(label, row, 1)
            load = QtWidgets.QPushButton("Load .s2p ...")
            load.clicked.connect(lambda _=False, n=name: self.load_fixture(n))
            clear = QtWidgets.QPushButton("Clear")
            clear.clicked.connect(lambda _=False, n=name: self.clear_fixture(n))
            grid.addWidget(load, row, 2)
            grid.addWidget(clear, row, 3)
        grid.addWidget(self.flip2, 2, 0, 1, 4)
        return box

    def z0_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Reference impedance")
        form = QtWidgets.QFormLayout(box)
        self.z0 = QtWidgets.QDoubleSpinBox()
        self.z0.setRange(1.0, 1000.0)
        self.z0.setDecimals(2)
        self.z0.setValue(50.0)
        self.z0.setSuffix(" Ω")
        self.z0.valueChanged.connect(self.apply)
        presets = QtWidgets.QHBoxLayout()
        for value in (50, 75, 100, 300, 450):
            btn = QtWidgets.QPushButton(f"{value} Ω")
            btn.clicked.connect(lambda _=False, v=value: self.z0.setValue(v))
            presets.addWidget(btn)
        form.addRow("Z0", self.z0)
        form.addRow(presets)
        label = QtWidgets.QLabel(
            "S-parameters are renormalised to Z0 (calibration stays 50 Ω)."
            " Smith chart, VSWR and return loss then refer to Z0."
        )
        label.setWordWrap(True)
        form.addRow(label)
        return box

    def settings(self) -> FixtureSettings:
        if not self.enabled.isChecked():
            return FixtureSettings()
        fixture2 = self.fixture2
        if fixture2 is not None and self.flip2.isChecked():
            fixture2 = SweepData.from_s_matrix(
                fixture2.freq, fixture2.s_matrix()[:, ::-1, ::-1]
            )
        return FixtureSettings(
            port1=self.port1.extension(),
            port2=self.port2.extension(),
            fixture1=self.fixture1,
            fixture2=fixture2,
            z0=self.z0.value(),
        )

    def apply(self) -> None:
        settings = self.settings()
        self.app.worker.fixture = settings
        set_reference_impedance(float(np.real(settings.z0)))
        self.status.setText(
            "Active: " + (self.app.worker.processing_tag() or "nothing")
        )
        if self.app.worker.has_raw_data():
            self.app.worker.reprocess()
        else:
            self.app.update_processing_tag()

    def _calibrated_without_fixture(self) -> Optional[SweepData]:
        worker = self.app.worker
        if not worker.has_raw_data():
            self.app.showError("Run a sweep first.")
            return None
        return correct(
            worker.raw, self.app.calibration, worker.offsetDelay, None, 0.0
        )

    def auto_port1(self, standard: str) -> None:
        data = self._calibrated_without_fixture()
        if data is None:
            return
        ext = auto_port_extension(data.freq, data.s11, standard)
        logger.info("Auto port extension port 1: %s", ext)
        self.port1.set_extension(ext)

    def auto_port2(self) -> None:
        data = self._calibrated_without_fixture()
        if data is None:
            return
        # S21 of a through: phase = -2 pi f (t1 + t2), loss = L1 + L2
        freq = data.freq
        phase = np.unwrap(np.angle(data.s21))
        slope, _ = np.polyfit(freq, phase, 1)
        total_delay = -slope / (2 * math.pi)
        x = np.sqrt(freq / 1e9)
        y = 20 * np.log10(np.maximum(np.abs(data.s21), 1e-12))
        total_loss = -float(np.sum(x * y)) / float(np.sum(x * x))
        p1 = self.port1.extension()
        self.port2.set_extension(
            PortExtension(
                delay=float(total_delay) - p1.delay,
                loss_db=max(total_loss - p1.loss_db, 0.0),
            )
        )

    def load_fixture(self, port: str) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, f"Fixture port {port}", "", "Touchstone 2-port (*.s2p)"
        )
        if not filename:
            return
        try:
            data = SweepData.load(filename)
        except (ValueError, OSError) as exc:
            self.app.showError(f"Unable to load {filename}: {exc}")
            return
        if not data.is_full_two_port:
            self.app.showError("Fixture file must be a full 2-port .s2p")
            return
        name = filename.replace("\\", "/").rsplit("/", 1)[-1]
        if port == "1":
            self.fixture1 = data
            self.fixture1_label.setText(name)
        else:
            self.fixture2 = data
            self.fixture2_label.setText(name)
        self.apply()

    def clear_fixture(self, port: str) -> None:
        if port == "1":
            self.fixture1 = None
            self.fixture1_label.setText("none")
        else:
            self.fixture2 = None
            self.fixture2_label.setText("none")
        self.apply()
