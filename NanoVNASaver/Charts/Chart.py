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
    reference: QtGui.QColor = QtGui.QColor(0, 0, 255, 64)
    reference_secondary: QtGui.QColor = QtGui.QColor(0, 0, 192, 48)
    sweep: QtGui.QColor =  QtGui.QColor(QtCore.Qt.darkYellow)
    sweep_secondary: QtGui.QColor = QtGui.QColor(QtCore.Qt.darkMagenta)
    swr: QtGui.QColor = QtGui.QColor(255, 0, 0, 128)
    text: QtGui.QColor = QtGui.QColor(QtCore.Qt.black)
    bands: QtGui.QColor = QtGui.QColor(128, 128, 128, 48)

@dataclass
class ChartDimensions:
    height: int = 200
    height_min: int = 200
    width: int = 200
    width_min: int = 200
    line: int = 1
    point: int = 2

@dataclass
class ChartDragBox:
    pos: Tuple[int]  = (-1, -1)
    pos_start: Tuple[int] = (0, 0)
    state: bool = False
    move_x: int = -1
    move_y: int = -1

@dataclass
class ChartFlags:
    draw_lines: bool = False
    is_popout: bool = False

@dataclass
class ChartMarkerConfig:
    draw_label: bool = False
    fill: bool = False
    at_tip: bool = False
    size: int = 3

class ChartMarker(QtWidgets.QWidget):
    cfg: ClassVar[ChartMarkerConfig] = ChartMarkerConfig()

    def __init__(self, qp: QtGui.QPaintDevice):
        super().__init__()
        self.qp = qp

    def draw(self, x: int, y: int, color: QtGui.QColor, text: str = ""):
        offset = self.cfg.size // 2
        if self.cfg.at_tip:
            y -= offset
        pen = QtGui.QPen(color)
        self.qp.setPen(pen)
        qpp = QtGui.QPainterPath()
        qpp.moveTo(x, y + offset)
        qpp.lineTo(x - offset, y - offset)
        qpp.lineTo(x + offset, y - offset)
        qpp.lineTo(x, y + offset)

        if self.cfg.fill:
            self.qp.fillPath(qpp, color)
        else:
            self.qp.drawPath(qpp)

        if text and self.cfg.draw_label:
            text_width = self.qp.fontMetrics().horizontalAdvance(text)
            self.qp.drawText(x - text_width // 2, y - 3 - offset, text)


class Chart(QtWidgets.QWidget):
    bands: ClassVar[Any] = None
    popoutRequested: ClassVar[Any] = pyqtSignal(object)
    color: ClassVar[ChartColors] = ChartColors()
    marker_cfg: ClassVar[ChartMarkerConfig] = ChartMarkerConfig()

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.sweepTitle = ""

        self.dim = ChartDimensions()
        self.dragbox = ChartDragBox()
        self.flag = ChartFlags()

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
        ChartMarker.cfg.size = size
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
            distance = abs(complex(x - mx, y - my))
            if distance < shortest:
                shortest = distance
                nearest = m
        return nearest

    def getPosition(self, d: Datapoint) -> Tuple[int, int]:
        return self.getXPosition(d), self.getYPosition(d)

    def setDrawLines(self, draw_lines):
        self.flag.draw_lines = draw_lines
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

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent):
        self.draggedMarker = None
        if self.dragbox.state:
            self.zoomTo(self.dragbox.pos_start[0], self.dragbox.pos_start[1], a0.x(), a0.y())
            self.dragbox.state = False
            self.dragbox.pos = (-1, -1)
            self.dragbox.pos_start = (0, 0)
            self.update()

    def zoomTo(self, x1, y1, x2, y2):
        raise NotImplementedError()

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
        new_chart.dim = replace(self.dim)
        new_chart.flag = replace(self.flag)
        new_chart.marker_cfg = replace(self.marker_cfg)
        new_chart.markers = self.markers
        new_chart.swrMarkers = self.swrMarkers
        new_chart.bands = self.bands

        new_chart.resize(self.width(), self.height())
        new_chart.setPointSize(self.dim.point)
        new_chart.setLineThickness(self.dim.line)
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

    def drawMarker(self, x, y, qp: QtGui.QPainter, color: QtGui.QColor, number=0):
        cmarker = ChartMarker(qp)
        cmarker.draw(x, y, color, str(number))

    def drawTitle(self, qp: QtGui.QPainter, position: QtCore.QPoint = None):
        if not self.sweepTitle:
            return
        qp.setPen(Chart.color.text)
        if position is None:
            qf = QtGui.QFontMetricsF(self.font())
            width = qf.boundingRect(self.sweepTitle).width()
            position = QtCore.QPointF(self.width()/2 - width/2, 15)
        qp.drawText(position, self.sweepTitle)

    def update(self):
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background, Chart.color.background)
        self.setPalette(pal)
        super().update()
