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
from enum import Enum
from time import sleep
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from NanoVNASaver.Calibration import correct_delay
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Settings.Sweep import Sweep, SweepMode

if TYPE_CHECKING:
    from NanoVNASaver.Hardware.VNA import VNA
    from NanoVNASaver.NanoVNASaver import NanoVNASaver as NanoVNA

logger = logging.getLogger(__name__)

VALUE_MAX: float = 9.5
RETRIES_RECONNECT: int = 5
RETRIES_MAX: int = 10


def truncate(values: list[list[complex]], count: int) -> list[list[complex]]:
    """truncate drops extrema from data list if averaging is active"""
    keep = len(values) - count
    logger.debug("Truncating from %d values to %d", len(values), keep)
    if count < 1 or keep < 1:
        logger.info("Not doing illegal truncate")
        return values
    truncated = []
    for valueset in np.swapaxes(values, 0, 1).tolist():
        avg = np.average(valueset)
        truncated.append(
            sorted(valueset, key=lambda v, a=avg: abs(a - v))[:keep]
        )
    return np.swapaxes(truncated, 0, 1).tolist()


class WorkerSignals(QObject):
    updated = pyqtSignal()
    finished = pyqtSignal()
    sweep_error = pyqtSignal()


class SweepState(Enum):
    STOPPED = 0
    RUNNING = 1


