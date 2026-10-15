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
"""Full 2-port measurement on a one path VNA by reversing the DUT."""

import logging
from typing import TYPE_CHECKING, Optional

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from ..engine.acquire import correct
from ..engine.sweepdata import SweepData
from ..Hardware.VirtualVNA import VirtualVNA
from .Defaults import make_scrollable
from .ui import get_window_icon

if TYPE_CHECKING:
    from ..NanoVNASaver.NanoVNASaver import NanoVNASaver as vna_app

logger = logging.getLogger(__name__)


def combine(forward: SweepData, reverse: SweepData) -> SweepData:
    """Raw forward + raw reversed sweep -> raw full 2-port data"""
    if len(forward) != len(reverse) or not np.allclose(
        forward.freq, reverse.freq
    ):
        raise ValueError(
            "Forward and reverse sweeps must use identical frequencies."
        )
    return SweepData(
        freq=forward.freq.copy(),
        s11=forward.s11.copy(),
        s21=forward.s21.copy(),
        s12=reverse.s21.copy(),
        s22=reverse.s11.copy(),
        z0=forward.z0,
    )


class TwoPortWindow(QtWidgets.QWidget):
    def __init__(self, app: "vna_app"):
        super().__init__()
        self.app = app
        self.forward: Optional[SweepData] = None
        self.reverse: Optional[SweepData] = None
        self.result: Optional[SweepData] = None

        self.setWindowTitle("Full 2-port measurement")
        self.setWindowIcon(get_window_icon())
        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)
        layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, layout)

        info = QtWidgets.QLabel(
            "NanoVNAs only measure in forward direction (S11, S21). To get"
            " all four S-parameters the DUT is measured twice:\n"
            "1. Connect the DUT normally, run a sweep, capture forward.\n"
            "2. Turn the DUT around (port 2 of the DUT on VNA port 1),"
            " run a sweep, capture reverse.\n"
            "3. Combine. With a full 2-port calibration (short, open, load,"
            " through, thru-reflection, isolation) the result is fully"
            " error corrected, including load match. Otherwise a 1-port /"
            " response corrected approximation is used."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        box = QtWidgets.QGroupBox("Measurement")
        grid = QtWidgets.QGridLayout(box)
        self.fwd_label = QtWidgets.QLabel("not captured")
        self.rev_label = QtWidgets.QLabel("not captured")
        btn_fwd = QtWidgets.QPushButton("1. Capture forward")
        btn_fwd.clicked.connect(self.capture_forward)
        btn_rev = QtWidgets.QPushButton("2. Capture reverse (DUT flipped)")
        btn_rev.clicked.connect(self.capture_reverse)
        btn_combine = QtWidgets.QPushButton("3. Combine && show")
        btn_combine.clicked.connect(self.combine_and_show)
        self.btn_save = QtWidgets.QPushButton("Save .s2p ...")
        self.btn_save.clicked.connect(self.save)
        self.btn_save.setEnabled(False)
        grid.addWidget(btn_fwd, 0, 0)
        grid.addWidget(self.fwd_label, 0, 1)
        grid.addWidget(btn_rev, 1, 0)
        grid.addWidget(self.rev_label, 1, 1)
        grid.addWidget(btn_combine, 2, 0)
        grid.addWidget(self.btn_save, 2, 1)
        layout.addWidget(box)

        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _capture(self) -> Optional[SweepData]:
        if self.app.sweep_control.btn_stop.isEnabled():
            self.app.showError("Stop the running sweep first.")
            return None
        if not self.app.worker.has_raw_data():
            self.app.showError("Run a sweep first.")
            return None
        return self.app.worker.raw.copy()

    def _virtual(self) -> Optional[VirtualVNA]:
        vna = self.app.vna
        return vna if isinstance(vna, VirtualVNA) else None

    def capture_forward(self) -> None:
        data = self._capture()
        if data is None:
            return
        self.forward = data
        self.fwd_label.setText(f"{len(data)} points captured")
        if vna := self._virtual():
            vna.reversed = True
            self.status.setText(
                "Virtual device: DUT reversed automatically. Run a sweep"
                " and capture reverse."
            )
        else:
            self.status.setText("Now turn the DUT around and run a sweep.")

    def capture_reverse(self) -> None:
        data = self._capture()
        if data is None:
            return
        self.reverse = data
        self.rev_label.setText(f"{len(data)} points captured")
        if vna := self._virtual():
            vna.reversed = False
        self.status.setText("Ready to combine.")

    def combine_and_show(self) -> None:
        if self.forward is None or self.reverse is None:
            self.app.showError("Capture forward and reverse first.")
            return
        try:
            raw = combine(self.forward, self.reverse)
        except ValueError as exc:
            self.app.showError(str(exc))
            return
        cal = self.app.calibration
        worker = self.app.worker
        full = cal.isCalculated and cal.isValid2Port()
        if full:
            result = correct(
                raw,
                cal,
                worker.offsetDelay,
                worker.fixture,
                worker.smoothing_pct,
            )
            mode = "fully corrected (one-path 2-port with DUT reversal)"
        else:
            fwd = worker.process(self.forward)
            rev = worker.process(self.reverse)
            result = combine(fwd, rev)
            mode = (
                "approximation (no 2-port calibration: S11/S22 1-port"
                " corrected, S21/S12 response only)"
            )
        self.result = result
        self.app.saveData(
            result.datapoints("s11"),
            result.datapoints("s21"),
            "Full 2-port",
            result.datapoints("s12"),
            result.datapoints("s22"),
        )
        self.app.dataUpdated()
        self.btn_save.setEnabled(True)
        self.status.setText(
            f"Result: {mode}. Shown as S11/S21 in the charts; S12/S22 are"
            " in the Pro traces window and in exported .s2p files. The"
            " next sweep replaces the result."
        )

    def save(self) -> None:
        if self.result is None:
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save full 2-port", "", "Touchstone 2-port (*.s2p)"
        )
        if not filename:
            return
        if not filename.lower().endswith(".s2p"):
            filename += ".s2p"
        self.result.save(filename)
        self.status.setText(f"Saved {filename}")
