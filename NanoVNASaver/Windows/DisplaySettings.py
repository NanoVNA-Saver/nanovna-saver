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
from typing import List

from PyQt5 import QtWidgets, QtCore, QtGui

from NanoVNASaver.Windows.Bands import BandsWindow
from NanoVNASaver.Windows.MarkerSettings import MarkerSettingsWindow
from NanoVNASaver.Marker import Marker
logger = logging.getLogger(__name__)


class DisplaySettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()

        self.app = app
        self.setWindowTitle("Display settings")
        self.setWindowIcon(self.app.icon)

        self.marker_window = MarkerSettingsWindow(self.app)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

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
        self.sweepColor = self.app.settings.value(
            "SweepColor", defaultValue=QtGui.QColor(160, 140, 20, 128),
            type=QtGui.QColor)
        self.setSweepColor(self.sweepColor)
        self.btnColorPicker.clicked.connect(lambda: self.setSweepColor(
            QtWidgets.QColorDialog.getColor(
                self.sweepColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Sweep color", self.btnColorPicker)

        self.btnSecondaryColorPicker = QtWidgets.QPushButton("█")
        self.btnSecondaryColorPicker.setFixedWidth(20)
        self.secondarySweepColor = self.app.settings.value("SecondarySweepColor",
                                                           defaultValue=QtGui.QColor(
                                                               20, 160, 140, 128),
                                                           type=QtGui.QColor)
        self.setSecondarySweepColor(self.secondarySweepColor)
        self.btnSecondaryColorPicker.clicked.connect(lambda: self.setSecondarySweepColor(
            QtWidgets.QColorDialog.getColor(self.secondarySweepColor,
                                            options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Second sweep color", self.btnSecondaryColorPicker)

        self.btnReferenceColorPicker = QtWidgets.QPushButton("█")
        self.btnReferenceColorPicker.setFixedWidth(20)
        self.referenceColor = self.app.settings.value(
            "ReferenceColor", defaultValue=QtGui.QColor(0, 0, 255, 48),
            type=QtGui.QColor)
        self.setReferenceColor(self.referenceColor)
        self.btnReferenceColorPicker.clicked.connect(lambda: self.setReferenceColor(
            QtWidgets.QColorDialog.getColor(
                self.referenceColor, options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow("Reference color", self.btnReferenceColorPicker)

        self.btnSecondaryReferenceColorPicker = QtWidgets.QPushButton("█")
        self.btnSecondaryReferenceColorPicker.setFixedWidth(20)
        self.secondaryReferenceColor = self.app.settings.value(
            "SecondaryReferenceColor",
            defaultValue=QtGui.QColor(0, 0, 255, 48),
            type=QtGui.QColor)
        self.setSecondaryReferenceColor(self.secondaryReferenceColor)
        self.btnSecondaryReferenceColorPicker.clicked.connect(
            lambda: self.setSecondaryReferenceColor(
                QtWidgets.QColorDialog.getColor(
                    self.secondaryReferenceColor,
                    options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        display_options_layout.addRow(
            "Second reference color",
            self.btnSecondaryReferenceColorPicker)

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
        self.btn_background_picker.clicked.connect(
            lambda: self.setColor(
                "background",
                QtWidgets.QColorDialog.getColor(
                    self.backgroundColor,
                    options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow(
            "Chart background", self.btn_background_picker)

        self.btn_foreground_picker = QtWidgets.QPushButton("█")
        self.btn_foreground_picker.setFixedWidth(20)
        self.btn_foreground_picker.clicked.connect(
            lambda: self.setColor(
                "foreground",
                QtWidgets.QColorDialog.getColor(
                    self.foregroundColor,
                    options=QtWidgets.QColorDialog.ShowAlphaChannel)))

        color_options_layout.addRow("Chart foreground", self.btn_foreground_picker)

        self.btn_text_picker = QtWidgets.QPushButton("█")
        self.btn_text_picker.setFixedWidth(20)
        self.btn_text_picker.clicked.connect(
            lambda: self.setColor(
                "text",
                QtWidgets.QColorDialog.getColor(
                    self.textColor,
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
        self.btn_bands_picker.clicked.connect(
            lambda: self.setColor(
                "bands",
                QtWidgets.QColorDialog.getColor(
                    self.bandsColor,
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
        self.btn_vswr_picker.clicked.connect(
            lambda: self.setColor(
                "vswr",
                QtWidgets.QColorDialog.getColor(
                    self.vswrColor,
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
        chart00_selection.currentTextChanged.connect(
            lambda: self.changeChart(0, 0, chart00_selection.currentText()))
        charts_layout.addWidget(chart00_selection, 0, 0)

        chart01_selection = QtWidgets.QComboBox()
        chart01_selection.addItems(selections)
        chart01 = self.app.settings.value("Chart01", "S11 Return Loss")
        if chart01_selection.findText(chart01) > -1:
            chart01_selection.setCurrentText(chart01)
        else:
            chart01_selection.setCurrentText("S11 Return Loss")
        chart01_selection.currentTextChanged.connect(
            lambda: self.changeChart(0, 1, chart01_selection.currentText()))
        charts_layout.addWidget(chart01_selection, 0, 1)

        chart02_selection = QtWidgets.QComboBox()
        chart02_selection.addItems(selections)
        chart02 = self.app.settings.value("Chart02", "None")
        if chart02_selection.findText(chart02) > -1:
            chart02_selection.setCurrentText(chart02)
        else:
            chart02_selection.setCurrentText("None")
        chart02_selection.currentTextChanged.connect(
            lambda: self.changeChart(0, 2, chart02_selection.currentText()))
        charts_layout.addWidget(chart02_selection, 0, 2)

        chart10_selection = QtWidgets.QComboBox()
        chart10_selection.addItems(selections)
        chart10 = self.app.settings.value("Chart10", "S21 Polar Plot")
        if chart10_selection.findText(chart10) > -1:
            chart10_selection.setCurrentText(chart10)
        else:
            chart10_selection.setCurrentText("S21 Polar Plot")
        chart10_selection.currentTextChanged.connect(
            lambda: self.changeChart(1, 0, chart10_selection.currentText()))
        charts_layout.addWidget(chart10_selection, 1, 0)

        chart11_selection = QtWidgets.QComboBox()
        chart11_selection.addItems(selections)
        chart11 = self.app.settings.value("Chart11", "S21 Gain")
        if chart11_selection.findText(chart11) > -1:
            chart11_selection.setCurrentText(chart11)
        else:
            chart11_selection.setCurrentText("S21 Gain")
        chart11_selection.currentTextChanged.connect(
            lambda: self.changeChart(1, 1, chart11_selection.currentText()))
        charts_layout.addWidget(chart11_selection, 1, 1)

        chart12_selection = QtWidgets.QComboBox()
        chart12_selection.addItems(selections)
        chart12 = self.app.settings.value("Chart12", "None")
        if chart12_selection.findText(chart12) > -1:
            chart12_selection.setCurrentText(chart12)
        else:
            chart12_selection.setCurrentText("None")
        chart12_selection.currentTextChanged.connect(
            lambda: self.changeChart(1, 2, chart12_selection.currentText()))
        charts_layout.addWidget(chart12_selection, 1, 2)

        self.changeChart(0, 0, chart00_selection.currentText())
        self.changeChart(0, 1, chart01_selection.currentText())
        self.changeChart(0, 2, chart02_selection.currentText())
        self.changeChart(1, 0, chart10_selection.currentText())
        self.changeChart(1, 1, chart11_selection.currentText())
        self.changeChart(1, 2, chart12_selection.currentText())

        self.backgroundColor = self.app.settings.value(
            "BackgroundColor", defaultValue=QtGui.QColor("white"),
            type=QtGui.QColor)
        self.foregroundColor = self.app.settings.value(
            "ForegroundColor", defaultValue=QtGui.QColor("lightgray"),
            type=QtGui.QColor)
        self.textColor = self.app.settings.value(
            "TextColor", defaultValue=QtGui.QColor("black"),
            type=QtGui.QColor)
        self.bandsColor = self.app.settings.value(
            "BandsColor", defaultValue=QtGui.QColor(128, 128, 128, 48),
            type=QtGui.QColor)
        self.app.bands.color = self.bandsColor
        self.vswrColor = self.app.settings.value(
            "VSWRColor", defaultValue=QtGui.QColor(192, 0, 0, 128),
            type=QtGui.QColor)

        self.dark_mode_option.setChecked(
            self.app.settings.value("DarkMode", False, bool))
        self.show_lines_option.setChecked(
            self.app.settings.value("ShowLines", False, bool))
        self.show_marker_number_option.setChecked(
            self.app.settings.value("ShowMarkerNumbers", False, bool))
        self.filled_marker_option.setChecked(
            self.app.settings.value("FilledMarkers", False, bool))

        if self.app.settings.value("UseCustomColors",
                                   defaultValue=False, type=bool):
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
        self.app.charts["s11"]["log_mag"].isInverted = state
        self.app.charts["s11"]["log_mag"].update()

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
        new_marker = Marker("", self.app.settings)
        new_marker.setScale(self.app.scaleFactor)
        self.app.markers.append(new_marker)
        self.app.marker_data_layout.addWidget(new_marker.getGroupBox())

        new_marker.updated.connect(self.app.markerUpdated)
        label, layout = new_marker.getRow()
        self.app.marker_control_layout.insertRow(Marker.count() - 1, label, layout)
        self.btn_remove_marker.setDisabled(False)

    def removeMarker(self):
        # keep at least one marker
        if Marker.count() <= 1:
            return
        if Marker.count() == 2:
            self.btn_remove_marker.setDisabled(True)
        last_marker = self.app.markers.pop()

        last_marker.updated.disconnect(self.app.markerUpdated)
        self.app.marker_data_layout.removeWidget(last_marker.getGroupBox())
        self.app.marker_control_layout.removeRow(Marker.count()-1)
        last_marker.getGroupBox().hide()
        last_marker.getGroupBox().destroy()
        label, _ = last_marker.getRow()
        label.hide()

    def addVSWRMarker(self):
        value, selected = QtWidgets.QInputDialog.getDouble(
            self, "Add VSWR Marker", "VSWR value to show:", min=1.001, decimals=3)
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
