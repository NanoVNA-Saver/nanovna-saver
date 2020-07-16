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
import math
import logging
from typing import List

import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore

from NanoVNASaver.Formatting import parse_frequency
from NanoVNASaver.RFTools import Datapoint
from .Chart import Chart

logger = logging.getLogger(__name__)


class FrequencyChart(Chart):
    fstart = 0
    fstop = 0

    maxFrequency = 100000000
    minFrequency = 1000000

    minDisplayValue = -1
    maxDisplayValue = 1

    fixedSpan = False
    fixedValues = False

    logarithmicX = False

    leftMargin = 30
    rightMargin = 20
    bottomMargin = 20
    topMargin = 30

    def __init__(self, name):
        super().__init__(name)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        mode_group = QtWidgets.QActionGroup(self)
        self.menu = QtWidgets.QMenu()

        self.reset = QtWidgets.QAction("Reset")
        self.reset.triggered.connect(self.resetDisplayLimits)
        self.menu.addAction(self.reset)

        self.x_menu = QtWidgets.QMenu("Frequency axis")
        self.action_automatic = QtWidgets.QAction("Automatic")
        self.action_automatic.setCheckable(True)
        self.action_automatic.setChecked(True)
        self.action_automatic.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked()))
        self.action_fixed_span = QtWidgets.QAction("Fixed span")
        self.action_fixed_span.setCheckable(True)
        self.action_fixed_span.changed.connect(
            lambda: self.setFixedSpan(self.action_fixed_span.isChecked()))
        mode_group.addAction(self.action_automatic)
        mode_group.addAction(self.action_fixed_span)
        self.x_menu.addAction(self.action_automatic)
        self.x_menu.addAction(self.action_fixed_span)
        self.x_menu.addSeparator()

        self.action_set_fixed_start = QtWidgets.QAction(
            "Start (" + Chart.shortenFrequency(self.minFrequency) + ")")
        self.action_set_fixed_start.triggered.connect(self.setMinimumFrequency)

        self.action_set_fixed_stop = QtWidgets.QAction(
            "Stop (" + Chart.shortenFrequency(self.maxFrequency) + ")")
        self.action_set_fixed_stop.triggered.connect(self.setMaximumFrequency)

        self.x_menu.addAction(self.action_set_fixed_start)
        self.x_menu.addAction(self.action_set_fixed_stop)

        self.x_menu.addSeparator()
        frequency_mode_group = QtWidgets.QActionGroup(self.x_menu)
        self.action_set_linear_x = QtWidgets.QAction("Linear")
        self.action_set_linear_x.setCheckable(True)
        self.action_set_logarithmic_x = QtWidgets.QAction("Logarithmic")
        self.action_set_logarithmic_x.setCheckable(True)
        frequency_mode_group.addAction(self.action_set_linear_x)
        frequency_mode_group.addAction(self.action_set_logarithmic_x)
        self.action_set_linear_x.triggered.connect(
            lambda: self.setLogarithmicX(False))
        self.action_set_logarithmic_x.triggered.connect(
            lambda: self.setLogarithmicX(True))
        self.action_set_linear_x.setChecked(True)
        self.x_menu.addAction(self.action_set_linear_x)
        self.x_menu.addAction(self.action_set_logarithmic_x)

        self.y_menu = QtWidgets.QMenu("Data axis")
        self.y_action_automatic = QtWidgets.QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        self.y_action_fixed_span = QtWidgets.QAction("Fixed span")
        self.y_action_fixed_span.setCheckable(True)
        self.y_action_fixed_span.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        mode_group = QtWidgets.QActionGroup(self)
        mode_group.addAction(self.y_action_automatic)
        mode_group.addAction(self.y_action_fixed_span)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed_span)
        self.y_menu.addSeparator()

        self.action_set_fixed_maximum = QtWidgets.QAction(
            f"Maximum ({self.maxDisplayValue})")
        self.action_set_fixed_maximum.triggered.connect(self.setMaximumValue)

        self.action_set_fixed_minimum = QtWidgets.QAction(
            f"Minimum ({self.minDisplayValue})")
        self.action_set_fixed_minimum.triggered.connect(self.setMinimumValue)

        self.y_menu.addAction(self.action_set_fixed_maximum)
        self.y_menu.addAction(self.action_set_fixed_minimum)

        self.menu.addMenu(self.x_menu)
        self.menu.addMenu(self.y_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.action_save_screenshot)
        self.action_popout = QtWidgets.QAction("Popout chart")
        self.action_popout.triggered.connect(
            lambda: self.popoutRequested.emit(self))
        self.menu.addAction(self.action_popout)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText(
            f"Start ({Chart.shortenFrequency(self.minFrequency)})")
        self.action_set_fixed_stop.setText(
            f"Stop ({Chart.shortenFrequency(self.maxFrequency)})")
        self.action_set_fixed_minimum.setText(
            f"Minimum ({self.minDisplayValue})")
        self.action_set_fixed_maximum.setText(
            f"Maximum ({self.maxDisplayValue})")

        if self.fixedSpan:
            self.action_fixed_span.setChecked(True)
        else:
            self.action_automatic.setChecked(True)

        if self.fixedValues:
            self.y_action_fixed_span.setChecked(True)
        else:
            self.y_action_automatic.setChecked(True)

        self.menu.exec_(event.globalPos())

    def setFixedSpan(self, fixed_span: bool):
        self.fixedSpan = fixed_span
        if fixed_span and self.minFrequency >= self.maxFrequency:
            self.fixedSpan = False
            self.action_automatic.setChecked(True)
            self.action_fixed_span.setChecked(False)
        self.update()

    def setFixedValues(self, fixed_values: bool):
        self.fixedValues = fixed_values
        if fixed_values and self.minDisplayValue >= self.maxDisplayValue:
            self.fixedValues = False
            self.y_action_automatic.setChecked(True)
            self.y_action_fixed_span.setChecked(False)
        self.update()

    def setLogarithmicX(self, logarithmic: bool):
        self.logarithmicX = logarithmic
        self.update()

    def setMinimumFrequency(self):
        min_freq_str, selected = QtWidgets.QInputDialog.getText(
            self, "Start frequency",
            "Set start frequency", text=str(self.minFrequency))
        if not selected:
            return
        min_freq = parse_frequency(min_freq_str)
        if min_freq > 0 and not (self.fixedSpan and min_freq >= self.maxFrequency):
            self.minFrequency = min_freq
        if self.fixedSpan:
            self.update()

    def setMaximumFrequency(self):
        max_freq_str, selected = QtWidgets.QInputDialog.getText(
            self, "Stop frequency",
            "Set stop frequency", text=str(self.maxFrequency))
        if not selected:
            return
        max_freq = parse_frequency(max_freq_str)
        if max_freq > 0 and not (self.fixedSpan and max_freq <= self.minFrequency):
            self.maxFrequency = max_freq
        if self.fixedSpan:
            self.update()

    def setMinimumValue(self):
        min_val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Minimum value",
            "Set minimum value", value=self.minDisplayValue,
            decimals=3)
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayValue):
            self.minDisplayValue = min_val
        if self.fixedValues:
            self.update()

    def setMaximumValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Maximum value",
            "Set maximum value", value=self.maxDisplayValue,
            decimals=3)
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minDisplayValue):
            self.maxDisplayValue = max_val
        if self.fixedValues:
            self.update()

    def resetDisplayLimits(self):
        self.fixedValues = False
        self.y_action_automatic.setChecked(True)
        self.fixedSpan = False
        self.action_automatic.setChecked(True)
        self.logarithmicX = False
        self.action_set_linear_x.setChecked(True)
        self.update()

    def getXPosition(self, d: Datapoint) -> int:
        span = self.fstop - self.fstart
        if span > 0:
            if self.logarithmicX:
                span = math.log(self.fstop) - math.log(self.fstart)
                return self.leftMargin + round(
                    self.chartWidth * (math.log(d.freq) -
                                       math.log(self.fstart)) / span)
            return self.leftMargin + round(
                self.chartWidth * (d.freq - self.fstart) / span)
        return math.floor(self.width()/2)

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
        if self.fstop - self.fstart > 0:
            absx = x - self.leftMargin
            if limit and absx < 0:
                return self.fstart
            if limit and absx > self.chartWidth:
                return self.fstop
            if self.logarithmicX:
                span = math.log(self.fstop) - math.log(self.fstart)
                step = span/self.chartWidth
                return round(math.exp(math.log(self.fstart) + absx * step))
            span = self.fstop - self.fstart
            step = span/self.chartWidth
            return round(self.fstart + absx * step)
        return -1

    def valueAtPosition(self, y) -> List[float]:
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
        return []

    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        if len(self.data) == 0 and len(self.reference) == 0:
            a0.ignore()
            return
        do_zoom_x = do_zoom_y = True
        if a0.modifiers() == QtCore.Qt.ShiftModifier:
            do_zoom_x = False
        if a0.modifiers() == QtCore.Qt.ControlModifier:
            do_zoom_y = False
        if a0.angleDelta().y() > 0:
            # Zoom in
            a0.accept()
            # Center of zoom = a0.x(), a0.y()
            # We zoom in by 1/10 of the width/height.
            rate = a0.angleDelta().y() / 120
            if do_zoom_x:
                zoomx = rate * self.chartWidth / 10
            else:
                zoomx = 0
            if do_zoom_y:
                zoomy = rate * self.chartHeight / 10
            else:
                zoomy = 0
            absx = max(0, a0.x() - self.leftMargin)
            absy = max(0, a0.y() - self.topMargin)
            ratiox = absx/self.chartWidth
            ratioy = absy/self.chartHeight
            p1x = int(self.leftMargin + ratiox * zoomx)
            p1y = int(self.topMargin + ratioy * zoomy)
            p2x = int(self.leftMargin + self.chartWidth - (1 - ratiox) * zoomx)
            p2y = int(self.topMargin + self.chartHeight - (1 - ratioy) * zoomy)
            self.zoomTo(p1x, p1y, p2x, p2y)
        elif a0.angleDelta().y() < 0:
            # Zoom out
            a0.accept()
            # Center of zoom = a0.x(), a0.y()
            # We zoom out by 1/9 of the width/height, to match zoom in.
            rate = -a0.angleDelta().y() / 120
            if do_zoom_x:
                zoomx = rate * self.chartWidth / 9
            else:
                zoomx = 0
            if do_zoom_y:
                zoomy = rate * self.chartHeight / 9
            else:
                zoomy = 0
            absx = max(0, a0.x() - self.leftMargin)
            absy = max(0, a0.y() - self.topMargin)
            ratiox = absx/self.chartWidth
            ratioy = absy/self.chartHeight
            p1x = int(self.leftMargin - ratiox * zoomx)
            p1y = int(self.topMargin - ratioy * zoomy)
            p2x = int(self.leftMargin + self.chartWidth + (1 - ratiox) * zoomx)
            p2y = int(self.topMargin + self.chartHeight + (1 - ratioy) * zoomy)
            self.zoomTo(p1x, p1y, p2x, p2y)
        else:
            a0.ignore()

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
        if a0.buttons() == QtCore.Qt.RightButton:
            a0.ignore()
            return
        if a0.buttons() == QtCore.Qt.MiddleButton:
            # Drag the display
            a0.accept()
            if self.moveStartX != -1 and self.moveStartY != -1:
                dx = self.moveStartX - a0.x()
                dy = self.moveStartY - a0.y()
                self.zoomTo(self.leftMargin + dx, self.topMargin + dy,
                            self.leftMargin + self.chartWidth + dx,
                            self.topMargin + self.chartHeight + dy)

            self.moveStartX = a0.x()
            self.moveStartY = a0.y()
            return
        if a0.modifiers() == QtCore.Qt.ControlModifier:
            # Dragging a box
            if not self.draggedBox:
                self.draggedBoxStart = (a0.x(), a0.y())
            self.draggedBoxCurrent = (a0.x(), a0.y())
            self.update()
            a0.accept()
            return
        x = a0.x()
        f = self.frequencyAtPosition(x)
        if x == -1:
            a0.ignore()
            return
        a0.accept()
        m = self.getActiveMarker()
        if m is not None:
            m.setFrequency(str(f))
            m.frequencyInput.setText(str(f))

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-self.rightMargin-self.leftMargin
        self.chartHeight = a0.size().height() - self.bottomMargin - self.topMargin
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        if (len(self.data) > 0 and
                (self.data[0].freq > self.fstop or
                 self.data[len(self.data)-1].freq < self.fstart)
                and
                (len(self.reference) == 0 or
                 self.reference[0].freq > self.fstop or
                 self.reference[len(self.reference)-1].freq < self.fstart)):
            # Data outside frequency range
            qp.setBackgroundMode(QtCore.Qt.OpaqueMode)
            qp.setBackground(self.backgroundColor)
            qp.setPen(self.textColor)
            qp.drawText(self.leftMargin + self.chartWidth/2 - 70,
                        self.topMargin + self.chartHeight/2 - 20,
                        "Data outside frequency span")
        if self.draggedBox and self.draggedBoxCurrent[0] != -1:
            dashed_pen = QtGui.QPen(self.foregroundColor, 1, QtCore.Qt.DashLine)
            qp.setPen(dashed_pen)
            top_left = QtCore.QPoint(self.draggedBoxStart[0], self.draggedBoxStart[1])
            bottom_right = QtCore.QPoint(self.draggedBoxCurrent[0], self.draggedBoxCurrent[1])
            rect = QtCore.QRect(top_left, bottom_right)
            qp.drawRect(rect)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin + self.chartHeight + 5)
        qp.drawLine(self.leftMargin-5, self.topMargin + self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawFrequencyTicks(self, qp):
        fspan = self.fstop - self.fstart
        qp.setPen(self.textColor)
        qp.drawText(self.leftMargin - 20,
                    self.topMargin + self.chartHeight + 15,
                    Chart.shortenFrequency(self.fstart))
        ticks = math.floor(self.chartWidth / 100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i + 1) * self.chartWidth / ticks)
            if self.logarithmicX:
                fspan = math.log(self.fstop) - math.log(self.fstart)
                freq = round(math.exp(((i + 1) * fspan / ticks) + math.log(self.fstart)))
            else:
                freq = round(fspan / ticks * (i + 1) + self.fstart)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(x, self.topMargin, x, self.topMargin + self.chartHeight + 5)
            qp.setPen(self.textColor)
            qp.drawText(x - 20,
                        self.topMargin + self.chartHeight + 15,
                        Chart.shortenFrequency(freq))

    def drawBands(self, qp, fstart, fstop):
        qp.setBrush(self.bands.color)
        qp.setPen(QtGui.QColor(128, 128, 128, 0))  # Don't outline the bands
        for (_, start, end) in self.bands.bands:
            if fstart < start < fstop and fstart < end < fstop:
                # The band is entirely within the chart
                x_start = self.getXPosition(Datapoint(start, 0, 0))
                x_end = self.getXPosition(Datapoint(end, 0, 0))
                qp.drawRect(x_start,
                            self.topMargin,
                            x_end - x_start,
                            self.chartHeight)
            elif fstart < start < fstop:
                # Only the start of the band is within the chart
                x_start = self.getXPosition(Datapoint(start, 0, 0))
                qp.drawRect(x_start,
                            self.topMargin,
                            self.leftMargin + self.chartWidth - x_start,
                            self.chartHeight)
            elif fstart < end < fstop:
                # Only the end of the band is within the chart
                x_end = self.getXPosition(Datapoint(end, 0, 0))
                qp.drawRect(self.leftMargin + 1,
                            self.topMargin,
                            x_end - (self.leftMargin + 1),
                            self.chartHeight)
            elif start < fstart < fstop < end:
                # All the chart is in a band, we won't show it(?)
                pass

    def drawData(self, qp: QtGui.QPainter, data: List[Datapoint],
                 color: QtGui.QColor, y_function=None):
        if y_function is None:
            y_function = self.getYPosition
        pen = QtGui.QPen(color)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.lineThickness)
        qp.setPen(pen)
        for i, d in enumerate(data):
            x = self.getXPosition(d)
            y = y_function(d)
            if y is None:
                continue
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.getXPosition(data[i - 1])
                prevy = y_function(data[i - 1])
                if prevy is None:
                    continue
                qp.setPen(line_pen)
                if self.isPlotable(x, y) and self.isPlotable(prevx, prevy):
                    qp.drawLine(x, y, prevx, prevy)
                elif self.isPlotable(x, y) and not self.isPlotable(prevx, prevy):
                    new_x, new_y = self.getPlotable(x, y, prevx, prevy)
                    qp.drawLine(x, y, new_x, new_y)
                elif not self.isPlotable(x, y) and self.isPlotable(prevx, prevy):
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
                    self.drawMarker(x, y, qp, m.color, self.markers.index(m)+1)

    def isPlotable(self, x, y):
        return y is not None and x is not None and \
               self.leftMargin <= x <= self.leftMargin + self.chartWidth and \
               self.topMargin <= y <= self.topMargin + self.chartHeight

    def getPlotable(self, x, y, distantx, distanty):
        p1 = np.array([x, y])
        p2 = np.array([distantx, distanty])
        # First check the top line
        if distanty < self.topMargin:
            p3 = np.array([self.leftMargin, self.topMargin])
            p4 = np.array([self.leftMargin + self.chartWidth, self.topMargin])
        elif distanty > self.topMargin + self.chartHeight:
            p3 = np.array([self.leftMargin, self.topMargin + self.chartHeight])
            p4 = np.array([self.leftMargin + self.chartWidth, self.topMargin + self.chartHeight])
        else:
            return x, y
        da = p2 - p1
        db = p4 - p3
        dp = p1 - p3
        dap = np.array([-da[1], da[0]])
        denom = np.dot(dap, db)
        if denom != 0:
            num = np.dot(dap, dp)
            result = (num / denom.astype(float)) * db + p3
            return result[0], result[1]
        return x, y

    def copy(self):
        new_chart: FrequencyChart = super().copy()
        new_chart.fstart = self.fstart
        new_chart.fstop = self.fstop
        new_chart.maxFrequency = self.maxFrequency
        new_chart.minFrequency = self.minFrequency
        new_chart.minDisplayValue = self.minDisplayValue
        new_chart.maxDisplayValue = self.maxDisplayValue
        new_chart.pointSize = self.pointSize
        new_chart.lineThickness = self.lineThickness

        new_chart.setFixedSpan(self.fixedSpan)
        new_chart.action_automatic.setChecked(not self.fixedSpan)
        new_chart.action_fixed_span.setChecked(self.fixedSpan)

        new_chart.setFixedValues(self.fixedValues)
        new_chart.y_action_automatic.setChecked(not self.fixedValues)
        new_chart.y_action_fixed_span.setChecked(self.fixedValues)

        new_chart.setLogarithmicX(self.logarithmicX)
        new_chart.action_set_logarithmic_x.setChecked(self.logarithmicX)
        new_chart.action_set_linear_x.setChecked(not self.logarithmicX)
        return new_chart

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        m = self.getActiveMarker()
        if m is not None and a0.modifiers() == QtCore.Qt.NoModifier:
            if a0.key() == QtCore.Qt.Key_Down or a0.key() == QtCore.Qt.Key_Left:
                m.frequencyInput.keyPressEvent(QtGui.QKeyEvent(
                    a0.type(), QtCore.Qt.Key_Down, a0.modifiers()))
            elif a0.key() == QtCore.Qt.Key_Up or a0.key() == QtCore.Qt.Key_Right:
                m.frequencyInput.keyPressEvent(QtGui.QKeyEvent(
                    a0.type(), QtCore.Qt.Key_Up, a0.modifiers()))
        else:
            super().keyPressEvent(a0)
