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
from typing import List

from PyQt5 import QtWidgets, QtCore, QtGui

from NanoVNASaver.Charts.Chart import (
    Chart, ChartColors, ChartMarker, ChartMarkerConfig)
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
        self.marker_cfg = ChartMarkerConfig()
        self.marker_window = MarkerSettingsWindow(self.app)
        self.callback_params = {}

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

        self.trace_colors(display_options_layout)

        self.pointSizeInput = QtWidgets.QSpinBox()
        self.pointSizeInput.setMinimumHeight(20)
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
        self.lineThicknessInput.setMinimumHeight(20)
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
        self.markerSizeInput.setMinimumHeight(20)
        markersize = self.app.settings.value("MarkerSize", 6, int)
        self.markerSizeInput.setValue(markersize)
        self.markerSizeInput.setMinimum(4)
        self.markerSizeInput.setMinimum(4)
        self.markerSizeInput.setMaximum(20)
        self.markerSizeInput.setSingleStep(2)
        self.markerSizeInput.setSuffix(" px")
        self.markerSizeInput.setAlignment(QtCore.Qt.AlignRight)
        self.markerSizeInput.valueChanged.connect(self.changeMarkerSize)
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
        self.use_custom_colors.stateChanged.connect(self.updateCharts)
        color_options_layout.addRow(self.use_custom_colors)

        self.custom_colors(color_options_layout)

        right_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(right_layout)

        font_options_box = QtWidgets.QGroupBox("Font")
        font_options_layout = QtWidgets.QFormLayout(font_options_box)
        self.font_dropdown = QtWidgets.QComboBox()
        self.font_dropdown.setMinimumHeight(20)
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
        bands_layout.addRow(
            "Chart bands",
            self.color_picker("BandsColor", "bands"))

        self.btn_manage_bands = QtWidgets.QPushButton("Manage bands")
        self.btn_manage_bands.setMinimumHeight(20)

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

        vswr_marker_layout.addRow(
            "VSWR Markers",self.color_picker("VSWRColor", "swr"))

        self.vswr_marker_dropdown = QtWidgets.QComboBox()
        self.vswr_marker_dropdown.setMinimumHeight(20)
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
        btn_add_vswr_marker.setMinimumHeight(20)
        btn_remove_vswr_marker = QtWidgets.QPushButton("Remove")
        btn_remove_vswr_marker.setMinimumHeight(20)
        vswr_marker_btn_layout = QtWidgets.QHBoxLayout()
        vswr_marker_btn_layout.addWidget(btn_add_vswr_marker)
        vswr_marker_btn_layout.addWidget(btn_remove_vswr_marker)
        vswr_marker_layout.addRow(vswr_marker_btn_layout)

        btn_add_vswr_marker.clicked.connect(self.addVSWRMarker)
        btn_remove_vswr_marker.clicked.connect(self.removeVSWRMarker)

        markers_box = QtWidgets.QGroupBox("Markers")
        markers_layout = QtWidgets.QFormLayout(markers_box)

        btn_add_marker = QtWidgets.QPushButton("Add")
        btn_add_marker.setMinimumHeight(30)
        btn_add_marker.clicked.connect(self.addMarker)
        self.btn_remove_marker = QtWidgets.QPushButton("Remove")
        self.btn_remove_marker.setMinimumHeight(30)
        self.btn_remove_marker.clicked.connect(self.removeMarker)
        btn_marker_settings = QtWidgets.QPushButton("Settings ...")
        btn_marker_settings.setMinimumHeight(30)
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
        chart00_selection.setMinimumHeight(30)
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
        chart01_selection.setMinimumHeight(30)
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
        chart02_selection.setMinimumHeight(30)
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
        chart10_selection.setMinimumHeight(30)
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
        chart11_selection.setMinimumHeight(30)
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
        chart12_selection.setMinimumHeight(30)
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

        Chart.color.background = self.app.settings.value(
            "BackgroundColor", defaultValue=ChartColors.background,
            type=QtGui.QColor)
        Chart.color.foreground = self.app.settings.value(
            "ForegroundColor", defaultValue=ChartColors.foreground,
            type=QtGui.QColor)
        Chart.color.text = self.app.settings.value(
            "TextColor", defaultValue=ChartColors.text,
            type=QtGui.QColor)
        self.bandsColor = self.app.settings.value(
            "BandsColor", defaultValue=ChartColors.bands,
            type=QtGui.QColor)
        self.app.bands.color = Chart.color.bands
        Chart.color.swr = self.app.settings.value(
            "VSWRColor", defaultValue=ChartColors.swr,
            type=QtGui.QColor)

        self.dark_mode_option.setChecked(
            self.app.settings.value("DarkMode", False, bool))
        self.show_lines_option.setChecked(
            self.app.settings.value("ShowLines", False, bool))
        self.show_marker_number_option.setChecked(
            self.app.settings.value("ShowMarkerNumbers", ChartMarkerConfig.draw_label, bool))
        self.filled_marker_option.setChecked(
            self.app.settings.value("FilledMarkers", ChartMarkerConfig.fill, bool))

        if self.app.settings.value("UseCustomColors",
                                   defaultValue=False, type=bool):
            self.dark_mode_option.setDisabled(True)
            self.dark_mode_option.setChecked(False)
            self.use_custom_colors.setChecked(True)

        left_layout.addWidget(display_options_box)
        left_layout.addWidget(charts_box)
        left_layout.addWidget(markers_box)
        left_layout.addStretch(1)

        right_layout.addWidget(color_options_box)
        right_layout.addWidget(font_options_box)
        right_layout.addWidget(bands_box)
        right_layout.addWidget(vswr_marker_box)
        right_layout.addStretch(1)
        self.update()

    def trace_colors(self, layout: QtWidgets.QLayout):
        for setting, name, attr in (
            ('SweepColor', 'Sweep color', 'sweep'),
            ('SecondarySweepColor', 'Second sweep color', 'sweep_secondary'),
            ('ReferenceColor', 'Reference color', 'reference'),
            ('SecondaryReferenceColor',
             'Second reference color', 'reference_secondary'),
        ):
            cp = self.color_picker(setting, attr)
            layout.addRow(name, cp)

    def custom_colors(self, layout: QtWidgets.QLayout):
        for setting, name, attr in (
            ('BackgroundColor', 'Chart background', 'background'),
            ('ForegroundColor', 'Chart foreground', 'foreground'),
            ('TextColor', 'Chart text', 'text'),
        ):
            cp = self.color_picker(setting, attr)
            layout.addRow(name, cp)

    def color_picker(self, setting: str, attr: str) -> QtWidgets.QPushButton:
        cp = QtWidgets.QPushButton("█")
        cp.setFixedWidth(20)
        cp.setMinimumHeight(20)
        default = getattr(Chart.color, attr)
        color = self.app.settings.value(
            setting, defaultValue=default, type=QtGui.QColor)
        setattr(Chart.color, attr, color)
        self.callback_params[cp] = (setting, attr)
        cp.clicked.connect(self.setColor)
        p = cp.palette()
        p.setColor(QtGui.QPalette.ButtonText, getattr(Chart.color, attr))
        cp.setPalette(p)
        return cp

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
            m.updateLabels(self.app.data.s11, self.app.data.s21)
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
        ChartMarker.cfg.draw_label = state
        self.updateCharts()

    def changeFilledMarkers(self):
        state = self.filled_marker_option.isChecked()
        self.app.settings.setValue("FilledMarkers", state)
        ChartMarker.cfg.fill = state
        self.updateCharts()

    def changeMarkerAtTip(self):
        state = self.marker_at_tip.isChecked()
        self.app.settings.setValue("MarkerAtTip", state)
        ChartMarker.cfg.at_tip = state
        self.updateCharts()

    def changePointSize(self, size: int):
        self.app.settings.setValue("PointSize", size)
        for c in self.app.subscribing_charts:
            c.setPointSize(size)

    def changeLineThickness(self, size: int):
        self.app.settings.setValue("LineThickness", size)
        for c in self.app.subscribing_charts:
            c.setLineThickness(size)

    def changeMarkerSize(self, size: int):
        self.app.settings.setValue("MarkerSize", size)
        ChartMarker.cfg.size = size
        self.markerSizeInput.setValue(size)
        self.updateCharts()

    def changeDarkMode(self):
        state = self.dark_mode_option.isChecked()
        self.app.settings.setValue("DarkMode", state)
        Chart.color.foreground = QtGui.QColor(QtCore.Qt.lightGray)
        if state:
            Chart.color.background = QtGui.QColor(QtCore.Qt.black)
            Chart.color.text = QtGui.QColor(QtCore.Qt.white)
            Chart.color.swr = Chart.color.swr
        else:
            Chart.color.background = QtGui.QColor(QtCore.Qt.white)
            Chart.color.text = QtGui.QColor(QtCore.Qt.black)
            Chart.color.swr = Chart.color.swr
        self.updateCharts()

    def changeSetting(self, setting: str, value: str):
        logger.debug("Setting %s: %s", setting, value)
        self.app.settings.setValue(setting, value)
        self.app.settings.sync()
        self.updateCharts()

    def setColor(self):
        sender = self.sender()
        logger.debug("Sender %s", sender)
        setting, attr = self.callback_params[sender]
        logger.debug("Setting: %s Attribute: %s", setting, attr)

        color = getattr(Chart.color, attr)
        color = QtWidgets.QColorDialog.getColor(
            color, options=QtWidgets.QColorDialog.ShowAlphaChannel)

        if not color.isValid():
            logger.info("Invalid color")
            return

        palette = sender.palette()
        palette.setColor(QtGui.QPalette.ButtonText, color)
        sender.setPalette(palette)
        self.changeSetting(setting, color)

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
        self.app.marker_data_layout.addWidget(new_marker.get_data_layout())
        self.app.marker_frame.adjustSize()

        new_marker.updated.connect(self.app.markerUpdated)
        label, layout = new_marker.getRow()
        self.app.marker_control.layout.insertRow(Marker.count() - 1, label, layout)
        self.btn_remove_marker.setDisabled(False)

        if Marker.count() >= 2:
            self.app.marker_control.check_delta.setDisabled(False)

    def removeMarker(self):
        # keep at least one marker
        if Marker.count() <= 1:
            return
        if Marker.count() == 2:
            self.btn_remove_marker.setDisabled(True)
            self.app.delta_marker_layout.setVisible(False)
            self.app.marker_control.check_delta.setDisabled(True)
        last_marker = self.app.markers.pop()

        last_marker.updated.disconnect(self.app.markerUpdated)
        self.app.marker_data_layout.removeWidget(last_marker.get_data_layout())
        self.app.marker_control.layout.removeRow(Marker.count()-1)
        self.app.marker_frame.adjustSize()

        last_marker.get_data_layout().hide()
        last_marker.get_data_layout().destroy()
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

    def updateCharts(self):
        for c in self.app.subscribing_charts:
            c.update()
