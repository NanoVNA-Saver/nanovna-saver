#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
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
import collections
import math
from typing import List
import numpy as np
import logging

from PyQt5 import QtWidgets, QtGui, QtCore

from .Marker import Marker
logger = logging.getLogger(__name__)
Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class Chart(QtWidgets.QWidget):
    sweepColor = QtCore.Qt.darkYellow
    secondarySweepColor = QtCore.Qt.darkMagenta
    referenceColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.blue)
    referenceColor.setAlpha(64)
    backgroundColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.white)
    foregroundColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.lightGray)
    textColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.black)
    data: List[Datapoint] = []
    reference: List[Datapoint] = []
    markers: List[Marker] = []
    bands = None
    draggedMarker: Marker = None
    name = ""
    drawLines = False
    minChartHeight = 200
    minChartWidth = 200

    def __init__(self, name):
        super().__init__()
        self.name = name

    def setSweepColor(self, color : QtGui.QColor):
        self.sweepColor = color
        self.update()

    def setSecondarySweepColor(self, color : QtGui.QColor):
        self.secondarySweepColor = color
        self.update()

    def setReferenceColor(self, color : QtGui.QColor):
        self.referenceColor = color
        self.update()

    def setBackgroundColor(self, color: QtGui.QColor):
        self.backgroundColor = color
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background, color)
        self.setPalette(pal)
        self.update()

    def setForegroundColor(self, color: QtGui.QColor):
        self.foregroundColor = color
        self.update()

    def setTextColor(self, color: QtGui.QColor):
        self.textColor = color
        self.update()

    def setReference(self, data):
        self.reference = data
        self.update()

    def resetReference(self):
        self.reference = []
        self.update()

    def setData(self, data):
        self.data = data
        self.update()

    def setMarkers(self, markers):
        self.markers = markers

    def setBands(self, bands):
        self.bands = bands

    def getActiveMarker(self, event: QtGui.QMouseEvent) -> Marker:
        if self.draggedMarker is not None:
            return self.draggedMarker
        for m in self.markers:
            if m.isMouseControlledRadioButton.isChecked():
                return m
        return None

    def getNearestMarker(self, x, y) -> Marker:
        if len(self.data) == 0:
            return None
        shortest = 10**6
        nearest = None
        for m in self.markers:
            mx, my = self.getPosition(self.data[m.location])
            dx = abs(x - mx)
            dy = abs(y - my)
            distance = math.sqrt(dx**2 + dy**2)
            if distance < shortest:
                shortest = distance
                nearest = m
        return nearest

    def getYPosition(self, d: Datapoint) -> int:
        return 0

    def getXPosition(self, d: Datapoint) -> int:
        return 0

    def getPosition(self, d: Datapoint) -> (int, int):
        return self.getXPosition(d), self.getYPosition(d)

    def setDrawLines(self, drawLines):
        self.drawLines = drawLines
        self.update()

    @staticmethod
    def shortenFrequency(frequency: int) -> str:
        if frequency < 50000:
            return str(frequency)
        if frequency < 5000000:
            return str(round(frequency / 1000)) + "k"
        return str(round(frequency / 1000000, 1)) + "M"

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.RightButton:
            event.ignore()
            return
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.draggedMarker = self.getNearestMarker(event.x(), event.y())
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.draggedMarker = None


