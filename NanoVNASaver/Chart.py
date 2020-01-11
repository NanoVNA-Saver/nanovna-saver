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
from typing import List, Set
import numpy as np
import logging
from scipy import signal

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver.RFTools import Datapoint, RFTools
from NanoVNASaver.SITools import Format, Value
from .Marker import Marker
logger = logging.getLogger(__name__)


class Chart(QtWidgets.QWidget):
    sweepColor = QtCore.Qt.darkYellow
    secondarySweepColor = QtCore.Qt.darkMagenta
    referenceColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.blue)
    referenceColor.setAlpha(64)
    secondaryReferenceColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.blue)
    secondaryReferenceColor.setAlpha(64)
    backgroundColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.white)
    foregroundColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.lightGray)
    textColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.black)
    swrColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.red)
    swrColor.setAlpha(128)
    data: List[Datapoint] = []
    reference: List[Datapoint] = []
    markers: List[Marker] = []
    swrMarkers: Set[float] = set()
    bands = None
    draggedMarker: Marker = None
    name = ""
    sweepTitle = ""
    drawLines = False
    minChartHeight = 200
    minChartWidth = 200
    chartWidth = minChartWidth
    chartHeight = minChartHeight
    lineThickness = 1
    pointSize = 2
    markerSize = 3
    drawMarkerNumbers = False
    markerAtTip = False
    filledMarkers = False
    draggedBox = False
    draggedBoxStart = (0, 0)
    draggedBoxCurrent = (-1, -1)
    moveStartX = -1
    moveStartY = -1

    isPopout = False
    popoutRequested = pyqtSignal(object)

    def __init__(self, name):
        super().__init__()
        self.name = name

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_save_screenshot = QtWidgets.QAction("Save image")
        self.action_save_screenshot.triggered.connect(self.saveScreenshot)
        self.addAction(self.action_save_screenshot)
        self.action_popout = QtWidgets.QAction("Popout chart")
        self.action_popout.triggered.connect(lambda: self.popoutRequested.emit(self))
        self.addAction(self.action_popout)

        self.swrMarkers = set()

    def setSweepColor(self, color : QtGui.QColor):
        self.sweepColor = color
        self.update()

    def setSecondarySweepColor(self, color : QtGui.QColor):
        self.secondarySweepColor = color
        self.update()

    def setReferenceColor(self, color : QtGui.QColor):
        self.referenceColor = color
        self.update()

    def setSecondaryReferenceColor(self, color : QtGui.QColor):
        self.secondaryReferenceColor = color
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

    def setLineThickness(self, thickness):
        self.lineThickness = thickness
        self.update()

    def setPointSize(self, size):
        self.pointSize = size
        self.update()

    def setMarkerSize(self, size):
        self.markerSize = size
        self.update()

    def setSweepTitle(self, title):
        self.sweepTitle = title
        self.update()

    def getActiveMarker(self) -> Marker:
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

    def setDrawLines(self, draw_lines):
        self.drawLines = draw_lines
        self.update()

    def setDrawMarkerNumbers(self, draw_marker_numbers):
        self.drawMarkerNumbers = draw_marker_numbers
        self.update()

    def setMarkerAtTip(self, marker_at_tip):
        self.markerAtTip = marker_at_tip
        self.update()

    def setFilledMarkers(self, filled_markers):
        self.filledMarkers = filled_markers
        self.update()

    @staticmethod
    def shortenFrequency(frequency: int) -> str:
        if frequency < 50000:
            return str(frequency)
        elif frequency < 5000000:
            return str(round(frequency / 1000)) + "k"
        elif frequency < 50000000:
            return str(round(frequency / 1000000, 2)) + "M"
        else:
            return str(round(frequency / 1000000, 1)) + "M"

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.RightButton:
            event.ignore()
            return
        elif event.buttons() == QtCore.Qt.MiddleButton:
            # Drag event
            event.accept()
            self.moveStartX = event.x()
            self.moveStartY = event.y()
            return
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.draggedMarker = self.getNearestMarker(event.x(), event.y())
        elif event.modifiers() == QtCore.Qt.ControlModifier:
            event.accept()
            self.draggedBox = True
            self.draggedBoxStart = (event.x(), event.y())
            return
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.draggedMarker = None
        if self.draggedBox:
            self.zoomTo(self.draggedBoxStart[0], self.draggedBoxStart[1], a0.x(), a0.y())
            self.draggedBox = False
            self.draggedBoxCurrent = (-1, -1)
            self.draggedBoxStart = (0, 0)
            self.update()

    def zoomTo(self, x1, y1, x2, y2):
        pass

    def saveScreenshot(self):
        logger.info("Saving %s to file...", self.name)
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(parent=self, caption="Save image",
                                                            filter="PNG (*.png);;All files (*.*)")

        logger.debug("Filename: %s", filename)
        if filename != "":
            self.grab().save(filename)

    def copy(self):
        new_chart = self.__class__(self.name)
        new_chart.data = self.data
        new_chart.reference = self.reference
        new_chart.sweepColor = self.sweepColor
        new_chart.secondarySweepColor = self.secondarySweepColor
        new_chart.referenceColor = self.referenceColor
        new_chart.secondaryReferenceColor = self.secondaryReferenceColor
        new_chart.setBackgroundColor(self.backgroundColor)
        new_chart.textColor = self.textColor
        new_chart.foregroundColor = self.foregroundColor
        new_chart.swrColor = self.swrColor
        new_chart.markers = self.markers
        new_chart.swrMarkers = self.swrMarkers
        new_chart.bands = self.bands
        new_chart.drawLines = self.drawLines
        new_chart.markerSize = self.markerSize
        new_chart.drawMarkerNumbers = self.drawMarkerNumbers
        new_chart.filledMarkers = self.filledMarkers
        new_chart.markerAtTip = self.markerAtTip
        new_chart.resize(self.width(), self.height())
        new_chart.setPointSize(self.pointSize)
        new_chart.setLineThickness(self.lineThickness)
        return new_chart

    def addSWRMarker(self, swr: float):
        self.swrMarkers.add(swr)
        self.update()

    def removeSWRMarker(self, swr: float):
        try:
            self.swrMarkers.remove(swr)
        except KeyError:
            logger.debug("KeyError from %s", self.name)
            return
        finally:
            self.update()

    def clearSWRMarkers(self):
        self.swrMarkers.clear()
        self.update()

    def setSWRColor(self, color: QtGui.QColor):
        self.swrColor = color
        self.update()

    def drawMarker(self, x, y, qp: QtGui.QPainter, color: QtGui.QColor, number=0):
        if self.markerAtTip:
            y -= self.markerSize
        pen = QtGui.QPen(color)
        qp.setPen(pen)
        qpp = QtGui.QPainterPath()
        qpp.moveTo(x, y + self.markerSize)
        qpp.lineTo(x - self.markerSize, y - self.markerSize)
        qpp.lineTo(x + self.markerSize, y - self.markerSize)
        qpp.lineTo(x, y + self.markerSize)

        if self.filledMarkers:
            qp.fillPath(qpp, color)
        else:
            qp.drawPath(qpp)

        if self.drawMarkerNumbers:
            number_x = x - 3
            number_y = y - self.markerSize - 3
            qp.drawText(number_x, number_y, str(number))

    def drawTitle(self, qp: QtGui.QPainter, position: QtCore.QPoint = None):
        if self.sweepTitle != "":
            qp.setPen(self.textColor)
            if position is None:
                qf = QtGui.QFontMetricsF(self.font())
                width = qf.boundingRect(self.sweepTitle).width()
                position = QtCore.QPointF(self.width()/2 - width/2, 15)
            qp.drawText(position, self.sweepTitle)


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
        
        self.x_menu.addSeparator()
        frequency_mode_group = QtWidgets.QActionGroup(self.x_menu)
        self.action_set_linear_x = QtWidgets.QAction("Linear")
        self.action_set_linear_x.setCheckable(True)
        self.action_set_logarithmic_x = QtWidgets.QAction("Logarithmic")
        self.action_set_logarithmic_x.setCheckable(True)
        frequency_mode_group.addAction(self.action_set_linear_x)
        frequency_mode_group.addAction(self.action_set_logarithmic_x)
        self.action_set_linear_x.triggered.connect(lambda: self.setLogarithmicX(False))
        self.action_set_logarithmic_x.triggered.connect(lambda: self.setLogarithmicX(True))
        self.action_set_linear_x.setChecked(True)
        self.x_menu.addAction(self.action_set_linear_x)
        self.x_menu.addAction(self.action_set_logarithmic_x)

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
        self.menu.addSeparator()
        self.menu.addAction(self.action_save_screenshot)
        self.action_popout = QtWidgets.QAction("Popout chart")
        self.action_popout.triggered.connect(lambda: self.popoutRequested.emit(self))
        self.menu.addAction(self.action_popout)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText("Start (" + Chart.shortenFrequency(self.minFrequency) + ")")
        self.action_set_fixed_stop.setText("Stop (" + Chart.shortenFrequency(self.maxFrequency) + ")")
        self.action_set_fixed_minimum.setText("Minimum (" + str(self.minDisplayValue) + ")")
        self.action_set_fixed_maximum.setText("Maximum (" + str(self.maxDisplayValue) + ")")

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
        min_freq_str, selected = QtWidgets.QInputDialog.getText(self, "Start frequency",
                                                                "Set start frequency", text=str(self.minFrequency))
        if not selected:
            return
        min_freq = RFTools.parseFrequency(min_freq_str)
        if min_freq > 0 and not (self.fixedSpan and min_freq >= self.maxFrequency):
            self.minFrequency = min_freq
        if self.fixedSpan:
            self.update()

    def setMaximumFrequency(self):
        max_freq_str, selected = QtWidgets.QInputDialog.getText(self, "Stop frequency",
                                                                "Set stop frequency", text=str(self.maxFrequency))
        if not selected:
            return
        max_freq = RFTools.parseFrequency(max_freq_str)
        if max_freq > 0 and not (self.fixedSpan and max_freq <= self.minFrequency):
            self.maxFrequency = max_freq
        if self.fixedSpan:
            self.update()

    def setMinimumValue(self):
        min_val, selected = QtWidgets.QInputDialog.getDouble(self, "Minimum value",
                                                             "Set minimum value", value=self.minDisplayValue,
                                                             decimals=3)
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayValue):
            self.minDisplayValue = min_val
        if self.fixedValues:
            self.update()

    def setMaximumValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(self, "Maximum value",
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
                return self.leftMargin +\
                       round(self.chartWidth * (math.log(d.freq) - math.log(self.fstart)) / span)
            else:
                return self.leftMargin + round(self.chartWidth * (d.freq - self.fstart) / span)
        else:
            return math.floor(self.width()/2)

    def frequencyAtPosition(self, x, limit=True) -> int:
        """
        Calculates the frequency at a given X-position
        :param limit: Determines whether frequencies outside the currently displayed span can be returned.
        :param x: The X position to calculate for.
        :return: The frequency at the given position, if one exists, or -1 otherwise.  If limit is True, and the value
                 is before or after the chart, returns minimum or maximum frequencies.
        """
        if self.fstop - self.fstart > 0:
            absx = x - self.leftMargin
            if limit and absx < 0:
                return self.fstart
            elif limit and absx > self.chartWidth:
                return self.fstop
            elif self.logarithmicX:
                span = math.log(self.fstop) - math.log(self.fstart)
                step = span/self.chartWidth
                return round(math.exp(math.log(self.fstart) + absx * step))
            else:
                span = self.fstop - self.fstart
                step = span/self.chartWidth
                return round(self.fstart + absx * step)
        else:
            return -1

    def valueAtPosition(self, y) -> List[float]:
        """
        Returns the chart-specific value(s) at the specified Y-position
        :param y: The Y position to calculate for.
        :return: A list of the values at the Y-position, either containing a single value, or the two values for the
                 chart from left to right Y-axis.  If no value can be found, returns the empty list.  If the frequency
                 is above or below the chart, returns maximum or minimum values.
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

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
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
                            self.leftMargin + self.chartWidth + dx, self.topMargin + self.chartHeight + dy)

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
        else:
            a0.accept()
            m = self.getActiveMarker()
            if m is not None:
                m.setFrequency(str(f))
                m.frequencyInput.setText(str(f))
        return

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-self.rightMargin-self.leftMargin
        self.chartHeight = a0.size().height() - self.bottomMargin - self.topMargin
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        if len(self.data) > 0\
                and (self.data[0].freq > self.fstop or self.data[len(self.data)-1].freq < self.fstart) \
                and (len(self.reference) == 0 or self.reference[0].freq > self.fstop or
                     self.reference[len(self.reference)-1].freq < self.fstart):
            # Data outside frequency range
            qp.setBackgroundMode(QtCore.Qt.OpaqueMode)
            qp.setBackground(self.backgroundColor)
            qp.setPen(self.textColor)
            qp.drawText(self.leftMargin + self.chartWidth/2 - 70, self.topMargin + self.chartHeight/2 - 20,
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
        qp.drawText(self.leftMargin - 20, self.topMargin + self.chartHeight + 15, Chart.shortenFrequency(self.fstart))
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
            qp.drawText(x - 20, self.topMargin + self.chartHeight + 15, Chart.shortenFrequency(freq))

    def drawBands(self, qp, fstart, fstop):
        qp.setBrush(self.bands.color)
        qp.setPen(QtGui.QColor(128, 128, 128, 0))  # Don't outline the bands
        for (name, start, end) in self.bands.bands:
            if fstart < start < fstop and fstart < end < fstop:
                # The band is entirely within the chart
                x_start = self.getXPosition(Datapoint(start, 0, 0))
                x_end = self.getXPosition(Datapoint(end, 0, 0))
                qp.drawRect(x_start, self.topMargin, x_end - x_start, self.chartHeight)
            elif fstart < start < fstop:
                # Only the start of the band is within the chart
                x_start = self.getXPosition(Datapoint(start, 0, 0))
                qp.drawRect(x_start, self.topMargin, self.leftMargin + self.chartWidth - x_start, self.chartHeight)
            elif fstart < end < fstop:
                # Only the end of the band is within the chart
                x_end = self.getXPosition(Datapoint(end, 0, 0))
                qp.drawRect(self.leftMargin + 1, self.topMargin, x_end - (self.leftMargin + 1), self.chartHeight)
            elif start < fstart < fstop < end:
                # All the chart is in a band, we won't show it(?)
                pass

    def drawData(self, qp: QtGui.QPainter, data: List[Datapoint], color: QtGui.QColor, y_function=None):
        if y_function is None:
            y_function = self.getYPosition
        pen = QtGui.QPen(color)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.lineThickness)
        qp.setPen(pen)
        for i in range(len(data)):
            x = self.getXPosition(data[i])
            y = y_function(data[i])
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.getXPosition(data[i - 1])
                prevy = y_function(data[i - 1])
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
        return self.leftMargin <= x <= self.leftMargin + self.chartWidth and \
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
        else:
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
                m.frequencyInput.keyPressEvent(QtGui.QKeyEvent(a0.type(), QtCore.Qt.Key_Down, a0.modifiers()))
            elif a0.key() == QtCore.Qt.Key_Up or a0.key() == QtCore.Qt.Key_Right:
                m.frequencyInput.keyPressEvent(QtGui.QKeyEvent(a0.type(), QtCore.Qt.Key_Up, a0.modifiers()))
        else:
            super().keyPressEvent(a0)


class SquareChart(Chart):
    def __init__(self, name):
        super().__init__(name)
        sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(sizepolicy)
        self.chartWidth = self.width()-40
        self.chartHeight = self.height()-40

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if not self.isPopout:
            self.setFixedWidth(a0.size().height())
            self.chartWidth = a0.size().height()-40
            self.chartHeight = a0.size().height()-40
        else:
            min_dimension = min(a0.size().height(), a0.size().width())
            self.chartWidth = self.chartHeight = min_dimension - 40
        self.update()


class PhaseChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 40
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.minAngle = 0
        self.maxAngle = 0
        self.span = 0
        self.unwrap = False

        self.unwrappedData = []
        self.unwrappedReference = []

        self.minDisplayValue = -180
        self.maxDisplayValue = 180

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.y_menu.addSeparator()
        self.action_unwrap = QtWidgets.QAction("Unwrap")
        self.action_unwrap.setCheckable(True)
        self.action_unwrap.triggered.connect(lambda: self.setUnwrap(self.action_unwrap.isChecked()))
        self.y_menu.addAction(self.action_unwrap)

    def copy(self):
        new_chart: PhaseChart = super().copy()
        new_chart.setUnwrap(self.unwrap)
        new_chart.action_unwrap.setChecked(self.unwrap)
        return new_chart

    def setUnwrap(self, unwrap: bool):
        self.unwrap = unwrap
        self.update()

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)

        if self.unwrap:
            rawData = []
            for d in self.data:
                rawData.append(d.phase)

            rawReference = []
            for d in self.reference:
                rawReference.append(d.phase)

            self.unwrappedData = np.degrees(np.unwrap(rawData))
            self.unwrappedReference = np.degrees(np.unwrap(rawReference))

        if self.fixedValues:
            minAngle = self.minDisplayValue
            maxAngle = self.maxDisplayValue
        elif self.unwrap and self.data:
            minAngle = math.floor(np.min(self.unwrappedData))
            maxAngle = math.ceil(np.max(self.unwrappedData))
        elif self.unwrap and self.reference:
            minAngle = math.floor(np.min(self.unwrappedReference))
            maxAngle = math.ceil(np.max(self.unwrappedReference))
        else:
            minAngle = -180
            maxAngle = 180

        span = maxAngle - minAngle
        if span == 0:
            span = 0.01
        self.minAngle = minAngle
        self.maxAngle = maxAngle
        self.span = span

        tickcount = math.floor(self.chartHeight / 60)

        for i in range(tickcount):
            angle = minAngle + span * i / tickcount
            y = self.topMargin + round((self.maxAngle - angle) / self.span * self.chartHeight)
            if angle != minAngle and angle != maxAngle:
                qp.setPen(QtGui.QPen(self.textColor))
                if angle != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(angle)))))
                    if digits == 0:
                        anglestr = str(round(angle))
                    else:
                        anglestr = str(round(angle, digits))
                else:
                    anglestr = "0"
                qp.drawText(3, y + 3, anglestr + "°")
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5, self.topMargin, self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 5, str(maxAngle) + "°")
        qp.drawText(3, self.chartHeight + self.topMargin, str(minAngle) + "°")

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

        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        if self.unwrap:
            if d in self.data:
                angle = self.unwrappedData[self.data.index(d)]
            elif d in self.reference:
                angle = self.unwrappedReference[self.reference.index(d)]
            else:
                angle = math.degrees(d.phase)
        else:
            angle = math.degrees(d.phase)
        return self.topMargin + round((self.maxAngle - angle) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxAngle)
        return [val]


class VSWRChart(FrequencyChart):
    logarithmicY = False
    maxVSWR = 3
    span = 2

    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.maxDisplayValue = 25
        self.minDisplayValue = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.y_menu.addSeparator()
        self.y_log_lin_group = QtWidgets.QActionGroup(self.y_menu)
        self.y_action_linear = QtWidgets.QAction("Linear")
        self.y_action_linear.setCheckable(True)
        self.y_action_linear.setChecked(True)
        self.y_action_logarithmic = QtWidgets.QAction("Logarithmic")
        self.y_action_logarithmic.setCheckable(True)
        self.y_action_linear.triggered.connect(lambda: self.setLogarithmicY(False))
        self.y_action_logarithmic.triggered.connect(lambda: self.setLogarithmicY(True))
        self.y_log_lin_group.addAction(self.y_action_linear)
        self.y_log_lin_group.addAction(self.y_action_logarithmic)
        self.y_menu.addAction(self.y_action_linear)
        self.y_menu.addAction(self.y_action_logarithmic)

    def setLogarithmicY(self, logarithmic: bool):
        self.logarithmicY = logarithmic
        self.update()

    def copy(self):
        new_chart: VSWRChart = super().copy()
        new_chart.logarithmicY = self.logarithmicY
        return new_chart

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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
                vswr = d.vswr
                if vswr > maxVSWR:
                    maxVSWR = vswr
            maxVSWR = min(self.maxDisplayValue, math.ceil(maxVSWR))
        self.maxVSWR = maxVSWR
        span = maxVSWR-minVSWR
        if span == 0:
            span = 0.01
        self.span = span

        target_ticks = math.floor(self.chartHeight / 60)

        if self.logarithmicY:
            for i in range(target_ticks):
                y = int(self.topMargin + (i / target_ticks) * self.chartHeight)
                vswr = self.valueAtPosition(y)[0]
                qp.setPen(self.textColor)
                if vswr != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(vswr)))))
                    if digits == 0:
                        vswrstr = str(round(vswr))
                    else:
                        vswrstr = str(round(vswr, digits))
                    qp.drawText(3, y+3, vswrstr)
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            qp.drawLine(self.leftMargin - 5, self.topMargin + self.chartHeight,
                        self.leftMargin + self.chartWidth, self.topMargin + self.chartHeight)
            qp.setPen(self.textColor)
            digits = max(0, min(2, math.floor(3 - math.log10(abs(minVSWR)))))
            if digits == 0:
                vswrstr = str(round(minVSWR))
            else:
                vswrstr = str(round(minVSWR, digits))
            qp.drawText(3, self.topMargin + self.chartHeight, vswrstr)
        else:
            for i in range(target_ticks):
                vswr = minVSWR + i * self.span/target_ticks
                y = self.getYPositionFromValue(vswr)
                qp.setPen(self.textColor)
                if vswr != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(vswr)))))
                    if digits == 0:
                        vswrstr = str(round(vswr))
                    else:
                        vswrstr = str(round(vswr, digits))
                    qp.drawText(3, y+3, vswrstr)
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            qp.drawLine(self.leftMargin - 5, self.topMargin, self.leftMargin + self.chartWidth, self.topMargin)
            qp.setPen(self.textColor)
            digits = max(0, min(2, math.floor(3 - math.log10(abs(maxVSWR)))))
            if digits == 0:
                vswrstr = str(round(maxVSWR))
            else:
                vswrstr = str(round(maxVSWR, digits))
            qp.drawText(3, 35, vswrstr)

        self.drawFrequencyTicks(qp)

        qp.setPen(self.swrColor)
        for vswr in self.swrMarkers:
            y = self.getYPositionFromValue(vswr)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.chartWidth, y)
            qp.drawText(self.leftMargin + 3, y - 1, str(vswr))

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPositionFromValue(self, vswr) -> int:
        if self.logarithmicY:
            min_val = self.maxVSWR - self.span
            if self.maxVSWR > 0 and min_val > 0 and vswr > 0:
                span = math.log(self.maxVSWR) - math.log(min_val)
            else:
                return -1
            return self.topMargin + round((math.log(self.maxVSWR) - math.log(vswr)) / span * self.chartHeight)
        else:
            return self.topMargin + round((self.maxVSWR - vswr) / self.span * self.chartHeight)

    def getYPosition(self, d: Datapoint) -> int:
        return self.getYPositionFromValue(d.vswr)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        if self.logarithmicY:
            min_val = self.maxVSWR - self.span
            if self.maxVSWR > 0 and min_val > 0:
                span = math.log(self.maxVSWR) - math.log(min_val)
                step = span / self.chartHeight
                val = math.exp(math.log(self.maxVSWR) - absy * step)
            else:
                val = -1
        else:
            val = -1 * ((absy / self.chartHeight * self.span) - self.maxVSWR)
        return [val]

    def resetDisplayLimits(self):
        self.maxDisplayValue = 25
        self.logarithmicY = False
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

        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.getXPosition(self.data[i])
            y = self.height()/2 + self.data[i].im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.getXPosition(self.data[i-1])
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
            x = self.getXPosition(self.reference[i])
            y = self.height()/2 + data.im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.getXPosition(self.reference[i-1])
                prevy = self.height() / 2 + self.reference[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1 and m.location < len(self.data):
                x = self.getXPosition(self.data[m.location])
                y = self.height() / 2 + self.data[m.location].im * -1 * self.chartHeight / 2
                self.drawMarker(x, y, qp, m.color, self.markers.index(m)+1)

    def getXPosition(self, d: Datapoint) -> int:
        return self.width()/2 + d.re * self.chartWidth/2

    def getYPosition(self, d: Datapoint) -> int:
        return self.height()/2 + d.im * -1 * self.chartHeight/2

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.buttons() == QtCore.Qt.RightButton:
            a0.ignore()
            return
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
        m = self.getActiveMarker()
        if m is not None:
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

        qp.drawEllipse(QtCore.QPoint(centerX + int(self.chartWidth/4), centerY),
                       int(self.chartWidth/4), int(self.chartHeight/4))  # Re(Z) = 1
        qp.drawEllipse(QtCore.QPoint(centerX + int(2/3*self.chartWidth/2), centerY),
                       int(self.chartWidth/6), int(self.chartHeight/6))  # Re(Z) = 2
        qp.drawEllipse(QtCore.QPoint(centerX + int(3 / 4 * self.chartWidth / 2), centerY),
                       int(self.chartWidth / 8), int(self.chartHeight / 8))  # Re(Z) = 3
        qp.drawEllipse(QtCore.QPoint(centerX + int(5 / 6 * self.chartWidth / 2), centerY),
                       int(self.chartWidth / 12), int(self.chartHeight / 12))  # Re(Z) = 5

        qp.drawEllipse(QtCore.QPoint(centerX + int(1 / 3 * self.chartWidth / 2), centerY),
                       int(self.chartWidth / 3), int(self.chartHeight / 3))  # Re(Z) = 0.5
        qp.drawEllipse(QtCore.QPoint(centerX + int(1 / 6 * self.chartWidth / 2), centerY),
                       int(self.chartWidth / 2.4), int(self.chartHeight / 2.4))  # Re(Z) = 0.2

        qp.drawArc(centerX + int(3/8*self.chartWidth), centerY, int(self.chartWidth/4),
                   int(self.chartWidth/4), 90*16, 152*16)  # Im(Z) = -5
        qp.drawArc(centerX + int(3/8*self.chartWidth), centerY, int(self.chartWidth/4),
                   -int(self.chartWidth/4), -90 * 16, -152 * 16)  # Im(Z) = 5
        qp.drawArc(centerX + int(self.chartWidth/4), centerY, int(self.chartWidth/2),
                   int(self.chartHeight/2), 90*16, 127*16)  # Im(Z) = -2
        qp.drawArc(centerX + int(self.chartWidth/4), centerY, int(self.chartWidth/2),
                   -int(self.chartHeight/2), -90*16, -127*16)  # Im(Z) = 2
        qp.drawArc(centerX, centerY, self.chartWidth, self.chartHeight, 90*16, 90*16)  # Im(Z) = -1
        qp.drawArc(centerX, centerY, self.chartWidth, -self.chartHeight, -90 * 16, -90 * 16)  # Im(Z) = 1
        qp.drawArc(centerX - int(self.chartWidth/2), centerY,
                   self.chartWidth*2, self.chartHeight*2, int(99.5*16), int(43.5*16))  # Im(Z) = -0.5
        qp.drawArc(centerX - int(self.chartWidth/2), centerY,
                   self.chartWidth*2, -self.chartHeight*2, int(-99.5 * 16), int(-43.5 * 16))  # Im(Z) = 0.5
        qp.drawArc(centerX - self.chartWidth*2, centerY,
                   self.chartWidth*5, self.chartHeight*5, int(93.85*16), int(18.85*16))  # Im(Z) = -0.2
        qp.drawArc(centerX - self.chartWidth*2, centerY,
                   self.chartWidth*5, -self.chartHeight*5, int(-93.85 * 16), int(-18.85 * 16))  # Im(Z) = 0.2

        self.drawTitle(qp)

        qp.setPen(self.swrColor)
        for swr in self.swrMarkers:
            if swr <= 1:
                continue
            gamma = (swr - 1)/(swr + 1)
            r = round(gamma * self.chartWidth/2)
            qp.drawEllipse(QtCore.QPoint(centerX, centerY), r, r)
            qp.drawText(QtCore.QRect(centerX - 50, centerY - 4 + r, 100, 20), QtCore.Qt.AlignCenter, str(swr))

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.getXPosition(self.data[i])
            y = int(self.height()/2 + self.data[i].im * -1 * self.chartHeight/2)
            qp.drawPoint(x, y)
            if self.drawLines and i > 0:
                prevx = self.getXPosition(self.data[i-1])
                prevy = int(self.height() / 2 + self.data[i-1].im * -1 * self.chartHeight / 2)
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
            x = self.getXPosition(data)
            y = int(self.height()/2 + data.im * -1 * self.chartHeight/2)
            qp.drawPoint(x, y)
            if self.drawLines and i > 0:
                prevx = self.getXPosition(self.reference[i-1])
                prevy = int(self.height() / 2 + self.reference[i-1].im * -1 * self.chartHeight / 2)
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                x = self.getXPosition(self.data[m.location])
                y = self.height() / 2 + self.data[m.location].im * -1 * self.chartHeight / 2
                self.drawMarker(x, y, qp, m.color, self.markers.index(m)+1)

    def getXPosition(self, d: Datapoint) -> int:
        return int(self.width()/2 + d.re * self.chartWidth/2)

    def getYPosition(self, d: Datapoint) -> int:
        return int(self.height()/2 + d.im * -1 * self.chartHeight/2)

    def heightForWidth(self, a0: int) -> int:
        return a0

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.buttons() == QtCore.Qt.RightButton:
            a0.ignore()
            return
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
        m = self.getActiveMarker()
        if m is not None:
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

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.isInverted = False

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name + " (dB)")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 100
            maxValue = -100
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
        if span == 0:
            span = 0.01
        self.span = span

        if self.span >= 50:
            # Ticks per 10dB step
            tick_count = math.floor(self.span/10)
            first_tick = math.ceil(self.minValue/10) * 10
            tick_step = 10
            if first_tick == minValue:
                first_tick += 10
        elif self.span >= 20:
            # 5 dB ticks
            tick_count = math.floor(self.span/5)
            first_tick = math.ceil(self.minValue/5) * 5
            tick_step = 5
            if first_tick == minValue:
                first_tick += 5
        elif self.span >= 10:
            # 2 dB ticks
            tick_count = math.floor(self.span/2)
            first_tick = math.ceil(self.minValue/2) * 2
            tick_step = 2
            if first_tick == minValue:
                first_tick += 2
        elif self.span >= 5:
            # 1dB ticks
            tick_count = math.floor(self.span)
            first_tick = math.ceil(minValue)
            tick_step = 1
            if first_tick == minValue:
                first_tick += 1
        elif self.span >= 2:
            # .5 dB ticks
            tick_count = math.floor(self.span*2)
            first_tick = math.ceil(minValue*2) / 2
            tick_step = .5
            if first_tick == minValue:
                first_tick += .5
        else:
            # .1 dB ticks
            tick_count = math.floor(self.span*10)
            first_tick = math.ceil(minValue*10) / 10
            tick_step = .1
            if first_tick == minValue:
                first_tick += .1

        for i in range(tick_count):
            db = first_tick + i * tick_step
            y = self.topMargin + round((maxValue - db)/span*self.chartHeight)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            if db > minValue and db != maxValue:
                qp.setPen(QtGui.QPen(self.textColor))
                if tick_step < 1:
                    dbstr = str(round(db, 1))
                else:
                    dbstr = str(db)
                qp.drawText(3, y + 4, dbstr)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        qp.setPen(self.swrColor)
        for vswr in self.swrMarkers:
            if vswr <= 1:
                continue
            logMag = 20 * math.log10((vswr-1)/(vswr+1))
            if self.isInverted:
                logMag = logMag * -1
            y = self.topMargin + round((self.maxValue - logMag) / self.span * self.chartHeight)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.chartWidth, y)
            qp.drawText(self.leftMargin + 3, y - 1, "VSWR: " + str(vswr))

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        logMag = self.logMag(d)
        return self.topMargin + round((self.maxValue - logMag) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val]

    def logMag(self, p: Datapoint) -> float:
        if self.isInverted:
            return -p.gain
        else:
            return p.gain

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        return new_chart


class SParameterChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = -1
        self.maxDisplayValue = 1
        self.fixedValues = True

        self.y_action_automatic.setChecked(False)
        self.y_action_fixed_span.setChecked(True)

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.isInverted = False

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(int(round(self.chartWidth / 2)) - 20, 15, self.name + "")
        qp.drawText(10, 15, "Real")
        qp.drawText(self.leftMargin + self.chartWidth - 15, 15, "Imag")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = -1
            maxValue = 1
            self.maxValue = maxValue
            self.minValue = minValue
            # for d in self.data:
            #     val = d.re
            #     if val > maxValue:
            #         maxValue = val
            #     if val < minValue:
            #         minValue = val
            # for d in self.reference:  # Also check min/max for the reference sweep
            #     if d.freq < self.fstart or d.freq > self.fstop:
            #         continue
            #     logmag = self.logMag(d)
            #     if logmag > maxValue:
            #         maxValue = logmag
            #     if logmag < minValue:
            #         minValue = logmag

            # minValue = 10*math.floor(minValue/10)
            # self.minValue = minValue
            # maxValue = 10*math.ceil(maxValue/10)
            # self.maxValue = maxValue

        span = maxValue-minValue
        if span == 0:
            span = 0.01
        self.span = span

        tick_count = math.floor(self.chartHeight / 60)
        tick_step = self.span / tick_count

        for i in range(tick_count):
            val = minValue + i * tick_step
            y = self.topMargin + round((maxValue - val)/span*self.chartHeight)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            if val > minValue and val != maxValue:
                qp.setPen(QtGui.QPen(self.textColor))
                qp.drawText(3, y + 4, str(round(val, 2)))

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor, self.getReYPosition)
        self.drawData(qp, self.reference, self.referenceColor, self.getReYPosition)
        self.drawData(qp, self.data, self.secondarySweepColor, self.getImYPosition)
        self.drawData(qp, self.reference, self.secondaryReferenceColor, self.getImYPosition)
        self.drawMarkers(qp, y_function=self.getReYPosition)
        self.drawMarkers(qp, y_function=self.getImYPosition)

    def getYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.re) / self.span * self.chartHeight)

    def getReYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.re) / self.span * self.chartHeight)

    def getImYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.im) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val]

    def logMag(self, p: Datapoint) -> float:
        if self.isInverted:
            return -p.gain
        else:
            return p.gain

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        return new_chart


class CombinedLogMagChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = -80
        self.maxDisplayValue = 10

        self.data11: List[Datapoint] = []
        self.data21: List[Datapoint] = []

        self.reference11: List[Datapoint] = []
        self.reference21: List[Datapoint] = []

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.isInverted = False

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def setCombinedData(self, data11, data21):
        self.data11 = data11
        self.data21 = data21
        self.update()

    def setCombinedReference(self, data11, data21):
        self.reference11 = data11
        self.reference21 = data21
        self.update()

    def resetReference(self):
        self.reference11 = []
        self.reference21 = []
        self.update()

    def resetDisplayLimits(self):
        self.reference11 = []
        self.reference21 = []
        self.update()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(int(round(self.chartWidth / 2)) - 20, 15, self.name + " (dB)")
        qp.drawText(10, 15, "S11")
        qp.drawText(self.leftMargin + self.chartWidth - 8, 15, "S21")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data11) == 0 and len(self.reference11) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if not self.fixedSpan:
            if len(self.data11) > 0:
                fstart = self.data11[0].freq
                fstop = self.data11[len(self.data11)-1].freq
            else:
                fstart = self.reference11[0].freq
                fstop = self.reference11[len(self.reference11) - 1].freq
            self.fstart = fstart
            self.fstop = fstop
        else:
            fstart = self.fstart = self.minFrequency
            fstop = self.fstop = self.maxFrequency

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 100
            maxValue = 0
            for d in self.data11:
                logmag = self.logMag(d)
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag
            for d in self.data21:
                logmag = self.logMag(d)
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag

            for d in self.reference11:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                logmag = self.logMag(d)
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag
            for d in self.reference21:  # Also check min/max for the reference sweep
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
        if span == 0:
            span = 0.01
        self.span = span

        if self.span >= 50:
            # Ticks per 10dB step
            tick_count = math.floor(self.span/10)
            first_tick = math.ceil(self.minValue/10) * 10
            tick_step = 10
            if first_tick == minValue:
                first_tick += 10
        elif self.span >= 20:
            # 5 dB ticks
            tick_count = math.floor(self.span/5)
            first_tick = math.ceil(self.minValue/5) * 5
            tick_step = 5
            if first_tick == minValue:
                first_tick += 5
        elif self.span >= 10:
            # 2 dB ticks
            tick_count = math.floor(self.span/2)
            first_tick = math.ceil(self.minValue/2) * 2
            tick_step = 2
            if first_tick == minValue:
                first_tick += 2
        elif self.span >= 5:
            # 1dB ticks
            tick_count = math.floor(self.span)
            first_tick = math.ceil(minValue)
            tick_step = 1
            if first_tick == minValue:
                first_tick += 1
        elif self.span >= 2:
            # .5 dB ticks
            tick_count = math.floor(self.span*2)
            first_tick = math.ceil(minValue*2) / 2
            tick_step = .5
            if first_tick == minValue:
                first_tick += .5
        else:
            # .1 dB ticks
            tick_count = math.floor(self.span*10)
            first_tick = math.ceil(minValue*10) / 10
            tick_step = .1
            if first_tick == minValue:
                first_tick += .1

        for i in range(tick_count):
            db = first_tick + i * tick_step
            y = self.topMargin + round((maxValue - db)/span*self.chartHeight)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            if db > minValue and db != maxValue:
                qp.setPen(QtGui.QPen(self.textColor))
                if tick_step < 1:
                    dbstr = str(round(db, 1))
                else:
                    dbstr = str(db)
                qp.drawText(3, y + 4, dbstr)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        qp.setPen(self.swrColor)
        for vswr in self.swrMarkers:
            if vswr <= 1:
                continue
            logMag = 20 * math.log10((vswr-1)/(vswr+1))
            if self.isInverted:
                logMag = logMag * -1
            y = self.topMargin + round((self.maxValue - logMag) / self.span * self.chartHeight)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.chartWidth, y)
            qp.drawText(self.leftMargin + 3, y - 1, "VSWR: " + str(vswr))

        if len(self.data11) > 0:
            c = QtGui.QColor(self.sweepColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 9, 38, 9)
            c = QtGui.QColor(self.secondarySweepColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.chartWidth - 20, 9, self.leftMargin + self.chartWidth - 15, 9)

        if len(self.reference11) > 0:
            c = QtGui.QColor(self.referenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 14, 38, 14)
            c = QtGui.QColor(self.secondaryReferenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.chartWidth - 20, 14, self.leftMargin + self.chartWidth - 15, 14)

        self.drawData(qp, self.data11, self.sweepColor)
        self.drawData(qp, self.data21, self.secondarySweepColor)
        self.drawData(qp, self.reference11, self.referenceColor)
        self.drawData(qp, self.reference21, self.secondaryReferenceColor)
        self.drawMarkers(qp, data=self.data11)
        self.drawMarkers(qp, data=self.data21)

    def getYPosition(self, d: Datapoint) -> int:
        logMag = self.logMag(d)
        return self.topMargin + round((self.maxValue - logMag) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val]

    def logMag(self, p: Datapoint) -> float:
        if self.isInverted:
            return -p.gain
        else:
            return p.gain

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        new_chart.data11 = self.data11
        new_chart.data21 = self.data21
        new_chart.reference11 = self.reference11
        new_chart.reference21 = self.reference21
        return new_chart


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

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        super().drawChart(qp)

        # Make up some sensible scaling here
        if self.fixedValues:
            maxQ = self.maxDisplayValue
            minQ = self.minDisplayValue
        else:
            minQ = 0
            maxQ = 0
            for d in self.data:
                Q = d.qFactor()
                if Q > maxQ:
                    maxQ = Q
            scale = 0
            if maxQ > 0:
                scale = max(scale, math.floor(math.log10(maxQ)))
                maxQ = math.ceil(maxQ / 10 ** scale) * 10 ** scale
        self.minQ = minQ
        self.maxQ = maxQ
        self.span = self.maxQ - self.minQ
        if self.span == 0:
            return  # No data to draw the graph from

        tickcount = math.floor(self.chartHeight / 60)

        for i in range(tickcount):
            q = self.minQ + i * self.span / tickcount
            y = self.topMargin + round((self.maxQ - q) / self.span * self.chartHeight)
            if q < 10:
                q = round(q, 2)
            elif q < 20:
                q = round(q, 1)
            else:
                q = round(q)
            qp.setPen(QtGui.QPen(self.textColor))
            qp.drawText(3, y+3, str(q))
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin + self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5, self.topMargin, self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        if maxQ < 10:
            qstr = str(round(maxQ, 2))
        elif maxQ < 20:
            qstr = str(round(maxQ, 1))
        else:
            qstr = str(round(maxQ))
        qp.drawText(3, 35, qstr)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        if self.span == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        self.drawFrequencyTicks(qp)
        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        Q = d.qFactor()
        return self.topMargin + round((self.maxQ - Q) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxQ)
        return [val]


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
        self.leftMargin = 30
        self.rightMargin = 20
        self.bottomMargin = 25
        self.topMargin = 20
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.menu = QtWidgets.QMenu()

        self.reset = QtWidgets.QAction("Reset")
        self.reset.triggered.connect(self.resetDisplayLimits)
        self.menu.addAction(self.reset)

        self.x_menu = QtWidgets.QMenu("Length axis")
        self.mode_group = QtWidgets.QActionGroup(self.x_menu)
        self.action_automatic = QtWidgets.QAction("Automatic")
        self.action_automatic.setCheckable(True)
        self.action_automatic.setChecked(True)
        self.action_automatic.changed.connect(lambda: self.setFixedSpan(self.action_fixed_span.isChecked()))
        self.action_fixed_span = QtWidgets.QAction("Fixed span")
        self.action_fixed_span.setCheckable(True)
        self.action_fixed_span.changed.connect(lambda: self.setFixedSpan(self.action_fixed_span.isChecked()))
        self.mode_group.addAction(self.action_automatic)
        self.mode_group.addAction(self.action_fixed_span)
        self.x_menu.addAction(self.action_automatic)
        self.x_menu.addAction(self.action_fixed_span)
        self.x_menu.addSeparator()

        self.action_set_fixed_start = QtWidgets.QAction("Start (" + str(self.minDisplayLength) + ")")
        self.action_set_fixed_start.triggered.connect(self.setMinimumLength)

        self.action_set_fixed_stop = QtWidgets.QAction("Stop (" + str(self.maxDisplayLength) + ")")
        self.action_set_fixed_stop.triggered.connect(self.setMaximumLength)

        self.x_menu.addAction(self.action_set_fixed_start)
        self.x_menu.addAction(self.action_set_fixed_stop)

        self.y_menu = QtWidgets.QMenu("Impedance axis")
        self.y_mode_group = QtWidgets.QActionGroup(self.y_menu)
        self.y_action_automatic = QtWidgets.QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(lambda: self.setFixedValues(self.y_action_fixed.isChecked()))
        self.y_action_fixed = QtWidgets.QAction("Fixed")
        self.y_action_fixed.setCheckable(True)
        self.y_action_fixed.changed.connect(lambda: self.setFixedValues(self.y_action_fixed.isChecked()))
        self.y_mode_group.addAction(self.y_action_automatic)
        self.y_mode_group.addAction(self.y_action_fixed)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed)
        self.y_menu.addSeparator()

        self.y_action_set_fixed_maximum = QtWidgets.QAction("Maximum (" + str(self.maxImpedance) + ")")
        self.y_action_set_fixed_maximum.triggered.connect(self.setMaximumImpedance)

        self.y_action_set_fixed_minimum = QtWidgets.QAction("Minimum (" + str(self.minImpedance) + ")")
        self.y_action_set_fixed_minimum.triggered.connect(self.setMinimumImpedance)

        self.y_menu.addAction(self.y_action_set_fixed_maximum)
        self.y_menu.addAction(self.y_action_set_fixed_minimum)

        self.menu.addMenu(self.x_menu)
        self.menu.addMenu(self.y_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.action_save_screenshot)
        self.action_popout = QtWidgets.QAction("Popout chart")
        self.action_popout.triggered.connect(lambda: self.popoutRequested.emit(self))
        self.menu.addAction(self.action_popout)

        self.chartWidth = self.width() - self.leftMargin - self.rightMargin
        self.chartHeight = self.height() - self.bottomMargin - self.topMargin

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText("Start (" + str(self.minDisplayLength) + ")")
        self.action_set_fixed_stop.setText("Stop (" + str(self.maxDisplayLength) + ")")
        self.y_action_set_fixed_minimum.setText("Minimum (" + str(self.minImpedance) + ")")
        self.y_action_set_fixed_maximum.setText("Maximum (" + str(self.maxImpedance) + ")")
        self.menu.exec_(event.globalPos())

    def isPlotable(self, x, y):
        return self.leftMargin <= x <= self.width() - self.rightMargin and \
               self.topMargin <= y <= self.height() - self.bottomMargin

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
        min_val, selected = QtWidgets.QInputDialog.getDouble(self, "Start length (m)",
                                                             "Set start length (m)", value=self.minDisplayLength,
                                                             min=0, decimals=1)
        if not selected:
            return
        if not (self.fixedSpan and min_val >= self.maxDisplayLength):
            self.minDisplayLength = min_val
        if self.fixedSpan:
            self.update()

    def setMaximumLength(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(self, "Stop length (m)",
                                                             "Set stop length (m)", value=self.minDisplayLength,
                                                             min=0.1, decimals=1)
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
        min_val, selected = QtWidgets.QInputDialog.getDouble(self, "Minimum impedance (\N{OHM SIGN})",
                                                             "Set minimum impedance (\N{OHM SIGN})",
                                                             value=self.minDisplayLength,
                                                             min=0, decimals=1)
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxImpedance):
            self.minImpedance = min_val
        if self.fixedValues:
            self.update()

    def setMaximumImpedance(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(self, "Maximum impedance (\N{OHM SIGN})",
                                                             "Set maximum impedance (\N{OHM SIGN})",
                                                             value=self.minDisplayLength,
                                                             min=0.1, decimals=1)
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

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
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
                            self.leftMargin + self.chartWidth + dx, self.topMargin + self.chartHeight + dy)

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
        absx = x - self.leftMargin
        if absx < 0 or absx > self.width() - self.rightMargin:
            a0.ignore()
            return
        a0.accept()
        width = self.width() - self.leftMargin - self.rightMargin
        if len(self.tdrWindow.td) > 0:
            if self.fixedSpan:
                max_index = np.searchsorted(self.tdrWindow.distance_axis, self.maxDisplayLength * 2)
                min_index = np.searchsorted(self.tdrWindow.distance_axis, self.minDisplayLength * 2)
                x_step = (max_index - min_index) / width
            else:
                max_index = math.ceil(len(self.tdrWindow.distance_axis) / 2)
                x_step = max_index / width

            self.markerLocation = int(round(absx * x_step))
            self.update()
        return

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)

        width = self.width() - self.leftMargin - self.rightMargin
        height = self.height() - self.bottomMargin - self.topMargin

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.height() - self.bottomMargin, self.width() - self.rightMargin,
                    self.height() - self.bottomMargin)
        qp.drawLine(self.leftMargin, self.topMargin - 5, self.leftMargin, self.height() - self.bottomMargin + 5)

        ticks = math.floor((self.width() - self.leftMargin)/100)  # Number of ticks does not include the origin

        self.drawTitle(qp)

        if len(self.tdrWindow.td) > 0:
            if self.fixedSpan:
                max_length = max(0.1, self.maxDisplayLength)
                max_index = np.searchsorted(self.tdrWindow.distance_axis, max_length * 2)
                min_index = np.searchsorted(self.tdrWindow.distance_axis, self.minDisplayLength * 2)
                if max_index == min_index:
                    if max_index < len(self.tdrWindow.distance_axis) - 1:
                        max_index += 1
                    else:
                        min_index -= 1
                x_step = (max_index - min_index) / width
            else:
                min_index = 0
                max_index = math.ceil(len(self.tdrWindow.distance_axis) / 2)
                x_step = max_index / width

            if self.fixedValues:
                min_impedance = max(0, self.minImpedance)
                max_impedance = max(0.1, self.maxImpedance)
            else:
                # TODO: Limit the search to the selected span?
                min_impedance = max(0, np.min(self.tdrWindow.step_response_Z) / 1.05)
                max_impedance = min(1000, np.max(self.tdrWindow.step_response_Z) * 1.05)

            y_step = np.max(self.tdrWindow.td) * 1.1 / height
            y_impedance_step = (max_impedance - min_impedance) / height

            for i in range(ticks):
                x = self.leftMargin + round((i + 1) * width / ticks)
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(x, self.topMargin, x, self.topMargin + height)
                qp.setPen(QtGui.QPen(self.textColor))
                qp.drawText(x - 15, self.topMargin + height + 15,
                            str(round(self.tdrWindow.distance_axis[min_index +
                                                                   int((x - self.leftMargin) * x_step) - 1]/2,
                                      1)
                                )
                            + "m")

            qp.setPen(QtGui.QPen(self.textColor))
            qp.drawText(self.leftMargin - 10, self.topMargin + height + 15,
                        str(round(self.tdrWindow.distance_axis[min_index]/2, 1)) + "m")

            y_ticks = math.floor(height / 60)
            y_tick_step = height/y_ticks

            for i in range(y_ticks):
                y = self.bottomMargin + int(i * y_tick_step)
                qp.setPen(self.foregroundColor)
                qp.drawLine(self.leftMargin, y, self.leftMargin + width, y)
                y_val = max_impedance - y_impedance_step * i * y_tick_step
                qp.setPen(self.textColor)
                qp.drawText(3, y + 3, str(round(y_val, 1)))

            qp.drawText(3, self.topMargin + height + 3, str(round(min_impedance, 1)))

            pen = QtGui.QPen(self.sweepColor)
            pen.setWidth(self.pointSize)
            qp.setPen(pen)
            for i in range(min_index, max_index):
                if i < min_index or i > max_index:
                    continue

                x = self.leftMargin + int((i - min_index) / x_step)
                y = (self.topMargin + height) - int(self.tdrWindow.td[i] / y_step)
                if self.isPlotable(x, y):
                    pen.setColor(self.sweepColor)
                    qp.setPen(pen)
                    qp.drawPoint(x, y)

                x = self.leftMargin + int((i - min_index) / x_step)
                y = (self.topMargin + height) -\
                    int((self.tdrWindow.step_response_Z[i]-min_impedance) / y_impedance_step)
                if self.isPlotable(x, y):
                    pen.setColor(self.secondarySweepColor)
                    qp.setPen(pen)
                    qp.drawPoint(x, y)

            id_max = np.argmax(self.tdrWindow.td)
            max_point = QtCore.QPoint(self.leftMargin + int((id_max - min_index) / x_step),
                                      (self.topMargin + height) - int(self.tdrWindow.td[id_max] / y_step))
            qp.setPen(self.markers[0].color)
            qp.drawEllipse(max_point, 2, 2)
            qp.setPen(self.textColor)
            qp.drawText(max_point.x() - 10, max_point.y() - 5,
                        str(round(self.tdrWindow.distance_axis[id_max]/2, 2)) + "m")

            if self.markerLocation != -1:
                marker_point = QtCore.QPoint(self.leftMargin + int((self.markerLocation - min_index) / x_step),
                                       (self.topMargin + height) - int(self.tdrWindow.td[self.markerLocation] / y_step))
                qp.setPen(self.textColor)
                qp.drawEllipse(marker_point, 2, 2)
                qp.drawText(marker_point.x() - 10, marker_point.y() - 5,
                            str(round(self.tdrWindow.distance_axis[self.markerLocation] / 2, 2)) + "m")

        if self.draggedBox and self.draggedBoxCurrent[0] != -1:
            dashed_pen = QtGui.QPen(self.foregroundColor, 1, QtCore.Qt.DashLine)
            qp.setPen(dashed_pen)
            top_left = QtCore.QPoint(self.draggedBoxStart[0], self.draggedBoxStart[1])
            bottom_right = QtCore.QPoint(self.draggedBoxCurrent[0], self.draggedBoxCurrent[1])
            rect = QtCore.QRect(top_left, bottom_right)
            qp.drawRect(rect)

        qp.end()

    def valueAtPosition(self, y):
        if len(self.tdrWindow.td) > 0:
            height = self.height() - self.topMargin - self.bottomMargin
            absy = (self.height() - y) - self.bottomMargin
            if self.fixedValues:
                min_impedance = self.minImpedance
                max_impedance = self.maxImpedance
            else:
                min_impedance = max(0, np.min(self.tdrWindow.step_response_Z) / 1.05)
                max_impedance = min(1000, np.max(self.tdrWindow.step_response_Z) * 1.05)
            y_step = (max_impedance - min_impedance) / height
            return y_step * absy + min_impedance
        else:
            return 0

    def lengthAtPosition(self, x, limit=True):
        if len(self.tdrWindow.td) > 0:
            width = self.width() - self.leftMargin - self.rightMargin
            absx = x - self.leftMargin
            if self.fixedSpan:
                max_length = self.maxDisplayLength
                min_length = self.minDisplayLength
                x_step = (max_length - min_length) / width
            else:
                min_length = 0
                max_length = self.tdrWindow.distance_axis[math.ceil(len(self.tdrWindow.distance_axis) / 2)]/2
                x_step = max_length / width
            if limit and absx < 0:
                return min_length
            if limit and absx > width:
                return max_length
            return absx * x_step + min_length
        else:
            return 0

    def zoomTo(self, x1, y1, x2, y2):
        logger.debug("Zoom to (x,y) by (x,y): (%d, %d) by (%d, %d)", x1, y1, x2, y2)
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

    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        if len(self.tdrWindow.td) == 0:
            a0.ignore()
            return
        chart_height = self.chartHeight
        chart_width = self.chartWidth
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
                zoomx = rate * chart_width / 10
            else:
                zoomx = 0
            if do_zoom_y:
                zoomy = rate * chart_height / 10
            else:
                zoomy = 0
            absx = max(0, a0.x() - self.leftMargin)
            absy = max(0, a0.y() - self.topMargin)
            ratiox = absx/chart_width
            ratioy = absy/chart_height
            # TODO: Change zoom to center on the mouse if possible, or extend box to the side that has room if not.
            p1x = int(self.leftMargin + ratiox * zoomx)
            p1y = int(self.topMargin + ratioy * zoomy)
            p2x = int(self.leftMargin + chart_width - (1 - ratiox) * zoomx)
            p2y = int(self.topMargin + chart_height - (1 - ratioy) * zoomy)
            self.zoomTo(p1x, p1y, p2x, p2y)
        elif a0.angleDelta().y() < 0:
            # Zoom out
            a0.accept()
            # Center of zoom = a0.x(), a0.y()
            # We zoom out by 1/9 of the width/height, to match zoom in.
            rate = -a0.angleDelta().y() / 120
            if do_zoom_x:
                zoomx = rate * chart_width / 9
            else:
                zoomx = 0
            if do_zoom_y:
                zoomy = rate * chart_height / 9
            else:
                zoomy = 0
            absx = max(0, a0.x() - self.leftMargin)
            absy = max(0, a0.y() - self.topMargin)
            ratiox = absx/chart_width
            ratioy = absy/chart_height
            p1x = int(self.leftMargin - ratiox * zoomx)
            p1y = int(self.topMargin - ratioy * zoomy)
            p2x = int(self.leftMargin + chart_width + (1 - ratiox) * zoomx)
            p2y = int(self.topMargin + chart_height + (1 - ratioy) * zoomy)
            self.zoomTo(p1x, p1y, p2x, p2y)
        else:
            a0.ignore()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        self.chartWidth = self.width() - self.leftMargin - self.rightMargin
        self.chartHeight = self.height() - self.bottomMargin - self.topMargin


class RealImaginaryChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 45
        self.rightMargin = 45
        self.chartWidth = 230
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.span_real = 0.01
        self.span_imag = 0.01
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
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def copy(self):
        new_chart: RealImaginaryChart = super().copy()

        new_chart.maxDisplayReal = self.maxDisplayReal
        new_chart.maxDisplayImag = self.maxDisplayImag
        new_chart.minDisplayReal = self.minDisplayReal
        new_chart.minDisplayImag = self.minDisplayImag
        return new_chart

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(self.leftMargin + 5, 15, self.name + " (\N{OHM SIGN})")
        qp.drawText(10, 15, "R")
        qp.drawText(self.leftMargin + self.chartWidth + 10, 15, "X")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5, self.leftMargin, self.topMargin + self.chartHeight + 5)
        qp.drawLine(self.leftMargin-5, self.topMargin + self.chartHeight,
                    self.leftMargin + self.chartWidth + 5, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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
                imp = d.impedance()
                re, im = imp.real, imp.imag
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
                imp = d.impedance()
                re, im = imp.real, imp.imag
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
        if span_real == 0:
            span_real = 0.01
        self.span_real = span_real

        span_imag = max_imag - min_imag
        if span_imag == 0:
            span_imag = 0.01
        self.span_imag = span_imag

        # We want one horizontal tick per 50 pixels, at most
        horizontal_ticks = math.floor(self.chartHeight/50)

        for i in range(horizontal_ticks):
            y = self.topMargin + round(i * self.chartHeight / horizontal_ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth + 5, y)
            qp.setPen(QtGui.QPen(self.textColor))
            re = max_real - i * span_real / horizontal_ticks
            im = max_imag - i * span_imag / horizontal_ticks
            qp.drawText(3, y + 4, str(round(re, 1)))
            qp.drawText(self.leftMargin + self.chartWidth + 8, y + 4, str(round(im, 1)))

        qp.drawText(3, self.chartHeight + self.topMargin, str(round(min_real, 1)))
        qp.drawText(self.leftMargin + self.chartWidth + 8, self.chartHeight + self.topMargin, str(round(min_imag, 1)))

        self.drawFrequencyTicks(qp)

        primary_pen = pen
        secondary_pen = QtGui.QPen(self.secondarySweepColor)
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

        primary_pen.setWidth(self.pointSize)
        secondary_pen.setWidth(self.pointSize)
        line_pen.setWidth(self.lineThickness)

        for i in range(len(self.data)):
            x = self.getXPosition(self.data[i])
            y_re = self.getReYPosition(self.data[i])
            y_im = self.getImYPosition(self.data[i])
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.drawLines and i > 0:
                prev_x = self.getXPosition(self.data[i - 1])
                prev_y_re = self.getReYPosition(self.data[i-1])
                prev_y_im = self.getImYPosition(self.data[i-1])

                # Real part first
                line_pen.setColor(self.sweepColor)
                qp.setPen(line_pen)
                if self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    qp.drawLine(x, y_re, prev_x, prev_y_re)
                elif self.isPlotable(x, y_re) and not self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(x, y_re, prev_x, prev_y_re)
                    qp.drawLine(x, y_re, new_x, new_y)
                elif not self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_re, x, y_re)
                    qp.drawLine(prev_x, prev_y_re, new_x, new_y)

                # Imag part second
                line_pen.setColor(self.secondarySweepColor)
                qp.setPen(line_pen)
                if self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    qp.drawLine(x, y_im, prev_x, prev_y_im)
                elif self.isPlotable(x, y_im) and not self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(x, y_im, prev_x, prev_y_im)
                    qp.drawLine(x, y_im, new_x, new_y)
                elif not self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_im, x, y_im)
                    qp.drawLine(prev_x, prev_y_im, new_x, new_y)

        primary_pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        secondary_pen.setColor(self.secondaryReferenceColor)
        qp.setPen(primary_pen)
        if len(self.reference) > 0:
            c = QtGui.QColor(self.referenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 14, 25, 14)
            c = QtGui.QColor(self.secondaryReferenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.chartWidth, 14, self.leftMargin + self.chartWidth + 5, 14)

        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            x = self.getXPosition(self.reference[i])
            y_re = self.getReYPosition(self.reference[i])
            y_im = self.getImYPosition(self.reference[i])
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.drawLines and i > 0:
                prev_x = self.getXPosition(self.reference[i - 1])
                prev_y_re = self.getReYPosition(self.reference[i-1])
                prev_y_im = self.getImYPosition(self.reference[i-1])

                line_pen.setColor(self.referenceColor)
                qp.setPen(line_pen)
                # Real part first
                if self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    qp.drawLine(x, y_re, prev_x, prev_y_re)
                elif self.isPlotable(x, y_re) and not self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(x, y_re, prev_x, prev_y_re)
                    qp.drawLine(x, y_re, new_x, new_y)
                elif not self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_re, x, y_re)
                    qp.drawLine(prev_x, prev_y_re, new_x, new_y)

                line_pen.setColor(self.secondaryReferenceColor)
                qp.setPen(line_pen)
                # Imag part second
                if self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    qp.drawLine(x, y_im, prev_x, prev_y_im)
                elif self.isPlotable(x, y_im) and not self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(x, y_im, prev_x, prev_y_im)
                    qp.drawLine(x, y_im, new_x, new_y)
                elif not self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_im, x, y_im)
                    qp.drawLine(prev_x, prev_y_im, new_x, new_y)

        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                x = self.getXPosition(self.data[m.location])
                y_re = self.getReYPosition(self.data[m.location])
                y_im = self.getImYPosition(self.data[m.location])

                self.drawMarker(x, y_re, qp, m.color, self.markers.index(m)+1)
                self.drawMarker(x, y_im, qp, m.color, self.markers.index(m)+1)

    def getImYPosition(self, d: Datapoint) -> int:
        im = d.impedance().imag
        return self.topMargin + round((self.max_imag - im) / self.span_imag * self.chartHeight)

    def getReYPosition(self, d: Datapoint) -> int:
        re = d.impedance().real
        return self.topMargin + round((self.max_real - re) / self.span_real * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        valRe = -1 * ((absy / self.chartHeight * self.span_real) - self.max_real)
        valIm = -1 * ((absy / self.chartHeight * self.span_imag) - self.max_imag)
        return [valRe, valIm]

    def zoomTo(self, x1, y1, x2, y2):
        val1 = self.valueAtPosition(y1)
        val2 = self.valueAtPosition(y2)

        if len(val1) == len(val2) == 2 and val1[0] != val2[0]:
            self.minDisplayReal = round(min(val1[0], val2[0]), 2)
            self.maxDisplayReal = round(max(val1[0], val2[0]), 2)
            self.minDisplayImag = round(min(val1[1], val2[1]), 2)
            self.maxDisplayImag = round(max(val1[1], val2[1]), 2)
            self.setFixedValues(True)

        freq1 = max(1, self.frequencyAtPosition(x1, limit=False))
        freq2 = max(1, self.frequencyAtPosition(x2, limit=False))

        if freq1 > 0 and freq2 > 0 and freq1 != freq2:
            self.minFrequency = min(freq1, freq2)
            self.maxFrequency = max(freq1, freq2)
            self.setFixedSpan(True)

        self.update()

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
        min_val, selected = QtWidgets.QInputDialog.getDouble(self, "Minimum real value",
                                                             "Set minimum real value", value=self.minDisplayReal,
                                                             decimals=2)
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayReal):
            self.minDisplayReal = min_val
        if self.fixedValues:
            self.update()

    def setMaximumRealValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(self, "Maximum real value",
                                                             "Set maximum real value", value=self.maxDisplayReal,
                                                             decimals=2)
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minDisplayReal):
            self.maxDisplayReal = max_val
        if self.fixedValues:
            self.update()

    def setMinimumImagValue(self):
        min_val, selected = QtWidgets.QInputDialog.getDouble(self, "Minimum imaginary value",
                                                             "Set minimum imaginary value", value=self.minDisplayImag,
                                                             decimals=2)
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayImag):
            self.minDisplayImag = min_val
        if self.fixedValues:
            self.update()

    def setMaximumImagValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(self, "Maximum imaginary value",
                                                             "Set maximum imaginary value", value=self.maxDisplayImag,
                                                             decimals=2)
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minDisplayImag):
            self.maxDisplayImag = max_val
        if self.fixedValues:
            self.update()

    def setFixedValues(self, fixed_values: bool):
        self.fixedValues = fixed_values
        if fixed_values and (self.minDisplayReal >= self.maxDisplayReal or self.minDisplayImag > self.maxDisplayImag):
            self.fixedValues = False
            self.y_action_automatic.setChecked(True)
            self.y_action_fixed_span.setChecked(False)
        self.update()

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText("Start (" + Chart.shortenFrequency(self.minFrequency) + ")")
        self.action_set_fixed_stop.setText("Stop (" + Chart.shortenFrequency(self.maxFrequency) + ")")
        self.action_set_fixed_minimum_real.setText("Minimum R (" + str(self.minDisplayReal) + ")")
        self.action_set_fixed_maximum_real.setText("Maximum R (" + str(self.maxDisplayReal) + ")")
        self.action_set_fixed_minimum_imag.setText("Minimum jX (" + str(self.minDisplayImag) + ")")
        self.action_set_fixed_maximum_imag.setText("Maximum jX (" + str(self.maxDisplayImag) + ")")

        self.menu.exec_(event.globalPos())


class MagnitudeChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = 0
        self.maxDisplayValue = 1

        self.fixedValues = True
        self.y_action_fixed_span.setChecked(True)
        self.y_action_automatic.setChecked(False)

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 100
            maxValue = 0
            for d in self.data:
                mag = self.magnitude(d)
                if mag > maxValue:
                    maxValue = mag
                if mag < minValue:
                    minValue = mag
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                mag = self.magnitude(d)
                if mag > maxValue:
                    maxValue = mag
                if mag < minValue:
                    minValue = mag

            minValue = 10*math.floor(minValue/10)
            self.minValue = minValue
            maxValue = 10*math.ceil(maxValue/10)
            self.maxValue = maxValue

        span = maxValue-minValue
        if span == 0:
            span = 0.01
        self.span = span

        target_ticks = math.floor(self.chartHeight / 60)

        for i in range(target_ticks):
            val = minValue + i / target_ticks * span
            y = self.topMargin + round((self.maxValue - val) / self.span * self.chartHeight)
            qp.setPen(self.textColor)
            if val != minValue:
                digits = max(0, min(2, math.floor(3 - math.log10(abs(val)))))
                if digits == 0:
                    vswrstr = str(round(val))
                else:
                    vswrstr = str(round(val, digits))
                qp.drawText(3, y + 3, vswrstr)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        qp.setPen(self.swrColor)
        for vswr in self.swrMarkers:
            if vswr <= 1:
                continue
            mag = (vswr-1)/(vswr+1)
            y = self.topMargin + round((self.maxValue - mag) / self.span * self.chartHeight)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.chartWidth, y)
            qp.drawText(self.leftMargin + 3, y - 1, "VSWR: " + str(vswr))

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        mag = self.magnitude(d)
        return self.topMargin + round((self.maxValue - mag) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val]

    @staticmethod
    def magnitude(p: Datapoint) -> float:
        return math.sqrt(p.re**2 + p.im**2)

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.span = self.span
        return new_chart


class MagnitudeZChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 100
            maxValue = 0
            for d in self.data:
                mag = self.magnitude(d)
                if mag > maxValue:
                    maxValue = mag
                if mag < minValue:
                    minValue = mag
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                mag = self.magnitude(d)
                if mag > maxValue:
                    maxValue = mag
                if mag < minValue:
                    minValue = mag

            minValue = 10*math.floor(minValue/10)
            self.minValue = minValue
            maxValue = 10*math.ceil(maxValue/10)
            self.maxValue = maxValue

        span = maxValue-minValue
        if span == 0:
            span = 0.01
        self.span = span

        target_ticks = math.floor(self.chartHeight / 60)

        for i in range(target_ticks):
            val = minValue + (i / target_ticks) * span
            y = self.topMargin + round((self.maxValue - val) / self.span * self.chartHeight)
            qp.setPen(self.textColor)
            if val != minValue:
                digits = max(0, min(2, math.floor(3 - math.log10(abs(val)))))
                if digits == 0:
                    vswrstr = str(round(val))
                else:
                    vswrstr = str(round(val, digits))
                qp.drawText(3, y + 3, vswrstr)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        mag = self.magnitude(d)
        return self.topMargin + round((self.maxValue - mag) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val]

    @staticmethod
    def magnitude(p: Datapoint) -> float:
        return abs(p.impedance())

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.span = self.span
        return new_chart


class PermeabilityChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 40
        self.rightMargin = 30
        self.chartWidth = 230
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.span = 0.01
        self.max = 0
        self.logarithmicY = True

        self.maxDisplayValue = 100
        self.minDisplayValue = -100

        #
        # Set up size policy and palette
        #

        self.setMinimumSize(self.chartWidth + self.leftMargin + self.rightMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.y_menu.addSeparator()
        self.y_log_lin_group = QtWidgets.QActionGroup(self.y_menu)
        self.y_action_linear = QtWidgets.QAction("Linear")
        self.y_action_linear.setCheckable(True)
        self.y_action_logarithmic = QtWidgets.QAction("Logarithmic")
        self.y_action_logarithmic.setCheckable(True)
        self.y_action_logarithmic.setChecked(True)
        self.y_action_linear.triggered.connect(lambda: self.setLogarithmicY(False))
        self.y_action_logarithmic.triggered.connect(lambda: self.setLogarithmicY(True))
        self.y_log_lin_group.addAction(self.y_action_linear)
        self.y_log_lin_group.addAction(self.y_action_logarithmic)
        self.y_menu.addAction(self.y_action_linear)
        self.y_menu.addAction(self.y_action_logarithmic)

    def setLogarithmicY(self, logarithmic: bool):
        self.logarithmicY = logarithmic
        self.update()

    def copy(self):
        new_chart: PermeabilityChart = super().copy()
        new_chart.logarithmicY = self.logarithmicY
        return new_chart

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(self.leftMargin + 5, 15, self.name + " (\N{MICRO SIGN}\N{OHM SIGN} / Hz)")
        qp.drawText(10, 15, "R")
        qp.drawText(self.leftMargin + self.chartWidth + 10, 15, "X")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin + self.chartHeight + 5)
        qp.drawLine(self.leftMargin-5, self.topMargin + self.chartHeight,
                    self.leftMargin + self.chartWidth + 5, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        # Find scaling
        if self.fixedValues:
            min_val = self.minDisplayValue
            max_val = self.maxDisplayValue
        else:
            min_val = 1000
            max_val = -1000
            for d in self.data:
                imp = d.impedance()
                re, im = imp.real, imp.imag
                re = re * 10e6 / d.freq
                im = im * 10e6 / d.freq
                if re > max_val:
                    max_val = re
                if re < min_val:
                    min_val = re
                if im > max_val:
                    max_val = im
                if im < min_val:
                    min_val = im
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < fstart or d.freq > fstop:
                    continue
                imp = d.impedance()
                re, im = imp.real, imp.imag
                re = re * 10e6 / d.freq
                im = im * 10e6 / d.freq
                if re > max_val:
                    max_val = re
                if re < min_val:
                    min_val = re
                if im > max_val:
                    max_val = im
                if im < min_val:
                    min_val = im

        if self.logarithmicY:
            min_val = max(0.01, min_val)

        self.max = max_val

        span = max_val - min_val
        if span == 0:
            span = 0.01
        self.span = span

        # We want one horizontal tick per 50 pixels, at most
        horizontal_ticks = math.floor(self.chartHeight/50)
        fmt = Format(max_nr_digits=4)
        for i in range(horizontal_ticks):
            y = self.topMargin + round(i * self.chartHeight / horizontal_ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth + 5, y)
            qp.setPen(QtGui.QPen(self.textColor))
            val = Value(self.valueAtPosition(y)[0], fmt=fmt)
            qp.drawText(3, y + 4, str(val))

        qp.drawText(3, self.chartHeight + self.topMargin, str(Value(min_val, fmt=fmt)))

        self.drawFrequencyTicks(qp)

        primary_pen = pen
        secondary_pen = QtGui.QPen(self.secondarySweepColor)
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

        primary_pen.setWidth(self.pointSize)
        secondary_pen.setWidth(self.pointSize)
        line_pen.setWidth(self.lineThickness)

        for i in range(len(self.data)):
            x = self.getXPosition(self.data[i])
            y_re = self.getReYPosition(self.data[i])
            y_im = self.getImYPosition(self.data[i])
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.drawLines and i > 0:
                prev_x = self.getXPosition(self.data[i - 1])
                prev_y_re = self.getReYPosition(self.data[i-1])
                prev_y_im = self.getImYPosition(self.data[i-1])

                # Real part first
                line_pen.setColor(self.sweepColor)
                qp.setPen(line_pen)
                if self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    qp.drawLine(x, y_re, prev_x, prev_y_re)
                elif self.isPlotable(x, y_re) and not self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(x, y_re, prev_x, prev_y_re)
                    qp.drawLine(x, y_re, new_x, new_y)
                elif not self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_re, x, y_re)
                    qp.drawLine(prev_x, prev_y_re, new_x, new_y)

                # Imag part second
                line_pen.setColor(self.secondarySweepColor)
                qp.setPen(line_pen)
                if self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    qp.drawLine(x, y_im, prev_x, prev_y_im)
                elif self.isPlotable(x, y_im) and not self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(x, y_im, prev_x, prev_y_im)
                    qp.drawLine(x, y_im, new_x, new_y)
                elif not self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_im, x, y_im)
                    qp.drawLine(prev_x, prev_y_im, new_x, new_y)

        primary_pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        secondary_pen.setColor(self.secondaryReferenceColor)
        qp.setPen(primary_pen)
        if len(self.reference) > 0:
            c = QtGui.QColor(self.referenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 14, 25, 14)
            c = QtGui.QColor(self.secondaryReferenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.chartWidth, 14, self.leftMargin + self.chartWidth + 5, 14)

        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            x = self.getXPosition(self.reference[i])
            y_re = self.getReYPosition(self.reference[i])
            y_im = self.getImYPosition(self.reference[i])
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.drawLines and i > 0:
                prev_x = self.getXPosition(self.reference[i - 1])
                prev_y_re = self.getReYPosition(self.reference[i-1])
                prev_y_im = self.getImYPosition(self.reference[i-1])

                line_pen.setColor(self.referenceColor)
                qp.setPen(line_pen)
                # Real part first
                if self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    qp.drawLine(x, y_re, prev_x, prev_y_re)
                elif self.isPlotable(x, y_re) and not self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(x, y_re, prev_x, prev_y_re)
                    qp.drawLine(x, y_re, new_x, new_y)
                elif not self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_re, x, y_re)
                    qp.drawLine(prev_x, prev_y_re, new_x, new_y)

                line_pen.setColor(self.secondaryReferenceColor)
                qp.setPen(line_pen)
                # Imag part second
                if self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    qp.drawLine(x, y_im, prev_x, prev_y_im)
                elif self.isPlotable(x, y_im) and not self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(x, y_im, prev_x, prev_y_im)
                    qp.drawLine(x, y_im, new_x, new_y)
                elif not self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_im, x, y_im)
                    qp.drawLine(prev_x, prev_y_im, new_x, new_y)

        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                x = self.getXPosition(self.data[m.location])
                y_re = self.getReYPosition(self.data[m.location])
                y_im = self.getImYPosition(self.data[m.location])

                self.drawMarker(x, y_re, qp, m.color, self.markers.index(m)+1)
                self.drawMarker(x, y_im, qp, m.color, self.markers.index(m)+1)

    def getImYPosition(self, d: Datapoint) -> int:
        im = d.impedance().imag
        im = im * 10e6 / d.freq
        if self.logarithmicY:
            min_val = self.max - self.span
            if self.max > 0 and min_val > 0 and im > 0:
                span = math.log(self.max) - math.log(min_val)
            else:
                return -1
            return self.topMargin + round((math.log(self.max) - math.log(im)) / span * self.chartHeight)
        else:
            return self.topMargin + round((self.max - im) / self.span * self.chartHeight)

    def getReYPosition(self, d: Datapoint) -> int:
        re = d.impedance().real
        re = re * 10e6 / d.freq
        if self.logarithmicY:
            min_val = self.max - self.span
            if self.max > 0 and min_val > 0 and re > 0:
                span = math.log(self.max) - math.log(min_val)
            else:
                return -1
            return self.topMargin + round((math.log(self.max) - math.log(re)) / span * self.chartHeight)
        else:
            return self.topMargin + round((self.max - re) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        if self.logarithmicY:
            min_val = self.max - self.span
            if self.max > 0 and min_val > 0:
                span = math.log(self.max) - math.log(min_val)
                step = span / self.chartHeight
                val = math.exp(math.log(self.max) - absy * step)
            else:
                val = -1
        else:
            val = -1 * ((absy / self.chartHeight * self.span) - self.max)
        return [val]

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


class GroupDelayChart(FrequencyChart):
    def __init__(self, name="", reflective=True):
        super().__init__(name)
        self.leftMargin = 40
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.minDelay = 0
        self.maxDelay = 0
        self.span = 0

        self.reflective = reflective

        self.groupDelay = []
        self.groupDelayReference = []

        self.minDisplayValue = -180
        self.maxDisplayValue = 180

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def copy(self):
        new_chart: GroupDelayChart = super().copy()
        new_chart.reflective = self.reflective
        new_chart.groupDelay = self.groupDelay.copy()
        new_chart.groupDelayReference = self.groupDelay.copy()
        return new_chart

    def setReference(self, data):
        self.reference = data

        self.calculateGroupDelay()

    def setData(self, data):
        self.data = data

        self.calculateGroupDelay()

    def calculateGroupDelay(self):
        rawData = []
        for d in self.data:
            rawData.append(d.phase)

        rawReference = []
        for d in self.reference:
            rawReference.append(d.phase)

        if len(self.data) > 0:
            unwrappedData = np.degrees(np.unwrap(rawData))
            self.groupDelay = []
            for i in range(len(self.data)):
                # TODO: Replace with call to RFTools.groupDelay
                if i == 0:
                    phase_change = unwrappedData[1] - unwrappedData[0]
                    freq_change = self.data[1].freq - self.data[0].freq
                elif i == len(self.data)-1:
                    idx = len(self.data)-1
                    phase_change = unwrappedData[idx] - unwrappedData[idx-1]
                    freq_change = self.data[idx].freq - self.data[idx-1].freq
                else:
                    phase_change = unwrappedData[i+1] - unwrappedData[i-1]
                    freq_change = self.data[i+1].freq - self.data[i-1].freq
                delay = (-phase_change / (freq_change * 360)) * 10e8
                if not self.reflective:
                    delay /= 2
                self.groupDelay.append(delay)

        if len(self.reference) > 0:
            unwrappedReference = np.degrees(np.unwrap(rawReference))
            self.groupDelayReference = []
            for i in range(len(self.reference)):
                if i == 0:
                    phase_change = unwrappedReference[1] - unwrappedReference[0]
                    freq_change = self.reference[1].freq - self.reference[0].freq
                elif i == len(self.reference)-1:
                    idx = len(self.reference)-1
                    phase_change = unwrappedReference[idx] - unwrappedReference[idx-1]
                    freq_change = self.reference[idx].freq - self.reference[idx-1].freq
                else:
                    phase_change = unwrappedReference[i+1] - unwrappedReference[i-1]
                    freq_change = self.reference[i+1].freq - self.reference[i-1].freq
                delay = (-phase_change / (freq_change * 360)) * 10e8
                if not self.reflective:
                    delay /= 2
                self.groupDelayReference.append(delay)

        self.update()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name + " (ns)")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)

        if self.fixedValues:
            min_delay = self.minDisplayValue
            max_delay = self.maxDisplayValue
        elif self.data:
            min_delay = math.floor(np.min(self.groupDelay))
            max_delay = math.ceil(np.max(self.groupDelay))
        elif self.reference:
            min_delay = math.floor(np.min(self.groupDelayReference))
            max_delay = math.ceil(np.max(self.groupDelayReference))

        span = max_delay - min_delay
        if span == 0:
            span = 0.01
        self.minDelay = min_delay
        self.maxDelay = max_delay
        self.span = span

        tickcount = math.floor(self.chartHeight / 60)

        for i in range(tickcount):
            delay = min_delay + span * i / tickcount
            y = self.topMargin + round((self.maxDelay - delay) / self.span * self.chartHeight)
            if delay != min_delay and delay != max_delay:
                qp.setPen(QtGui.QPen(self.textColor))
                if delay != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(delay)))))
                    if digits == 0:
                        delaystr = str(round(delay))
                    else:
                        delaystr = str(round(delay, digits))
                else:
                    delaystr = "0"
                qp.drawText(3, y + 3, delaystr)
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5, self.topMargin, self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 5, str(max_delay))
        qp.drawText(3, self.chartHeight + self.topMargin, str(min_delay))

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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        self.drawFrequencyTicks(qp)

        color = self.sweepColor
        pen = QtGui.QPen(color)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.lineThickness)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.getXPosition(self.data[i])
            y = self.getYPositionFromDelay(self.groupDelay[i])
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.getXPosition(self.data[i - 1])
                prevy = self.getYPositionFromDelay(self.groupDelay[i - 1])
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

        color = self.referenceColor
        pen = QtGui.QPen(color)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.lineThickness)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            x = self.getXPosition(self.reference[i])
            y = self.getYPositionFromDelay(self.groupDelayReference[i])
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.getXPosition(self.reference[i - 1])
                prevy = self.getYPositionFromDelay(self.groupDelayReference[i - 1])
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

        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        # TODO: Find a faster way than these expensive "d in self.data" lookups
        if d in self.data:
            delay = self.groupDelay[self.data.index(d)]
        elif d in self.reference:
            delay = self.groupDelayReference[self.reference.index(d)]
        else:
            delay = 0
        return self.getYPositionFromDelay(delay)

    def getYPositionFromDelay(self, delay: float):
        return self.topMargin + round((self.maxDelay - delay) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxDelay)
        return [val]


class CapacitanceChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

        self.minValue = -1
        self.maxValue = 1
        self.span = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name + " (F)")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue / 10e11
            minValue = self.minDisplayValue / 10e11
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 1
            maxValue = -1
            for d in self.data:
                val = d.capacitiveEquivalent()
                if val > maxValue:
                    maxValue = val
                if val < minValue:
                    minValue = val
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                val = d.capacitiveEquivalent()
                if val > maxValue:
                    maxValue = val
                if val < minValue:
                    minValue = val
            self.maxValue = maxValue
            self.minValue = minValue

        span = maxValue - minValue
        if span == 0:
            logger.info("Span is zero for CapacitanceChart, setting to a small value.")
            span = 1e-15
        self.span = span

        target_ticks = math.floor(self.chartHeight / 60)
        fmt = Format(max_nr_digits=3)
        for i in range(target_ticks):
            val = minValue + (i / target_ticks) * span
            y = self.topMargin + round((self.maxValue - val) / self.span * self.chartHeight)
            qp.setPen(self.textColor)
            if val != minValue:
                valstr = str(Value(val, fmt=fmt))
                qp.drawText(3, y + 3, valstr)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(Value(maxValue, fmt=fmt)))
        qp.drawText(3, self.chartHeight+self.topMargin, str(Value(minValue, fmt=fmt)))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.capacitiveEquivalent()) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val * 10e11]

    def copy(self):
        new_chart: CapacitanceChart = super().copy()
        new_chart.span = self.span
        return new_chart


class InductanceChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = 0
        self.maxDisplayValue = 100

        self.minValue = -1
        self.maxValue = 1
        self.span = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name + " (H)")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
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

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue / 10e11
            minValue = self.minDisplayValue / 10e11
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 1
            maxValue = -1
            for d in self.data:
                val = d.inductiveEquivalent()
                if val > maxValue:
                    maxValue = val
                if val < minValue:
                    minValue = val
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                val = d.inductiveEquivalent()
                if val > maxValue:
                    maxValue = val
                if val < minValue:
                    minValue = val
            self.maxValue = maxValue
            self.minValue = minValue

        span = maxValue - minValue
        if span == 0:
            logger.info("Span is zero for CapacitanceChart, setting to a small value.")
            span = 1e-15
        self.span = span

        target_ticks = math.floor(self.chartHeight / 60)
        fmt = Format(max_nr_digits=3)
        for i in range(target_ticks):
            val = minValue + (i / target_ticks) * span
            y = self.topMargin + round((self.maxValue - val) / self.span * self.chartHeight)
            qp.setPen(self.textColor)
            if val != minValue:
                valstr = str(Value(val, fmt=fmt))
                qp.drawText(3, y + 3, valstr)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.chartWidth, y)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(Value(maxValue, fmt=fmt)))
        qp.drawText(3, self.chartHeight+self.topMargin, str(Value(minValue, fmt=fmt)))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.maxValue - d.inductiveEquivalent()) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val * 10e11]

    def copy(self):
        new_chart: InductanceChart = super().copy()
        new_chart.span = self.span
        return new_chart
