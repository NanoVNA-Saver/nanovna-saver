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
from typing import List

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
        self.data11: List[Datapoint] = []
        self.data21: List[Datapoint] = []
        self.rawData11: List[Datapoint] = []
        self.rawData21: List[Datapoint] = []
        self.stopped = False
        self.continuousSweep = False

    @pyqtSlot()
    def run(self):
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
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
            sweepFrom = NanoVNASaver.parseFrequency(self.app.sweepStartInput.text())
            sweepTo = NanoVNASaver.parseFrequency(self.app.sweepEndInput.text())
            if sweepFrom < 0 or sweepTo < 0:
                print("Can't sweep from " + self.app.sweepStartInput.text() + " to " + self.app.sweepEndInput.text())
                self.signals.finished.emit()
                return

        span = sweepTo - sweepFrom
        stepsize = int(span / (100 + (self.noSweeps-1)*101))
        values = []
        values12 = []
        frequencies = []
        for i in range(self.noSweeps):
            if self.stopped:
                break
            self.app.setSweep(sweepFrom + i*101*stepsize, sweepFrom+(100+i*101)*stepsize)
            sleep(0.3)
            # S11
            values += self.readData("data 0")
            # S12
            values12 += self.readData("data 1")

            frequencies += self.readFreq()
            self.percentage = (i+1)*100/self.noSweeps
            self.saveData(frequencies, values, values12)

        while self.continuousSweep and not self.stopped:
            for i in range(self.noSweeps):
                if self.stopped:
                    break
                self.app.setSweep(sweepFrom + i * 101 * stepsize, sweepFrom + (100 + i * 101) * stepsize)
                sleep(0.3)
                # S11
                values = self.readData("data 0")
                # S12
                values12 = self.readData("data 1")

                self.updateData(values, values12, i)

        # Reset the device to show the full range
        self.app.setSweep(NanoVNASaver.parseFrequency(self.app.sweepStartInput.text()), NanoVNASaver.parseFrequency(self.app.sweepEndInput.text()))

        self.percentage = 100
        self.signals.finished.emit()
        return

    def updateData(self, values11, values21, offset):
        # Update the data from (i*101) to (i+1)*101
        for i in range(len(values11)):
            reStr, imStr = values11[i].split(" ")
            re = float(reStr)
            im = float(imStr)
            reStr, imStr = values21[i].split(" ")
            re21 = float(reStr)
            im21 = float(imStr)
            freq = self.data11[offset*101 + i].freq
            rawData11 = Datapoint(freq, re, im)
            rawData21 = Datapoint(freq, re21, im21)
            if self.app.calibration.isCalculated:
                re, im = self.app.calibration.correct11(re, im, freq)
                if self.app.calibration.isValid2Port():
                    re21, im21 = self.app.calibration.correct21(re21, im21, freq)
            self.data11[offset*101 + i] = Datapoint(freq, re, im)
            self.data21[offset * 101 + i] = Datapoint(freq, re21, im21)
            self.rawData11[offset * 101 + i] = rawData11
            self.rawData21[offset * 101 + i] = rawData21
        self.app.saveData(self.data11, self.data21)
        self.signals.updated.emit()

    def saveData(self, frequencies, values, values12):
        data = []
        data12 = []
        rawData11 = []
        rawData21 = []
        for i in range(len(values)):
            reStr, imStr = values[i].split(" ")
            re = float(reStr)
            im = float(imStr)
            reStr, imStr = values12[i].split(" ")
            re21 = float(reStr)
            im21 = float(imStr)
            freq = int(frequencies[i])
            rawData11 += [Datapoint(freq, re, im)]
            rawData21 += [Datapoint(freq, re21, im21)]
            if self.app.calibration.isCalculated:
                re, im = self.app.calibration.correct11(re, im, freq)
                if self.app.calibration.isValid2Port():
                    re21, im21 = self.app.calibration.correct21(re21, im21, freq)
            data += [Datapoint(freq, re, im)]
            data12 += [Datapoint(freq, re21, im21)]
        self.data11 = data
        self.data21 = data12
        self.rawData11 = rawData11
        self.rawData21 = rawData21
        self.app.saveData(data, data12)
        self.signals.updated.emit()

    def readData(self, data):
        done = False
        tmpdata = []
        while not done:
            done = True
            tmpdata = self.app.readValues(data)
            for d in tmpdata:
                a, b = d.split(" ")
                try:
                    if float(a) < -9.5 or float(a) > 9.5:
                        print("Warning: Got a non-float data value: " + d + " (" + a + ")")
                        done = False
                    if float(b) < -9.5 or float(b) > 9.5:
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

    def setContinuousSweep(self, continuousSweep):
        self.continuousSweep = continuousSweep
