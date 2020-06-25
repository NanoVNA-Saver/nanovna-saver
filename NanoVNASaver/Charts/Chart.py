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
from typing import List, Set
import logging

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Marker import Marker
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

    def setSweepColor(self, color: QtGui.QColor):
        self.sweepColor = color
        self.update()

    def setSecondarySweepColor(self, color: QtGui.QColor):
        self.secondarySweepColor = color
        self.update()

    def setReferenceColor(self, color: QtGui.QColor):
        self.referenceColor = color
        self.update()

    def setSecondaryReferenceColor(self, color: QtGui.QColor):
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
        if frequency < 5000000:
            return str(round(frequency / 1000)) + "k"
        if frequency < 50000000:
            return str(round(frequency / 1000000, 2)) + "M"
        return str(round(frequency / 1000000, 1)) + "M"

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.RightButton:
            event.ignore()
            return
        if event.buttons() == QtCore.Qt.MiddleButton:
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
            if not QtCore.QFileInfo(filename).suffix():
                filename += ".png"
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