class SweepWorker(QRunnable):
    def __init__(self, app: "NanoVNA") -> None:
        super().__init__()
        logger.info("Initializing SweepWorker")
        self.signals: WorkerSignals = WorkerSignals()
        self.app: NanoVNA = app
        self.sweep = Sweep()
        self.setAutoDelete(False)
        self.percentage: float = 0.0
        self.data11: list[Datapoint] = []
        self.data21: list[Datapoint] = []
        self.rawData11: list[Datapoint] = []
        self.rawData21: list[Datapoint] = []
        self.init_data()
        self.state: "SweepState" = SweepState.STOPPED
        self.error_message: str = ""
        self.offsetDelay: float = 0.0

    @pyqtSlot()
    def run(self) -> None:
        try:
            self._run()
        except BaseException as exc:  # pylint: disable=broad-except
            self.state = SweepState.STOPPED
            logger.exception("%s", exc)
            self.gui_error(f"ERROR during sweep\n\nStopped\n\n{exc}")
            if logger.isEnabledFor(logging.DEBUG):
                raise exc

    def _run(self) -> None:
        logger.info("Initializing SweepWorker")
        if not self.app.vna.connected():
            logger.debug(
                "Attempted to run without being connected to the NanoVNA"
            )
            return

        self.state = SweepState.RUNNING
        self.percentage = 0.0

        sweep = self.app.sweep.copy()

        if sweep != self.sweep:  # parameters changed
            self.sweep = sweep
            self.init_data()

        self._run_loop()

        if sweep.segments > 1:
            start = sweep.start
            end = sweep.end
            logger.debug(
                "Resetting NanoVNA sweep to full range: %d to %d", start, end
            )
            self.app.vna.resetSweep(start, end)

        self.percentage = 100.0
        logger.debug('Sending "finished" signal')
        self.signals.finished.emit()
        self.state = SweepState.STOPPED

    def _run_loop(self) -> None:
        sweep = self.sweep
        averages = (
            sweep.properties.averages[0]
            if sweep.properties.mode == SweepMode.AVERAGE
            else 1
        )
        logger.info("%d averages", averages)

        while True:
            for i in range(sweep.segments):
                logger.debug("Sweep segment no %d", i)
                if self.state == SweepState.STOPPED:
                    logger.debug("Stopping sweeping as signalled")
                    break
                start, stop = sweep.get_index_range(i)

                freq, values11, values21 = self.read_averaged_segment(
                    start, stop, averages
                )
                self.percentage = (i + 1) * 100 / sweep.segments
                self.update_data(freq, values11, values21, i)
            if (
                sweep.properties.mode != SweepMode.CONTINOUS
                or self.state == SweepState.STOPPED
            ):
                break

    def init_data(self) -> None:
        self.data11: list[Datapoint] = []
        self.data21: list[Datapoint] = []
        self.rawData11: list[Datapoint] = []
        self.rawData21: list[Datapoint] = []
        for freq in self.sweep.get_frequencies():
            self.data11.append(Datapoint(freq, 0.0, 0.0))
            self.data21.append(Datapoint(freq, 0.0, 0.0))
            self.rawData11.append(Datapoint(freq, 0.0, 0.0))
            self.rawData21.append(Datapoint(freq, 0.0, 0.0))
        logger.debug("Init data length: %s", len(self.data11))

    def update_data(
        self,
        frequencies: list[int],
        values11: list[complex],
        values21: list[complex],
        index: int,
    ) -> None:
        # Update the data from (i*101) to (i+1)*101
        logger.debug(
            "Calculating data and inserting in existing data at index %d", index
        )
        offset = self.sweep.points * index

        raw_data11 = [
            Datapoint(freq, values11[i].real, values11[i].imag)
            for i, freq in enumerate(frequencies)
        ]
        raw_data21 = [
            Datapoint(freq, values21[i].real, values21[i].imag)
            for i, freq in enumerate(frequencies)
        ]

        data11, data21 = self.applyCalibration(raw_data11, raw_data21)
        logger.debug("update Freqs: %s, Offset: %s", len(frequencies), offset)
        for i in range(len(frequencies)):
            self.data11[offset + i] = data11[i]
            self.data21[offset + i] = data21[i]
            self.rawData11[offset + i] = raw_data11[i]
            self.rawData21[offset + i] = raw_data21[i]

        logger.debug(
            "Saving data to application (%d and %d points)",
            len(self.data11),
            len(self.data21),
        )
        self.app.saveData(self.data11, self.data21)
        logger.debug('Sending "updated" signal')
        self.signals.updated.emit()

    def applyCalibration(
        self, raw_data11: list[Datapoint], raw_data21: list[Datapoint]
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        data11: list[Datapoint] = []
        data21: list[Datapoint] = []

        if not self.app.calibration.isCalculated:
            data11 = raw_data11.copy()
            data21 = raw_data21.copy()
        elif self.app.calibration.isValid1Port():
            data11.extend(
                self.app.calibration.correct11(dp) for dp in raw_data11
            )
        else:
            data11 = raw_data11.copy()

        if self.app.calibration.isValid2Port():
            for counter, dp in enumerate(raw_data21):
                dp11 = raw_data11[counter]
                data21.append(self.app.calibration.correct21(dp, dp11))
        else:
            data21 = raw_data21

        if self.offsetDelay != 0.0:
            data11 = [
                correct_delay(dp, self.offsetDelay, reflect=True)
                for dp in data11
            ]
            data21 = [correct_delay(dp, self.offsetDelay) for dp in data21]

        return data11, data21

    def read_averaged_segment(
        self, start: int, stop: int, averages: int = 1
    ) -> tuple[list[int], list[complex], list[complex]]:
        logger.info(
            "Reading from %d to %d. Averaging %d values", start, stop, averages
        )

        freq: list[int] = []
        values11: list[complex] = []
        values21: list[complex] = []

        for i in range(averages):
            if self.state == SweepState.STOPPED:
                logger.debug("Stopping averaging as signalled.")
                if averages == 1:
                    break
                logger.warning("Stop during average. Discarding sweep result.")
                return [], [], []
            logger.debug("Reading average no %d / %d", i + 1, averages)
            retries = RETRIES_RECONNECT
            tmp_11: list[complex] = []
            tmp_21: list[complex] = []
            while retries and not tmp_11:
                if retries < RETRIES_RECONNECT:
                    logger.warning("retry readSegment(%s,%s)", start, stop)
                    sleep(0.5)
                retries -= 1
                freq, tmp_11, tmp_21 = self.read_segment(start, stop)

            if not tmp_11:
                raise IOError("Invalid data during swwep")

            values11.append(tmp_11)
            values21.append(tmp_21)
            self.percentage += 100 / (self.sweep.segments * averages)
            self.signals.updated.emit()

        if not values11:
            raise IOError("Invalid data during swwep")

        truncates = self.sweep.properties.averages[1]
        if truncates > 0 and averages > 1:
            logger.debug("Truncating %d values by %d", len(values11), truncates)
            values11 = truncate(values11, truncates)
            values21 = truncate(values21, truncates)

        logger.debug("Averaging %d values", len(values11))
        values11: list[complex] = np.average(values11, axis=0).tolist()
        values21: list[complex] = np.average(values21, axis=0).tolist()
        return freq, values11, values21

    def read_segment(
        self, start: int, stop: int
    ) -> tuple[list[int], list[complex], list[complex]]:
        logger.debug("Setting sweep range to %d to %d", start, stop)
        self.app.vna.setSweep(start, stop)

        frequencies = self.app.vna.read_frequencies()
        logger.debug("Read %s frequencies", len(frequencies))
        values11 = self.read_data("data 0")
        values21 = self.read_data("data 1")
        if not len(frequencies) == len(values11) == len(values21):
            logger.info("No valid data during this run")
            frequencies = []
            values11 = values21 = []
        return frequencies, values11, values21

    def read_data(self, data) -> list[complex]:
        logger.debug("Reading %s", data)

        vna: "VNA" = self.app.vna  # shortcut to device
        retries = RETRIES_MAX
        while retries:
            retries -= 1
            try:
                result = vna.readValues(data)
                logger.debug("Read %d values", len(result))
                if vna.validateInput and any(
                    abs(v) > VALUE_MAX for v in result
                ):
                    logger.error("Got a non plausible data: (%s)", data)
                else:
                    return result
            except ValueError as exc:
                logger.exception(
                    "An exception occurred reading %s: %s", data, exc
                )
            logger.error("Re-reading %s", data)
            sleep(0.2)
            vna.reconnect()

        logger.critical(
            "Tried and failed to read %s %s times. Giving up.",
            data,
            RETRIES_MAX,
        )
        raise IOError(
            f"Failed reading {data} {RETRIES_MAX} times.\n"
            f"Data outside expected valid ranges,"
            f" or in an unexpected format.\n\n"
            f"You can disable data validation on the"
            f"device settings screen."
        )

    def gui_error(self, message: str) -> None:
        self.error_message = message
        self.state = SweepState.STOPPED
        self.signals.sweep_error.emit()
