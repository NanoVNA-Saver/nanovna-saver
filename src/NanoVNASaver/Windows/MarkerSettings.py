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

from NanoVNASaver.Marker.Values import TYPES, default_label_ids
from NanoVNASaver.Marker.Widget import Marker
from NanoVNASaver.RFTools import Datapoint

logger = logging.getLogger(__name__)


class MarkerSettingsWindow(QtWidgets.QWidget):
    EXAMPLE_DATA11 = [
        Datapoint(123000000, 0.89, -0.11),
        Datapoint(123500000, 0.9, -0.1),
        Datapoint(124000000, 0.91, -0.95),
    ]
    EXAMPLE_DATA21 = [
        Datapoint(123000000, -0.25, 0.49),
        Datapoint(123456000, -0.3, 0.5),
        Datapoint(124000000, -0.2, 0.5),
    ]

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setWindowTitle("Marker settings")
        self.setWindowIcon(self.app.icon)

        QtGui.QShortcut(QtCore.Qt.Key.Key_Escape, self, self.cancelButtonClick)

        self.exampleMarker = Marker("Example marker")
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        settings_group_box = QtWidgets.QGroupBox("Settings")
        settings_group_box_layout = QtWidgets.QFormLayout(settings_group_box)
        self.checkboxColouredMarker = QtWidgets.QCheckBox("Colored marker name")
        self.checkboxColouredMarker.setChecked(
            self.app.settings.value("ColoredMarkerNames", True, bool)
        )
        self.checkboxColouredMarker.stateChanged.connect(self.updateMarker)
        settings_group_box_layout.addRow(self.checkboxColouredMarker)

        fields_group_box = QtWidgets.QGroupBox("Displayed data")
        fields_group_box_layout = QtWidgets.QFormLayout(fields_group_box)

        self.savedFieldSelection = self.app.settings.value(
            "MarkerFields", defaultValue=default_label_ids()
        )

        if self.savedFieldSelection == "":
            self.savedFieldSelection = []

        self.currentFieldSelection = self.savedFieldSelection[:]

        self.active_labels_view = QtWidgets.QListView()
        self.update_displayed_data_form()

        fields_group_box_layout.addRow(self.active_labels_view)

        layout.addWidget(settings_group_box)
        layout.addWidget(fields_group_box)
        layout.addWidget(self.exampleMarker.get_data_layout())

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
        self.exampleMarker.setFrequency(123456000)
        self.exampleMarker.setColoredText(
            self.checkboxColouredMarker.isChecked()
        )
        self.exampleMarker.setFieldSelection(self.currentFieldSelection)
        self.exampleMarker.findLocation(self.EXAMPLE_DATA11)
        self.exampleMarker.resetLabels()
        self.exampleMarker.updateLabels(
            self.EXAMPLE_DATA11, self.EXAMPLE_DATA21
        )

    def updateField(self, field: QtGui.QStandardItem):
        if field.checkState() == Qt.CheckState.Checked:
            if field.data() not in self.currentFieldSelection:
                self.currentFieldSelection = []
                for i in range(self.model.rowCount()):
                    field = self.model.item(i, 0)
                    if field.checkState() == Qt.CheckState.Checked:
                        self.currentFieldSelection.append(field.data())
        elif field.data() in self.currentFieldSelection:
            self.currentFieldSelection.remove(field.data())
        self.updateMarker()

    def applyButtonClick(self):
        self.savedFieldSelection = self.currentFieldSelection[:]
        self.app.settings.setValue("MarkerFields", self.savedFieldSelection)
        self.app.settings.setValue(
            "ColoredMarkerNames", self.checkboxColouredMarker.isChecked()
        )
        for m in self.app.markers + [
            self.app.delta_marker,
        ]:
            m.setFieldSelection(self.savedFieldSelection)
            m.setColoredText(self.checkboxColouredMarker.isChecked())

    def okButtonClick(self):
        self.applyButtonClick()
        self.close()

    def cancelButtonClick(self):
        self.currentFieldSelection = self.savedFieldSelection[:]
        self.update_displayed_data_form()
        self.updateMarker()
        self.close()

    def defaultButtonClick(self):
        self.currentFieldSelection = default_label_ids()
        self.update_displayed_data_form()
        self.updateMarker()

    def update_displayed_data_form(self):
        self.model = QtGui.QStandardItemModel()
        for label in TYPES:
            item = QtGui.QStandardItem(label.description)
            item.setData(label.label_id)
            item.setCheckable(True)
            item.setEditable(False)
            if label.label_id in self.currentFieldSelection:
                item.setCheckState(Qt.CheckState.Checked)
            self.model.appendRow(item)
        self.active_labels_view.setModel(self.model)
        self.model.itemChanged.connect(self.updateField)
