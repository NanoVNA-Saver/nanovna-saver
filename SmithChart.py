#  Copyright 2019 Rune B. Broberg

from PyQt5 import QtWidgets, QtGui, QtCore


class SmithChart(QtWidgets.QWidget):
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
        self.marker1 = -1
        self.marker2 = -1
        self.marker1Location = -1
        self.marker2Location = -1

        self.marker1Color = QtGui.QColor(255, 0, 20)
        self.marker2Color = QtGui.QColor(20, 0, 255)

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
        pen = QtGui.QPen(QtGui.QColor(220, 200, 30, 128))
        pen.setWidth(2)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(3)
        qp.setPen(pen)
        marker1 = -1
        marker2 = -1
        for i in range(len(self.values)):
            # TODO: Make this check for being "nearest" neater
            if self.marker1 != -1 and abs(int(self.frequencies[i]) - self.marker1) < (int(self.frequencies[2]) - int(self.frequencies[1])):
                if marker1 != -1:
                    # Are we closer than the other spot?
                    if abs(int(self.frequencies[i]) - self.marker1) < abs(int(self.frequencies[marker1]) - self.marker1):
                        marker1 = i
                else:
                    marker1 = i

            if self.marker2 != -1 and abs(int(self.frequencies[i]) - self.marker2) < (int(self.frequencies[2]) - int(self.frequencies[1])):
                if marker2 != -1:
                    # Are we closer than the other spot?
                    if abs(int(self.frequencies[i]) - self.marker2) < abs(int(self.frequencies[marker2]) - self.marker2):
                        marker2 = i
                else:
                    marker2 = i

            rawx, rawy = self.values[i].split(" ")
            x = self.width()/2 + float(rawx) * self.chartWidth/2
            y = self.height()/2 + float(rawy) * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))
        # Now draw the markers
        if marker1 != -1:
            highlighter.setColor(self.marker1Color)
            qp.setPen(highlighter)
            rawx, rawy = self.values[marker1].split(" ")
            x = self.width() / 2 + float(rawx) * self.chartWidth / 2
            y = self.height() / 2 + float(rawy) * -1 * self.chartHeight / 2
            qp.drawPoint(int(x), int(y))
            self.marker1Location = marker1

        if marker2 != -1:
            highlighter.setColor(self.marker2Color)
            qp.setPen(highlighter)
            rawx, rawy = self.values[marker2].split(" ")
            x = self.width() / 2 + float(rawx) * self.chartWidth / 2
            y = self.height() / 2 + float(rawy) * -1 * self.chartHeight / 2
            qp.drawPoint(int(x), int(y))
            self.marker2Location = marker2

    def setValues(self, values, frequencies):
        print("### Updating values ###")
        self.values = values
        self.frequencies = frequencies
        self.update()

    def setMarker1(self, value):
        self.marker1Location = -1
        if value.isnumeric():
            self.marker1 = int(value)
        else:
            self.marker1 = -1
        self.update()

    def setMarker2(self, value):
        self.marker2Location = -1
        if value.isnumeric():
            self.marker2 = int(value)
        else:
            self.marker2 = -1
        self.update()