#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020 Rune B. Broberg
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

from PyQt6 import QtCore, QtGui

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Square import SquareChart

logger = logging.getLogger(__name__)


class SmithChart(SquareChart):
    def drawChart(self, qp: QtGui.QPainter) -> None:
        center_x = self.width() // 2
        center_y = self.height() // 2
        width_2 = self.dim.width // 2
        height_2 = self.dim.height // 2
        qp.setPen(QtGui.QPen(Chart.color.text))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawEllipse(QtCore.QPoint(center_x, center_y), width_2, height_2)
        qp.drawLine(center_x - width_2, center_y, center_x + width_2, center_y)

        qp.drawEllipse(
            QtCore.QPoint(center_x + int(self.dim.width / 4), center_y),
            self.dim.width // 4,
            self.dim.height // 4,
        )  # Re(Z) = 1
        qp.drawEllipse(
            QtCore.QPoint(center_x + self.dim.width // 3, center_y),
            self.dim.width // 6,
            self.dim.height // 6,
        )  # Re(Z) = 2
        qp.drawEllipse(
            QtCore.QPoint(center_x + 3 * self.dim.width // 8, center_y),
            self.dim.width // 8,
            self.dim.height // 8,
        )  # Re(Z) = 3
        qp.drawEllipse(
            QtCore.QPoint(center_x + 5 * self.dim.width // 12, center_y),
            self.dim.width // 12,
            self.dim.height // 12,
        )  # Re(Z) = 5
        qp.drawEllipse(
            QtCore.QPoint(center_x + self.dim.width // 6, center_y),
            self.dim.width // 3,
            self.dim.height // 3,
        )  # Re(Z) = 0.5
        qp.drawEllipse(
            QtCore.QPoint(center_x + self.dim.width // 12, center_y),
            5 * self.dim.width // 12,
            5 * self.dim.height // 12,
        )  # Re(Z) = 0.2

        qp.drawArc(
            center_x + 3 * self.dim.width // 8,
            center_y,
            self.dim.width // 4,
            self.dim.width // 4,
            90 * 16,
            152 * 16,
        )  # Im(Z) = -5
        qp.drawArc(
            center_x + 3 * self.dim.width // 8,
            center_y,
            self.dim.width // 4,
            -self.dim.width // 4,
            -90 * 16,
            -152 * 16,
        )  # Im(Z) = 5
        qp.drawArc(
            center_x + self.dim.width // 4,
            center_y,
            width_2,
            height_2,
            90 * 16,
            127 * 16,
        )  # Im(Z) = -2
        qp.drawArc(
            center_x + self.dim.width // 4,
            center_y,
            width_2,
            -height_2,
            -90 * 16,
            -127 * 16,
        )  # Im(Z) = 2
        qp.drawArc(
            center_x,
            center_y,
            self.dim.width,
            self.dim.height,
            90 * 16,
            90 * 16,
        )  # Im(Z) = -1
        qp.drawArc(
            center_x,
            center_y,
            self.dim.width,
            -self.dim.height,
            -90 * 16,
            -90 * 16,
        )  # Im(Z) = 1
        qp.drawArc(
            center_x - width_2,
            center_y,
            self.dim.width * 2,
            self.dim.height * 2,
            int(99.5 * 16),
            int(43.5 * 16),
        )  # Im(Z) = -0.5
        qp.drawArc(
            center_x - width_2,
            center_y,
            self.dim.width * 2,
            -self.dim.height * 2,
            int(-99.5 * 16),
            int(-43.5 * 16),
        )  # Im(Z) = 0.5
        qp.drawArc(
            center_x - self.dim.width * 2,
            center_y,
            self.dim.width * 5,
            self.dim.height * 5,
            int(93.85 * 16),
            int(18.85 * 16),
        )  # Im(Z) = -0.2
        qp.drawArc(
            center_x - self.dim.width * 2,
            center_y,
            self.dim.width * 5,
            -self.dim.height * 5,
            int(-93.85 * 16),
            int(-18.85 * 16),
        )  # Im(Z) = 0.2

        self.drawTitle(qp)

        qp.setPen(Chart.color.swr)
        for swr in self.swrMarkers:
            if swr <= 1:
                continue
            gamma = (swr - 1) / (swr + 1)
            r = int(gamma * self.dim.width / 2)
            qp.drawEllipse(QtCore.QPoint(center_x, center_y), r, r)
            qp.drawText(
                QtCore.QRect(center_x - 50, center_y - 4 + r, 100, 20),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                f"{swr}",
            )
