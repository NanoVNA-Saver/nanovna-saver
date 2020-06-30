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
from functools import partial

from PyQt5 import QtWidgets, QtCore

from NanoVNASaver.Calibration import Calibration

logger = logging.getLogger(__name__)


def _format_cal_label(size: int, prefix: str = "Set") -> str:
    return f"{prefix} ({size} points)"


class CalibrationWindow(QtWidgets.QWidget):
    nextStep = -1

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setMinimumWidth(450)
        self.setWindowTitle("Calibration")
        self.setWindowIcon(self.app.icon)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        top_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()
        right_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout)
        self.setLayout(top_layout)

        calibration_status_group = QtWidgets.QGroupBox("Active calibration")
        calibration_status_layout = QtWidgets.QFormLayout()
        self.calibration_status_label = QtWidgets.QLabel("Device calibration")
        self.calibration_source_label = QtWidgets.QLabel("NanoVNA")
        calibration_status_layout.addRow("Calibration:", self.calibration_status_label)
        calibration_status_layout.addRow("Source:", self.calibration_source_label)
        calibration_status_group.setLayout(calibration_status_layout)
        left_layout.addWidget(calibration_status_group)

        calibration_control_group = QtWidgets.QGroupBox("Calibrate")
        calibration_control_layout = QtWidgets.QFormLayout(calibration_control_group)
        cal_btn = {}
        self.cal_label = {}
        for label_name in Calibration.CAL_NAMES:
            self.cal_label[label_name] = QtWidgets.QLabel("Uncalibrated")
            cal_btn[label_name] = QtWidgets.QPushButton(
                label_name.capitalize())
            cal_btn[label_name].clicked.connect(partial(self.manual_save, label_name))
            calibration_control_layout.addRow(
                cal_btn[label_name], self.cal_label[label_name])

        self.input_offset_delay = QtWidgets.QDoubleSpinBox()
        self.input_offset_delay.setValue(0)
        self.input_offset_delay.setSuffix(" ps")
        self.input_offset_delay.setAlignment(QtCore.Qt.AlignRight)
        self.input_offset_delay.valueChanged.connect(self.setOffsetDelay)
        self.input_offset_delay.setRange(-10e6, 10e6)

        calibration_control_layout.addRow(QtWidgets.QLabel(""))
        calibration_control_layout.addRow("Offset delay", self.input_offset_delay)

        self.btn_automatic = QtWidgets.QPushButton("Calibration assistant")
        calibration_control_layout.addRow(self.btn_automatic)
        self.btn_automatic.clicked.connect(self.automaticCalibration)

        apply_reset_layout = QtWidgets.QHBoxLayout()

        btn_apply = QtWidgets.QPushButton("Apply")
        btn_apply.clicked.connect(self.calculate)

        btn_reset = QtWidgets.QPushButton("Reset")
        btn_reset.clicked.connect(self.reset)

        apply_reset_layout.addWidget(btn_apply)
        apply_reset_layout.addWidget(btn_reset)

        calibration_control_layout.addRow(apply_reset_layout)

        left_layout.addWidget(calibration_control_group)

        calibration_notes_group = QtWidgets.QGroupBox("Notes")
        calibration_notes_layout = QtWidgets.QVBoxLayout(calibration_notes_group)
        self.notes_textedit = QtWidgets.QPlainTextEdit()
        calibration_notes_layout.addWidget(self.notes_textedit)

        left_layout.addWidget(calibration_notes_group)

        file_box = QtWidgets.QGroupBox("Files")
        file_layout = QtWidgets.QFormLayout(file_box)
        btn_save_file = QtWidgets.QPushButton("Save calibration")
        btn_save_file.clicked.connect(lambda: self.saveCalibration())
        btn_load_file = QtWidgets.QPushButton("Load calibration")
        btn_load_file.clicked.connect(lambda: self.loadCalibration())

        save_load_layout = QtWidgets.QHBoxLayout()
        save_load_layout.addWidget(btn_save_file)
        save_load_layout.addWidget(btn_load_file)

        file_layout.addRow(save_load_layout)

        left_layout.addWidget(file_box)

        cal_standard_box = QtWidgets.QGroupBox("Calibration standards")
        cal_standard_layout = QtWidgets.QFormLayout(cal_standard_box)
        self.use_ideal_values = QtWidgets.QCheckBox("Use ideal values")
        self.use_ideal_values.setChecked(True)
        self.use_ideal_values.stateChanged.connect(self.idealCheckboxChanged)
        cal_standard_layout.addRow(self.use_ideal_values)

        self.cal_short_box = QtWidgets.QGroupBox("Short")
        cal_short_form = QtWidgets.QFormLayout(self.cal_short_box)
        self.cal_short_box.setDisabled(True)
        self.short_l0_input = QtWidgets.QLineEdit("0")
        self.short_l1_input = QtWidgets.QLineEdit("0")
        self.short_l2_input = QtWidgets.QLineEdit("0")
        self.short_l3_input = QtWidgets.QLineEdit("0")
        self.short_length = QtWidgets.QLineEdit("0")
        cal_short_form.addRow("L0 (H(e-12))", self.short_l0_input)
        cal_short_form.addRow("L1 (H(e-24))", self.short_l1_input)
        cal_short_form.addRow("L2 (H(e-33))", self.short_l2_input)
        cal_short_form.addRow("L3 (H(e-42))", self.short_l3_input)
        cal_short_form.addRow("Offset Delay (ps)", self.short_length)

        self.cal_open_box = QtWidgets.QGroupBox("Open")
        cal_open_form = QtWidgets.QFormLayout(self.cal_open_box)
        self.cal_open_box.setDisabled(True)
        self.open_c0_input = QtWidgets.QLineEdit("50")
        self.open_c1_input = QtWidgets.QLineEdit("0")
        self.open_c2_input = QtWidgets.QLineEdit("0")
        self.open_c3_input = QtWidgets.QLineEdit("0")
        self.open_length = QtWidgets.QLineEdit("0")
        cal_open_form.addRow("C0 (F(e-15))", self.open_c0_input)
        cal_open_form.addRow("C1 (F(e-27))", self.open_c1_input)
        cal_open_form.addRow("C2 (F(e-36))", self.open_c2_input)
        cal_open_form.addRow("C3 (F(e-45))", self.open_c3_input)
        cal_open_form.addRow("Offset Delay (ps)", self.open_length)

        self.cal_load_box = QtWidgets.QGroupBox("Load")
        cal_load_form = QtWidgets.QFormLayout(self.cal_load_box)
        self.cal_load_box.setDisabled(True)
        self.load_resistance = QtWidgets.QLineEdit("50")
        self.load_inductance = QtWidgets.QLineEdit("0")
        # self.load_capacitance = QtWidgets.QLineEdit("0")
        # self.load_capacitance.setDisabled(True)  # Not yet implemented
        self.load_length = QtWidgets.QLineEdit("0")
        cal_load_form.addRow("Resistance (\N{OHM SIGN})", self.load_resistance)
        cal_load_form.addRow("Inductance (H(e-12))", self.load_inductance)
        # cal_load_form.addRow("Capacitance (F(e-12))", self.load_capacitance)
        cal_load_form.addRow("Offset Delay (ps)", self.load_length)

        self.cal_through_box = QtWidgets.QGroupBox("Through")
        cal_through_form = QtWidgets.QFormLayout(self.cal_through_box)
        self.cal_through_box.setDisabled(True)
        self.through_length = QtWidgets.QLineEdit("0")
        cal_through_form.addRow("Offset Delay (ps)", self.through_length)

        cal_standard_layout.addWidget(self.cal_short_box)
        cal_standard_layout.addWidget(self.cal_open_box)
        cal_standard_layout.addWidget(self.cal_load_box)
        cal_standard_layout.addWidget(self.cal_through_box)

        self.cal_standard_save_box = QtWidgets.QGroupBox("Saved settings")
        cal_standard_save_layout = QtWidgets.QVBoxLayout(self.cal_standard_save_box)
        self.cal_standard_save_box.setDisabled(True)

        self.cal_standard_save_selector = QtWidgets.QComboBox()
        self.listCalibrationStandards()
        cal_standard_save_layout.addWidget(self.cal_standard_save_selector)
        cal_standard_save_button_layout = QtWidgets.QHBoxLayout()
        btn_save_standard = QtWidgets.QPushButton("Save")
        btn_save_standard.clicked.connect(self.saveCalibrationStandard)
        btn_load_standard = QtWidgets.QPushButton("Load")
        btn_load_standard.clicked.connect(self.loadCalibrationStandard)
        btn_delete_standard = QtWidgets.QPushButton("Delete")
        btn_delete_standard.clicked.connect(self.deleteCalibrationStandard)
        cal_standard_save_button_layout.addWidget(btn_load_standard)
        cal_standard_save_button_layout.addWidget(btn_save_standard)
        cal_standard_save_button_layout.addWidget(btn_delete_standard)
        cal_standard_save_layout.addLayout(cal_standard_save_button_layout)

        cal_standard_layout.addWidget(self.cal_standard_save_box)
        right_layout.addWidget(cal_standard_box)

    def checkExpertUser(self):
        if not self.app.settings.value("ExpertCalibrationUser", False, bool):
            response = QtWidgets.QMessageBox.question(
                self, "Are you sure?",
                "Use of the manual calibration buttons " +
                "is non-intuitive, and primarily suited for users with very " +
                "specialized needs. The buttons do not sweep for you, nor do " +
                "they interact with the NanoVNA calibration.\n\n" +
                "If you are trying to do a calibration of the NanoVNA, do so " +
                "on the device itself instead. If you are trying to do a " +
                "calibration with NanoVNA-Saver, use the Calibration Assistant " +
                "if possible.\n\n" +
                "If you are certain you know what you are doing, click Yes.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel)

            if response == QtWidgets.QMessageBox.Yes:
                self.app.settings.setValue("ExpertCalibrationUser", True)
                return True
            return False
        return True

    def cal_save(self, name: str):
        if name in ("through", "isolation"):
            self.app.calibration.insert(name, self.app.data21)
        else:
            self.app.calibration.insert(name, self.app.data)
        self.cal_label[name].setText(
            _format_cal_label(len(self.app.data)))

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
                self, "Calibration standard name", "Enter name to save as")
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
        # self.app.settings.setValue("LoadC", self.load_capacitance.text())
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
        # self.load_capacitance.setText(str(self.app.settings.value("LoadC", 0)))
        self.load_length.setText(str(self.app.settings.value("LoadDelay", 0)))

        self.through_length.setText(str(self.app.settings.value("ThroughDelay", 0)))

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

            self.app.settings.beginWriteArray("CalibrationStandards", len(names))
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

        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Saving and displaying raw data.")
            self.app.saveData(self.app.worker.rawData11,
                              self.app.worker.rawData21, self.app.sweepSource)
            self.app.worker.signals.updated.emit()

    def setOffsetDelay(self, value: float):
        logger.debug("New offset delay value: %f ps", value)
        self.app.worker.offsetDelay = value / 1e12
        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Applying new offset to existing sweep data.")
            self.app.worker.data11, self.app.worker.data21 = \
                self.app.worker.applyCalibration(
                    self.app.worker.rawData11, self.app.worker.rawData21)
            logger.debug("Saving and displaying corrected data.")
            self.app.saveData(self.app.worker.data11, self.app.worker.data21, self.app.sweepSource)
            self.app.worker.signals.updated.emit()

    def calculate(self):
        if self.app.btnStopSweep.isEnabled():
            # Currently sweeping
            self.app.showError("Unable to apply calibration while a sweep is running. " +
                               "Please stop the sweep and try again.")
            return
        if self.use_ideal_values.isChecked():
            self.app.calibration.useIdealShort = True
            self.app.calibration.useIdealOpen = True
            self.app.calibration.useIdealLoad = True
            self.app.calibration.useIdealThrough = True
        else:
            # We are using custom calibration standards
            try:
                self.app.calibration.shortL0 = self.getFloatValue(
                    self.short_l0_input.text())/10**12
                self.app.calibration.shortL1 = self.getFloatValue(
                    self.short_l1_input.text())/10**24
                self.app.calibration.shortL2 = self.getFloatValue(
                    self.short_l2_input.text())/10**33
                self.app.calibration.shortL3 = self.getFloatValue(
                    self.short_l3_input.text())/10**42
                self.app.calibration.shortLength = self.getFloatValue(
                    self.short_length.text())/10**12
                self.app.calibration.useIdealShort = False
            except ValueError:
                self.app.calibration.useIdealShort = True
                logger.warning(
                    'Invalid data for "short" calibration standard. Using ideal values.')

            try:
                self.app.calibration.openC0 = self.getFloatValue(
                    self.open_c0_input.text())/10**15
                if self.app.calibration.openC0 == 0:
                    raise ValueError("C0 cannot be 0.")
                self.app.calibration.openC1 = self.getFloatValue(
                    self.open_c1_input.text())/10**27
                self.app.calibration.openC2 = self.getFloatValue(
                    self.open_c2_input.text())/10**36
                self.app.calibration.openC3 = self.getFloatValue(
                    self.open_c3_input.text())/10**45
                self.app.calibration.openLength = self.getFloatValue(
                    self.open_length.text())/10**12
                self.app.calibration.useIdealOpen = False
            except ValueError:
                self.app.calibration.useIdealOpen = True
                logger.warning(
                    'Invalid data for "open" calibration standard. Using ideal values.')

            try:
                self.app.calibration.loadR = self.getFloatValue(
                    self.load_resistance.text())
                self.app.calibration.loadL = self.getFloatValue(
                    self.load_inductance.text())/10**12
                # self.app.calibration.loadC = self.getFloatValue(
                #   self.load_capacitance.text()) / 10 ** 12
                self.app.calibration.loadLength = self.getFloatValue(
                    self.load_length.text())/10**12
                self.app.calibration.useIdealLoad = False
            except ValueError:
                self.app.calibration.useIdealLoad = True
                logger.warning(
                    'Invalid data for "load" calibration standard.'
                    ' Using ideal values.')
            try:
                self.app.calibration.throughLength = self.getFloatValue(
                    self.through_length.text())/10**12
                self.app.calibration.useIdealThrough = False
            except ValueError:
                self.app.calibration.useIdealThrough = True
                logger.warning(
                    'Invalid data for "through" calibration standard.'
                    ' Using ideal values.')

        logger.debug("Attempting calibration calculation.")
        try:
            self.app.calibration.calc_corrections()
            self.calibration_status_label.setText(
                _format_cal_label(self.app.calibration.size(),
                                  "Application calibration"))
            if self.use_ideal_values.isChecked():
                self.calibration_source_label.setText(self.app.calibration.source)
            else:
                self.calibration_source_label.setText(
                    self.app.calibration.source + " (Standards: Custom)")

            if len(self.app.worker.rawData11) > 0:
                # There's raw data, so we can get corrected data
                logger.debug("Applying calibration to existing sweep data.")
                self.app.worker.data11, self.app.worker.data21 = self.app.worker.applyCalibration(
                    self.app.worker.rawData11, self.app.worker.rawData21)
                logger.debug("Saving and displaying corrected data.")
                self.app.saveData(self.app.worker.data11,
                                  self.app.worker.data21, self.app.sweepSource)
                self.app.worker.signals.updated.emit()
        except ValueError as e:
            # showError here hides the calibration window, so we need to pop up our own
            QtWidgets.QMessageBox.warning(self, "Error applying calibration", str(e))
            self.calibration_status_label.setText("Applying calibration failed.")
            self.calibration_source_label.setText(self.app.calibration.source)

    @staticmethod
    def getFloatValue(text: str) -> float:
        if text == "":
            # Default value is float
            return 0
        return float(text)

    def loadCalibration(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Calibration Files (*.cal);;All files (*.*)")
        if filename:
            self.app.calibration.load(filename)
        if not self.app.calibration.isValid1Port():
            return
        for i, name in enumerate(
                ("short", "open", "load", "through", "isolation")):
            self.cal_label[name].setText(
                _format_cal_label(self.app.calibration.data_size(name), "Loaded"))
            if i == 2 and not self.app.calibration.isValid2Port():
                break
        self.calculate()
        self.notes_textedit.clear()
        for note in self.app.calibration.notes:
            self.notes_textedit.appendPlainText(note)
        self.app.settings.setValue("CalibrationFile", filename)

    def saveCalibration(self):
        if not self.app.calibration.isCalculated:
            logger.debug("Attempted to save an uncalculated calibration.")
            self.app.showError("Cannot save an unapplied calibration state.")
            return
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("cal")
        filedialog.setNameFilter("Calibration Files (*.cal);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        selected = filedialog.exec()
        if selected:
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if filename == "":
            logger.debug("No file name selected.")
            return
        self.app.calibration.notes = self.notes_textedit.toPlainText().splitlines()
        try:
            self.app.calibration.save(filename)
            self.app.settings.setValue("CalibrationFile", filename)
        except IOError:
            logger.error("Calibration save failed!")
            self.app.showError("Calibration save failed.")

    def idealCheckboxChanged(self):
        self.cal_short_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_open_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_load_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_through_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_standard_save_box.setDisabled(self.use_ideal_values.isChecked())

    def automaticCalibration(self):
        self.btn_automatic.setDisabled(True)
        introduction = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information,
            "Calibration assistant",
            "This calibration assistant will help you create a calibration in the "
            "NanoVNASaver application.  It will sweep the standards for you, and "
            "guide you through the process.<br><br>"
            "Before starting, ensure you have Open, Short and Load standards "
            "available, and the cables you wish to have calibrated with the device "
            "connected.<br><br>"
            "If you want a 2-port calibration, also have a \"through\" connector "
            "to hand.<br><br>"
            "<b>The best results are achieved by having the NanoVNA calibrated "
            "on-device for the full span of interest and saved to save slot 0 "
            "before starting.</b><br><br>"
            "Once you are ready to proceed, press Ok",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        response = introduction.exec()
        if response != QtWidgets.QMessageBox.Ok:
            self.btn_automatic.setDisabled(False)
            return
        logger.info("Starting automatic calibration assistant.")
        if not self.app.serial.is_open:
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "NanoVNA not connected",
                "Please ensure the NanoVNA is connected before attempting calibration."
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        if self.app.windows["sweep_settings"].continuous_sweep_radiobutton.isChecked():
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Continuous sweep enabled",
                "Please disable continuous sweeping before attempting calibration."
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        short_step = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information,
            "Calibrate short",
            "Please connect the \"short\" standard to port 0 of the NanoVNA.\n\n"
            "Press Ok when you are ready to continue.",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

        response = short_step.exec()
        if response != QtWidgets.QMessageBox.Ok:
            self.btn_automatic.setDisabled(False)
            return
        self.reset()
        self.app.calibration.source = "Calibration assistant"
        self.nextStep = 0
        self.app.worker.signals.finished.connect(self.automaticCalibrationStep)
        self.app.sweep()
        return

    def automaticCalibrationStep(self):
        if self.nextStep == -1:
            self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
            return

        if self.nextStep == 0:
            # Short
            self.cal_save("short")
            self.nextStep = 1

            open_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibrate open",
                "Please connect the \"open\" standard to port 0 of the NanoVNA.\n\n"
                "Either use a supplied open, or leave the end of the cable unconnected "
                "if desired.\n\n"
                "Press Ok when you are ready to continue.",
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = open_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.nextStep = -1
                self.btn_automatic.setDisabled(False)
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep()
            return

        if self.nextStep == 1:
            # Open
            self.cal_save("open")
            self.nextStep = 2
            load_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibrate load",
                "Please connect the \"load\" standard to port 0 of the NanoVNA.\n\n"
                "Press Ok when you are ready to continue.",
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = load_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep()
            return

        if self.nextStep == 2:
            # Load
            self.cal_save("load")
            self.nextStep = 3
            continue_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "1-port calibration complete",
                "The required steps for a 1-port calibration are now complete.\n\n"
                "If you wish to continue and perform a 2-port calibration, press "
                "\"Yes\".  To apply the 1-port calibration and stop, press \"Apply\"",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Apply |
                QtWidgets.QMessageBox.Cancel)

            response = continue_step.exec()
            if response == QtWidgets.QMessageBox.Apply:
                self.calculate()
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                self.btn_automatic.setDisabled(False)
                return
            if response != QtWidgets.QMessageBox.Yes:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                return

            isolation_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibrate isolation",
                "Please connect the \"load\" standard to port 1 of the NanoVNA.\n\n"
                "If available, also connect a load standard to port 0.\n\n"
                "Press Ok when you are ready to continue.",
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = isolation_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep()
            return

        if self.nextStep == 3:
            # Isolation
            self.cal_save("isolation")
            self.nextStep = 4
            through_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibrate through",
                "Please connect the \"through\" standard between port 0 and port 1 "
                "of the NanoVNA.\n\n"
                "Press Ok when you are ready to continue.",
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = through_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep()
            return

        if self.nextStep == 4:
            # Done
            self.cal_save("through")
            apply_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibrate complete",
                "The calibration process is now complete.  Press \"Apply\" to apply "
                "the calibration parameters.",
                QtWidgets.QMessageBox.Apply | QtWidgets.QMessageBox.Cancel)

            response = apply_step.exec()
            if response != QtWidgets.QMessageBox.Apply:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.calculate()
            self.btn_automatic.setDisabled(False)
            self.nextStep = -1
            self.app.worker.signals.finished.disconnect(
                self.automaticCalibrationStep)
            return
