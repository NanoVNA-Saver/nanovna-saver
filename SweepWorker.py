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
from time import sleep

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, pyqtSignal

import NanoVNASaver

Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class WorkerSignals(QtCore.QObject):
    updated = pyqtSignal()
    finished = pyqtSignal()


class SweepWorker(QtCore.QRunnable):
    def __init__(self, app: NanoVNASaver):
        super().__init__()
        self.signals = WorkerSignals()
        self.app = app
        self.noSweeps = 1
        self.setAutoDelete(False)
        self.percentage = 0

    @pyqtSlot()
    def run(self):
        print("I am thread")
        self.percentage = 0
        if not self.app.serial.is_open:
            return

        if int(self.app.sweepCountInput.text()) > 0:
            self.noSweeps = int(self.app.sweepCountInput.text())

        print("### Updating... ### ")
        if not self.app.sweepStartInput.text().isnumeric() or not self.app.sweepEndInput.text().isnumeric():
            # We should handle the first startup by reading frequencies?
            sweepFrom = 1000000
            sweepTo = 800000000
        else:
            sweepFrom = int(self.app.sweepStartInput.text())
            sweepTo = int(self.app.sweepEndInput.text())

        if self.noSweeps > 1:
            # We're going to run multiple sweeps
            print("### Multisweep ###")
            span = sweepTo - sweepFrom
            stepsize = int(span / (100 + (self.noSweeps-1)*101))
            print("Doing " + str(100 + (self.noSweeps-1)*101) + " steps of size " + str(stepsize))
            values = []
            frequencies = []
            for i in range(self.noSweeps):
                self.app.setSweep(sweepFrom + i*101*stepsize, sweepFrom+(100+i*101)*stepsize)
                sleep(0.8)
                tmpdata = []
                done = False
                while not done:
                    done = True
                    tmpdata = self.app.readValues("data 0")
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
                tmpfreq = []
                done = False
                while not done:
                    done = True
                    tmpfreq = self.app.readValues("frequencies")
                    for f in tmpfreq:
                        if not f.isdigit():
                            print("Warning: Got a non-digit frequency: " + f)
                            done = False

                frequencies += tmpfreq
                self.percentage = (i+1)*100/self.noSweeps
                self.saveData(frequencies, values)

            # Reset the device to show the full range
            self.app.setSweep(self.app.sweepStartInput.text(), self.app.sweepEndInput.text())
        else:
            print("### Reading values ###")
            self.values = self.app.readValues("data 0")
            print("### Reading frequencies ###")
            self.frequencies = self.app.readValues("frequencies")
            print("Read data, saving")
            self.saveData(self.frequencies, self.values)

        self.percentage = 100
        self.signals.finished.emit()
        return

    def saveData(self, frequencies, values):
        data = []
        for i in range(len(values)):
            reStr, imStr = values[i].split(" ")
            re = float(reStr)
            im = float(imStr)
            freq = int(frequencies[i])
            data += [Datapoint(freq, re, im)]
        self.app.saveData(data)
        print("Saved data, emitting signal")
        self.signals.updated.emit()
