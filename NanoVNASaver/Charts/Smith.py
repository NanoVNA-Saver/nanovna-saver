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
from PyQt5 import QtGui, QtCore

from NanoVNASaver import Defaults
from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Square import SquareChart

logger = logging.getLogger(__name__)


class SmithChart(SquareChart):
    def drawChart(self, qp: QtGui.QPainter) -> None:
        centerX = int(self.width()/2)
        centerY = int(self.height()/2)
        qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.text))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.foreground))
        qp.drawEllipse(QtCore.QPoint(centerX, centerY),
                       int(self.dim.width / 2),
                       int(self.dim.height / 2))
        qp.drawLine(
            centerX - int(self.dim.width / 2),
            centerY,
            centerX + int(self.dim.width / 2),
            centerY)

        qp.drawEllipse(QtCore.QPoint(centerX + int(self.dim.width/4), centerY),
                       int(self.dim.width/4), int(self.dim.height/4))  # Re(Z) = 1
        qp.drawEllipse(QtCore.QPoint(centerX + int(2/3*self.dim.width/2), centerY),
                       int(self.dim.width/6), int(self.dim.height/6))  # Re(Z) = 2
        qp.drawEllipse(QtCore.QPoint(centerX + int(3 / 4 * self.dim.width / 2), centerY),
                       int(self.dim.width / 8), int(self.dim.height / 8))  # Re(Z) = 3
        qp.drawEllipse(QtCore.QPoint(centerX + int(5 / 6 * self.dim.width / 2), centerY),
                       int(self.dim.width / 12), int(self.dim.height / 12))  # Re(Z) = 5

        qp.drawEllipse(QtCore.QPoint(centerX + int(1 / 3 * self.dim.width / 2), centerY),
                       int(self.dim.width / 3), int(self.dim.height / 3))  # Re(Z) = 0.5
        qp.drawEllipse(QtCore.QPoint(centerX + int(1 / 6 * self.dim.width / 2), centerY),
                       int(self.dim.width / 2.4), int(self.dim.height / 2.4))  # Re(Z) = 0.2

        qp.drawArc(centerX + int(3/8*self.dim.width), centerY, int(self.dim.width/4),
                   int(self.dim.width/4), 90*16, 152*16)  # Im(Z) = -5
        qp.drawArc(centerX + int(3/8*self.dim.width), centerY, int(self.dim.width/4),
                   -int(self.dim.width/4), -90 * 16, -152 * 16)  # Im(Z) = 5
        qp.drawArc(centerX + int(self.dim.width/4), centerY, int(self.dim.width/2),
                   int(self.dim.height/2), 90*16, 127*16)  # Im(Z) = -2
        qp.drawArc(centerX + int(self.dim.width/4), centerY, int(self.dim.width/2),
                   -int(self.dim.height/2), -90*16, -127*16)  # Im(Z) = 2
        qp.drawArc(centerX, centerY,
                   self.dim.width, self.dim.height,
                   90*16, 90*16)  # Im(Z) = -1
        qp.drawArc(centerX, centerY,
                   self.dim.width, -self.dim.height,
                   -90 * 16, -90 * 16)  # Im(Z) = 1
        qp.drawArc(centerX - int(self.dim.width / 2), centerY,
                   self.dim.width * 2, self.dim.height * 2,
                   int(99.5*16), int(43.5*16))  # Im(Z) = -0.5
        qp.drawArc(centerX - int(self.dim.width / 2), centerY,
                   self.dim.width * 2, -self.dim.height * 2,
                   int(-99.5 * 16), int(-43.5 * 16))  # Im(Z) = 0.5
        qp.drawArc(centerX - self.dim.width * 2, centerY,
                   self.dim.width * 5, self.dim.height * 5,
                   int(93.85 * 16), int(18.85 * 16))  # Im(Z) = -0.2
        qp.drawArc(centerX - self.dim.width*2, centerY,
                   self.dim.width*5, -self.dim.height*5,
                   int(-93.85 * 16), int(-18.85 * 16))  # Im(Z) = 0.2

        self.drawTitle(qp)

        qp.setPen(Defaults.cfg.chart_colors.swr)
        for swr in self.swrMarkers:
            if swr <= 1:
                continue
            gamma = (swr - 1)/(swr + 1)
            r = round(gamma * self.dim.width/2)
            qp.drawEllipse(QtCore.QPoint(centerX, centerY), r, r)
            qp.drawText(
                QtCore.QRect(centerX - 50, centerY - 4 + r, 100, 20),
                QtCore.Qt.AlignCenter, str(swr))

    def zoomTo(self, x1, y1, x2, y2):
        raise NotImplementedError()