class FrequencyChart(Chart):
    fstart = 0
    fstop = 0

    maxFrequency = 100000000
    minFrequency = 1000000

    minDisplayValue = -1
    maxDisplayValue = 1

    fixedSpan = False
    fixedValues = False

    linear = True
    logarithmic = False

    def __init__(self, name):
        super().__init__(name)

        mode_group = QtWidgets.QActionGroup(self)
        self.menu = QtWidgets.QMenu()

        self.reset = QtWidgets.QAction("Reset")
        self.reset.triggered.connect(self.resetDisplayLimits)
        self.menu.addAction(self.reset)

        self.x_menu = QtWidgets.QMenu("Frequency axis")
        self.action_automatic = QtWidgets.QAction("Automatic")
        self.action_automatic.setCheckable(True)
        self.action_automatic.setChecked(True)
        self.action_automatic.changed.connect(lambda: self.setFixedSpan(self.action_fixed_span.isChecked()))
        self.action_fixed_span = QtWidgets.QAction("Fixed span")
        self.action_fixed_span.setCheckable(True)
        self.action_fixed_span.changed.connect(lambda: self.setFixedSpan(self.action_fixed_span.isChecked()))
        mode_group.addAction(self.action_automatic)
        mode_group.addAction(self.action_fixed_span)
        self.x_menu.addAction(self.action_automatic)
        self.x_menu.addAction(self.action_fixed_span)
        self.x_menu.addSeparator()

        self.action_set_fixed_start = QtWidgets.QAction("Start (" + Chart.shortenFrequency(self.minFrequency) + ")")
        self.action_set_fixed_start.triggered.connect(self.setMinimumFrequency)

        self.action_set_fixed_stop = QtWidgets.QAction("Stop (" + Chart.shortenFrequency(self.maxFrequency) + ")")
        self.action_set_fixed_stop.triggered.connect(self.setMaximumFrequency)

        self.x_menu.addAction(self.action_set_fixed_start)
        self.x_menu.addAction(self.action_set_fixed_stop)

        self.y_menu = QtWidgets.QMenu("Data axis")
        self.y_action_automatic = QtWidgets.QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        self.y_action_fixed_span = QtWidgets.QAction("Fixed span")
        self.y_action_fixed_span.setCheckable(True)
        self.y_action_fixed_span.changed.connect(lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        mode_group = QtWidgets.QActionGroup(self)
        mode_group.addAction(self.y_action_automatic)
        mode_group.addAction(self.y_action_fixed_span)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed_span)
        self.y_menu.addSeparator()

        self.action_set_fixed_maximum = QtWidgets.QAction("Maximum (" + str(self.maxDisplayValue) + ")")
        self.action_set_fixed_maximum.triggered.connect(self.setMaximumValue)

        self.action_set_fixed_minimum = QtWidgets.QAction("Minimum (" + str(self.minDisplayValue) + ")")
        self.action_set_fixed_minimum.triggered.connect(self.setMinimumValue)

        self.y_menu.addAction(self.action_set_fixed_maximum)
        self.y_menu.addAction(self.action_set_fixed_minimum)

        self.menu.addMenu(self.x_menu)
        self.menu.addMenu(self.y_menu)

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText("Start (" + Chart.shortenFrequency(self.minFrequency) + ")")
        self.action_set_fixed_stop.setText("Stop (" + Chart.shortenFrequency(self.maxFrequency) + ")")
        self.action_set_fixed_minimum.setText("Minimum (" + str(self.minDisplayValue) + ")")
        self.action_set_fixed_maximum.setText("Maximum (" + str(self.maxDisplayValue) + ")")

        self.menu.exec_(event.globalPos())

    def setFixedSpan(self, fixed_span: bool):
        self.fixedSpan = fixed_span
        self.update()

    def setFixedValues(self, fixed_values: bool):
        self.fixedValues = fixed_values
        self.update()

    def setMinimumFrequency(self):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        min_freq_str, selected = QtWidgets.QInputDialog.getText(self, "Start frequency",
                                                                "Set start frequency", text=str(self.minFrequency))
        if not selected:
            return
        min_freq = NanoVNASaver.parseFrequency(min_freq_str)
        if min_freq > 0:
            self.minFrequency = min_freq
        if self.fixedSpan:
            self.update()

    def setMaximumFrequency(self):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        max_freq_str, selected = QtWidgets.QInputDialog.getText(self, "Stop frequency",
                                                                "Set stop frequency", text=str(self.maxFrequency))
        if not selected:
            return
        max_freq = NanoVNASaver.parseFrequency(max_freq_str)
        if max_freq > 0:
            self.maxFrequency = max_freq
        if self.fixedSpan:
            self.update()

    def setMinimumValue(self):
        min_val, selected = QtWidgets.QInputDialog.getInt(self, "Minimum value",
                                                          "Set minimum value", value=self.minDisplayValue)
        if not selected:
            return
        self.minDisplayValue = min_val
        if self.fixedValues:
            self.update()

    def setMaximumValue(self):
        max_val, selected = QtWidgets.QInputDialog.getInt(self, "Maximum value",
                                                          "Set maximum value", value=self.maxDisplayValue)
        if not selected:
            return
        self.maxDisplayValue = max_val
        if self.fixedValues:
            self.update()

    def resetDisplayLimits(self):
        self.fixedValues = False
        self.y_action_automatic.setChecked(True)
        self.fixedSpan = False
        self.action_automatic.setChecked(True)
        self.update()

    def getXPosition(self, d: Datapoint) -> int:
        span = self.fstop - self.fstart
        if span > 0:
            return self.leftMargin + 1 + round(self.chartWidth * (d.freq - self.fstart) / span)
        else:
            return math.floor(self.width()/2)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.buttons() == QtCore.Qt.RightButton:
            a0.ignore()
            return
        x = a0.x()
        absx = x - self.leftMargin
        if absx < 0 or absx > self.chartWidth:
            a0.ignore()
            return
        a0.accept()
        if self.fstop - self.fstart > 0:
            m = self.getActiveMarker(a0)
            span = self.fstop - self.fstart
            step = span/self.chartWidth
            f = self.fstart + absx * step
            m.setFrequency(str(round(f)))
            m.frequencyInput.setText(str(round(f)))
        return

    def drawBands(self, qp, fstart, fstop):
        qp.setBrush(QtGui.QColor(128, 128, 128, 48))
        qp.setPen(QtGui.QColor(128, 128, 128, 0))
        for (name, start, end) in self.bands.bands:
            if fstart < start < fstop and fstart < end < fstop:
                # The band is entirely within the chart
                x_start = self.getXPosition(Datapoint(start, 0, 0))
                x_end = self.getXPosition(Datapoint(end, 0, 0))
                qp.drawRect(x_start, 30, x_end - x_start, self.chartHeight - 10)
            elif fstart < start < fstop:
                # Only the start of the band is within the chart
                x_start = self.getXPosition(Datapoint(start, 0, 0))
                qp.drawRect(x_start, 30, self.leftMargin + self.chartWidth - x_start, self.chartHeight - 10)
            elif fstart < end < fstop:
                # Only the end of the band is within the chart
                x_end = self.getXPosition(Datapoint(end, 0, 0))
                qp.drawRect(self.leftMargin + 1, 30, x_end - (self.leftmargin + 1), self.chartHeight - 10)
            elif start < fstart < fstop < end:
                # All the chart is in a band, we won't show it(?)
                pass


class SquareChart(Chart):
    def __init__(self, name):
        super().__init__(name)
        sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(sizepolicy)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.setFixedWidth(a0.size().height())
        self.chartWidth = a0.size().height()-40
        self.chartHeight = a0.size().height()-40
        self.update()


class PhaseChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 35
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.minAngle = 0
        self.span = 0

        self.y_menu.setDisabled(True)

        self.setMinimumSize(self.chartWidth + 20 + self.leftMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-20-self.leftMargin
        self.chartHeight = a0.size().height()-40
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, 20+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, 20+self.chartHeight, self.leftMargin+self.chartWidth, 20 + self.chartHeight)
        minAngle = -180
        maxAngle = 180
        span = maxAngle-minAngle
        self.minAngle = minAngle
        self.span = span
        for i in range(minAngle, maxAngle, 90):
            y = 30 + round((i-minAngle)/span*(self.chartHeight-10))
            if i != minAngle and i != maxAngle:
                qp.setPen(QtGui.QPen(self.textColor))
                qp.drawText(3, y+3, str(-i) + "°")
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.setPen(self.textColor)
        qp.drawText(3, 35, str(-minAngle) + "°")
        qp.drawText(3, self.chartHeight+20, str(-maxAngle) + "°")

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if self.fixedSpan:
            fstart = self.minFrequency
            fstop = self.maxFrequency
        else:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop
        fspan = self.fstop-self.fstart

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        minAngle = -180
        maxAngle = 180
        span = maxAngle-minAngle
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(self.fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(self.textColor)
            qp.drawText(x-20, 20+self.chartHeight+15, Chart.shortenFrequency(round(fspan/ticks*(i+1) + self.fstart)))

        qp.setPen(pen)
        for i in range(len(self.data)):
            angle = self.angle(self.data[i])
            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((angle-minAngle)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                angle = self.angle(self.data[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth / len(self.data) * (i-1))
                prevy = 30 + round((angle - minAngle) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            angle = self.angle(self.reference[i])
            x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i].freq - fstart)/fspan)
            y = 30 + round((angle-minAngle)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                angle = self.angle(self.reference[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i-1].freq - fstart)/fspan)
                prevy = 30 + round((angle - minAngle) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                angle = self.angle(self.data[m.location])
                x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * m.location)
                y = 30 + round((angle - minAngle) / span * (self.chartHeight - 10))
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)

    def getXPosition(self, d: Datapoint) -> int:
        span = self.fstop - self.fstart
        return self.leftMargin + 1 + round(self.chartWidth * (d.freq - self.fstart) / span)

    def getYPosition(self, d: Datapoint) -> int:
        angle = self.angle(d)
        return 30 + round((angle - self.minAngle) / self.span * (self.chartHeight - 10))

    @staticmethod
    def angle(d: Datapoint) -> float:
        re = d.re
        im = d.im
        return -math.degrees(math.atan2(im, re))


class VSWRChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.maxDisplayValue = 25
        self.minDisplayValue = 1

        self.setMinimumSize(self.chartWidth + 20 + self.leftMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-20-self.leftMargin
        self.chartHeight = a0.size().height()-40
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, 20+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, 20+self.chartHeight, self.leftMargin+self.chartWidth, 20 + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if self.fixedSpan:
            fstart = self.minFrequency
            fstop = self.maxFrequency
        elif len(self.data) > 0:
            fstart = self.data[0].freq
            fstop = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop
        fspan = fstop-fstart

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        # Find scaling
        if self.fixedValues:
            minVSWR = max(1, self.minDisplayValue)
            maxVSWR = self.maxDisplayValue
        else:
            minVSWR = 1
            maxVSWR = 3
            for d in self.data:
                _, _, vswr = NanoVNASaver.vswr(d)
                if vswr > maxVSWR:
                    maxVSWR = vswr
            maxVSWR = min(self.maxDisplayValue, math.ceil(maxVSWR))
        self.maxVSWR = maxVSWR
        span = maxVSWR-minVSWR
        self.span = span
        ticksize = 1
        if span > 15 and span % 7 == 0:
            ticksize = 7
        elif span > 10 and span % 5 == 0:
            ticksize = 5
        elif span > 12 and span % 4 == 0:
            ticksize = 4
        elif span > 8 and span % 3 == 0:
            ticksize = 3
        elif span > 7 and span % 2 == 0:
            ticksize = 2

        for i in range(minVSWR, maxVSWR, ticksize):
            y = 30 + round((maxVSWR-i)/span*(self.chartHeight-10))
            if i != minVSWR and i != maxVSWR:
                qp.setPen(self.textColor)
                qp.drawText(3, y+3, str(i))
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5, 30, self.leftMargin + self.chartWidth, 30)
        qp.setPen(self.textColor)
        qp.drawText(3, 35, str(maxVSWR))
        qp.drawText(3, self.chartHeight+20, str(minVSWR))
        # At least 100 px between ticks
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(self.textColor)
            qp.drawText(x-20, 20+self.chartHeight+15, Chart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        qp.setPen(pen)
        for i in range(len(self.data)):
            _, _, vswr = NanoVNASaver.vswr(self.data[i])
            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((maxVSWR-vswr)/span*(self.chartHeight-10))
            if y < 30:
                continue
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                _, _, vswr = NanoVNASaver.vswr(self.data[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth / len(self.data) * (i-1))
                prevy = 30 + round((maxVSWR - vswr) / span * (self.chartHeight - 10))
                if prevy < 30:
                    continue
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            _, _, vswr = NanoVNASaver.vswr(self.reference[i])
            x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i].freq - fstart)/fspan)
            y = 30 + round((maxVSWR - vswr) / span * (self.chartHeight - 10))
            if y < 30:
                continue
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                _, _, vswr = NanoVNASaver.vswr(self.reference[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i-1].freq - fstart)/fspan)
                prevy = 30 + round((maxVSWR - vswr) / span * (self.chartHeight - 10))
                if prevy < 30:
                    continue
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                _, _, vswr = NanoVNASaver.vswr(self.data[m.location])
                x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * m.location)
                y = 30 + round((maxVSWR-vswr) / span * (self.chartHeight - 10))
                if y < 30:
                    continue
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)

    def getXPosition(self, d: Datapoint) -> int:
        span = self.fstop - self.fstart
        return self.leftMargin + 1 + round(self.chartWidth * (d.freq - self.fstart) / span)

    def getYPosition(self, d: Datapoint) -> int:
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        _, _, vswr = NanoVNASaver.vswr(d)
        return 30 + round((self.maxVSWR - vswr) / self.span * (self.chartHeight - 10))

    def resetDisplayLimits(self):
        self.maxDisplayValue = 25
        super().resetDisplayLimits()


