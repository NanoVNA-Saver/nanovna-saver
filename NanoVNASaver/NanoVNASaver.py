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
import collections
import logging
import math
import sys
import threading
from time import sleep, strftime, gmtime
from typing import List

import numpy as np
import serial
from PyQt5 import QtWidgets, QtCore, QtGui
from serial.tools import list_ports

from .Chart import Chart, PhaseChart, VSWRChart, PolarChart, SmithChart, LogMagChart, QualityFactorChart, TDRChart, \
    RealImaginaryChart
from .Calibration import CalibrationWindow, Calibration
from .Marker import Marker
from .SweepWorker import SweepWorker
from .Touchstone import Touchstone
from .about import version as ver

Datapoint = collections.namedtuple('Datapoint', 'freq re im')

VID = 1155
PID = 22336

logger = logging.getLogger(__name__)


class NanoVNASaver(QtWidgets.QWidget):
    version = ver

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon("icon_48x48.png"))

        self.settings = QtCore.QSettings(QtCore.QSettings.IniFormat,
                                         QtCore.QSettings.UserScope,
                                         "NanoVNASaver", "NanoVNASaver")
        print("Settings: " + self.settings.fileName())
        self.threadpool = QtCore.QThreadPool()
        self.worker = SweepWorker(self)

        self.noSweeps = 1  # Number of sweeps to run

        self.serialLock = threading.Lock()
        self.serial = serial.Serial()

        self.dataLock = threading.Lock()
        self.data: List[Datapoint] = []
        self.data21: List[Datapoint] = []
        self.referenceS11data: List[Datapoint] = []
        self.referenceS21data: List[Datapoint] = []

        self.sweepSource = ""
        self.referenceSource = ""

        self.calibration = Calibration()

        self.markers = []

        self.serialPort = self.getPort()

        logger.debug("Building user interface")

        self.baseTitle = "NanoVNA Saver " + NanoVNASaver.version
        self.updateTitle()
        layout = QtWidgets.QGridLayout()
        scrollarea = QtWidgets.QScrollArea()
        outer = QtWidgets.QVBoxLayout()
        outer.addWidget(scrollarea)
        self.setLayout(outer)
        scrollarea.setWidgetResizable(True)
        window_width = self.settings.value("WindowWidth", 1350, type=int)
        window_height = self.settings.value("WindowHeight", 950, type=int)
        self.resize(window_width, window_height)
        scrollarea.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        scrollarea.setWidget(widget)

        self.s11SmithChart = SmithChart("S11 Smith Chart")
        self.s21PolarChart = PolarChart("S21 Polar Plot")
        self.s11LogMag = LogMagChart("S11 Return Loss")
        self.s21LogMag = LogMagChart("S21 Gain")
        self.s11Phase = PhaseChart("S11 Phase")
        self.s21Phase = PhaseChart("S21 Phase")
        self.s11VSWR = VSWRChart("S11 VSWR")
        self.s11QualityFactor = QualityFactorChart("S11 Quality Factor")
        self.s11RealImaginary = RealImaginaryChart("S11 R+jX")

        self.s11charts: List[Chart] = []
        self.s11charts.append(self.s11SmithChart)
        self.s11charts.append(self.s11LogMag)
        self.s11charts.append(self.s11Phase)
        self.s11charts.append(self.s11VSWR)
        self.s11charts.append(self.s11RealImaginary)
        self.s11charts.append(self.s11QualityFactor)

        self.s21charts: List[Chart] = []
        self.s21charts.append(self.s21PolarChart)
        self.s21charts.append(self.s21LogMag)
        self.s21charts.append(self.s21Phase)

        self.charts = self.s11charts + self.s21charts

        self.tdr_chart = TDRChart("TDR")
        self.charts.append(self.tdr_chart)

        self.charts_layout = QtWidgets.QGridLayout()

        left_column = QtWidgets.QVBoxLayout()
        marker_column = QtWidgets.QVBoxLayout()
        self.marker_frame = QtWidgets.QFrame()
        marker_column.setContentsMargins(0, 0, 0, 0)
        self.marker_frame.setLayout(marker_column)
        right_column = QtWidgets.QVBoxLayout()
        right_column.addLayout(self.charts_layout)
        self.marker_frame.setHidden(not self.settings.value("MarkersVisible", True, bool))

        layout.addLayout(left_column, 0, 0)
        layout.addWidget(self.marker_frame, 0, 1)
        layout.addLayout(right_column, 0, 2)

        ################################################################################################################
        #  Sweep control
        ################################################################################################################

        sweep_control_box = QtWidgets.QGroupBox()
        sweep_control_box.setMaximumWidth(250)
        sweep_control_box.setTitle("Sweep control")
        sweep_control_layout = QtWidgets.QFormLayout(sweep_control_box)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)

        sweep_input_layout = QtWidgets.QHBoxLayout()
        sweep_input_left_layout = QtWidgets.QFormLayout()
        sweep_input_right_layout = QtWidgets.QFormLayout()
        sweep_input_layout.addLayout(sweep_input_left_layout)
        sweep_input_layout.addWidget(line)
        sweep_input_layout.addLayout(sweep_input_right_layout)
        sweep_control_layout.addRow(sweep_input_layout)

        self.sweepStartInput = QtWidgets.QLineEdit("")
        self.sweepStartInput.setMinimumWidth(60)
        self.sweepStartInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepStartInput.textEdited.connect(self.updateCenterSpan)

        sweep_input_left_layout.addRow(QtWidgets.QLabel("Start"), self.sweepStartInput)

        self.sweepEndInput = QtWidgets.QLineEdit("")
        self.sweepEndInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepEndInput.textEdited.connect(self.updateCenterSpan)

        sweep_input_left_layout.addRow(QtWidgets.QLabel("Stop"), self.sweepEndInput)

        self.sweepCenterInput = QtWidgets.QLineEdit("")
        self.sweepCenterInput.setMinimumWidth(60)
        self.sweepCenterInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepCenterInput.textEdited.connect(self.updateStartEnd)

        sweep_input_right_layout.addRow(QtWidgets.QLabel("Center"), self.sweepCenterInput)
        
        self.sweepSpanInput = QtWidgets.QLineEdit("")
        self.sweepSpanInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepSpanInput.textEdited.connect(self.updateStartEnd)

        sweep_input_right_layout.addRow(QtWidgets.QLabel("Span"), self.sweepSpanInput)

        self.sweepCountInput = QtWidgets.QLineEdit(self.settings.value("Segments", "1"))
        self.sweepCountInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepCountInput.setFixedWidth(60)
        self.sweepCountInput.textEdited.connect(self.updateStepSize)

        self.sweepStepLabel = QtWidgets.QLabel("Hz/step")
        self.sweepStepLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        segment_layout = QtWidgets.QHBoxLayout()
        segment_layout.addWidget(self.sweepCountInput)
        segment_layout.addWidget(self.sweepStepLabel)
        sweep_control_layout.addRow(QtWidgets.QLabel("Segments"), segment_layout)

        self.sweepSettingsWindow = SweepSettingsWindow(self)
        btn_sweep_settings_window = QtWidgets.QPushButton("Sweep settings")
        btn_sweep_settings_window.clicked.connect(self.displaySweepSettingsWindow)

        sweep_control_layout.addRow(btn_sweep_settings_window)

        self.sweepProgressBar = QtWidgets.QProgressBar()
        self.sweepProgressBar.setMaximum(100)
        self.sweepProgressBar.setValue(0)
        sweep_control_layout.addRow(self.sweepProgressBar)

        self.btnSweep = QtWidgets.QPushButton("Sweep")
        self.btnSweep.clicked.connect(self.sweep)
        self.btnStopSweep = QtWidgets.QPushButton("Stop")
        self.btnStopSweep.clicked.connect(self.stopSweep)
        self.btnStopSweep.setDisabled(True)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.btnSweep)
        btn_layout.addWidget(self.btnStopSweep)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout_widget = QtWidgets.QWidget()
        btn_layout_widget.setLayout(btn_layout)
        sweep_control_layout.addRow(btn_layout_widget)

        left_column.addWidget(sweep_control_box)

        ################################################################################################################
        #  Marker control
        ################################################################################################################

        marker_control_box = QtWidgets.QGroupBox()
        marker_control_box.setTitle("Markers")
        marker_control_box.setMaximumWidth(250)
        marker_control_layout = QtWidgets.QFormLayout(marker_control_box)

        marker1_color = self.settings.value("Marker1Color", QtGui.QColor(255, 0, 20), QtGui.QColor)
        marker1 = Marker("Marker 1", marker1_color)
        marker1.updated.connect(self.dataUpdated)
        label, layout = marker1.getRow()
        marker_control_layout.addRow(label, layout)
        self.markers.append(marker1)
        marker1.isMouseControlledRadioButton.setChecked(True)

        marker2_color = self.settings.value("Marker2Color", QtGui.QColor(20, 0, 255), QtGui.QColor)
        marker2 = Marker("Marker 2", marker2_color)
        marker2.updated.connect(self.dataUpdated)
        label, layout = marker2.getRow()
        marker_control_layout.addRow(label, layout)
        self.markers.append(marker2)

        marker3_color = self.settings.value("Marker3Color", QtGui.QColor(20, 255, 20), QtGui.QColor)
        marker3 = Marker("Marker 3", marker3_color)
        marker3.updated.connect(self.dataUpdated)
        label, layout = marker3.getRow()
        marker_control_layout.addRow(label, layout)

        self.markers.append(marker3)

        self.showMarkerButton = QtWidgets.QPushButton()
        if self.marker_frame.isHidden():
            self.showMarkerButton.setText("Show data")
        else:
            self.showMarkerButton.setText("Hide data")
        self.showMarkerButton.clicked.connect(self.toggleMarkerFrame)
        marker_control_layout.addRow(self.showMarkerButton)

        for c in self.charts:
            c.setMarkers(self.markers)
        left_column.addWidget(marker_control_box)

        marker_column.addWidget(self.markers[0].getGroupBox())
        marker_column.addWidget(self.markers[1].getGroupBox())
        marker_column.addWidget(self.markers[2].getGroupBox())

        ################################################################################################################
        #  Statistics/analysis
        ################################################################################################################

        s11_control_box = QtWidgets.QGroupBox()
        s11_control_box.setTitle("S11")
        s11_control_layout = QtWidgets.QFormLayout()
        s11_control_box.setLayout(s11_control_layout)

        self.s11_min_swr_label = QtWidgets.QLabel()
        s11_control_layout.addRow("Min VSWR:", self.s11_min_swr_label)
        self.s11_min_rl_label = QtWidgets.QLabel()
        s11_control_layout.addRow("Return loss:", self.s11_min_rl_label)

        marker_column.addWidget(s11_control_box)

        s21_control_box = QtWidgets.QGroupBox()
        s21_control_box.setTitle("S21")
        s21_control_layout = QtWidgets.QFormLayout()
        s21_control_box.setLayout(s21_control_layout)

        self.s21_min_gain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Min gain:", self.s21_min_gain_label)

        self.s21_max_gain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Max gain:", self.s21_max_gain_label)

        marker_column.addWidget(s21_control_box)

        marker_column.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding))

        ################################################################################################################
        # TDR
        ################################################################################################################

        self.tdr_window = TDRWindow(self)
        self.tdr_chart.tdrWindow = self.tdr_window

        tdr_control_box = QtWidgets.QGroupBox()
        tdr_control_box.setTitle("TDR")
        tdr_control_layout = QtWidgets.QFormLayout()
        tdr_control_box.setLayout(tdr_control_layout)
        tdr_control_box.setMaximumWidth(250)

        self.tdr_result_label = QtWidgets.QLabel()
        tdr_control_layout.addRow("Estimated cable length:", self.tdr_result_label)

        self.tdr_button = QtWidgets.QPushButton("Time Domain Reflectometry ...")
        self.tdr_button.clicked.connect(self.displayTDRWindow)

        tdr_control_layout.addRow(self.tdr_button)

        left_column.addWidget(tdr_control_box)

        ################################################################################################################
        #  Spacer
        ################################################################################################################

        left_column.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding))

        ################################################################################################################
        #  Reference control
        ################################################################################################################

        reference_control_box = QtWidgets.QGroupBox()
        reference_control_box.setMaximumWidth(250)
        reference_control_box.setTitle("Reference sweep")
        reference_control_layout = QtWidgets.QFormLayout(reference_control_box)

        btnSetReference = QtWidgets.QPushButton("Set current as reference")
        btnSetReference.clicked.connect(self.setReference)
        self.btnResetReference = QtWidgets.QPushButton("Reset reference")
        self.btnResetReference.clicked.connect(self.resetReference)
        self.btnResetReference.setDisabled(True)

        reference_control_layout.addRow(btnSetReference)
        reference_control_layout.addRow(self.btnResetReference)

        left_column.addWidget(reference_control_box)

        ################################################################################################################
        #  Serial control
        ################################################################################################################

        serial_control_box = QtWidgets.QGroupBox()
        serial_control_box.setMaximumWidth(250)
        serial_control_box.setTitle("Serial port control")
        serial_control_layout = QtWidgets.QFormLayout(serial_control_box)
        self.serialPortInput = QtWidgets.QLineEdit(self.serialPort)
        self.serialPortInput.setAlignment(QtCore.Qt.AlignRight)
        btn_rescan_serial_port = QtWidgets.QPushButton("Rescan")
        btn_rescan_serial_port.setFixedWidth(60)
        btn_rescan_serial_port.clicked.connect(self.rescanSerialPort)
        serial_port_input_layout = QtWidgets.QHBoxLayout()
        serial_port_input_layout.addWidget(self.serialPortInput)
        serial_port_input_layout.addWidget(btn_rescan_serial_port)
        serial_control_layout.addRow(QtWidgets.QLabel("Serial port"), serial_port_input_layout)

        self.btnSerialToggle = QtWidgets.QPushButton("Connect to NanoVNA")
        self.btnSerialToggle.clicked.connect(self.serialButtonClick)
        serial_control_layout.addRow(self.btnSerialToggle)

        left_column.addWidget(serial_control_box)

        ################################################################################################################
        #  File control
        ################################################################################################################

        self.fileWindow = QtWidgets.QWidget()
        self.fileWindow.setWindowTitle("Files")
        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self.fileWindow, self.fileWindow.hide)
        file_window_layout = QtWidgets.QVBoxLayout()
        self.fileWindow.setLayout(file_window_layout)

        reference_file_control_box = QtWidgets.QGroupBox("Import file")
        reference_file_control_layout = QtWidgets.QFormLayout(reference_file_control_box)
        self.referenceFileNameInput = QtWidgets.QLineEdit("")
        btn_reference_file_picker = QtWidgets.QPushButton("...")
        btn_reference_file_picker.setMaximumWidth(25)
        btn_reference_file_picker.clicked.connect(self.pickReferenceFile)
        reference_file_name_layout = QtWidgets.QHBoxLayout()
        reference_file_name_layout.addWidget(self.referenceFileNameInput)
        reference_file_name_layout.addWidget(btn_reference_file_picker)

        reference_file_control_layout.addRow(QtWidgets.QLabel("Filename"), reference_file_name_layout)
        file_window_layout.addWidget(reference_file_control_box)

        btn_load_reference = QtWidgets.QPushButton("Load reference")
        btn_load_reference.clicked.connect(self.loadReferenceFile)
        btn_load_sweep = QtWidgets.QPushButton("Load as sweep")
        btn_load_sweep.clicked.connect(self.loadSweepFile)
        reference_file_control_layout.addRow(btn_load_reference)
        reference_file_control_layout.addRow(btn_load_sweep)

        file_control_box = QtWidgets.QGroupBox()
        file_control_box.setTitle("Export file")
        file_control_box.setMaximumWidth(300)
        file_control_layout = QtWidgets.QFormLayout(file_control_box)
        self.fileNameInput = QtWidgets.QLineEdit("")
        btn_file_picker = QtWidgets.QPushButton("...")
        btn_file_picker.setMaximumWidth(25)
        btn_file_picker.clicked.connect(self.pickFile)
        file_name_layout = QtWidgets.QHBoxLayout()
        file_name_layout.addWidget(self.fileNameInput)
        file_name_layout.addWidget(btn_file_picker)

        file_control_layout.addRow(QtWidgets.QLabel("Filename"), file_name_layout)

        self.btnExportFile = QtWidgets.QPushButton("Export data S1P")
        self.btnExportFile.clicked.connect(self.exportFileS1P)
        file_control_layout.addRow(self.btnExportFile)

        self.btnExportFile = QtWidgets.QPushButton("Export data S2P")
        self.btnExportFile.clicked.connect(self.exportFileS2P)
        file_control_layout.addRow(self.btnExportFile)

        file_window_layout.addWidget(file_control_box)

        btn_open_file_window = QtWidgets.QPushButton("Files ...")
        btn_open_file_window.clicked.connect(self.displayFileWindow)

        ################################################################################################################
        #  Calibration
        ################################################################################################################

        btnOpenCalibrationWindow = QtWidgets.QPushButton("Calibration ...")
        self.calibrationWindow = CalibrationWindow(self)
        btnOpenCalibrationWindow.clicked.connect(self.displayCalibrationWindow)

        ################################################################################################################
        #  Display setup
        ################################################################################################################

        btn_display_setup = QtWidgets.QPushButton("Display setup ...")
        btn_display_setup.setMaximumWidth(250)
        self.displaySetupWindow = DisplaySettingsWindow(self)
        btn_display_setup.clicked.connect(self.displaySettingsWindow)

        btn_about = QtWidgets.QPushButton("About ...")
        btn_about.setMaximumWidth(250)
        btn_about.clicked.connect(lambda: QtWidgets.QMessageBox.about(self, "About NanoVNASaver",
                                                                      "NanoVNASaver version "
                                                                      + NanoVNASaver.version +
                                                                      "\n\n\N{COPYRIGHT SIGN} Copyright 2019 Rune B. Broberg\n" +
                                                                      "This program comes with ABSOLUTELY NO WARRANTY\n" +
                                                                      "This program is licensed under the GNU General Public License version 3\n\n" +
                                                                      "See https://mihtjel.github.io/nanovna-saver/ for further details"))

        button_grid = QtWidgets.QGridLayout()
        button_grid.addWidget(btn_open_file_window, 0, 0)
        button_grid.addWidget(btnOpenCalibrationWindow, 0, 1)
        button_grid.addWidget(btn_display_setup, 1, 0)
        button_grid.addWidget(btn_about, 1, 1)
        left_column.addLayout(button_grid)

        ################################################################################################################
        #  Right side
        ################################################################################################################

        self.worker.signals.updated.connect(self.dataUpdated)
        self.worker.signals.finished.connect(self.sweepFinished)
        self.worker.signals.sweepError.connect(self.showSweepError)

        logger.debug("Finished building interface")

    def rescanSerialPort(self):
        serial_port = self.getPort()
        self.serialPort = serial_port
        self.serialPortInput.setText(serial_port)

    # Get that windows port
    @staticmethod
    def getPort() -> str:
        device_list = list_ports.comports()
        for d in device_list:
            if (d.vid == VID and
                    d.pid == PID):
                port = d.device
                logger.info("Found NanoVNA (%04x %04x) on port %s", d.vid, d.pid, d.device)
                return port
        return ""

    def pickReferenceFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(directory=self.referenceFileNameInput.text(),
                                                            filter="Touchstone Files (*.s1p *.s2p);;All files (*.*)")
        if filename != "":
            self.referenceFileNameInput.setText(filename)

    def pickFile(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(directory=self.fileNameInput.text(),
                                                            filter="Touchstone Files (*.s1p *.s2p);;All files (*.*)")
        if filename != "":
            self.fileNameInput.setText(filename)

    def exportFileS1P(self):
        logger.debug("Save S1P file to %s", self.fileNameInput.text())
        if len(self.data) == 0:
            logger.warning("No data stored, nothing written.")
            return
        filename = self.fileNameInput.text()
        if filename == "":
            logger.warning("No filename entered, nothing saved.")
            return
        try:
            logger.debug("Opening %s for writing", filename)
            file = open(filename, "w+")
            logger.debug("Writing file")
            file.write("# Hz S RI R 50\n")
            for i in range(len(self.data)):
                if i == 0 or self.data[i].freq != self.data[i-1].freq:
                    file.write(str(self.data[i].freq) + " " + str(self.data[i].re) + " " + str(self.data[i].im) + "\n")
            file.close()
            logger.debug("File written")
        except Exception as e:
            logger.exception("Error during file export: %s", e)
            return

    def exportFileS2P(self):
        logger.debug("Save S2P file to %s", self.fileNameInput.text())
        if len(self.data) == 0 or len(self.data21) == 0:
            logger.warning("No data stored, nothing written.")
            return
        filename = self.fileNameInput.text()
        if filename == "":
            logger.warning("No filename entered, nothing saved.")
            return
        try:
            logger.debug("Opening %s for writing", filename)
            file = open(filename, "w+")
            logger.debug("Writing file")
            file.write("# Hz S RI R 50\n")
            for i in range(len(self.data)):
                if i == 0 or self.data[i].freq != self.data[i-1].freq:
                    file.write(str(self.data[i].freq) + " " + str(self.data[i].re) + " " + str(self.data[i].im) + " " +
                               str(self.data21[i].re) + " " + str(self.data21[i].im) + " 0 0 0 0\n")
            file.close()
            logger.debug("File written")
        except Exception as e:
            logger.exception("Error during file export: %s", e)
            return

    def serialButtonClick(self):
        if self.serial.is_open:
            self.stopSerial()
        else:
            self.startSerial()
        return

    def flushSerialBuffers(self):
        if self.serialLock.acquire():
            self.serial.write(b"\r\n\r\n")
            sleep(0.1)
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            sleep(0.1)
            self.serialLock.release()

    def startSerial(self):
        if self.serialLock.acquire():
            self.serialPort = self.serialPortInput.text()
            logger.info("Opening serial port %s", self.serialPort)
            try:
                self.serial = serial.Serial(port=self.serialPort, baudrate=115200)
                self.serial.timeout = 0.05
            except serial.SerialException as exc:
                logger.error("Tried to open %s and failed: %s", self.serialPort, exc)
                self.serialLock.release()
                return
            self.btnSerialToggle.setText("Disconnect")

            self.serialLock.release()
            sleep(0.05)

            self.flushSerialBuffers()
            sleep(0.05)

            logger.info(self.readFirmware())

            frequencies = self.readValues("frequencies")
            logger.info("Read starting frequency %s and end frequency %s", frequencies[0], frequencies[100])
            if int(frequencies[0]) == int(frequencies[100]) and (self.sweepStartInput.text() == "" or self.sweepEndInput.text() == ""):
                self.sweepStartInput.setText(frequencies[0])
                self.sweepEndInput.setText(str(int(frequencies[100]) + 100000))
            elif self.sweepStartInput.text() == "" or self.sweepEndInput.text() == "":
                self.sweepStartInput.setText(frequencies[0])
                self.sweepEndInput.setText(frequencies[100])

            logger.debug("Starting initial sweep")
            self.sweep()
            return

    def stopSerial(self):
        if self.serialLock.acquire():
            logger.info("Closing connection to NanoVNA")
            self.serial.close()
            self.serialLock.release()
            self.btnSerialToggle.setText("Connect to NanoVNA")

    def writeSerial(self, command):
        if not self.serial.is_open:
            logger.warning("Writing without serial port being opened (%s)", command)
            return
        if self.serialLock.acquire():
            try:
                self.serial.write(str(command + "\r").encode('ascii'))
                self.serial.readline()
            except serial.SerialException as exc:
                logger.exception("Exception while writing to serial port (%s): %s", command, exc)
            self.serialLock.release()
        return

    def setSweep(self, start, stop):
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " 101")

    def sweep(self):
        # Run the serial port update
        if not self.serial.is_open:
            return
        self.worker.stopped = False

        self.sweepProgressBar.setValue(0)
        self.btnSweep.setDisabled(True)
        self.btnStopSweep.setDisabled(False)
        for m in self.markers:
            m.resetLabels()
        self.s11_min_rl_label.setText("")
        self.s11_min_swr_label.setText("")
        self.s21_min_gain_label.setText("")
        self.s21_max_gain_label.setText("")
        self.tdr_result_label.setText("")

        if self.sweepCountInput.text().isdigit():
            self.settings.setValue("Segments", self.sweepCountInput.text())

        self.threadpool.start(self.worker)

    def stopSweep(self):
        self.worker.stopped = True

    def readFirmware(self):
        if self.serialLock.acquire():
            result = ""
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')
                #  Then send the command to read data
                self.serial.write("info\r".encode('ascii'))
                result = ""
                data = ""
                sleep(0.01)
                while "ch>" not in data:
                    data = self.serial.readline().decode('ascii')
                    result += data
            except serial.SerialException as exc:
                logger.exception("Exception while reading firmware data: %s", exc)
            self.serialLock.release()
            return result
        else:
            logger.error("Unable to acquire serial lock to read firmware.")
            return ""

    def readValues(self, value):
        if self.serialLock.acquire():
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')

                #  Then send the command to read data
                self.serial.write(str(value + "\r").encode('ascii'))
                result = ""
                data = ""
                sleep(0.05)
                while "ch>" not in data:
                    data = self.serial.readline().decode('ascii')
                    result += data
                values = result.split("\r\n")
            except serial.SerialException as exc:
                logger.exception("Exception while reading %s: %s", value, exc)

            self.serialLock.release()
            return values[1:102]
        else:
            logger.error("Unable to acquire serial lock to read %s", value)
            return

    def saveData(self, data, data12, source=None):
        if self.dataLock.acquire(blocking=True):
            self.data = data
            self.data21 = data12
        else:
            logger.error("Failed acquiring data lock while saving.")
        self.dataLock.release()
        if source is not None:
            self.sweepSource = source
        else:
            self.sweepSource = strftime("%Y-%m-%d %H:%M:%S", gmtime())

    def dataUpdated(self):
        if self.dataLock.acquire(blocking=True):
            for m in self.markers:
                m.findLocation(self.data)
                m.resetLabels()
                m.updateLabels(self.data, self.data21)

            for c in self.s11charts:
                c.setData(self.data)

            for c in self.s21charts:
                c.setData(self.data21)

            self.sweepProgressBar.setValue(self.worker.percentage)
            self.tdr_window.updateTDR()

            # Find the minimum S11 VSWR:
            minVSWR = 100
            minVSWRfreq = -1
            for d in self.data:
                _, _, vswr = self.vswr(d)
                if minVSWR > vswr > 0:
                    minVSWR = vswr
                    minVSWRfreq = d.freq

            if minVSWRfreq > -1:
                self.s11_min_swr_label.setText(str(round(minVSWR, 3)) + " @ " + self.formatFrequency(minVSWRfreq))
                self.s11_min_rl_label.setText(str(round(20*math.log10((minVSWR-1)/(minVSWR+1)), 3)) + " dB")
            else:
                self.s11_min_swr_label.setText("")
                self.s11_min_rl_label.setText("")
            minGain = 100
            minGainFreq = -1
            maxGain = -100
            maxGainFreq = -1
            for d in self.data21:
                gain = self.gain(d)
                if gain > maxGain:
                    maxGain = gain
                    maxGainFreq = d.freq
                if gain < minGain:
                    minGain = gain
                    minGainFreq = d.freq

            if maxGainFreq > -1:
                self.s21_min_gain_label.setText(str(round(minGain, 3)) + " dB @ " + self.formatFrequency(minGainFreq))
                self.s21_max_gain_label.setText(str(round(maxGain, 3)) + " dB @ " + self.formatFrequency(maxGainFreq))
            else:
                self.s21_min_gain_label.setText("")
                self.s21_max_gain_label.setText("")

        else:
            logger.error("Failed acquiring data lock while updating.")
        self.updateTitle()
        self.dataLock.release()

    @staticmethod
    def vswr(data: Datapoint):
        re50, im50 = NanoVNASaver.normalize50(data)
        mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
        # mag = math.sqrt(re * re + im * im)  # Is this even right?
        vswr = (1 + mag) / (1 - mag)
        return im50, re50, vswr

    @staticmethod
    def qualifyFactor(data: Datapoint):
        im50, re50, _ = NanoVNASaver.vswr(data)
        if re50 != 0:
            Q = im50 / re50
        else:
            Q = 0
        return abs(Q)

    @staticmethod
    def capacitanceEquivalent(im50, freq) -> str:
        if im50 == 0 or freq == 0:
            return "- pF"
        capacitance = 10**12/(freq * 2 * math.pi * im50)
        return str(round(-capacitance, 3)) + " pF"

    @staticmethod
    def inductanceEquivalent(im50, freq) -> str:
        if freq == 0:
            return "- nH"
        inductance = im50 / (freq * 2 * math.pi)
        return str(round(inductance * 1000000000, 3)) + " nH"

    @staticmethod
    def gain(data: Datapoint):
        re50, im50 = NanoVNASaver.normalize50(data)
        # Calculate the gain / reflection coefficient
        mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt(
            (re50 + 50) * (re50 + 50) + im50 * im50)
        return 20 * math.log10(mag)

    @staticmethod
    def normalize50(data):
        re = data.re
        im = data.im
        re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
        im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
        return re50, im50

    @staticmethod
    def admittance(data):
        re50, im50 = NanoVNASaver.normalize50(data)
        rp = re50 / (re50**2 + im50**2)
        xp = - im50 / (re50**2 + im50**2)
        return rp, xp

    def sweepFinished(self):
        self.sweepProgressBar.setValue(100)
        self.btnSweep.setDisabled(False)
        self.btnStopSweep.setDisabled(True)

    def updateCenterSpan(self):
        fstart = self.parseFrequency(self.sweepStartInput.text())
        fstop = self.parseFrequency(self.sweepEndInput.text())
        fspan = fstop - fstart
        fcenter = int(round((fstart+fstop)/2))
        if fspan < 0 or fstart < 0 or fstop < 0:
            return
        self.sweepSpanInput.setText(str(fspan))
        self.sweepCenterInput.setText(str(fcenter))
        self.updateStepSize()

    def updateStartEnd(self):
        fcenter = self.parseFrequency(self.sweepCenterInput.text())
        fspan = self.parseFrequency(self.sweepSpanInput.text())
        if fspan < 0 or fcenter < 0:
            return
        fstart = int(round(fcenter - fspan/2))
        fstop = int(round(fcenter + fspan/2))
        if fstart < 0 or fstop < 0:
            return
        self.sweepStartInput.setText(str(fstart))
        self.sweepEndInput.setText(str(fstop))
        self.updateStepSize()

    def updateStepSize(self):
        fspan = self.parseFrequency(self.sweepSpanInput.text())
        if fspan < 0:
            return
        if self.sweepCountInput.text().isdigit():
            segments = int(self.sweepCountInput.text())
            fstep = fspan / (segments * 101)
            self.sweepStepLabel.setText(self.formatShortFrequency(fstep) + "/step")

    @staticmethod
    def formatFrequency(freq):
        if freq < 1:
            return "- Hz"
        if math.log10(freq) < 3:
            return str(round(freq)) + " Hz"
        elif math.log10(freq) < 7:
            return "{:.3f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 8:
            return "{:.4f}".format(freq/1000000) + " MHz"
        else:
            return "{:.3f}".format(freq/1000000) + " MHz"

    @staticmethod
    def formatShortFrequency(freq):
        if freq < 1:
            return "- Hz"
        if math.log10(freq) < 3:
            return str(round(freq)) + " Hz"
        elif math.log10(freq) < 5:
            return "{:.3f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 6:
            return "{:.2f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 7:
            return "{:.1f}".format(freq/1000) + " kHz"
        elif math.log10(freq) < 8:
            return "{:.3f}".format(freq/1000000) + " MHz"
        elif math.log10(freq) < 9:
            return "{:.2f}".format(freq/1000000) + " MHz"
        else:
            return "{:.1f}".format(freq/1000000) + " MHz"

    @staticmethod
    def parseFrequency(freq: str):
        freq = freq.replace(" ", "")  # People put all sorts of weird whitespace in.
        if freq.isnumeric():
            return int(freq)

        multiplier = 1
        freq = freq.lower()

        if freq.endswith("k"):
            multiplier = 1000
            freq = freq[:-1]
        elif freq.endswith("m"):
            multiplier = 1000000
            freq = freq[:-1]

        if freq.isnumeric():
            return int(freq) * multiplier

        try:
            f = float(freq)
            return int(round(multiplier * f))
        except ValueError:
            # Okay, we couldn't parse this however much we tried.
            return -1

    def setReference(self, s11data=None, s21data=None, source=None):
        if not s11data:
            s11data = self.data
        if not s21data:
            s21data = self.data21
        self.referenceS11data = s11data
        for c in self.s11charts:
            c.setReference(s11data)

        self.referenceS21data = s21data
        for c in self.s21charts:
            c.setReference(s21data)
        self.btnResetReference.setDisabled(False)

        if source is not None:
            # Save the reference source info
            self.referenceSource = source
        else:
            self.referenceSource = self.sweepSource
        self.updateTitle()

    def updateTitle(self):
        title = self.baseTitle
        insert = ""
        if self.sweepSource != "":
            insert += "Sweep: " + self.sweepSource + " @ " + str(len(self.data)) + " points"
        if self.referenceSource != "":
            if insert != "":
                insert += ", "
            insert += "Reference: " + self.referenceSource + " @ " + str(len(self.referenceS11data)) + " points"
        if insert != "":
            title = title + " (" + insert + ")"
        self.setWindowTitle(title)

    def toggleMarkerFrame(self):
        if self.marker_frame.isHidden():
            self.marker_frame.setHidden(False)
            self.settings.setValue("MarkersVisible", True)
            self.showMarkerButton.setText("Hide data")
        else:
            self.marker_frame.setHidden(True)
            self.settings.setValue("MarkersVisible", False)
            self.showMarkerButton.setText("Show data")

    def resetReference(self):
        self.referenceS11data = []
        self.referenceS21data = []
        self.referenceSource = ""
        self.updateTitle()
        for c in self.charts:
            c.resetReference()
        self.btnResetReference.setDisabled(True)

    def loadReferenceFile(self):
        filename = self.referenceFileNameInput.text()
        if filename is not "":
            self.resetReference()
            t = Touchstone(filename)
            t.load()
            self.setReference(t.s11data, t.s21data, filename)

    def loadSweepFile(self):
        filename = self.referenceFileNameInput.text()
        if filename is not "":
            self.data = []
            self.data21 = []
            t = Touchstone(filename)
            t.load()
            self.saveData(t.s11data, t.s21data, filename)
            self.dataUpdated()

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(1100, 950)

    def displaySettingsWindow(self):
        self.displaySetupWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.displaySetupWindow)

    def displaySweepSettingsWindow(self):
        self.sweepSettingsWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.sweepSettingsWindow)

    def displayCalibrationWindow(self):
        self.calibrationWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.calibrationWindow)

    def displayFileWindow(self):
        self.fileWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.fileWindow)

    def displayTDRWindow(self):
        self.tdr_window.show()
        QtWidgets.QApplication.setActiveWindow(self.tdr_window)

    def showError(self, text):
        error_message = QtWidgets.QErrorMessage(self)
        error_message.showMessage(text)

    def showSweepError(self):
        self.showError(self.worker.error_message)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.worker.stopped = True
        self.settings.setValue("Marker1Color", self.markers[0].color)
        self.settings.setValue("Marker2Color", self.markers[1].color)
        self.settings.setValue("Marker3Color", self.markers[2].color)

        self.settings.setValue("WindowHeight", self.height())
        self.settings.setValue("WindowWidth", self.width())
        self.settings.sync()
        self.threadpool.waitForDone(2500)
        a0.accept()
        sys.exit()


class DisplaySettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()

        self.app = app
        self.setWindowTitle("Display settings")

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        display_options_box = QtWidgets.QGroupBox("Options")
        display_options_layout = QtWidgets.QFormLayout(display_options_box)

        self.show_lines_option = QtWidgets.QCheckBox("Show lines")
        show_lines_label = QtWidgets.QLabel("Displays a thin line between data points")
        self.show_lines_option.stateChanged.connect(self.changeShowLines)
        display_options_layout.addRow(self.show_lines_option, show_lines_label)

        self.dark_mode_option = QtWidgets.QCheckBox("Dark mode")
        dark_mode_label = QtWidgets.QLabel("Black background with white text")
        self.dark_mode_option.stateChanged.connect(self.changeDarkMode)
        display_options_layout.addRow(self.dark_mode_option, dark_mode_label)

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setFixedWidth(20)
        self.sweepColor = self.app.settings.value("SweepColor", defaultValue=QtGui.QColor(160, 140, 20, 128),
                                                  type=QtGui.QColor)
        self.setSweepColor(self.sweepColor)
        self.btnColorPicker.clicked.connect(lambda: self.setSweepColor(
                 QtWidgets.QColorDialog.getColor(self.sweepColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Sweep color", self.btnColorPicker)

        self.btnSecondaryColorPicker = QtWidgets.QPushButton("█")
        self.btnSecondaryColorPicker.setFixedWidth(20)
        self.secondarySweepColor = self.app.settings.value("SecondarySweepColor",
                                                           defaultValue=QtGui.QColor(20, 160, 140, 128),
                                                           type=QtGui.QColor)
        self.setSecondarySweepColor(self.secondarySweepColor)
        self.btnSecondaryColorPicker.clicked.connect(lambda: self.setSecondarySweepColor(
                 QtWidgets.QColorDialog.getColor(self.secondarySweepColor,
                                                 options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Second sweep color", self.btnSecondaryColorPicker)

        self.btnReferenceColorPicker = QtWidgets.QPushButton("█")
        self.btnReferenceColorPicker.setFixedWidth(20)
        self.referenceColor = self.app.settings.value("ReferenceColor", defaultValue=QtGui.QColor(0, 0, 255, 32),
                                                      type=QtGui.QColor)
        self.setReferenceColor(self.referenceColor)
        self.btnReferenceColorPicker.clicked.connect(lambda: self.setReferenceColor(
            QtWidgets.QColorDialog.getColor(self.referenceColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Reference color", self.btnReferenceColorPicker)

        layout.addWidget(display_options_box)

        color_options_box = QtWidgets.QGroupBox("Chart colors")
        color_options_layout = QtWidgets.QFormLayout(color_options_box)

        self.use_custom_colors = QtWidgets.QCheckBox("Use custom chart colors")
        self.use_custom_colors.stateChanged.connect(self.changeCustomColors)
        color_options_layout.addRow(self.use_custom_colors)

        self.btn_background_picker = QtWidgets.QPushButton("█")
        self.btn_background_picker.setFixedWidth(20)
        self.btn_background_picker.clicked.connect(lambda: self.setColor("background", QtWidgets.QColorDialog.getColor(self.backgroundColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow("Chart background", self.btn_background_picker)

        self.btn_foreground_picker = QtWidgets.QPushButton("█")
        self.btn_foreground_picker.setFixedWidth(20)
        self.btn_foreground_picker.clicked.connect(lambda: self.setColor("foreground", QtWidgets.QColorDialog.getColor(self.foregroundColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow("Chart foreground", self.btn_foreground_picker)
        
        self.btn_text_picker = QtWidgets.QPushButton("█")
        self.btn_text_picker.setFixedWidth(20)
        self.btn_text_picker.clicked.connect(lambda: self.setColor("text", QtWidgets.QColorDialog.getColor(self.textColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow("Chart text", self.btn_text_picker)

        layout.addWidget(color_options_box)

        font_options_box = QtWidgets.QGroupBox("Font")
        font_options_layout = QtWidgets.QFormLayout(font_options_box)
        self.font_dropdown = QtWidgets.QComboBox()
        self.font_dropdown.addItems(["7", "8", "9", "10", "11", "12"])
        font_size = self.app.settings.value("FontSize",
                                            defaultValue=str(QtWidgets.QApplication.instance().font().pointSize()),
                                            type=str)
        self.font_dropdown.setCurrentText(font_size)
        self.changeFont()

        self.font_dropdown.currentTextChanged.connect(self.changeFont)
        font_options_layout.addRow("Font size", self.font_dropdown)

        layout.addWidget(font_options_box)

        charts_box = QtWidgets.QGroupBox("Displayed charts")
        charts_layout = QtWidgets.QGridLayout(charts_box)

        # selections = ["S11 Smith chart",
        #               "S11 LogMag",
        #               "S11 VSWR",
        #               "S11 Phase",
        #               "S21 Smith chart",
        #               "S21 LogMag",
        #               "S21 Phase",
        #               "None"]

        selections = []

        for c in self.app.charts:
            selections.append(c.name)

        selections.append("None")

        chart00_selection = QtWidgets.QComboBox()
        chart00_selection.addItems(selections)
        chart00_selection.setCurrentIndex(selections.index(self.app.settings.value("Chart00", "S11 Smith Chart")))
        chart00_selection.currentTextChanged.connect(lambda: self.changeChart(0, 0, chart00_selection.currentText()))
        charts_layout.addWidget(chart00_selection, 0, 0)

        chart01_selection = QtWidgets.QComboBox()
        chart01_selection.addItems(selections)
        chart01_selection.setCurrentIndex(selections.index(self.app.settings.value("Chart01", "S11 Return Loss")))
        chart01_selection.currentTextChanged.connect(lambda: self.changeChart(0, 1, chart01_selection.currentText()))
        charts_layout.addWidget(chart01_selection, 0, 1)
        
        chart02_selection = QtWidgets.QComboBox()
        chart02_selection.addItems(selections)
        chart02_selection.setCurrentIndex(selections.index(self.app.settings.value("Chart02", "None")))
        chart02_selection.currentTextChanged.connect(lambda: self.changeChart(0, 2, chart02_selection.currentText()))
        charts_layout.addWidget(chart02_selection, 0, 2)

        chart10_selection = QtWidgets.QComboBox()
        chart10_selection.addItems(selections)
        chart10_selection.setCurrentIndex(selections.index(self.app.settings.value("Chart10", "S21 Polar Plot")))
        chart10_selection.currentTextChanged.connect(lambda: self.changeChart(1, 0, chart10_selection.currentText()))
        charts_layout.addWidget(chart10_selection, 1, 0)

        chart11_selection = QtWidgets.QComboBox()
        chart11_selection.addItems(selections)
        chart11_selection.setCurrentIndex(selections.index(self.app.settings.value("Chart11", "S21 Gain")))
        chart11_selection.currentTextChanged.connect(lambda: self.changeChart(1, 1, chart11_selection.currentText()))
        charts_layout.addWidget(chart11_selection, 1, 1)

        chart12_selection = QtWidgets.QComboBox()
        chart12_selection.addItems(selections)
        chart12_selection.setCurrentIndex(selections.index(self.app.settings.value("Chart12", "None")))
        chart12_selection.currentTextChanged.connect(lambda: self.changeChart(1, 2, chart12_selection.currentText()))
        charts_layout.addWidget(chart12_selection, 1, 2)

        self.changeChart(0, 0, chart00_selection.currentText())
        self.changeChart(0, 1, chart01_selection.currentText())
        self.changeChart(0, 2, chart02_selection.currentText())
        self.changeChart(1, 0, chart10_selection.currentText())
        self.changeChart(1, 1, chart11_selection.currentText())
        self.changeChart(1, 2, chart12_selection.currentText())

        layout.addWidget(charts_box)
        self.dark_mode_option.setChecked(self.app.settings.value("DarkMode", False, bool))
        self.show_lines_option.setChecked(self.app.settings.value("ShowLines", False, bool))

        self.backgroundColor = self.app.settings.value("BackgroundColor", defaultValue=QtGui.QColor("white"),
                                                       type=QtGui.QColor)
        self.foregroundColor = self.app.settings.value("ForegroundColor", defaultValue=QtGui.QColor("lightgray"),
                                                       type=QtGui.QColor)
        self.textColor = self.app.settings.value("TextColor", defaultValue=QtGui.QColor("black"),
                                                 type=QtGui.QColor)

        if self.app.settings.value("UseCustomColors", defaultValue=False, type=bool):
            self.dark_mode_option.setDisabled(True)
            self.dark_mode_option.setChecked(False)
            self.use_custom_colors.setChecked(True)
        else:
            self.btn_background_picker.setDisabled(True)
            self.btn_foreground_picker.setDisabled(True)
            self.btn_text_picker.setDisabled(True)

        p = self.btn_background_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.backgroundColor)
        self.btn_background_picker.setPalette(p)

        p = self.btn_foreground_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.foregroundColor)
        self.btn_foreground_picker.setPalette(p)

        p = self.btn_text_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.textColor)
        self.btn_text_picker.setPalette(p)

    def changeChart(self, x, y, chart):
        found = None
        for c in self.app.charts:
            if c.name == chart:
                found = c

        self.app.settings.setValue("Chart" + str(x) + str(y), chart)

        oldWidget = self.app.charts_layout.itemAtPosition(x, y)
        if oldWidget is not None:
            w = oldWidget.widget()
            self.app.charts_layout.removeWidget(w)
            w.hide()
        if found is not None:
            self.app.charts_layout.addWidget(found, x, y)
            if found.isHidden():
                found.show()

    def changeShowLines(self):
        state = self.show_lines_option.isChecked()
        self.app.settings.setValue("ShowLines", state)
        for c in self.app.charts:
            c.setDrawLines(state)

    def changeDarkMode(self):
        state = self.dark_mode_option.isChecked()
        self.app.settings.setValue("DarkMode", state)
        if state:
            for c in self.app.charts:
                c.setBackgroundColor(QtGui.QColor(QtCore.Qt.black))
                c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
                c.setTextColor(QtGui.QColor(QtCore.Qt.white))
        else:
            for c in self.app.charts:
                c.setBackgroundColor(QtGui.QColor(QtCore.Qt.white))
                c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
                c.setTextColor(QtGui.QColor(QtCore.Qt.black))

    def changeCustomColors(self):
        self.app.settings.setValue("UseCustomColors", self.use_custom_colors.isChecked())
        if self.use_custom_colors.isChecked():
            self.dark_mode_option.setDisabled(True)
            self.dark_mode_option.setChecked(False)
            self.btn_background_picker.setDisabled(False)
            self.btn_foreground_picker.setDisabled(False)
            self.btn_text_picker.setDisabled(False)
            for c in self.app.charts:
                c.setBackgroundColor(self.backgroundColor)
                c.setForegroundColor(self.foregroundColor)
                c.setTextColor(self.textColor)
        else:
            self.dark_mode_option.setDisabled(False)
            self.btn_background_picker.setDisabled(True)
            self.btn_foreground_picker.setDisabled(True)
            self.btn_text_picker.setDisabled(True)
            self.changeDarkMode()  # Reset to the default colors depending on Dark Mode setting

    def setColor(self, name: str, color: QtGui.QColor):
        if name == "background":
            p = self.btn_background_picker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btn_background_picker.setPalette(p)
            self.backgroundColor = color
            self.app.settings.setValue("BackgroundColor", color)
        elif name == "foreground":
            p = self.btn_foreground_picker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btn_foreground_picker.setPalette(p)
            self.foregroundColor = color
            self.app.settings.setValue("ForegroundColor", color)
        elif name == "text":
            p = self.btn_text_picker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btn_text_picker.setPalette(p)
            self.textColor = color
            self.app.settings.setValue("TextColor", color)
        self.changeCustomColors()

    def setSweepColor(self, color: QtGui.QColor):
        if color.isValid():
            self.sweepColor = color
            p = self.btnColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnColorPicker.setPalette(p)
            self.app.settings.setValue("SweepColor", color)
            self.app.settings.sync()
            for c in self.app.charts:
                c.setSweepColor(color)

    def setSecondarySweepColor(self, color: QtGui.QColor):
        if color.isValid():
            self.secondarySweepColor = color
            p = self.btnSecondaryColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnSecondaryColorPicker.setPalette(p)
            self.app.settings.setValue("SecondarySweepColor", color)
            self.app.settings.sync()
            for c in self.app.charts:
                c.setSecondarySweepColor(color)

    def setReferenceColor(self, color):
        if color.isValid():
            self.referenceColor = color
            p = self.btnReferenceColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnReferenceColorPicker.setPalette(p)
            self.app.settings.setValue("ReferenceColor", color)
            self.app.settings.sync()

            for c in self.app.charts:
                c.setReferenceColor(color)

    def changeFont(self):
        font_size = self.font_dropdown.currentText()
        self.app.settings.setValue("FontSize", font_size)
        app: QtWidgets.QApplication = QtWidgets.QApplication.instance()
        font = app.font()
        font.setPointSize(int(font_size))
        app.setFont(font)


class TDRWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()
        self.app = app

        self.td = []
        self.distance_axis = []

        self.setWindowTitle("TDR")

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.tdr_velocity_dropdown = QtWidgets.QComboBox()
        self.tdr_velocity_dropdown.addItem("Jelly filled (0.64)", 0.64)
        self.tdr_velocity_dropdown.addItem("Polyethylene (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("PTFE (Teflon) (0.70)", 0.70)
        self.tdr_velocity_dropdown.addItem("Pulp Insulation (0.72)", 0.72)
        self.tdr_velocity_dropdown.addItem("Foam or Cellular PE (0.78)", 0.78)
        self.tdr_velocity_dropdown.addItem("Semi-solid PE (SSPE) (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("Air (Helical spacers) (0.94)", 0.94)
        self.tdr_velocity_dropdown.insertSeparator(self.tdr_velocity_dropdown.count())
        # Lots of cable types added by Larry Goga, AE5CZ
        self.tdr_velocity_dropdown.addItem("RG-6/U PE 75\N{OHM SIGN} (Belden 8215) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-6/U Foam 75\N{OHM SIGN} (Belden 9290) (0.81)", 0.81)
        self.tdr_velocity_dropdown.addItem("RG-8/U PE 50\N{OHM SIGN} (Belden 8237) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-8/U Foam (Belden 8214) (0.78)", 0.78)
        self.tdr_velocity_dropdown.addItem("RG-8/U (Belden 9913) (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("RG-8X (Belden 9258) (0.82)", 0.82)
        self.tdr_velocity_dropdown.addItem("RG-11/U 75\N{OHM SIGN} Foam HDPE (Belden 9292) (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("RG-58/U 52\N{OHM SIGN} PE (Belden 9201) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-58A/U 54\N{OHM SIGN} Foam (Belden 8219) (0.73)", 0.73)
        self.tdr_velocity_dropdown.addItem("RG-59A/U PE 75\N{OHM SIGN} (Belden 8241) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-59A/U Foam 75\N{OHM SIGN} (Belden 8241F) (0.78)", 0.78)
        self.tdr_velocity_dropdown.addItem("RG-174 PE (Belden 8216)(0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG-174 Foam (Belden 7805R) (0.735)", 0.735)
        self.tdr_velocity_dropdown.addItem("RG-213/U PE (Belden 8267) (0.66)", 0.66)
        self.tdr_velocity_dropdown.addItem("RG316 (0.695)", 0.695)
        self.tdr_velocity_dropdown.addItem("RG402 (0.695)", 0.695)
        self.tdr_velocity_dropdown.addItem("LMR-240 (0.84)", 0.84)
        self.tdr_velocity_dropdown.addItem("LMR-240UF (0.80)", 0.80)
        self.tdr_velocity_dropdown.addItem("LMR-400 (0.85)", 0.85)
        self.tdr_velocity_dropdown.addItem("LMR400UF (0.83)", 0.83)
        self.tdr_velocity_dropdown.addItem("Davis Bury-FLEX (0.82)", 0.82)
        self.tdr_velocity_dropdown.insertSeparator(self.tdr_velocity_dropdown.count())
        self.tdr_velocity_dropdown.addItem("Custom", -1)

        self.tdr_velocity_dropdown.setCurrentIndex(1)  # Default to PE (0.66)

        self.tdr_velocity_dropdown.currentIndexChanged.connect(self.updateTDR)

        layout.addRow(self.tdr_velocity_dropdown)

        self.tdr_velocity_input = QtWidgets.QLineEdit()
        self.tdr_velocity_input.setDisabled(True)
        self.tdr_velocity_input.setText("0.66")
        self.tdr_velocity_input.textChanged.connect(self.app.dataUpdated)

        layout.addRow("Velocity factor", self.tdr_velocity_input)

        self.tdr_result_label = QtWidgets.QLabel()
        layout.addRow("Estimated cable length:", self.tdr_result_label)

        layout.addRow(self.app.tdr_chart)

    def updateTDR(self):
        c = 299792458
        if len(self.app.data) < 2:
            return

        if self.tdr_velocity_dropdown.currentData() == -1:
            self.tdr_velocity_input.setDisabled(False)
        else:
            self.tdr_velocity_input.setDisabled(True)
            self.tdr_velocity_input.setText(str(self.tdr_velocity_dropdown.currentData()))

        try:
            v = float(self.tdr_velocity_input.text())
        except ValueError:
            return

        step_size = self.app.data[1].freq - self.app.data[0].freq
        if step_size == 0:
            self.tdr_result_label.setText("")
            logger.info("Cannot compute cable length at 0 span")
            return

        s11 = []
        for d in self.app.data:
            s11.append(np.complex(d.re, d.im))

        window = np.blackman(len(self.app.data))

        windowed_s11 = window * s11

        self.td = np.abs(np.fft.ifft(windowed_s11, 2**14))

        time_axis = np.linspace(0, 1/step_size, 2**14)
        self.distance_axis = time_axis * v * c

        # peak = np.max(td)  # We should check that this is an actual *peak*, and not just a vague maximum
        index_peak = np.argmax(self.td)

        cable_len = round(self.distance_axis[index_peak]/2, 3)
        feet = math.floor(cable_len / 0.3048)
        inches = round(((cable_len / 0.3048) - feet)*12, 1)

        self.tdr_result_label.setText(str(cable_len) + " m (" + str(feet) + "ft " + str(inches) + "in)")
        self.app.tdr_result_label.setText(str(cable_len) + " m")
        self.app.tdr_chart.update()


class SweepSettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()

        self.app = app
        self.setWindowTitle("Sweep settings")

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QFormLayout()
        self.setLayout(layout)

        self.single_sweep_radiobutton = QtWidgets.QRadioButton("Single sweep")
        self.continuous_sweep_radiobutton = QtWidgets.QRadioButton("Continuous sweep")
        self.averaged_sweep_radiobutton = QtWidgets.QRadioButton("Averaged sweep")

        layout.addWidget(self.single_sweep_radiobutton)
        self.single_sweep_radiobutton.setChecked(True)
        layout.addWidget(self.continuous_sweep_radiobutton)
        layout.addWidget(self.averaged_sweep_radiobutton)

        self.averages = QtWidgets.QLineEdit("3")
        self.truncates = QtWidgets.QLineEdit("0")

        layout.addRow("Number of measurements to average", self.averages)
        layout.addRow("Number to discard", self.truncates)
        layout.addRow(QtWidgets.QLabel("Averaging allows discarding outlying samples to get better averages."))
        layout.addRow(QtWidgets.QLabel("Common values are 3/0, 5/2, 9/4 and 25/6."))

        self.continuous_sweep_radiobutton.toggled.connect(lambda: self.app.worker.setContinuousSweep(self.continuous_sweep_radiobutton.isChecked()))
        self.averaged_sweep_radiobutton.toggled.connect(self.updateAveraging)
        self.averages.textEdited.connect(self.updateAveraging)
        self.truncates.textEdited.connect(self.updateAveraging)

    def updateAveraging(self):
        self.app.worker.setAveraging(self.averaged_sweep_radiobutton.isChecked(),
                                     self.averages.text(),
                                     self.truncates.text())
