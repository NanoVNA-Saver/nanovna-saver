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
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, NamedTuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QColorConstants

from NanoVNASaver import Defaults
from NanoVNASaver.Marker.Widget import Marker
from NanoVNASaver.RFTools import Datapoint

logger = logging.getLogger(__name__)


@dataclass
class ChartColors:  # pylint: disable=too-many-instance-attributes
    background: QColor = field(
        default_factory=lambda: QColor(QColorConstants.White)
    )
    foreground: QColor = field(
        default_factory=lambda: QColor(QColorConstants.LightGray)
    )
    reference: QColor = field(default_factory=lambda: QColor(0, 0, 255, 64))
    reference_secondary: QColor = field(
        default_factory=lambda: QColor(0, 0, 192, 48)
    )
    sweep: QColor = field(
        default_factory=lambda: QColor(QColorConstants.DarkYellow)
    )
    sweep_secondary: QColor = field(
        default_factory=lambda: QColor(QColorConstants.DarkMagenta)
    )
    swr: QColor = field(default_factory=lambda: QColor(255, 0, 0, 128))
    text: QColor = field(default_factory=lambda: QColor(QColorConstants.Black))
    bands: QColor = field(default_factory=lambda: QColor(128, 128, 128, 48))


class ChartPosition(NamedTuple):
    """just a point in the chart"""

    x: int
    y: int


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
    pos: ChartPosition = (-1, -1)
    pos_start: ChartPosition = (0, 0)
    state: bool = False
    move_x: int = -1
    move_y: int = -1


@dataclass
class ChartFlags:
    draw_lines: bool = False
    is_popout: bool = False


