#  Copyright 2019 Rune B. Broberg

from PyQt5 import QtWidgets

from NanoVNASaver import NanoVNASaver

if __name__ == '__main__':
    # Main code goes here
    app = QtWidgets.QApplication([])
    window = NanoVNASaver()
    window.show()
    app.exec_()
