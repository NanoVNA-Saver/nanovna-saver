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
    def __init__(self, name=""):
        super().__init__()
        self.leftMargin = 30
        self.chartWidth = 360
        self.chartHeight = 360
        self.name = name

        self.setMinimumSize(self.chartWidth + 20 + self.leftMargin, self.chartHeight + 40)
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
        self.chartWidth = a0.size().width()-20-self.leftMargin
        self.chartHeight = min(a0.size().width()-40, a0.size().height()-40)
        self.update()

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        #qp.begin(self)  # Apparently not needed?
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, 20+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, 20+self.chartHeight, self.leftMargin+self.chartWidth, 20 + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0:
            return
        pen = QtGui.QPen(QtGui.QColor(220, 200, 30, 128))
        pen.setWidth(2)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(3)
        # Find scaling
        min = 100
        max = 0
        for i in range(len(self.data)):
            re = self.data[i].re
            im = self.data[i].im
            re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
            im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
            # Calculate the reflection coefficient
            mag = math.sqrt((re50-50)*(re50-50) + im50 * im50)/math.sqrt((re50+50)*(re50+50) + im50 * im50)
            logmag = -20 * math.log10(mag)
            if logmag > max:
                max = logmag
            if logmag < min:
                min = logmag
        min = 10*math.floor(min/10)
        max = 10*math.ceil(max/10)
        span = max-min
        for i in range(min, max, 10):
            y = 30 + round((i-min)/span*(self.chartHeight-10))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.setPen(QtCore.Qt.black)
        qp.drawText(3, 35, str(-min))
        qp.drawText(3, self.chartHeight+20, str(-max))
        # Draw frequency markers
        fstart = self.data[0].freq
        fstop = self.data[len(self.data)-1].freq
        fspan = fstop-fstart
        # At least 100 px between ticks
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, LogMagChart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(QtCore.Qt.black)
            qp.drawText(x-20, 20+self.chartHeight+15, LogMagChart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        qp.setPen(pen)
        for i in range(len(self.data)):
            re = self.data[i].re
            im = self.data[i].im
            re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
            im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
            # Calculate the reflection coefficient
            mag = math.sqrt((re50-50)*(re50-50) + im50 * im50)/math.sqrt((re50+50)*(re50+50) + im50 * im50)
            logmag = -20 * math.log10(mag)
            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((logmag-min)/span*(self.chartHeight-10))
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
                x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * m.location)
                y = 30 + round((logmag - min) / span * (self.chartHeight - 10))
                qp.drawPoint(int(x), int(y))

    def setValues(self, values, frequencies):
        self.values = values
        self.frequencies = frequencies
        self.update()

    def setData(self, data):
        self.data = data
        self.update()

    def setMarkers(self, markers):
        self.markers = markers

    @staticmethod
    def shortenFrequency(frequency):
        if frequency < 50000:
            return frequency
        if frequency < 5000000:
            return str(round(frequency / 1000)) + "k"
        return str(round(frequency / 1000000, 1)) + "M"