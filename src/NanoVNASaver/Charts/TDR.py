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
import math

import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
    QResizeEvent,
    QWheelEvent,
    QShortcut,
    QColor,
    QFontMetrics,
)
from PySide6.QtWidgets import QDialog, QInputDialog, QMenu, QSizePolicy

from .Chart import Chart, ChartPosition

logger = logging.getLogger(__name__)

MIN_IMPEDANCE = 0
MAX_IMPEDANCE = 1000

MIN_S11 = -60
MAX_S11 = 0

MIN_VSWR = 1
MAX_VSWR = 10

class TDRChart(Chart):
    max_display_length: int = 50
    min_display_length: int = 0
    fixed_span: bool = False

    min_y_lim: float = 0.0
    max_y_lim: float = 1000.0

    decimals: int = 1

    format_string: str = ""
    fixed_values: bool = False
    marker_location: int = -1

    def __init__(self, name) -> None:
        super().__init__(name)
        self.tdrWindow: QDialog = QDialog()

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
        self.action_fixed_span = QAction("Fixed span")
        self.action_fixed_span.setCheckable(True)
        self.action_fixed_span.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked())
        )
        self.action_automatic = QAction("Automatic")
        self.action_automatic.setCheckable(True)
        self.action_automatic.setChecked(True)
        self.action_automatic.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked())
        )
        self.mode_group.addAction(self.action_automatic)
        self.mode_group.addAction(self.action_fixed_span)
        self.x_menu.addAction(self.action_automatic)
        self.x_menu.addAction(self.action_fixed_span)
        self.x_menu.addSeparator()

        self.action_set_fixed_start = QAction(
            f"Start ({self.min_display_length})"
        )
        self.action_set_fixed_start.triggered.connect(self.setMinimumLength)

        self.action_set_fixed_stop = QAction(
            f"Stop ({self.max_display_length})"
        )
        self.action_set_fixed_stop.triggered.connect(self.setMaximumLength)

        self.x_menu.addAction(self.action_set_fixed_start)
        self.x_menu.addAction(self.action_set_fixed_stop)

        self.y_menu = QMenu("Y axis")
        self.y_mode_group = QActionGroup(self.y_menu)
        self.y_action_fixed = QAction("Fixed")
        self.y_action_fixed.setCheckable(True)
        self.y_action_fixed.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed.isChecked())
        )
        self.y_action_automatic = QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed.isChecked())
        )
        self.y_mode_group.addAction(self.y_action_automatic)
        self.y_mode_group.addAction(self.y_action_fixed)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed)
        self.y_menu.addSeparator()

        self.y_action_set_fixed_maximum = QAction(f"Maximum ({self.max_y_lim})")
        self.y_action_set_fixed_maximum.triggered.connect(self.setMaximumY)

        self.y_action_set_fixed_minimum = QAction(f"Minimum ({self.min_y_lim})")
        self.y_action_set_fixed_minimum.triggered.connect(self.setMinimumY)

        self.y_menu.addAction(self.y_action_set_fixed_maximum)
        self.y_menu.addAction(self.y_action_set_fixed_minimum)

        self.menu.addMenu(self.x_menu)
        self.menu.addMenu(self.y_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.action_save_screenshot)
        self.action_popout = QAction("Popout chart")
        self.action_popout.triggered.connect(
            lambda: self.popout_requested.emit(self)
        )
        self.menu.addAction(self.action_popout)

        self.dim.width = self.width() - self.leftMargin - self.rightMargin
        self.dim.height = self.height() - self.bottomMargin - self.topMargin

        QShortcut(Qt.Key.Key_Up, self, lambda: self.pan_graph(0, 1))
        QShortcut(Qt.Key.Key_Down, self, lambda: self.pan_graph(0, -1))
        QShortcut(Qt.Key.Key_Left, self, lambda: self.pan_graph(1, 0))
        QShortcut(Qt.Key.Key_Right, self, lambda: self.pan_graph(-1, 0))

    def pan_graph(self, x, y):
        logger.debug(f"Moving graph {x}, {y}")
        dx = self.dim.width / 10 * x
        dy = self.dim.height / 10 * y
        self.zoomTo(
            self.leftMargin + dx,
            self.topMargin + dy,
            self.leftMargin + self.dim.width + dx,
            self.topMargin + self.dim.height + dy,
        )

    def contextMenuEvent(self, event) -> None:
        self.action_set_fixed_start.setText(
            f"Start ({self.min_display_length})"
        )
        self.action_set_fixed_stop.setText(f"Stop ({self.max_display_length})")
        self.y_action_set_fixed_minimum.setText(f"Minimum ({self.min_y_lim})")
        self.y_action_set_fixed_maximum.setText(f"Maximum ({self.max_y_lim})")
        self.menu.exec(event.globalPos())

    def isLinePlotable(self, p1, p2):
        """
        Test if the line could be drawn.
        This is a very simple test. Even if the result is true,
        the line could still be invisible. But if the result is false,
        the line is guaranteed to be invisible.

        Returns
        -------
        False, if the line is outside the current chart area. True otherwise.
        """

        if p1.x() is None or p1.y() is None or p2.x() is None or p2.y() is None:
            return False

        # logger.debug(f"P1 {p1}, {p2}")

        horizontal = [self.leftMargin, self.width() - self.rightMargin]
        x1q = np.searchsorted(horizontal, p1.x())
        x2q = np.searchsorted(horizontal, p2.x())
        # logger.debug(f"x1 {x1q}, {x2q}, horizontal: {horizontal}")
        if x1q == x2q != 1:
            # logger.debug(f"   -> FALSE")
            return False

        vertical = [self.topMargin, self.height() - self.bottomMargin]
        y1q = np.searchsorted(vertical, p1.y())
        y2q = np.searchsorted(vertical, p2.y())
        # logger.debug(f"y1 {y1q}, {y2q}, vertical: {vertical}")
        if y1q == y2q != 1:
            # logger.debug(f"   -> FALSE")
            return False

        # logger.debug(f"   -> TRUE")
        return True

    def isPlotable(self, p: QPoint) -> bool:
        if p.x() is None or p.y() is None:
            return False
        return (
            self.leftMargin <= p.x() <= self.width() - self.rightMargin
            and self.topMargin <= p.y() <= self.height() - self.bottomMargin
        )

    def _configureGraphFromFormat(self) -> None:
        FORMAT_DEFAULTS = {
            "|Z| (lowpass)": (
                MIN_IMPEDANCE,
                MAX_IMPEDANCE,
                "impedance (\N{OHM SIGN})",
                1,
            ),
            "S11 (lowpass)": (MIN_S11, MAX_S11, "S11 (dB)", 1),
            "VSWR (lowpass)": (MIN_VSWR, MAX_VSWR, "VSWR", 2),
            "Refl (lowpass)": (-1, 1, "U", 2),
            "Refl (bandpass)": (0, 1, "U", 2),
        }
        self.min_y_lim, self.max_y_lim, self.format_string, self.decimals = (
            FORMAT_DEFAULTS[self.tdrWindow.format_dropdown.currentText()]
        )

    def resetDisplayLimits(self) -> None:
        self._configureGraphFromFormat()
        self.fixed_span = False
        self.min_display_length = 0
        self.max_display_length = 100
        self.fixed_values = False
        self.update()

    def setFixedSpan(self, fixed_span) -> None:
        self.fixed_span = fixed_span
        self.update()

    def setMinimumLength(self) -> None:
        min_val, selected = QInputDialog.getDouble(
            self,
            "Start length (m)",
            "Set start length (m)",
            value=self.min_display_length,
            minValue=0,
            decimals=1,
        )
        if not selected:
            return
        if not (self.fixed_span and min_val >= self.max_display_length):
            self.min_display_length = round(min_val)
        if self.fixed_span:
            self.update()

    def setMaximumLength(self) -> None:
        max_val, selected = QInputDialog.getDouble(
            self,
            "Stop length (m)",
            "Set stop length (m)",
            value=self.max_display_length,
            minValue=0.1,
            decimals=1,
        )
        if not selected:
            return
        if not (self.fixed_span and max_val <= self.min_display_length):
            self.max_display_length = round(max_val)
        if self.fixed_span:
            self.update()

    def setFixedValues(self, fixed_values) -> None:
        self.fixed_values = fixed_values
        self.update()

    def setMinimumY(self) -> None:
        min_val, selected = QInputDialog.getDouble(
            self,
            "Minimum " + self.format_string,
            "Set minimum " + self.format_string,
            value=self.min_y_lim,
            decimals=self.decimals,
        )
        if not selected:
            return
        if not (self.fixed_values and min_val >= self.max_y_lim):
            self.min_y_lim = min_val
        if self.fixed_values:
            self.update()

    def setMaximumY(self) -> None:
        max_val, selected = QInputDialog.getDouble(
            self,
            "Maximum " + self.format_string,
            "Set maximum " + self.format_string,
            value=self.max_y_lim,
            decimals=self.decimals,
        )
        if not selected:
            return
        if not (self.fixed_values and max_val <= self.min_y_lim):
            self.max_y_lim = max_val
        if self.fixed_values:
            self.update()

    def copy(self) -> "TDRChart":
        new_chart: TDRChart = super().copy()
        new_chart.tdrWindow = self.tdrWindow
        new_chart.min_display_length = self.min_display_length
        new_chart.max_display_length = self.max_display_length
        new_chart.fixed_span = self.fixed_span
        new_chart.min_y_lim = self.min_y_lim
        new_chart.max_y_lim = self.max_y_lim
        new_chart.fixed_values = self.fixed_values
        self.tdrWindow.updated.connect(new_chart.update)
        return new_chart

    def wheelEvent(self, a0: QWheelEvent) -> None:
        a0.accept()
        self.data = [0]  # A bit of cheating otherwise the super().wheelEvent() exits without doing anything.
        super().wheelEvent(a0)

    def mouseMoveEvent(self, a0: QMouseEvent) -> None:
        if not hasattr(self.tdrWindow, "td"):
            return
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
            a0.accept()
            if not self.dragbox.state:
                self.dragbox.state = True
                self.dragbox.pos_start = ChartPosition(
                    a0.position().x(), a0.position().y()
                )
            self.dragbox.pos = ChartPosition(
                a0.position().x(), a0.position().y()
            )
            self.update()
            return

        x = a0.position().x()
        absx = x - self.leftMargin
        if absx < 0 or absx > self.width() - self.rightMargin:
            a0.ignore()
            return
        a0.accept()
        self.marker_location = self.lengthAtPosition(x, limit=False)
        self.update()

    def _draw_ticks(self, height, width, x_step, min_index, qp: QPainter) -> None:
        desired_steps = math.ceil((self.width() - self.leftMargin - self.rightMargin) / 100)

        min_length, max_length, m_per_pixel = self._get_chart_parameters()
        delta_length = max_length - min_length

        step_length =  delta_length / desired_steps #  get approx 10 vertical ticks
        # logger.debug(f"Step length: {step_length}, desired_steps={desired_steps}")
        decimals = math.ceil(abs(math.log10(step_length))) - 1
        delta_length_step = math.ceil(step_length * (10 ** decimals)) / (10 ** decimals)
        # logger.debug(f"delta_length_step: {delta_length_step}, decimals: {decimals}")

        start_length = min_length - (min_length % delta_length_step) + delta_length_step

        for distance in np.arange(start_length, max_length, delta_length_step):
            x = self.leftMargin + round((distance - min_length) / m_per_pixel)

            # lines
            qp.setPen(QPen(Chart.color.foreground))
            qp.drawLine(x, self.topMargin, x, self.topMargin + height)

            # text
            qp.setPen(QPen(Chart.color.text))
            self._draw_centered_hanging_text(qp, f"{{:.{decimals}f}} m".format(distance), QPoint(x, self.topMargin + height), False)

        # text at origin
        qp.setPen(QPen(Chart.color.text))
        distance = self.tdrWindow.distance_axis[min_index] / 2
        self._draw_centered_hanging_text(qp, f"{{:.{decimals}f}} m".format(distance), QPoint(self.leftMargin, self.topMargin + height), False)

    def _draw_y_ticks(
        self, height, width, min_impedance, max_impedance, qp: QPainter
    ) -> None:
        y_step = (max_impedance - min_impedance) / height
        y_ticks = math.floor(height / 60)
        y_tick_step = height / y_ticks
        for i in range(y_ticks):
            y = self.bottomMargin + int(i * y_tick_step)
            qp.setPen(Chart.color.foreground)
            qp.drawLine(self.leftMargin, y, self.leftMargin + width, y)
            y_val = max_impedance - y_step * i * y_tick_step
            qp.setPen(Chart.color.text)
            qp.drawText(3, y + 3, str(round(y_val, self.decimals)))
        qp.setPen(Chart.color.text)
        qp.drawText(
            3,
            self.topMargin + height + 3,
            f"{round(min_impedance, self.decimals)}",
        )

    def _draw_max_point(self, height, x_step, y_step, min_index, qp: QPainter) -> None:
        id_max = np.argmax(self.tdrWindow.td)

        max_point = QPoint(
            self.leftMargin + int((id_max - min_index) / x_step),
            (self.topMargin + height)
            - int(np.real(self.tdrWindow.td[id_max]) / y_step),
        )

        qp.setPen(self.markers[0].color)
        qp.drawEllipse(max_point, 2, 2)
        qp.setPen(Chart.color.text)
        self._draw_centered_hanging_text(
            qp,
            f"{round(self.tdrWindow.distance_axis[id_max] / 2, 2)}m",
             max_point,
            True)

    def _draw_marker(self, height, x_step, y_step, min_index, qp: QPainter):
        marker_point = QPoint(
            self.positionAtLength(self.marker_location, limit=False),
            (self.topMargin + height)
        )
        qp.setPen(Chart.color.text)
        qp.drawEllipse(marker_point, 2, 2)
        self._draw_centered_hanging_text(qp, f"{self.marker_location:.3f} m", marker_point, True)

    def _draw_graph(self, height, width, qp: QPainter) -> None:
        min_index = 0
        max_index = math.ceil(len(self.tdrWindow.distance_axis) / 2)
        if self.fixed_span:
            max_length = max(0.1, self.max_display_length)
            max_index = np.searchsorted(
                self.tdrWindow.distance_axis, max_length * 2
            )
            min_index = np.searchsorted(
                self.tdrWindow.distance_axis, self.min_display_length * 2
            )
            if max_index == min_index:
                if max_index < len(self.tdrWindow.distance_axis) - 1:
                    max_index += 1
                else:
                    min_index -= 1
        x_step = (max_index - min_index) / width

        # TODO: Limit the search to the selected span?
        min_Z = np.min(self.tdrWindow.step_response_Z)
        max_Z = np.max(self.tdrWindow.step_response_Z)

        # Ensure that everything works even if limits are negative
        min_impedance = max(self.min_y_lim, min_Z - 0.05 * np.abs(min_Z))
        max_impedance = min(self.max_y_lim, max_Z + 0.05 * np.abs(max_Z))
        if self.fixed_values:
            min_impedance = self.min_y_lim
            max_impedance = self.max_y_lim

        self._draw_ticks(height, width, x_step, min_index, qp)
        self._draw_y_ticks(height, width, min_impedance, max_impedance, qp)

        pen = QPen(Chart.color.sweep)
        pen.setWidth(self.dim.line if self.flag.draw_lines else self.dim.point)
        qp.setPen(pen)
        y_step = (max_impedance - min_impedance) / height

        tdr_points = [
            QPoint(
                self.leftMargin + int((i - min_index) / x_step),
                (self.topMargin + height) - int(np.real(self.tdrWindow.td[i]) / y_step)
            ) for i in range(min_index, max_index)]
        step_response_points = [
            QPoint(
                self.leftMargin + int((i - min_index) / x_step),
                (self.topMargin + height) - int((self.tdrWindow.step_response_Z[i] - min_impedance) / y_step)
            ) for i in range(min_index, max_index)]

        pen.setColor(Chart.color.sweep)
        qp.setPen(pen)

        if self.flag.draw_lines:
            last_pt = tdr_points[0]
            for point in tdr_points[1:]:
                if self.isLinePlotable(last_pt, point):
                    qp.drawLine(last_pt, point)
                last_pt = point

            pen.setColor(Chart.color.sweep_secondary)
            qp.setPen(pen)
            last_pt = step_response_points[0]
            for point in step_response_points[1:]:
                if self.isLinePlotable(last_pt, point):
                    qp.drawLine(last_pt, point)
                last_pt = point
        else:
            [qp.drawPoint(p) for p in tdr_points if self.isPlotable(p)]
            pen.setColor(Chart.color.sweep_secondary)
            qp.setPen(pen)
            [qp.drawPoint(p) for p in step_response_points if self.isPlotable(p)]

        self._draw_max_point(height, x_step, y_step, min_index, qp)

        if self.marker_location != -1:
            self._draw_marker(height, x_step, y_step, min_index, qp)

    def paintEvent(self, _: QPaintEvent) -> None:
        qp = QPainter(self)
        # qp.setRenderHint(QPainter.Antialiasing)
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
        self.drawTitle(qp)

        if hasattr(self.tdrWindow, "td"):
            self._draw_graph(height, width, qp)

        if self.dragbox.state and self.dragbox.pos[0] != -1:
            self.drawDragbog(qp)

        qp.end()

    def valueAtPosition(self, y: int) -> float:
        if hasattr(self.tdrWindow, "td"):
            height = self.height() - self.topMargin - self.bottomMargin
            absy = (self.height() - y) - self.bottomMargin
            if self.fixed_values:
                min_impedance = self.min_y_lim
                max_impedance = self.max_y_lim
            else:
                min_Z = float(np.min(self.tdrWindow.step_response_Z))
                max_Z = float(np.max(self.tdrWindow.step_response_Z))
                # Ensure that everything works even if limits are negative
                min_impedance = max(
                    self.min_y_lim, min_Z - 0.05 * float(np.abs(min_Z))
                )
                max_impedance = min(
                    self.max_y_lim, max_Z + 0.05 * float(np.abs(max_Z))
                )
            y_step = (max_impedance - min_impedance) / height
            return y_step * absy + min_impedance
        return 0.0

    def _get_chart_parameters(self):
        """
        Get the currently displayed
        start end length in meter and the step size in m/pixel

        Returns:
            float, float, float: min_length, max_length, step_size
        """
        width_px = self.width() - self.leftMargin - self.rightMargin
        min_length = self.min_display_length if self.fixed_span else 0
        max_length = (
            self.max_display_length
            if self.fixed_span
            else (
                self.tdrWindow.distance_axis[
                    math.ceil(len(self.tdrWindow.distance_axis) / 2)
                ]
                / 2
            )
        )
        x_step = float(max_length - min_length) / width_px
        # logger.debug(f"min_length: {min_length}, max_length: {max_length}, x_step: {x_step}")
        return min_length, max_length, x_step

    def lengthAtPosition(self, x: int, limit=True):
        if not hasattr(self.tdrWindow, "td"):
            return 0
        min_length, max_length, x_step = self._get_chart_parameters()
        absx = x - self.leftMargin
        if limit and absx < 0:
            return float(min_length)
        return float(
            max_length if limit and absx > width else absx * x_step + min_length
        )

    def positionAtLength(self, length, limit=True):
        # logger.debug(f"positionAtLength(length={length}, limit={limit})")
        if not hasattr(self.tdrWindow, "td"):
            return 0
        min_length, max_length, x_step = self._get_chart_parameters()
        if limit:
            return self.leftMargin  # really? not sure how to handle this
        pos = ((length - min_length) / x_step) + self.leftMargin
        return pos

    def zoomTo(self, x1, y1, x2, y2) -> None:
        logger.debug(
            f"Zoom to (x,y) by (x,y): ({x1}, {y1}) by ({x2}, {y2})"
        )

        val1 = self.valueAtPosition(y1)
        val2 = self.valueAtPosition(y2)

        if val1 != val2:
            self.min_y_lim = round(min(val1, val2), 3)
            self.max_y_lim = round(max(val1, val2), 3)
            self.setFixedValues(True)

        x_min = min(x1, x2)
        x_max = max(x1, x2)

        # test if we reach the negative length range -> adjust to zero
        if self.lengthAtPosition(x_min, limit=False) < 0:
            at_zero = self.positionAtLength(0, limit=False)
            x_max = x_max + (at_zero - x_min)
            x_min = at_zero

        if self.lengthAtPosition(x_max, limit=False) > (self.tdrWindow.distance_axis[-1] / 2):
            at_end = self.positionAtLength(self.tdrWindow.distance_axis[-1] / 2, limit=False)
            x_min = x_min + (at_end - x_max)
            x_max = at_end

        len1 = max(0, self.lengthAtPosition(x_min, limit=False))
        len2 = max(0, self.lengthAtPosition(x_max, limit=False))

        if len1 >= 0 and len2 >= 0 and len1 != len2:
            self.min_display_length = min(len1, len2)
            self.max_display_length = max(len1, len2)
            self.setFixedSpan(True)

        self.update()

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)
        self.dim.width = self.width() - self.leftMargin - self.rightMargin
        self.dim.height = self.height() - self.bottomMargin - self.topMargin

    def _draw_centered_hanging_text(self, qp, text, center: QPoint, above: bool):
        # Measure text size
        fm = QFontMetrics(qp.font())
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()

        # Compute top-left position for centered text
        x = center.x() - text_width // 2
        y = center.y() + (- text_height / 4 if above else text_height)

        # enhance readability when drawn over ticks
        margin = 5
        rect = QRect(x - margin, y - text_height, text_width + 2 * margin, text_height)
        semi_transparent_bg = QColor(Chart.color.background)
        semi_transparent_bg.setAlpha(150)
        qp.fillRect(rect, semi_transparent_bg)

        # draw the length
        qp.drawText(x, y, text)  # Draw text at computed position

    def get_fft_points(self):
        """
        Get the number of FFT points. When we draw with lines as opposed to
        separate points a lower (but still very high resolution) makes
        the GUI more responsive.
        """
        return 2 ** 12 if self.flag.draw_lines else 2 ** 14
