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

import html
import logging
from functools import partial
from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from ..Calibration import Calibration
from ..engine.calkit import CalKit, CalKitLibrary
from ..engine.health import check_calibration, verify_standard
from ..Hardware.VirtualVNA import STANDARDS, VirtualVNA
from ..Settings.Sweep import SweepMode
from ..Touchstone import Touchstone
from .Defaults import make_scrollable
from .ui import get_window_icon

logger = logging.getLogger(__name__)


def _format_cal_label(size: int, prefix: str = "Set") -> str:
    return f"{prefix} ({size} points)"


def getFloatValue(text: str) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


class CalibrationWindow(QtWidgets.QWidget):
    next_step = -1

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setMinimumWidth(450)
        self.setWindowTitle("Calibration")
        self.setWindowIcon(get_window_icon())
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        top_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()
        right_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout)

        make_scrollable(self, top_layout)

        calibration_status_group = QtWidgets.QGroupBox("Active calibration")
        calibration_status_layout = QtWidgets.QFormLayout()
        self.calibration_status_label = QtWidgets.QLabel("Device calibration")
        self.calibration_source_label = QtWidgets.QLabel("NanoVNA")
        calibration_status_layout.addRow(
            "Calibration:", self.calibration_status_label
        )
        calibration_status_layout.addRow(
            "Source:", self.calibration_source_label
        )
        calibration_status_group.setLayout(calibration_status_layout)
        left_layout.addWidget(calibration_status_group)

        calibration_control_group = QtWidgets.QGroupBox("Calibrate")
        calibration_control_layout = QtWidgets.QFormLayout(
            calibration_control_group
        )
        cal_btn = {}
        self.cal_label = {}
        for label_name in (
            "short",
            "open",
            "load",
            "through",
            "thrurefl",
            "isolation",
        ):
            self.cal_label[label_name] = QtWidgets.QLabel("Uncalibrated")
            cal_btn[label_name] = QtWidgets.QPushButton(label_name.capitalize())
            cal_btn[label_name].setMinimumHeight(20)
            cal_btn[label_name].clicked.connect(
                partial(self.manual_save, label_name)
            )
            calibration_control_layout.addRow(
                cal_btn[label_name], self.cal_label[label_name]
            )

        self.input_offset_delay = QtWidgets.QDoubleSpinBox()
        self.input_offset_delay.setMinimumHeight(20)
        self.input_offset_delay.setValue(0)
        self.input_offset_delay.setSuffix(" ps")
        self.input_offset_delay.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.input_offset_delay.valueChanged.connect(self.setOffsetDelay)
        self.input_offset_delay.setRange(-10e6, 10e6)

        calibration_control_layout.addRow(QtWidgets.QLabel(""))
        calibration_control_layout.addRow(
            "Offset delay", self.input_offset_delay
        )

        self.btn_automatic = QtWidgets.QPushButton("Calibration assistant")
        self.btn_automatic.setMinimumHeight(20)
        calibration_control_layout.addRow(self.btn_automatic)
        self.btn_automatic.clicked.connect(self.automaticCalibration)

        apply_reset_layout = QtWidgets.QHBoxLayout()

        btn_apply = QtWidgets.QPushButton("Apply")
        btn_apply.setMinimumHeight(20)
        btn_apply.clicked.connect(self.calculate)

        btn_reset = QtWidgets.QPushButton("Reset")
        btn_reset.setMinimumHeight(20)
        btn_reset.clicked.connect(self.reset)

        apply_reset_layout.addWidget(btn_apply)
        apply_reset_layout.addWidget(btn_reset)

        calibration_control_layout.addRow(apply_reset_layout)

        left_layout.addWidget(calibration_control_group)

        calibration_notes_group = QtWidgets.QGroupBox("Notes")
        calibration_notes_layout = QtWidgets.QVBoxLayout(
            calibration_notes_group
        )
        self.notes_textedit = QtWidgets.QPlainTextEdit()
        calibration_notes_layout.addWidget(self.notes_textedit)

        left_layout.addWidget(calibration_notes_group)

        file_box = QtWidgets.QGroupBox("Files")
        file_layout = QtWidgets.QFormLayout(file_box)
        btn_save_file = QtWidgets.QPushButton("Save calibration")
        btn_save_file.setMinimumHeight(20)
        btn_save_file.clicked.connect(lambda: self.saveCalibration())
        btn_load_file = QtWidgets.QPushButton("Load calibration")
        btn_load_file.setMinimumHeight(20)
        btn_load_file.clicked.connect(lambda: self.loadCalibration())

        save_load_layout = QtWidgets.QHBoxLayout()
        save_load_layout.addWidget(btn_save_file)
        save_load_layout.addWidget(btn_load_file)

        file_layout.addRow(save_load_layout)

        left_layout.addWidget(file_box)

        cal_standard_box = QtWidgets.QGroupBox("Calibration standards")
        cal_standard_layout = QtWidgets.QFormLayout(cal_standard_box)
        self.use_ideal_values = QtWidgets.QRadioButton("Use ideal values")
        self.use_s1p_files = QtWidgets.QRadioButton("Use s1p files")
        self.use_coefficients = QtWidgets.QRadioButton("Use coefficients")

        self.use_ideal_values.setChecked(True)
        self.radio_group = QtWidgets.QButtonGroup(self)
        self.radio_group.addButton(self.use_ideal_values)
        self.radio_group.addButton(self.use_s1p_files)
        self.radio_group.addButton(self.use_coefficients)
        self.radio_group.buttonClicked.connect(self.calStandardChanged)

        self.radio_layout = QtWidgets.QHBoxLayout()
        self.radio_layout.addWidget(self.use_ideal_values)
        self.radio_layout.addWidget(self.use_s1p_files)
        self.radio_layout.addWidget(self.use_coefficients)
        cal_standard_layout.addRow(self.radio_layout)

        self.file_button_short = QtWidgets.QPushButton("Short S1P file")
        self.file_button_open = QtWidgets.QPushButton("Open S1P file")
        self.file_button_load = QtWidgets.QPushButton("Load S1P file")
        self.file_button_short.setEnabled(False)
        self.file_button_open.setEnabled(False)
        self.file_button_load.setEnabled(False)

        cal_standard_layout.addRow(self.file_button_short)
        cal_standard_layout.addRow(self.file_button_open)
        cal_standard_layout.addRow(self.file_button_load)

        self.file_button_open.clicked.connect(self.select_file_open)
        self.file_button_short.clicked.connect(self.select_file_short)
        self.file_button_load.clicked.connect(self.select_file_load)

        self.cal_short_box = QtWidgets.QGroupBox("Short")
        cal_short_form = QtWidgets.QFormLayout(self.cal_short_box)
        self.cal_short_box.setDisabled(True)
        self.short_l0_input = QtWidgets.QLineEdit("0")
        self.short_l0_input.setMinimumHeight(20)
        self.short_l1_input = QtWidgets.QLineEdit("0")
        self.short_l1_input.setMinimumHeight(20)
        self.short_l2_input = QtWidgets.QLineEdit("0")
        self.short_l2_input.setMinimumHeight(20)
        self.short_l3_input = QtWidgets.QLineEdit("0")
        self.short_l3_input.setMinimumHeight(20)
        self.short_length = QtWidgets.QLineEdit("0")
        self.short_length.setMinimumHeight(20)
        cal_short_form.addRow("L0 (H(e-12))", self.short_l0_input)
        cal_short_form.addRow("L1 (H(e-24))", self.short_l1_input)
        cal_short_form.addRow("L2 (H(e-33))", self.short_l2_input)
        cal_short_form.addRow("L3 (H(e-42))", self.short_l3_input)
        cal_short_form.addRow("Offset Delay (ps)", self.short_length)

        self.cal_open_box = QtWidgets.QGroupBox("Open")
        cal_open_form = QtWidgets.QFormLayout(self.cal_open_box)
        self.cal_open_box.setDisabled(True)
        self.open_c0_input = QtWidgets.QLineEdit("50")
        self.open_c0_input.setMinimumHeight(20)
        self.open_c1_input = QtWidgets.QLineEdit("0")
        self.open_c1_input.setMinimumHeight(20)
        self.open_c2_input = QtWidgets.QLineEdit("0")
        self.open_c2_input.setMinimumHeight(20)
        self.open_c3_input = QtWidgets.QLineEdit("0")
        self.open_c3_input.setMinimumHeight(20)
        self.open_length = QtWidgets.QLineEdit("0")
        self.open_length.setMinimumHeight(20)
        cal_open_form.addRow("C0 (F(e-15))", self.open_c0_input)
        cal_open_form.addRow("C1 (F(e-27))", self.open_c1_input)
        cal_open_form.addRow("C2 (F(e-36))", self.open_c2_input)
        cal_open_form.addRow("C3 (F(e-45))", self.open_c3_input)
        cal_open_form.addRow("Offset Delay (ps)", self.open_length)

        self.cal_load_box = QtWidgets.QGroupBox("Load")
        cal_load_form = QtWidgets.QFormLayout(self.cal_load_box)
        self.cal_load_box.setDisabled(True)
        self.load_resistance = QtWidgets.QLineEdit("50")
        self.load_resistance.setMinimumHeight(20)
        self.load_inductance = QtWidgets.QLineEdit("0")
        self.load_inductance.setMinimumHeight(20)
        self.load_capacitance = QtWidgets.QLineEdit("0")
        self.load_capacitance.setMinimumHeight(20)
        # self.load_capacitance.setDisabled(True)  # Not yet implemented
        self.load_length = QtWidgets.QLineEdit("0")
        self.load_length.setMinimumHeight(20)
        cal_load_form.addRow("Resistance (\N{OHM SIGN})", self.load_resistance)
        cal_load_form.addRow("Inductance (H(e-12))", self.load_inductance)
        cal_load_form.addRow("Capacitance (F(e-15))", self.load_capacitance)
        cal_load_form.addRow("Offset Delay (ps)", self.load_length)

        self.cal_through_box = QtWidgets.QGroupBox("Through")
        cal_through_form = QtWidgets.QFormLayout(self.cal_through_box)
        self.cal_through_box.setDisabled(True)
        self.through_length = QtWidgets.QLineEdit("0")
        self.through_length.setMinimumHeight(20)
        cal_through_form.addRow("Offset Delay (ps)", self.through_length)

        cal_standard_layout.addWidget(self.cal_short_box)
        cal_standard_layout.addWidget(self.cal_open_box)
        cal_standard_layout.addWidget(self.cal_load_box)
        cal_standard_layout.addWidget(self.cal_through_box)

        self.cal_standard_save_box = QtWidgets.QGroupBox("Saved settings")
        cal_standard_save_layout = QtWidgets.QVBoxLayout(
            self.cal_standard_save_box
        )
        self.cal_standard_save_box.setDisabled(True)

        self.cal_standard_save_selector = QtWidgets.QComboBox()
        self.cal_standard_save_selector.setMinimumHeight(20)
        self.listCalibrationStandards()
        cal_standard_save_layout.addWidget(self.cal_standard_save_selector)
        cal_standard_save_button_layout = QtWidgets.QHBoxLayout()
        btn_save_standard = QtWidgets.QPushButton("Save")
        btn_save_standard.setMinimumHeight(20)
        btn_save_standard.clicked.connect(self.saveCalibrationStandard)
        btn_load_standard = QtWidgets.QPushButton("Load")
        btn_load_standard.setMinimumHeight(20)
        btn_load_standard.clicked.connect(self.loadCalibrationStandard)
        btn_delete_standard = QtWidgets.QPushButton("Delete")
        btn_delete_standard.setMinimumHeight(20)
        btn_delete_standard.clicked.connect(self.deleteCalibrationStandard)
        cal_standard_save_button_layout.addWidget(btn_load_standard)
        cal_standard_save_button_layout.addWidget(btn_save_standard)
        cal_standard_save_button_layout.addWidget(btn_delete_standard)
        cal_standard_save_layout.addLayout(cal_standard_save_button_layout)

        cal_standard_layout.addWidget(self.cal_standard_save_box)
        right_layout.addWidget(cal_standard_box)
        right_layout.addWidget(self.calkit_box())
        left_layout.addWidget(self.health_box())
        left_layout.addWidget(self.virtual_box())
        self.app.communicate.data_available.connect(self.auto_health)
        self.open_touchstone = None
        self.short_touchstone = None
        self.load_touchstone = None

    def checkExpertUser(self):
        if not self.app.settings.value("ExpertCalibrationUser", False, bool):
            response = QtWidgets.QMessageBox.question(
                self,
                "Are you sure?",
                (
                    "Use of the manual calibration buttons is non-intuitive"
                    " and primarily suited for users with very specialized"
                    " needs. The buttons do not sweep for you nor do"
                    " they interact with the NanoVNA calibration.\n\n"
                    "If you are trying to do a calibration of the NanoVNA, do"
                    " so on the device itself instead. If you are trying to do"
                    ' a calibration with NanoVNA-Saver, use the "Calibration'
                    ' assistant" if possible.\n\n'
                    "If you are certain you know what you are doing, click"
                    " Yes."
                ),
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            if response == QtWidgets.QMessageBox.StandardButton.Yes:
                self.app.settings.setValue("ExpertCalibrationUser", True)
                return True
            return False
        return True

    def cal_save(self, name: str):
        # Standards must be captured uncorrected: use the raw sweep data
        # (no calibration, fixture or smoothing) when available.
        worker = self.app.worker
        if worker.has_raw_data() and len(worker.raw) == len(self.app.data.s11):
            s11, s21 = worker.rawData11, worker.rawData21
        else:
            s11, s21 = self.app.data.s11, self.app.data.s21
        if name in {"through", "isolation"}:
            self.app.calibration.insert(name, s21)
        else:
            self.app.calibration.insert(name, s11)
        self.cal_label[name].setText(_format_cal_label(len(s11)))

    # Virtual device support

    def virtual_box(self) -> QtWidgets.QGroupBox:
        self._virtual_group = QtWidgets.QGroupBox("Virtual device: connected")
        layout = QtWidgets.QHBoxLayout(self._virtual_group)
        self.virtual_standard = QtWidgets.QComboBox()
        for name in STANDARDS:
            self.virtual_standard.addItem(name, name)
        self.virtual_standard.currentIndexChanged.connect(
            lambda: self._virtual_connect(self.virtual_standard.currentData())
        )
        layout.addWidget(self.virtual_standard)
        layout.addWidget(
            QtWidgets.QLabel("(the assistant switches automatically)")
        )
        self._virtual_group.setVisible(False)
        return self._virtual_group

    def _virtual_connect(self, standard: str) -> None:
        vna = self.app.vna
        if isinstance(vna, VirtualVNA):
            vna.set_standard(standard)
            self.virtual_standard.blockSignals(True)
            self.virtual_standard.setCurrentIndex(STANDARDS.index(standard))
            self.virtual_standard.blockSignals(False)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._virtual_group.setVisible(isinstance(self.app.vna, VirtualVNA))
        self.update_health()

    # Cal kit library

    def calkit_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Calibration kit library")
        layout = QtWidgets.QVBoxLayout(box)
        self.calkit_library = CalKitLibrary()
        self.calkit_selector = QtWidgets.QComboBox()
        layout.addWidget(self.calkit_selector)
        buttons = QtWidgets.QGridLayout()
        for i, (label, slot) in enumerate(
            (
                ("Use kit", self.use_calkit),
                ("Save fields as kit ...", self.save_calkit),
                ("Delete", self.delete_calkit),
                ("Import ...", self.import_calkit),
                ("Export ...", self.export_calkit),
            )
        ):
            btn = QtWidgets.QPushButton(label)
            btn.clicked.connect(slot)
            buttons.addWidget(btn, i // 3, i % 3)
        layout.addLayout(buttons)
        self.calkit_info = QtWidgets.QLabel()
        self.calkit_info.setWordWrap(True)
        layout.addWidget(self.calkit_info)
        self.calkit_selector.currentIndexChanged.connect(self._calkit_selected)
        self.refresh_calkits()
        return box

    def refresh_calkits(self, select: str = "") -> None:
        self.calkit_selector.blockSignals(True)
        self.calkit_selector.clear()
        for name in self.calkit_library.names():
            self.calkit_selector.addItem(name)
        if select:
            self.calkit_selector.setCurrentText(select)
        self.calkit_selector.blockSignals(False)
        self._calkit_selected()

    def _calkit_selected(self) -> None:
        name = self.calkit_selector.currentText()
        try:
            kit = self.calkit_library.get(name)
        except KeyError:
            self.calkit_info.setText("")
            return
        origin = "builtin" if self.calkit_library.is_builtin(name) else "user"
        self.calkit_info.setText(f"{kit.description} ({origin})".strip())

    def _kit_to_fields(self, kit: CalKit) -> None:
        if kit.ideal:
            self.use_ideal_values.setChecked(True)
            self.calStandardChanged(self.use_ideal_values)
            return
        self.use_coefficients.setChecked(True)
        self.calStandardChanged(self.use_coefficients)
        for field, value, scale in (
            (self.short_l0_input, kit.short_l0, 1e12),
            (self.short_l1_input, kit.short_l1, 1e24),
            (self.short_l2_input, kit.short_l2, 1e33),
            (self.short_l3_input, kit.short_l3, 1e42),
            (self.short_length, kit.short_delay, 1e12),
            (self.open_c0_input, kit.open_c0, 1e15),
            (self.open_c1_input, kit.open_c1, 1e27),
            (self.open_c2_input, kit.open_c2, 1e36),
            (self.open_c3_input, kit.open_c3, 1e45),
            (self.open_length, kit.open_delay, 1e12),
            (self.load_resistance, kit.load_r, 1.0),
            (self.load_inductance, kit.load_l, 1e12),
            (self.load_capacitance, kit.load_c, 1e15),
            (self.load_length, kit.load_delay, 1e12),
            (self.through_length, kit.through_delay, 1e12),
        ):
            field.setText(f"{value * scale:.6g}")

    def _kit_from_fields(self, name: str) -> CalKit:
        return CalKit(
            name=name,
            ideal=self.use_ideal_values.isChecked(),
            short_l0=getFloatValue(self.short_l0_input.text()) / 1e12,
            short_l1=getFloatValue(self.short_l1_input.text()) / 1e24,
            short_l2=getFloatValue(self.short_l2_input.text()) / 1e33,
            short_l3=getFloatValue(self.short_l3_input.text()) / 1e42,
            short_delay=getFloatValue(self.short_length.text()) / 1e12,
            open_c0=getFloatValue(self.open_c0_input.text()) / 1e15,
            open_c1=getFloatValue(self.open_c1_input.text()) / 1e27,
            open_c2=getFloatValue(self.open_c2_input.text()) / 1e36,
            open_c3=getFloatValue(self.open_c3_input.text()) / 1e45,
            open_delay=getFloatValue(self.open_length.text()) / 1e12,
            load_r=getFloatValue(self.load_resistance.text()) or 50.0,
            load_l=getFloatValue(self.load_inductance.text()) / 1e12,
            load_c=getFloatValue(self.load_capacitance.text()) / 1e15,
            load_delay=getFloatValue(self.load_length.text()) / 1e12,
            through_delay=getFloatValue(self.through_length.text()) / 1e12,
        )

    def use_calkit(self) -> None:
        try:
            kit = self.calkit_library.get(self.calkit_selector.currentText())
        except KeyError:
            return
        self._kit_to_fields(kit)
        self.calkit_info.setText(
            f"Fields set from {kit.name}. Press Apply to recalculate."
        )

    def save_calkit(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save cal kit", "Kit name:"
        )
        if not ok or not name.strip():
            return
        try:
            self.calkit_library.save(self._kit_from_fields(name.strip()))
        except ValueError as exc:
            self.app.showError(str(exc))
            return
        self.refresh_calkits(name.strip())

    def delete_calkit(self) -> None:
        name = self.calkit_selector.currentText()
        try:
            self.calkit_library.delete(name)
        except ValueError as exc:
            self.app.showError(str(exc))
            return
        self.refresh_calkits()

    def import_calkit(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import cal kit", "", "Cal kit (*.json)"
        )
        if not filename:
            return
        try:
            kit = CalKit.load(Path(filename))
            self.calkit_library.save(kit)
        except (ValueError, TypeError, OSError) as exc:
            self.app.showError(f"Unable to import: {exc}")
            return
        self.refresh_calkits(kit.name)

    def export_calkit(self) -> None:
        try:
            kit = self.calkit_library.get(self.calkit_selector.currentText())
        except KeyError:
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export cal kit", f"{kit.name}.json", "Cal kit (*.json)"
        )
        if filename:
            kit.save(Path(filename))

    # Calibration health

    def health_box(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Calibration health")
        layout = QtWidgets.QVBoxLayout(box)
        self.health_label = QtWidgets.QLabel()
        self.health_label.setWordWrap(True)
        self.health_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(self.health_label)
        row = QtWidgets.QHBoxLayout()
        btn = QtWidgets.QPushButton("Check")
        btn.clicked.connect(self.update_health)
        row.addWidget(btn)
        for std in ("load", "open", "short"):
            b = QtWidgets.QPushButton(f"Verify {std}")
            b.setToolTip(
                f"Connect a {std} standard, sweep, then press to verify the"
                " corrected measurement."
            )
            b.clicked.connect(lambda _=False, n=std: self.verify(n))
            row.addWidget(b)
        layout.addLayout(row)
        return box

    def update_health(self) -> None:
        freq = np.array([d.freq for d in self.app.data.s11], dtype=float)
        report = check_calibration(self.app.calibration, freq)
        color = ("#16a34a", "#2563eb", "#d97706", "#dc2626")[report.severity]
        text = "<br>".join(
            html.escape(x) for x in report.summary().splitlines()
        )
        self.health_label.setText(f'<span style="color:{color}">{text}</span>')

    def auto_health(self) -> None:
        if self.isVisible():
            self.update_health()

    def verify(self, standard: str) -> None:
        s11 = np.array([d.z for d in self.app.data.s11])
        result = verify_standard(s11, standard)
        color = "#16a34a" if result.passed else "#dc2626"
        self.health_label.setText(
            f'<span style="color:{color}">{html.escape(result.message)}</span>'
        )

    def manual_save(self, name: str):
        if self.checkExpertUser():
            self.cal_save(name)

    def listCalibrationStandards(self):
        self.cal_standard_save_selector.clear()
        num_standards = self.app.settings.beginReadArray("CalibrationStandards")
        for i in range(num_standards):
            self.app.settings.setArrayIndex(i)
            name = self.app.settings.value("Name", defaultValue="INVALID NAME")
            self.cal_standard_save_selector.addItem(name, userData=i)
        self.app.settings.endArray()
        self.cal_standard_save_selector.addItem("New", userData=-1)
        self.cal_standard_save_selector.setCurrentText("New")

    def saveCalibrationStandard(self):
        num_standards = self.app.settings.beginReadArray("CalibrationStandards")
        self.app.settings.endArray()

        if self.cal_standard_save_selector.currentData() == -1:
            # New cal standard
            # Get a name
            name, selected = QtWidgets.QInputDialog.getText(
                self, "Calibration standard name", "Enter name to save as"
            )
            if not selected or not name:
                return
            write_num = num_standards
            num_standards += 1
        else:
            write_num = self.cal_standard_save_selector.currentData()
            name = self.cal_standard_save_selector.currentText()

        self.app.settings.beginWriteArray("CalibrationStandards", num_standards)
        self.app.settings.setArrayIndex(write_num)
        self.app.settings.setValue("Name", name)

        self.app.settings.setValue("ShortL0", self.short_l0_input.text())
        self.app.settings.setValue("ShortL1", self.short_l1_input.text())
        self.app.settings.setValue("ShortL2", self.short_l2_input.text())
        self.app.settings.setValue("ShortL3", self.short_l3_input.text())
        self.app.settings.setValue("ShortDelay", self.short_length.text())

        self.app.settings.setValue("OpenC0", self.open_c0_input.text())
        self.app.settings.setValue("OpenC1", self.open_c1_input.text())
        self.app.settings.setValue("OpenC2", self.open_c2_input.text())
        self.app.settings.setValue("OpenC3", self.open_c3_input.text())
        self.app.settings.setValue("OpenDelay", self.open_length.text())

        self.app.settings.setValue("LoadR", self.load_resistance.text())
        self.app.settings.setValue("LoadL", self.load_inductance.text())
        self.app.settings.setValue("LoadC", self.load_capacitance.text())
        self.app.settings.setValue("LoadDelay", self.load_length.text())

        self.app.settings.setValue("ThroughDelay", self.through_length.text())

        self.app.settings.endArray()
        self.app.settings.sync()
        self.listCalibrationStandards()
        self.cal_standard_save_selector.setCurrentText(name)

    def loadCalibrationStandard(self):
        if self.cal_standard_save_selector.currentData() == -1:
            return
        read_num = self.cal_standard_save_selector.currentData()
        logger.debug("Loading calibration no %d", read_num)
        self.app.settings.beginReadArray("CalibrationStandards")
        self.app.settings.setArrayIndex(read_num)

        name = self.app.settings.value("Name")
        logger.info("Loading: %s", name)

        self.short_l0_input.setText(str(self.app.settings.value("ShortL0", 0)))
        self.short_l1_input.setText(str(self.app.settings.value("ShortL1", 0)))
        self.short_l2_input.setText(str(self.app.settings.value("ShortL2", 0)))
        self.short_l3_input.setText(str(self.app.settings.value("ShortL3", 0)))
        self.short_length.setText(str(self.app.settings.value("ShortDelay", 0)))

        self.open_c0_input.setText(str(self.app.settings.value("OpenC0", 50)))
        self.open_c1_input.setText(str(self.app.settings.value("OpenC1", 0)))
        self.open_c2_input.setText(str(self.app.settings.value("OpenC2", 0)))
        self.open_c3_input.setText(str(self.app.settings.value("OpenC3", 0)))
        self.open_length.setText(str(self.app.settings.value("OpenDelay", 0)))

        self.load_resistance.setText(str(self.app.settings.value("LoadR", 50)))
        self.load_inductance.setText(str(self.app.settings.value("LoadL", 0)))
        self.load_capacitance.setText(str(self.app.settings.value("LoadC", 0)))
        self.load_length.setText(str(self.app.settings.value("LoadDelay", 0)))

        self.through_length.setText(
            str(self.app.settings.value("ThroughDelay", 0))
        )

        self.app.settings.endArray()

    def deleteCalibrationStandard(self):
        if self.cal_standard_save_selector.currentData() == -1:
            return
        delete_num = self.cal_standard_save_selector.currentData()
        logger.debug("Deleting calibration no %d", delete_num)
        num_standards = self.app.settings.beginReadArray("CalibrationStandards")
        self.app.settings.endArray()

        logger.debug("Number of standards known: %d", num_standards)

        if num_standards == 1:
            logger.debug("Only one standard known")
            self.app.settings.beginWriteArray("CalibrationStandards", 0)
            self.app.settings.endArray()
        else:
            names = []

            shortL0 = []
            shortL1 = []
            shortL2 = []
            shortL3 = []
            shortDelay = []

            openC0 = []
            openC1 = []
            openC2 = []
            openC3 = []
            openDelay = []

            loadR = []
            loadL = []
            loadC = []
            loadDelay = []

            throughDelay = []

            self.app.settings.beginReadArray("CalibrationStandards")
            for i in range(num_standards):
                if i == delete_num:
                    continue
                self.app.settings.setArrayIndex(i)
                names.append(self.app.settings.value("Name"))

                shortL0.append(self.app.settings.value("ShortL0"))
                shortL1.append(self.app.settings.value("ShortL1"))
                shortL2.append(self.app.settings.value("ShortL2"))
                shortL3.append(self.app.settings.value("ShortL3"))
                shortDelay.append(self.app.settings.value("ShortDelay"))

                openC0.append(self.app.settings.value("OpenC0"))
                openC1.append(self.app.settings.value("OpenC1"))
                openC2.append(self.app.settings.value("OpenC2"))
                openC3.append(self.app.settings.value("OpenC3"))
                openDelay.append(self.app.settings.value("OpenDelay"))

                loadR.append(self.app.settings.value("LoadR"))
                loadL.append(self.app.settings.value("LoadL"))
                loadC.append(self.app.settings.value("LoadC"))
                loadDelay.append(self.app.settings.value("LoadDelay"))

                throughDelay.append(self.app.settings.value("ThroughDelay"))
            self.app.settings.endArray()

            self.app.settings.beginWriteArray("CalibrationStandards")
            self.app.settings.remove("")
            self.app.settings.endArray()

            self.app.settings.beginWriteArray(
                "CalibrationStandards", len(names)
            )
            for i, name in enumerate(names):
                self.app.settings.setArrayIndex(i)
                self.app.settings.setValue("Name", name)

                self.app.settings.setValue("ShortL0", shortL0[i])
                self.app.settings.setValue("ShortL1", shortL1[i])
                self.app.settings.setValue("ShortL2", shortL2[i])
                self.app.settings.setValue("ShortL3", shortL3[i])
                self.app.settings.setValue("ShortDelay", shortDelay[i])

                self.app.settings.setValue("OpenC0", openC0[i])
                self.app.settings.setValue("OpenC1", openC1[i])
                self.app.settings.setValue("OpenC2", openC2[i])
                self.app.settings.setValue("OpenC3", openC3[i])
                self.app.settings.setValue("OpenDelay", openDelay[i])

                self.app.settings.setValue("LoadR", loadR[i])
                self.app.settings.setValue("LoadL", loadL[i])
                self.app.settings.setValue("LoadC", loadC[i])
                self.app.settings.setValue("LoadDelay", loadDelay[i])

                self.app.settings.setValue("ThroughDelay", throughDelay[i])
            self.app.settings.endArray()

        self.app.settings.sync()
        self.listCalibrationStandards()

    def reset(self):
        self.app.calibration = Calibration()
        for label in self.cal_label.values():
            label.setText("Uncalibrated")
        self.calibration_status_label.setText("Device calibration")
        self.calibration_source_label.setText("Device")
        self.notes_textedit.clear()
        self.short_touchstone = None
        self.open_touchstone = None
        self.load_touchstone = None

        if self.app.worker.has_raw_data():
            # no calibration any more: show the raw data
            self.app.worker.reprocess()
        self.app.sweep_control.update_text()

    def setOffsetDelay(self, value: float):
        logger.debug("New offset delay value: %f ps", value)
        self.app.worker.offsetDelay = value / 1e12
        if self.app.worker.has_raw_data():
            logger.debug("Applying new offset to existing sweep data.")
            self.app.worker.reprocess()

    def calculate(self):
        cal_element = self.app.calibration.cal_element
        if self.app.sweep_control.btn_stop.isEnabled():
            self.app.showError(
                "Unable to apply calibration while a sweep is running."
                " Please stop the sweep and try again."
            )
            return

        if not self.app.calibration.isValid1Port():
            self.app.showError(
                "Not enough data to apply calibration."
                " Please complete SOL calibration and try again."
            )
            return

        cal_element.short_state = "IDEAL"
        cal_element.open_state = "IDEAL"
        cal_element.load_state = "IDEAL"
        cal_element.through_is_ideal = True

        # TODO: all ideal or not?
        if self.radio_group.checkedButton() == self.use_coefficients:
            cal_element.short_state = "COEFF"
            cal_element.open_state = "COEFF"
            cal_element.load_state = "COEFF"
            cal_element.through_is_ideal = False

            # We are using custom calibration standards

            cal_element.short_l0 = (
                getFloatValue(self.short_l0_input.text()) / 1.0e12
            )
            cal_element.short_l1 = (
                getFloatValue(self.short_l1_input.text()) / 1.0e24
            )
            cal_element.short_l2 = (
                getFloatValue(self.short_l2_input.text()) / 1.0e33
            )
            cal_element.short_l3 = (
                getFloatValue(self.short_l3_input.text()) / 1.0e42
            )
            cal_element.short_length = (
                getFloatValue(self.short_length.text()) / 1.0e12
            )

            cal_element.open_c0 = (
                getFloatValue(self.open_c0_input.text()) / 1.0e15
            )
            cal_element.open_c1 = (
                getFloatValue(self.open_c1_input.text()) / 1.0e27
            )
            cal_element.open_c2 = (
                getFloatValue(self.open_c2_input.text()) / 1.0e36
            )
            cal_element.open_c3 = (
                getFloatValue(self.open_c3_input.text()) / 1.0e45
            )
            cal_element.open_length = (
                getFloatValue(self.open_length.text()) / 1.0e12
            )

            cal_element.load_r = getFloatValue(self.load_resistance.text())
            cal_element.load_l = (
                getFloatValue(self.load_inductance.text()) / 1.0e12
            )
            cal_element.load_c = (
                getFloatValue(self.load_capacitance.text()) / 1.0e15
            )
            cal_element.load_length = (
                getFloatValue(self.load_length.text()) / 1.0e12
            )

            cal_element.through_length = (
                getFloatValue(self.through_length.text()) / 1.0e12
            )
        elif self.radio_group.checkedButton() == self.use_s1p_files:
            if self.short_touchstone is not None:
                cal_element.short_state = "FILE"
                cal_element.short_touchstone = self.short_touchstone
            if self.open_touchstone is not None:
                cal_element.open_state = "FILE"
                cal_element.open_touchstone = self.open_touchstone
            if self.load_touchstone is not None:
                cal_element.load_state = "FILE"
                cal_element.load_touchstone = self.load_touchstone
            cal_element.through_is_ideal = False
            cal_element.through_length = (
                getFloatValue(self.through_length.text()) / 1.0e12
            )

        logger.debug("Attempting calibration calculation.")
        try:
            self.app.calibration.calc_corrections()
            self.calibration_status_label.setText(
                _format_cal_label(
                    self.app.calibration.size(), "Application calibration"
                )
            )
            if self.use_ideal_values.isChecked():
                self.calibration_source_label.setText(
                    self.app.calibration.source
                )
            else:
                self.calibration_source_label.setText(
                    f"{self.app.calibration.source} (Standards: Custom)"
                )

            if self.app.worker.has_raw_data():
                logger.debug("Applying calibration to existing sweep data.")
                self.app.worker.reprocess()
            self.update_health()

        except ValueError as e:
            # showError here hides the calibration window,
            # so we need to pop up our own
            self.calibration_status_label.setText(
                "Applying calibration failed."
            )
            self.calibration_source_label.setText(self.app.calibration.source)
            self.app.showError(
                f"{e} Please complete SOL calibration and try again."
            )
            self.reset()
            return
        self.app.sweep_control.update_text()

    def loadCalibration(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Calibration Files (*.cal);;All files (*.*)"
        )
        if filename:
            self.app.calibration.load(filename)
        if not self.app.calibration.isValid1Port():
            return
        for i, name in enumerate(
            ("short", "open", "load", "through", "isolation", "thrurefl")
        ):
            self.cal_label[name].setText(
                _format_cal_label(
                    self.app.calibration.data_size(name), "Loaded"
                )
            )
            if i == 2 and not self.app.calibration.isValid2Port():
                break
        self.calculate()
        self.notes_textedit.clear()
        for note in self.app.calibration.notes:
            self.notes_textedit.appendPlainText(note)
        self.app.settings.setValue("CalibrationFile", filename)
        self.app.sweep_control.update_text()

    def saveCalibration(self):
        if not self.app.calibration.isCalculated:
            logger.debug("Attempted to save an uncalculated calibration.")
            self.app.showError("Cannot save an unapplied calibration state.")
            return
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("cal")
        filedialog.setNameFilter("Calibration Files (*.cal);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        if filedialog.exec():
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if not filename:
            logger.debug("No file name selected.")
            return
        self.app.calibration.notes = (
            self.notes_textedit.toPlainText().splitlines()
        )
        try:
            self.app.calibration.save(filename)
            self.app.settings.setValue("CalibrationFile", filename)
        except IOError:
            logger.error("Calibration save failed!")
            self.app.showError("Calibration save failed.")

    def calStandardChanged(self, button):
        if button == self.use_ideal_values:
            self.cal_short_box.setDisabled(True)
            self.cal_open_box.setDisabled(True)
            self.cal_load_box.setDisabled(True)
            self.cal_through_box.setDisabled(True)
            self.cal_standard_save_box.setDisabled(True)
            self.file_button_short.setDisabled(True)
            self.file_button_open.setDisabled(True)
            self.file_button_load.setDisabled(True)
        elif button == self.use_s1p_files:
            self.cal_short_box.setDisabled(True)
            self.cal_open_box.setDisabled(True)
            self.cal_load_box.setDisabled(True)
            self.cal_through_box.setDisabled(False)
            self.cal_standard_save_box.setDisabled(True)
            self.file_button_short.setDisabled(False)
            self.file_button_open.setDisabled(False)
            self.file_button_load.setDisabled(False)
        elif button == self.use_coefficients:
            self.cal_short_box.setDisabled(False)
            self.cal_open_box.setDisabled(False)
            self.cal_load_box.setDisabled(False)
            self.cal_through_box.setDisabled(False)
            self.cal_standard_save_box.setDisabled(False)
            self.file_button_short.setDisabled(True)
            self.file_button_open.setDisabled(True)
            self.file_button_load.setDisabled(True)

    def automaticCalibration(self):
        self.btn_automatic.setDisabled(True)
        introduction = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Information,
            "Calibration assistant",
            (
                "This calibration assistant will help you create a calibration"
                " in the NanoVNASaver application. It will sweep the"
                " standards for you and guide you through the process.<br><br>"
                "Before starting, ensure you have Open, Short and Load"
                " standards available and the cables you wish to have"
                " calibrated connected to the device.<br><br>"
                'If you want a 2-port calibration, also have a "through"'
                " connector on hand.<br><br>"
                "<b>The best results are achieved by having the NanoVNA"
                " calibrated on-device for the full span of interest and stored"
                " in save slot 0 before starting.</b><br><br>"
                "Once you are ready to proceed, press Ok."
            ),
            QtWidgets.QMessageBox.StandardButton.Ok
            | QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        response = introduction.exec()
        if response != QtWidgets.QMessageBox.StandardButton.Ok:
            self.btn_automatic.setDisabled(False)
            return
        logger.info("Starting automatic calibration assistant.")
        if not self.app.vna.connected():
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "NanoVNA not connected",
                (
                    "Please ensure the NanoVNA is connected before attempting"
                    " calibration."
                ),
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        if self.app.sweep.properties.mode == SweepMode.CONTINOUS:
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "Continuous sweep enabled",
                (
                    "Please disable continuous sweeping before attempting"
                    " calibration."
                ),
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        short_step = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Information,
            "Calibrate short",
            (
                'Please connect the "short" standard to port 0 of the'
                " NanoVNA.\n\n"
                "Press Ok when you are ready to continue."
            ),
            QtWidgets.QMessageBox.StandardButton.Ok
            | QtWidgets.QMessageBox.StandardButton.Cancel,
        )

        response = short_step.exec()
        if response != QtWidgets.QMessageBox.StandardButton.Ok:
            self.btn_automatic.setDisabled(False)
            return
        self.reset()
        self.app.calibration.source = "Calibration assistant"
        self.next_step = 0
        self.app.worker.signals.finished.connect(self.automaticCalibrationStep)
        self._virtual_connect("short")
        self.app.sweep_start()
        return

    def automaticCalibrationStep(self):
        if self.next_step == -1:
            self.app.worker.signals.finished.disconnect(
                self.automaticCalibrationStep
            )
            return

        if self.next_step == 0:
            # Short
            self.cal_save("short")
            self.next_step = 1

            open_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "Calibrate open",
                (
                    'Please connect the "open" standard to port 0 of the'
                    " NanoVNA.\n\n"
                    "Either use a supplied open, or leave the end of the"
                    " cable unconnected if desired.\n\n"
                    "Press Ok when you are ready to continue."
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = open_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.next_step = -1
                self.btn_automatic.setDisabled(False)
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self._virtual_connect("open")
            self.app.sweep_start()
            return

        if self.next_step == 1:
            # Open
            self.cal_save("open")
            self.next_step = 2
            load_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "Calibrate load",
                (
                    'Please connect the "load" standard to port 0 of the'
                    " NanoVNA.\n\n"
                    "Press Ok when you are ready to continue."
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = load_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self._virtual_connect("load")
            self.app.sweep_start()
            return

        if self.next_step == 2:
            # Load
            self.cal_save("load")
            self.next_step = 3
            continue_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "1-port calibration complete",
                (
                    "The required steps for a 1-port calibration are now"
                    " complete.\n\n"
                    "If you wish to continue and perform a 2-port calibration,"
                    ' press "Yes". To apply the 1-port calibration and stop,'
                    ' press "Apply"'
                ),
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.Apply
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = continue_step.exec()
            if response == QtWidgets.QMessageBox.StandardButton.Apply:
                self._virtual_connect("dut")
                self.calculate()
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                self.btn_automatic.setDisabled(False)
                return
            if response != QtWidgets.QMessageBox.StandardButton.Yes:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return

            isolation_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "Calibrate isolation",
                (
                    'Please connect the "load" standard to port 1 of the'
                    " NanoVNA.\n\n"
                    "If available, also connect a load standard to"
                    " port 0.\n\n"
                    "Press Ok when you are ready to continue."
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = isolation_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self._virtual_connect("isolation")
            self.app.sweep_start()
            return

        if self.next_step == 3:
            # Isolation
            self.cal_save("isolation")
            self.next_step = 4
            through_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "Calibrate through",
                (
                    'Please connect the "through" standard between'
                    " port 0 and port 1 of the NanoVNA.\n\n"
                    "Press Ok when you are ready to continue."
                ),
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = through_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Ok:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return
            self._virtual_connect("thru")
            self.app.sweep_start()
            return

        if self.next_step == 4:
            # Done
            self.cal_save("thrurefl")
            self.cal_save("through")
            apply_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Information,
                "Calibrate complete",
                (
                    "The calibration process is now complete. Press"
                    ' "Apply" to apply the calibration parameters.'
                ),
                QtWidgets.QMessageBox.StandardButton.Apply
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )

            response = apply_step.exec()
            if response != QtWidgets.QMessageBox.StandardButton.Apply:
                self.btn_automatic.setDisabled(False)
                self.next_step = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep
                )
                return

            self._virtual_connect("dut")
            self.calculate()
            self.btn_automatic.setDisabled(False)
            self.next_step = -1
            self.app.worker.signals.finished.disconnect(
                self.automaticCalibrationStep
            )
            return

    def select_file_open(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Open S1P", "", "Touchstone Files (*.s1p)"
        )
        if filename != "":
            self.open_touchstone = Touchstone(filename)
            self.open_touchstone.load()

    def select_file_short(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Short S1P", "", "Touchstone Files (*.s1p)"
        )
        if filename != "":
            self.short_touchstone = Touchstone(filename)
            self.short_touchstone.load()

    def select_file_load(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Load S1P", "", "Touchstone Files (*.s1p)"
        )
        if filename != "":
            self.load_touchstone = Touchstone(filename)
            self.load_touchstone.load()
