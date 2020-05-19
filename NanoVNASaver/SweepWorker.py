#  NanoVNASaver - a python program to view and export Touchstone data from a NanoVNA
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
import logging
from time import sleep
from typing import List
import math
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSlot, pyqtSignal

import NanoVNASaver
from NanoVNASaver.Calibration import Calibration
from NanoVNASaver.Hardware import VNA, InvalidVNA
from NanoVNASaver.RFTools import RFTools, Datapoint

logger = logging.getLogger(__name__)


class WorkerSignals(QtCore.QObject):
    updated = pyqtSignal()
    finished = pyqtSignal()
    sweepError = pyqtSignal()
    fatalSweepError = pyqtSignal()


class SweepWorker(QtCore.QRunnable):
    def __init__(self, app: NanoVNASaver):
        super().__init__()
        logger.info("Initializing SweepWorker")
        self.signals = WorkerSignals()
        self.app = app
        self.vna: VNA = InvalidVNA()
        self.noSweeps = 1
        self.setAutoDelete(False)
        self.percentage = 0
        self.data11: List[Datapoint] = []
        self.data21: List[Datapoint] = []
        self.rawData11: List[Datapoint] = []
        self.rawData21: List[Datapoint] = []
        self.stopped = False
        self.running = False
        self.continuousSweep = False
        self.averaging = False
        self.averages = 3
        self.truncates = 0
        self.error_message = ""
        self.offsetDelay = 0

    @pyqtSlot()
    def run(self):
        logger.info("Initializing SweepWorker")
        self.running = True
        self.percentage = 0
        if not self.app.serial.is_open:
            logger.debug("Attempted to run without being connected to the NanoVNA")
            self.running = False
            return

        if int(self.app.sweepCountInput.text()) > 0:
            self.noSweeps = int(self.app.sweepCountInput.text())

        logger.info("%d sweeps", self.noSweeps)
        if self.averaging:
            logger.info("%d averages", self.averages)

        if self.app.sweepStartInput.text() == "" or self.app.sweepEndInput.text() == "":
            logger.debug("First sweep - standard range")
            # We should handle the first startup by reading frequencies?
            sweep_from = 100000
            sweep_to = 350000000
        else:
            sweep_from = RFTools.parseFrequency(self.app.sweepStartInput.text())
            sweep_to = RFTools.parseFrequency(self.app.sweepEndInput.text())
            logger.debug("Parsed sweep range as %d to %d", sweep_from, sweep_to)
            if sweep_from < 0 or sweep_to < 0 or sweep_from == sweep_to:
                logger.warning("Can't sweep from %s to %s",
                               self.app.sweepStartInput.text(),
                               self.app.sweepEndInput.text())
                self.error_message = "Unable to parse frequency inputs - check start and stop fields."
                self.stopped = True
                self.running = False
                self.signals.sweepError.emit()
                return

        span = sweep_to - sweep_from
        stepsize = int(span / (290 + (self.noSweeps-1)*290))

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
                start = sweep_from + i * 290 * stepsize
                freq, val11, val21 = self.readAveragedSegment(start, start + 290 * stepsize, self.averages)

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
                start = sweep_from + i*290*stepsize
                try:
                    freq, val11, val21 = self.readSegment(start, start+290*stepsize)

                    frequencies += freq
                    values += val11
                    values21 += val21

                    self.percentage = (i+1)*100/self.noSweeps
                    logger.debug("Saving acquired data")
                    self.saveData(frequencies, values, values21)
                except NanoVNAValueException as e:
                    self.error_message = str(e)
                    self.stopped = True
                    self.running = False
                    self.signals.sweepError.emit()
                except NanoVNASerialException as e:
                    self.error_message = str(e)
                    self.stopped = True
                    self.running = False
                    self.signals.sweepFatalError.emit()

        while self.continuousSweep and not self.stopped:
            logger.debug("Continuous sweeping")
            for i in range(self.noSweeps):
                logger.debug("Sweep segment no %d", i)
                if self.stopped:
                    logger.debug("Stopping sweeping as signalled")
                    break
                start = sweep_from + i * 290 * stepsize
                try:
                    _, values, values21 = self.readSegment(start, start + 290 * stepsize)
                    logger.debug("Updating acquired data")
                    self.updateData(values, values21, i)
                except NanoVNAValueException as e:
                    self.error_message = str(e)
                    self.stopped = True
                    self.running = False
                    self.signals.sweepError.emit()
                except NanoVNASerialException as e:
                    self.error_message = str(e)
                    self.stopped = True
                    self.running = False
                    self.signals.sweepFatalError.emit()

        # Reset the device to show the full range
        logger.debug("Resetting NanoVNA sweep to full range: %d to %d",
                     RFTools.parseFrequency(self.app.sweepStartInput.text()),
                     RFTools.parseFrequency(self.app.sweepEndInput.text()))
        self.vna.resetSweep(RFTools.parseFrequency(self.app.sweepStartInput.text()),
                            RFTools.parseFrequency(self.app.sweepEndInput.text()))

        self.percentage = 100
        logger.debug("Sending \"finished\" signal")
        self.signals.finished.emit()
        self.running = False
        return

    def updateData(self, values11, values21, offset, segment_size=290):
        # Update the data from (i*290) to (i+1)*290
        logger.debug("Calculating data and inserting in existing data at offset %d", offset)
        for i in range(len(values11)):
            re, im = values11[i]
            re21, im21 = values21[i]
            freq = self.data11[offset * segment_size + i].freq
            raw_data11 = Datapoint(freq, re, im)
            raw_data21 = Datapoint(freq, re21, im21)
            data11, data21 = self.applyCalibration([raw_data11], [raw_data21])

            self.data11[offset * segment_size + i] = data11
            self.data21[offset * segment_size + i] = data21
            self.rawData11[offset * segment_size + i] = raw_data11
            self.rawData21[offset * segment_size + i] = raw_data21
        logger.debug("Saving data to application (%d and %d points)", len(self.data11), len(self.data21))
        self.app.saveData(self.data11, self.data21)
        logger.debug("Sending \"updated\" signal")
        self.signals.updated.emit()

    def saveData(self, frequencies, values11, values21):
        raw_data11 = []
        raw_data21 = []
        logger.debug("Calculating data including corrections")
        for i in range(len(values11)):
            re, im = values11[i]
            re21, im21 = values21[i]
            freq = frequencies[i]
            raw_data11 += [Datapoint(freq, re, im)]
            raw_data21 += [Datapoint(freq, re21, im21)]
        self.data11, self.data21 = self.applyCalibration(raw_data11, raw_data21)
        self.rawData11 = raw_data11
        self.rawData21 = raw_data21
        logger.debug("Saving data to application (%d and %d points)", len(self.data11), len(self.data21))
        self.app.saveData(self.data11, self.data21)
        logger.debug("Sending \"updated\" signal")
        self.signals.updated.emit()

    def applyCalibration(self, raw_data11: List[Datapoint], raw_data21: List[Datapoint]) ->\
                        (List[Datapoint], List[Datapoint]):
        if self.offsetDelay != 0:
            tmp = []
            for d in raw_data11:
                tmp.append(Calibration.correctDelay11(d, self.offsetDelay))
            raw_data11 = tmp
            tmp = []
            for d in raw_data21:
                tmp.append(Calibration.correctDelay21(d, self.offsetDelay))
            raw_data21 = tmp

        if not self.app.calibration.isCalculated:
            return raw_data11, raw_data21

        data11: List[Datapoint] = []
        data21: List[Datapoint] = []

        if self.app.calibration.isValid1Port():
            for d in raw_data11:
                re, im = self.app.calibration.correct11(d.re, d.im, d.freq)
                data11.append(Datapoint(d.freq, re, im))
        else:
            data11 = raw_data11

        if self.app.calibration.isValid2Port():
            for d in raw_data21:
                re, im = self.app.calibration.correct21(d.re, d.im, d.freq)
                data21.append(Datapoint(d.freq, re, im))
        else:
            data21 = raw_data21
        return data11, data21

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

    @staticmethod
    def truncate(values: List[List[tuple]], count):
        logger.debug("Truncating from %d values to %d", len(values), len(values) - count)
        if count < 1:
            return values
        values = np.swapaxes(values, 0, 1)
        return_values = []

        for valueset in values:
            avg = np.average(valueset, 0)  # avg becomes a 2-value array of the location of the average
            new_valueset = valueset
            for n in range(count):
                max_deviance = 0
                max_idx = -1
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
        self.vna.setSweep(start, stop)

        # Let's check the frequencies first:
        frequencies = self.readFreq()
        #  TODO: Set up checks for getting the right frequencies. Challenge: We don't set frequency to single-Hz
        #        accuracy, but rather "quite close". Ex: 106213728 vs 106213726
        # if start != int(frequencies[i*290]):
        #     # We got the wrong frequencies? Let's just log it for now.
        #     logger.warning("Wrong frequency received - %d is not %d", int(frequencies[i*290]), start)
        # S11
        values11 = self.readData("data 0")
        # S21
        values21 = self.readData("data 0")

        return frequencies, values11, values21

    def readData(self, data):
        logger.debug("Reading %s", data)
        done = False
        returndata = []
        count = 0
        while not done:
            done = True
            returndata = []
            tmpdata = self.vna.readValues(data)
            if not tmpdata:
                logger.warning("Read no values")
                raise NanoVNASerialException("Failed reading data: Returned no values.")
            logger.debug("Read %d values", len(tmpdata))
            for d in tmpdata:
 #               a, b = d.split(" ")
                a = d
                b = 0
                try:
                    if self.vna.validateInput and (float(a) < -9.5 or float(a) > 9.5):
                        logger.warning("Got a non-float data value: %s (%s)", d, a)
                        logger.debug("Re-reading %s", data)
                        done = False
                    elif self.vna.validateInput and (float(b) < -9.5 or float(b) > 9.5):
                        logger.warning("Got a non-float data value: %s (%s)", d, b)
                        logger.debug("Re-reading %s", data)
                        done = False
                    else:
                        returndata.append((10**((float(a)/20)), float(b)))
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
                    logger.critical("Tried and failed to read %s %d times. Giving up.", data, count)
                    raise NanoVNAValueException("Failed reading " + str(data) + " " + str(count) + " times.\n" +
                                                "Data outside expected valid ranges, or in an unexpected format.\n\n" +
                                                "You can disable data validation on the device settings screen.")
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
            tmpfreq = self.vna.readFrequencies()
            if not tmpfreq:
                logger.warning("Read no frequencies")
                raise NanoVNASerialException("Failed reading frequencies: Returned no values.")
            for f in tmpfreq:
                if not f.isdigit():
                    logger.warning("Got a non-digit frequency: %s", f)
                    logger.debug("Re-reading frequencies")
                    done = False
                    count += 1
                    if count == 10:
                        logger.error("Tried and failed %d times to read frequencies.", count)
                    if count >= 20:
                        logger.critical("Tried and failed to read frequencies from the NanoVNA %d times.", count)
                        raise NanoVNAValueException("Failed reading frequencies " + str(count) + " times.")
                else:
                    returnfreq.append(int(f))
        return returnfreq

    def setContinuousSweep(self, continuous_sweep: bool):
        self.continuousSweep = continuous_sweep

    def setAveraging(self, averaging: bool, averages: str, truncates: str):
        self.averaging = averaging
        try:
            self.averages = int(averages)
            self.truncates = int(truncates)
        except ValueError:
            return

    def setVNA(self, vna):
        self.vna = vna


class NanoVNAValueException(Exception):
    pass


class NanoVNASerialException(Exception):
    pass