class PolarChart(SquareChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.chartWidth = 250
        self.chartHeight = 250

        self.setMinimumSize(self.chartWidth + 40, self.chartHeight + 40)
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        centerX = int(self.width()/2)
        centerY = int(self.height()/2)
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawEllipse(QtCore.QPoint(centerX, centerY), int(self.chartWidth/2), int(self.chartHeight/2))
        qp.drawEllipse(QtCore.QPoint(centerX, centerY), int(self.chartWidth/4), int(self.chartHeight/4))
        qp.drawLine(centerX - int(self.chartWidth/2), centerY, centerX + int(self.chartWidth/2), centerY)
        qp.drawLine(centerX, centerY - int(self.chartHeight/2), centerX, centerY + int(self.chartHeight/2))

        qp.drawLine(centerX + int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY + int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerX - int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY - int(self.chartHeight / 2 * math.sin(math.pi / 4)))

        qp.drawLine(centerX + int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY - int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerX - int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY + int(self.chartHeight / 2 * math.sin(math.pi / 4)))

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.width()/2 + self.data[i].re * self.chartWidth/2
            y = self.height()/2 + self.data[i].im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.data[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.data[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        qp.setPen(pen)
        if len(self.data) > 0:
            fstart = self.data[0].freq
            fstop  = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop  = self.reference[len(self.reference)-1].freq
        for i in range(len(self.reference)):
            data = self.reference[i]
            if data.freq < fstart or data.freq > fstop:
                continue
            x = self.width()/2 + data.re * self.chartWidth/2
            y = self.height()/2 + data.im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.reference[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.reference[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                x = self.width() / 2 + self.data[m.location].re * self.chartWidth / 2
                y = self.height() / 2 + self.data[m.location].im * -1 * self.chartHeight / 2
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)
                #qp.drawPoint(int(x), int(y))

    def getXPosition(self, d: Datapoint) -> int:
        return self.width()/2 + d.re * self.chartWidth/2

    def getYPosition(self, d: Datapoint) -> int:
        return self.height()/2 + d.im * -1 * self.chartHeight/2

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        x = a0.x()
        y = a0.y()
        absx = x - (self.width() - self.chartWidth) / 2
        absy = y - (self.height() - self.chartHeight) / 2
        if absx < 0 or absx > self.chartWidth or absy < 0 or absy > self.chartHeight \
                or len(self.data) == len(self.reference) == 0:
            a0.ignore()
            return
        a0.accept()

        if len(self.data) > 0:
            target = self.data
        else:
            target = self.reference
        positions = []
        for d in target:
            thisx = self.width() / 2 + d.re * self.chartWidth / 2
            thisy = self.height() / 2 + d.im * -1 * self.chartHeight / 2
            positions.append(math.sqrt((x - thisx)**2 + (y - thisy)**2))

        minimum_position = positions.index(min(positions))
        m = self.getActiveMarker(a0)
        m.setFrequency(str(round(target[minimum_position].freq)))
        m.frequencyInput.setText(str(round(target[minimum_position].freq)))
        return


class SmithChart(SquareChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.chartWidth = 250
        self.chartHeight = 250

        self.setMinimumSize(self.chartWidth + 40, self.chartHeight + 40)
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        #qp.begin(self)  # Apparently not needed?
        self.drawSmithChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawSmithChart(self, qp: QtGui.QPainter):
        centerX = int(self.width()/2)
        centerY = int(self.height()/2)
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawEllipse(QtCore.QPoint(centerX, centerY), int(self.chartWidth/2), int(self.chartHeight/2))
        qp.drawLine(centerX - int(self.chartWidth/2), centerY, centerX + int(self.chartWidth/2), centerY)

        qp.drawEllipse(QtCore.QPoint(centerX + int(self.chartWidth/4), centerY), int(self.chartWidth/4), int(self.chartHeight/4))  # Re(Z) = 1
        qp.drawEllipse(QtCore.QPoint(centerX + int(2/3*self.chartWidth/2), centerY), int(self.chartWidth/6), int(self.chartHeight/6))  # Re(Z) = 2
        qp.drawEllipse(QtCore.QPoint(centerX + int(3 / 4 * self.chartWidth / 2), centerY), int(self.chartWidth / 8), int(self.chartHeight / 8))  # Re(Z) = 3
        qp.drawEllipse(QtCore.QPoint(centerX + int(5 / 6 * self.chartWidth / 2), centerY), int(self.chartWidth / 12), int(self.chartHeight / 12))  # Re(Z) = 5

        qp.drawEllipse(QtCore.QPoint(centerX + int(1 / 3 * self.chartWidth / 2), centerY), int(self.chartWidth / 3), int(self.chartHeight / 3))  # Re(Z) = 0.5
        qp.drawEllipse(QtCore.QPoint(centerX + int(1 / 6 * self.chartWidth / 2), centerY), int(self.chartWidth / 2.4), int(self.chartHeight / 2.4))  # Re(Z) = 0.2

        qp.drawArc(centerX + int(3/8*self.chartWidth), centerY, int(self.chartWidth/4), int(self.chartWidth/4), 90*16, 152*16)  # Im(Z) = -5
        qp.drawArc(centerX + int(3/8*self.chartWidth), centerY, int(self.chartWidth/4), -int(self.chartWidth/4), -90 * 16, -152 * 16)  # Im(Z) = 5
        qp.drawArc(centerX + int(self.chartWidth/4), centerY, int(self.chartWidth/2), int(self.chartHeight/2), 90*16, 127*16)  # Im(Z) = -2
        qp.drawArc(centerX + int(self.chartWidth/4), centerY, int(self.chartWidth/2), -int(self.chartHeight/2), -90*16, -127*16)  # Im(Z) = 2
        qp.drawArc(centerX, centerY, self.chartWidth, self.chartHeight, 90*16, 90*16)  # Im(Z) = -1
        qp.drawArc(centerX, centerY, self.chartWidth, -self.chartHeight, -90 * 16, -90 * 16)  # Im(Z) = 1
        qp.drawArc(centerX - int(self.chartWidth/2), centerY, self.chartWidth*2, self.chartHeight*2, int(99.5*16), int(43.5*16))  # Im(Z) = -0.5
        qp.drawArc(centerX - int(self.chartWidth/2), centerY, self.chartWidth*2, -self.chartHeight*2, int(-99.5 * 16), int(-43.5 * 16))  # Im(Z) = 0.5
        qp.drawArc(centerX - self.chartWidth*2, centerY, self.chartWidth*5, self.chartHeight*5, int(93.85*16), int(18.85*16))  # Im(Z) = -0.2
        qp.drawArc(centerX - self.chartWidth*2, centerY, self.chartWidth*5, -self.chartHeight*5, int(-93.85 * 16), int(-18.85 * 16))  # Im(Z) = 0.2

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.width()/2 + self.data[i].re * self.chartWidth/2
            y = self.height()/2 + self.data[i].im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.data[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.data[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        qp.setPen(pen)
        if len(self.data) > 0:
            fstart = self.data[0].freq
            fstop  = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop  = self.reference[len(self.reference)-1].freq
        for i in range(len(self.reference)):
            data = self.reference[i]
            if data.freq < fstart or data.freq > fstop:
                continue
            x = self.width()/2 + data.re * self.chartWidth/2
            y = self.height()/2 + data.im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.reference[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.reference[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                x = self.width() / 2 + self.data[m.location].re * self.chartWidth / 2
                y = self.height() / 2 + self.data[m.location].im * -1 * self.chartHeight / 2
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)
                #qp.drawPoint(int(x), int(y))

    def getXPosition(self, d: Datapoint) -> int:
        return self.width()/2 + d.re * self.chartWidth/2

    def getYPosition(self, d: Datapoint) -> int:
        return self.height()/2 + d.im * -1 * self.chartHeight/2

    def heightForWidth(self, a0: int) -> int:
        return a0

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        x = a0.x()
        y = a0.y()
        absx = x - (self.width() - self.chartWidth) / 2
        absy = y - (self.height() - self.chartHeight) / 2
        if absx < 0 or absx > self.chartWidth or absy < 0 or absy > self.chartHeight \
                or len(self.data) == len(self.reference) == 0:
            a0.ignore()
            return
        a0.accept()

        if len(self.data) > 0:
            target = self.data
        else:
            target = self.reference
        positions = []
        for d in target:
            thisx = self.width() / 2 + d.re * self.chartWidth / 2
            thisy = self.height() / 2 + d.im * -1 * self.chartHeight / 2
            positions.append(math.sqrt((x - thisx)**2 + (y - thisy)**2))

        minimum_position = positions.index(min(positions))
        m = self.getActiveMarker(a0)
        m.setFrequency(str(round(target[minimum_position].freq)))
        m.frequencyInput.setText(str(round(target[minimum_position].freq)))
        return


class LogMagChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = -80
        self.maxDisplayValue = 10

        self.setMinimumSize(self.chartWidth + 20 + self.leftMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-20-self.leftMargin
        self.chartHeight = a0.size().height()-40
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        #qp.begin(self)  # Apparently not needed?
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name + " (dB)")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, 20+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, 20+self.chartHeight, self.leftMargin+self.chartWidth, 20 + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if not self.fixedSpan:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
            self.fstart = fstart
            self.fstop = fstop
        else:
            fstart = self.fstart = self.minFrequency
            fstop = self.fstop = self.maxFrequency
        fspan = self.fstop - self.fstart

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = -self.minDisplayValue  # These are negative, because the entire logmag chart is
            minValue = -self.maxDisplayValue  # upside down.
        else:
            # Find scaling
            minValue = 100
            maxValue = 0
            for d in self.data:
                logmag = self.logMag(d)
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                logmag = self.logMag(d)
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag

            minValue = 10*math.floor(minValue/10)
            self.minValue = minValue
            maxValue = 10*math.ceil(maxValue/10)
            self.maxValue = maxValue

        span = maxValue-minValue
        self.span = span
        for i in range(minValue, maxValue, 10):
            y = 30 + round((i-minValue)/span*(self.chartHeight-10))
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            if i > minValue:
                qp.setPen(QtGui.QPen(self.textColor))
                qp.drawText(3, y + 4, str(-i))
        qp.setPen(self.textColor)
        qp.drawText(3, 35, str(-minValue))
        qp.drawText(3, self.chartHeight+20, str(-maxValue))

        # Frequency ticks
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(self.fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(self.textColor)
            qp.drawText(x-20, 20+self.chartHeight+15, LogMagChart.shortenFrequency(round(fspan/ticks*(i+1) + self.fstart)))

        qp.setPen(pen)
        for i in range(len(self.data)):
            if self.data[i].freq < self.fstart or self.data[i].freq > self.fstop:
                continue
            logmag = self.logMag(self.data[i])
            x = self.getXPosition(self.data[i])
            y = 30 + round((logmag-minValue)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                logmag = self.logMag(self.data[i-1])
                prevx = self.getXPosition(self.data[i-1])
                prevy = 30 + round((logmag - minValue) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < self.fstart or self.reference[i].freq > self.fstop:
                continue
            logmag = self.logMag(self.reference[i])
            x = self.getXPosition(self.reference[i])
            y = 30 + round((logmag-minValue)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                logmag = self.logMag(self.reference[i-1])
                prevx = self.getXPosition(self.reference[i-1])
                prevy = 30 + round((logmag - minValue) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                if self.data[m.location].freq > self.fstop or self.data[m.location].freq < self.fstart:
                    continue
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                logmag = self.logMag(self.data[m.location])
                x = self.getXPosition(self.data[m.location])
                y = 30 + round((logmag - minValue) / span * (self.chartHeight - 10))
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)

    def getYPosition(self, d: Datapoint) -> int:
        logMag = self.logMag(d)
        return 30 + round((logMag - self.minValue) / self.span * (self.chartHeight - 10))

    @staticmethod
    def logMag(p: Datapoint) -> float:
        re = p.re
        im = p.im
        re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
        im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
        # Calculate the reflection coefficient
        mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
        return -20 * math.log10(mag)


class QualityFactorChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 35
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.minQ = 0
        self.maxQ = 0
        self.span = 0
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

        self.setMinimumSize(self.chartWidth + 20 + self.leftMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-20-self.leftMargin
        self.chartHeight = a0.size().height()-40
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, 20+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, 20+self.chartHeight, self.leftMargin+self.chartWidth, 20 + self.chartHeight)
        maxQ = 0

        # Make up some sensible scaling here
        if self.fixedValues:
            maxQ = self.maxDisplayValue
            minQ = self.minDisplayValue
        else:
            minQ = 0
            for d in self.data:
                Q = NanoVNASaver.qualifyFactor(d)
                if Q > maxQ:
                    maxQ = Q
        scale = 0
        if maxQ > 0:
            scale = max(scale, math.floor(math.log10(maxQ)))

        self.minQ = minQ
        self.maxQ = math.ceil(maxQ/10**scale) * 10**scale
        self.span = self.maxQ - self.minQ
        step = math.floor(self.span / 10)
        if step == 0:
            step = 1  # Always show at least one step of size 1
        if self.span == 0:
            return  # No data to draw the graph from
        for i in range(self.minQ, self.maxQ, step):
            y = 30 + round((self.maxQ - i) / self.span * (self.chartHeight-10))
            qp.setPen(QtGui.QPen(self.textColor))
            qp.drawText(3, y+3, str(i))
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5, 30, self.leftMargin + self.chartWidth, 30)
        qp.setPen(self.textColor)
        qp.drawText(3, 35, str(self.maxQ))

    def drawValues(self, qp: QtGui.QPainter):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        if self.span == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if self.fixedSpan:
            fstart = self.minFrequency
            fstop = self.maxFrequency
        else:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop
        fspan = fstop-fstart

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(self.textColor)
            qp.drawText(x-20, 20+self.chartHeight+15, Chart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        qp.setPen(pen)
        for i in range(len(self.data)):
            Q = NanoVNASaver.qualifyFactor(self.data[i])

            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((self.maxQ - Q)/ self.span *(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                Q = NanoVNASaver.qualifyFactor(self.data[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth / len(self.data) * (i-1))
                prevy = 30 + round((self.maxQ - Q) / self.span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            Q = NanoVNASaver.qualifyFactor(self.reference[i])
            x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i].freq - fstart)/fspan)
            y = 30 + round((self.maxQ - Q)/self.span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                Q = NanoVNASaver.qualifyFactor(self.reference[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i-1].freq - fstart)/fspan)
                prevy = 30 + round((self.maxQ - Q) / self.span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                Q = NanoVNASaver.qualifyFactor(self.data[m.location])
                x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * m.location)
                y = 30 + round((self.maxQ - Q) / self.span * (self.chartHeight - 10))
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)

    def getXPosition(self, d: Datapoint) -> int:
        span = self.fstop - self.fstart
        return self.leftMargin + 1 + round(self.chartWidth * (d.freq - self.fstart) / span)

    def getYPosition(self, d: Datapoint) -> int:
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        Q = NanoVNASaver.qualifyFactor(d)
        return 30 + round((self.maxQ - Q) / self.span * (self.chartHeight - 10))

    @staticmethod
    def angle(d: Datapoint) -> float:
        re = d.re
        im = d.im
        return -math.degrees(math.atan2(im, re))


class TDRChart(Chart):
    def __init__(self, name):
        super().__init__(name)
        self.tdrWindow = None
        self.leftMargin = 20
        self.rightMargin = 20
        self.lowerMargin = 35
        self.setMinimumSize(250, 250)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)

        width = self.width() - self.leftMargin - self.rightMargin
        height = self.height() - self.lowerMargin

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.height() - self.lowerMargin, self.width() - self.rightMargin,
                    self.height() - self.lowerMargin)
        qp.drawLine(self.leftMargin, 20, self.leftMargin, self.height() - self.lowerMargin + 5)

        ticks = math.floor((self.width() - self.leftMargin)/100)  # Number of ticks does not include the origin

        if len(self.tdrWindow.td) > 0:
            x_step = len(self.tdrWindow.distance_axis) / width
            y_step = np.max(self.tdrWindow.td)*1.1 / height

            for i in range(ticks):
                x = self.leftMargin + round((i + 1) * width / ticks)
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(x, 20, x, height)
                qp.setPen(QtGui.QPen(self.textColor))
                qp.drawText(x - 20, 20 + height,
                            str(round(self.tdrWindow.distance_axis[int((x - self.leftMargin) * x_step) - 1]/2, 1)) + "m")

            qp.setPen(self.sweepColor)
            for i in range(len(self.tdrWindow.distance_axis)):
                qp.drawPoint(self.leftMargin + int(i / x_step), height - int(self.tdrWindow.td[i] / y_step))
            id_max = np.argmax(self.tdrWindow.td)
            max_point = QtCore.QPoint(self.leftMargin + int(id_max / x_step),
                                      height - int(self.tdrWindow.td[id_max] / y_step))
            qp.setPen(self.markers[0].color)
            qp.drawEllipse(max_point, 2, 2)
            qp.setPen(self.textColor)
            qp.drawText(max_point.x() - 10, max_point.y() - 5, str(round(self.tdrWindow.distance_axis[id_max]/2, 2)) + "m")
        qp.end()


class RealImaginaryChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 45
        self.rightMargin = 45
        self.chartWidth = 230
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.span_real = 0
        self.span_imag = 0
        self.max_real = 0
        self.max_imag = 0

        self.maxDisplayReal = 100
        self.maxDisplayImag = 100
        self.minDisplayReal = 0
        self.minDisplayImag = -100

        #
        #  Build the context menu
        #

        self.y_menu.clear()

        self.y_action_automatic = QtWidgets.QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        self.y_action_fixed_span = QtWidgets.QAction("Fixed span")
        self.y_action_fixed_span.setCheckable(True)
        self.y_action_fixed_span.changed.connect(lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        mode_group = QtWidgets.QActionGroup(self)
        mode_group.addAction(self.y_action_automatic)
        mode_group.addAction(self.y_action_fixed_span)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed_span)
        self.y_menu.addSeparator()

        self.action_set_fixed_maximum_real = QtWidgets.QAction("Maximum R (" + str(self.maxDisplayReal) + ")")
        self.action_set_fixed_maximum_real.triggered.connect(self.setMaximumRealValue)

        self.action_set_fixed_minimum_real = QtWidgets.QAction("Minimum R (" + str(self.minDisplayReal) + ")")
        self.action_set_fixed_minimum_real.triggered.connect(self.setMinimumRealValue)

        self.action_set_fixed_maximum_imag = QtWidgets.QAction("Maximum jX (" + str(self.maxDisplayImag) + ")")
        self.action_set_fixed_maximum_imag.triggered.connect(self.setMaximumImagValue)

        self.action_set_fixed_minimum_imag = QtWidgets.QAction("Minimum jX (" + str(self.minDisplayImag) + ")")
        self.action_set_fixed_minimum_imag.triggered.connect(self.setMinimumImagValue)

        self.y_menu.addAction(self.action_set_fixed_maximum_real)
        self.y_menu.addAction(self.action_set_fixed_minimum_real)
        self.y_menu.addSeparator()
        self.y_menu.addAction(self.action_set_fixed_maximum_imag)
        self.y_menu.addAction(self.action_set_fixed_minimum_imag)

        #
        # Set up size policy and palette
        #

        self.setMinimumSize(self.chartWidth + self.leftMargin + self.rightMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-self.leftMargin-self.rightMargin
        self.chartHeight = a0.size().height()-40
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(self.leftMargin + 5, 15, self.name + " (\N{OHM SIGN})")
        qp.drawText(10, 15, "R")
        qp.drawText(self.leftMargin + self.chartWidth + 10, 15, "X")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, 20+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, 20+self.chartHeight, self.leftMargin+self.chartWidth+5, 20 + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if self.fixedSpan:
            fstart = self.minFrequency
            fstop = self.maxFrequency
        else:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop
        fspan = fstop-fstart

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        # Find scaling
        if self.fixedValues:
            min_real = self.minDisplayReal
            max_real = self.maxDisplayReal
            min_imag = self.minDisplayImag
            max_imag = self.maxDisplayImag
        else:
            min_real = 1000
            min_imag = 1000
            max_real = 0
            max_imag = -1000
            for d in self.data:
                re, im = NanoVNASaver.normalize50(d)
                if re > max_real:
                    max_real = re
                if re < min_real:
                    min_real = re
                if im > max_imag:
                    max_imag = im
                if im < min_imag:
                    min_imag = im
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < fstart or d.freq > fstop:
                    continue
                re, im = NanoVNASaver.normalize50(d)
                if re > max_real:
                    max_real = re
                if re < min_real:
                    min_real = re
                if im > max_imag:
                    max_imag = im
                if im < min_imag:
                    min_imag = im

            max_real = max(8, math.ceil(max_real))   # Always have at least 8 numbered horizontal lines
            min_real = max(0, math.floor(min_real))  # Negative real resistance? No.
            max_imag = math.ceil(max_imag)
            min_imag = math.floor(min_imag)

            if max_imag - min_imag < 8:
                missing = 8 - (max_imag - min_imag)
                max_imag += math.ceil(missing/2)
                min_imag -= math.floor(missing/2)

            if 0 > max_imag > -2:
                max_imag = 0
            if 0 < min_imag < 2:
                min_imag = 0

            if (max_imag - min_imag) > 8 and min_imag < 0 < max_imag:
                # We should show a "0" line for the reactive part
                span = max_imag - min_imag
                step_size = span / 8
                if max_imag < step_size:
                    # The 0 line is the first step after the top. Scale accordingly.
                    max_imag = -min_imag/7
                elif -min_imag < step_size:
                    # The 0 line is the last step before the bottom. Scale accordingly.
                    min_imag = -max_imag/7
                else:
                    # Scale max_imag to be a whole factor of min_imag
                    num_min = math.floor(min_imag/step_size * -1)
                    num_max = 8 - num_min
                    max_imag = num_max * (min_imag / num_min) * -1

        self.max_real = max_real
        self.max_imag = max_imag

        span_real = max_real - min_real
        self.span_real = span_real

        span_imag = max_imag - min_imag
        self.span_imag = span_imag

        # We want one horizontal tick per 50 pixels, at most
        horizontal_ticks = math.floor(self.chartHeight/50)

        # TODO: Find a way to always have a line at X=0
        for i in range(horizontal_ticks):
            y = 30 + round(i * (self.chartHeight-10) / horizontal_ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth + 5, y)
            qp.setPen(QtGui.QPen(self.textColor))
            re = max_real - i * span_real / horizontal_ticks
            im = max_imag - i * span_imag / horizontal_ticks
            qp.drawText(3, y + 4, str(round(re, 1)))
            qp.drawText(self.leftMargin + self.chartWidth + 8, y + 4, str(round(im, 1)))

        qp.drawText(3, self.chartHeight + 20, str(round(min_real, 1)))
        qp.drawText(self.leftMargin + self.chartWidth + 8, self.chartHeight + 20, str(round(min_imag, 1)))

        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(self.textColor)
            qp.drawText(x-20, 20+self.chartHeight+15, Chart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        primary_pen = pen
        secondary_pen = QtGui.QPen(self.secondarySweepColor)
        secondary_pen.setWidth(2)
        if len(self.data) > 0:
            c = QtGui.QColor(self.sweepColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 9, 25, 9)
            c = QtGui.QColor(self.secondarySweepColor)
            c.setAlpha(255)
            pen.setColor(c)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.chartWidth, 9, self.leftMargin + self.chartWidth + 5, 9)

        for i in range(len(self.data)):
            re, im = NanoVNASaver.normalize50(self.data[i])
            x = self.getXPosition(self.data[i])
            y_re = 30 + round((max_real - re) / span_real * (self.chartHeight - 10))
            y_im = 30 + round((max_imag - im) / span_imag * (self.chartHeight - 10))
            qp.setPen(primary_pen)
            if re > 0:
                qp.drawPoint(int(x), int(y_re))
            qp.setPen(secondary_pen)
            qp.drawPoint(int(x), int(y_im))
            if self.drawLines and i > 0:
                new_re, new_im = NanoVNASaver.normalize50(self.data[i-1])
                prev_x = self.getXPosition(self.data[i-1])
                prev_y_re = 30 + round((max_real - new_re) / span_real * (self.chartHeight - 10))
                prev_y_im = 30 + round((max_imag - new_im) / span_imag * (self.chartHeight - 10))

                if re > 0 and new_re > 0:
                    line_pen.setColor(self.sweepColor)
                    qp.setPen(line_pen)
                    qp.drawLine(x, y_re, prev_x, prev_y_re)

                line_pen.setColor(self.secondarySweepColor)
                qp.setPen(line_pen)
                qp.drawLine(x, y_im, prev_x, prev_y_im)

        primary_pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        secondary_pen.setColor(self.referenceColor)
        qp.setPen(primary_pen)
        if len(self.reference) > 0:
            c = QtGui.QColor(self.referenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 14, 25, 14)  # Alpha might be low, so we draw twice
            qp.drawLine(self.leftMargin + self.chartWidth, 14, self.leftMargin + self.chartWidth + 5, 14)

        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            re, im = NanoVNASaver.normalize50(self.reference[i])
            x = self.getXPosition(self.reference[i])
            y_re = 30 + round((max_real - re) / span_real * (self.chartHeight - 10))
            y_im = 30 + round((max_imag - im) / span_imag * (self.chartHeight - 10))
            qp.setPen(primary_pen)
            if re > 0:
                qp.drawPoint(int(x), int(y_re))
            qp.setPen(secondary_pen)
            qp.drawPoint(int(x), int(y_im))

            if self.drawLines and i > 0:
                new_re, new_im = NanoVNASaver.normalize50(self.reference[i-1])
                prev_x = self.getXPosition(self.reference[i-1])
                prev_y_re = 30 + round((max_real - new_re) / span_real * (self.chartHeight - 10))
                prev_y_im = 30 + round((max_imag - new_im) / span_imag * (self.chartHeight - 10))

                if re > 0 and new_re > 0:
                    line_pen.setColor(self.referenceColor)
                    qp.setPen(line_pen)
                    qp.drawLine(x, y_re, prev_x, prev_y_re)

                qp.drawLine(x, y_im, prev_x, prev_y_im)

        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                re, im = NanoVNASaver.normalize50(self.data[m.location])
                x = self.getXPosition(self.data[m.location])
                y_re = 30 + round((max_real - re) / span_real * (self.chartHeight - 10))
                y_im = 30 + round((max_imag - im) / span_imag * (self.chartHeight - 10))

                qp.drawLine(int(x), int(y_re) + 3, int(x) - 3, int(y_re) - 3)
                qp.drawLine(int(x), int(y_re) + 3, int(x) + 3, int(y_re) - 3)
                qp.drawLine(int(x) - 3, int(y_re) - 3, int(x) + 3, int(y_re) - 3)

                qp.drawLine(int(x), int(y_im) + 3, int(x) - 3, int(y_im) - 3)
                qp.drawLine(int(x), int(y_im) + 3, int(x) + 3, int(y_im) - 3)
                qp.drawLine(int(x) - 3, int(y_im) - 3, int(x) + 3, int(y_im) - 3)

    def getXPosition(self, d: Datapoint) -> int:
        span = self.fstop - self.fstart
        return self.leftMargin + 1 + round(self.chartWidth * (d.freq - self.fstart) / span)

    def getImYPosition(self, d: Datapoint) -> int:
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        re, im = NanoVNASaver.normalize50(d)
        return 30 + round((self.max_imag - im) / self.span_imag * (self.chartHeight - 10))

    def getReYPosition(self, d: Datapoint) -> int:
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        re, im = NanoVNASaver.normalize50(d)
        return 30 + round((self.max_real - re) / self.span_real * (self.chartHeight - 10))

    def getNearestMarker(self, x, y) -> Marker:
        if len(self.data) == 0:
            return None
        shortest = 10**6
        nearest = None
        for m in self.markers:
            mx, _ = self.getPosition(self.data[m.location])
            myr = self.getReYPosition(self.data[m.location])
            myi = self.getImYPosition(self.data[m.location])
            dx = abs(x - mx)
            dy = min(abs(y - myr), abs(y-myi))
            distance = math.sqrt(dx**2 + dy**2)
            if distance < shortest:
                shortest = distance
                nearest = m
        return nearest

    def setMinimumRealValue(self):
        min_val, selected = QtWidgets.QInputDialog.getInt(self, "Minimum real value",
                                                          "Set minimum real value", value=self.minDisplayReal)
        if not selected:
            return
        self.minDisplayValue = min_val
        if self.fixedValues:
            self.update()

    def setMaximumRealValue(self):
        max_val, selected = QtWidgets.QInputDialog.getInt(self, "Maximum real value",
                                                          "Set maximum real value", value=self.maxDisplayReal)
        if not selected:
            return
        self.maxDisplayValue = max_val
        if self.fixedValues:
            self.update()

    def setMinimumImagValue(self):
        min_val, selected = QtWidgets.QInputDialog.getInt(self, "Minimum imaginary value",
                                                          "Set minimum imaginary value", value=self.minDisplayImag)
        if not selected:
            return
        self.minDisplayValue = min_val
        if self.fixedValues:
            self.update()

    def setMaximumImagValue(self):
        max_val, selected = QtWidgets.QInputDialog.getInt(self, "Maximum imaginary value",
                                                          "Set maximum imaginary value", value=self.maxDisplayImag)
        if not selected:
            return
        self.maxDisplayValue = max_val
        if self.fixedValues:
            self.update()

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText("Start (" + Chart.shortenFrequency(self.minFrequency) + ")")
        self.action_set_fixed_stop.setText("Stop (" + Chart.shortenFrequency(self.maxFrequency) + ")")
        self.action_set_fixed_minimum_real.setText("Minimum R (" + str(self.minDisplayReal) + ")")
        self.action_set_fixed_maximum_real.setText("Maximum R (" + str(self.maxDisplayReal) + ")")
        self.action_set_fixed_minimum_imag.setText("Minimum jX (" + str(self.minDisplayImag) + ")")
        self.action_set_fixed_maximum_imag.setText("Maximum jX (" + str(self.maxDisplayImag) + ")")

        self.menu.exec_(event.globalPos())
