#  Copyright 2019 Rune B. Broberg
import math
from time import sleep
from PyQt5 import QtWidgets, QtCore, QtGui
import serial
import threading


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


class NanoVNASaver(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.noSweeps = 2  # Number of sweeps to run

        self.serialLock = threading.Lock()
        self.serial = serial.Serial()

        self.values = []
        self.frequencies = []

        self.serialPort = "COM11"
        # self.serialSpeed = "115200"

        self.setWindowTitle("NanoVNA Saver")
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.smithChart = SmithChart()

        left_column = QtWidgets.QVBoxLayout()
        right_column = QtWidgets.QVBoxLayout()

        layout.addLayout(left_column, 0, 0)
        layout.addLayout(right_column, 0, 1)

        ################################################################################################################
        #  Sweep control
        ################################################################################################################

        sweep_control_box = QtWidgets.QGroupBox()
        sweep_control_box.setMaximumWidth(400)
        sweep_control_box.setTitle("Sweep control")
        sweep_control_layout = QtWidgets.QFormLayout(sweep_control_box)

        self.sweepStartInput = QtWidgets.QLineEdit("")
        self.sweepStartInput.setAlignment(QtCore.Qt.AlignRight)

        sweep_control_layout.addRow(QtWidgets.QLabel("Sweep start"), self.sweepStartInput)

        self.sweepEndInput = QtWidgets.QLineEdit("")
        self.sweepEndInput.setAlignment(QtCore.Qt.AlignRight)

        sweep_control_layout.addRow(QtWidgets.QLabel("Sweep end"), self.sweepEndInput)
        
        self.sweepCountInput = QtWidgets.QLineEdit("")
        self.sweepCountInput.setAlignment(QtCore.Qt.AlignRight)
        self.sweepCountInput.setText("1")

        sweep_control_layout.addRow(QtWidgets.QLabel("Sweep count"), self.sweepCountInput)

        self.btnSweep = QtWidgets.QPushButton("Sweep")
        self.btnSweep.clicked.connect(self.sweep)
        sweep_control_layout.addRow(self.btnSweep)

        left_column.addWidget(sweep_control_box)

        ################################################################################################################
        #  Marker control
        ################################################################################################################

        marker_control_box = QtWidgets.QGroupBox()
        marker_control_box.setTitle("Markers")
        marker_control_box.setMaximumWidth(400)
        marker_control_layout = QtWidgets.QFormLayout(marker_control_box)

        self.marker1FrequencyInput = QtWidgets.QLineEdit("")
        self.marker1FrequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.marker1FrequencyInput.returnPressed.connect(lambda: self.smithChart.setMarker1(self.marker1FrequencyInput.text()))

        self.btnMarker1ColorPicker = QtWidgets.QPushButton("█")
        self.btnMarker1ColorPicker.setFixedWidth(20)
        p = self.btnMarker1ColorPicker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.smithChart.marker1Color)
        self.btnMarker1ColorPicker.setPalette(p)
        self.btnMarker1ColorPicker.clicked.connect(lambda: self.setMarker1Color(QtWidgets.QColorDialog.getColor()))

        marker1layout = QtWidgets.QHBoxLayout()
        marker1layout.addWidget(self.marker1FrequencyInput)
        marker1layout.addWidget(self.btnMarker1ColorPicker)

        marker_control_layout.addRow(QtWidgets.QLabel("Marker 1"), marker1layout)

        self.marker2FrequencyInput = QtWidgets.QLineEdit("")
        self.marker2FrequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.marker2FrequencyInput.returnPressed.connect(lambda: self.smithChart.setMarker2(self.marker2FrequencyInput.text()))

        self.btnMarker2ColorPicker = QtWidgets.QPushButton("█")
        self.btnMarker2ColorPicker.setFixedWidth(20)
        p = self.btnMarker2ColorPicker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.smithChart.marker2Color)
        self.btnMarker2ColorPicker.setPalette(p)
        self.btnMarker2ColorPicker.clicked.connect(lambda: self.setMarker2Color(QtWidgets.QColorDialog.getColor()))

        marker2layout = QtWidgets.QHBoxLayout()
        marker2layout.addWidget(self.marker2FrequencyInput)
        marker2layout.addWidget(self.btnMarker2ColorPicker)

        marker_control_layout.addRow(QtWidgets.QLabel("Marker 2"), marker2layout)

        self.marker1label = QtWidgets.QLabel("")
        marker_control_layout.addRow(QtWidgets.QLabel("Marker 1: "), self.marker1label)

        self.marker2label = QtWidgets.QLabel("")
        marker_control_layout.addRow(QtWidgets.QLabel("Marker 2: "), self.marker2label)

        left_column.addWidget(marker_control_box)

        left_column.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding))

        ################################################################################################################
        #  Serial control
        ################################################################################################################

        serial_control_box = QtWidgets.QGroupBox()
        serial_control_box.setMaximumWidth(400)
        serial_control_box.setTitle("Serial port control")
        serial_control_layout = QtWidgets.QFormLayout(serial_control_box)
        self.serialPortInput = QtWidgets.QLineEdit(self.serialPort)
        self.serialPortInput.setAlignment(QtCore.Qt.AlignRight)
        # self.serialSpeedInput = QtWidgets.QLineEdit(str(self.serialSpeed))
        # self.serialSpeedInput.setValidator(QtGui.QIntValidator())
        # self.serialSpeedInput.setAlignment(QtCore.Qt.AlignRight)
        serial_control_layout.addRow(QtWidgets.QLabel("Serial port"), self.serialPortInput)
        # serial_control_layout.addRow(QtWidgets.QLabel("Speed"), self.serialSpeedInput)

        self.btnSerialToggle = QtWidgets.QPushButton("Open serial")
        self.btnSerialToggle.clicked.connect(self.serialButtonClick)
        serial_control_layout.addRow(self.btnSerialToggle)

        left_column.addWidget(serial_control_box)

        ################################################################################################################
        #  File control
        ################################################################################################################

        file_control_box = QtWidgets.QGroupBox()
        file_control_box.setTitle("Export file")
        file_control_box.setMaximumWidth(400)
        file_control_layout = QtWidgets.QFormLayout(file_control_box)
        self.fileNameInput = QtWidgets.QLineEdit("")
        self.fileNameInput.setAlignment(QtCore.Qt.AlignRight)

        file_control_layout.addRow(QtWidgets.QLabel("Filename"), self.fileNameInput)

        self.btnExportFile = QtWidgets.QPushButton("Export data")
        self.btnExportFile.clicked.connect(self.exportFile)
        file_control_layout.addRow(self.btnExportFile)

        left_column.addWidget(file_control_box)

        ################################################################################################################
        #  Right side
        ################################################################################################################

        self.lister = QtWidgets.QPlainTextEdit()
        self.lister.setFixedHeight(200)
        right_column.addWidget(self.lister)
        right_column.addWidget(self.smithChart)

    def exportFile(self):
        print("Save file to " + self.fileNameInput.text())
        filename = self.fileNameInput.text()
        # TODO: Make some proper file handling here?
        file = open(filename, "w+")
        self.lister.clear()
        self.lister.appendPlainText("# Hz S RI R 50")
        file.write("# Hz S RI R 50\n")
        for i in range(len(self.values)):
            if i > 0 and self.frequencies[i] != self.frequencies[i-1]:
                self.lister.appendPlainText(self.frequencies[i] + " " + self.values[i])
                file.write(self.frequencies[i] + " " + self.values[i] + "\n")
        file.close()

    def serialButtonClick(self):
        if self.serial.is_open:
            self.stopSerial()
        else:
            self.startSerial()
        return

    def startSerial(self):
        self.lister.appendPlainText("Opening serial port " + self.serialPort)

        if self.serialLock.acquire():
            self.serialPort = self.serialPortInput.text()
            try:
                self.serial = serial.Serial(port=self.serialPort, baudrate=115200)
            except serial.SerialException as exc:
                self.lister.appendPlainText("Tried to open " + self.serialPort + " and failed.")
                self.serialLock.release()
                return
            self.btnSerialToggle.setText("Close serial")
            self.serial.timeout = 0.05

            self.serialLock.release()
            sleep(0.25)
            self.sweep()
            return

    def stopSerial(self):
        if self.serialLock.acquire():
            self.serial.close()
            self.serialLock.release()
            self.btnSerialToggle.setText("Open serial")

    def writeSerial(self, command):
        if not self.serial.is_open:
            print("Warning: Writing without serial port being opened (" + command + ")")
            return
        if self.serialLock.acquire():
            try:
                self.serial.write(str(command + "\r").encode('ascii'))
                self.serial.readline()
            except serial.SerialException as exc:
                print("Exception received")
            self.serialLock.release()
        return

    def setSweep(self, start, stop):
        print("Sending: " + "sweep " + str(start) + " " + str(stop) + " 101")
        self.writeSerial("sweep " + str(start) + " " + str(stop) + " 101")

    def sweep(self):
        # Run the serial port update
        if not self.serial.is_open:
            return

        self.btnSweep.setDisabled(True)

        if int(self.sweepCountInput.text()) > 0:
            self.noSweeps = int(self.sweepCountInput.text())

        print("### Updating... ### ")

        if len(self.frequencies) > 1:
            # We've already run at least once
            print("### Run at least once ###")
            if (self.sweepStartInput.text() != self.frequencies[0]
               or self.sweepEndInput.text() != self.frequencies[100]):
                # Need to set frequency span
                print("### Setting span ###")
                # TODO: Set up for multiple sweeps
                print("Setting sweep to run " + self.sweepStartInput.text() + " to " + self.sweepEndInput.text())
                self.setSweep(self.sweepStartInput.text(), self.sweepEndInput.text())
                sleep(0.5)

        if self.noSweeps > 1 and self.sweepStartInput.text() != "" and self.sweepEndInput.text() != "":
            # We're going to run multiple sweeps
            print("### Multisweep ###")
            span = int(self.sweepEndInput.text()) - int(self.sweepStartInput.text())
            start = int(self.sweepStartInput.text())
            end = int(self.sweepEndInput.text())
            stepsize = int(span / (100 + (self.noSweeps-1)*101))
            print("Doing " + str(100 + (self.noSweeps-1)*101) + " steps of size " + str(stepsize))
            values = []
            frequencies = []
            for i in range(self.noSweeps):
                self.setSweep(start + i*101*stepsize, start+(100+i*101)*stepsize)
                QtWidgets.QApplication.processEvents()  # TODO: Make this multithreaded using the QT threads instead
                sleep(0.2)
                QtWidgets.QApplication.processEvents()  # This is a really stupid way to limit UI sleeps to 0.2 seconds
                sleep(0.2)
                QtWidgets.QApplication.processEvents()
                sleep(0.2)
                QtWidgets.QApplication.processEvents()
                sleep(0.2)
                done = False
                while not done:
                    done = True
                    tmpdata = self.readValues("data 0")
                    for d in tmpdata:
                        a, b = d.split(" ")
                        try:
                            if float(a) < -1.5 or float(a) > 1.5:
                                print("Warning: Got a non-float data value: " + d + " (" + a + ")")
                                done = False
                            if float(b) < -1.5 or float(b) > 1.5:
                                print("Warning: Got a non-float data value: " + d + " (" + b + ")")
                                done = False
                        except Exception:
                            done = False

                values += tmpdata

                # TODO: Figure out why frequencies sometimes arrive as non-numbers
                done = False
                while not done:
                    done = True
                    tmpfreq = self.readValues("frequencies")
                    for f in tmpfreq:
                        if not f.isdigit():
                            print("Warning: Got a non-digit frequency: " + f)
                            done = False

                frequencies += tmpfreq
                self.smithChart.setValues(values, frequencies)

            self.values = values
            self.frequencies = frequencies

            # Reset the device to show the full range
            self.setSweep(self.sweepStartInput.text(), self.sweepEndInput.text())
        else:
            print("### Reading values ###")
            self.values = self.readValues("data 0")
            print("### Reading frequencies ###")
            self.frequencies = self.readValues("frequencies")
            if self.sweepStartInput.text() == "":
                self.sweepStartInput.setText(self.frequencies[0])
            if self.sweepEndInput.text() == "":
                self.sweepEndInput.setText(self.frequencies[100])

        print("### Outputting values in textbox ###")
        for line in self.values:
            self.lister.appendPlainText(line)
        print("### Displaying Smith chart ###")
        self.smithChart.setValues(self.values, self.frequencies)
        if self.smithChart.marker1Location != -1:
            reStr, imStr = self.values[self.smithChart.marker1Location].split(" ")
            re = float(reStr)
            im = float(imStr)

            re50 = 50*(1-re*re-im*im)/(1+re*re+im*im-2*re)
            im50 = 50*(2*im)/(1+re*re+im*im-2*re)

            mag = math.sqrt(re*re+im*im)
            vswr = (1+mag)/(1-mag)
            self.marker1label.setText(str(round(re50, 3)) + " + j" + str(round(im50, 3)) + " VSWR: 1:" + str(round(vswr, 3)))

        if self.smithChart.marker2Location != -1:
            reStr, imStr = self.values[self.smithChart.marker2Location].split(" ")
            re = float(reStr)
            im = float(imStr)

            re50 = 50*(1-re*re-im*im)/(1+re*re+im*im-2*re)
            im50 = 50*(2*im)/(1+re*re+im*im-2*re)

            mag = math.sqrt(re*re+im*im)
            vswr = (1+mag)/(1-mag)
            self.marker2label.setText(str(round(re50, 3)) + " + j" + str(round(im50, 3)) + " VSWR: 1:" + str(round(vswr, 3)))

        self.btnSweep.setDisabled(False)
        return

    def readValues(self, value):
        if self.serialLock.acquire():
            print("### Reading " + str(value) + " ###")
            try:
                data = "a"
                while data != "":
                    data = self.serial.readline().decode('ascii')

                #  Then send the command to read data
                self.serial.write(str(value + "\r").encode('ascii'))
            except serial.SerialException as exc:
                print("Exception received")
            result = ""
            data = ""
            sleep(0.01)
            while "ch>" not in data:
                data = self.serial.readline().decode('ascii')
                result += data
            print("### Done reading ###")
            values = result.split("\r\n")
            print("Total values: " + str(len(values) - 2))
            self.serialLock.release()
            return values[1:102]

    def setMarker1Color(self, color):
        self.smithChart.marker1Color = color
        p = self.btnMarker1ColorPicker.palette()
        p.setColor(QtGui.QPalette.ButtonText, color)
        self.btnMarker1ColorPicker.setPalette(p)

    def setMarker2Color(self, color):
        self.smithChart.marker2Color = color
        p = self.btnMarker2ColorPicker.palette()
        p.setColor(QtGui.QPalette.ButtonText, color)
        self.btnMarker2ColorPicker.setPalette(p)

if __name__ == '__main__':
    # Main code goes here
    app = QtWidgets.QApplication([])
    window = NanoVNASaver()
    window.show()
    app.exec_()
