import sys
from time import sleep
from PyQt5 import QtWidgets, QtCore, QtGui
import serial
import threading
import math


class SmithChart(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.chartWidth = 720
        self.chartHeight = 720

        self.setMinimumSize(self.chartWidth + 40, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, QtGui.QColor("white"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.values = []
        self.frequencies = []
        self.marker = 0

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter(self)
        #qp.begin(self)  # Apparently not needed?
        self.drawSmithChart(qp)
        self.drawValues(qp)
        qp.end()

    def drawSmithChart(self, qp: QtGui.QPainter):  # TODO: Make the Smith chart resizable
        centerX = int(self.width()/2)
        centerY = int(self.height()/2)
        qp.setPen(QtGui.QPen(QtGui.QColor("lightgray")))
        qp.drawEllipse(QtCore.QPoint(centerX, centerY), int(self.chartWidth/2), int(self.chartHeight/2))
        qp.drawLine(20, centerY, self.chartWidth+20, centerY)

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
        qp.drawArc(centerY, centerY, self.chartWidth, -self.chartHeight, -90 * 16, -90 * 16)  # Im(Z) = 1
        qp.drawArc(20, centerY, self.chartWidth*2, self.chartHeight*2, 90*16, 53*16)  # Im(Z) = -0.5
        qp.drawArc(20, centerY, self.chartWidth*2, -self.chartHeight*2, -90 * 16, -53 * 16)  # Im(Z) = 0.5
        qp.drawArc(centerX - self.chartWidth*2, centerY, self.chartWidth*5, self.chartHeight*5, int(93.85*16), int(18.85*16))  # Im(Z) = -0.2
        qp.drawArc(centerX - self.chartWidth*2, centerY, self.chartWidth*5, -self.chartHeight*5, int(-93.85 * 16), int(-18.85 * 16))  # Im(Z) = 0.2

        # SWR rings
        #qp.drawEllipse(QtCore.QPoint(200, 200), 54, 54)  # SWR = 2
        #qp.drawEllipse(QtCore.QPoint(200, 200), 90, 90)  # SWR = 3
        #qp.drawEllipse(QtCore.QPoint(200, 200), 126, 126)  # SWR = 5

    def drawValues(self, qp: QtGui.QPainter):
        pen = QtGui.QPen(QtGui.QColor(255, 220, 40))
        pen.setWidth(2)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(3)
        qp.setPen(pen)
        for i in range(len(self.values)):
            # TODO: Make this check for being "nearest" neater
            if self.marker != 0 and abs(int(self.frequencies[i]) - self.marker) < (int(self.frequencies[2]) - int(self.frequencies[1])):
                qp.setPen(highlighter)
            else:
                qp.setPen(pen)
            rawx, rawy = self.values[i].split(" ")
            x = (self.chartWidth+40)/2 + float(rawx) * self.chartWidth/2
            y = (self.chartHeight+40)/2 + float(rawy) * -1 * self.chartHeight/2
            qp.drawPoint(int(x), int(y))

    def setValues(self, values, frequencies):
        self.values = values
        self.frequencies = frequencies
        self.update()

    def setMarker(self, value):
        if value.isnumeric():
            self.marker = int(value)
        else:
            self.marker = 0
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

        left_column = QtWidgets.QVBoxLayout()
        right_column = QtWidgets.QVBoxLayout()

        layout.addLayout(left_column, 0, 0)
        layout.addLayout(right_column, 0, 1)

        ################################################################################################################
        #  Sweep control
        ################################################################################################################

        sweep_control_box = QtWidgets.QGroupBox()
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
        marker_control_box.setTitle("Marker")
        marker_control_layout = QtWidgets.QFormLayout(marker_control_box)

        self.markerFrequencyInput = QtWidgets.QLineEdit("")
        self.markerFrequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.markerFrequencyInput.returnPressed.connect(lambda: self.smithChart.setMarker(self.markerFrequencyInput.text()))

        marker_control_layout.addRow(QtWidgets.QLabel("Marker"), self.markerFrequencyInput)

        left_column.addWidget(marker_control_box)

        left_column.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
          
        ################################################################################################################
        #  Serial control
        ################################################################################################################

        serial_control_box = QtWidgets.QGroupBox()
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
        right_column.addWidget(self.lister)
        self.smithChart = SmithChart()
        right_column.addWidget(self.smithChart)

    def exportFile(self):
        print("Save file to " + self.fileNameInput.text())
        print("For now we just save to the text editor...")
        self.lister.clear()
        self.lister.appendPlainText("# Hz S RI R 50")
        for i in range(len(self.values)):
            if i > 0 and self.frequencies[i] != self.frequencies[i-1]:
                self.lister.appendPlainText(self.frequencies[i] + " " + self.values[i])

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
                values += self.readValues("data 0")
                frequencies += self.readValues("frequencies")
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


if __name__ == '__main__':
    # Main code goes here
    app = QtWidgets.QApplication([])
    window = NanoVNASaver()
    window.show()
    app.exec_()
