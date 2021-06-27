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
import math

from dataclasses import dataclass, replace
from typing import List, Set, Tuple, ClassVar, Any

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Marker import Marker

logger = logging.getLogger(__name__)

@dataclass
class ChartColors:  # pylint: disable=too-many-instance-attributes
    background: QtGui.QColor = QtGui.QColor(QtCore.Qt.white)
    foreground: QtGui.QColor = QtGui.QColor(QtCore.Qt.lightGray)
    reference: QtGui.QColor = QtGui.QColor(QtCore.Qt.blue).setAlpha(64)
    reference_secondary: QtGui.QColor = QtGui.QColor(QtCore.Qt.blue).setAlpha(64)
    sweep: QtGui.QColor = QtCore.Qt.darkYellow
    sweep_secondary: QtGui.QColor = QtCore.Qt.darkMagenta
    swr: QtGui.QColor = QtGui.QColor(QtCore.Qt.red).setAlpha(128)
    text: QtGui.QColor = QtGui.QColor(QtCore.Qt.black)

@dataclass
class ChartDimensions:
    height: int = 200
    height_min: int = 200
    width: int = 200
    width_min: int = 200
    line: int = 1
    marker: int = 3
    point: int = 2

@dataclass
class ChartDragBox:
    pos: Tuple[int]  = (-1, -1)
    pos_start: Tuple[int] = (0, 0)
    state: bool = False
    move_x: int = -1
    move_y: int = -1

@dataclass
class ChartMarkerFlags:
    draw_numbers: bool = False
    filled: bool = False
    at_tip: bool = False

@dataclass
class ChartFlags:
    draw_lines: bool = False
    is_popout: bool = False

class Chart(QtWidgets.QWidget):
    bands: ClassVar[Any] = None
    popoutRequested: ClassVar[Any] = pyqtSignal(object)

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.sweepTitle = ""

        self.color = ChartColors()
        self.dim = ChartDimensions()
        self.dragbox = ChartDragBox()
        self.flag = ChartFlags()
        self.marker_flag = ChartMarkerFlags()

        self.draggedMarker = None

        self.data: List[Datapoint] = []
        self.reference: List[Datapoint] = []

        self.markers: List[Marker] = []
        self.swrMarkers: Set[float] = set()

        self.action_popout = QtWidgets.QAction("Popout chart")
        self.action_popout.triggered.connect(lambda: self.popoutRequested.emit(self))
        self.addAction(self.action_popout)

        self.action_save_screenshot = QtWidgets.QAction("Save image")
        self.action_save_screenshot.triggered.connect(self.saveScreenshot)
        self.addAction(self.action_save_screenshot)

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def setSweepColor(self, color: QtGui.QColor):
        self.color.sweep = color
        self.update()

    def setSecondarySweepColor(self, color: QtGui.QColor):
        self.color.sweep_secondary = color
        self.update()

    def setReferenceColor(self, color: QtGui.QColor):
        self.color.reference = color
        self.update()

    def setSecondaryReferenceColor(self, color: QtGui.QColor):
        self.color.reference_secondary = color
        self.update()

    def setBackgroundColor(self, color: QtGui.QColor):
        self.color.background = color
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background, color)
        self.setPalette(pal)
        self.update()

    def setForegroundColor(self, color: QtGui.QColor):
        self.color.foreground = color
        self.update()

    def setTextColor(self, color: QtGui.QColor):
        self.color.text = color
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
        self.dim.line = thickness
        self.update()

    def setPointSize(self, size):
        self.dim.point = size
        self.update()

    def setMarkerSize(self, size):
        self.dim.marker = size
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

    # pylint: disable=no-self-use
    def getYPosition(self, _: Datapoint) -> int:
        return 0

    # pylint: disable=no-self-use
    def getXPosition(self, _: Datapoint) -> int:
        return 0

    def getPosition(self, d: Datapoint) -> Tuple[int, int]:
        return self.getXPosition(d), self.getYPosition(d)

    def setDrawLines(self, draw_lines):
        self.flag.draw_lines = draw_lines
        self.update()

    def setDrawMarkerNumbers(self, draw_marker_numbers):
        self.marker_flag.draw_numbers = draw_marker_numbers
        self.update()

    def setMarkerAtTip(self, marker_at_tip):
        self.marker_flag.at_tip = marker_at_tip
        self.update()

    def setFilledMarkers(self, filled_markers):
        self.marker_flag.filled = filled_markers
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.RightButton:
            event.ignore()
            return
        if event.buttons() == QtCore.Qt.MiddleButton:
            # Drag event
            event.accept()
            self.dragbox.move_x = event.x()
            self.dragbox.move_y = event.y()
            return
        if event.modifiers() == QtCore.Qt.ControlModifier:
            event.accept()
            self.dragbox.state = True
            self.dragbox.pos_start = (event.x(), event.y())
            return
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            self.draggedMarker = self.getNearestMarker(event.x(), event.y())
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.draggedMarker = None
        if self.dragbox.state:
            self.zoomTo(self.dragbox.pos_start[0], self.dragbox.pos_start[1], a0.x(), a0.y())
            self.dragbox.state = False
            self.dragbox.pos = (-1, -1)
            self.dragbox.pos_start = (0, 0)
            self.update()

    def zoomTo(self, x1, y1, x2, y2):
        pass

    def saveScreenshot(self):
        logger.info("Saving %s to file...", self.name)
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption="Save image",
            filter="PNG (*.png);;All files (*.*)")

        logger.debug("Filename: %s", filename)
        if not filename:
            return
        if not QtCore.QFileInfo(filename).suffix():
            filename += ".png"
        self.grab().save(filename)

    def copy(self):
        new_chart = self.__class__(self.name)
        new_chart.data = self.data
        new_chart.reference = self.reference
        new_chart.color = replace(self.color)
        new_chart.dim = replace(self.dim)
        new_chart.flag = replace(self.flag)
        new_chart.marker_flag = replace(self.marker_flag)
        new_chart.markers = self.markers
        new_chart.swrMarkers = self.swrMarkers
        new_chart.bands = self.bands

        new_chart.resize(self.width(), self.height())
        new_chart.setPointSize(self.dim.point)
        new_chart.setLineThickness(self.dim.line)
        new_chart.setBackgroundColor(self.color.background)
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
        self.color.swr = color
        self.update()

    def drawMarker(self, x, y, qp: QtGui.QPainter, color: QtGui.QColor, number=0):
        if self.marker_flag.at_tip:
            y -= self.dim.marker
        pen = QtGui.QPen(color)
        qp.setPen(pen)
        qpp = QtGui.QPainterPath()
        qpp.moveTo(x, y + self.dim.marker)
        qpp.lineTo(x - self.dim.marker, y - self.dim.marker)
        qpp.lineTo(x + self.dim.marker, y - self.dim.marker)
        qpp.lineTo(x, y + self.dim.marker)

        if self.marker_flag.filled:
            qp.fillPath(qpp, color)
        else:
            qp.drawPath(qpp)

        if self.marker_flag.draw_numbers:
            number_x = x - 3
            number_y = y - self.dim.marker - 3
            qp.drawText(number_x, number_y, str(number))

    def drawTitle(self, qp: QtGui.QPainter, position: QtCore.QPoint = None):
        if not self.sweepTitle:
            return
        qp.setPen(self.color.text)
        if position is None:
            qf = QtGui.QFontMetricsF(self.font())
            width = qf.boundingRect(self.sweepTitle).width()
            position = QtCore.QPointF(self.width()/2 - width/2, 15)
        qp.drawText(position, self.sweepTitle)