class ChartMarker(QtWidgets.QWidget):
    def __init__(self, qp: QtGui.QPaintDevice):
        super().__init__()
        self.qp = qp

    def draw(self, x: int, y: int, color: QtGui.QColor, text: str = ""):
        offset = int(Defaults.cfg.chart.marker_size // 2)
        if Defaults.cfg.chart.marker_at_tip:
            y -= offset
        pen = QtGui.QPen(color)
        self.qp.setPen(pen)
        qpp = QtGui.QPainterPath()
        qpp.moveTo(x, y + offset)
        qpp.lineTo(x - offset, y - offset)
        qpp.lineTo(x + offset, y - offset)
        qpp.lineTo(x, y + offset)

        if Defaults.cfg.chart.marker_filled:
            self.qp.fillPath(qpp, color)
        else:
            self.qp.drawPath(qpp)

        if text and Defaults.cfg.chart.marker_label:
            text_width = self.qp.fontMetrics().horizontalAdvance(text)
            self.qp.drawText(x - int(text_width // 2), y - 3 - offset, text)


class Chart(QtWidgets.QWidget):
    bands: ClassVar[Any] = None
    popout_requested: ClassVar[pyqtSignal] = pyqtSignal(object)
    color: ClassVar[ChartColors] = ChartColors()

    def __init__(self, name) -> None:
        super().__init__()
        self.name: str = name
        self.sweepTitle: str = ""

        self.leftMargin = 30
        self.rightMargin = 20
        self.bottomMargin = 20
        self.topMargin = 30

        self.dim = ChartDimensions()
        self.dragbox = ChartDragBox()
        self.flag = ChartFlags()

        self.draggedMarker = None

        self.data: list[Datapoint] = []
        self.reference: list[Datapoint] = []

        self.markers: list[Marker] = []
        self.swrMarkers: set[float] = set()

        self.action_popout = QAction("Popout chart")
        self.action_popout.triggered.connect(
            lambda: self.popout_requested.emit(self)
        )
        self.addAction(self.action_popout)

        self.action_save_screenshot = QAction("Save image")
        self.action_save_screenshot.triggered.connect(self.saveScreenshot)
        self.addAction(self.action_save_screenshot)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

    def setReference(self, data) -> None:
        self.reference = data
        self.update()

    def resetReference(self) -> None:
        self.reference = []
        self.update()

    def setData(self, data) -> None:
        self.data = data
        self.update()

    def setMarkers(self, markers) -> None:
        self.markers = markers

    def setBands(self, bands) -> None:
        self.bands = bands

    def setLineThickness(self, thickness) -> None:
        self.dim.line = thickness
        self.update()

    def setPointSize(self, size) -> None:
        self.dim.point = size
        self.update()

    def setMarkerSize(self, size) -> None:
        Defaults.cfg.chart.marker_size = size
        self.update()

    def setSweepTitle(self, title) -> None:
        self.sweepTitle = title
        self.update()

    def getActiveMarker(self) -> Marker:
        if self.draggedMarker is not None:
            return self.draggedMarker
        return next(
            (
                m
                for m in self.markers
                if m.isMouseControlledRadioButton.isChecked()
            ),
            None,
        )

    def getNearestMarker(self, x, y) -> None | Marker:
        if not self.data:
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

    def getPosition(self, d: Datapoint) -> tuple[int, int]:
        return self.getXPosition(d), self.getYPosition(d)

    def setDrawLines(self, draw_lines) -> None:
        self.flag.draw_lines = draw_lines
        self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.RightButton:
            event.ignore()
            return
        if event.buttons() == Qt.MouseButton.MiddleButton:
            # Drag event
            event.accept()
            self.dragbox.move_x = event.position().x()
            self.dragbox.move_y = event.position().y()
            return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            event.accept()
            self.dragbox.state = True
            self.dragbox.pos_start = (
                event.position().x(),
                event.position().y(),
            )
            return
        if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.draggedMarker = self.getNearestMarker(
                event.position().x(), event.position().y()
            )
        self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.draggedMarker = None
        if self.dragbox.state:
            self.zoomTo(
                self.dragbox.pos_start[0],
                self.dragbox.pos_start[1],
                a0.position().x(),
                a0.position().y(),
            )
            self.dragbox.state = False
            self.dragbox.pos = (-1, -1)
            self.dragbox.pos_start = (0, 0)
            self.update()

    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        delta = a0.angleDelta().y()
        if not delta or (not self.data and not self.reference):
            a0.ignore()
            return
        modifiers = a0.modifiers()

        zoom_x = modifiers != Qt.KeyboardModifier.ShiftModifier
        zoom_y = modifiers != Qt.KeyboardModifier.ControlModifier
        rate = -delta / 120
        # zooming in 10% increments and 9% complementary
        divisor = 10 if delta > 0 else 9

        factor_x = rate * self.dim.width / divisor if zoom_x else 0
        factor_y = rate * self.dim.height / divisor if zoom_y else 0

        abs_x = max(0, a0.position().x() - self.leftMargin)
        abs_y = max(0, a0.position().y() - self.topMargin)

        ratio_x = abs_x / self.dim.width
        ratio_y = abs_y / self.dim.height

        self.zoomTo(
            int(self.leftMargin + ratio_x * factor_x),
            int(self.topMargin + ratio_y * factor_y),
            int(self.leftMargin + self.dim.width - (1 - ratio_x) * factor_x),
            int(self.topMargin + self.dim.height - (1 - ratio_y) * factor_y),
        )
        a0.accept()

    def zoomTo(self, x1, y1, x2, y2):
        raise NotImplementedError()

    def saveScreenshot(self) -> None:
        logger.info("Saving %s to file...", self.name)
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Save image",
            filter="PNG (*.png);;All files (*.*)",
        )

        logger.debug("Filename: %s", filename)
        if not filename:
            return
        if not QtCore.QFileInfo(filename).suffix():
            filename += ".png"
        self.grab().save(filename)

    def copy(self) -> "Chart":
        new_chart = self.__class__(self.name)
        new_chart.data = self.data
        new_chart.reference = self.reference
        new_chart.dim = replace(self.dim)
        new_chart.flag = replace(self.flag)
        new_chart.markers = self.markers
        new_chart.swrMarkers = self.swrMarkers
        new_chart.bands = self.bands

        new_chart.resize(self.width(), self.height())
        new_chart.setPointSize(self.dim.point)
        new_chart.setLineThickness(self.dim.line)
        return new_chart

    def addSWRMarker(self, swr: float) -> None:
        self.swrMarkers.add(swr)
        self.update()

    def removeSWRMarker(self, swr: float) -> None:
        try:
            self.swrMarkers.remove(swr)
        except KeyError:
            logger.debug("KeyError from %s", self.name)
        finally:
            self.update()

    def clearSWRMarkers(self) -> None:
        self.swrMarkers.clear()
        self.update()

    @staticmethod
    def drawMarker(
        x: int, y: int, qp: QtGui.QPainter, color: QtGui.QColor, number: int = 0
    ) -> None:
        cmarker = ChartMarker(qp)
        cmarker.draw(x, y, color, f"{number}")

    def drawTitle(
        self, qp: QtGui.QPainter, position: QtCore.QPoint = None
    ) -> None:
        qp.setPen(Chart.color.text)
        if position is None:
            qf = QtGui.QFontMetricsF(self.font())
            width = qf.boundingRect(self.sweepTitle).width()
            position = QtCore.QPointF(self.width() / 2 - width / 2, 15)
        qp.drawText(position, self.sweepTitle)

    def update(self) -> None:
        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, Chart.color.background)
        self.setPalette(pal)
        super().update()
