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
from PyQt6.QtCore import Qt

from NanoVNASaver.Analysis.AntennaAnalysis import MagLoopAnalysis
from NanoVNASaver.Analysis.BandPassAnalysis import BandPassAnalysis
from NanoVNASaver.Analysis.BandStopAnalysis import BandStopAnalysis
from NanoVNASaver.Analysis.Base import Analysis
from NanoVNASaver.Analysis.EFHWAnalysis import EFHWAnalysis
from NanoVNASaver.Analysis.HighPassAnalysis import HighPassAnalysis
from NanoVNASaver.Analysis.LowPassAnalysis import LowPassAnalysis
from NanoVNASaver.Analysis.PeakSearchAnalysis import PeakSearchAnalysis
from NanoVNASaver.Analysis.ResonanceAnalysis import ResonanceAnalysis
from NanoVNASaver.Analysis.SimplePeakSearchAnalysis import (
    SimplePeakSearchAnalysis,
)
from NanoVNASaver.Analysis.VSWRAnalysis import VSWRAnalysis
from NanoVNASaver.Windows.Defaults import make_scrollable

logger = logging.getLogger(__name__)


class AnalysisWindow(QtWidgets.QWidget):
    analyses = []
    analysis: Analysis = None

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()

        self.app = app
        self.setWindowTitle("Sweep analysis")
        self.setWindowIcon(self.app.icon)

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, layout)

        select_analysis_box = QtWidgets.QGroupBox("Select analysis")
        select_analysis_layout = QtWidgets.QFormLayout(select_analysis_box)
        self.analysis_list = QtWidgets.QComboBox()
        self.analysis_list.addItem("Low-pass filter", LowPassAnalysis(self.app))
        self.analysis_list.addItem(
            "Band-pass filter", BandPassAnalysis(self.app)
        )
        self.analysis_list.addItem(
            "High-pass filter", HighPassAnalysis(self.app)
        )
        self.analysis_list.addItem(
            "Band-stop filter", BandStopAnalysis(self.app)
        )
        self.analysis_list.addItem(
            "Simple Peak search", SimplePeakSearchAnalysis(self.app)
        )
        self.analysis_list.addItem("Peak search", PeakSearchAnalysis(self.app))
        self.analysis_list.addItem("VSWR analysis", VSWRAnalysis(self.app))
        self.analysis_list.addItem(
            "Resonance analysis", ResonanceAnalysis(self.app)
        )
        self.analysis_list.addItem("HWEF analysis", EFHWAnalysis(self.app))
        self.analysis_list.addItem(
            "MagLoop analysis", MagLoopAnalysis(self.app)
        )
        select_analysis_layout.addRow("Analysis type", self.analysis_list)
        self.analysis_list.currentIndexChanged.connect(self.updateSelection)

        btn_run_analysis = QtWidgets.QPushButton("Run analysis")
        btn_run_analysis.clicked.connect(self.runAnalysis)
        select_analysis_layout.addRow(btn_run_analysis)

        self.checkbox_run_automatically = QtWidgets.QCheckBox(
            "Run automatically"
        )
        self.checkbox_run_automatically.stateChanged.connect(
            self.toggleAutomaticRun
        )
        select_analysis_layout.addRow(self.checkbox_run_automatically)

        analysis_box = QtWidgets.QGroupBox("Analysis")
        analysis_box.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

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
            self.analysis_layout.replaceWidget(
                old_widget, self.analysis.widget()
            )
            old_widget.hide()
        else:
            self.analysis_layout.addWidget(self.analysis.widget())
        self.analysis.widget().show()
        self.update()

    def toggleAutomaticRun(self, state: Qt.CheckState):
        if state == Qt.CheckState.Checked.value:
            self.analysis_list.setDisabled(True)
            self.app.communicate.data_available.connect(self.runAnalysis)
        else:
            self.analysis_list.setDisabled(False)
            self.app.communicate.data_available.disconnect(self.runAnalysis)
