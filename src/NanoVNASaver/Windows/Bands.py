#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020 Rune B. Broberg
#  Copyright (C) 2020-2024 NanoVNA-Saver Authors
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

logger = logging.getLogger(__name__)


class BandsWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()

        self.app = app
        self.setWindowTitle("Manage bands")
        self.setWindowIcon(self.app.icon)

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setMinimumSize(500, 300)

        self.bands_table = QtWidgets.QTableView()
        self.bands_table.setModel(self.app.bands)
        self.bands_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.bands_table)

        btn_add_row = QtWidgets.QPushButton("Add row")
        btn_delete_row = QtWidgets.QPushButton("Delete row")
        btn_reset_bands = QtWidgets.QPushButton("Reset bands/Select region")
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
        confirmBox = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Warning,
            "Confirm reset",
            "Are you sure you want to reset the bands to default?",
            QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        region_1_defaults_button = QtWidgets.QPushButton(
            "Reset to Region 1 defaults", confirmBox
        )
        region_2_defaults_button = QtWidgets.QPushButton(
            "Reset to Region 2 defaults", confirmBox
        )
        region_3_defaults_button = QtWidgets.QPushButton(
            "Reset to Region 3 defaults", confirmBox
        )
        confirmBox.addButton(
            region_1_defaults_button,
            QtWidgets.QMessageBox.ButtonRole.AcceptRole,
        )
        confirmBox.addButton(
            region_2_defaults_button,
            QtWidgets.QMessageBox.ButtonRole.AcceptRole,
        )
        confirmBox.addButton(
            region_3_defaults_button,
            QtWidgets.QMessageBox.ButtonRole.AcceptRole,
        )
        confirmBox.exec()

        clicked_button = confirmBox.clickedButton()
        if clicked_button == region_1_defaults_button:
            self.app.bands.resetBands(1)
        elif clicked_button == region_2_defaults_button:
            self.app.bands.resetBands(2)
        elif clicked_button == region_3_defaults_button:
            self.app.bands.resetBands(3)
