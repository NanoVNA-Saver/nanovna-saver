#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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

from PySide6 import QtCore, QtWidgets

from NanoVNASaver import NanoVNASaver

from ..Defaults import SweepConfig, get_app_config
from ..Formatting import (
    format_frequency_inputs,
    format_frequency_short,
    format_frequency_sweep,
    parse_frequency,
)
from .Control import Control

logger = logging.getLogger(__name__)


class FrequencyInputWidget(QtWidgets.QLineEdit):
    def __init__(self, text=""):
        super().__init__(text)
        self.nextFrequency = -1
        self.previousFrequency = -1
        self.setFixedHeight(20)
        self.setMinimumWidth(60)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

    def setText(self, text: str) -> None:
        super().setText(format_frequency_inputs(text))

    def get_freq(self) -> int:
        return parse_frequency(self.text())


class SweepControl(Control):
    def __init__(self, app: NanoVNASaver):
        super().__init__(app, "Sweep control")

        sweep_settings = self.get_settings()

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.VLine)

        input_layout = QtWidgets.QHBoxLayout()
        input_layout_l = QtWidgets.QFormLayout()
        input_layout_r = QtWidgets.QFormLayout()

        input_layout.addLayout(input_layout_l)
        input_layout.addWidget(line)
        input_layout.addLayout(input_layout_r)

        self.layout.addRow(input_layout)

        self.inputs: dict[str, FrequencyInputWidget] = {
            "Start": FrequencyInputWidget(sweep_settings.start),
            "Stop": FrequencyInputWidget(sweep_settings.end),
            "Center": FrequencyInputWidget(sweep_settings.center),
            "Span": FrequencyInputWidget(sweep_settings.span),
        }
        self.inputs["Start"].textEdited.connect(self.update_center_span)
        self.inputs["Start"].textChanged.connect(self.update_step_size)
        self.inputs["Stop"].textEdited.connect(self.update_center_span)
        self.inputs["Stop"].textChanged.connect(self.update_step_size)
        self.inputs["Center"].textEdited.connect(self.update_start_end)
        self.inputs["Span"].textEdited.connect(self.update_start_end)

        input_layout_l.addRow(QtWidgets.QLabel("Start"), self.inputs["Start"])
        input_layout_l.addRow(QtWidgets.QLabel("Stop"), self.inputs["Stop"])
        input_layout_r.addRow(QtWidgets.QLabel("Center"), self.inputs["Center"])
        input_layout_r.addRow(QtWidgets.QLabel("Span"), self.inputs["Span"])

        self.input_segments = QtWidgets.QLineEdit(sweep_settings.segments)
        self.input_segments.textEdited.connect(self.update_step_size)

        self.label_step = QtWidgets.QLabel("Hz/step")
        self.label_step.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        segment_layout = QtWidgets.QHBoxLayout()
        segment_layout.addWidget(self.input_segments)
        segment_layout.addWidget(self.label_step)
        self.layout.addRow(QtWidgets.QLabel("Segments"), segment_layout)

        btn_settings_window = QtWidgets.QPushButton("Sweep settings ...")
        btn_settings_window.setFixedHeight(20)
        btn_settings_window.clicked.connect(
            lambda: self.app.display_window("sweep_settings")
        )

        self.layout.addRow(btn_settings_window)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.layout.addRow(self.progress_bar)

        self.btn_start = self._build_start_button()
        self.btn_stop = self._build_stop_button()

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout_widget = QtWidgets.QWidget()
        btn_layout_widget.setLayout(btn_layout)
        self.layout.addRow(btn_layout_widget)

        self.inputs["Start"].textEdited.emit(self.inputs["Start"].text())
        self.inputs["Start"].textChanged.emit(self.inputs["Start"].text())

    def _build_start_button(self) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton("Sweep")
        btn.setFixedHeight(20)
        btn.clicked.connect(self.app.sweep_start)
        btn.setShortcut(QtCore.Qt.Key.Key_Control + QtCore.Qt.Key.Key_W)
        # Will be enabled when VNA is connected
        btn.setEnabled(False)
        return btn

    def _build_stop_button(self) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton("Stop")
        btn.setFixedHeight(20)
        btn.clicked.connect(self.app.worker.quit)
        btn.setShortcut(QtCore.Qt.Key.Key_Escape)
        btn.setDisabled(True)
        return btn

    def get_start(self) -> int:
        return self.inputs["Start"].get_freq()

    def set_start(self, start: int):
        self.inputs["Start"].setText(format_frequency_sweep(start))
        self.inputs["Start"].textEdited.emit(self.inputs["Start"].text())
        self.updated.emit(self)

    def get_end(self) -> int:
        return self.inputs["Stop"].get_freq()

    def set_end(self, end: int):
        self.inputs["Stop"].setText(format_frequency_sweep(end))
        self.inputs["Stop"].setText(format_frequency_sweep(end))
        self.inputs["Stop"].textEdited.emit(self.inputs["Stop"].text())
        self.updated.emit(self)

    def get_center(self) -> int:
        return self.inputs["Center"].get_freq()

    def set_center(self, center: int):
        self.inputs["Center"].setText(format_frequency_sweep(center))
        self.inputs["Center"].textEdited.emit(self.inputs["Center"].text())
        self.updated.emit(self)

    def get_segments(self) -> int:
        try:
            result = int(self.input_segments.text())
        except ValueError:
            result = 1
        return result

    def set_segments(self, count: int):
        self.input_segments.setText(str(count))
        self.input_segments.textEdited.emit(self.input_segments.text())
        self.updated.emit(self)

    def get_span(self) -> int:
        return self.inputs["Span"].get_freq()

    def set_span(self, span: int):
        self.inputs["Span"].setText(format_frequency_sweep(span))
        self.inputs["Span"].textEdited.emit(self.inputs["Span"].text())
        self.updated.emit(self)

    def toggle_settings(self, disabled):
        self.inputs["Start"].setDisabled(disabled)
        self.inputs["Stop"].setDisabled(disabled)
        self.inputs["Span"].setDisabled(disabled)
        self.inputs["Center"].setDisabled(disabled)
        self.input_segments.setDisabled(disabled)

    def update_center_span(self):
        fstart = self.get_start()
        fstop = self.get_end()
        fspan = fstop - fstart
        fcenter = round((fstart + fstop) / 2)
        if fspan < 0 or fstart < 0 or fstop < 0:
            return
        self.inputs["Center"].setText(fcenter)
        self.inputs["Span"].setText(fspan)
        self.update_text()
        self.update_sweep()

    def update_start_end(self):
        fcenter = self.get_center()
        fspan = self.get_span()
        if fspan < 0 or fcenter < 0:
            return
        fstart = round(fcenter - fspan / 2)
        fstop = round(fcenter + fspan / 2)
        if fstart < 0 or fstop < 0:
            return
        self.inputs["Start"].setText(fstart)
        self.inputs["Stop"].setText(fstop)
        self.update_text()
        self.update_sweep()

    def update_step_size(self):
        fspan = self.get_span()
        if fspan < 0:
            return
        segments = self.get_segments()
        if segments > 0:
            fstep = fspan / (segments * self.app.vna.datapoints - 1)
            self.label_step.setText(f"{format_frequency_short(fstep)}/step")
        self.update_sweep()

    def update_sweep(self):
        self.app.sweep.update(
            start=self.get_start(),
            end=self.get_end(),
            segments=self.get_segments(),
            points=self.app.vna.datapoints,
        )

    def update_sweep_btn(self, enabled: bool) -> None:
        self.btn_start.setEnabled(enabled)

    def get_settings(self) -> SweepConfig:
        return get_app_config().sweep_settings

    def store_settings(self) -> None:
        settings = self.get_settings()
        settings.start = self.inputs["Start"].text()
        settings.end = self.inputs["Stop"].text()
        settings.center = self.inputs["Center"].text()
        settings.span = self.inputs["Span"].text()
        settings.segments = self.input_segments.text()

    def update_text(self) -> None:
        cal_ds = self.app.calibration.dataset
        start = self.get_start()
        stop = self.get_end()
        if cal_ds.data:
            oor_text = (
                f"Out of calibration range ("
                f"{format_frequency_inputs(cal_ds.freq_min())} - "
                f"{format_frequency_inputs(cal_ds.freq_max())})"
            )
        else:
            oor_text = "No calibration data"
        self.inputs["Start"].setStyleSheet("QLineEdit {}")
        self.inputs["Stop"].setStyleSheet("QLineEdit {}")
        self.inputs["Start"].setToolTip("")
        self.inputs["Stop"].setToolTip("")
        if not cal_ds.data:
            self.inputs["Start"].setToolTip(oor_text)
            self.inputs["Start"].setStyleSheet("QLineEdit { color: red; }")
            self.inputs["Stop"].setToolTip(oor_text)
            self.inputs["Stop"].setStyleSheet("QLineEdit { color: red; }")
        else:
            if start < cal_ds.freq_min():
                self.inputs["Start"].setToolTip(oor_text)
                self.inputs["Start"].setStyleSheet("QLineEdit { color: red; }")
            if stop > cal_ds.freq_max():
                self.inputs["Stop"].setToolTip(oor_text)
                self.inputs["Stop"].setStyleSheet("QLineEdit { color: red; }")
        self.inputs["Start"].repaint()
        self.inputs["Stop"].repaint()
