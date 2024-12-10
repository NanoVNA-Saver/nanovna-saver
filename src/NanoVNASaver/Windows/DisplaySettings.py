#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
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
from typing import TYPE_CHECKING

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QColor, QColorConstants, QPalette, QShortcut

from NanoVNASaver import Defaults
from NanoVNASaver.Charts.Chart import Chart, ChartColors
from NanoVNASaver.Marker.Widget import Marker
from NanoVNASaver.Windows.Bands import BandsWindow
from NanoVNASaver.Windows.Defaults import make_scrollable
from NanoVNASaver.Windows.MarkerSettings import MarkerSettingsWindow

if TYPE_CHECKING:
    from NanoVNASaver.NanoVNASaver import NanoVNASaver as NanoVNA

logger = logging.getLogger(__name__)

MIN_MARKERS_FOR_DELTA = 2


class DisplaySettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: "NanoVNA") -> None:
        super().__init__()

        self.app: "NanoVNA" = app
        self.setWindowTitle("Display settings")
        self.setWindowIcon(self.app.icon)
        self.marker_window = MarkerSettingsWindow(self.app)
        self.callback_params = {}

        QShortcut(QtCore.Qt.Key.Key_Escape, self, self.hide)

        layout = QtWidgets.QHBoxLayout()
        make_scrollable(self, layout)

        left_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(left_layout)

        display_options_box = QtWidgets.QGroupBox("Options")
        display_options_layout = QtWidgets.QFormLayout(display_options_box)

        self.returnloss_group = QtWidgets.QButtonGroup()
        self.returnloss_is_negative = QtWidgets.QRadioButton("Negative")
        self.returnloss_is_positive = QtWidgets.QRadioButton("Positive")
        self.returnloss_group.addButton(self.returnloss_is_positive)
        self.returnloss_group.addButton(self.returnloss_is_negative)

        display_options_layout.addRow(
            "Return loss is:", self.returnloss_is_negative
        )
        display_options_layout.addRow("", self.returnloss_is_positive)

        self.returnloss_is_positive.setChecked(
            Defaults.cfg.chart.returnloss_is_positive
        )
        self.returnloss_is_negative.setChecked(
            not Defaults.cfg.chart.returnloss_is_positive
        )

        self.returnloss_is_positive.toggled.connect(self.changeReturnLoss)
        self.changeReturnLoss()

        self.show_lines_option = QtWidgets.QCheckBox("Show lines")
        show_lines_label = QtWidgets.QLabel(
            "Displays a thin line between data points"
        )
        self.show_lines_option.stateChanged.connect(self.changeShowLines)
        display_options_layout.addRow(self.show_lines_option, show_lines_label)

        self.dark_mode_option = QtWidgets.QCheckBox("Dark mode")
        dark_mode_label = QtWidgets.QLabel("Black background with white text")
        self.dark_mode_option.stateChanged.connect(self.changeDarkMode)
        display_options_layout.addRow(self.dark_mode_option, dark_mode_label)

        self.trace_colors(display_options_layout)

        self.pointSizeInput = QtWidgets.QSpinBox()
        self.pointSizeInput.setMinimumHeight(20)
        pointsize = Defaults.cfg.chart.point_size
        self.pointSizeInput.setValue(pointsize)
        self.changePointSize(pointsize)
        self.pointSizeInput.setMinimum(1)
        self.pointSizeInput.setMaximum(10)
        self.pointSizeInput.setSuffix(" px")
        self.pointSizeInput.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.pointSizeInput.valueChanged.connect(self.changePointSize)
        display_options_layout.addRow("Point size", self.pointSizeInput)

        self.lineThicknessInput = QtWidgets.QSpinBox()
        self.lineThicknessInput.setMinimumHeight(20)
        linethickness = Defaults.cfg.chart.line_thickness
        self.lineThicknessInput.setValue(linethickness)
        self.changeLineThickness(linethickness)
        self.lineThicknessInput.setMinimum(1)
        self.lineThicknessInput.setMaximum(10)
        self.lineThicknessInput.setSuffix(" px")
        self.lineThicknessInput.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.lineThicknessInput.valueChanged.connect(self.changeLineThickness)
        display_options_layout.addRow("Line thickness", self.lineThicknessInput)

        self.markerSizeInput = QtWidgets.QSpinBox()
        self.markerSizeInput.setMinimumHeight(20)
        markersize = Defaults.cfg.chart.marker_size
        self.markerSizeInput.setValue(markersize)
        self.markerSizeInput.setMinimum(4)
        self.markerSizeInput.setMaximum(20)
        self.markerSizeInput.setSingleStep(2)
        self.markerSizeInput.setSuffix(" px")
        self.markerSizeInput.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.markerSizeInput.valueChanged.connect(self.changeMarkerSize)
        display_options_layout.addRow("Marker size", self.markerSizeInput)

        self.show_marker_number_option = QtWidgets.QCheckBox(
            "Show marker numbers"
        )
        show_marker_number_label = QtWidgets.QLabel(
            "Displays the marker number next to the marker"
        )
        self.show_marker_number_option.stateChanged.connect(
            self.changeShowMarkerNumber
        )
        display_options_layout.addRow(
            self.show_marker_number_option, show_marker_number_label
        )

        self.filled_marker_option = QtWidgets.QCheckBox("Filled markers")
        filled_marker_label = QtWidgets.QLabel(
            "Shows the marker as a filled triangle"
        )
        self.filled_marker_option.stateChanged.connect(self.changeFilledMarkers)
        display_options_layout.addRow(
            self.filled_marker_option, filled_marker_label
        )

        self.marker_tip_group = QtWidgets.QButtonGroup()
        self.marker_at_center = QtWidgets.QRadioButton(
            "At the center of the marker"
        )
        self.marker_at_tip = QtWidgets.QRadioButton("At the tip of the marker")
        self.marker_tip_group.addButton(self.marker_at_center)
        self.marker_tip_group.addButton(self.marker_at_tip)

        display_options_layout.addRow("Data point is:", self.marker_at_center)
        display_options_layout.addRow("", self.marker_at_tip)

        self.marker_at_tip.setChecked(Defaults.cfg.chart.marker_at_tip)
        self.marker_at_center.setChecked(not Defaults.cfg.chart.marker_at_tip)

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
        self.font_dropdown.setCurrentText(str(Defaults.cfg.gui.font_size))
        self.changeFont()

        self.font_dropdown.currentTextChanged.connect(self.changeFont)
        font_options_layout.addRow("Font size", self.font_dropdown)

        bands_box = QtWidgets.QGroupBox("Bands")
        bands_layout = QtWidgets.QFormLayout(bands_box)

        self.show_bands = QtWidgets.QCheckBox("Show bands")
        self.show_bands.setChecked(self.app.bands.enabled)
        self.show_bands.stateChanged.connect(
            lambda: self.setShowBands(self.show_bands.isChecked())
        )
        bands_layout.addRow(self.show_bands)
        bands_layout.addRow(
            "Chart bands", self.color_picker("BandsColor", "bands")
        )

        self.btn_manage_bands = QtWidgets.QPushButton("Manage bands")
        self.btn_manage_bands.setMinimumHeight(20)

        self.bandsWindow = BandsWindow(self.app)
        self.btn_manage_bands.clicked.connect(self.displayBandsWindow)

        bands_layout.addRow(self.btn_manage_bands)

        vswr_marker_box = QtWidgets.QGroupBox("VSWR Markers")
        vswr_marker_layout = QtWidgets.QFormLayout(vswr_marker_box)

        self.vswrMarkers: list[float] = self.app.settings.value(
            "VSWRMarkers", [], float
        )

        if isinstance(self.vswrMarkers, float):
            # Single values from the .ini become floats rather than lists.
            # Convert them.
            self.vswrMarkers = (
                [] if self.vswrMarkers == 0.0 else [self.vswrMarkers]
            )

        vswr_marker_layout.addRow(
            "VSWR Markers", self.color_picker("VSWRColor", "swr")
        )

        self.vswr_marker_dropdown = QtWidgets.QComboBox()
        self.vswr_marker_dropdown.setMinimumHeight(20)
        vswr_marker_layout.addRow(self.vswr_marker_dropdown)

        if not self.vswrMarkers:
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

        selections = [c.name for c in self.app.selectable_charts]
        selections.append("None")

        self._chart_selection(charts_layout, selections)

        chart_colors = ChartColors()
        Chart.color.background = self.app.settings.value(
            "BackgroundColor",
            defaultValue=chart_colors.background,
            type=QColor,
        )
        Chart.color.foreground = self.app.settings.value(
            "ForegroundColor",
            defaultValue=chart_colors.foreground,
            type=QColor,
        )
        Chart.color.text = self.app.settings.value(
            "TextColor", defaultValue=chart_colors.text, type=QColor
        )
        self.bandsColor = self.app.settings.value(
            "BandsColor", defaultValue=chart_colors.bands, type=QColor
        )
        self.app.bands.color = Chart.color.bands
        Chart.color.swr = self.app.settings.value(
            "VSWRColor", defaultValue=chart_colors.swr, type=QColor
        )

        self.dark_mode_option.setChecked(Defaults.cfg.gui.dark_mode)
        self.show_lines_option.setChecked(Defaults.cfg.chart.show_lines)
        self.show_marker_number_option.setChecked(
            Defaults.cfg.chart.marker_label
        )
        self.filled_marker_option.setChecked(Defaults.cfg.chart.marker_filled)

        if self.app.settings.value(
            "UseCustomColors", defaultValue=False, type=bool
        ):
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

    def _chart_selection(self, charts_layout, selections) -> None:
        def _combo_box(
            key: str, val: str, x: int, y: int
        ) -> QtWidgets.QComboBox:
            box = QtWidgets.QComboBox()
            box.setMinimumHeight(30)
            box.addItems(selections)
            chart = self.app.settings.value(key, val)
            if box.findText(chart) > -1:
                box.setCurrentText(chart)
            else:
                box.setCurrentText(val)
            box.currentTextChanged.connect(
                lambda: self.changeChart(x, y, box.currentText())
            )
            charts_layout.addWidget(box, x, y)
            return box

        chart00_selection = _combo_box("Chart00", "S11 Smith Chart", 0, 0)
        chart01_selection = _combo_box("Chart01", "S11 Return Loss", 0, 1)
        chart02_selection = _combo_box("Chart02", "None", 0, 2)
        chart10_selection = _combo_box("Chart10", "S21 Polar Plot", 1, 0)
        chart11_selection = _combo_box("Chart11", "S21 Gain", 1, 1)
        chart12_selection = _combo_box("Chart12", "None", 1, 2)

        self.changeChart(0, 0, chart00_selection.currentText())
        self.changeChart(0, 1, chart01_selection.currentText())
        self.changeChart(0, 2, chart02_selection.currentText())
        self.changeChart(1, 0, chart10_selection.currentText())
        self.changeChart(1, 1, chart11_selection.currentText())
        self.changeChart(1, 2, chart12_selection.currentText())

    def trace_colors(self, layout: QtWidgets.QLayout) -> None:
        for setting, name, attr in (
            ("SweepColor", "Sweep color", "sweep"),
            ("SecondarySweepColor", "Second sweep color", "sweep_secondary"),
            ("ReferenceColor", "Reference color", "reference"),
            (
                "SecondaryReferenceColor",
                "Second reference color",
                "reference_secondary",
            ),
        ):
            cp = self.color_picker(setting, attr)
            layout.addRow(name, cp)

    def custom_colors(self, layout: QtWidgets.QLayout) -> None:
        for setting, name, attr in (
            ("BackgroundColor", "Chart background", "background"),
            ("ForegroundColor", "Chart foreground", "foreground"),
            ("TextColor", "Chart text", "text"),
        ):
            cp = self.color_picker(setting, attr)
            layout.addRow(name, cp)

    def color_picker(self, setting: str, attr: str) -> QtWidgets.QPushButton:
        cp = QtWidgets.QPushButton("█")
        cp.setFixedWidth(20)
        cp.setMinimumHeight(20)
        default = getattr(Chart.color, attr)
        color = self.app.settings.value(
            setting, defaultValue=default, type=QColor
        )
        setattr(Chart.color, attr, color)
        self.callback_params[cp] = (setting, attr)
        cp.clicked.connect(self.setColor)
        p = cp.palette()
        p.setColor(QPalette.ColorRole.ButtonText, getattr(Chart.color, attr))
        cp.setPalette(p)
        return cp

    def changeChart(self, x, y, chart) -> None:
        found = None
        for c in self.app.selectable_charts:
            if c.name == chart:
                found = c
        self.app.settings.setValue(f"Chart{x}{y}", chart)
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

    def changeReturnLoss(self) -> None:
        state = self.returnloss_is_positive.isChecked()
        Defaults.cfg.chart.returnloss_is_positive = bool(state)
        for m in self.app.markers:
            m.returnloss_is_positive = state
            m.updateLabels(self.app.data.s11, self.app.data.s21)
        self.marker_window.exampleMarker.returnloss_is_positive = state
        self.marker_window.updateMarker()
        self.app.charts["s11"]["log_mag"].isInverted = state
        self.app.charts["s11"]["log_mag"].update()

    def changeShowLines(self) -> None:
        state = self.show_lines_option.isChecked()
        Defaults.cfg.chart.show_lines = bool(state)
        for c in self.app.subscribing_charts:
            c.setDrawLines(state)

    def changeShowMarkerNumber(self) -> None:
        Defaults.cfg.chart.marker_label = bool(
            self.show_marker_number_option.isChecked()
        )
        self.updateCharts()

    def changeFilledMarkers(self):
        Defaults.cfg.chart.marker_filled = bool(
            self.filled_marker_option.isChecked()
        )
        self.updateCharts()

    def changeMarkerAtTip(self) -> None:
        Defaults.cfg.chart.marker_at_tip = bool(self.marker_at_tip.isChecked())
        self.updateCharts()

    def changePointSize(self, size: int) -> None:
        Defaults.cfg.chart.point_size = size
        for c in self.app.subscribing_charts:
            c.setPointSize(size)

    def changeLineThickness(self, size: int) -> None:
        Defaults.cfg.chart.line_thickness = size
        for c in self.app.subscribing_charts:
            c.setLineThickness(size)

    def changeMarkerSize(self, size: int) -> None:
        Defaults.cfg.chart.marker_size = size
        self.markerSizeInput.setValue(size)
        self.updateCharts()

    def changeDarkMode(self) -> None:
        state = self.dark_mode_option.isChecked()
        Defaults.cfg.gui.dark_mode = bool(state)
        Chart.color.foreground = QColor(QColorConstants.LightGray)
        if state:
            Chart.color.background = QColor(QColorConstants.Black)
            Chart.color.text = QColor(QColorConstants.White)
        else:
            Chart.color.background = QColor(QColorConstants.White)
            Chart.color.text = QColor(QColorConstants.Black)
        Chart.color.swr = Chart.color.swr
        self.updateCharts()

    def changeSetting(self, setting: str, value: str) -> None:
        logger.debug("Setting %s: %s", setting, value)
        self.app.settings.setValue(setting, value)
        self.app.settings.sync()
        self.updateCharts()

    def setColor(self) -> None:
        sender = self.sender()
        logger.debug("Sender %s", sender)
        setting, attr = self.callback_params[sender]
        logger.debug("Setting: %s Attribute: %s", setting, attr)

        color = getattr(Chart.color, attr)
        color = QtWidgets.QColorDialog.getColor(
            color,
            options=QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )

        if not color.isValid():
            logger.info("Invalid color")
            return

        setattr(Chart.color, attr, color)  # update trace color immediately
        palette = sender.palette()
        palette.setColor(QPalette.ColorRole.ButtonText, color)
        sender.setPalette(palette)
        self.changeSetting(setting, color)

    def setShowBands(self, show_bands) -> None:
        self.app.bands.enabled = show_bands
        self.app.bands.settings.setValue("ShowBands", show_bands)
        self.app.bands.settings.sync()
        for c in self.app.subscribing_charts:
            c.update()

    def changeFont(self) -> None:
        font_size = int(self.font_dropdown.currentText())
        Defaults.cfg.gui.font_size = font_size
        app: QtWidgets.QApplication = QtWidgets.QApplication.instance()
        font = app.font()
        font.setPointSize(font_size)
        app.setFont(font)
        self.app.changeFont(font)

    def displayBandsWindow(self) -> None:
        self.bandsWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.bandsWindow)

    def displayMarkerWindow(self) -> None:
        self.marker_window.show()
        QtWidgets.QApplication.setActiveWindow(self.marker_window)

    def addMarker(self) -> None:
        new_marker = Marker("", self.app.settings)
        new_marker.setScale(self.app.scaleFactor)
        self.app.markers.append(new_marker)
        self.app.marker_data_layout.addWidget(new_marker.get_data_layout())
        self.app.marker_frame.adjustSize()

        new_marker.updated.connect(self.app.markerUpdated)
        label, layout = new_marker.getRow()
        self.app.marker_control.layout.insertRow(
            Marker.count() - 1, label, layout
        )
        self.btn_remove_marker.setDisabled(False)

        if Marker.count() >= MIN_MARKERS_FOR_DELTA:
            self.app.marker_control.check_delta.setDisabled(False)

    def removeMarker(self) -> None:
        # keep at least one marker
        if Marker.count() <= 1:
            return
        if Marker.count() == MIN_MARKERS_FOR_DELTA:
            self.btn_remove_marker.setDisabled(True)
            self.app.delta_marker_layout.setVisible(False)
            self.app.marker_control.check_delta.setDisabled(True)
        last_marker = self.app.markers.pop()

        last_marker.updated.disconnect(self.app.markerUpdated)
        self.app.marker_data_layout.removeWidget(last_marker.get_data_layout())
        self.app.marker_control.layout.removeRow(Marker.count() - 1)
        self.app.marker_frame.adjustSize()

        last_marker.get_data_layout().hide()
        last_marker.get_data_layout().destroy()
        label, _ = last_marker.getRow()
        label.hide()

    def addVSWRMarker(self) -> None:
        value, selected = QtWidgets.QInputDialog.getDouble(
            self,
            "Add VSWR Marker",
            "VSWR value to show:",
            min=1.001,
            decimals=3,
        )
        if selected:
            self.vswrMarkers.append(value)
            if self.vswr_marker_dropdown.itemText(0) == "None":
                self.vswr_marker_dropdown.removeItem(0)
            self.vswr_marker_dropdown.addItem(str(value))
            self.vswr_marker_dropdown.setCurrentText(str(value))
            for c in self.app.s11charts:
                c.addSWRMarker(value)
            self.app.settings.setValue("VSWRMarkers", self.vswrMarkers)

    def removeVSWRMarker(self) -> None:
        value_str = self.vswr_marker_dropdown.currentText()
        if value_str != "None":
            value = float(value_str)
            self.vswrMarkers.remove(value)
            self.vswr_marker_dropdown.removeItem(
                self.vswr_marker_dropdown.currentIndex()
            )
            if self.vswr_marker_dropdown.count() == 0:
                self.vswr_marker_dropdown.addItem("None")
                self.app.settings.remove("VSWRMarkers")
            else:
                self.app.settings.setValue("VSWRMarkers", self.vswrMarkers)
            for c in self.app.s11charts:
                c.removeSWRMarker(value)

    def updateCharts(self) -> None:
        for c in self.app.subscribing_charts:
            c.update()
        Defaults.store(self.app.settings, Defaults.cfg)
