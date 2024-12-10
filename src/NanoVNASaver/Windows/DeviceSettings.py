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

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QIntValidator

from NanoVNASaver.SweepWorker import SweepState
from NanoVNASaver.Windows.Defaults import make_scrollable
from NanoVNASaver.Windows.Screenshot import ScreenshotWindow

logger = logging.getLogger(__name__)


class DeviceSettingsWindow(QtWidgets.QWidget):
    custom_points_checkbox = QtWidgets.QCheckBox
    custom_points_edit = QtWidgets.QLineEdit

    def __init__(self, app: QtWidgets.QWidget) -> None:  # noqa: PLR0915
        super().__init__()

        self.app = app
        self.setWindowTitle("Device settings")
        self.setWindowIcon(self.app.icon)

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        self.label = {
            "status": QtWidgets.QLabel("Not connected."),
            "firmware": QtWidgets.QLabel("Not connected."),
            "calibration": QtWidgets.QLabel("Not connected."),
            "SN": QtWidgets.QLabel("Not connected."),
        }

        top_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()
        right_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout)
        make_scrollable(self, top_layout)

        status_box = QtWidgets.QGroupBox("Status")
        status_layout = QtWidgets.QFormLayout(status_box)

        status_layout.addRow("Status:", self.label["status"])
        status_layout.addRow("Firmware:", self.label["firmware"])
        status_layout.addRow("Calibration:", self.label["calibration"])
        status_layout.addRow("SN:", self.label["SN"])

        status_layout.addRow(QtWidgets.QLabel("Features:"))

        self.featureList = QtWidgets.QListWidget()
        status_layout.addRow(self.featureList)

        settings_box = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QFormLayout(settings_box)

        self.chkValidateInputData = QtWidgets.QCheckBox(
            "Validate received data"
        )
        validate_input = self.app.settings.value(
            "SerialInputValidation", False, bool
        )
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

        self.custom_points_checkbox = QtWidgets.QCheckBox("Custom points")
        self.custom_points_checkbox.stateChanged.connect(self.customPoint_check)
        self.custom_points_edit = QtWidgets.QLineEdit("101")
        self.custom_points_edit.setValidator(
            QIntValidator(
                self.app.vna.sweep_points_min, self.app.vna.sweep_points_max
            )
        )
        self.custom_points_edit.textEdited.connect(self.updatecustomPoint)
        self.custom_points_edit.setDisabled(True)

        self.bandwidth = QtWidgets.QComboBox()
        self.bandwidth.addItem(str(self.app.vna.bandwidth))
        self.bandwidth.currentIndexChanged.connect(self.updateBandwidth)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow(QtWidgets.QLabel("Datapoints"), self.datapoints)
        form_layout.addRow(self.custom_points_checkbox, self.custom_points_edit)
        form_layout.addRow(QtWidgets.QLabel("Bandwidth"), self.bandwidth)
        right_layout.addWidget(settings_box)
        settings_layout.addRow(form_layout)

    def _set_datapoint_index(self, dpoints: int) -> None:
        self.datapoints.setCurrentIndex(self.datapoints.findText(str(dpoints)))

    def _set_bandwidth_index(self, bw: int) -> None:
        self.bandwidth.setCurrentIndex(self.bandwidth.findText(str(bw)))

    def show(self):
        super().show()
        self.updateFields()

    def updateFields(self):
        if not self.app.vna.connected():
            self.label["status"].setText("Not connected.")
            self.label["firmware"].setText("Not connected.")
            self.label["calibration"].setText("Not connected.")
            self.label["SN"].setText("Not connected.")
            self.featureList.clear()
            self.btnCaptureScreenshot.setDisabled(True)
            return

        self.label["status"].setText(f"Connected to {self.app.vna.name}.")
        self.label["firmware"].setText(
            f"{self.app.vna.name} v{self.app.vna.version}"
        )
        if self.app.worker.state == SweepState.RUNNING:
            self.label["calibration"].setText("(Sweep running)")
        else:
            self.label["calibration"].setText(self.app.vna.getCalibration())
        self.label["SN"].setText(self.app.vna.SN)
        self.featureList.clear()
        features = self.app.vna.getFeatures()
        for item in features:
            self.featureList.addItem(item)

        self.btnCaptureScreenshot.setDisabled("Screenshots" not in features)

        if "Customizable data points" in features:
            self.datapoints.clear()
            self.custom_points_edit.setValidator(
                QIntValidator(
                    self.app.vna.sweep_points_min, self.app.vna.sweep_points_max
                )
            )
            cur_dps = self.app.vna.datapoints
            for d in sorted(self.app.vna.valid_datapoints):
                self.datapoints.addItem(str(d))
            self._set_datapoint_index(cur_dps)
            self.datapoints.setDisabled(False)
        else:
            self.datapoints.setDisabled(True)

        if "Bandwidth" in features:
            self.bandwidth.clear()
            cur_bw = self.app.vna.bandwidth
            for d in sorted(self.app.vna.get_bandwidths()):
                self.bandwidth.addItem(str(d))
            self._set_bandwidth_index(cur_bw)
            self.bandwidth.setDisabled(False)
        else:
            self.bandwidth.setDisabled(True)

    def updateValidation(self, validate_data: bool) -> None:
        self.app.vna.validateInput = validate_data
        self.app.settings.setValue("SerialInputValidation", validate_data)

    def captureScreenshot(self) -> None:
        if self.app.worker.state != SweepState.RUNNING:
            pixmap = self.app.vna.getScreenshot()
            self.screenshotWindow.setScreenshot(pixmap)
            self.screenshotWindow.show()
        # TODO: Tell the user no screenshots while sweep is running?
        # TODO: Consider having a list of widgets that want to be
        #       disabled when a sweep is running?

    def updateNrDatapoints(self, i) -> None:
        if i < 0 or self.app.worker.state == SweepState.RUNNING:
            return
        logger.debug("DP: %s", self.datapoints.itemText(i))
        self.app.vna.datapoints = int(self.datapoints.itemText(i))
        self.app.sweep.set_points(self.app.vna.datapoints)
        self.app.sweep_control.update_step_size()

    def updateBandwidth(self, i) -> None:
        if i < 0 or self.app.worker.state == SweepState.RUNNING:
            return
        logger.debug("Bandwidth: %s", self.bandwidth.itemText(i))
        self.app.vna.set_bandwidth(int(self.bandwidth.itemText(i)))

    def customPoint_check(self, validate_data: bool) -> None:
        self.datapoints.setDisabled(validate_data)
        self.custom_points_edit.setDisabled(not validate_data)

    def updatecustomPoint(self, points_str: str) -> None:
        if self.custom_points_checkbox.isChecked():
            # points_str = self.custom_points_Eidt.text()
            if len(points_str) == 0:
                return
            points = int(points_str)
            if points < self.app.vna.sweep_points_min:
                return
            if points > self.app.vna.sweep_points_max:
                points = int(self.app.vna.sweep_points_max)

            if points != self.app.vna.datapoints:
                logger.debug("DP: %s", points)
                self.app.vna.datapoints = points
                self.app.sweep.set_points(self.app.vna.datapoints)
                self.app.sweep_control.update_step_size()
                self.custom_points_edit.setText(str(points))
