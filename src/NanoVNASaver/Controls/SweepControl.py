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

from PyQt6 import QtCore, QtWidgets

from NanoVNASaver.Controls.Control import Control
from NanoVNASaver.Formatting import (
    format_frequency_short,
    format_frequency_sweep,
    parse_frequency,
)
from NanoVNASaver.Inputs import FrequencyInputWidget

logger = logging.getLogger(__name__)


class SweepControl(Control):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__(app, "Sweep control")

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.VLine)

        input_layout = QtWidgets.QHBoxLayout()
        input_left_layout = QtWidgets.QFormLayout()
        input_right_layout = QtWidgets.QFormLayout()
        input_layout.addLayout(input_left_layout)
        input_layout.addWidget(line)
        input_layout.addLayout(input_right_layout)
        self.layout.addRow(input_layout)

        self.input_start = FrequencyInputWidget()
        self.input_start.setFixedHeight(20)
        self.input_start.setMinimumWidth(60)
        self.input_start.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.input_start.textEdited.connect(self.update_center_span)
        self.input_start.textChanged.connect(self.update_step_size)
        input_left_layout.addRow(QtWidgets.QLabel("Start"), self.input_start)

        self.input_end = FrequencyInputWidget()
        self.input_end.setFixedHeight(20)
        self.input_end.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.input_end.textEdited.connect(self.update_center_span)
        self.input_end.textChanged.connect(self.update_step_size)
        input_left_layout.addRow(QtWidgets.QLabel("Stop"), self.input_end)

        self.input_center = FrequencyInputWidget()
        self.input_center.setFixedHeight(20)
        self.input_center.setMinimumWidth(60)
        self.input_center.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.input_center.textEdited.connect(self.update_start_end)

        input_right_layout.addRow(QtWidgets.QLabel("Center"), self.input_center)

        self.input_span = FrequencyInputWidget()
        self.input_span.setFixedHeight(20)
        self.input_span.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.input_span.textEdited.connect(self.update_start_end)

        input_right_layout.addRow(QtWidgets.QLabel("Span"), self.input_span)

        self.input_segments = QtWidgets.QLineEdit(
            self.app.settings.value("Segments", "1")
        )
        self.input_segments.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.input_segments.setFixedHeight(20)
        self.input_segments.setFixedWidth(60)
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

        self.btn_start = QtWidgets.QPushButton("Sweep")
        self.btn_start.setFixedHeight(20)
        self.btn_start.clicked.connect(self.app.sweep_start)
        self.btn_start.setShortcut(
            QtCore.Qt.Key.Key_Control + QtCore.Qt.Key.Key_W
        )
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setFixedHeight(20)
        self.btn_stop.clicked.connect(self.app.sweep_stop)
        self.btn_stop.setShortcut(QtCore.Qt.Key.Key_Escape)
        self.btn_stop.setDisabled(True)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout_widget = QtWidgets.QWidget()
        btn_layout_widget.setLayout(btn_layout)
        self.layout.addRow(btn_layout_widget)

        self.input_start.textEdited.emit(self.input_start.text())
        self.input_start.textChanged.emit(self.input_start.text())

    def get_start(self) -> int:
        return parse_frequency(self.input_start.text())

    def set_start(self, start: int):
        self.input_start.setText(format_frequency_sweep(start))
        self.input_start.textEdited.emit(self.input_start.text())
        self.updated.emit(self)

    def get_end(self) -> int:
        return parse_frequency(self.input_end.text())

    def set_end(self, end: int):
        self.input_end.setText(format_frequency_sweep(end))
        self.input_end.textEdited.emit(self.input_end.text())
        self.updated.emit(self)

    def get_center(self) -> int:
        return parse_frequency(self.input_center.text())

    def set_center(self, center: int):
        self.input_center.setText(format_frequency_sweep(center))
        self.input_center.textEdited.emit(self.input_center.text())
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
        return parse_frequency(self.input_span.text())

    def set_span(self, span: int):
        self.input_span.setText(format_frequency_sweep(span))
        self.input_span.textEdited.emit(self.input_span.text())
        self.updated.emit(self)

    def toggle_settings(self, disabled):
        self.input_start.setDisabled(disabled)
        self.input_end.setDisabled(disabled)
        self.input_span.setDisabled(disabled)
        self.input_center.setDisabled(disabled)
        self.input_segments.setDisabled(disabled)

    def update_center_span(self):
        fstart = self.get_start()
        fstop = self.get_end()
        fspan = fstop - fstart
        fcenter = round((fstart + fstop) / 2)
        if fspan < 0 or fstart < 0 or fstop < 0:
            return
        self.input_span.setText(fspan)
        self.input_center.setText(fcenter)
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
        self.input_start.setText(fstart)
        self.input_end.setText(fstop)
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
