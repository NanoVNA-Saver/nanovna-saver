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

from PyQt5 import QtWidgets, QtCore

from NanoVNASaver.Windows.Screenshot import ScreenshotWindow

logger = logging.getLogger(__name__)


class DeviceSettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()

        self.app = app
        self.setWindowTitle("Device settings")
        self.setWindowIcon(self.app.icon)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        top_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()
        right_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout)
        self.setLayout(top_layout)

        status_box = QtWidgets.QGroupBox("Status")
        status_layout = QtWidgets.QFormLayout(status_box)
        self.statusLabel = QtWidgets.QLabel("Not connected.")
        status_layout.addRow("Status:", self.statusLabel)

        self.calibrationStatusLabel = QtWidgets.QLabel("Not connected.")
        status_layout.addRow("Calibration:", self.calibrationStatusLabel)

        status_layout.addRow(QtWidgets.QLabel("Features:"))
        self.featureList = QtWidgets.QListWidget()
        status_layout.addRow(self.featureList)

        settings_box = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QFormLayout(settings_box)

        self.chkValidateInputData = QtWidgets.QCheckBox("Validate received data")
        validate_input = self.app.settings.value("SerialInputValidation", True, bool)
        self.chkValidateInputData.setChecked(validate_input)
        self.chkValidateInputData.stateChanged.connect(self.updateValidation)
        settings_layout.addRow("Validation", self.chkValidateInputData)

        control_layout = QtWidgets.QHBoxLayout()
        self.btnRefresh = QtWidgets.QPushButton("Refresh")
        self.btnRefresh.clicked.connect(self.updateFields)
        control_layout.addWidget(self.btnRefresh)

        self.screenshotWindow = ScreenshotWindow()
        self.btnCaptureScreenshot = QtWidgets.QPushButton("Screenshot")
        self.btnCaptureScreenshot.clicked.connect(self.captureScreenshot)
        control_layout.addWidget(self.btnCaptureScreenshot)

        left_layout.addWidget(status_box)
        left_layout.addLayout(control_layout)

        self.datapoints = QtWidgets.QComboBox()
        self.datapoints.addItem(str(self.app.vna.datapoints))
        self.datapoints.currentIndexChanged.connect(self.updateNrDatapoints)
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow(QtWidgets.QLabel("Datapoints"), self.datapoints)
        right_layout.addWidget(settings_box)
        settings_layout.addRow(form_layout)

    def _set_datapoint_index(self, dpoints: int):
        self.datapoints.setCurrentIndex(
            self.datapoints.findText(str(dpoints)))

    def show(self):
        super().show()
        self.updateFields()

    def updateFields(self):
        if self.app.vna.isValid():
            self.statusLabel.setText("Connected to " + self.app.vna.name + ".")
            if self.app.worker.running:
                self.calibrationStatusLabel.setText("(Sweep running)")
            else:
                self.calibrationStatusLabel.setText(self.app.vna.getCalibration())

            self.featureList.clear()
            self.featureList.addItem(self.app.vna.name + " v" + str(self.app.vna.version))
            features = self.app.vna.getFeatures()
            for item in features:
                self.featureList.addItem(item)

            self.btnCaptureScreenshot.setDisabled("Screenshots" not in features)
            if "Customizable data points" in features:
                self.datapoints.clear()
                cur_dps = self.app.vna.datapoints
                dplist = self.app.vna._datapoints[:]
                for d in sorted(dplist):
                    self.datapoints.addItem(str(d))
                self._set_datapoint_index(cur_dps)
        else:
            self.statusLabel.setText("Not connected.")
            self.calibrationStatusLabel.setText("Not connected.")
            self.featureList.clear()
            self.featureList.addItem("Not connected.")
            self.btnCaptureScreenshot.setDisabled(True)

    def updateValidation(self, validate_data: bool):
        self.app.vna.validateInput = validate_data
        self.app.settings.setValue("SerialInputValidation", validate_data)

    def captureScreenshot(self):
        if not self.app.worker.running:
            pixmap = self.app.vna.getScreenshot()
            self.screenshotWindow.setScreenshot(pixmap)
            self.screenshotWindow.show()
        # TODO: Tell the user no screenshots while sweep is running?
        # TODO: Consider having a list of widgets that want to be
        #       disabled when a sweep is running?

    def updateNrDatapoints(self, i):
        if i < 0 or self.app.worker.running:
            return
        logger.debug("DP: %s", self.datapoints.itemText(i))
        self.app.vna.datapoints = int(self.datapoints.itemText(i))
