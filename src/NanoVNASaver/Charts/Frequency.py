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
import math

import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Formatting import (
    format_frequency_chart,
    format_frequency_chart_2,
    format_y_axis,
    parse_frequency,
    parse_value,
)
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.SITools import Format, Value

logger = logging.getLogger(__name__)


class FrequencyChart(Chart):
    def __init__(self, name):  # noqa: PLR0915
        super().__init__(name)
        self.maxFrequency = 100000000
        self.minFrequency = 1000000
        self.fixedSpan = False
        self.fixedValues = False
        self.logarithmicX = False
        self.logarithmicY = False

        self.leftMargin: int = 30
        self.rightMargin: int = 20
        self.bottomMargin: int = 20
        self.topMargin: int = 30

        self.dim.width = 250
        self.dim.height = 250
        self.fstart = 0
        self.fstop = 0

        self.name_unit = ""
        self.value_function = lambda x: 0.0

        # TODO: use unscaled values instead of unit dependend ones
        self.minDisplayValue = -1
        self.maxDisplayValue = 1

        self.minValue = -1
        self.maxValue = 1
        self.span = 1

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        mode_group = QtGui.QActionGroup(self)
        self.menu = QtWidgets.QMenu()

        self.reset = QtGui.QAction("Reset")
        self.reset.triggered.connect(self.resetDisplayLimits)
        self.menu.addAction(self.reset)

        self.x_menu = QtWidgets.QMenu("Frequency axis")
        self.action_automatic = QtGui.QAction("Automatic")
        self.action_automatic.setCheckable(True)
        self.action_automatic.setChecked(True)
        self.action_automatic.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked())
        )
        self.action_fixed_span = QtGui.QAction("Fixed span")
        self.action_fixed_span.setCheckable(True)
        self.action_fixed_span.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked())
        )
        mode_group.addAction(self.action_automatic)
        mode_group.addAction(self.action_fixed_span)
        self.x_menu.addAction(self.action_automatic)
        self.x_menu.addAction(self.action_fixed_span)
        self.x_menu.addSeparator()

        self.action_set_fixed_start = QtGui.QAction(
            f"Start ({format_frequency_chart(self.minFrequency)})"
        )
        self.action_set_fixed_start.triggered.connect(self.setMinimumFrequency)

        self.action_set_fixed_stop = QtGui.QAction(
            f"Stop ({format_frequency_chart(self.maxFrequency)})"
        )
        self.action_set_fixed_stop.triggered.connect(self.setMaximumFrequency)

        self.x_menu.addAction(self.action_set_fixed_start)
        self.x_menu.addAction(self.action_set_fixed_stop)

        self.x_menu.addSeparator()
        frequency_mode_group = QtGui.QActionGroup(self.x_menu)
        self.action_set_linear_x = QtGui.QAction("Linear")
        self.action_set_linear_x.setCheckable(True)
        self.action_set_logarithmic_x = QtGui.QAction("Logarithmic")
        self.action_set_logarithmic_x.setCheckable(True)
        frequency_mode_group.addAction(self.action_set_linear_x)
        frequency_mode_group.addAction(self.action_set_logarithmic_x)
        self.action_set_linear_x.triggered.connect(
            lambda: self.setLogarithmicX(False)
        )
        self.action_set_logarithmic_x.triggered.connect(
            lambda: self.setLogarithmicX(True)
        )
        self.action_set_linear_x.setChecked(True)
        self.x_menu.addAction(self.action_set_linear_x)
        self.x_menu.addAction(self.action_set_logarithmic_x)

        self.y_menu = QtWidgets.QMenu("Data axis")
        self.y_action_automatic = QtGui.QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked())
        )
        self.y_action_fixed_span = QtGui.QAction("Fixed span")
        self.y_action_fixed_span.setCheckable(True)
        self.y_action_fixed_span.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked())
        )
        mode_group = QtGui.QActionGroup(self)
        mode_group.addAction(self.y_action_automatic)
        mode_group.addAction(self.y_action_fixed_span)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed_span)
        self.y_menu.addSeparator()

        self.action_set_fixed_minimum = QtGui.QAction(
            f"Minimum ({self.minDisplayValue})"
        )
        self.action_set_fixed_minimum.triggered.connect(self.setMinimumValue)

        self.action_set_fixed_maximum = QtGui.QAction(
            f"Maximum ({self.maxDisplayValue})"
        )
        self.action_set_fixed_maximum.triggered.connect(self.setMaximumValue)

        self.y_menu.addAction(self.action_set_fixed_maximum)
        self.y_menu.addAction(self.action_set_fixed_minimum)

        if self.logarithmicYAllowed():  # This only works for some plot types
            self.y_menu.addSeparator()
            vertical_mode_group = QtGui.QActionGroup(self.y_menu)
            self.action_set_linear_y = QtGui.QAction("Linear")
            self.action_set_linear_y.setCheckable(True)
            self.action_set_logarithmic_y = QtGui.QAction("Logarithmic")
            self.action_set_logarithmic_y.setCheckable(True)
            vertical_mode_group.addAction(self.action_set_linear_y)
            vertical_mode_group.addAction(self.action_set_logarithmic_y)
            self.action_set_linear_y.triggered.connect(
                lambda: self.setLogarithmicY(False)
            )
            self.action_set_logarithmic_y.triggered.connect(
                lambda: self.setLogarithmicY(True)
            )
            self.action_set_linear_y.setChecked(True)
            self.y_menu.addAction(self.action_set_linear_y)
            self.y_menu.addAction(self.action_set_logarithmic_y)

        self.menu.addMenu(self.x_menu)
        self.menu.addMenu(self.y_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.action_save_screenshot)
        self.action_popout = QtGui.QAction("Popout chart")
        self.action_popout.triggered.connect(
            lambda: self.popout_requested.emit(self)
        )
        self.menu.addAction(self.action_popout)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.setMinimumSize(
            self.dim.width + self.rightMargin + self.leftMargin,
            self.dim.height + self.topMargin + self.bottomMargin,
        )
        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            )
        )
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, Chart.color.background)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def _set_start_stop(self):
        if self.fixedSpan:
            self.fstart = self.minFrequency
            self.fstop = self.maxFrequency
            return
        if self.data:
            self.fstart = self.data[0].freq
            self.fstop = self.data[len(self.data) - 1].freq
            return
        self.fstart = self.reference[0].freq
        self.fstop = self.reference[len(self.reference) - 1].freq

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText(
            f"Start ({format_frequency_chart(self.minFrequency)})"
        )
        self.action_set_fixed_stop.setText(
            f"Stop ({format_frequency_chart(self.maxFrequency)})"
        )
        self.action_set_fixed_minimum.setText(
            f"Minimum ({self.minDisplayValue})"
        )
        self.action_set_fixed_maximum.setText(
            f"Maximum ({self.maxDisplayValue})"
        )

        if self.fixedSpan:
            self.action_fixed_span.setChecked(True)
        else:
            self.action_automatic.setChecked(True)

        if self.fixedValues:
            self.y_action_fixed_span.setChecked(True)
        else:
            self.y_action_automatic.setChecked(True)

        self.menu.exec(event.globalPos())

    def setFixedSpan(self, fixed_span: bool):
        self.fixedSpan = fixed_span
        if fixed_span and self.minFrequency >= self.maxFrequency:
            self.fixedSpan = False
            self.action_automatic.setChecked(True)
            self.action_fixed_span.setChecked(False)
        self.update()

    def setFixedValues(self, fixed_values: bool):
        self.fixedValues = fixed_values
        self.update()

    def setLogarithmicX(self, logarithmic: bool):
        self.logarithmicX = logarithmic
        self.update()

    def setLogarithmicY(self, logarithmic: bool):
        self.logarithmicY = logarithmic and self.logarithmicYAllowed()
        self.update()

    def logarithmicYAllowed(self) -> bool:
        return False

    def setMinimumFrequency(self):
        min_freq_str, selected = QtWidgets.QInputDialog.getText(
            self,
            "Start frequency",
            "Set start frequency",
            text=str(self.minFrequency),
        )
        if not selected:
            return
        span = abs(self.maxFrequency - self.minFrequency)
        min_freq = parse_frequency(min_freq_str)
        if min_freq < 0:
            return
        self.minFrequency = min_freq
        if self.minFrequency >= self.maxFrequency:
            self.maxFrequency = self.minFrequency + span
        self.fixedSpan = True
        self.update()

    def setMaximumFrequency(self):
        max_freq_str, selected = QtWidgets.QInputDialog.getText(
            self,
            "Stop frequency",
            "Set stop frequency",
            text=str(self.maxFrequency),
        )
        if not selected:
            return
        span = abs(self.maxFrequency - self.minFrequency)
        max_freq = parse_frequency(max_freq_str)
        if max_freq < 0:
            return
        self.maxFrequency = max_freq
        if self.maxFrequency <= self.minFrequency:
            self.minFrequency = max(self.maxFrequency - span, 0)
        self.fixedSpan = True
        self.update()

    def setMinimumValue(self):
        text, selected = QtWidgets.QInputDialog.getText(
            self,
            "Minimum value",
            "Set minimum value",
            text=format_y_axis(self.minDisplayValue, self.name_unit),
        )
        if not selected:
            return
        text = text.replace("dB", "")
        min_val = parse_value(text)
        yspan = abs(self.maxDisplayValue - self.minDisplayValue)
        self.minDisplayValue = min_val
        if self.minDisplayValue >= self.maxDisplayValue:
            self.maxDisplayValue = self.minDisplayValue + yspan
        # TODO: negativ logarythmical scale
        # if self.logarithmicY and min_val <= 0:
        #    self.minDisplayValue = 0.01
        self.fixedValues = True
        self.update()

    def setMaximumValue(self):
        text, selected = QtWidgets.QInputDialog.getText(
            self,
            "Maximum value",
            "Set maximum value",
            text=format_y_axis(self.maxDisplayValue, self.name_unit),
        )
        text = text.replace("dB", "")
        if not selected:
            return
        max_val = parse_value(text)
        yspan = abs(self.maxDisplayValue - self.minDisplayValue)
        self.maxDisplayValue = max_val
        if self.maxDisplayValue <= self.minDisplayValue:
            self.minDisplayValue = self.maxDisplayValue - yspan
        self.fixedValues = True
        self.update()

    def resetDisplayLimits(self):
        self.fixedValues = False
        self.y_action_automatic.setChecked(True)
        self.fixedSpan = False
        self.action_automatic.setChecked(True)
        self.logarithmicX = False
        self.action_set_linear_x.setChecked(True)
        self.logarithmicY = False
        if self.logarithmicYAllowed():
            self.action_set_linear_y.setChecked(True)
        self.update()

    def getXPosition(self, d: Datapoint) -> int:
        span = self.fstop - self.fstart
        if span > 0:
            if self.logarithmicX:
                span = math.log(self.fstop) - math.log(self.fstart)
                return self.leftMargin + round(
                    self.dim.width
                    * (math.log(d.freq) - math.log(self.fstart))
                    / span
                )
            return self.leftMargin + round(
                self.dim.width * (d.freq - self.fstart) / span
            )
        return math.floor(self.width() / 2)

    def getYPosition(self, d: Datapoint) -> int:
        try:
            return self.topMargin + round(
                (self.maxValue - self.value_function(d))
                / self.span
                * self.dim.height
            )
        except ValueError:
            return self.topMargin

    def frequencyAtPosition(self, x, limit=True) -> int:
        """
        Calculates the frequency at a given X-position
        :param limit: Determines whether frequencies outside the
                      currently displayed span can be returned.
        :param x:     The X position to calculate for.
        :return:      The frequency at the given position, if one
                      exists or -1 otherwise. If limit is True,
                      and the value is before or after the chart,
                      returns minimum or maximum frequencies.
        """
        if self.fstop - self.fstart <= 0:
            return -1
        absx = x - self.leftMargin
        if limit:
            if absx < 0:
                return self.fstart
            if absx > self.dim.width:
                return self.fstop
        if self.logarithmicX:
            span = math.log(self.fstop) - math.log(self.fstart)
            step = span / self.dim.width
            return round(math.exp(math.log(self.fstart) + absx * step))
        span = self.fstop - self.fstart
        step = span / self.dim.width
        return round(self.fstart + absx * step)

    def valueAtPosition(self, y) -> list[float]:
        """
        Returns the chart-specific value(s) at the specified Y-position
        :param y: The Y position to calculate for.
        :return: A list of the values at the Y-position, either
                 containing a single value, or the two values for the
                 chart from left to right Y-axis.  If no value can be
                 found, returns the empty list.  If the frequency
                 is above or below the chart, returns maximum
                 or minimum values.
        """
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.maxValue)
        return [val * 10e11]

    def zoomTo(self, x1, y1, x2, y2):
        val1 = self.valueAtPosition(y1)
        val2 = self.valueAtPosition(y2)

        if len(val1) == len(val2) == 1 and val1[0] != val2[0]:
            self.minDisplayValue = round(min(val1[0], val2[0]), 3)
            self.maxDisplayValue = round(max(val1[0], val2[0]), 3)
            self.setFixedValues(True)

        freq1 = max(1, self.frequencyAtPosition(x1, limit=False))
        freq2 = max(1, self.frequencyAtPosition(x2, limit=False))

        if freq1 > 0 and freq2 > 0 and freq1 != freq2:
            self.minFrequency = min(freq1, freq2)
            self.maxFrequency = max(freq1, freq2)
            self.setFixedSpan(True)

        self.update()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent):
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
        f = self.frequencyAtPosition(x)
        if x == -1:
            a0.ignore()
            return
        a0.accept()
        m = self.getActiveMarker()
        if m is not None:
            m.setFrequency(str(f))

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.dim.width = a0.size().width() - self.rightMargin - self.leftMargin
        self.dim.height = (
            a0.size().height() - self.bottomMargin - self.topMargin
        )
        self.update()

    def paintEvent(self, _: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        self._check_frequency_boundaries(qp)
        if self.dragbox.state and self.dragbox.pos[0] != -1:
            self.drawDragbog(qp)
        qp.end()

    def _data_oob(self, data: list[Datapoint]) -> bool:
        return data[0].freq > self.fstop or self.data[-1].freq < self.fstart

    def _check_frequency_boundaries(self, qp: QtGui.QPainter):
        if (
            self.data
            and self._data_oob(self.data)
            and (not self.reference or self._data_oob(self.reference))
        ):
            # Data outside frequency range
            qp.setBackgroundMode(Qt.BGMode.OpaqueMode)
            qp.setBackground(Chart.color.background)
            qp.setPen(Chart.color.text)
            qp.drawText(
                self.leftMargin + int(self.dim.width // 2) - 70,
                self.topMargin + int(self.dim.height // 2) - 20,
                "Data outside frequency span",
            )

    def drawDragbog(self, qp: QtGui.QPainter):
        dashed_pen = QtGui.QPen(Chart.color.foreground, 1, Qt.PenStyle.DashLine)
        qp.setPen(dashed_pen)
        top_left = QtCore.QPoint(
            self.dragbox.pos_start[0], self.dragbox.pos_start[1]
        )
        bottom_right = QtCore.QPoint(self.dragbox.pos[0], self.dragbox.pos[1])
        rect = QtCore.QRect(top_left, bottom_right)
        qp.drawRect(rect)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Chart.color.text))
        headline = self.name
        if self.name_unit:
            headline += f" ({self.name_unit})"
        qp.drawText(3, 15, headline)
        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(
            self.leftMargin,
            20,
            self.leftMargin,
            self.topMargin + self.dim.height + 5,
        )
        qp.drawLine(
            self.leftMargin - 5,
            self.topMargin + self.dim.height,
            self.leftMargin + self.dim.width,
            self.topMargin + self.dim.height,
        )
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(Chart.color.sweep)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Chart.color.sweep)
        line_pen.setWidth(self.dim.line)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

        min_value, max_value = self._find_scaling()
        self.maxValue = max_value
        self.minValue = min_value
        span = max_value - min_value
        if span == 0:
            logger.info(
                "Span is zero for %s-Chart, setting to a small value.",
                self.name,
            )
            span = 1e-15
        self.span = span

        target_ticks = math.floor(self.dim.height / 60)
        fmt = Format(max_nr_digits=1)
        for i in range(target_ticks):
            val = min_value + (i / target_ticks) * span
            y = self.topMargin + round(
                (self.maxValue - val) / self.span * self.dim.height
            )
            qp.setPen(Chart.color.text)
            if val != min_value:
                valstr = str(Value(val, fmt=fmt))
                qp.drawText(3, y + 3, valstr)
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(
                self.leftMargin - 5, y, self.leftMargin + self.dim.width, y
            )

        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(
            self.leftMargin - 5,
            self.topMargin,
            self.leftMargin + self.dim.width,
            self.topMargin,
        )
        qp.setPen(Chart.color.text)
        qp.drawText(3, self.topMargin + 4, str(Value(max_value, fmt=fmt)))
        qp.drawText(
            3, self.dim.height + self.topMargin, str(Value(min_value, fmt=fmt))
        )
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, Chart.color.sweep)
        self.drawData(qp, self.reference, Chart.color.reference)
        self.drawMarkers(qp)

    def _find_scaling(self) -> tuple[float, float]:
        min_value = self.minDisplayValue / 10e11
        max_value = self.maxDisplayValue / 10e11
        if self.fixedValues:
            return (min_value, max_value)
        for d in self.data:
            val = self.value_function(d)
            min_value = min(min_value, val)
            max_value = max(max_value, val)
        for d in self.reference:  # Also check min/max for the reference sweep
            if d.freq < self.fstart or d.freq > self.fstop:
                continue
            val = self.value_function(d)
            min_value = min(min_value, val)
            max_value = max(max_value, val)
        return (min_value, max_value)

    def drawFrequencyTicks(self, qp):
        fspan = self.fstop - self.fstart
        qp.setPen(Chart.color.text)
        # Number of ticks does not include the origin
        ticks = math.floor(self.dim.width / 100)

        # try to adapt format to span
        if (
            self.fstart == 0
            or int(fspan / ticks / self.fstart * 10000) > 2  # noqa: PLR2004
        ):
            my_format_frequency = format_frequency_chart
        else:
            my_format_frequency = format_frequency_chart_2

        qp.drawText(
            self.leftMargin - 20,
            self.topMargin + self.dim.height + 15,
            my_format_frequency(self.fstart),
        )

        for i in range(ticks):
            x = self.leftMargin + round((i + 1) * self.dim.width / ticks)
            if self.logarithmicX:
                fspan = math.log(self.fstop) - math.log(self.fstart)
                freq = round(
                    math.exp(((i + 1) * fspan / ticks) + math.log(self.fstart))
                )
            else:
                freq = round(fspan / ticks * (i + 1) + self.fstart)
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(
                x, self.topMargin, x, self.topMargin + self.dim.height + 5
            )
            qp.setPen(Chart.color.text)
            qp.drawText(
                x - 20,
                self.topMargin + self.dim.height + 15,
                my_format_frequency(freq),
            )

    def drawBands(self, qp, fstart, fstop):
        qp.setBrush(self.bands.color)
        qp.setPen(QtGui.QColor(128, 128, 128, 0))  # Don't outline the bands
        for _, s, e in self.bands.bands:
            try:
                start = int(s)
                end = int(e)
            except ValueError:
                continue
            # don't draw if either band not in chart or completely in band
            if start < fstart < fstop < end or end < fstart or start > fstop:
                continue
            x_start = max(
                self.leftMargin + 1, self.getXPosition(Datapoint(start, 0, 0))
            )
            x_stop = min(
                self.leftMargin + self.dim.width,
                self.getXPosition(Datapoint(end, 0, 0)),
            )
            qp.drawRect(
                x_start, self.topMargin, x_stop - x_start, self.dim.height
            )

    def drawData(
        self,
        qp: QtGui.QPainter,
        data: list[Datapoint],
        color: QtGui.QColor,
        y_function=None,
    ):
        if y_function is None:
            y_function = self.getYPosition
        pen = QtGui.QPen(color)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.dim.line)
        qp.setPen(pen)
        for i, d in enumerate(data):
            x = self.getXPosition(d)
            y = y_function(d)
            if y is None:
                continue
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.flag.draw_lines and i > 0:
                prevx = self.getXPosition(data[i - 1])
                prevy = y_function(data[i - 1])
                if prevy is None:
                    continue
                qp.setPen(line_pen)
                if self.isPlotable(x, y):
                    if self.isPlotable(prevx, prevy):
                        qp.drawLine(x, y, prevx, prevy)
                    else:
                        new_x, new_y = self.getPlotable(x, y, prevx, prevy)
                        qp.drawLine(x, y, new_x, new_y)
                elif self.isPlotable(prevx, prevy):
                    new_x, new_y = self.getPlotable(prevx, prevy, x, y)
                    qp.drawLine(prevx, prevy, new_x, new_y)
                qp.setPen(pen)

    def drawMarkers(self, qp, data=None, y_function=None):
        if data is None:
            data = self.data
        if y_function is None:
            y_function = self.getYPosition
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        for m in self.markers:
            if m.location != -1 and m.location < len(data):
                x = self.getXPosition(data[m.location])
                y = y_function(data[m.location])
                if self.isPlotable(x, y):
                    self.drawMarker(
                        x, y, qp, m.color, self.markers.index(m) + 1
                    )

    def isPlotable(self, x, y):
        return (
            y is not None
            and x is not None
            and self.leftMargin <= x <= self.leftMargin + self.dim.width
            and self.topMargin <= y <= self.topMargin + self.dim.height
        )

    def getPlotable(self, x, y, distantx, distanty):
        p1 = np.array([x, y])
        p2 = np.array([distantx, distanty])
        # First check the top line
        if distanty < self.topMargin:
            p3 = np.array([self.leftMargin, self.topMargin])
            p4 = np.array([self.leftMargin + self.dim.width, self.topMargin])
        elif distanty > self.topMargin + self.dim.height:
            p3 = np.array([self.leftMargin, self.topMargin + self.dim.height])
            p4 = np.array(
                [
                    self.leftMargin + self.dim.width,
                    self.topMargin + self.dim.height,
                ]
            )
        else:
            return x, y

        da = p2 - p1
        db = p4 - p3
        dp = p1 - p3
        dap = np.array([-da[1], da[0]])
        denom = np.dot(dap, db)

        if denom:
            x, y = ((np.dot(dap, dp) / denom.astype(float)) * db + p3)[:2]

        return int(x), int(y)

    def copy(self):
        new_chart = super().copy()
        new_chart.fstart = self.fstart
        new_chart.fstop = self.fstop
        new_chart.maxFrequency = self.maxFrequency
        new_chart.minFrequency = self.minFrequency
        new_chart.span = self.span
        new_chart.minDisplayValue = self.minDisplayValue
        new_chart.maxDisplayValue = self.maxDisplayValue
        new_chart.pointSize = self.dim.point
        new_chart.lineThickness = self.dim.line

        new_chart.setFixedSpan(self.fixedSpan)
        new_chart.action_automatic.setChecked(not self.fixedSpan)
        new_chart.action_fixed_span.setChecked(self.fixedSpan)

        new_chart.setFixedValues(self.fixedValues)
        new_chart.y_action_automatic.setChecked(not self.fixedValues)
        new_chart.y_action_fixed_span.setChecked(self.fixedValues)

        new_chart.setLogarithmicX(self.logarithmicX)
        new_chart.action_set_logarithmic_x.setChecked(self.logarithmicX)
        new_chart.action_set_linear_x.setChecked(not self.logarithmicX)

        new_chart.setLogarithmicY(self.logarithmicY)
        if self.logarithmicYAllowed():
            new_chart.action_set_logarithmic_y.setChecked(self.logarithmicY)
            new_chart.action_set_linear_y.setChecked(not self.logarithmicY)
        return new_chart

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        m = self.getActiveMarker()
        if m is not None and a0.modifiers() == Qt.KeyboardModifier.NoModifier:
            if a0.key() in [Qt.Key.Key_Down, Qt.Key.Key_Left]:
                m.frequencyInput.keyPressEvent(
                    QtGui.QKeyEvent(a0.type(), Qt.Key.Key_Down, a0.modifiers())
                )
            elif a0.key() in [Qt.Key.Key_Up, Qt.Key.Key_Right]:
                m.frequencyInput.keyPressEvent(
                    QtGui.QKeyEvent(a0.type(), Qt.Key.Key_Up, a0.modifiers())
                )
        else:
            super().keyPressEvent(a0)
