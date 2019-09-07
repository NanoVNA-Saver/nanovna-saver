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
import math
from typing import List

from PyQt5 import QtWidgets, QtGui, QtCore

from .Marker import Marker
Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class Chart(QtWidgets.QWidget):
    sweepColor = QtCore.Qt.darkYellow
    referenceColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.blue)
    referenceColor.setAlpha(64)
    data: List[Datapoint] = []
    reference: List[Datapoint] = []
    markers: List[Marker] = []
    name = ""

    def setSweepColor(self, color : QtGui.QColor):
        self.sweepColor = color
        self.update()

    def setReferenceColor(self, color : QtGui.QColor):
        self.referenceColor = color
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

    @staticmethod
    def shortenFrequency(frequency):
        if frequency < 50000:
            return frequency
        if frequency < 5000000:
            return str(round(frequency / 1000)) + "k"
        return str(round(frequency / 1000000, 1)) + "M"


class PhaseChart(Chart):
    def __init__(self, name=""):
        super().__init__()
        self.leftMargin = 35
        self.chartWidth = 360
        self.chartHeight = 360
        self.name = name
        self.fstart = 0
        self.fstop = 0
        self.mouselocation = 0

        self.setMinimumSize(self.chartWidth + 20 + self.leftMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, QtGui.QColor("white"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.marker1Color = QtGui.QColor(255, 0, 20)
        self.marker2Color = QtGui.QColor(20, 0, 255)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-20-self.leftMargin
        self.chartHeight = a0.size().height()-40
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
        minAngle = -180
        maxAngle = 180
        span = maxAngle-minAngle
        for i in range(minAngle, maxAngle, 90):
            y = 30 + round((i-minAngle)/span*(self.chartHeight-10))
            if i != minAngle and i != maxAngle:
                qp.setPen(QtGui.QPen(QtGui.QColor("black")))
                qp.drawText(3, y+3, str(-i) + "°")
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.setPen(QtCore.Qt.black)
        qp.drawText(3, 35, str(-minAngle) + "°")
        qp.drawText(3, self.chartHeight+20, str(-maxAngle) + "°")

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if len(self.data) > 0:
            fstart = self.data[0].freq
            fstop = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop
        fspan = fstop-fstart
        minAngle = -180
        maxAngle = 180
        span = maxAngle-minAngle
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(QtCore.Qt.black)
            qp.drawText(x-20, 20+self.chartHeight+15, Chart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        if self.mouselocation != 0:
            qp.setPen(QtGui.QPen(QtGui.QColor(224,224,224)))
            x = self.leftMargin + 1 + round(self.chartWidth * (self.mouselocation - fstart) / fspan)
            qp.drawLine(x, 20, x, 20 + self.chartHeight +5)

        qp.setPen(pen)
        for i in range(len(self.data)):
            re = self.data[i].re
            im = self.data[i].im
            angle = math.degrees(math.atan2(im, re))
            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((angle-minAngle)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
        pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue

            re = self.reference[i].re
            im = self.reference[i].im
            angle = math.degrees(math.atan2(im, re))
            x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i].freq - fstart)/fspan)
            y = 30 + round((angle-minAngle)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                re = self.data[m.location].re
                im = self.data[m.location].im
                angle = math.degrees(math.atan2(im, re))
                x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * m.location)
                y = 30 + round((angle - minAngle) / span * (self.chartHeight - 10))
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)
                #qp.drawPoint(int(x), int(y))

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.mouseMoveEvent(a0)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        x = a0.x()
        absx = x - self.leftMargin
        if absx < 0 or absx > self.chartWidth:
            self.mouselocation = 0
            a0.ignore()
            return
        a0.accept()
        if self.fstop - self.fstart > 0:
            span = self.fstop - self.fstart
            step = span/self.chartWidth
            f = self.fstart + absx * step
#            self.mouselocation = f
            self.markers[0].setFrequency(str(round(f)))
        else:
            self.mouselocation = 0
        return


