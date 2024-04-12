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


from time import sleep
import numpy as np
import threading
from .RFTools import corr_att_data

from .Sweep import Sweep, SweepMode
from .RFTools import Datapoint


def truncate(values: list[list[tuple]], count: int, verbose=False) -> list[list[tuple]]:
    """truncate drops extrema from data list if averaging is active"""
    keep = len(values) - count
    if verbose:
        print("Truncating from %d values to %d", len(values), keep)
    if count < 1 or keep < 1:
        if verbose:
            print("Not doing illegal truncate")
        return values
    truncated = []
    for valueset in np.swapaxes(values, 0, 1).tolist():
        avg = complex(*np.average(valueset, 0))
        truncated.append(
            sorted(valueset, key=lambda v, a=avg: abs(a - complex(*v)))[:keep]
        )
    return np.swapaxes(truncated, 0, 1).tolist()


class SweepWorker:
    def __init__(self, vna, calibration, data, verbose=False):
        if verbose:
            print("Initializing SweepWorker")
        self.sweep = Sweep()
        self.percentage = 0
        self.data11: list[Datapoint] = []
        self.data21: list[Datapoint] = []
        self.rawData11: list[Datapoint] = []
        self.rawData21: list[Datapoint] = []
        self.verbose = verbose
        self.vna = vna
        self.calibration = calibration
        self.data = data
        self.init_data()
        self.stopped = False
        self.running = False
        self.error_message = ""
        self.offsetDelay = 0
        self.dataLock = threading.Lock()
        self.s21att = 0.0

    def saveData(
        self, data11, data21
    ):  # This function is werid and should probably be rewritten.
        with self.dataLock:
            self.data.s11 = data11
            self.data.s21 = data21
            if self.s21att > 0:
                self.data.s21 = corr_att_data(self.data.s21, self.s21att)

    def run(self) -> None:
        try:
            self._run()
        except BaseException as exc:  # pylint: disable=broad-except
            print("%s", exc)
            print(f"ERROR during sweep\n\nStopped\n\n{exc}")
            if self.verbose:
                raise exc

    def _run(self) -> None:
        if self.verbose:
            print("Initializing SweepWorker")
        if not self.vna.connected():
            if self.verbose:
                print("Attempted to run without being connected to the NanoVNA")
            self.running = False
            return

        self.running = True
        self.percentage = 0

        sweep = self.sweep.copy()

        if sweep != self.sweep:  # parameters changed
            self.sweep = sweep
            self.init_data()

        self._run_loop()

        if sweep.segments > 1:
            start = sweep.start
            end = sweep.end
            if self.verbose:
                print("Resetting NanoVNA sweep to full range: %d to %d", start, end)
            self.vna.resetSweep(start, end)

        self.percentage = 100
        if self.verbose:
            print('Sending "finished" signal')
        self.running = False

    def _run_loop(self) -> None:
        sweep = self.sweep
        averages = (
            sweep.properties.averages[0]
            if sweep.properties.mode == SweepMode.AVERAGE
            else 1
        )
        if self.verbose:
            print("%d averages", averages)

        while True:
            for i in range(sweep.segments):
                if self.verbose:
                    print("Sweep segment no %d", i)
                if self.stopped:
                    if self.verbose:
                        print("Stopping sweeping as signalled")
                    break
                start, stop = sweep.get_index_range(i)

                freq, values11, values21 = self.readAveragedSegment(
                    start, stop, averages
                )
                self.percentage = (i + 1) * 100 / sweep.segments
                self.updateData(freq, values11, values21, i)
            if sweep.properties.mode != SweepMode.CONTINOUS or self.stopped:
                break

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
        if self.verbose:
            print("Init data length: %s", len(self.data11))

    def updateData(self, frequencies, values11, values21, index):
        # Update the data from (i*101) to (i+1)*101
        if self.verbose:
            print("Calculating data and inserting in existing data at index %d", index)
        offset = self.sweep.points * index

        raw_data11 = [
            Datapoint(freq, values11[i][0], values11[i][1])
            for i, freq in enumerate(frequencies)
        ]
        raw_data21 = [
            Datapoint(freq, values21[i][0], values21[i][1])
            for i, freq in enumerate(frequencies)
        ]

        data11, data21 = self.applyCalibration(raw_data11, raw_data21)
        if self.verbose:
            print("update Freqs: %s, Offset: %s", len(frequencies), offset)
        for i in range(len(frequencies)):
            self.data11[offset + i] = data11[i]
            self.data21[offset + i] = data21[i]
            self.rawData11[offset + i] = raw_data11[i]
            self.rawData21[offset + i] = raw_data21[i]

        if self.verbose:
            print(
                "Saving data to application (%d and %d points)",
                len(self.data11),
                len(self.data21),
            )
        self.saveData(self.data11, self.data21)
        if self.verbose:
            print('Sending "updated" signal')

    def applyCalibration(
        self, raw_data11: list[Datapoint], raw_data21: list[Datapoint]
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        data11: list[Datapoint] = []
        data21: list[Datapoint] = []

        if not self.calibration.isCalculated:
            data11 = raw_data11.copy()
            data21 = raw_data21.copy()
        elif self.calibration.isValid1Port():
            data11.extend(self.calibration.correct11(dp) for dp in raw_data11)
        else:
            data11 = raw_data11.copy()

        if self.calibration.isValid2Port():
            for counter, dp in enumerate(raw_data21):
                dp11 = raw_data11[counter]
                data21.append(self.calibration.correct21(dp, dp11))
        else:
            data21 = raw_data21

        if self.offsetDelay != 0:
            data11 = [
                self.calibration.correct_delay(dp, self.offsetDelay, reflect=True)
                for dp in data11
            ]
            data21 = [
                self.calibration.correct_delay(dp, self.offsetDelay) for dp in data21
            ]

        return data11, data21

    def readAveragedSegment(self, start, stop, averages=1):
        values11 = []
        values21 = []
        freq = []
        if self.verbose:
            print("Reading from %d to %d. Averaging %d values", start, stop, averages)
        for i in range(averages):
            if self.stopped:
                if self.verbose:
                    print("Stopping averaging as signalled.")
                if averages == 1:
                    break
                if self.verbose:
                    print("Stop during average. Discarding sweep result.")
                return [], [], []
            if self.verbose:
                print("Reading average no %d / %d", i + 1, averages)
            retry = 0
            tmp11 = []
            tmp21 = []
            while not tmp11 and retry < 5:
                sleep(0.5 * retry)
                retry += 1
                freq, tmp11, tmp21 = self.readSegment(start, stop)
                if retry > 1:
                    if self.verbose:
                        print("retry %s readSegment(%s,%s)", retry, start, stop)
                    sleep(0.5)
            values11.append(tmp11)
            values21.append(tmp21)
            self.percentage += 100 / (self.sweep.segments * averages)

        if not values11:
            raise IOError("Invalid data during swwep")

        truncates = self.sweep.properties.averages[1]
        if truncates > 0 and averages > 1:
            if self.verbose:
                print("Truncating %d values by %d", len(values11), truncates)
            values11 = truncate(values11, truncates)
            values21 = truncate(values21, truncates)

        if self.verbose:
            print("Averaging %d values", len(values11))
        values11 = np.average(values11, 0).tolist()
        values21 = np.average(values21, 0).tolist()

        return freq, values11, values21

    def readSegment(self, start, stop):
        if self.verbose:
            print("Setting sweep range to %d to %d", start, stop)
        self.vna.setSweep(start, stop)

        frequencies = self.vna.readFrequencies()
        if self.verbose:
            print("Read %s frequencies", len(frequencies))
        values11 = self.readData("data 0")
        values21 = self.readData("data 1")
        if not len(frequencies) == len(values11) == len(values21):
            if self.verbose:
                print("No valid data during this run")
            return [], [], []
        return frequencies, values11, values21

    def readData(self, data):
        if self.verbose:
            print("Reading %s", data)
        done = False
        returndata = []
        count = 0
        while not done:
            done = True
            returndata = []
            tmpdata = self.vna.readValues(data)
            if self.verbose:
                print("Read %d values", len(tmpdata))
            for d in tmpdata:
                a, b = d.split(" ")
                try:
                    if self.vna.validateInput and (
                        abs(float(a)) > 9.5 or abs(float(b)) > 9.5
                    ):
                        if self.verbose:
                            print("Got a non plausible data value: (%s)", d)
                        done = False
                        break
                    returndata.append((float(a), float(b)))
                except ValueError as exc:
                    print("An exception occurred reading %s: %s", data, exc)
                    done = False
            if not done:
                if self.verbose:
                    print("Re-reading %s", data)
                sleep(0.2)
                count += 1
                if count == 5:
                    if self.verbose:
                        print("Tried and failed to read %s %d times.", data, count)
                    if self.verbose:
                        print("trying to reconnect")
                    self.vna.reconnect()
                if count >= 10:
                    print(
                        "Tried and failed to read %s %d times. Giving up.", data, count
                    )
                    raise IOError(
                        f"Failed reading {data} {count} times.\n"
                        f"Data outside expected valid ranges,"
                        f" or in an unexpected format.\n\n"
                        f"You can disable data validation on the"
                        f"device settings screen."
                    )
        return returndata

    def gui_error(self, message: str):
        self.error_message = message
        self.stopped = True
        self.running = False
