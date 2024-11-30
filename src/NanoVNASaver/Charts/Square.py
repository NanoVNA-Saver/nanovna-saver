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

from PyQt6 import QtCore, QtGui, QtWidgets

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.RFTools import Datapoint

logger = logging.getLogger(__name__)


class SquareChart(Chart):
    def __init__(self, name=""):
        super().__init__(name)
        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        self.setSizePolicy(sizepolicy)
        self.dim.width = 250
        self.dim.height = 250
        self.setMinimumSize(self.dim.width + 40, self.dim.height + 40)

        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, Chart.color.background)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def paintEvent(self, _: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter) -> None:
        raise NotImplementedError()

    def draw_data(
        self,
        qp: QtGui.QPainter,
        color: QtGui.QColor,
        data: list[Datapoint],
        fstart: int = 0,
        fstop: int = 0,
    ):
        if not data:
            return
        fstop = fstop or data[-1].freq
        pen = QtGui.QPen(color)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.dim.line)

        qp.setPen(pen)
        prev_x = self.getXPosition(data[0])
        prev_y = int(self.height() / 2 + data[0].im * -1 * self.dim.height / 2)
        for i, d in enumerate(data):
            x = self.getXPosition(d)
            y = int(self.height() / 2 + d.im * -1 * self.dim.height / 2)
            if d.freq > fstart and d.freq < fstop:
                qp.drawPoint(x, y)
                if self.flag.draw_lines and i > 0:
                    qp.setPen(line_pen)
                    qp.drawLine(x, y, prev_x, prev_y)
                    qp.setPen(pen)
            prev_x, prev_y = x, y

    def drawValues(self, qp: QtGui.QPainter):
        if not (self.data or self.reference):
            return
        self.draw_data(qp, Chart.color.sweep, self.data)

        fstart = self.data[0].freq if self.data else 0
        fstop = self.data[-1].freq if self.data else 0
        self.draw_data(qp, Chart.color.reference, self.reference, fstart, fstop)

        for m in self.markers:
            if m.location != -1 and m.location < len(self.data):
                x = self.getXPosition(self.data[m.location])
                y = int(
                    self.height() // 2
                    - self.data[m.location].im * self.dim.height // 2
                )
                self.drawMarker(x, y, qp, m.color, self.markers.index(m) + 1)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if not self.flag.is_popout:
            self.setFixedWidth(a0.size().height())
            self.dim.width = a0.size().height() - 40
            self.dim.height = a0.size().height() - 40
        else:
            min_dimension = min(a0.size().height(), a0.size().width())
            self.dim.width = self.dim.height = min_dimension - 40
        self.update()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent):
        if a0.buttons() == QtCore.Qt.MouseButton.RightButton:
            a0.ignore()
            return

        x = a0.position().x()
        y = a0.position().y()
        absx = x - (self.width() - self.dim.width) / 2
        absy = y - (self.height() - self.dim.height) / 2
        if (
            absx < 0
            or absx > self.dim.width
            or absy < 0
            or absy > self.dim.height
            or (not self.data and not self.reference)
        ):
            a0.ignore()
            return
        a0.accept()

        target = self.data or self.reference
        positions = []

        dim_x_2 = self.dim.width / 2
        dim_y_2 = self.dim.height / 2
        width_2 = self.width() / 2
        height_2 = self.height() / 2

        positions = [
            math.sqrt(
                (x - (width_2 + d.re * dim_x_2)) ** 2
                + (y - (height_2 - d.im * dim_y_2)) ** 2
            )
            for d in target
        ]

        minimum_position = positions.index(min(positions))
        if m := self.getActiveMarker():
            m.setFrequency(str(round(target[minimum_position].freq)))

    def getXPosition(self, d: Datapoint) -> int:
        return int(self.width() / 2 + d.re * self.dim.width / 2)

    def getYPosition(self, d: Datapoint) -> int:
        return int(self.height() / 2 + d.im * -1 * self.dim.height / 2)

    def zoomTo(self, x1, y1, x2, y2):
        pass
