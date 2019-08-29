#  Copyright (c) $year Rune B. Broberg
import collections
from typing import List

from PyQt5 import QtGui, QtWidgets, QtCore
Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class Marker:
    name = "Marker"
    frequency = 0
    color = QtGui.QColor()
    location = -1

    def __init__(self, name, initialColor, frequency=""):
        super().__init__()
        self.name = name

        if frequency.isnumeric():
            self.frequency = int(frequency)
        self.frequencyInput = QtWidgets.QLineEdit(frequency)
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.returnPressed.connect(lambda: self.setFrequency(self.frequencyInput.text()))

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setFixedWidth(20)
        self.setColor(initialColor)
        self.btnColorPicker.clicked.connect(lambda: self.setColor(QtWidgets.QColorDialog.getColor()))

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.frequencyInput)
        self.layout.addWidget(self.btnColorPicker)

    def setFrequency(self, frequency):
        self.frequency = int(frequency)

    def setColor(self, color):
        self.color = color
        p = self.btnColorPicker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.color)
        self.btnColorPicker.setPalette(p)

    def getRow(self):
        return (QtWidgets.QLabel(self.name), self.layout)

    def findLocation(self, data: List[Datapoint]):
        self.location = -1
        stepsize = data[1].freq-data[0].freq
        for i in range(len(data)):
            if abs(data[i].freq-self.frequency) <= (stepsize/2):
                self.location = i
                return
