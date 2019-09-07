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
    backgroundColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.white)
    textColor: QtGui.QColor = QtGui.QColor(QtCore.Qt.black)
    data: List[Datapoint] = []
    reference: List[Datapoint] = []
    markers: List[Marker] = []
    name = ""
    drawLines = False

    def setSweepColor(self, color : QtGui.QColor):
        self.sweepColor = color
        self.update()

    def setReferenceColor(self, color : QtGui.QColor):
        self.referenceColor = color
        self.update()

    def setBackgroundColor(self, color: QtGui.QColor):
        self.backgroundColor = color
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background, color)
        self.setPalette(pal)
        self.update()

    def setTextColor(self, color: QtGui.QColor):
        self.textColor = color
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

    def setDrawLines(self, drawLines):
        self.drawLines = drawLines
        self.update()

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
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
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
        qp.setPen(QtGui.QPen(self.textColor))
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
                qp.setPen(QtGui.QPen(self.textColor))
                qp.drawText(3, y+3, str(-i) + "°")
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.setPen(self.textColor)
        qp.drawText(3, 35, str(-minAngle) + "°")
        qp.drawText(3, self.chartHeight+20, str(-maxAngle) + "°")

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
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
            qp.setPen(self.textColor)
            qp.drawText(x-20, 20+self.chartHeight+15, Chart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        if self.mouselocation != 0:
            qp.setPen(QtGui.QPen(QtGui.QColor(224,224,224)))
            x = self.leftMargin + 1 + round(self.chartWidth * (self.mouselocation - fstart) / fspan)
            qp.drawLine(x, 20, x, 20 + self.chartHeight +5)

        qp.setPen(pen)
        for i in range(len(self.data)):
            angle = self.angle(self.data[i])
            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((angle-minAngle)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                angle = self.angle(self.data[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth / len(self.data) * (i-1))
                prevy = 30 + round((angle - minAngle) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            angle = self.angle(self.reference[i])
            x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i].freq - fstart)/fspan)
            y = 30 + round((angle-minAngle)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                angle = self.angle(self.reference[i-1])
                prevx = x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i-1].freq - fstart)/fspan)
                prevy = 30 + round((angle - minAngle) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                angle = self.angle(self.data[m.location])
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

    @staticmethod
    def angle(d: Datapoint) -> float:
        re = d.re
        im = d.im
        return math.degrees(math.atan2(im, re))


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
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
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
        qp.setPen(QtGui.QPen(self.textColor))
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
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
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
                qp.setPen(self.textColor)
                qp.drawText(3, y+3, str(i))
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.drawLine(self.leftMargin - 5, 30, self.leftMargin + self.chartWidth, 30)
        qp.setPen(self.textColor)
        qp.drawText(3, 35, str(maxVSWR))
        qp.drawText(3, self.chartHeight+20, str(minVSWR))
        # At least 100 px between ticks
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, Chart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(self.textColor)
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
            if self.drawLines and i > 0:
                _, _, vswr = NanoVNASaver.vswr(self.data[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth / len(self.data) * (i-1))
                prevy = 30 + round((maxVSWR - vswr) / span * (self.chartHeight - 10))
                if prevy < 30:
                    continue
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
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
            if self.drawLines and i > 0:
                _, _, vswr = NanoVNASaver.vswr(self.reference[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i-1].freq - fstart)/fspan)
                prevy = 30 + round((maxVSWR - vswr) / span * (self.chartHeight - 10))
                if prevy < 30:
                    continue
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
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
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
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
        qp.setPen(QtGui.QPen(self.textColor))
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
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.width()/2 + self.data[i].re * self.chartWidth/2
            y = self.height()/2 + self.data[i].im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.data[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.data[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        qp.setPen(pen)
        if len(self.data) > 0:
            fstart = self.data[0].freq
            fstop  = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop  = self.reference[len(self.reference)-1].freq
        for i in range(len(self.reference)):
            data = self.reference[i]
            if data.freq < fstart or data.freq > fstop:
                continue
            x = self.width()/2 + data.re * self.chartWidth/2
            y = self.height()/2 + data.im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.reference[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.reference[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
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
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
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
        qp.setPen(QtGui.QPen(self.textColor))
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
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.width()/2 + self.data[i].re * self.chartWidth/2
            y = self.height()/2 + self.data[i].im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.data[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.data[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        qp.setPen(pen)
        if len(self.data) > 0:
            fstart = self.data[0].freq
            fstop  = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop  = self.reference[len(self.reference)-1].freq
        for i in range(len(self.reference)):
            data = self.reference[i]
            if data.freq < fstart or data.freq > fstop:
                continue
            x = self.width()/2 + data.re * self.chartWidth/2
            y = self.height()/2 + data.im * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                prevx = self.width() / 2 + self.reference[i-1].re * self.chartWidth / 2
                prevy = self.height() / 2 + self.reference[i-1].im * -1 * self.chartHeight / 2
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
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


class LogMagChart(Chart):
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
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
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
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name)
        qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
        qp.drawLine(self.leftMargin, 20, self.leftMargin, 20+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, 20+self.chartHeight, self.leftMargin+self.chartWidth, 20 + self.chartHeight)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(2)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(1)
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
        minValue = 100
        maxValue = 0
        for d in self.data:
            logmag = self.logMag(d)
            if logmag > maxValue:
                maxValue = logmag
            if logmag < minValue:
                minValue = logmag
        for d in self.reference:  # Also check min/max for the reference sweep
            if d.freq < fstart or d.freq > fstop:
                continue
            logmag = self.logMag(d)
            if logmag > maxValue:
                maxValue = logmag
            if logmag < minValue:
                minValue = logmag

        minValue = 10*math.floor(minValue/10)
        maxValue = 10*math.ceil(maxValue/10)
        span = maxValue-minValue
        for i in range(minValue, maxValue, 10):
            y = 30 + round((i-minValue)/span*(self.chartHeight-10))
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
        qp.setPen(self.textColor)
        qp.drawText(3, 35, str(-minValue))
        qp.drawText(3, self.chartHeight+20, str(-maxValue))
        # At least 100 px between ticks
        qp.drawText(self.leftMargin-20, 20 + self.chartHeight + 15, LogMagChart.shortenFrequency(fstart))
        ticks = math.floor(self.chartWidth/100)  # Number of ticks does not include the origin
        for i in range(ticks):
            x = self.leftMargin + round((i+1)*self.chartWidth/ticks)
            qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
            qp.drawLine(x, 20, x, 20+self.chartHeight+5)
            qp.setPen(self.textColor)
            qp.drawText(x-20, 20+self.chartHeight+15, LogMagChart.shortenFrequency(round(fspan/ticks*(i+1) + fstart)))

        if self.mouselocation != 0:
            qp.setPen(QtGui.QPen(QtGui.QColor(224,224,224)))
            x = self.leftMargin + 1 + round(self.chartWidth * (self.mouselocation - fstart) / fspan)
            qp.drawLine(x, 20, x, 20 + self.chartHeight +5)

        qp.setPen(pen)
        for i in range(len(self.data)):
            logmag = self.logMag(self.data[i])
            x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * i)
            y = 30 + round((logmag-minValue)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                logmag = self.logMag(self.data[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth / len(self.data) * (i-1))
                prevy = 30 + round((logmag - minValue) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            logmag = self.logMag(self.reference[i])
            x = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i].freq - fstart)/fspan)
            y = 30 + round((logmag-minValue)/span*(self.chartHeight-10))
            qp.drawPoint(int(x), int(y))
            if self.drawLines and i > 0:
                logmag = self.logMag(self.reference[i-1])
                prevx = self.leftMargin + 1 + round(self.chartWidth*(self.reference[i-1].freq - fstart)/fspan)
                prevy = 30 + round((logmag - minValue) / span * (self.chartHeight - 10))
                qp.setPen(line_pen)
                qp.drawLine(x, y, prevx, prevy)
                qp.setPen(pen)
        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                highlighter.setColor(m.color)
                qp.setPen(highlighter)
                logmag = self.logMag(self.data[m.location])
                x = self.leftMargin + 1 + round(self.chartWidth/len(self.data) * m.location)
                y = 30 + round((logmag - minValue) / span * (self.chartHeight - 10))
                qp.drawLine(int(x), int(y) + 3, int(x) - 3, int(y) - 3)
                qp.drawLine(int(x), int(y) + 3, int(x) + 3, int(y) - 3)
                qp.drawLine(int(x) - 3, int(y) - 3, int(x) + 3, int(y) - 3)
                #qp.drawPoint(int(x), int(y))

    @staticmethod
    def shortenFrequency(frequency):
        if frequency < 50000:
            return frequency
        if frequency < 5000000:
            return str(round(frequency / 1000)) + "k"
        return str(round(frequency / 1000000, 1)) + "M"

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

    @staticmethod
    def logMag(p: Datapoint) -> float:
        re = p.re
        im = p.im
        re50 = 50 * (1 - re * re - im * im) / (1 + re * re + im * im - 2 * re)
        im50 = 50 * (2 * im) / (1 + re * re + im * im - 2 * re)
        # Calculate the reflection coefficient
        mag = math.sqrt((re50 - 50) * (re50 - 50) + im50 * im50) / math.sqrt((re50 + 50) * (re50 + 50) + im50 * im50)
        return -20 * math.log10(mag)