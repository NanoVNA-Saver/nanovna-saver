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

import logging
import math
import os
from typing import List

import numpy as np
from PyQt5 import QtWidgets, QtCore

from .RFTools import Datapoint

logger = logging.getLogger(__name__)


class CalibrationWindow(QtWidgets.QWidget):
    nextStep = -1

    def __init__(self, app):
        super().__init__()

        from .NanoVNASaver import NanoVNASaver

        self.app: NanoVNASaver = app

        self.setMinimumWidth(450)
        self.setWindowTitle("Calibration")
        self.setWindowIcon(self.app.icon)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

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
        btn_cal_short = QtWidgets.QPushButton("Short")
        btn_cal_short.clicked.connect(self.manualSaveShort)
        self.cal_short_label = QtWidgets.QLabel("Uncalibrated")
        
        btn_cal_open = QtWidgets.QPushButton("Open")
        btn_cal_open.clicked.connect(self.manualSaveOpen)
        self.cal_open_label = QtWidgets.QLabel("Uncalibrated")
        
        btn_cal_load = QtWidgets.QPushButton("Load")
        btn_cal_load.clicked.connect(self.manualSaveLoad)
        self.cal_load_label = QtWidgets.QLabel("Uncalibrated")

        btn_cal_through = QtWidgets.QPushButton("Through")
        btn_cal_through.clicked.connect(self.manualSaveThrough)
        # btn_cal_through.setDisabled(True)
        self.cal_through_label = QtWidgets.QLabel("Uncalibrated")

        btn_cal_isolation = QtWidgets.QPushButton("Isolation")
        btn_cal_isolation.clicked.connect(self.manualSaveIsolation)
        # btn_cal_isolation.setDisabled(True)
        self.cal_isolation_label = QtWidgets.QLabel("Uncalibrated")

        self.input_offset_delay = QtWidgets.QDoubleSpinBox()
        self.input_offset_delay.setValue(0)
        self.input_offset_delay.setSuffix(" ps")
        self.input_offset_delay.setAlignment(QtCore.Qt.AlignRight)
        self.input_offset_delay.valueChanged.connect(self.setOffsetDelay)
        self.input_offset_delay.setRange(-10e6, 10e6)

        calibration_control_layout.addRow(btn_cal_short, self.cal_short_label)
        calibration_control_layout.addRow(btn_cal_open, self.cal_open_label)
        calibration_control_layout.addRow(btn_cal_load, self.cal_load_label)
        calibration_control_layout.addRow(btn_cal_isolation, self.cal_isolation_label)
        calibration_control_layout.addRow(btn_cal_through, self.cal_through_label)

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
            response = QtWidgets.QMessageBox.question(self, "Are you sure?", "Use of the manual calibration buttons " +
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
            else:
                return False
        else:
            return True

    def manualSaveShort(self):
        if self.checkExpertUser():
            self.saveShort()

    def saveShort(self):
        self.app.calibration.s11short = self.app.data
        self.cal_short_label.setText("Data set (" + str(len(self.app.calibration.s11short)) + " points)")

    def manualSaveOpen(self):
        if self.checkExpertUser():
            self.saveOpen()

    def saveOpen(self):
        self.app.calibration.s11open = self.app.data
        self.cal_open_label.setText("Data set (" + str(len(self.app.calibration.s11open)) + " points)")

    def manualSaveLoad(self):
        if self.checkExpertUser():
            self.saveLoad()

    def saveLoad(self):
        self.app.calibration.s11load = self.app.data
        self.cal_load_label.setText("Data set (" + str(len(self.app.calibration.s11load)) + " points)")

    def manualSaveIsolation(self):
        if self.checkExpertUser():
            self.saveIsolation()

    def saveIsolation(self):
        self.app.calibration.s21isolation = self.app.data21
        self.cal_isolation_label.setText("Data set (" + str(len(self.app.calibration.s21isolation)) + " points)")

    def manualSaveThrough(self):
        if self.checkExpertUser():
            self.saveThrough()

    def saveThrough(self):
        self.app.calibration.s21through = self.app.data21
        self.cal_through_label.setText("Data set (" + str(len(self.app.calibration.s21through)) + " points)")

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
            name, selected = QtWidgets.QInputDialog.getText(self, "Calibration standard name", "Enter name to save as")
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
            for i in range(len(names)):
                self.app.settings.setArrayIndex(i)
                self.app.settings.setValue("Name", names[i])
                
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
        self.cal_short_label.setText("Uncalibrated")
        self.cal_open_label.setText("Uncalibrated")
        self.cal_load_label.setText("Uncalibrated")
        self.cal_through_label.setText("Uncalibrated")
        self.cal_isolation_label.setText("Uncalibrated")
        self.calibration_status_label.setText("Device calibration")
        self.calibration_source_label.setText("Device")
        self.notes_textedit.clear()

        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Saving and displaying raw data.")
            self.app.saveData(self.app.worker.rawData11, self.app.worker.rawData21, self.app.sweepSource)
            self.app.worker.signals.updated.emit()

    def setOffsetDelay(self, value: float):
        logger.debug("New offset delay value: %f ps", value)
        self.app.worker.offsetDelay = value / 1e12
        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Applying new offset to existing sweep data.")
            self.app.worker.data11, self.app.worker.data21 = self.app.worker.applyCalibration(self.app.worker.rawData11,
                                                                                              self.app.worker.rawData21)
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
                self.app.calibration.shortL0 = self.getFloatValue(self.short_l0_input.text())/10**12
                self.app.calibration.shortL1 = self.getFloatValue(self.short_l1_input.text())/10**24
                self.app.calibration.shortL2 = self.getFloatValue(self.short_l2_input.text())/10**33
                self.app.calibration.shortL3 = self.getFloatValue(self.short_l3_input.text())/10**42
                self.app.calibration.shortLength = self.getFloatValue(self.short_length.text())/10**12
                self.app.calibration.useIdealShort = False
            except ValueError:
                self.app.calibration.useIdealShort = True
                logger.warning("Invalid data for \"short\" calibration standard. Using ideal values.")

            try:
                self.app.calibration.openC0 = self.getFloatValue(self.open_c0_input.text())/10**15
                if self.app.calibration.openC0 == 0:
                    raise ValueError("C0 cannot be 0.")
                self.app.calibration.openC1 = self.getFloatValue(self.open_c1_input.text())/10**27
                self.app.calibration.openC2 = self.getFloatValue(self.open_c2_input.text())/10**36
                self.app.calibration.openC3 = self.getFloatValue(self.open_c3_input.text())/10**45
                self.app.calibration.openLength = self.getFloatValue(self.open_length.text())/10**12
                self.app.calibration.useIdealOpen = False
            except ValueError:
                self.app.calibration.useIdealOpen = True
                logger.warning("Invalid data for \"open\" calibration standard. Using ideal values.")

            try:
                self.app.calibration.loadR = self.getFloatValue(self.load_resistance.text())
                self.app.calibration.loadL = self.getFloatValue(self.load_inductance.text())/10**12
                # self.app.calibration.loadC = self.getFloatValue(self.load_capacitance.text()) / 10 ** 12
                self.app.calibration.loadLength = self.getFloatValue(self.load_length.text())/10**12
                self.app.calibration.useIdealLoad = False
            except ValueError:
                self.app.calibration.useIdealLoad = True
                logger.warning("Invalid data for \"load\" calibration standard. Using ideal values.")

            try:
                self.app.calibration.throughLength = self.getFloatValue(self.through_length.text())/10**12
                self.app.calibration.useIdealThrough = False
            except ValueError:
                self.app.calibration.useIdealThrough = True
                logger.warning("Invalid data for \"through\" calibration standard. Using ideal values.")

        logger.debug("Attempting calibration calculation.")
        valid, error = self.app.calibration.calculateCorrections()
        if valid:
            self.calibration_status_label.setText("Application calibration (" +
                                                  str(len(self.app.calibration.s11short)) + " points)")
            if self.use_ideal_values.isChecked():
                self.calibration_source_label.setText(self.app.calibration.source)
            else:
                self.calibration_source_label.setText(self.app.calibration.source + " (Standards: Custom)")

            if len(self.app.worker.rawData11) > 0:
                # There's raw data, so we can get corrected data
                logger.debug("Applying calibration to existing sweep data.")
                self.app.worker.data11, self.app.worker.data21 = self.app.worker.applyCalibration(
                    self.app.worker.rawData11, self.app.worker.rawData21)
                logger.debug("Saving and displaying corrected data.")
                self.app.saveData(self.app.worker.data11, self.app.worker.data21, self.app.sweepSource)
                self.app.worker.signals.updated.emit()
        else:
            # showError here hides the calibration window, so we need to pop up our own
            QtWidgets.QMessageBox.warning(self, "Error applying calibration", error)
            self.calibration_status_label.setText("Applying calibration failed.")
            self.calibration_source_label.setText(self.app.calibration.source)

    @staticmethod
    def getFloatValue(text: str) -> float:
        if text == "":
            # Default value is float
            return 0
        return float(text)

    def loadCalibration(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(filter="Calibration Files (*.cal);;All files (*.*)")
        if filename:
            self.app.calibration.loadCalibration(filename)
            if self.app.calibration.isValid1Port():
                self.cal_short_label.setText("Loaded (" + str(len(self.app.calibration.s11short)) + ")")
                self.cal_open_label.setText("Loaded (" + str(len(self.app.calibration.s11open)) + ")")
                self.cal_load_label.setText("Loaded (" + str(len(self.app.calibration.s11load)) + ")")
                if self.app.calibration.isValid2Port():
                    self.cal_through_label.setText("Loaded (" + str(len(self.app.calibration.s21through)) + ")")
                    self.cal_isolation_label.setText("Loaded (" + str(len(self.app.calibration.s21isolation)) + ")")
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
        if filename and self.app.calibration.saveCalibration(filename):
            self.app.settings.setValue("CalibrationFile", filename)
        else:
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
        introduction = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                             "Calibration assistant",
                                             "This calibration assistant will help you create a calibration in the " +
                                             "NanoVNASaver application.  It will sweep the standards for you, and "+
                                             "guide you through the process.<br><br>" +
                                             "Before starting, ensure you have Open, Short and Load standards " +
                                             "available, and the cables you wish to have calibrated with the device " +
                                             "connected.<br><br>" +
                                             "If you want a 2-port calibration, also have a \"through\" connector " +
                                             "to hand.<br><br>" +
                                             "<b>The best results are achieved by having the NanoVNA calibrated " +
                                             "on-device for the full span of interest and saved to save slot 0 " +
                                             "before starting.</b><br><br>" +
                                             "Once you are ready to proceed, press Ok",
                                             QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        response = introduction.exec()
        if response != QtWidgets.QMessageBox.Ok:
            self.btn_automatic.setDisabled(False)
            return
        logger.info("Starting automatic calibration assistant.")
        if not self.app.serial.is_open:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "NanoVNA not connected",
                                  "Please ensure the NanoVNA is connected before attempting calibration.").exec()
            self.btn_automatic.setDisabled(False)
            return

        if self.app.sweepSettingsWindow.continuous_sweep_radiobutton.isChecked():
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, "Continuous sweep enabled",
                                  "Please disable continuous sweeping before attempting calibration.").exec()
            self.btn_automatic.setDisabled(False)
            return

        short_step = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                           "Calibrate short",
                                           "Please connect the \"short\" standard to port 0 of the NanoVNA.\n\n" +
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
        if self.nextStep == 0:
            # Short
            self.saveShort()
            self.nextStep = 1

            open_step = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                              "Calibrate open",
                                              "Please connect the \"open\" standard to port 0 of the NanoVNA.\n\n" +
                                              "Either use a supplied open, or leave the end of the cable unconnected " +
                                              "if desired.\n\n" +
                                              "Press Ok when you are ready to continue.",
                                              QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = open_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.nextStep = -1
                self.btn_automatic.setDisabled(False)
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                return
            else:
                self.app.sweep()
                return

        elif self.nextStep == 1:
            # Open
            self.saveOpen()
            self.nextStep = 2
            load_step = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                              "Calibrate load",
                                              "Please connect the \"load\" standard to port 0 of the NanoVNA.\n\n" +
                                              "Press Ok when you are ready to continue.",
                                              QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = load_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                return
            else:
                self.app.sweep()
                return

        if self.nextStep == 2:
            # Load
            self.saveLoad()
            self.nextStep = 3
            continue_step = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                                  "1-port calibration complete",
                                                  "The required steps for a 1-port calibration are now complete.\n\n" +
                                                  "If you wish to continue and perform a 2-port calibration, press " +
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
            elif response != QtWidgets.QMessageBox.Yes:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                return
            else:
                isolation_step = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                                       "Calibrate isolation",
                                                       "Please connect the \"load\" standard to port 1 of the NanoVNA.\n\n" +
                                                       "If available, also connect a load standard to port 0.\n\n" +
                                                       "Press Ok when you are ready to continue.",
                                                       QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

                response = isolation_step.exec()
                if response != QtWidgets.QMessageBox.Ok:
                    self.btn_automatic.setDisabled(False)
                    self.nextStep = -1
                    self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                    return
                else:
                    self.app.sweep()
                    return

        elif self.nextStep == 3:
            # Isolation
            self.saveIsolation()
            self.nextStep = 4
            through_step = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                                 "Calibrate through",
                                                 "Please connect the \"through\" standard between port 0 and port 1 " +
                                                 "of the NanoVNA.\n\n" +
                                                 "Press Ok when you are ready to continue.",
                                                 QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = through_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                return
            else:
                self.app.sweep()
                return

        elif self.nextStep == 4:
            # Done
            self.saveThrough()
            apply_step = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information,
                                               "Calibrate complete",
                                               "The calibration process is now complete.  Press \"Apply\" to apply " +
                                               "the calibration parameters.",
                                               QtWidgets.QMessageBox.Apply | QtWidgets.QMessageBox.Cancel)

            response = apply_step.exec()
            if response != QtWidgets.QMessageBox.Apply:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                return
            else:
                self.calculate()
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(self.automaticCalibrationStep)
                return
        return


