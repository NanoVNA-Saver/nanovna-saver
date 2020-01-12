#  NanoVNASaver
#  A python program to view and export Touchstone data from a NanoVNA
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

from PyQt5 import QtWidgets, QtCore, QtGui

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Marker import Marker

VID = 1155
PID = 22336

logger = logging.getLogger(__name__)


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

    def __init__(self, app: QtWidgets.QWidget):
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
