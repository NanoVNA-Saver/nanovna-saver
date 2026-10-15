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
import threading
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot

from .engine.acquire import (
    SweepStoppedError,
    correct,
    read_averaged_segment,
    read_segment,
    truncate,
)
from .engine.acquire import read_data as _read_data
from .engine.deembed import FixtureSettings
from .engine.dsp import SegmentRunningAverage
from .engine.sweepdata import SweepData, to_datapoints
from .RFTools import Datapoint
from .Settings.Sweep import Sweep, SweepMode

if TYPE_CHECKING:
    from .NanoVNASaver.NanoVNASaver import NanoVNASaver as vna_app

logger = logging.getLogger(__name__)

__all__ = ["SweepWorker", "WorkerSignals", "truncate"]


class WorkerSignals(QObject):
    updated = Signal()
    finished = Signal()
    sweep_error = Signal()


class SweepWorker(QThread):
    # pylint: disable=too-many-instance-attributes
    def __init__(self, app: "vna_app") -> None:
        super().__init__()
        logger.info("Initializing SweepWorker")
        self.signals: WorkerSignals = WorkerSignals()
        self.app = app
        self.sweep = Sweep()
        self.percentage: float = 0.0
        self.error_message: str = ""
        self.offsetDelay: float = 0.0
        self._terminate: bool = False
        self._lock = threading.RLock()

        # processing pipeline settings
        self.smoothing_pct: float = 0.0
        self.fixture = FixtureSettings()
        self.running_average = SegmentRunningAverage(1)

        self.raw = SweepData()
        self.processed = SweepData()
        self.init_data()

    # Compatibility accessors (lists of Datapoints)

    @property
    def rawData11(self) -> list[Datapoint]:
        return self.raw.datapoints("s11")

    @property
    def rawData21(self) -> list[Datapoint]:
        return self.raw.datapoints("s21")

    @property
    def data11(self) -> list[Datapoint]:
        return self.processed.datapoints("s11")

    @data11.setter
    def data11(self, value: list[Datapoint]) -> None:
        self.processed.s11 = np.array([d.z for d in value], dtype=complex)

    @property
    def data21(self) -> list[Datapoint]:
        return self.processed.datapoints("s21")

    @data21.setter
    def data21(self, value: list[Datapoint]) -> None:
        self.processed.s21 = np.array([d.z for d in value], dtype=complex)

    def has_raw_data(self) -> bool:
        return len(self.raw) > 0 and bool(np.any(self.raw.s11))

    @property
    def averaging_count(self) -> int:
        return self.running_average.count

    def set_running_average(self, count: int) -> None:
        self.running_average.set_count(count)

    def processing_tag(self) -> str:
        """Short description of the active processing for chart titles"""
        parts = []
        props = self.sweep.properties
        if props.mode == SweepMode.AVERAGE:
            parts.append(f"Avg {props.averages[0]}")
        elif self.running_average.count > 1:
            parts.append(
                f"Avg {self.running_average.n}/{self.running_average.count}"
            )
        if self.smoothing_pct > 0:
            parts.append(f"Smo {self.smoothing_pct:g}%")
        if self.fixture.port1.active or self.fixture.port2.active:
            parts.append("PortExt")
        if (
            self.fixture.fixture1 is not None
            or self.fixture.fixture2 is not None
        ):
            parts.append("De-emb")
        if self.fixture.z0 != 50.0:
            parts.append(f"Z0 {np.real(self.fixture.z0):g}Ω")
        return " · ".join(parts)

    @Slot()
    def quit(self) -> None:
        logger.debug("Worker quit request")
        self._terminate = True

    @Slot()
    def run(self) -> None:
        self._terminate = False
        try:
            self._run()
        except SweepStoppedError:
            logger.info("Sweep stopped during averaging")
            self.signals.finished.emit()
        except BaseException as exc:  # pylint: disable=broad-except
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

        self.percentage = 0.0

        sweep = self.app.sweep.copy()

        if sweep != self.sweep:  # parameters changed
            self.sweep = sweep
            self.init_data()
        self.running_average.reset()

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
                if self._terminate:
                    logger.debug("Stopping sweeping as signalled")
                    break
                start, stop = sweep.get_index_range(i)

                freq, values11, values21 = self.read_averaged_segment(
                    start, stop, averages
                )
                self.percentage = (i + 1) * 100 / sweep.segments
                self.update_data(freq, values11, values21, i)
            if sweep.properties.mode != SweepMode.CONTINOUS or self._terminate:
                break

    def init_data(self) -> None:
        freq = np.array(list(self.sweep.get_frequencies()), dtype=np.float64)
        zeros = np.zeros(len(freq), dtype=np.complex128)
        with self._lock:
            self.raw = SweepData(freq, zeros.copy(), zeros.copy())
            self.processed = self.raw.copy()
        self.running_average.reset()
        logger.debug("Init data length: %s", len(freq))

    def update_data(
        self,
        frequencies: list[int],
        values11: list[complex],
        values21: list[complex],
        index: int,
    ) -> None:
        logger.debug(
            "Calculating data and inserting in existing data at index %d", index
        )
        offset = self.sweep.points * index
        n = len(frequencies)
        s11 = np.asarray(values11, dtype=np.complex128)
        s21 = np.asarray(values21, dtype=np.complex128)
        if (
            self.sweep.properties.mode == SweepMode.CONTINOUS
            and self.running_average.count > 1
        ):
            both = self.running_average.add(index, np.concatenate([s11, s21]))
            s11, s21 = both[:n], both[n:]
        with self._lock:
            if offset + n > len(self.raw):
                logger.warning("Segment does not fit into sweep data")
                return
            self.raw.freq[offset : offset + n] = frequencies
            self.raw.s11[offset : offset + n] = s11
            self.raw.s21[offset : offset + n] = s21
        self.reprocess(keep_source=False)

    def process(self, raw: SweepData) -> SweepData:
        return correct(
            raw,
            self.app.calibration,
            self.offsetDelay,
            self.fixture,
            self.smoothing_pct,
        )

    def reprocess(self, emit: bool = True, keep_source: bool = True) -> None:
        """Re-run calibration / fixture / smoothing on the stored raw data
        and publish the result to the application"""
        with self._lock:
            if len(self.raw) == 0:
                return
            raw = self.raw.copy()
        processed = self.process(raw)
        with self._lock:
            self.processed = processed
        self.app.saveData(
            processed.datapoints("s11"),
            processed.datapoints("s21"),
            self.app.sweepSource
            if keep_source and self.app.sweepSource
            else None,
        )
        if emit:
            logger.debug('Sending "updated" signal')
            self.signals.updated.emit()

    def applyCalibration(
        self, raw_data11: list[Datapoint], raw_data21: list[Datapoint]
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        raw = SweepData.from_datapoints(raw_data11, raw_data21)
        out = self.process(raw)
        return (
            to_datapoints(out.freq, out.s11),
            to_datapoints(out.freq, out.s21),
        )

    def read_averaged_segment(
        self, start: int, stop: int, averages: int = 1
    ) -> tuple[list[int], list[complex], list[complex]]:
        def progress() -> None:
            self.percentage += 100 / (self.sweep.segments * averages)
            self.signals.updated.emit()

        return read_averaged_segment(
            self.app.vna,
            start,
            stop,
            averages,
            self.sweep.properties.averages[1],
            should_stop=lambda: self._terminate,
            on_progress=progress if averages > 1 else None,
        )

    def read_segment(
        self, start: int, stop: int
    ) -> tuple[list[int], list[complex], list[complex]]:
        return read_segment(self.app.vna, start, stop)

    def read_data(self, data) -> list[complex]:
        return _read_data(self.app.vna, data)

    def gui_error(self, message: str) -> None:
        self.error_message = message
        self.signals.sweep_error.emit()
