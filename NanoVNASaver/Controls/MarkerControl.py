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
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QCheckBox

from NanoVNASaver.Marker import Marker

logger = logging.getLogger(__name__)

class MarkerControl(QtWidgets.QGroupBox):
    updated = pyqtSignal(object)

    def __init__(self, app: QtWidgets.QWidget, title: str = "Markers"):
        super().__init__()
        self.app = app
        self.setMaximumWidth(250)
        self.setTitle(title)
        self.layout = QtWidgets.QFormLayout(self)

        marker_count = max(self.app.settings.value("MarkerCount", 3, int), 1)
        for i in range(marker_count):
            marker = Marker("", self.app.settings)
            marker.updated.connect(self.app.markerUpdated)
            label, layout = marker.getRow()
            self.layout.addRow(label, layout)
            self.app.markers.append(marker)
            if i == 0:
                marker.isMouseControlledRadioButton.setChecked(True)

        self.check_delta = QCheckBox("Enable Delta Marker")
        self.check_delta.toggled.connect(self.toggle_delta)
        self.layout.addRow(self.check_delta)

        self.showMarkerButton = QtWidgets.QPushButton()
        if self.app.marker_frame.isHidden():
            self.showMarkerButton.setText("Show data")
        else:
            self.showMarkerButton.setText("Hide data")
        self.showMarkerButton.clicked.connect(self.toggle_frame)

        lock_radiobutton = QtWidgets.QRadioButton("Locked")
        lock_radiobutton.setLayoutDirection(QtCore.Qt.RightToLeft)
        lock_radiobutton.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.showMarkerButton)
        hbox.addWidget(lock_radiobutton)
        self.layout.addRow(hbox)

    def toggle_frame(self):
        if self.app.marker_frame.isHidden():
            self.app.marker_frame.setHidden(False)
            self.app.settings.setValue("MarkersVisible", True)
            self.showMarkerButton.setText("Hide data")
            self.showMarkerButton.repaint()
        else:
            self.app.marker_frame.setHidden(True)
            self.app.settings.setValue("MarkersVisible", False)
            self.showMarkerButton.setText("Show data")
            self.showMarkerButton.repaint()

    def toggle_delta(self):
        self.app.delta_marker_layout.setVisible(self.check_delta.isChecked())
