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
        self.percentage = 0
        if not self.app.serial.is_open:
            return

        if int(self.app.sweepCountInput.text()) > 0:
            self.noSweeps = int(self.app.sweepCountInput.text())

        if self.app.sweepStartInput.text() == "" or self.app.sweepEndInput.text() == "":
            # We should handle the first startup by reading frequencies?
            sweepFrom = 1000000
            sweepTo = 800000000
        else:
            from NanoVNASaver import NanoVNASaver
            sweepFrom = NanoVNASaver.parseFrequency(self.app.sweepStartInput.text())
            sweepTo = NanoVNASaver.parseFrequency(self.app.sweepEndInput.text())
            if sweepFrom < 0 or sweepTo < 0:
                print("Can't sweep from " + self.app.sweepStartInput.text() + " to " + self.app.sweepEndInput.text())
                self.signals.finished.emit()
                return

        if self.noSweeps > 1:
            # We're going to run multiple sweeps
            print("### Multisweep ###")
            span = sweepTo - sweepFrom
            stepsize = int(span / (100 + (self.noSweeps-1)*101))
            print("Doing " + str(100 + (self.noSweeps-1)*101) + " steps of size " + str(stepsize))
            values = []
            values12 = []
            frequencies = []
            for i in range(self.noSweeps):
                self.app.setSweep(sweepFrom + i*101*stepsize, sweepFrom+(100+i*101)*stepsize)
                sleep(0.8)
                # S11
                values += self.readData("data 0")
                # S12
                values12 += self.readData("data 1")

                frequencies += self.readFreq()
                self.percentage = (i+1)*100/self.noSweeps
                self.saveData(frequencies, values, values12)

            # Reset the device to show the full range
            self.app.setSweep(self.app.sweepStartInput.text(), self.app.sweepEndInput.text())
        else:
            self.app.setSweep(sweepFrom, sweepTo)
            sleep(0.8)
            values = self.readData("data 0")
            values12 = self.readData("data 1")
            frequencies = self.readFreq()
            self.saveData(frequencies, values, values12)

        self.percentage = 100
        self.signals.finished.emit()
        return

    def saveData(self, frequencies, values, values12):
        data = []
        data12 = []
        for i in range(len(values)):
            reStr, imStr = values[i].split(" ")
            re = float(reStr)
            im = float(imStr)
            reStr, imStr = values12[i].split(" ")
            re12 = float(reStr)
            im12 = float(imStr)
            freq = int(frequencies[i])
            data += [Datapoint(freq, re, im)]
            data12 += [Datapoint(freq, re12, im12)]
        self.app.saveData(data, data12)
        self.signals.updated.emit()

    def readData(self, data):
        done = False
        while not done:
            done = True
            tmpdata = self.app.readValues(data)
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
        return tmpdata

    def readFreq(self):
        # TODO: Figure out why frequencies sometimes arrive as non-integers
        tmpfreq = []
        done = False
        while not done:
            done = True
            tmpfreq = self.app.readValues("frequencies")
            for f in tmpfreq:
                if not f.isdigit():
                    print("Warning: Got a non-digit frequency: " + f)
                    done = False
        return tmpfreq