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
import math
import logging

import numpy as np
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QMouseEvent,
    QPalette,
    QPainter,
    QPaintEvent,
    QPen,
    QResizeEvent,
)
from PyQt6.QtWidgets import QInputDialog, QMenu, QSizePolicy

from NanoVNASaver.Charts.Chart import Chart

logger = logging.getLogger(__name__)


class TDRChart(Chart):
    maxDisplayLength = 50
    minDisplayLength = 0
    fixedSpan = False

    minImpedance = 0
    maxImpedance = 1000
    fixedValues = False

    markerLocation = -1

    def __init__(self, name):
        super().__init__(name)
        self.tdrWindow = None

        self.bottomMargin = 25
        self.topMargin = 20

        self.setMinimumSize(300, 300)
        self.setSizePolicy(
            QSizePolicy(
                QSizePolicy.Policy.MinimumExpanding,
                QSizePolicy.Policy.MinimumExpanding,
            )
        )
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, Chart.color.background)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.menu = QMenu()

        self.reset = QAction("Reset")
        self.reset.triggered.connect(self.resetDisplayLimits)
        self.menu.addAction(self.reset)

        self.x_menu = QMenu("Length axis")
        self.mode_group = QActionGroup(self.x_menu)
        self.action_automatic = QAction("Automatic")
        self.action_automatic.setCheckable(True)
        self.action_automatic.setChecked(True)
        self.action_automatic.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked())
        )
        self.action_fixed_span = QAction("Fixed span")
        self.action_fixed_span.setCheckable(True)
        self.action_fixed_span.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked())
        )
        self.mode_group.addAction(self.action_automatic)
        self.mode_group.addAction(self.action_fixed_span)
        self.x_menu.addAction(self.action_automatic)
        self.x_menu.addAction(self.action_fixed_span)
        self.x_menu.addSeparator()

        self.action_set_fixed_start = QAction(
            f"Start ({self.minDisplayLength})"
        )
        self.action_set_fixed_start.triggered.connect(self.setMinimumLength)

        self.action_set_fixed_stop = QAction(f"Stop ({self.maxDisplayLength})")
        self.action_set_fixed_stop.triggered.connect(self.setMaximumLength)

        self.x_menu.addAction(self.action_set_fixed_start)
        self.x_menu.addAction(self.action_set_fixed_stop)

        self.y_menu = QMenu("Impedance axis")
        self.y_mode_group = QActionGroup(self.y_menu)
        self.y_action_automatic = QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed.isChecked())
        )
        self.y_action_fixed = QAction("Fixed")
        self.y_action_fixed.setCheckable(True)
        self.y_action_fixed.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed.isChecked())
        )
        self.y_mode_group.addAction(self.y_action_automatic)
        self.y_mode_group.addAction(self.y_action_fixed)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed)
        self.y_menu.addSeparator()

        self.y_action_set_fixed_maximum = QAction(
            f"Maximum ({self.maxImpedance})"
        )
        self.y_action_set_fixed_maximum.triggered.connect(
            self.setMaximumImpedance
        )

        self.y_action_set_fixed_minimum = QAction(
            f"Minimum ({self.minImpedance})"
        )
        self.y_action_set_fixed_minimum.triggered.connect(
            self.setMinimumImpedance
        )

        self.y_menu.addAction(self.y_action_set_fixed_maximum)
        self.y_menu.addAction(self.y_action_set_fixed_minimum)

        self.menu.addMenu(self.x_menu)
        self.menu.addMenu(self.y_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.action_save_screenshot)
        self.action_popout = QAction("Popout chart")
        self.action_popout.triggered.connect(
            lambda: self.popoutRequested.emit(self)
        )
        self.menu.addAction(self.action_popout)

        self.dim.width = self.width() - self.leftMargin - self.rightMargin
        self.dim.height = self.height() - self.bottomMargin - self.topMargin

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText(f"Start ({self.minDisplayLength})")
        self.action_set_fixed_stop.setText(f"Stop ({self.maxDisplayLength})")
        self.y_action_set_fixed_minimum.setText(
            f"Minimum ({self.minImpedance})"
        )
        self.y_action_set_fixed_maximum.setText(
            f"Maximum ({self.maxImpedance})"
        )
        self.menu.exec(event.globalPos())

    def isPlotable(self, x, y):
        return (
            self.leftMargin <= x <= self.width() - self.rightMargin
            and self.topMargin <= y <= self.height() - self.bottomMargin
        )

    def resetDisplayLimits(self):
        self.fixedSpan = False
        self.minDisplayLength = 0
        self.maxDisplayLength = 100
        self.fixedValues = False
        self.minImpedance = 0
        self.maxImpedance = 1000
        self.update()

    def setFixedSpan(self, fixed_span):
        self.fixedSpan = fixed_span
        self.update()

    def setMinimumLength(self):
        min_val, selected = QInputDialog.getDouble(
            self,
            "Start length (m)",
            "Set start length (m)",
            value=self.minDisplayLength,
            min=0,
            decimals=1,
        )
        if not selected:
            return
        if not (self.fixedSpan and min_val >= self.maxDisplayLength):
            self.minDisplayLength = min_val
        if self.fixedSpan:
            self.update()

    def setMaximumLength(self):
        max_val, selected = QInputDialog.getDouble(
            self,
            "Stop length (m)",
            "Set stop length (m)",
            value=self.minDisplayLength,
            min=0.1,
            decimals=1,
        )
        if not selected:
            return
        if not (self.fixedSpan and max_val <= self.minDisplayLength):
            self.maxDisplayLength = max_val
        if self.fixedSpan:
            self.update()

    def setFixedValues(self, fixed_values):
        self.fixedValues = fixed_values
        self.update()

    def setMinimumImpedance(self):
        min_val, selected = QInputDialog.getDouble(
            self,
            "Minimum impedance (\N{OHM SIGN})",
            "Set minimum impedance (\N{OHM SIGN})",
            value=self.minDisplayLength,
            min=0,
            decimals=1,
        )
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxImpedance):
            self.minImpedance = min_val
        if self.fixedValues:
            self.update()

    def setMaximumImpedance(self):
        max_val, selected = QInputDialog.getDouble(
            self,
            "Maximum impedance (\N{OHM SIGN})",
            "Set maximum impedance (\N{OHM SIGN})",
            value=self.minDisplayLength,
            min=0.1,
            decimals=1,
        )
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minImpedance):
            self.maxImpedance = max_val
        if self.fixedValues:
            self.update()

    def copy(self):
        new_chart: TDRChart = super().copy()
        new_chart.tdrWindow = self.tdrWindow
        new_chart.minDisplayLength = self.minDisplayLength
        new_chart.maxDisplayLength = self.maxDisplayLength
        new_chart.fixedSpan = self.fixedSpan
        new_chart.minImpedance = self.minImpedance
        new_chart.maxImpedance = self.maxImpedance
        new_chart.fixedValues = self.fixedValues
        self.tdrWindow.updated.connect(new_chart.update)
        return new_chart

    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        if a0.buttons() == Qt.MouseButton.RightButton:
            a0.ignore()
            return
        if a0.buttons() == Qt.MouseButton.MiddleButton:
            # Drag the display
            a0.accept()
            if self.dragbox.move_x != -1 and self.dragbox.move_y != -1:
                dx = self.dragbox.move_x - a0.position().x()
                dy = self.dragbox.move_y - a0.position().y()
                self.zoomTo(
                    self.leftMargin + dx,
                    self.topMargin + dy,
                    self.leftMargin + self.dim.width + dx,
                    self.topMargin + self.dim.height + dy,
                )
            self.dragbox.move_x = a0.position().x()
            self.dragbox.move_y = a0.position().y()
            return
        if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Dragging a box
            if not self.dragbox.state:
                self.dragbox.pos_start = (a0.position().x(), a0.position().y())
            self.dragbox.pos = (a0.position().x(), a0.position().y())
            self.update()
            a0.accept()
            return

        x = a0.position().x()
        absx = x - self.leftMargin
        if absx < 0 or absx > self.width() - self.rightMargin:
            a0.ignore()
            return
        a0.accept()
        width = self.width() - self.leftMargin - self.rightMargin
        if self.tdrWindow.td:
            if self.fixedSpan:
                max_index = np.searchsorted(
                    self.tdrWindow.distance_axis, self.maxDisplayLength * 2
                )
                min_index = np.searchsorted(
                    self.tdrWindow.distance_axis, self.minDisplayLength * 2
                )
                x_step = (max_index - min_index) / width
            else:
                max_index = math.ceil(len(self.tdrWindow.distance_axis) / 2)
                x_step = max_index / width

            self.markerLocation = int(round(absx * x_step))
            self.update()
        return

    def _draw_ticks(self, height, width, x_step, min_index):
        ticks = (self.width() - self.leftMargin) // 100
        qp = QPainter(self)
        for i in range(ticks):
            x = self.leftMargin + round((i + 1) * width / ticks)
            qp.setPen(QPen(Chart.color.foreground))
            qp.drawLine(x, self.topMargin, x, self.topMargin + height)
            qp.setPen(QPen(Chart.color.text))
            distance = (
                self.tdrWindow.distance_axis[
                    min_index + int((x - self.leftMargin) * x_step) - 1
                ]
                / 2
            )
            qp.drawText(
                x - 15, self.topMargin + height + 15, f"{round(distance, 1)}m"
            )
        qp.setPen(QPen(Chart.color.text))
        qp.drawText(
            self.leftMargin - 10,
            self.topMargin + height + 15,
            f"{str(round(self.tdrWindow.distance_axis[min_index] / 2, 1))}m",
        )

    def _draw_y_ticks(self, height, width, min_impedance, max_impedance):
        qp = QPainter(self)
        y_step = (max_impedance - min_impedance) / height
        y_ticks = math.floor(height / 60)
        y_tick_step = height / y_ticks
        for i in range(y_ticks):
            y = self.bottomMargin + int(i * y_tick_step)
            qp.setPen(Chart.color.foreground)
            qp.drawLine(self.leftMargin, y, self.leftMargin + width, y)
            y_val = max_impedance - y_step * i * y_tick_step
            qp.setPen(Chart.color.text)
            qp.drawText(3, y + 3, str(round(y_val, 1)))
        qp.setPen(Chart.color.text)
        qp.drawText(
            3, self.topMargin + height + 3, f"{round(min_impedance, 1)}"
        )

    def _draw_max_point(self, height, x_step, y_step, min_index):
        qp = QPainter(self)
        id_max = np.argmax(self.tdrWindow.td)

        max_point = QPoint(
            self.leftMargin + int((id_max - min_index) / x_step),
            (self.topMargin + height) - int(self.tdrWindow.td[id_max] / y_step),
        )

        qp.setPen(self.markers[0].color)
        qp.drawEllipse(max_point, 2, 2)
        qp.setPen(Chart.color.text)
        qp.drawText(
            max_point.x() - 10,
            max_point.y() - 5,
            f"{round(self.tdrWindow.distance_axis[id_max] / 2, 2)}m",
        )

    def _draw_marker(self, height, x_step, y_step, min_index):
        qp = QPainter(self)
        marker_point = QPoint(
            self.leftMargin + int((self.markerLocation - min_index) / x_step),
            (self.topMargin + height)
            - int(self.tdrWindow.td[self.markerLocation] / y_step),
        )
        qp.setPen(Chart.color.text)
        qp.drawEllipse(marker_point, 2, 2)
        qp.drawText(
            marker_point.x() - 10,
            marker_point.y() - 5,
            f"""{round(
                    self.tdrWindow.distance_axis[self.markerLocation] / 2,
                    2)}m""",
        )

    def _draw_graph(self, height, width):
        min_index = 0
        max_index = math.ceil(len(self.tdrWindow.distance_axis) / 2)

        if self.fixedSpan:
            max_length = max(0.1, self.maxDisplayLength)
            max_index = np.searchsorted(
                self.tdrWindow.distance_axis, max_length * 2
            )
            min_index = np.searchsorted(
                self.tdrWindow.distance_axis, self.minDisplayLength * 2
            )
            if max_index == min_index:
                if max_index < len(self.tdrWindow.distance_axis) - 1:
                    max_index += 1
                else:
                    min_index -= 1
        x_step = (max_index - min_index) / width

        # TODO: Limit the search to the selected span?
        min_impedance = max(0, np.min(self.tdrWindow.step_response_Z) / 1.05)
        max_impedance = min(1000, np.max(self.tdrWindow.step_response_Z) * 1.05)
        if self.fixedValues:
            min_impedance = max(0, self.minImpedance)
            max_impedance = max(0.1, self.maxImpedance)

        y_step = max(self.tdrWindow.td) * 1.1 / height or 1.0e-30

        self._draw_ticks(height, width, x_step, min_index)
        self._draw_y_ticks(height, width, min_impedance, max_impedance)

        qp = QPainter(self)
        pen = QPen(Chart.color.sweep)
        pen.setWidth(self.dim.point)
        qp.setPen(pen)

        y_step = (max_impedance - min_impedance) / height
        for i in range(min_index, max_index):
            x = self.leftMargin + int((i - min_index) / x_step)
            y = (self.topMargin + height) - int(self.tdrWindow.td[i] / y_step)
            if self.isPlotable(x, y):
                pen.setColor(Chart.color.sweep)
                qp.setPen(pen)
                qp.drawPoint(x, y)

            x = self.leftMargin + int((i - min_index) / x_step)
            y = (self.topMargin + height) - int(
                (self.tdrWindow.step_response_Z[i] - min_impedance) / y_step
            )
            if self.isPlotable(x, y):
                pen.setColor(Chart.color.sweep_secondary)
                qp.setPen(pen)
                qp.drawPoint(x, y)

        self._draw_max_point(height, x_step, y_step, min_index)

        if self.markerLocation != -1:
            self._draw_marker(height, x_step, y_step, min_index)

    def paintEvent(self, _: QPaintEvent) -> None:
        qp = QPainter(self)
        qp.setPen(QPen(Chart.color.text))
        qp.drawText(3, 15, self.name)

        width = self.width() - self.leftMargin - self.rightMargin
        height = self.height() - self.bottomMargin - self.topMargin

        qp.setPen(QPen(Chart.color.foreground))
        qp.drawLine(
            self.leftMargin - 5,
            self.height() - self.bottomMargin,
            self.width() - self.rightMargin,
            self.height() - self.bottomMargin,
        )
        qp.drawLine(
            self.leftMargin,
            self.topMargin - 5,
            self.leftMargin,
            self.height() - self.bottomMargin + 5,
        )
        # Number of ticks does not include the origin
        self.drawTitle(qp)

        if self.tdrWindow.td:
            self._draw_graph(height, width)

        if self.dragbox.state and self.dragbox.pos[0] != -1:
            dashed_pen = QPen(Chart.color.foreground, 1, Qt.PenStyle.DashLine)
            qp.setPen(dashed_pen)
            qp.drawRect(
                QRect(
                    QPoint(*self.dragbox.pos_start),
                    QPoint(*self.dragbox.pos),
                )
            )

        qp.end()

    def valueAtPosition(self, y):
        if self.tdrWindow.td:
            height = self.height() - self.topMargin - self.bottomMargin
            absy = (self.height() - y) - self.bottomMargin
            if self.fixedValues:
                min_impedance = self.minImpedance
                max_impedance = self.maxImpedance
            else:
                min_impedance = max(
                    0, np.min(self.tdrWindow.step_response_Z) / 1.05
                )
                max_impedance = min(
                    1000, np.max(self.tdrWindow.step_response_Z) * 1.05
                )
            y_step = (max_impedance - min_impedance) / height
            return y_step * absy + min_impedance
        return 0

    def lengthAtPosition(self, x, limit=True):
        if not self.tdrWindow.td:
            return 0
        width = self.width() - self.leftMargin - self.rightMargin
        absx = x - self.leftMargin
        min_length = self.minDisplayLength if self.fixedSpan else 0
        max_length = (
            self.maxDisplayLength
            if self.fixedSpan
            else (
                self.tdrWindow.distance_axis[
                    math.ceil(len(self.tdrWindow.distance_axis) / 2)
                ]
                / 2
            )
        )

        x_step = (max_length - min_length) / width
        if limit and absx < 0:
            return min_length
        return (
            max_length if limit and absx > width else absx * x_step + min_length
        )

    def zoomTo(self, x1, y1, x2, y2):
        logger.debug(
            "Zoom to (x,y) by (x,y): (%d, %d) by (%d, %d)", x1, y1, x2, y2
        )
        val1 = self.valueAtPosition(y1)
        val2 = self.valueAtPosition(y2)

        if val1 != val2:
            self.minImpedance = round(min(val1, val2), 3)
            self.maxImpedance = round(max(val1, val2), 3)
            self.setFixedValues(True)

        len1 = max(0, self.lengthAtPosition(x1, limit=False))
        len2 = max(0, self.lengthAtPosition(x2, limit=False))

        if len1 >= 0 and len2 >= 0 and len1 != len2:
            self.minDisplayLength = min(len1, len2)
            self.maxDisplayLength = max(len1, len2)
            self.setFixedSpan(True)

        self.update()

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)
        self.dim.width = self.width() - self.leftMargin - self.rightMargin
        self.dim.height = self.height() - self.bottomMargin - self.topMargin