class Calibration:
    notes = []
    s11short: List[Datapoint] = []
    s11open: List[Datapoint] = []
    s11load: List[Datapoint] = []
    s21through: List[Datapoint] = []
    s21isolation: List[Datapoint] = []

    frequencies = []

    # 1-port
    e00 = []     # Directivity
    e11 = []     # Port match
    deltaE = []  # Tracking

    # 2-port
    e30 = []     # Port match
    e10e32 = []  # Transmission

    shortIdeal = np.complex(-1, 0)
    useIdealShort = True
    shortL0 = 5.7 * 10E-12
    shortL1 = -8960 * 10E-24
    shortL2 = -1100 * 10E-33
    shortL3 = -41200 * 10E-42
    shortLength = -34.2  # Picoseconds
    # These numbers look very large, considering what Keysight suggests their numbers are.

    useIdealOpen = True
    openIdeal = np.complex(1, 0)
    openC0 = 2.1 * 10E-14  # Subtract 50fF for the nanoVNA calibration if nanoVNA is calibrated?
    openC1 = 5.67 * 10E-23
    openC2 = -2.39 * 10E-31
    openC3 = 2.0 * 10E-40
    openLength = 0

    useIdealLoad = True
    loadR = 25
    loadL = 0
    loadC = 0
    loadLength = 0
    loadIdeal = np.complex(0, 0)

    useIdealThrough = True
    throughLength = 0

    isCalculated = False

    source = "Manual"

    def isValid2Port(self):
        valid = len(self.s21through) > 0 and len(self.s21isolation) > 0 and self.isValid1Port()
        valid &= len(self.s21through) == len(self.s21isolation) == len(self.s11short)
        return valid

    def isValid1Port(self):
        valid = len(self.s11short) > 0 and len(self.s11open) > 0 and len(self.s11load) > 0
        valid &= len(self.s11short) == len(self.s11open) == len(self.s11load)
        return valid

    def calculateCorrections(self) -> (bool, str):
        if not self.isValid1Port():
            logger.warning("Tried to calibrate from insufficient data.")
            if len(self.s11short) == 0 or len(self.s11open) == 0 or len(self.s11load) == 0:
                return False, "All of short, open and load calibration steps must be completed for calibration to be " \
                            + "applied."
            else:
                return False, "All calibration data sets must be the same size."
        self.frequencies = [int] * len(self.s11short)
        self.e00 = [np.complex] * len(self.s11short)
        self.e11 = [np.complex] * len(self.s11short)
        self.deltaE = [np.complex] * len(self.s11short)
        self.e30 = [np.complex] * len(self.s11short)
        self.e10e32 = [np.complex] * len(self.s11short)
        logger.debug("Calculating calibration for %d points.", len(self.s11short))
        if self.useIdealShort:
            logger.debug("Using ideal values.")
        else:
            logger.debug("Using calibration set values.")
        if self.isValid2Port():
            logger.debug("Calculating 2-port calibration.")
        else:
            logger.debug("Calculating 1-port calibration.")
        for i in range(len(self.s11short)):
            self.frequencies[i] = self.s11short[i].freq
            f = self.s11short[i].freq
            pi = math.pi

            if self.useIdealShort:
                g1 = self.shortIdeal
            else:
                Zsp = np.complex(0, 1) * 2 * pi * f * (self.shortL0 +
                                                       self.shortL1 * f +
                                                       self.shortL2 * f**2 +
                                                       self.shortL3 * f**3)
                gammaShort = ((Zsp/50) - 1) / ((Zsp/50) + 1)
                # (lower case) gamma = 2*pi*f
                # e^j*2*gamma*length
                # Referencing https://arxiv.org/pdf/1606.02446.pdf (18) - (21)
                g1 = gammaShort * np.exp(np.complex(0, 1) * 2 * 2 * math.pi * f * self.shortLength * -1)

            if self.useIdealOpen:
                g2 = self.openIdeal
            else:
                divisor = (2 * pi * f * (self.openC0 + self.openC1 * f + self.openC2 * f**2 + self.openC3 * f**3))
                if divisor != 0:
                    Zop = np.complex(0, -1) / divisor
                    gammaOpen = ((Zop/50) - 1) / ((Zop/50) + 1)
                    g2 = gammaOpen * np.exp(np.complex(0, 1) * 2 * 2 * math.pi * f * self.openLength * -1)
                else:
                    g2 = self.openIdeal
            if self.useIdealLoad:
                g3 = self.loadIdeal
            else:
                Zl = self.loadR + (np.complex(0, 1) * 2 * math.pi * f * self.loadL)
                g3 = ((Zl/50)-1) / ((Zl/50)+1)
                g3 = g3 * np.exp(np.complex(0, 1) * 2 * 2 * math.pi * f * self.loadLength * -1)

            gm1 = np.complex(self.s11short[i].re, self.s11short[i].im)
            gm2 = np.complex(self.s11open[i].re, self.s11open[i].im)
            gm3 = np.complex(self.s11load[i].re, self.s11load[i].im)

            try:
                denominator = g1*(g2-g3)*gm1 + g2*g3*gm2 - g2*g3*gm3 - (g2*gm2-g3*gm3)*g1
                self.e00[i] = - ((g2*gm3 - g3*gm3)*g1*gm2 - (g2*g3*gm2 - g2*g3*gm3 - (g3*gm2 - g2*gm3)*g1)*gm1) / denominator
                self.e11[i] = ((g2-g3)*gm1-g1*(gm2-gm3)+g3*gm2-g2*gm3) / denominator
                self.deltaE[i] = - ((g1*(gm2-gm3)-g2*gm2+g3*gm3)*gm1+(g2*gm3-g3*gm3)*gm2) / denominator
            except ZeroDivisionError:
                self.isCalculated = False
                logger.error("Division error - did you use the same measurement for two of short, open and load?")
                logger.debug("Division error at index %d", i)
                logger.debug("Short == Load: %s", self.s11short[i] == self.s11load[i])
                logger.debug("Short == Open: %s", self.s11short[i] == self.s11open[i])
                logger.debug("Open == Load: %s", self.s11open[i] == self.s11load[i])
                return self.isCalculated, "Two of short, open and load returned the same values at frequency " \
                                          + str(self.s11open[i].freq) + " Hz."

            if self.isValid2Port():
                self.e30[i] = np.complex(self.s21isolation[i].re, self.s21isolation[i].im)
                s21m = np.complex(self.s21through[i].re, self.s21through[i].im)
                if not self.useIdealThrough:
                    gammaThrough = np.exp(np.complex(0, 1) * 2 * math.pi * self.throughLength * f * -1)
                    s21m = s21m / gammaThrough
                self.e10e32[i] = (s21m - self.e30[i]) * (1 - (self.e11[i]*self.e11[i]))

        self.isCalculated = True
        logger.debug("Calibration correctly calculated.")
        return self.isCalculated, "Calibration successful."

    def correct11(self, re, im, freq):
        s11m = np.complex(re, im)
        distance = 10**10
        index = 0
        for i in range(len(self.s11short)):
            if abs(self.s11short[i].freq - freq) < distance:
                index = i
                distance = abs(self.s11short[i].freq - freq)
        # TODO: Interpolate with the adjacent data point to get better corrections?

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

    @staticmethod
    def correctDelay11(d: Datapoint, delay):
        input_val = np.complex(d.re, d.im)
        output = input_val * np.exp(np.complex(0, 1) * 2 * 2 * math.pi * d.freq * delay * -1)
        return Datapoint(d.freq, output.real, output.imag)

    @staticmethod
    def correctDelay21(d: Datapoint, delay):
        input_val = np.complex(d.re, d.im)
        output = input_val * np.exp(np.complex(0, 1) * 2 * math.pi * d.freq * delay * -1)
        return Datapoint(d.freq, output.real, output.imag)

    def saveCalibration(self, filename):
        # Save the calibration data to file
        if filename == "" or not self.isValid1Port():
            return False
        try:
            file = open(filename, "w+")
            file.write("# Calibration data for NanoVNA-Saver\n")
            for note in self.notes:
                file.write("! " + note + "\n")
            file.write("# Hz ShortR ShortI OpenR OpenI LoadR LoadI ThroughR ThroughI IsolationR IsolationI\n")
            for i in range(len(self.s11short)):
                freq = str(self.s11short[i].freq)
                shortr = str(self.s11short[i].re)
                shorti = str(self.s11short[i].im)
                openr = str(self.s11open[i].re)
                openi = str(self.s11open[i].im)
                loadr = str(self.s11load[i].re)
                loadi = str(self.s11load[i].im)
                file.write(freq + " " + shortr + " " + shorti + " " + openr + " " + openi + " " + loadr + " " + loadi)
                if self.isValid2Port():
                    throughr = str(self.s21through[i].re)
                    throughi = str(self.s21through[i].im)
                    isolationr = str(self.s21isolation[i].re)
                    isolationi = str(self.s21isolation[i].im)
                    file.write(" " + throughr + " " + throughi + " " + isolationr + " " + isolationi)
                file.write("\n")
            file.close()
            return True
        except Exception as e:
            logger.exception("Error saving calibration data: %s", e)
            return False

    def loadCalibration(self, filename):
        # Load calibration data from file
        if filename == "":
            return

        self.source = os.path.basename(filename)

        self.s11short = []
        self.s11open = []
        self.s11load = []

        self.s21through = []
        self.s21isolation = []
        self.notes = []

        try:
            file = open(filename, "r")
            lines = file.readlines()
            parsed_header = False

            for line in lines:
                line = line.strip()
                if line.startswith("!"):
                    note = line[2:]
                    self.notes.append(note)
                    continue
                if line.startswith("#") and not parsed_header:
                    # Check that this is a valid header
                    if line == "# Hz ShortR ShortI OpenR OpenI LoadR LoadI ThroughR ThroughI IsolationR IsolationI":
                        parsed_header = True
                        continue
                    else:
                        # This is some other comment line
                        continue
                if not parsed_header:
                    logger.warning("Warning: Read line without having read header: %s", line)
                    continue

                try:
                    if line.count(" ") == 6:
                        freq, shortr, shorti, openr, openi, loadr, loadi = line.split(" ")
                        self.s11short.append(Datapoint(int(freq), float(shortr), float(shorti)))
                        self.s11open.append(Datapoint(int(freq), float(openr), float(openi)))
                        self.s11load.append(Datapoint(int(freq), float(loadr), float(loadi)))

                    else:
                        freq, shortr, shorti, openr, openi, loadr, loadi, throughr, throughi, isolationr, isolationi = line.split(" ")
                        self.s11short.append(Datapoint(int(freq), float(shortr), float(shorti)))
                        self.s11open.append(Datapoint(int(freq), float(openr), float(openi)))
                        self.s11load.append(Datapoint(int(freq), float(loadr), float(loadi)))
                        self.s21through.append(Datapoint(int(freq), float(throughr), float(throughi)))
                        self.s21isolation.append(Datapoint(int(freq), float(isolationr), float(isolationi)))

                except ValueError as e:
                    logger.exception("Error parsing calibration data \"%s\": %s", line, e)
            file.close()
        except Exception as e:
            logger.exception("Failed loading calibration data: %s", e)
