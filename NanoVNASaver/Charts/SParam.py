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
import math
import logging
from typing import List

from PyQt5 import QtGui

from NanoVNASaver import Defaults
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Frequency import FrequencyChart
from NanoVNASaver.Charts.LogMag import LogMagChart

logger = logging.getLogger(__name__)


class SParameterChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.minDisplayValue = -1
        self.maxDisplayValue = 1
        self.fixedValues = True

        self.y_action_automatic.setChecked(False)
        self.y_action_fixed_span.setChecked(True)

        self.min_value = 0
        self.max_value = 1
        self.span = 1

        self.isInverted = False

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Chart.color.text))
        qp.drawText(int(round(self.dim.width / 2)) - 20, 15, self.name)
        qp.drawText(10, 15, "Real")
        qp.drawText(self.leftMargin + self.dim.width - 15, 15, "Imag")
        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin + self.dim.height + 5)
        qp.drawLine(self.leftMargin - 5, self.topMargin + self.dim.height,
                    self.leftMargin + self.dim.width, self.topMargin + self.dim.height)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return

        self._set_start_stop()

        # Draw bands if required
        if Defaults.cfg.chart.show_bands:
            self.drawBands(qp, self.fstart, self.fstop)

        if self.fixedValues:
            max_value = self.maxDisplayValue
            min_value = self.minDisplayValue
        else:
            # Find scaling
            min_value = -1
            max_value = 1
            # for d in self.data:
            #     val = d.re
            #     min_value = min(min_value, val)
            #     max_value = max(max_value, val)
            # for d in self.reference:  # Also check min/max for the reference sweep
            #     if d.freq < self.fstart or d.freq > self.fstop:
            #         continue
            #     val = self.logMag(d)
            #     min_value = min(min_value, val)
            #     max_value = max(max_value, val)
            # min_value = round_floor(min_value, -1)
            # self.min_value = min_value
            # max_value = round_ceil(max_value, -1)
            # self.max_value = max_value

        self.max_value = max_value
        self.min_value = min_value

        span = max_value - min_value
        if span == 0:
            span = 0.01
        self.span = span

        tick_count = math.floor(self.dim.height / 60)
        tick_step = self.span / tick_count

        for i in range(tick_count):
            val = min_value + i * tick_step
            y = self.topMargin + round((max_value - val) / span * self.dim.height)
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.dim.width, y)
            if val > min_value and val != max_value:
                qp.setPen(QtGui.QPen(Chart.color.text))
                qp.drawText(3, y + 4, str(round(val, 2)))

        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.dim.width, self.topMargin)
        qp.setPen(Chart.color.text)
        qp.drawText(3, self.topMargin + 4, str(max_value))
        qp.drawText(3, self.dim.height + self.topMargin, str(min_value))
        self.drawFrequencyTicks(qp)

        self.drawData(qp, self.data, Chart.color.sweep, self.getReYPosition)
        self.drawData(qp, self.reference, Chart.color.reference, self.getReYPosition)
        self.drawData(qp, self.data, Chart.color.sweep_secondary, self.getImYPosition)
        self.drawData(qp, self.reference, Chart.color.reference_secondary, self.getImYPosition)
        self.drawMarkers(qp, y_function=self.getReYPosition)
        self.drawMarkers(qp, y_function=self.getImYPosition)

    def getYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.max_value - d.re) / self.span * self.dim.height)

    def getReYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.max_value - d.re) / self.span * self.dim.height)

    def getImYPosition(self, d: Datapoint) -> int:
        return self.topMargin + round((self.max_value - d.im) / self.span * self.dim.height)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.max_value)
        return [val]

    def logMag(self, p: Datapoint) -> float:
        return -p.gain if self.isInverted else p.gain

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        return new_chart