class VSWRChart(Chart):
    def __init__(self, name=""):
        super().__init__()
        self.leftMargin = 30
        self.chartWidth = 360
        self.chartHeight = 360
        self.name = name
        self.fstart = 0
        self.fstop = 0
        self.mouselocation = 0

        self.setMinimumSize(self.chartWidth + 20 + self.leftMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, QtGui.QColor("white"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.marker1Color = QtGui.QColor(255, 0, 20)
        self.marker2Color = QtGui.QColor(20, 0, 255)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.chartWidth = a0.size().width()-20-self.leftMargin
        self.chartHeight = a0.size().height()-40
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
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if len(self.data) > 0:
            fstart = self.data[0].freq
            fstop = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop
        fspan = fstop-fstart
        # Find scaling
        minVSWR = 1
        maxVSWR = 3
        for d in self.data:
            _, _, vswr = NanoVNASaver.vswr(d)
            if vswr > maxVSWR:
                maxVSWR = vswr
        maxVSWR = min(25, math.ceil(maxVSWR))
        span = maxVSWR-minVSWR
        ticksize = 1
        if span > 10 and span % 5 == 0:
            ticksize = 5
        elif span > 12 and span % 4 == 0:
            ticksize = 4
        elif span > 8 and span % 3 == 0:
            ticksize = 3
        elif span > 7 and span % 2 == 0:
            ticksize = 2

        for i in range(minVSWR, maxVSWR, ticksize):
            y = 30 + round((maxVSWR-i)/span*(self.chartHeight-10))
            if i != minVSWR and i != maxVSWR:
                qp.setPen(QtGui.QPen(QtGui.QColor("black")))
                qp.drawText(3, y+3, str(i))
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5, 30, self.leftMargin + self.chartWidth, 30)
        qp.setPen(QtCore.Qt.black)
        qp.drawText(3, 35, str(maxVSWR))
        qp.drawText(3, self.chartHeight+20, str(minVSWR))
        # At least 100 px between ticks
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(QtCore.Qt.black)
            qp.drawText(x-20, 20+self.chartHeight+15, Chart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        if self.mouselocation != 0:
            qp.setPen(QtGui.QPen(QtGui.QColor(224,224,224)))
            x = self.leftMargin + 1 + round(self.chartWidth * (self.mouselocation - fstart) / fspan)
            qp.drawLine(x, 20, x, 20 + self.chartHeight +5)

        qp.setPen(pen)
        for i in range(len(self.data)):
            _, _, vswr = NanoVNASaver.vswr(self.data[i])
            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((maxVSWR-vswr)/span*(self.chartHeight-10))
            if y < 30:
                continue
            qp.drawPoint(int(x), int(y))
        pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            _, _, vswr = NanoVNASaver.vswr(self.reference[i])
            x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i].freq - fstart)/fspan)
            y = 30 + round((maxVSWR - vswr) / span * (self.chartHeight - 10))
            if y < 30:
                continue
            qp.drawPoint(int(x), int(y))
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                _, _, vswr = NanoVNASaver.vswr(self.data[m.location])
                x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * m.location)
                y = 30 + round((maxVSWR-vswr) / span * (self.chartHeight - 10))
                if y < 30:
                    continue
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)
                #qp.drawPoint(int(x), int(y))

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.mouseMoveEvent(a0)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        x = a0.x()
        absx = x - self.leftMargin
        if absx < 0 or absx > self.chartWidth:
            self.mouselocation = 0
            a0.ignore()
            return
        a0.accept()
        if self.fstop - self.fstart > 0:
            span = self.fstop - self.fstart
            step = span/self.chartWidth
            f = self.fstart + absx * step
#            self.mouselocation = f
            self.markers[0].setFrequency(str(round(f)))
        else:
            self.mouselocation = 0
        return


class PolarChart(Chart):
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
        self.drawChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawChart(self, qp: QtGui.QPainter):
        centerX = int(self.width()/2)
        centerY = int(self.height()/2)
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
        qp.drawEllipse(QtCore.QPoint(centerX, centerY), int(self.chartWidth/2), int(self.chartHeight/2))
        qp.drawEllipse(QtCore.QPoint(centerX, centerY), int(self.chartWidth/4), int(self.chartHeight/4))
        qp.drawLine(centerX - int(self.chartWidth/2), centerY, centerX + int(self.chartWidth/2), centerY)
        qp.drawLine(centerX, centerY - int(self.chartHeight/2), centerX, centerY + int(self.chartHeight/2))

        qp.drawLine(centerX + int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY + int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerX - int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY - int(self.chartHeight / 2 * math.sin(math.pi / 4)))

        qp.drawLine(centerX + int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY - int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerX - int(self.chartHeight / 2 * math.sin(math.pi / 4)),
                    centerY + int(self.chartHeight / 2 * math.sin(math.pi / 4)))

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
