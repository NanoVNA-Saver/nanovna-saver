#  Copyright (c) $year Rune B. Broberg

from PyQt5 import QtGui, QtWidgets, QtCore


class Marker:
    name = "Marker"
    frequency = ""
    color = QtGui.QColor()

    def __init__(self, name, initialColor, frequency=""):
        super().__init__()
        self.name = name
        self.color = initialColor
        self.frequency = frequency
        self.frequencyInput = QtWidgets.QLineEdit(frequency)
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.returnPressed.connect(lambda: self.setFrequency(self.frequencyInput.text()))

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setFixedWidth(20)
        p = self.btnColorPicker.palette()
        p.setColor(QtGui.QPalette.ButtonText, self.color)
        self.btnColorPicker.setPalette(p)
        self.btnColorPicker.clicked.connect(lambda: self.setColor(QtWidgets.QColorDialog.getColor()))

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.frequencyInput)
        self.layout.addWidget(self.btnColorPicker)

    def setFrequency(self, frequency):
        self.frequency = frequency

    def setColor(self, color):
        self.color = color

    def getRow(self):
        return (QtWidgets.QLabel(self.name), self.layout)