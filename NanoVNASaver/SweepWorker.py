#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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
from typing import List, Tuple

import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSlot, pyqtSignal

from NanoVNASaver.Calibration import correct_delay
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Settings.Sweep import Sweep, SweepMode

logger = logging.getLogger(__name__)


def truncate(values: List[List[Tuple]], count: int) -> List[List[Tuple]]:
    """truncate drops extrema from data list if averaging is active"""
    keep = len(values) - count
    logger.debug("Truncating from %d values to %d", len(values), keep)
    if count < 1 or keep < 1:
        logger.info("Not doing illegal truncate")
        return values
    truncated = []
    for valueset in np.swapaxes(values, 0, 1).tolist():
        avg = complex(*np.average(valueset, 0))
        truncated.append(
            sorted(valueset,
                   key=lambda v, a=avg:
                   abs(a - complex(*v)))[:keep])
    return np.swapaxes(truncated, 0, 1).tolist()


class WorkerSignals(QtCore.QObject):
    updated = pyqtSignal()
    finished = pyqtSignal()
    sweepError = pyqtSignal()


class SweepWorker(QtCore.QRunnable):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        logger.info("Initializing SweepWorker")
        self.signals = WorkerSignals()
        self.app = app
        self.sweep = Sweep()
        self.setAutoDelete(False)
        self.percentage = 0
        self.data11: List[Datapoint] = []
        self.data21: List[Datapoint] = []
        self.rawData11: List[Datapoint] = []
        self.rawData21: List[Datapoint] = []
        self.init_data()
        self.stopped = False
        self.running = False
        self.error_message = ""
        self.offsetDelay = 0

    @pyqtSlot()
    def run(self):
        try:
            self._run()
        except BaseException as exc:  # pylint: disable=broad-except
            logger.exception("%s", exc)
            self.gui_error(f"ERROR during sweep\n\nStopped\n\n{exc}")
            return
            # raise exc

    def _run(self):
        logger.info("Initializing SweepWorker")
        self.running = True
        self.percentage = 0

        if not self.app.vna.connected():
            logger.debug(
                "Attempted to run without being connected to the NanoVNA")
            self.running = False
            return

        with self.app.sweep.lock:
            sweep = self.app.sweep.copy()

        averages = 1
        if sweep.properties.mode == SweepMode.AVERAGE:
            averages = sweep.properties.averages[0]
            logger.info("%d averages", averages)

        if sweep != self.sweep:  # parameters changed
            self.sweep = sweep
            self.init_data()

        while True:
            for i in range(sweep.segments):
                logger.debug("Sweep segment no %d", i)
                if self.stopped:
                    logger.debug("Stopping sweeping as signalled")
                    break
                start, stop = sweep.get_index_range(i)

                try:
                    freq, values11, values21 = self.readAveragedSegment(
                        start, stop, averages)
                    self.percentage = (i + 1) * 100 / sweep.segments
                    self.updateData(freq, values11, values21, i)
                except ValueError as e:
                    self.gui_error(str(e))
            else:
                if sweep.properties.mode == SweepMode.CONTINOUS:
                    continue
            break

        if sweep.segments > 1:
            start = sweep.start
            end = sweep.end
            logger.debug("Resetting NanoVNA sweep to full range: %d to %d",
                         start, end)
            self.app.vna.resetSweep(start, end)

        self.percentage = 100
        logger.debug('Sending "finished" signal')
        self.signals.finished.emit()
        self.running = False

    def init_data(self):
        self.data11 = []
        self.data21 = []
        self.rawData11 = []
        self.rawData21 = []
        for freq in self.sweep.get_frequencies():
            self.data11.append(Datapoint(freq, 0.0, 0.0))
            self.data21.append(Datapoint(freq, 0.0, 0.0))
            self.rawData11.append(Datapoint(freq, 0.0, 0.0))
            self.rawData21.append(Datapoint(freq, 0.0, 0.0))
        logger.debug("Init data length: %s", len(self.data11))

    def updateData(self, frequencies, values11, values21, index):
        # Update the data from (i*101) to (i+1)*101
        logger.debug(
            "Calculating data and inserting in existing data at index %d",
            index)
        offset = self.sweep.points * index
        v11 = values11[:]
        v21 = values21[:]
        raw_data11 = []
        raw_data21 = []

        for freq in frequencies:
            real11, imag11 = v11.pop(0)
            real21, imag21 = v21.pop(0)
            raw_data11.append(Datapoint(freq, real11, imag11))
            raw_data21.append(Datapoint(freq, real21, imag21))

        data11, data21 = self.applyCalibration(raw_data11, raw_data21)
        logger.debug("update Freqs: %s, Offset: %s", len(frequencies), offset)
        for i in range(len(frequencies)):
            self.data11[offset + i] = data11[i]
            self.data21[offset + i] = data21[i]
            self.rawData11[offset + i] = raw_data11[i]
            self.rawData21[offset + i] = raw_data21[i]

        logger.debug("Saving data to application (%d and %d points)",
                     len(self.data11), len(self.data21))
        self.app.saveData(self.data11, self.data21)
        logger.debug('Sending "updated" signal')
        self.signals.updated.emit()

    def applyCalibration(self,
                         raw_data11: List[Datapoint],
                         raw_data21: List[Datapoint]
                         ) -> Tuple[List[Datapoint], List[Datapoint]]:

        data11: List[Datapoint] = []
        data21: List[Datapoint] = []

        if not self.app.calibration.isCalculated:
            data11 = raw_data11.copy()
            data21 = raw_data21.copy()
        else:
            if self.app.calibration.isValid1Port():
                for dp in raw_data11:
                    data11.append(self.app.calibration.correct11(dp))
            else:
                data11 = raw_data11.copy()

            if self.app.calibration.isValid2Port():
                for dp in raw_data21:
                    data21.append(self.app.calibration.correct21(dp))
            else:
                data21 = raw_data21.copy()

        if self.offsetDelay != 0:
            data11 = [correct_delay(dp, self.offsetDelay, reflect=True) for dp in data11]
            data21 = [correct_delay(dp, self.offsetDelay) for dp in data21]

        return data11, data21

    def readAveragedSegment(self, start, stop, averages=1):
        values11 = []
        values21 = []
        freq = []
        logger.info("Reading from %d to %d. Averaging %d values",
                    start, stop, averages)
        for i in range(averages):
            if self.stopped:
                logger.debug("Stopping averaging as signalled.")
                if averages == 1:
                    break
                logger.warning("Stop during average. Discarding sweep result.")
                return [], [], []
            logger.debug("Reading average no %d / %d", i + 1, averages)
            retry = 0
            tmp11 = []
            while not tmp11 and retry < 5:
                sleep(0.5 * retry)
                retry += 1
                freq, tmp11, tmp21 = self.readSegment(start, stop)
                if retry > 1:
                    logger.error("retry %s readSegment(%s,%s)",
                                 retry, start, stop)
                    sleep(0.5)
            values11.append(tmp11)
            values21.append(tmp21)
            self.percentage += 100 / (self.sweep.segments * averages)
            self.signals.updated.emit()

        if not values11:
            raise IOError("Invalid data during swwep")

        truncates = self.sweep.properties.averages[1]
        if truncates > 0 and averages > 1:
            logger.debug("Truncating %d values by %d",
                         len(values11), truncates)
            values11 = truncate(values11, truncates)
            values21 = truncate(values21, truncates)

        logger.debug("Averaging %d values", len(values11))
        values11 = np.average(values11, 0).tolist()
        values21 = np.average(values21, 0).tolist()

        return freq, values11, values21

    def readSegment(self, start, stop):
        logger.debug("Setting sweep range to %d to %d", start, stop)
        self.app.vna.setSweep(start, stop)

        frequencies = self.app.vna.readFrequencies()
        logger.debug("Read %s frequencies", len(frequencies))
        values11 = self.readData("data 0")
        values21 = self.readData("data 1")
        if not len(frequencies) == len(values11) == len(values21):
            logger.info("No valid data during this run")
            return [], [], []
        return frequencies, values11, values21

    def readData(self, data):
        logger.debug("Reading %s", data)
        done = False
        returndata = []
        count = 0
        while not done:
            done = True
            returndata = []
            tmpdata = self.app.vna.readValues(data)
            logger.debug("Read %d values", len(tmpdata))
            for d in tmpdata:
                a, b = d.split(" ")
                try:
                    if self.app.vna.validateInput and (
                            abs(float(a)) > 9.5 or
                            abs(float(b)) > 9.5):
                        logger.warning(
                            "Got a non plausible data value: (%s)", d)
                        done = False
                        break
                    returndata.append((float(a), float(b)))
                except ValueError as exc:
                    logger.exception("An exception occurred reading %s: %s",
                                     data, exc)
                    done = False
            if not done:
                logger.debug("Re-reading %s", data)
                sleep(0.2)
                count += 1
                if count == 5:
                    logger.error("Tried and failed to read %s %d times.",
                                 data, count)
                    logger.debug("trying to reconnect")
                    self.app.vna.reconnect()
                if count >= 10:
                    logger.critical(
                        "Tried and failed to read %s %d times. Giving up.",
                        data, count)
                    raise IOError(
                        f"Failed reading {data} {count} times.\n"
                        f"Data outside expected valid ranges,"
                        f" or in an unexpected format.\n\n"
                        f"You can disable data validation on the"
                        f"device settings screen.")
        return returndata

    def gui_error(self, message: str):
        self.error_message = message
        self.stopped = True
        self.running = False
        self.signals.sweepError.emit()
