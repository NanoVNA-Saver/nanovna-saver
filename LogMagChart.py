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
from typing import List

from PyQt5 import QtWidgets, QtGui, QtCore

from Marker import Marker

Datapoint = collections.namedtuple('Datapoint', 'freq re im')

class LogMagChart(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.chartWidth = 360
        self.chartHeight = 360

        self.setMinimumSize(self.chartWidth + 40, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, QtGui.QColor("white"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.values = []
        self.frequencies = []
        self.data : List[Datapoint] = []
        self.markers : List[Marker] = []

        self.marker1Color = QtGui.QColor(255, 0, 20)
        self.marker2Color = QtGui.QColor(20, 0, 255)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = min(a0.size().width()-40, a0.size().height()-40)
        self.chartHeight = min(a0.size().width()-40, a0.size().height()-40)
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        #qp.begin(self)  # Apparently not needed?
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
        qp.drawLine(20, 20, 20, 20+self.chartHeight+5)
        qp.drawLine(15, 20+self.chartHeight, 20+self.chartWidth, 20 + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        pen = QtGui.QPen(QtGui.QColor(220, 200, 30, 128))
        pen.setWidth(2)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(3)
        qp.setPen(pen)
        for i in range(len(self.data)):
            re = self.data[i].re
            im = self.data[i].im
            re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
            im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
            # Calculate the reflection coefficient
            mag = math.sqrt((re50-50)*(re50-50) + im50 * im50)/math.sqrt((re50+50)*(re50+50) + im50 * im50)
            logmag = -20 * math.log10(mag)
            x = 21 + round(self.chartWidth/len(self.data) * i)
            y = 20 + round(logmag/100*self.chartHeight)
            qp.drawPoint(int(x), int(y))
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                re = self.data[m.location].re
                im = self.data[m.location].im
                re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
                im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
                # Calculate the reflection coefficient
                mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt(
                    (re50 + 50) * (re50 + 50) + im50 * im50)
                logmag = -20 * math.log10(mag)
                x = 21 + round(self.chartWidth/len(self.data) * m.location)
                y = 20 + round(logmag/100*self.chartHeight)
                print(m.name + ": Re:" + str(re) + " Im " + str(im) + " Mag: " + str(mag) + " Y: " + str(y))
                qp.drawPoint(int(x), int(y))

    def setValues(self, values, frequencies):
        print("### Updating values ###")
        self.values = values
        self.frequencies = frequencies
        self.update()

    def setData(self, data):
        print("### Updating data ###")
        self.data = data
        self.update()

    def setMarkers(self, markers):
        self.markers = markers