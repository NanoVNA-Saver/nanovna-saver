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


class PolarChart(SquareChart):
    def drawChart(self, qp: QtGui.QPainter):
        center_x = int(self.width()/2)
        center_y = int(self.height()/2)
        width_2 = int(self.dim.width / 2)
        height_2 = int(self.dim.height / 2)         
        width_45 = width_2 * 0.7071
        height_45 = height_2 * 0.7071

        qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.text))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.foreground))

        qp.drawEllipse(QtCore.QPoint(center_x, center_y), width_2, height_2)
        qp.drawEllipse(QtCore.QPoint(center_x, center_y),
                       width_2 // 2, height_2 // 2)

        qp.drawLine(center_x - width_2, center_y, center_x + width_2, center_y)
        qp.drawLine(center_x, center_y - height_2,
                    center_x, center_y + height_2)

        qp.drawLine(center_x + width_45, center_y + height_45,
                    center_x - width_45, center_y - height_45)
        qp.drawLine(center_x + width_45, center_y - height_45,
                    center_x - width_45, center_y + height_45)

        self.drawTitle(qp)

    def zoomTo(self, x1, y1, x2, y2):
        raise NotImplementedError()
