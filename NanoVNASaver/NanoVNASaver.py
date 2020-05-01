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
import sys
import threading
from time import sleep, strftime, localtime
from typing import List, Tuple

import numpy as np
import scipy.signal as signal
import serial
import typing
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QModelIndex
from serial.tools import list_ports

from .Hardware import VNA, InvalidVNA, Version
from .RFTools import RFTools, Datapoint
from .Chart import Chart, PhaseChart, VSWRChart, PolarChart, SmithChart, LogMagChart, QualityFactorChart, TDRChart, \
    RealImaginaryChart, MagnitudeChart, MagnitudeZChart, CombinedLogMagChart, SParameterChart, PermeabilityChart, \
    GroupDelayChart, CapacitanceChart, InductanceChart
from .Calibration import CalibrationWindow, Calibration
from .Inputs import FrequencyInputWidget
from .Marker import Marker
from .SweepWorker import SweepWorker
from .Touchstone import Touchstone
from .Analysis import Analysis, LowPassAnalysis, HighPassAnalysis, BandPassAnalysis, BandStopAnalysis, \
    PeakSearchAnalysis, VSWRAnalysis, SimplePeakSearchAnalysis
from .about import version as ver

VID = 1155
PID = 22336

logger = logging.getLogger(__name__)


class NanoVNASaver(QtWidgets.QWidget):
    version = ver
    default_marker_colors = [QtGui.QColor(255, 0, 0),
                             QtGui.QColor(0, 255, 0),
                             QtGui.QColor(0, 0, 255),
                             QtGui.QColor(0, 255, 255),
                             QtGui.QColor(255, 0, 255),
                             QtGui.QColor(255, 255, 0)]

    dataAvailable = QtCore.pyqtSignal()
    scaleFactor = 1

    sweepTitle = ""

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
        self.worker.signals.fatalSweepError.connect(self.showFatalSweepError)

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

        # outer.setContentsMargins(2, 2, 2, 2)  # Small screen mode, reduce margins?

        self.s11SmithChart = SmithChart("S11 Smith Chart")
        self.s21PolarChart = PolarChart("S21 Polar Plot")
        self.s11SParameterChart = SParameterChart("S11 Real/Imaginary")
        self.s21SParameterChart = SParameterChart("S21 Real/Imaginary")
        self.s11LogMag = LogMagChart("S11 Return Loss")
        self.s21LogMag = LogMagChart("S21 Gain")
        self.s11Mag = MagnitudeChart("|S11|")
        self.s21Mag = MagnitudeChart("|S21|")
        self.s11MagZ = MagnitudeZChart("S11 |Z|")
        self.s11Phase = PhaseChart("S11 Phase")
        self.s21Phase = PhaseChart("S21 Phase")
        self.s11GroupDelay = GroupDelayChart("S11 Group Delay")
        self.s11CapacitanceChart = CapacitanceChart("S11 Serial C")
        self.s11InductanceChart = InductanceChart("S11 Serial L")
        self.s21GroupDelay = GroupDelayChart("S21 Group Delay", reflective=False)
        self.permabilityChart = PermeabilityChart("S11 R/\N{GREEK SMALL LETTER OMEGA} & X/\N{GREEK SMALL LETTER OMEGA}")
        self.s11VSWR = VSWRChart("S11 VSWR")
        self.s11QualityFactor = QualityFactorChart("S11 Quality Factor")
        self.s11RealImaginary = RealImaginaryChart("S11 R+jX")
        self.tdr_chart = TDRChart("TDR")
        self.tdr_mainwindow_chart = TDRChart("TDR")
        self.combinedLogMag = CombinedLogMagChart("S11 & S21 LogMag")

        # List of all the S11 charts, for selecting
        self.s11charts: List[Chart] = []
        self.s11charts.append(self.s11SmithChart)
        self.s11charts.append(self.s11LogMag)
        self.s11charts.append(self.s11Mag)
        self.s11charts.append(self.s11MagZ)
        self.s11charts.append(self.s11Phase)
        self.s11charts.append(self.s11GroupDelay)
        self.s11charts.append(self.s11VSWR)
        self.s11charts.append(self.s11RealImaginary)
        self.s11charts.append(self.s11QualityFactor)
        self.s11charts.append(self.s11SParameterChart)
        self.s11charts.append(self.s11CapacitanceChart)
        self.s11charts.append(self.s11InductanceChart)
        self.s11charts.append(self.permabilityChart)

        # List of all the S21 charts, for selecting
        self.s21charts: List[Chart] = []
        self.s21charts.append(self.s21PolarChart)
        self.s21charts.append(self.s21LogMag)
        self.s21charts.append(self.s21Mag)
        self.s21charts.append(self.s21Phase)
        self.s21charts.append(self.s21GroupDelay)
        self.s21charts.append(self.s21SParameterChart)

        # List of all charts that use both S11 and S21
        self.combinedCharts: List[Chart] = []
        self.combinedCharts.append(self.combinedLogMag)

        # List of all charts that can be selected for display
        self.selectable_charts = self.s11charts + self.s21charts + self.combinedCharts
        self.selectable_charts.append(self.tdr_mainwindow_chart)

        # List of all charts that subscribe to updates (including duplicates!)
        self.subscribing_charts = []
        self.subscribing_charts.extend(self.selectable_charts)
        self.subscribing_charts.append(self.tdr_chart)

        for c in self.subscribing_charts:
            c.popoutRequested.connect(self.popoutChart)

        self.charts_layout = QtWidgets.QGridLayout()

        left_column = QtWidgets.QVBoxLayout()
        self.marker_column = QtWidgets.QVBoxLayout()
        self.marker_frame = QtWidgets.QFrame()
        self.marker_column.setContentsMargins(0, 0, 0, 0)
        self.marker_frame.setLayout(self.marker_column)
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

        self.sweepStartInput = FrequencyInputWidget()
        self.sweepStartInput.setMinimumWidth(60)
        self.sweepStartInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepStartInput.textEdited.connect(self.updateCenterSpan)
        self.sweepStartInput.textChanged.connect(self.updateStepSize)
        sweep_input_left_layout.addRow(QtWidgets.QLabel("Start"), self.sweepStartInput)

        self.sweepEndInput = FrequencyInputWidget()
        self.sweepEndInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepEndInput.textEdited.connect(self.updateCenterSpan)
        self.sweepEndInput.textChanged.connect(self.updateStepSize)
        sweep_input_left_layout.addRow(QtWidgets.QLabel("Stop"), self.sweepEndInput)

        self.sweepCenterInput = FrequencyInputWidget()
        self.sweepCenterInput.setMinimumWidth(60)
        self.sweepCenterInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepCenterInput.textEdited.connect(self.updateStartEnd)

        sweep_input_right_layout.addRow(QtWidgets.QLabel("Center"), self.sweepCenterInput)
        
        self.sweepSpanInput = FrequencyInputWidget()
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
        self.btnSweep.setShortcut(QtCore.Qt.Key_W | QtCore.Qt.CTRL)
        self.btnStopSweep = QtWidgets.QPushButton("Stop")
        self.btnStopSweep.clicked.connect(self.stopSweep)
        self.btnStopSweep.setShortcut(QtCore.Qt.Key_Escape)
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
        self.marker_control_layout = QtWidgets.QFormLayout(marker_control_box)

        marker_count = max(self.settings.value("MarkerCount", 3, int), 1)
        for i in range(marker_count):
            if i < len(self.default_marker_colors):
                default_color = self.default_marker_colors[i]
            else:
                default_color = QtGui.QColor(QtCore.Qt.darkGray)
            color = self.settings.value("Marker" + str(i+1) + "Color", default_color)
            marker = Marker("Marker " + str(i+1), color)
            marker.updated.connect(self.markerUpdated)
            label, layout = marker.getRow()
            self.marker_control_layout.addRow(label, layout)
            self.markers.append(marker)
            if i == 0:
                marker.isMouseControlledRadioButton.setChecked(True)

        self.showMarkerButton = QtWidgets.QPushButton()
        if self.marker_frame.isHidden():
            self.showMarkerButton.setText("Show data")
        else:
            self.showMarkerButton.setText("Hide data")
        self.showMarkerButton.clicked.connect(self.toggleMarkerFrame)
        lock_radiobutton = QtWidgets.QRadioButton("Locked")
        lock_radiobutton.setLayoutDirection(QtCore.Qt.RightToLeft)
        lock_radiobutton.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.showMarkerButton)
        hbox.addWidget(lock_radiobutton)
        self.marker_control_layout.addRow(hbox)

        for c in self.subscribing_charts:
            c.setMarkers(self.markers)
            c.setBands(self.bands)
        left_column.addWidget(marker_control_box)

        self.marker_data_layout = QtWidgets.QVBoxLayout()
        self.marker_data_layout.setContentsMargins(0, 0, 0, 0)

        for m in self.markers:
            self.marker_data_layout.addWidget(m.getGroupBox())

        self.marker_column.addLayout(self.marker_data_layout)

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

        self.marker_column.addWidget(s11_control_box)

        s21_control_box = QtWidgets.QGroupBox()
        s21_control_box.setTitle("S21")
        s21_control_layout = QtWidgets.QFormLayout()
        s21_control_box.setLayout(s21_control_layout)

        self.s21_min_gain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Min gain:", self.s21_min_gain_label)

        self.s21_max_gain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Max gain:", self.s21_max_gain_label)

        self.marker_column.addWidget(s21_control_box)

        self.marker_column.addStretch(1)
        self.analysis_window = AnalysisWindow(self)

        btn_show_analysis = QtWidgets.QPushButton("Analysis ...")
        btn_show_analysis.clicked.connect(self.displayAnalysisWindow)
        self.marker_column.addWidget(btn_show_analysis)

        ################################################################################################################
        # TDR
        ################################################################################################################

        self.tdr_window = TDRWindow(self)
        self.tdr_chart.tdrWindow = self.tdr_window
        self.tdr_mainwindow_chart.tdrWindow = self.tdr_window
        self.tdr_window.updated.connect(self.tdr_chart.update)
        self.tdr_window.updated.connect(self.tdr_mainwindow_chart.update)

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

        left_column.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed,
                                                        QtWidgets.QSizePolicy.Expanding))

        ################################################################################################################
        #  Reference control
        ################################################################################################################

        reference_control_box = QtWidgets.QGroupBox()
        reference_control_box.setMaximumWidth(250)
        reference_control_box.setTitle("Reference sweep")
        reference_control_layout = QtWidgets.QFormLayout(reference_control_box)

        btn_set_reference = QtWidgets.QPushButton("Set current as reference")
        btn_set_reference.clicked.connect(self.setReference)
        self.btnResetReference = QtWidgets.QPushButton("Reset reference")
        self.btnResetReference.clicked.connect(self.resetReference)
        self.btnResetReference.setDisabled(True)

        reference_control_layout.addRow(btn_set_reference)
        reference_control_layout.addRow(self.btnResetReference)

        left_column.addWidget(reference_control_box)

        ################################################################################################################
        #  Serial control
        ################################################################################################################

        serial_control_box = QtWidgets.QGroupBox()
        serial_control_box.setMaximumWidth(250)
        serial_control_box.setTitle("Serial port control")
        serial_control_layout = QtWidgets.QFormLayout(serial_control_box)
        self.serialPortInput = QtWidgets.QComboBox()
        self.rescanSerialPort()
        self.serialPortInput.setEditable(True)
        btn_rescan_serial_port = QtWidgets.QPushButton("Rescan")
        btn_rescan_serial_port.setFixedWidth(60)
        btn_rescan_serial_port.clicked.connect(self.rescanSerialPort)
        serial_port_input_layout = QtWidgets.QHBoxLayout()
        serial_port_input_layout.addWidget(self.serialPortInput)
        serial_port_input_layout.addWidget(btn_rescan_serial_port)
        serial_control_layout.addRow(QtWidgets.QLabel("Serial port"), serial_port_input_layout)

        serial_button_layout = QtWidgets.QHBoxLayout()

        self.btnSerialToggle = QtWidgets.QPushButton("Connect to NanoVNA")
        self.btnSerialToggle.clicked.connect(self.serialButtonClick)
        serial_button_layout.addWidget(self.btnSerialToggle, stretch=1)

        self.deviceSettingsWindow = DeviceSettingsWindow(self)
        self.btnDeviceSettings = QtWidgets.QPushButton("Manage")
        self.btnDeviceSettings.clicked.connect(self.displayDeviceSettingsWindow)
        serial_button_layout.addWidget(self.btnDeviceSettings, stretch=0)
        serial_control_layout.addRow(serial_button_layout)
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

        btn_export_file = QtWidgets.QPushButton("Save file (S1P)")
        btn_export_file.clicked.connect(self.exportFileS1P)
        save_file_control_layout.addRow(btn_export_file)

        btn_export_file = QtWidgets.QPushButton("Save file (S2P)")
        btn_export_file.clicked.connect(self.exportFileS2P)
        save_file_control_layout.addRow(btn_export_file)

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
        self.serialPortInput.clear()
        for port in self.getPort():
            self.serialPortInput.insertItem(1, port)

    # Get that windows port
    @staticmethod
    def getPort() -> list:
        return_ports = []
        device_list = list_ports.comports()
        for d in device_list:
            if (d.vid == VID and
                    d.pid == PID):
                port = d.device
                logger.info("Found NanoVNA (%04x %04x) on port %s", d.vid, d.pid, d.device)
                return_ports.append(port)
        return return_ports

    def exportFileS1P(self):
        if len(self.data) == 0:
            # No data to save, alert the user
            QtWidgets.QMessageBox.warning(self, "No data to save", "There is no data to save.")
            return

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
        if len(self.data21) == 0:
            # No S21 data to save, alert the user
            QtWidgets.QMessageBox.warning(self, "No S21 data to save", "There is no S21 data to save.")
            return

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
            self.serialPort = self.serialPortInput.currentText()
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
            self.vna.validateInput = self.settings.value("SerialInputValidation", True, bool)
            self.worker.setVNA(self.vna)

            logger.info(self.vna.readFirmware())

            frequencies = self.vna.readFrequencies()
            if frequencies:
                logger.info("Read starting frequency %s and end frequency %s", frequencies[0], frequencies[100])
                if int(frequencies[0]) == int(frequencies[100]) and (self.sweepStartInput.text() == "" or
                                                                     self.sweepEndInput.text() == ""):
                    self.sweepStartInput.setText(RFTools.formatSweepFrequency(int(frequencies[0])))
                    self.sweepEndInput.setText(RFTools.formatSweepFrequency(int(frequencies[100]) + 100000))
                elif self.sweepStartInput.text() == "" or self.sweepEndInput.text() == "":
                    self.sweepStartInput.setText(RFTools.formatSweepFrequency(int(frequencies[0])))
                    self.sweepEndInput.setText(RFTools.formatSweepFrequency(int(frequencies[100])))
                self.sweepStartInput.textEdited.emit(self.sweepStartInput.text())
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
        elif self.sweepTitle != "":
            self.sweepSource = self.sweepTitle + " " + strftime("%Y-%m-%d %H:%M:%S", localtime())
        else:
            self.sweepSource = strftime("%Y-%m-%d %H:%M:%S", localtime())

    def markerUpdated(self, marker: Marker):
        if self.dataLock.acquire(blocking=True):
            marker.findLocation(self.data)
            for m in self.markers:
                m.resetLabels()
                m.updateLabels(self.data, self.data21)

            for c in self.subscribing_charts:
                c.update()
        self.dataLock.release()

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

            for c in self.combinedCharts:
                c.setCombinedData(self.data, self.data21)

            self.sweepProgressBar.setValue(self.worker.percentage)
            self.tdr_window.updateTDR()

            # Find the minimum S11 VSWR:
            min_vswr = 100
            min_vswr_freq = -1
            for d in self.data:
                vswr = d.vswr
                if min_vswr > vswr > 0:
                    min_vswr = vswr
                    min_vswr_freq = d.freq

            if min_vswr_freq > -1:
                self.s11_min_swr_label.setText(str(round(min_vswr, 3)) + " @ " + RFTools.formatFrequency(min_vswr_freq))
                if min_vswr > 1:
                    self.s11_min_rl_label.setText(str(round(20*math.log10((min_vswr-1)/(min_vswr+1)), 3)) + " dB")
                else:
                    # Infinite return loss?
                    self.s11_min_rl_label.setText("\N{INFINITY} dB")
            else:
                self.s11_min_swr_label.setText("")
                self.s11_min_rl_label.setText("")
            min_gain = 100
            min_gain_freq = -1
            max_gain = -100
            max_gain_freq = -1
            for d in self.data21:
                gain = d.gain
                if gain > max_gain:
                    max_gain = gain
                    max_gain_freq = d.freq
                if gain < min_gain:
                    min_gain = gain
                    min_gain_freq = d.freq

            if max_gain_freq > -1:
                self.s21_min_gain_label.setText(
                    str(round(min_gain, 3)) + " dB @ " + RFTools.formatFrequency(min_gain_freq))
                self.s21_max_gain_label.setText(
                    str(round(max_gain, 3)) + " dB @ " + RFTools.formatFrequency(max_gain_freq))
            else:
                self.s21_min_gain_label.setText("")
                self.s21_max_gain_label.setText("")

        else:
            logger.error("Failed acquiring data lock while updating.")
        self.updateTitle()
        self.dataLock.release()
        self.dataAvailable.emit()

    def sweepFinished(self):
        self.sweepProgressBar.setValue(100)
        self.btnSweep.setDisabled(False)
        self.btnStopSweep.setDisabled(True)
        self.toggleSweepSettings(False)

    def updateCenterSpan(self):
        fstart = RFTools.parseFrequency(self.sweepStartInput.text())
        fstop = RFTools.parseFrequency(self.sweepEndInput.text())
        fspan = fstop - fstart
        fcenter = int(round((fstart+fstop)/2))
        if fspan < 0 or fstart < 0 or fstop < 0:
            return
        self.sweepSpanInput.setText(RFTools.formatSweepFrequency(fspan))
        self.sweepCenterInput.setText(RFTools.formatSweepFrequency(fcenter))

    def updateStartEnd(self):
        fcenter = RFTools.parseFrequency(self.sweepCenterInput.text())
        fspan = RFTools.parseFrequency(self.sweepSpanInput.text())
        if fspan < 0 or fcenter < 0:
            return
        fstart = int(round(fcenter - fspan/2))
        fstop = int(round(fcenter + fspan/2))
        if fstart < 0 or fstop < 0:
            return
        self.sweepStartInput.setText(RFTools.formatSweepFrequency(fstart))
        self.sweepEndInput.setText(RFTools.formatSweepFrequency(fstop))

    def updateStepSize(self):
        fspan = RFTools.parseFrequency(self.sweepSpanInput.text())
        if fspan < 0:
            return
        if self.sweepCountInput.text().isdigit():
            segments = int(self.sweepCountInput.text())
            if segments > 0:
                fstep = fspan / (segments * 290 - 1)
                self.sweepStepLabel.setText(RFTools.formatShortFrequency(fstep) + "/step")

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

        for c in self.combinedCharts:
            c.setCombinedReference(s11data, s21data)

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
        for c in self.subscribing_charts:
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

    def displayDeviceSettingsWindow(self):
        self.deviceSettingsWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.deviceSettingsWindow)

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

    def showFatalSweepError(self):
        self.showError(self.worker.error_message)
        self.stopSerial()

    def showSweepError(self):
        self.showError(self.worker.error_message)
        self.serial.flushInput()  # Remove any left-over data
        self.sweepFinished()

    def popoutChart(self, chart: Chart):
        logger.debug("Requested popout for chart: %s", chart.name)
        new_chart = self.copyChart(chart)
        new_chart.isPopout = True
        new_chart.show()
        new_chart.setWindowTitle(new_chart.name)

    def copyChart(self, chart: Chart):
        new_chart = chart.copy()
        self.subscribing_charts.append(new_chart)
        if chart in self.s11charts:
            self.s11charts.append(new_chart)
        if chart in self.s21charts:
            self.s21charts.append(new_chart)
        if chart in self.combinedCharts:
            self.combinedCharts.append(new_chart)
        new_chart.popoutRequested.connect(self.popoutChart)
        return new_chart

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.worker.stopped = True
        self.settings.setValue("MarkerCount", len(self.markers))
        for i in range(len(self.markers)):
            self.settings.setValue("Marker" + str(i+1) + "Color", self.markers[i].color)

        self.settings.setValue("WindowHeight", self.height())
        self.settings.setValue("WindowWidth", self.width())
        self.settings.sync()
        self.bands.saveSettings()
        self.threadpool.waitForDone(2500)
        a0.accept()
        sys.exit()

    def changeFont(self, font: QtGui.QFont) -> None:
        qf_new = QtGui.QFontMetricsF(font)
        normal_font = QtGui.QFont(font)
        normal_font.setPointSize(8)
        qf_normal = QtGui.QFontMetricsF(normal_font)
        standard_string = "0.123456789 0.123456789 MHz \N{OHM SIGN}"  # Characters we would normally display
        new_width = qf_new.boundingRect(standard_string).width()
        old_width = qf_normal.boundingRect(standard_string).width()
        self.scaleFactor = new_width / old_width
        logger.debug("New font width: %f, normal font: %f, factor: %f", new_width, old_width, self.scaleFactor)
        # TODO: Update all the fixed widths to account for the scaling
        for m in self.markers:
            m.getGroupBox().setFont(font)
            m.setScale(self.scaleFactor)

    def setSweepTitle(self, title):
        self.sweepTitle = title
        for c in self.subscribing_charts:
            c.setSweepTitle(title)


class DisplaySettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()

        self.app = app
        self.setWindowTitle("Display settings")
        self.setWindowIcon(self.app.icon)

        self.marker_window = MarkerSettingsWindow(self.app)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        left_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(left_layout)

        display_options_box = QtWidgets.QGroupBox("Options")
        display_options_layout = QtWidgets.QFormLayout(display_options_box)

        self.returnloss_group = QtWidgets.QButtonGroup()
        self.returnloss_is_negative = QtWidgets.QRadioButton("Negative")
        self.returnloss_is_positive = QtWidgets.QRadioButton("Positive")
        self.returnloss_group.addButton(self.returnloss_is_positive)
        self.returnloss_group.addButton(self.returnloss_is_negative)

        display_options_layout.addRow("Return loss is:", self.returnloss_is_negative)
        display_options_layout.addRow("", self.returnloss_is_positive)

        if self.app.settings.value("ReturnLossPositive", False, bool):
            self.returnloss_is_positive.setChecked(True)
        else:
            self.returnloss_is_negative.setChecked(True)

        self.returnloss_is_positive.toggled.connect(self.changeReturnLoss)
        self.changeReturnLoss()

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
        self.referenceColor = self.app.settings.value("ReferenceColor", defaultValue=QtGui.QColor(0, 0, 255, 48),
                                                      type=QtGui.QColor)
        self.setReferenceColor(self.referenceColor)
        self.btnReferenceColorPicker.clicked.connect(lambda: self.setReferenceColor(
            QtWidgets.QColorDialog.getColor(self.referenceColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Reference color", self.btnReferenceColorPicker)

        self.btnSecondaryReferenceColorPicker = QtWidgets.QPushButton("█")
        self.btnSecondaryReferenceColorPicker.setFixedWidth(20)
        self.secondaryReferenceColor = self.app.settings.value("SecondaryReferenceColor",
                                                               defaultValue=QtGui.QColor(0, 0, 255, 48),
                                                               type=QtGui.QColor)
        self.setSecondaryReferenceColor(self.secondaryReferenceColor)
        self.btnSecondaryReferenceColorPicker.clicked.connect(lambda: self.setSecondaryReferenceColor(
            QtWidgets.QColorDialog.getColor(self.secondaryReferenceColor,
                                            options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Second reference color", self.btnSecondaryReferenceColorPicker)

        self.pointSizeInput = QtWidgets.QSpinBox()
        pointsize = self.app.settings.value("PointSize", 2, int)
        self.pointSizeInput.setValue(pointsize)
        self.changePointSize(pointsize)
        self.pointSizeInput.setMinimum(1)
        self.pointSizeInput.setMaximum(10)
        self.pointSizeInput.setSuffix(" px")
        self.pointSizeInput.setAlignment(QtCore.Qt.AlignRight)
        self.pointSizeInput.valueChanged.connect(self.changePointSize)
        display_options_layout.addRow("Point size", self.pointSizeInput)

        self.lineThicknessInput = QtWidgets.QSpinBox()
        linethickness = self.app.settings.value("LineThickness", 1, int)
        self.lineThicknessInput.setValue(linethickness)
        self.changeLineThickness(linethickness)
        self.lineThicknessInput.setMinimum(1)
        self.lineThicknessInput.setMaximum(10)
        self.lineThicknessInput.setSuffix(" px")
        self.lineThicknessInput.setAlignment(QtCore.Qt.AlignRight)
        self.lineThicknessInput.valueChanged.connect(self.changeLineThickness)
        display_options_layout.addRow("Line thickness", self.lineThicknessInput)

        self.markerSizeInput = QtWidgets.QSpinBox()
        markersize = self.app.settings.value("MarkerSize", 6, int)
        self.markerSizeInput.setValue(markersize)
        self.changeMarkerSize(markersize)
        self.markerSizeInput.setMinimum(4)
        self.markerSizeInput.setMaximum(20)
        self.markerSizeInput.setSingleStep(2)
        self.markerSizeInput.setSuffix(" px")
        self.markerSizeInput.setAlignment(QtCore.Qt.AlignRight)
        self.markerSizeInput.valueChanged.connect(self.changeMarkerSize)
        self.markerSizeInput.editingFinished.connect(self.validateMarkerSize)
        display_options_layout.addRow("Marker size", self.markerSizeInput)

        self.show_marker_number_option = QtWidgets.QCheckBox("Show marker numbers")
        show_marker_number_label = QtWidgets.QLabel("Displays the marker number next to the marker")
        self.show_marker_number_option.stateChanged.connect(self.changeShowMarkerNumber)
        display_options_layout.addRow(self.show_marker_number_option, show_marker_number_label)

        self.filled_marker_option = QtWidgets.QCheckBox("Filled markers")
        filled_marker_label = QtWidgets.QLabel("Shows the marker as a filled triangle")
        self.filled_marker_option.stateChanged.connect(self.changeFilledMarkers)
        display_options_layout.addRow(self.filled_marker_option, filled_marker_label)

        self.marker_tip_group = QtWidgets.QButtonGroup()
        self.marker_at_center = QtWidgets.QRadioButton("At the center of the marker")
        self.marker_at_tip = QtWidgets.QRadioButton("At the tip of the marker")
        self.marker_tip_group.addButton(self.marker_at_center)
        self.marker_tip_group.addButton(self.marker_at_tip)

        display_options_layout.addRow("Data point is:", self.marker_at_center)
        display_options_layout.addRow("", self.marker_at_tip)

        if self.app.settings.value("MarkerAtTip", False, bool):
            self.marker_at_tip.setChecked(True)
        else:
            self.marker_at_center.setChecked(True)

        self.marker_at_tip.toggled.connect(self.changeMarkerAtTip)
        self.changeMarkerAtTip()
        
        color_options_box = QtWidgets.QGroupBox("Chart colors")
        color_options_layout = QtWidgets.QFormLayout(color_options_box)

        self.use_custom_colors = QtWidgets.QCheckBox("Use custom chart colors")
        self.use_custom_colors.stateChanged.connect(self.changeCustomColors)
        color_options_layout.addRow(self.use_custom_colors)

        self.btn_background_picker = QtWidgets.QPushButton("█")
        self.btn_background_picker.setFixedWidth(20)
        self.btn_background_picker.clicked.connect(lambda: self.setColor("background",
                                                   QtWidgets.QColorDialog.getColor(self.backgroundColor,
                                                                      options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow("Chart background", self.btn_background_picker)

        self.btn_foreground_picker = QtWidgets.QPushButton("█")
        self.btn_foreground_picker.setFixedWidth(20)
        self.btn_foreground_picker.clicked.connect(lambda: self.setColor("foreground",
                                                   QtWidgets.QColorDialog.getColor(self.foregroundColor,
                                                                      options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow("Chart foreground", self.btn_foreground_picker)

        self.btn_text_picker = QtWidgets.QPushButton("█")
        self.btn_text_picker.setFixedWidth(20)
        self.btn_text_picker.clicked.connect(lambda: self.setColor("text",
                                             QtWidgets.QColorDialog.getColor(self.textColor,
                                                                      options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow("Chart text", self.btn_text_picker)

        right_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(right_layout)

        font_options_box = QtWidgets.QGroupBox("Font")
        font_options_layout = QtWidgets.QFormLayout(font_options_box)
        self.font_dropdown = QtWidgets.QComboBox()
        self.font_dropdown.addItems(["7", "8", "9", "10", "11", "12"])
        font_size = self.app.settings.value("FontSize",
                                            defaultValue="8",
                                            type=str)
        self.font_dropdown.setCurrentText(font_size)
        self.changeFont()

        self.font_dropdown.currentTextChanged.connect(self.changeFont)
        font_options_layout.addRow("Font size", self.font_dropdown)

        bands_box = QtWidgets.QGroupBox("Bands")
        bands_layout = QtWidgets.QFormLayout(bands_box)

        self.show_bands = QtWidgets.QCheckBox("Show bands")
        self.show_bands.setChecked(self.app.bands.enabled)
        self.show_bands.stateChanged.connect(lambda: self.setShowBands(self.show_bands.isChecked()))
        bands_layout.addRow(self.show_bands)

        self.btn_bands_picker = QtWidgets.QPushButton("█")
        self.btn_bands_picker.setFixedWidth(20)
        self.btn_bands_picker.clicked.connect(lambda: self.setColor("bands",
                                              QtWidgets.QColorDialog.getColor(self.bandsColor,
                                                                      options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        bands_layout.addRow("Chart bands", self.btn_bands_picker)

        self.btn_manage_bands = QtWidgets.QPushButton("Manage bands")

        self.bandsWindow = BandsWindow(self.app)
        self.btn_manage_bands.clicked.connect(self.displayBandsWindow)

        bands_layout.addRow(self.btn_manage_bands)

        vswr_marker_box = QtWidgets.QGroupBox("VSWR Markers")
        vswr_marker_layout = QtWidgets.QFormLayout(vswr_marker_box)

        self.vswrMarkers: List[float] = self.app.settings.value("VSWRMarkers", [], float)

        if isinstance(self.vswrMarkers, float):
            if self.vswrMarkers == 0:
                self.vswrMarkers = []
            else:
                # Single values from the .ini become floats rather than lists. Convert them.
                self.vswrMarkers = [self.vswrMarkers]

        self.btn_vswr_picker = QtWidgets.QPushButton("█")
        self.btn_vswr_picker.setFixedWidth(20)
        self.btn_vswr_picker.clicked.connect(lambda: self.setColor("vswr",
                                             QtWidgets.QColorDialog.getColor(self.vswrColor,
                                                                      options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        vswr_marker_layout.addRow("VSWR Markers", self.btn_vswr_picker)

        self.vswr_marker_dropdown = QtWidgets.QComboBox()
        vswr_marker_layout.addRow(self.vswr_marker_dropdown)

        if len(self.vswrMarkers) == 0:
            self.vswr_marker_dropdown.addItem("None")
        else:
            for m in self.vswrMarkers:
                self.vswr_marker_dropdown.addItem(str(m))
                for c in self.app.s11charts:
                    c.addSWRMarker(m)

        self.vswr_marker_dropdown.setCurrentIndex(0)
        btn_add_vswr_marker = QtWidgets.QPushButton("Add ...")
        btn_remove_vswr_marker = QtWidgets.QPushButton("Remove")
        vswr_marker_btn_layout = QtWidgets.QHBoxLayout()
        vswr_marker_btn_layout.addWidget(btn_add_vswr_marker)
        vswr_marker_btn_layout.addWidget(btn_remove_vswr_marker)
        vswr_marker_layout.addRow(vswr_marker_btn_layout)

        btn_add_vswr_marker.clicked.connect(self.addVSWRMarker)
        btn_remove_vswr_marker.clicked.connect(self.removeVSWRMarker)

        markers_box = QtWidgets.QGroupBox("Markers")
        markers_layout = QtWidgets.QFormLayout(markers_box)

        btn_add_marker = QtWidgets.QPushButton("Add")
        btn_add_marker.clicked.connect(self.addMarker)
        self.btn_remove_marker = QtWidgets.QPushButton("Remove")
        self.btn_remove_marker.clicked.connect(self.removeMarker)
        btn_marker_settings = QtWidgets.QPushButton("Settings ...")
        btn_marker_settings.clicked.connect(self.displayMarkerWindow)

        marker_btn_layout = QtWidgets.QHBoxLayout()
        marker_btn_layout.addWidget(btn_add_marker)
        marker_btn_layout.addWidget(self.btn_remove_marker)
        marker_btn_layout.addWidget(btn_marker_settings)

        markers_layout.addRow(marker_btn_layout)

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

        for c in self.app.selectable_charts:
            selections.append(c.name)

        selections.append("None")
        chart00_selection = QtWidgets.QComboBox()
        chart00_selection.addItems(selections)
        chart00 = self.app.settings.value("Chart00", "S11 Smith Chart")
        if chart00_selection.findText(chart00) > -1:
            chart00_selection.setCurrentText(chart00)
        else:
            chart00_selection.setCurrentText("S11 Smith Chart")
        chart00_selection.currentTextChanged.connect(lambda: self.changeChart(0, 0, chart00_selection.currentText()))
        charts_layout.addWidget(chart00_selection, 0, 0)

        chart01_selection = QtWidgets.QComboBox()
        chart01_selection.addItems(selections)
        chart01 = self.app.settings.value("Chart01", "S11 Return Loss")
        if chart01_selection.findText(chart01) > -1:
            chart01_selection.setCurrentText(chart01)
        else:
            chart01_selection.setCurrentText("S11 Return Loss")
        chart01_selection.currentTextChanged.connect(lambda: self.changeChart(0, 1, chart01_selection.currentText()))
        charts_layout.addWidget(chart01_selection, 0, 1)

        chart02_selection = QtWidgets.QComboBox()
        chart02_selection.addItems(selections)
        chart02 = self.app.settings.value("Chart02", "None")
        if chart02_selection.findText(chart02) > -1:
            chart02_selection.setCurrentText(chart02)
        else:
            chart02_selection.setCurrentText("None")
        chart02_selection.currentTextChanged.connect(lambda: self.changeChart(0, 2, chart02_selection.currentText()))
        charts_layout.addWidget(chart02_selection, 0, 2)

        chart10_selection = QtWidgets.QComboBox()
        chart10_selection.addItems(selections)
        chart10 = self.app.settings.value("Chart10", "S21 Polar Plot")
        if chart10_selection.findText(chart10) > -1:
            chart10_selection.setCurrentText(chart10)
        else:
            chart10_selection.setCurrentText("S21 Polar Plot")
        chart10_selection.currentTextChanged.connect(lambda: self.changeChart(1, 0, chart10_selection.currentText()))
        charts_layout.addWidget(chart10_selection, 1, 0)

        chart11_selection = QtWidgets.QComboBox()
        chart11_selection.addItems(selections)
        chart11 = self.app.settings.value("Chart11", "S21 Gain")
        if chart11_selection.findText(chart11) > -1:
            chart11_selection.setCurrentText(chart11)
        else:
            chart11_selection.setCurrentText("S21 Gain")
        chart11_selection.currentTextChanged.connect(lambda: self.changeChart(1, 1, chart11_selection.currentText()))
        charts_layout.addWidget(chart11_selection, 1, 1)

        chart12_selection = QtWidgets.QComboBox()
        chart12_selection.addItems(selections)
        chart12 = self.app.settings.value("Chart12", "None")
        if chart12_selection.findText(chart12) > -1:
            chart12_selection.setCurrentText(chart12)
        else:
            chart12_selection.setCurrentText("None")
        chart12_selection.currentTextChanged.connect(lambda: self.changeChart(1, 2, chart12_selection.currentText()))
        charts_layout.addWidget(chart12_selection, 1, 2)

        self.changeChart(0, 0, chart00_selection.currentText())
        self.changeChart(0, 1, chart01_selection.currentText())
        self.changeChart(0, 2, chart02_selection.currentText())
        self.changeChart(1, 0, chart10_selection.currentText())
        self.changeChart(1, 1, chart11_selection.currentText())
        self.changeChart(1, 2, chart12_selection.currentText())

        self.backgroundColor = self.app.settings.value("BackgroundColor", defaultValue=QtGui.QColor("white"),
                                                       type=QtGui.QColor)
        self.foregroundColor = self.app.settings.value("ForegroundColor", defaultValue=QtGui.QColor("lightgray"),
                                                       type=QtGui.QColor)
        self.textColor = self.app.settings.value("TextColor", defaultValue=QtGui.QColor("black"),
                                                 type=QtGui.QColor)
        self.bandsColor = self.app.settings.value("BandsColor", defaultValue=QtGui.QColor(128, 128, 128, 48),
                                                  type=QtGui.QColor)
        self.app.bands.color = self.bandsColor
        self.vswrColor = self.app.settings.value("VSWRColor", defaultValue=QtGui.QColor(192, 0, 0, 128),
                                                 type=QtGui.QColor)

        self.dark_mode_option.setChecked(self.app.settings.value("DarkMode", False, bool))
        self.show_lines_option.setChecked(self.app.settings.value("ShowLines", False, bool))
        self.show_marker_number_option.setChecked(self.app.settings.value("ShowMarkerNumbers", False, bool))
        self.filled_marker_option.setChecked(self.app.settings.value("FilledMarkers", False, bool))

        if self.app.settings.value("UseCustomColors", defaultValue=False, type=bool):
            self.dark_mode_option.setDisabled(True)
            self.dark_mode_option.setChecked(False)
            self.use_custom_colors.setChecked(True)
        else:
            self.btn_background_picker.setDisabled(True)
            self.btn_foreground_picker.setDisabled(True)
            self.btn_text_picker.setDisabled(True)

        self.changeCustomColors()  # Update all the colours of all the charts

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

        p = self.btn_vswr_picker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.vswrColor)
        self.btn_vswr_picker.setPalette(p)

        left_layout.addWidget(display_options_box)
        left_layout.addWidget(charts_box)
        left_layout.addWidget(markers_box)
        left_layout.addStretch(1)

        right_layout.addWidget(color_options_box)
        right_layout.addWidget(font_options_box)
        right_layout.addWidget(bands_box)
        right_layout.addWidget(vswr_marker_box)
        right_layout.addStretch(1)

    def changeChart(self, x, y, chart):
        found = None
        for c in self.app.selectable_charts:
            if c.name == chart:
                found = c

        self.app.settings.setValue("Chart" + str(x) + str(y), chart)

        old_widget = self.app.charts_layout.itemAtPosition(x, y)
        if old_widget is not None:
            w = old_widget.widget()
            self.app.charts_layout.removeWidget(w)
            w.hide()
        if found is not None:
            if self.app.charts_layout.indexOf(found) > -1:
                logger.debug("%s is already shown, duplicating.", found.name)
                found = self.app.copyChart(found)

            self.app.charts_layout.addWidget(found, x, y)
            if found.isHidden():
                found.show()

    def changeReturnLoss(self):
        state = self.returnloss_is_positive.isChecked()
        self.app.settings.setValue("ReturnLossPositive", state)

        for m in self.app.markers:
            m.returnloss_is_positive = state
            m.updateLabels(self.app.data, self.app.data21)
        self.marker_window.exampleMarker.returnloss_is_positive = state
        self.marker_window.updateMarker()
        self.app.s11LogMag.isInverted = state
        self.app.s11LogMag.update()

    def changeShowLines(self):
        state = self.show_lines_option.isChecked()
        self.app.settings.setValue("ShowLines", state)
        for c in self.app.subscribing_charts:
            c.setDrawLines(state)

    def changeShowMarkerNumber(self):
        state = self.show_marker_number_option.isChecked()
        self.app.settings.setValue("ShowMarkerNumbers", state)
        for c in self.app.subscribing_charts:
            c.setDrawMarkerNumbers(state)

    def changeFilledMarkers(self):
        state = self.filled_marker_option.isChecked()
        self.app.settings.setValue("FilledMarkers", state)
        for c in self.app.subscribing_charts:
            c.setFilledMarkers(state)

    def changeMarkerAtTip(self):
        state = self.marker_at_tip.isChecked()
        self.app.settings.setValue("MarkerAtTip", state)
        for c in self.app.subscribing_charts:
            c.setMarkerAtTip(state)

    def changePointSize(self, size: int):
        self.app.settings.setValue("PointSize", size)
        for c in self.app.subscribing_charts:
            c.setPointSize(size)

    def changeLineThickness(self, size: int):
        self.app.settings.setValue("LineThickness", size)
        for c in self.app.subscribing_charts:
            c.setLineThickness(size)

    def changeMarkerSize(self, size: int):
        if size % 2 == 0:
            self.app.settings.setValue("MarkerSize", size)
            for c in self.app.subscribing_charts:
                c.setMarkerSize(int(size / 2))

    def validateMarkerSize(self):
        size = self.markerSizeInput.value()
        if size % 2 != 0:
            self.markerSizeInput.setValue(size + 1)

    def changeDarkMode(self):
        state = self.dark_mode_option.isChecked()
        self.app.settings.setValue("DarkMode", state)
        if state:
            for c in self.app.subscribing_charts:
                c.setBackgroundColor(QtGui.QColor(QtCore.Qt.black))
                c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
                c.setTextColor(QtGui.QColor(QtCore.Qt.white))
                c.setSWRColor(self.vswrColor)
        else:
            for c in self.app.subscribing_charts:
                c.setBackgroundColor(QtGui.QColor(QtCore.Qt.white))
                c.setForegroundColor(QtGui.QColor(QtCore.Qt.lightGray))
                c.setTextColor(QtGui.QColor(QtCore.Qt.black))
                c.setSWRColor(self.vswrColor)

    def changeCustomColors(self):
        self.app.settings.setValue("UseCustomColors", self.use_custom_colors.isChecked())
        if self.use_custom_colors.isChecked():
            self.dark_mode_option.setDisabled(True)
            self.dark_mode_option.setChecked(False)
            self.btn_background_picker.setDisabled(False)
            self.btn_foreground_picker.setDisabled(False)
            self.btn_text_picker.setDisabled(False)
            for c in self.app.subscribing_charts:
                c.setBackgroundColor(self.backgroundColor)
                c.setForegroundColor(self.foregroundColor)
                c.setTextColor(self.textColor)
                c.setSWRColor(self.vswrColor)
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
        elif name == "vswr":
            p = self.btn_vswr_picker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btn_vswr_picker.setPalette(p)
            self.vswrColor = color
            self.app.settings.setValue("VSWRColor", color)
        self.changeCustomColors()

    def setSweepColor(self, color: QtGui.QColor):
        if color.isValid():
            self.sweepColor = color
            p = self.btnColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnColorPicker.setPalette(p)
            self.app.settings.setValue("SweepColor", color)
            self.app.settings.sync()
            for c in self.app.subscribing_charts:
                c.setSweepColor(color)

    def setSecondarySweepColor(self, color: QtGui.QColor):
        if color.isValid():
            self.secondarySweepColor = color
            p = self.btnSecondaryColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnSecondaryColorPicker.setPalette(p)
            self.app.settings.setValue("SecondarySweepColor", color)
            self.app.settings.sync()
            for c in self.app.subscribing_charts:
                c.setSecondarySweepColor(color)

    def setReferenceColor(self, color):
        if color.isValid():
            self.referenceColor = color
            p = self.btnReferenceColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnReferenceColorPicker.setPalette(p)
            self.app.settings.setValue("ReferenceColor", color)
            self.app.settings.sync()

            for c in self.app.subscribing_charts:
                c.setReferenceColor(color)

    def setSecondaryReferenceColor(self, color):
        if color.isValid():
            self.secondaryReferenceColor = color
            p = self.btnSecondaryReferenceColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, color)
            self.btnSecondaryReferenceColorPicker.setPalette(p)
            self.app.settings.setValue("SecondaryReferenceColor", color)
            self.app.settings.sync()

            for c in self.app.subscribing_charts:
                c.setSecondaryReferenceColor(color)

    def setShowBands(self, show_bands):
        self.app.bands.enabled = show_bands
        self.app.bands.settings.setValue("ShowBands", show_bands)
        self.app.bands.settings.sync()
        for c in self.app.subscribing_charts:
            c.update()

    def changeFont(self):
        font_size = self.font_dropdown.currentText()
        self.app.settings.setValue("FontSize", font_size)
        app: QtWidgets.QApplication = QtWidgets.QApplication.instance()
        font = app.font()
        font.setPointSize(int(font_size))
        app.setFont(font)
        self.app.changeFont(font)

    def displayBandsWindow(self):
        self.bandsWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.bandsWindow)

    def displayMarkerWindow(self):
        self.marker_window.show()
        QtWidgets.QApplication.setActiveWindow(self.marker_window)

    def addMarker(self):
        marker_count = len(self.app.markers)
        if marker_count < 6:
            color = NanoVNASaver.default_marker_colors[marker_count]
        else:
            color = QtGui.QColor(QtCore.Qt.darkGray)
        new_marker = Marker("Marker " + str(marker_count+1), color)
        new_marker.setColoredText(self.app.settings.value("ColoredMarkerNames", True, bool))
        new_marker.setFieldSelection(self.app.settings.value("MarkerFields",
                                                             defaultValue=self.marker_window.defaultValue))
        new_marker.setScale(self.app.scaleFactor)
        self.app.markers.append(new_marker)
        self.app.marker_data_layout.addWidget(new_marker.getGroupBox())

        new_marker.updated.connect(self.app.markerUpdated)
        label, layout = new_marker.getRow()
        self.app.marker_control_layout.insertRow(marker_count, label, layout)
        if marker_count == 0:
            new_marker.isMouseControlledRadioButton.setChecked(True)

        self.btn_remove_marker.setDisabled(False)

    def removeMarker(self):
        # keep at least one marker
        if len(self.app.markers) <= 1:
            return
        if len(self.app.markers) == 2:
            self.btn_remove_marker.setDisabled(True)
        last_marker = self.app.markers.pop()

        last_marker.updated.disconnect(self.app.markerUpdated)
        self.app.marker_data_layout.removeWidget(last_marker.getGroupBox())
        self.app.marker_control_layout.removeRow(len(self.app.markers))
        last_marker.getGroupBox().hide()
        last_marker.getGroupBox().destroy()
        label, layout = last_marker.getRow()
        label.hide()

    def addVSWRMarker(self):
        value, selected = QtWidgets.QInputDialog.getDouble(self, "Add VSWR Marker",
                                                           "VSWR value to show:", min=1.001, decimals=3)
        if selected:
            self.vswrMarkers.append(value)
            if self.vswr_marker_dropdown.itemText(0) == "None":
                self.vswr_marker_dropdown.removeItem(0)
            self.vswr_marker_dropdown.addItem(str(value))
            self.vswr_marker_dropdown.setCurrentText(str(value))
            for c in self.app.s11charts:
                c.addSWRMarker(value)
            self.app.settings.setValue("VSWRMarkers", self.vswrMarkers)

    def removeVSWRMarker(self):
        value_str = self.vswr_marker_dropdown.currentText()
        if value_str != "None":
            value = float(value_str)
            self.vswrMarkers.remove(value)
            self.vswr_marker_dropdown.removeItem(self.vswr_marker_dropdown.currentIndex())
            if self.vswr_marker_dropdown.count() == 0:
                self.vswr_marker_dropdown.addItem("None")
                self.app.settings.remove("VSWRMarkers")
            else:
                self.app.settings.setValue("VSWRMarkers", self.vswrMarkers)
            for c in self.app.s11charts:
                c.removeSWRMarker(value)


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
            self.findUpdates(automatic=True)
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
            req = request.Request(update_url)
            req.add_header('User-Agent', "NanoVNA-Saver/" + self.app.version)
            updates = json.load(request.urlopen(req, timeout=3))
            latest_version = Version(updates['version'])
            latest_url = updates['url']
        except error.HTTPError as e:
            logger.exception("Checking for updates produced an HTTP exception: %s", e)
            self.updateLabel.setText("Connection error.")
            return
        except json.JSONDecodeError as e:
            logger.exception("Checking for updates provided an unparseable file: %s", e)
            self.updateLabel.setText("Data error reading versions.")
            return
        except error.URLError as e:
            logger.exception("Checking for updates produced a URL exception: %s", e)
            self.updateLabel.setText("Connection error.")
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
    updated = QtCore.pyqtSignal()

    def __init__(self, app: NanoVNASaver):
        super().__init__()
        self.app = app

        self.td = []
        self.distance_axis = []
        self.step_response = []
        self.step_response_Z = []

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
        # TODO: Let the user select whether to use high or low resolution TDR?
        FFT_POINTS = 2**14

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
        self.td = np.abs(np.fft.ifft(windowed_s11, FFT_POINTS))
        step = np.ones(FFT_POINTS)
        self.step_response = signal.convolve(self.td, step)

        self.step_response_Z = 50 * (1 + self.step_response) / (1 - self.step_response)

        time_axis = np.linspace(0, 1/step_size, FFT_POINTS)
        self.distance_axis = time_axis * v * c
        # peak = np.max(td)  # We should check that this is an actual *peak*, and not just a vague maximum
        index_peak = np.argmax(self.td)

        cable_len = round(self.distance_axis[index_peak]/2, 3)
        feet = math.floor(cable_len / 0.3048)
        inches = round(((cable_len / 0.3048) - feet)*12, 1)

        self.tdr_result_label.setText(str(cable_len) + " m (" + str(feet) + "ft " + str(inches) + "in)")
        self.app.tdr_result_label.setText(str(cable_len) + " m")
        self.updated.emit()


class SweepSettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()

        self.app = app
        self.setWindowTitle("Sweep settings")
        self.setWindowIcon(self.app.icon)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        title_box = QtWidgets.QGroupBox("Sweep name")
        title_layout = QtWidgets.QFormLayout(title_box)
        self.sweep_title_input = QtWidgets.QLineEdit()
        title_layout.addRow("Sweep name", self.sweep_title_input)
        title_button_layout = QtWidgets.QHBoxLayout()
        btn_set_sweep_title = QtWidgets.QPushButton("Set")
        btn_set_sweep_title.clicked.connect(lambda: self.app.setSweepTitle(self.sweep_title_input.text()))
        btn_reset_sweep_title = QtWidgets.QPushButton("Reset")
        btn_reset_sweep_title.clicked.connect(lambda: self.app.setSweepTitle(""))
        title_button_layout.addWidget(btn_set_sweep_title)
        title_button_layout.addWidget(btn_reset_sweep_title)
        title_layout.addRow(title_button_layout)
        layout.addWidget(title_box)

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

        self.continuous_sweep_radiobutton.toggled.connect(
            lambda: self.app.worker.setContinuousSweep(self.continuous_sweep_radiobutton.isChecked()))
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

        self.band_pad_group = QtWidgets.QButtonGroup()
        self.band_pad_0 = QtWidgets.QRadioButton("None")
        self.band_pad_10 = QtWidgets.QRadioButton("10%")
        self.band_pad_25 = QtWidgets.QRadioButton("25%")
        self.band_pad_100 = QtWidgets.QRadioButton("100%")
        self.band_pad_0.setChecked(True)
        self.band_pad_group.addButton(self.band_pad_0)
        self.band_pad_group.addButton(self.band_pad_10)
        self.band_pad_group.addButton(self.band_pad_25)
        self.band_pad_group.addButton(self.band_pad_100)
        self.band_pad_group.buttonClicked.connect(self.updateCurrentBand)
        band_sweep_layout.addRow("Pad band limits", self.band_pad_0)
        band_sweep_layout.addRow("", self.band_pad_10)
        band_sweep_layout.addRow("", self.band_pad_25)
        band_sweep_layout.addRow("", self.band_pad_100)

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

        if self.band_pad_10.isChecked():
            padding = 10
        elif self.band_pad_25.isChecked():
            padding = 25
        elif self.band_pad_100.isChecked():
            padding = 100
        else:
            padding = 0

        if padding > 0:
            span = stop - start
            start -= round(span * padding / 100)
            start = max(1, start)
            stop += round(span * padding / 100)

        self.band_limit_label.setText("Sweep span: " + RFTools.formatShortFrequency(start) + " to " +
                                      RFTools.formatShortFrequency(stop))

    def setBandSweep(self):
        index_start = self.band_list.model().index(self.band_list.currentIndex(), 1)
        index_stop = self.band_list.model().index(self.band_list.currentIndex(), 2)
        start = int(self.band_list.model().data(index_start, QtCore.Qt.ItemDataRole).value())
        stop = int(self.band_list.model().data(index_stop, QtCore.Qt.ItemDataRole).value())

        if self.band_pad_10.isChecked():
            padding = 10
        elif self.band_pad_25.isChecked():
            padding = 25
        elif self.band_pad_100.isChecked():
            padding = 100
        else:
            padding = 0

        if padding > 0:
            span = stop - start
            start -= round(span * padding / 100)
            start = max(1, start)
            stop += round(span * padding / 100)

        self.app.sweepStartInput.setText(RFTools.formatSweepFrequency(start))
        self.app.sweepEndInput.setText(RFTools.formatSweepFrequency(stop))
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
                     "30 m;29000000;29050000",
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
        # self.analysis_list.addItem("Peak search", PeakSearchAnalysis(self.app))
        self.analysis_list.addItem("Peak search", SimplePeakSearchAnalysis(self.app))
        self.analysis_list.addItem("VSWR analysis", VSWRAnalysis(self.app))
        select_analysis_layout.addRow("Analysis type", self.analysis_list)
        self.analysis_list.currentIndexChanged.connect(self.updateSelection)

        btn_run_analysis = QtWidgets.QPushButton("Run analysis")
        btn_run_analysis.clicked.connect(self.runAnalysis)
        select_analysis_layout.addRow(btn_run_analysis)

        self.checkbox_run_automatically = QtWidgets.QCheckBox("Run automatically")
        self.checkbox_run_automatically.stateChanged.connect(self.toggleAutomaticRun)
        select_analysis_layout.addRow(self.checkbox_run_automatically)

        analysis_box = QtWidgets.QGroupBox("Analysis")
        analysis_box.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        self.analysis_layout = QtWidgets.QVBoxLayout(analysis_box)
        self.analysis_layout.setContentsMargins(0, 0, 0, 0)

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

    def toggleAutomaticRun(self, state: QtCore.Qt.CheckState):
        if state == QtCore.Qt.Checked:
            self.analysis_list.setDisabled(True)
            self.app.dataAvailable.connect(self.runAnalysis)
        else:
            self.analysis_list.setDisabled(False)
            self.app.dataAvailable.disconnect(self.runAnalysis)


class MarkerSettingsWindow(QtWidgets.QWidget):
    exampleData11 = [Datapoint(123000000, 0.89, -0.11),
                     Datapoint(123500000, 0.9, -0.1),
                     Datapoint(124000000, 0.91, -0.95)]
    exampleData21 = [Datapoint(123000000, -0.25, 0.49),
                     Datapoint(123456000, -0.3, 0.5),
                     Datapoint(124000000, -0.2, 0.5)]

    fieldList = {"actualfreq": "Actual frequency",
                 "impedance": "Impedance",
                 "admittance": "Admittance",
                 "s11polar": "S11 Polar Form",
                 "s21polar": "S21 Polar Form",
                 "serr": "Series R",
                 "serlc": "Series equivalent L/C",
                 "serl": "Series equivalent L",
                 "serc": "Series equivalent C",
                 "parr": "Parallel R",
                 "parlc": "Parallel equivalent L/C",
                 "parl": "Parallel equivalent L",
                 "parc": "Parallel equivalent C",
                 "vswr": "VSWR",
                 "returnloss": "Return loss",
                 "s11q": "S11 Quality factor",
                 "s11phase": "S11 Phase",
                 "s11groupdelay": "S11 Group Delay",
                 "s21gain": "S21 Gain",
                 "s21phase": "S21 Phase",
                 "s21groupdelay": "S21 Group Delay",
                }

    defaultValue = ["actualfreq",
                    "impedance",
                    "serl",
                    "serc",
                    "parr",
                    "parlc",
                    "vswr",
                    "returnloss",
                    "s11q",
                    "s11phase",
                    "s21gain",
                    "s21phase"
                    ]

    def __init__(self, app: NanoVNASaver):
        super().__init__()
        self.app = app

        self.setWindowTitle("Marker settings")
        self.setWindowIcon(self.app.icon)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.cancelButtonClick)

        if len(self.app.markers) > 0:
            color = self.app.markers[0].color
        else:
            color = self.app.default_marker_colors[0]

        self.exampleMarker = Marker("Example marker", initialColor=color, frequency="123456000")

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        settings_group_box = QtWidgets.QGroupBox("Settings")
        settings_group_box_layout = QtWidgets.QFormLayout(settings_group_box)
        self.checkboxColouredMarker = QtWidgets.QCheckBox("Colored marker name")
        self.checkboxColouredMarker.setChecked(self.app.settings.value("ColoredMarkerNames", True, bool))
        self.checkboxColouredMarker.stateChanged.connect(self.updateMarker)
        settings_group_box_layout.addRow(self.checkboxColouredMarker)

        fields_group_box = QtWidgets.QGroupBox("Displayed data")
        fields_group_box_layout = QtWidgets.QFormLayout(fields_group_box)

        self.savedFieldSelection = self.app.settings.value("MarkerFields", defaultValue=self.defaultValue)

        if self.savedFieldSelection == "":
            self.savedFieldSelection = []

        self.currentFieldSelection = self.savedFieldSelection.copy()

        self.fieldSelectionView = QtWidgets.QListView()
        self.model = QtGui.QStandardItemModel()
        for field in self.fieldList:
            item = QtGui.QStandardItem(self.fieldList[field])
            item.setData(field)
            item.setCheckable(True)
            item.setEditable(False)
            if field in self.currentFieldSelection:
                item.setCheckState(QtCore.Qt.Checked)
            self.model.appendRow(item)
        self.fieldSelectionView.setModel(self.model)

        self.model.itemChanged.connect(self.updateField)

        fields_group_box_layout.addRow(self.fieldSelectionView)

        layout.addWidget(settings_group_box)
        layout.addWidget(fields_group_box)
        layout.addWidget(self.exampleMarker.getGroupBox())

        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_ok = QtWidgets.QPushButton("OK")
        btn_apply = QtWidgets.QPushButton("Apply")
        btn_default = QtWidgets.QPushButton("Defaults")
        btn_cancel = QtWidgets.QPushButton("Cancel")

        btn_ok.clicked.connect(self.okButtonClick)
        btn_apply.clicked.connect(self.applyButtonClick)
        btn_default.clicked.connect(self.defaultButtonClick)
        btn_cancel.clicked.connect(self.cancelButtonClick)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_default)
        btn_layout.addWidget(btn_cancel)

        self.updateMarker()
        for m in self.app.markers:
            m.setFieldSelection(self.currentFieldSelection)
            m.setColoredText(self.checkboxColouredMarker.isChecked())

    def updateMarker(self):
        self.exampleMarker.setColoredText(self.checkboxColouredMarker.isChecked())
        self.exampleMarker.setFieldSelection(self.currentFieldSelection)
        self.exampleMarker.findLocation(self.exampleData11)
        self.exampleMarker.resetLabels()
        self.exampleMarker.updateLabels(self.exampleData11, self.exampleData21)

    def updateField(self, field: QtGui.QStandardItem):
        if field.checkState() == QtCore.Qt.Checked:
            if not field.data() in self.currentFieldSelection:
                self.currentFieldSelection = []
                for i in range(self.model.rowCount()):
                    field = self.model.item(i, 0)
                    if field.checkState() == QtCore.Qt.Checked:
                        self.currentFieldSelection.append(field.data())
        else:
            if field.data() in self.currentFieldSelection:
                self.currentFieldSelection.remove(field.data())
        self.updateMarker()

    def applyButtonClick(self):
        self.savedFieldSelection = self.currentFieldSelection.copy()
        self.app.settings.setValue("MarkerFields", self.savedFieldSelection)
        self.app.settings.setValue("ColoredMarkerNames", self.checkboxColouredMarker.isChecked())
        for m in self.app.markers:
            m.setFieldSelection(self.savedFieldSelection)
            m.setColoredText(self.checkboxColouredMarker.isChecked())

    def okButtonClick(self):
        self.applyButtonClick()
        self.close()

    def cancelButtonClick(self):
        self.currentFieldSelection = self.savedFieldSelection.copy()
        self.resetModel()
        self.updateMarker()
        self.close()

    def defaultButtonClick(self):
        self.currentFieldSelection = self.defaultValue.copy()
        self.resetModel()
        self.updateMarker()

    def resetModel(self):
        self.model = QtGui.QStandardItemModel()
        for field in self.fieldList:
            item = QtGui.QStandardItem(self.fieldList[field])
            item.setData(field)
            item.setCheckable(True)
            item.setEditable(False)
            if field in self.currentFieldSelection:
                item.setCheckState(QtCore.Qt.Checked)
            self.model.appendRow(item)
        self.fieldSelectionView.setModel(self.model)
        self.model.itemChanged.connect(self.updateField)


class DeviceSettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: NanoVNASaver):
        super().__init__()

        self.app = app
        self.setWindowTitle("Device settings")
        self.setWindowIcon(self.app.icon)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

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

        layout.addWidget(status_box)
        layout.addWidget(settings_box)
        layout.addLayout(control_layout)

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

            if "Screenshots" in features:
                self.btnCaptureScreenshot.setDisabled(False)
            else:
                self.btnCaptureScreenshot.setDisabled(True)
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
        else:
            # TODO: Tell the user no screenshots while sweep is running?
            # TODO: Consider having a list of widgets that want to be disabled when a sweep is running?
            pass


class ScreenshotWindow(QtWidgets.QLabel):
    pix = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screenshot")
        # TODO : self.setWindowIcon(self.app.icon)

        shortcut = QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.action_original_size = QtWidgets.QAction("Original size")
        self.action_original_size.triggered.connect(lambda: self.setScale(1))
        self.action_2x_size = QtWidgets.QAction("2x size")
        self.action_2x_size.triggered.connect(lambda: self.setScale(2))
        self.action_3x_size = QtWidgets.QAction("3x size")
        self.action_3x_size.triggered.connect(lambda: self.setScale(3))
        self.action_4x_size = QtWidgets.QAction("4x size")
        self.action_4x_size.triggered.connect(lambda: self.setScale(4))
        self.action_5x_size = QtWidgets.QAction("5x size")
        self.action_5x_size.triggered.connect(lambda: self.setScale(5))

        self.addAction(self.action_original_size)
        self.addAction(self.action_2x_size)
        self.addAction(self.action_3x_size)
        self.addAction(self.action_4x_size)
        self.addAction(self.action_5x_size)
        self.action_save_screenshot = QtWidgets.QAction("Save image")
        self.action_save_screenshot.triggered.connect(self.saveScreenshot)
        self.addAction(self.action_save_screenshot)

    def setScreenshot(self, pixmap: QtGui.QPixmap):
        if self.pix is None:
            self.resize(pixmap.size())
        self.pix = pixmap
        self.setPixmap(self.pix.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation))
        w, h = pixmap.width(), pixmap.height()
        self.action_original_size.setText("Original size (" + str(w) + "x" + str(h) + ")")
        self.action_2x_size.setText("2x size (" + str(w * 2) + "x" + str(h * 2) + ")")
        self.action_3x_size.setText("3x size (" + str(w * 3) + "x" + str(h * 3) + ")")
        self.action_4x_size.setText("4x size (" + str(w * 4) + "x" + str(h * 4) + ")")
        self.action_5x_size.setText("5x size (" + str(w * 5) + "x" + str(h * 5) + ")")

    def saveScreenshot(self):
        if self.pix is not None:
            logger.info("Saving screenshot to file...")
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(parent=self, caption="Save image",
                                                                filter="PNG (*.png);;All files (*.*)")

            logger.debug("Filename: %s", filename)
            if filename != "":
                self.pixmap().save(filename)
        else:
            logger.warning("The user got shown an empty screenshot window?")

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        if self.pixmap() is not None:
            self.setPixmap(self.pix.scaled(self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation))

    def setScale(self, scale):
        width, height = self.pix.size().width() * scale, self.pix.size().height() * scale
        self.resize(width, height)
