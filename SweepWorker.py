#  Copyright (c) Rune B. Broberg

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot

from NanoVNASaver import NanoVNASaver


class SweepWorker(QtCore.QRunnable):
    def __init__(self, app: NanoVNASaver):
        super().__init__()
        self.app = app
        self.serial = app.serial
        self.serialLock = app.serialLock

    @pyqtSlot()
    def run(self):
        print("I am thread")
        # TODO: Set up multithreading contents
        # Fetch all the parameters before starting
        # Optionally split the sweep into subsweeps
        # For each sweep:
        #   - Fetch data
        #   - Process data
        #   - Store data
        #   - Signal update
        # Signal finishing