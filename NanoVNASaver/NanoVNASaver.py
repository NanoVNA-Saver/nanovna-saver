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
from time import sleep, strftime, localtime
from typing import List, Tuple

import numpy as np
import serial
import typing
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QModelIndex
from serial.tools import list_ports

from NanoVNASaver.Hardware import VNA, InvalidVNA, Version
from .Chart import Chart, PhaseChart, VSWRChart, PolarChart, SmithChart, LogMagChart, QualityFactorChart, TDRChart, \
    RealImaginaryChart
from .Calibration import CalibrationWindow, Calibration
from .Marker import Marker
from .SweepWorker import SweepWorker
from .Touchstone import Touchstone
from .Analysis import Analysis, LowPassAnalysis, HighPassAnalysis, BandPassAnalysis, BandStopAnalysis
from .about import version as ver

Datapoint = collections.namedtuple('Datapoint', 'freq re im')

VID = 1155
PID = 22336

logger = logging.getLogger(__name__)


class NanoVNASaver(QtWidgets.QWidget):
    version = ver

    def __init__(self):
        super().__init__()
        if getattr(sys, 'frozen', False):
            logger.debug("Running from pyinstaller bundle")
            self.icon = QtGui.QIcon(sys._MEIPASS + "/icon_48x48.png")
        else:
            self.icon = QtGui.QIcon("icon_48x48.png")
        self.setWindowIcon(self.icon)

        self.settings = QtCore.QSettings(QtCore.QSettings.IniFormat,
                                         QtCore.QSettings.UserScope,
                                         "NanoVNASaver", "NanoVNASaver")
        print("Settings: " + self.settings.fileName())
        self.threadpool = QtCore.QThreadPool()
        self.vna: VNA = InvalidVNA()
        self.worker = SweepWorker(self)

        self.worker.signals.updated.connect(self.dataUpdated)
        self.worker.signals.finished.connect(self.sweepFinished)
        self.worker.signals.sweepError.connect(self.showSweepError)

        self.bands = BandsModel()

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
        btn_sweep_settings_window = QtWidgets.QPushButton("Sweep settings ...")
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
            c.setBands(self.bands)
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

        self.analysis_window = AnalysisWindow(self)

        btn_show_analysis = QtWidgets.QPushButton("Analysis ...")
        btn_show_analysis.clicked.connect(self.displayAnalysisWindow)
        marker_column.addWidget(btn_show_analysis)

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
        self.fileWindow.setWindowIcon(self.icon)
        self.fileWindow.setMinimumWidth(200)
        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self.fileWindow, self.fileWindow.hide)
        file_window_layout = QtWidgets.QVBoxLayout()
        self.fileWindow.setLayout(file_window_layout)

        load_file_control_box = QtWidgets.QGroupBox("Import file")
        load_file_control_box.setMaximumWidth(300)
        load_file_control_layout = QtWidgets.QFormLayout(load_file_control_box)

        btn_load_sweep = QtWidgets.QPushButton("Load as sweep")
        btn_load_sweep.clicked.connect(self.loadSweepFile)
        btn_load_reference = QtWidgets.QPushButton("Load reference")
        btn_load_reference.clicked.connect(self.loadReferenceFile)
        load_file_control_layout.addRow(btn_load_sweep)
        load_file_control_layout.addRow(btn_load_reference)

        file_window_layout.addWidget(load_file_control_box)

        save_file_control_box = QtWidgets.QGroupBox("Export file")
        save_file_control_box.setMaximumWidth(300)
        save_file_control_layout = QtWidgets.QFormLayout(save_file_control_box)

        btnExportFile = QtWidgets.QPushButton("Save file (S1P)")
        btnExportFile.clicked.connect(self.exportFileS1P)
        save_file_control_layout.addRow(btnExportFile)

        btnExportFile = QtWidgets.QPushButton("Save file (S2P)")
        btnExportFile.clicked.connect(self.exportFileS2P)
        save_file_control_layout.addRow(btnExportFile)

        file_window_layout.addWidget(save_file_control_box)

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

        self.aboutWindow = AboutWindow(self)

        btn_about = QtWidgets.QPushButton("About ...")
        btn_about.setMaximumWidth(250)

        btn_about.clicked.connect(self.displayAboutWindow)

        button_grid = QtWidgets.QGridLayout()
        button_grid.addWidget(btn_open_file_window, 0, 0)
        button_grid.addWidget(btnOpenCalibrationWindow, 0, 1)
        button_grid.addWidget(btn_display_setup, 1, 0)
        button_grid.addWidget(btn_about, 1, 1)
        left_column.addLayout(button_grid)

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

    def exportFileS1P(self):
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("s1p")
        filedialog.setNameFilter("Touchstone Files (*.s1p *.s2p);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        selected = filedialog.exec()
        if selected:
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if filename == "":
            logger.debug("No file name selected.")
            return
        logger.debug("Save S1P file to %s", filename)
        if len(self.data) == 0:
            logger.warning("No data stored, nothing written.")
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
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("s2p")
        filedialog.setNameFilter("Touchstone Files (*.s1p *.s2p);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        selected = filedialog.exec()
        if selected:
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if filename == "":
            logger.debug("No file name selected.")
            return
        logger.debug("Save S2P file to %s", filename)
        if len(self.data) == 0 or len(self.data21) == 0:
            logger.warning("No data stored, nothing written.")
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

            self.vna = VNA.getVNA(self, self.serial)
            self.worker.setVNA(self.vna)

            logger.info(self.vna.readFirmware())

            frequencies = self.vna.readFrequencies()
            if frequencies:
                logger.info("Read starting frequency %s and end frequency %s", frequencies[0], frequencies[100])
                if int(frequencies[0]) == int(frequencies[100]) and (self.sweepStartInput.text() == "" or self.sweepEndInput.text() == ""):
                    self.sweepStartInput.setText(frequencies[0])
                    self.sweepEndInput.setText(str(int(frequencies[100]) + 100000))
                elif self.sweepStartInput.text() == "" or self.sweepEndInput.text() == "":
                    self.sweepStartInput.setText(frequencies[0])
                    self.sweepEndInput.setText(frequencies[100])
                self.sweepStartInput.textChanged.emit(self.sweepStartInput.text())
            else:
                logger.warning("No frequencies read")
                return
            logger.debug("Starting initial sweep")
            self.sweep()
            return

    def stopSerial(self):
        if self.serialLock.acquire():
            logger.info("Closing connection to NanoVNA")
            self.serial.close()
            self.serialLock.release()
            self.btnSerialToggle.setText("Connect to NanoVNA")

    def toggleSweepSettings(self, disabled):
        self.sweepStartInput.setDisabled(disabled)
        self.sweepEndInput.setDisabled(disabled)
        self.sweepSpanInput.setDisabled(disabled)
        self.sweepCenterInput.setDisabled(disabled)
        self.sweepCountInput.setDisabled(disabled)

    def sweep(self):
        # Run the serial port update
        if not self.serial.is_open:
            return
        self.worker.stopped = False

        self.sweepProgressBar.setValue(0)
        self.btnSweep.setDisabled(True)
        self.btnStopSweep.setDisabled(False)
        self.toggleSweepSettings(True)
        for m in self.markers:
            m.resetLabels()
        self.s11_min_rl_label.setText("")
        self.s11_min_swr_label.setText("")
        self.s21_min_gain_label.setText("")
        self.s21_max_gain_label.setText("")
        self.tdr_result_label.setText("")

        if self.sweepCountInput.text().isdigit():
            self.settings.setValue("Segments", self.sweepCountInput.text())

        logger.debug("Starting worker thread")
        self.threadpool.start(self.worker)

    def stopSweep(self):
        self.worker.stopped = True

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
            self.sweepSource = strftime("%Y-%m-%d %H:%M:%S", localtime())

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
                if minVSWR > 1:
                    self.s11_min_rl_label.setText(str(round(20*math.log10((minVSWR-1)/(minVSWR+1)), 3)) + " dB")
                else:
                    # Infinite return loss?
                    self.s11_min_rl_label.setText("\N{INFINITY} dB")
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
        try:
            mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
            vswr = (1 + mag) / (1 - mag)
        except ZeroDivisionError as e:
            vswr = 1
        return im50, re50, vswr

    @staticmethod
    def qualifyFactor(data: Datapoint):
        im50, re50, _ = NanoVNASaver.vswr(data)
        if re50 != 0:
            Q = abs(im50 / re50)
        else:
            Q = -1
        return Q

    @staticmethod
    def capacitanceEquivalent(im50, freq) -> str:
        if im50 == 0 or freq == 0:
            return "- pF"
        capacitance = 10**12/(freq * 2 * math.pi * im50)
        if abs(capacitance) > 10000:
            return str(round(-capacitance/1000, 2)) + " nF"
        elif abs(capacitance) > 1000:
            return str(round(-capacitance/1000, 3)) + " nF"
        elif abs(capacitance) > 10:
            return str(round(-capacitance, 2)) + " pF"
        else:
            return str(round(-capacitance, 3)) + " pF"

    @staticmethod
    def inductanceEquivalent(im50, freq) -> str:
        if freq == 0:
            return "- nH"
        inductance = im50 * 1000000000 / (freq * 2 * math.pi)
        if abs(inductance) > 10000:
            return str(round(inductance / 1000, 2)) + " μH"
        elif abs(inductance) > 1000:
            return str(round(inductance/1000, 3)) + " μH"
        elif abs(inductance) > 10:
            return str(round(inductance, 2)) + " nH"
        else:
            return str(round(inductance, 3)) + " nH"

    @staticmethod
    def gain(data: Datapoint):
        re50, im50 = NanoVNASaver.normalize50(data)
        # Calculate the gain / reflection coefficient
        mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt(
            (re50 + 50) * (re50 + 50) + im50 * im50)
        if mag > 0:
            return 20 * math.log10(mag)
        else:
            return 0

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
        self.toggleSweepSettings(False)

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
            if segments > 0:
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
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(filter="Touchstone Files (*.s1p *.s2p);;All files (*.*)")
        if filename != "":
            self.resetReference()
            t = Touchstone(filename)
            t.load()
            self.setReference(t.s11data, t.s21data, filename)

    def loadSweepFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(filter="Touchstone Files (*.s1p *.s2p);;All files (*.*)")
        if filename != "":
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

    def displayAnalysisWindow(self):
        self.analysis_window.show()
        QtWidgets.QApplication.setActiveWindow(self.analysis_window)

    def displayAboutWindow(self):
        self.aboutWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.aboutWindow)

    def showError(self, text):
        QtWidgets.QMessageBox.warning(self, "Error", text)

    def showSweepError(self):
        self.showError(self.worker.error_message)
        self.stopSerial()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.worker.stopped = True
        self.settings.setValue("Marker1Color", self.markers[0].color)
        self.settings.setValue("Marker2Color", self.markers[1].color)
        self.settings.setValue("Marker3Color", self.markers[2].color)

        self.settings.setValue("WindowHeight", self.height())
        self.settings.setValue("WindowWidth", self.width())
        self.settings.sync()
        self.bands.saveSettings()
        self.threadpool.waitForDone(2500)
        a0.accept()
        sys.exit()


class DisplaySettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()

        self.app = app
        self.setWindowTitle("Display settings")
        self.setWindowIcon(self.app.icon)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        display_options_box = QtWidgets.QGroupBox("Options")
        display_options_layout = QtWidgets.QFormLayout(display_options_box)

        returnloss_group = QtWidgets.QButtonGroup()
        self.returnloss_is_negative = QtWidgets.QRadioButton("Negative")
        self.returnloss_is_positive = QtWidgets.QRadioButton("Positive")
        returnloss_group.addButton(self.returnloss_is_positive)
        returnloss_group.addButton(self.returnloss_is_negative)

        display_options_layout.addRow("Return loss is:", self.returnloss_is_negative)
        display_options_layout.addRow("", self.returnloss_is_positive)

        if self.app.settings.value("ReturnLossPositive", False):
            self.returnloss_is_positive.setChecked(True)
        else:
            self.returnloss_is_negative.setChecked(True)

        self.returnloss_is_positive.toggled.connect(self.changeReturnLoss)

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

        self.btnSecondaryReferenceColorPicker = QtWidgets.QPushButton("█")
        self.btnSecondaryReferenceColorPicker.setFixedWidth(20)
        self.secondaryReferenceColor = self.app.settings.value("SecondaryReferenceColor",
                                                               defaultValue=QtGui.QColor(0, 0, 255, 32),
                                                               type=QtGui.QColor)
        self.setSecondaryReferenceColor(self.secondaryReferenceColor)
        self.btnSecondaryReferenceColorPicker.clicked.connect(lambda: self.setSecondaryReferenceColor(
            QtWidgets.QColorDialog.getColor(self.secondaryReferenceColor,
                                            options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Second reference color", self.btnSecondaryReferenceColorPicker)

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

        bands_box = QtWidgets.QGroupBox("Bands")
        bands_layout = QtWidgets.QFormLayout(bands_box)

        self.show_bands = QtWidgets.QCheckBox("Show bands")
        self.show_bands.setChecked(self.app.bands.enabled)
        self.show_bands.stateChanged.connect(lambda: self.setShowBands(self.show_bands.isChecked()))
        bands_layout.addRow(self.show_bands)

        self.btn_bands_picker = QtWidgets.QPushButton("█")
        self.btn_bands_picker.setFixedWidth(20)
        self.btn_bands_picker.clicked.connect(lambda: self.setColor("bands", QtWidgets.QColorDialog.getColor(self.bandsColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        bands_layout.addRow("Chart bands", self.btn_bands_picker)

        self.btn_manage_bands = QtWidgets.QPushButton("Manage bands")

        self.bandsWindow = BandsWindow(self.app)
        self.btn_manage_bands.clicked.connect(self.displayBandsWindow)

        bands_layout.addRow(self.btn_manage_bands)

        layout.addWidget(bands_box)

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
        self.bandsColor = self.app.settings.value("BandsColor", defaultValue=QtGui.QColor(128, 128, 128, 48),
                                                  type=QtGui.QColor)
        self.app.bands.color = self.bandsColor

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

        p = self.btn_bands_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.bandsColor)
        self.btn_bands_picker.setPalette(p)

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

    def changeReturnLoss(self):
        state = self.returnloss_is_positive.isChecked()
        self.app.settings.setValue("ReturnLossPositive", state)

        for m in self.app.markers:
            m.returnloss_is_positive = state
            m.updateLabels(self.app.data, self.app.data21)
        self.app.s11LogMag.isInverted = state
        self.app.s11LogMag.update()

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
        elif name == "bands":
            p = self.btn_bands_picker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btn_bands_picker.setPalette(p)
            self.bandsColor = color
            self.app.settings.setValue("BandsColor", color)
            self.app.bands.setColor(color)
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

    def setSecondaryReferenceColor(self, color):
        if color.isValid():
            self.secondaryReferenceColor = color
            p = self.btnSecondaryReferenceColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnSecondaryReferenceColorPicker.setPalette(p)
            self.app.settings.setValue("SecondaryReferenceColor", color)
            self.app.settings.sync()

            for c in self.app.charts:
                c.setSecondaryReferenceColor(color)

    def setShowBands(self, show_bands):
        self.app.bands.enabled = show_bands
        self.app.bands.settings.setValue("ShowBands", show_bands)
        self.app.bands.settings.sync()
        for c in self.app.charts:
            c.update()

    def changeFont(self):
        font_size = self.font_dropdown.currentText()
        self.app.settings.setValue("FontSize", font_size)
        app: QtWidgets.QApplication = QtWidgets.QApplication.instance()
        font = app.font()
        font.setPointSize(int(font_size))
        app.setFont(font)

    def displayBandsWindow(self):
        self.bandsWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.bandsWindow)


class AboutWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()
        self.app = app

        self.setWindowTitle("About NanoVNASaver")
        self.setWindowIcon(self.app.icon)
        top_layout = QtWidgets.QHBoxLayout()
        self.setLayout(top_layout)
        #self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background, QtGui.QColor("white"))
        self.setPalette(pal)
        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        icon_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(icon_layout)
        icon = QtWidgets.QLabel()
        icon.setPixmap(self.app.icon.pixmap(128, 128))
        icon_layout.addWidget(icon)
        icon_layout.addStretch()

        layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(layout)

        layout.addWidget(QtWidgets.QLabel("NanoVNASaver version " + NanoVNASaver.version))
        layout.addWidget(QtWidgets.QLabel(""))
        layout.addWidget(QtWidgets.QLabel("\N{COPYRIGHT SIGN} Copyright 2019 Rune B. Broberg"))
        layout.addWidget(QtWidgets.QLabel("This program comes with ABSOLUTELY NO WARRANTY"))
        layout.addWidget(QtWidgets.QLabel("This program is licensed under the GNU General Public License version 3"))
        layout.addWidget(QtWidgets.QLabel(""))
        link_label = QtWidgets.QLabel("For further details, see: " +
                                      "<a href=\"https://mihtjel.github.io/nanovna-saver/\">" +
                                      "https://mihtjel.github.io/nanovna-saver/</a>")
        link_label.setOpenExternalLinks(True)
        layout.addWidget(link_label)
        layout.addWidget(QtWidgets.QLabel(""))

        self.versionLabel = QtWidgets.QLabel("NanoVNA Firmware Version: Not connected.")
        layout.addWidget(self.versionLabel)

        layout.addStretch()

        btn_check_version = QtWidgets.QPushButton("Check for updates")
        btn_check_version.clicked.connect(self.findUpdates)

        self.updateLabel = QtWidgets.QLabel("Last checked: ")
        self.updateCheckBox = QtWidgets.QCheckBox("Check for updates on startup")

        self.updateCheckBox.toggled.connect(self.updateSettings)

        check_for_updates = self.app.settings.value("CheckForUpdates", "Ask")
        if check_for_updates == "Yes":
            self.updateCheckBox.setChecked(True)
            self.findUpdates(automatic = True)
        elif check_for_updates == "No":
            self.updateCheckBox.setChecked(False)
        else:
            logger.debug("Starting timer")
            QtCore.QTimer.singleShot(2000, self.askAboutUpdates)

        update_hbox = QtWidgets.QHBoxLayout()
        update_hbox.addWidget(btn_check_version)
        update_form = QtWidgets.QFormLayout()
        update_hbox.addLayout(update_form)
        update_hbox.addStretch()
        update_form.addRow(self.updateLabel)
        update_form.addRow(self.updateCheckBox)
        layout.addLayout(update_hbox)

        layout.addStretch()

        btn_ok = QtWidgets.QPushButton("Ok")
        btn_ok.clicked.connect(lambda: self.close())
        layout.addWidget(btn_ok)

    def show(self):
        super().show()
        self.updateLabels()

    def updateLabels(self):
        if self.app.vna.isValid():
            logger.debug("Valid VNA")
            v: Version = self.app.vna.version
            self.versionLabel.setText("NanoVNA Firmware Version: " + self.app.vna.name + " " + v.version_string)

    def updateSettings(self):
        if self.updateCheckBox.isChecked():
            self.app.settings.setValue("CheckForUpdates", "Yes")
        else:
            self.app.settings.setValue("CheckForUpdates", "No")

    def askAboutUpdates(self):
        logger.debug("Asking about automatic update checks")
        selection = QtWidgets.QMessageBox.question(self.app, "Enable checking for updates?",
                                                   "Would you like NanoVNA-Saver to check for updates automatically?")
        if selection == QtWidgets.QMessageBox.Yes:
            self.updateCheckBox.setChecked(True)
            self.app.settings.setValue("CheckForUpdates", "Yes")
            self.findUpdates()
        elif selection == QtWidgets.QMessageBox.No:
            self.updateCheckBox.setChecked(False)
            self.app.settings.setValue("CheckForUpdates", "No")
            QtWidgets.QMessageBox.information(self.app, "Checking for updates disabled",
                                              "You can check for updates using the \"About\" window.")
        else:
            self.app.settings.setValue("CheckForUpdates", "Ask")

    def findUpdates(self, automatic=False):
        from urllib import request, error
        import json
        update_url = "http://mihtjel.dk/nanovna-saver/latest.json"

        try:
            updates = json.load(request.urlopen(update_url, timeout=3))
            latest_version = Version(updates['version'])
            latest_url = updates['url']
        except error.HTTPError as e:
            logger.exception("Checking for updates produced an HTTP exception: %s", e)
            return
        except json.JSONDecodeError as e:
            logger.exception("Checking for updates provided an unparseable file: %s", e)
            return

        logger.info("Latest version is " + latest_version.version_string)
        this_version = Version(NanoVNASaver.version)
        logger.info("This is " + this_version.version_string)
        if latest_version > this_version:
            logger.info("New update available: %s!", latest_version)
            if automatic:
                QtWidgets.QMessageBox.information(self, "Updates available",
                                                  "There is a new update for NanoVNA-Saver available!\n" +
                                                  "Version " + latest_version.version_string + "\n\n" +
                                                  "Press \"About\" to find the update.")
            else:
                QtWidgets.QMessageBox.information(self, "Updates available",
                                                  "There is a new update for NanoVNA-Saver available!")
            self.updateLabel.setText("<a href=\"" + latest_url + "\">New version available</a>.")
            self.updateLabel.setOpenExternalLinks(True)
        else:
            # Probably don't show a message box, just update the screen?
            # Maybe consider showing it if not an automatic update.
            #
            # QtWidgets.QMessageBox.information(self, "No updates available", "There are no new updates available.")
            #
            self.updateLabel.setText("Last checked: " + strftime("%Y-%m-%d %H:%M:%S", localtime()))
        return


class TDRWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()
        self.app = app

        self.td = []
        self.distance_axis = []

        self.setWindowTitle("TDR")
        self.setWindowIcon(self.app.icon)

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

        self.td = np.abs(np.fft.ifft(windowed_s11, 2**16))

        time_axis = np.linspace(0, 1/step_size, 2**16)
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
        self.setWindowIcon(self.app.icon)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        settings_box = QtWidgets.QGroupBox("Settings")
        settings_layout = QtWidgets.QFormLayout(settings_box)

        self.single_sweep_radiobutton = QtWidgets.QRadioButton("Single sweep")
        self.continuous_sweep_radiobutton = QtWidgets.QRadioButton("Continuous sweep")
        self.averaged_sweep_radiobutton = QtWidgets.QRadioButton("Averaged sweep")

        settings_layout.addWidget(self.single_sweep_radiobutton)
        self.single_sweep_radiobutton.setChecked(True)
        settings_layout.addWidget(self.continuous_sweep_radiobutton)
        settings_layout.addWidget(self.averaged_sweep_radiobutton)

        self.averages = QtWidgets.QLineEdit("3")
        self.truncates = QtWidgets.QLineEdit("0")

        settings_layout.addRow("Number of measurements to average", self.averages)
        settings_layout.addRow("Number to discard", self.truncates)
        settings_layout.addRow(QtWidgets.QLabel("Averaging allows discarding outlying samples to get better averages."))
        settings_layout.addRow(QtWidgets.QLabel("Common values are 3/0, 5/2, 9/4 and 25/6."))

        self.continuous_sweep_radiobutton.toggled.connect(lambda: self.app.worker.setContinuousSweep(self.continuous_sweep_radiobutton.isChecked()))
        self.averaged_sweep_radiobutton.toggled.connect(self.updateAveraging)
        self.averages.textEdited.connect(self.updateAveraging)
        self.truncates.textEdited.connect(self.updateAveraging)

        layout.addWidget(settings_box)

        band_sweep_box = QtWidgets.QGroupBox("Sweep band")
        band_sweep_layout = QtWidgets.QFormLayout(band_sweep_box)

        self.band_list = QtWidgets.QComboBox()
        self.band_list.setModel(self.app.bands)
        self.band_list.currentIndexChanged.connect(self.updateCurrentBand)

        band_sweep_layout.addRow("Select band", self.band_list)

        self.band_pad_limits = QtWidgets.QCheckBox("Pad band limits (10%)")
        self.band_pad_limits.stateChanged.connect(self.updateCurrentBand)
        band_sweep_layout.addRow(self.band_pad_limits)

        self.band_limit_label = QtWidgets.QLabel()

        band_sweep_layout.addRow(self.band_limit_label)

        btn_set_band_sweep = QtWidgets.QPushButton("Set band sweep")
        btn_set_band_sweep.clicked.connect(self.setBandSweep)
        band_sweep_layout.addRow(btn_set_band_sweep)

        self.updateCurrentBand()

        layout.addWidget(band_sweep_box)

    def updateCurrentBand(self):
        index_start = self.band_list.model().index(self.band_list.currentIndex(), 1)
        index_stop = self.band_list.model().index(self.band_list.currentIndex(), 2)
        start = int(self.band_list.model().data(index_start, QtCore.Qt.ItemDataRole).value())
        stop = int(self.band_list.model().data(index_stop, QtCore.Qt.ItemDataRole).value())

        if self.band_pad_limits.isChecked():
            span = stop - start
            start -= round(span / 10)
            start = max(1, start)
            stop += round(span / 10)

        self.band_limit_label.setText("Sweep span: " + NanoVNASaver.formatShortFrequency(start) + " to " +
                                      NanoVNASaver.formatShortFrequency(stop))

    def setBandSweep(self):
        index_start = self.band_list.model().index(self.band_list.currentIndex(), 1)
        index_stop = self.band_list.model().index(self.band_list.currentIndex(), 2)
        start = int(self.band_list.model().data(index_start, QtCore.Qt.ItemDataRole).value())
        stop = int(self.band_list.model().data(index_stop, QtCore.Qt.ItemDataRole).value())

        if self.band_pad_limits.isChecked():
            span = stop - start
            start -= round(span / 10)
            start = max(1, start)
            stop += round(span / 10)

        self.app.sweepStartInput.setText(str(start))
        self.app.sweepEndInput.setText(str(stop))
        self.app.sweepEndInput.textEdited.emit(self.app.sweepEndInput.text())

    def updateAveraging(self):
        self.app.worker.setAveraging(self.averaged_sweep_radiobutton.isChecked(),
                                     self.averages.text(),
                                     self.truncates.text())


class BandsWindow(QtWidgets.QWidget):
    def __init__(self, app):
        super().__init__()

        self.app: NanoVNASaver = app
        self.setWindowTitle("Manage bands")
        self.setWindowIcon(self.app.icon)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setMinimumSize(500, 300)

        self.bands_table = QtWidgets.QTableView()
        self.bands_table.setModel(self.app.bands)
        self.bands_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.bands_table)

        btn_add_row = QtWidgets.QPushButton("Add row")
        btn_delete_row = QtWidgets.QPushButton("Delete row")
        btn_reset_bands = QtWidgets.QPushButton("Reset bands")
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(btn_add_row)
        btn_layout.addWidget(btn_delete_row)
        btn_layout.addWidget(btn_reset_bands)
        layout.addLayout(btn_layout)

        btn_add_row.clicked.connect(self.app.bands.addRow)
        btn_delete_row.clicked.connect(self.deleteRows)
        btn_reset_bands.clicked.connect(self.resetBands)

    def deleteRows(self):
        rows = self.bands_table.selectedIndexes()
        for row in rows:
            self.app.bands.removeRow(row.row())

    def resetBands(self):
        confirm = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning,
                                        "Confirm reset",
                                        "Are you sure you want to reset the bands to default?",
                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel).exec()
        if confirm == QtWidgets.QMessageBox.Yes:
            self.app.bands.resetBands()


class BandsModel(QtCore.QAbstractTableModel):
    bands: List[Tuple[str, int, int]] = []
    enabled = False
    color = QtGui.QColor(128, 128, 128, 48)

    # These bands correspond broadly to the Danish Amateur Radio allocation
    default_bands = ["2200 m;135700;137800",
                     "630 m;472000;479000",
                     "160 m;1800000;2000000",
                     "80 m;3500000;3800000",
                     "60 m;5250000;5450000",
                     "40 m;7000000;7200000",
                     "30 m;10100000;10150000",
                     "20 m;14000000;14350000",
                     "17 m;18068000;18168000",
                     "15 m;21000000;21450000",
                     "12 m;24890000;24990000",
                     "10 m;28000000;29700000",
                     "6 m;50000000;52000000",
                     "4 m;69887500;70512500",
                     "2 m;144000000;146000000",
                     "70 cm;432000000;438000000",
                     "23 cm;1240000000;1300000000"]

    def __init__(self):
        super().__init__()
        self.settings = QtCore.QSettings(QtCore.QSettings.IniFormat,
                                         QtCore.QSettings.UserScope,
                                         "NanoVNASaver", "Bands")
        self.settings.setIniCodec("UTF-8")
        self.enabled = self.settings.value("ShowBands", False, bool)

        stored_bands: List[str] = self.settings.value("bands", self.default_bands)
        if stored_bands:
            for b in stored_bands:
                (name, start, end) = b.split(";")
                self.bands.append((name, int(start), int(end)))

    def saveSettings(self):
        stored_bands = []
        for b in self.bands:
            stored_bands.append(b[0] + ";" + str(b[1]) + ";" + str(b[2]))
        self.settings.setValue("bands", stored_bands)
        self.settings.sync()

    def resetBands(self):
        self.bands = []
        for b in self.default_bands:
            (name, start, end) = b.split(";")
            self.bands.append((name, int(start), int(end)))
        self.layoutChanged.emit()
        self.saveSettings()

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 3

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.bands)

    def data(self, index: QModelIndex, role: int = ...) -> QtCore.QVariant:
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.ItemDataRole or role == QtCore.Qt.EditRole:
            return QtCore.QVariant(self.bands[index.row()][index.column()])
        elif role == QtCore.Qt.TextAlignmentRole:
            if index.column() == 0:
                return QtCore.QVariant(QtCore.Qt.AlignCenter)
            else:
                return QtCore.QVariant(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        else:
            return QtCore.QVariant()

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        if role == QtCore.Qt.EditRole and index.isValid():
            t = self.bands[index.row()]
            name = t[0]
            start = t[1]
            end = t[2]
            if index.column() == 0:
                name = value
            elif index.column() == 1:
                start = value
            elif index.column() == 2:
                end = value
            self.bands[index.row()] = (name, start, end)
            self.dataChanged.emit(index, index)
            self.saveSettings()
            return True
        return False

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        return self.createIndex(row, column)

    def addRow(self):
        self.bands.append(("New", 0, 0))
        self.dataChanged.emit(self.index(len(self.bands), 0), self.index(len(self.bands), 2))
        self.layoutChanged.emit()

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        self.bands.remove(self.bands[row])
        self.layoutChanged.emit()
        self.saveSettings()
        return True

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            if section == 0:
                return "Band"
            if section == 1:
                return "Start (Hz)"
            if section == 2:
                return "End (Hz)"
            else:
                return "Invalid"
        else:
            super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> QtCore.Qt.ItemFlags:
        if index.isValid():
            return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        else:
            super().flags(index)

    def setColor(self, color):
        self.color = color


class AnalysisWindow(QtWidgets.QWidget):
    analyses = []
    analysis: Analysis = None

    def __init__(self, app):
        super().__init__()

        self.app: NanoVNASaver = app
        self.setWindowTitle("Sweep analysis")
        self.setWindowIcon(self.app.icon)

        #self.setMinimumSize(400, 600)

        #self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        select_analysis_box = QtWidgets.QGroupBox("Select analysis")
        select_analysis_layout = QtWidgets.QFormLayout(select_analysis_box)
        self.analysis_list = QtWidgets.QComboBox()
        self.analysis_list.addItem("Low-pass filter", LowPassAnalysis(self.app))
        self.analysis_list.addItem("Band-pass filter", BandPassAnalysis(self.app))
        self.analysis_list.addItem("High-pass filter", HighPassAnalysis(self.app))
        self.analysis_list.addItem("Band-stop filter", BandStopAnalysis(self.app))
        select_analysis_layout.addRow("Analysis type", self.analysis_list)
        self.analysis_list.currentIndexChanged.connect(self.updateSelection)

        btn_run_analysis = QtWidgets.QPushButton("Run analysis")
        btn_run_analysis.clicked.connect(self.runAnalysis)
        select_analysis_layout.addRow(btn_run_analysis)

        analysis_box = QtWidgets.QGroupBox("Analysis")
        analysis_box.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.analysis_layout = QtWidgets.QVBoxLayout(analysis_box)

        layout.addWidget(select_analysis_box)
        layout.addWidget(analysis_box)

        self.updateSelection()

    def runAnalysis(self):
        if self.analysis is not None:
            self.analysis.runAnalysis()

    def updateSelection(self):
        self.analysis = self.analysis_list.currentData()
        old_item = self.analysis_layout.itemAt(0)
        if old_item is not None:
            old_widget = self.analysis_layout.itemAt(0).widget()
            self.analysis_layout.replaceWidget(old_widget, self.analysis.widget())
            old_widget.hide()
        else:
            self.analysis_layout.addWidget(self.analysis.widget())
        self.analysis.widget().show()
        self.update()
