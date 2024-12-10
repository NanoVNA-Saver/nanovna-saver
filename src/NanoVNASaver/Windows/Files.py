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

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Touchstone import Touchstone
from NanoVNASaver.Windows.Defaults import make_scrollable

logger = logging.getLogger(__name__)


class FilesWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setWindowTitle("Files")
        self.setWindowIcon(self.app.icon)
        self.setMinimumWidth(200)
        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        file_window_layout = QtWidgets.QVBoxLayout()
        make_scrollable(self, file_window_layout)

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

        btn_export_file = QtWidgets.QPushButton("Save 1-Port file (S1P)")
        btn_export_file.clicked.connect(lambda: self.exportFile(1))
        save_file_control_layout.addRow(btn_export_file)

        btn_export_file = QtWidgets.QPushButton("Save 2-Port file (S2P)")
        btn_export_file.clicked.connect(lambda: self.exportFile(4))
        save_file_control_layout.addRow(btn_export_file)

        file_window_layout.addWidget(save_file_control_box)

        btn_open_file_window = QtWidgets.QPushButton("Files ...")
        btn_open_file_window.clicked.connect(
            lambda: self.app.display_window("file")
        )

    def exportFile(self, nr_params: int = 1):
        if len(self.app.data.s11) == 0:
            QtWidgets.QMessageBox.warning(
                self, "No data to save", "There is no data to save."
            )
            return
        if nr_params > 2 and len(self.app.data.s21) == 0:  # noqa: PLR2004
            QtWidgets.QMessageBox.warning(
                self, "No S21 data to save", "There is no S21 data to save."
            )
            return

        filedialog = QtWidgets.QFileDialog(self)
        if nr_params == 1:
            filedialog.setDefaultSuffix("s1p")
            filedialog.setNameFilter(
                "Touchstone 1-Port Files (*.s1p);;All files (*.*)"
            )
        else:
            filedialog.setDefaultSuffix("s2p")
            filedialog.setNameFilter(
                "Touchstone 2-Port Files (*.s2p);;All files (*.*)"
            )
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        selected = filedialog.exec()
        if not selected:
            return
        filename = filedialog.selectedFiles()[0]
        if filename == "":
            logger.debug("No file name selected.")
            return

        ts = Touchstone(filename)
        ts.sdata[0] = self.app.data.s11
        if nr_params > 1:
            ts.sdata[1] = self.app.data.s21
            for dp in self.app.data.s11:
                ts.sdata[2].append(Datapoint(dp.freq, 0, 0))
                ts.sdata[3].append(Datapoint(dp.freq, 0, 0))
        try:
            ts.save(nr_params)
        except IOError as e:
            logger.exception("Error during file export: %s", e)
            return

    def loadReferenceFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Touchstone Files (*.s1p *.s2p);;All files (*.*)"
        )
        if filename != "":
            self.app.resetReference()
            t = Touchstone(filename)
            t.load()
            self.app.setReference(t.s11, t.s21, filename)

    def loadSweepFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Touchstone Files (*.s1p *.s2p);;All files (*.*)"
        )
        if filename != "":
            self.app.data.s11 = []
            self.app.data.s21 = []
            t = Touchstone(filename)
            t.load()
            self.app.saveData(t.s11, t.s21, filename)
            self.app.dataUpdated()
