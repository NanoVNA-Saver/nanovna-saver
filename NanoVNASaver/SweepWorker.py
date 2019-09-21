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

import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, pyqtSignal

import NanoVNASaver
import logging

logger = logging.getLogger(__name__)

Datapoint = collections.namedtuple('Datapoint', 'freq re im')


class WorkerSignals(QtCore.QObject):
    updated = pyqtSignal()
    finished = pyqtSignal()


class SweepWorker(QtCore.QRunnable):
    def __init__(self, app: NanoVNASaver):
        super().__init__()
        logger.info("Initializing SweepWorker")
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
        self.averaging = False
        self.averages = 3
        self.truncates = 0

    @pyqtSlot()
    def run(self):
        logger.info("Initializing SweepWorker")
        from NanoVNASaver.NanoVNASaver import NanoVNASaver
        self.percentage = 0
        if not self.app.serial.is_open:
            logger.debug("Attempted to run without being connected to the NanoVNA")
            return

        if int(self.app.sweepCountInput.text()) > 0:
            self.noSweeps = int(self.app.sweepCountInput.text())

        logger.info("%d sweeps", self.noSweeps)
        if self.averaging:
            logger.info("%d averages", self.averages)

        if self.app.sweepStartInput.text() == "" or self.app.sweepEndInput.text() == "":
            logger.debug("First sweep - standard range")
            # We should handle the first startup by reading frequencies?
            sweep_from = 1000000
            sweep_to = 800000000
        else:
            sweep_from = NanoVNASaver.parseFrequency(self.app.sweepStartInput.text())
            sweep_to = NanoVNASaver.parseFrequency(self.app.sweepEndInput.text())
            logger.debug("Parsed sweep range as %d to %d", sweep_from, sweep_to)
            if sweep_from < 0 or sweep_to < 0:
                logger.warning("Can't sweep from %s to %s",
                               self.app.sweepStartInput.text(),
                               self.app.sweepEndInput.text())
                self.signals.finished.emit()
                return

        span = sweep_to - sweep_from
        stepsize = int(span / (100 + (self.noSweeps-1)*101))

        #  Setup complete

        values = []
        values21 = []
        frequencies = []

        if self.averaging:
            for i in range(self.noSweeps):
                logger.debug("Sweep segment no %d averaged over %d readings", i, self.averages)
                if self.stopped:
                    logger.debug("Stopping sweeping as signalled")
                    break
                start = sweep_from + i * 101 * stepsize
                freq, val11, val21 = self.readAveragedSegment(start, start + 100 * stepsize, self.averages)

                frequencies += freq
                values += val11
                values21 += val21

                self.percentage = (i + 1) * 100 / self.noSweeps
                logger.debug("Saving acquired data")
                self.saveData(frequencies, values, values21)

        else:
            for i in range(self.noSweeps):
                logger.debug("Sweep segment no %d", i)
                if self.stopped:
                    logger.debug("Stopping sweeping as signalled")
                    break
                start = sweep_from + i*101*stepsize
                freq, val11, val21 = self.readSegment(start, start+100*stepsize)

                frequencies += freq
                values += val11
                values21 += val21

                self.percentage = (i+1)*100/self.noSweeps
                logger.debug("Saving acquired data")
                self.saveData(frequencies, values, values21)

        while self.continuousSweep and not self.stopped:
            logger.debug("Continuous sweeping")
            for i in range(self.noSweeps):
                logger.debug("Sweep segment no %d", i)
                if self.stopped:
                    logger.debug("Stopping sweeping as signalled")
                    break
                start = sweep_from + i * 101 * stepsize
                _, values, values21 = self.readSegment(start, start + 100 * stepsize)
                logger.debug("Updating acquired data")
                self.updateData(values, values21, i)

        # Reset the device to show the full range
        logger.debug("Resetting NanoVNA sweep to full range: %d to %d",
                     NanoVNASaver.parseFrequency(self.app.sweepStartInput.text()),
                     NanoVNASaver.parseFrequency(self.app.sweepEndInput.text()))
        self.app.setSweep(NanoVNASaver.parseFrequency(self.app.sweepStartInput.text()), NanoVNASaver.parseFrequency(self.app.sweepEndInput.text()))

        self.percentage = 100
        logger.debug("Sending \"finished\" signal")
        self.signals.finished.emit()
        return

    def updateData(self, values11, values21, offset):
        # Update the data from (i*101) to (i+1)*101
        logger.debug("Calculating data and inserting in existing data at offset %d", offset)
        for i in range(len(values11)):
            re, im = values11[i]
            re21, im21 = values21[i]
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
        logger.debug("Saving data to application (%d and %d points)", len(self.data11), len(self.data21))
        self.app.saveData(self.data11, self.data21)
        logger.debug("Sending \"updated\" signal")
        self.signals.updated.emit()

    def saveData(self, frequencies, values11, values21):
        data = []
        data12 = []
        rawData11 = []
        rawData21 = []
        logger.debug("Calculating data including corrections")
        for i in range(len(values11)):
            re, im = values11[i]
            re21, im21 = values21[i]
            freq = frequencies[i]
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
        logger.debug("Saving data to application (%d and %d points)", len(self.data11), len(self.data21))
        self.app.saveData(data, data12)
        logger.debug("Sending \"updated\" signal")
        self.signals.updated.emit()

    def readAveragedSegment(self, start, stop, averages):
        val11 = []
        val21 = []
        freq = []
        logger.info("Reading %d averages from %d to %d", averages, start, stop)
        for i in range(averages):
            if self.stopped:
                logger.debug("Stopping averaging as signalled")
                break
            logger.debug("Reading average no %d / %d", i+1, averages)
            freq, tmp11, tmp21 = self.readSegment(start, stop)
            val11.append(tmp11)
            val21.append(tmp21)
            self.percentage += 100/(self.noSweeps*averages)
            self.signals.updated.emit()

        logger.debug("Post-processing averages")
        logger.debug("Truncating %d values by %d", len(val11), self.truncates)
        val11 = self.truncate(val11, self.truncates)
        val21 = self.truncate(val21, self.truncates)
        logger.debug("Averaging %d values", len(val11))

        return11 = np.average(val11, 0).tolist()
        return21 = np.average(val21, 0).tolist()

        return freq, return11, return21

    def truncate(self, values: List[List[tuple]], count):
        logger.debug("Truncating from %d values to %d", len(values), len(values) - count)
        if count < 1:
            return values
        values = np.swapaxes(values, 0, 1)
        return_values = []

        for valueset in values:
            avg = np.average(valueset, 0)  # avg becomes a 2-value array of the location of the average
            for n in range(count):
                max_deviance = 0
                max_idx = -1
                new_valueset = valueset
                for i in range(len(new_valueset)):
                    deviance = abs(new_valueset[i][0] - avg[0])**2 + abs(new_valueset[i][1] - avg[1])**2
                    if deviance > max_deviance:
                        max_deviance = deviance
                        max_idx = i
                next_valueset = []
                for i in range(len(new_valueset)):
                    if i != max_idx:
                        next_valueset.append((new_valueset[i][0], new_valueset[i][1]))
                new_valueset = next_valueset

            return_values.append(new_valueset)

        return_values = np.swapaxes(return_values, 0, 1)
        return return_values.tolist()

    def readSegment(self, start, stop):
        logger.debug("Setting sweep range to %d to %d", start, stop)
        self.app.setSweep(start, stop)
        sleep(0.3)
        # Let's check the frequencies first:
        frequencies = self.readFreq()
        #  TODO: Set up checks for getting the right frequencies. Challenge: We don't set frequency to single-Hz
        #        accuracy, but rather "quite close". Ex: 106213728 vs 106213726
        # if start != int(frequencies[i*101]):
        #     # We got the wrong frequencies? Let's just log it for now.
        #     logger.warning("Wrong frequency received - %d is not %d", int(frequencies[i*101]), start)
        # S11
        values11 = self.readData("data 0")
        # S21
        values21 = self.readData("data 1")

        return frequencies, values11, values21

    def readData(self, data):
        logger.debug("Reading %s", data)
        done = False
        returndata = []
        count = 0
        while not done:
            done = True
            returndata = []
            tmpdata = self.app.readValues(data)
            logger.debug("Read %d values", len(tmpdata))
            for d in tmpdata:
                a, b = d.split(" ")
                try:
                    if float(a) < -9.5 or float(a) > 9.5:
                        logger.warning("Got a non-float data value: %s (%s)", d, a)
                        logger.debug("Re-reading %s", data)
                        done = False
                    elif float(b) < -9.5 or float(b) > 9.5:
                        logger.warning("Got a non-float data value: %s (%s)", d, b)
                        logger.debug("Re-reading %s", data)
                        done = False
                    else:
                        returndata.append((float(a), float(b)))
                except Exception as e:
                    logger.exception("An exception occurred reading %s: %s", data, e)
                    logger.debug("Re-reading %s", data)
                    done = False
            if not done:
                sleep(0.2)
                count += 1
                if count == 10:
                    logger.error("Tried and failed to read %s %d times.", data, count)
                if count >= 20:
                    logger.error("Tried and failed to read %s %d times. Giving up.", data, count)
                    return None  # Put a proper exception in here
        return returndata

    def readFreq(self):
        # TODO: Figure out why frequencies sometimes arrive as non-integers
        logger.debug("Reading frequencies")
        returnfreq = []
        done = False
        count = 0
        while not done:
            done = True
            returnfreq = []
            tmpfreq = self.app.readValues("frequencies")
            for f in tmpfreq:
                if not f.isdigit():
                    logger.warning("Got a non-digit frequency: %s", f)
                    logger.debug("Re-reading frequencies")
                    done = False
                    count += 1
                    if count == 10:
                        logger.error("Tried and failed %d times to read frequencies.", count)
                    if count >= 20:
                        logger.critical("Tried and failed to read frequencies from the NanoVNA more than %d times.", count)
                        return None  # Put a proper exception in here
                else:
                    returnfreq.append(int(f))
        return returnfreq

    def setContinuousSweep(self, continuousSweep):
        self.continuousSweep = continuousSweep

    def setAveraging(self, averaging, averages, truncates):
        self.averaging = averaging
        try:
            self.averages = int(averages)
            self.truncates = int(truncates)
        except:
            return
