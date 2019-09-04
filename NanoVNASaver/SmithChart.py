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
from typing import List

from PyQt5 import QtWidgets, QtGui, QtCore

from .Chart import Chart
from .Marker import Marker

Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class SmithChart(Chart):
    def __init__(self, name=""):
        super().__init__()
        self.chartWidth = 360
        self.chartHeight = 36

        self.name = name

        self.setMinimumSize(self.chartWidth + 40, self.chartHeight + 40)
        sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)
        sizepolicy.setHeightForWidth(True)
        self.setSizePolicy(sizepolicy)
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, QtGui.QColor("white"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.marker1Color = QtGui.QColor(255, 0, 20)
        self.marker2Color = QtGui.QColor(20, 0, 255)
        self.sweepColor   = QtGui.QColor(220, 200, 30, 128)
        self.sweepColor = QtGui.QColor(50, 50, 200, 64)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = min(a0.size().width()-40, a0.size().height()-40)
        self.chartHeight = min(a0.size().width()-40, a0.size().height()-40)
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        #qp.begin(self)  # Apparently not needed?
        self.drawSmithChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawSmithChart(self, qp: QtGui.QPainter):
        centerX = int(self.width()/2)
        centerY = int(self.height()/2)
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
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
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.width()/2 + self.data[i].re * self.chartWidth/2
            y = self.height()/2 + self.data[i].im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
        pen.setColor(self.referenceColor)
        qp.setPen(pen)
        if len(self.data) > 0:
            fstart = self.data[0].freq
            fstop  = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop  = self.reference[len(self.reference)-1].freq
        for data in self.reference:
            if data.freq < fstart or data.freq > fstop:
                continue
            x = self.width()/2 + data.re * self.chartWidth/2
            y = self.height()/2 + data.im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
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

    def heightForWidth(self, a0: int) -> int:
        return a0
