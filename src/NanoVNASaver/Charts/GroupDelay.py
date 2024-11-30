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
import math

import numpy as np
from PyQt6 import QtGui

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.RFTools import Datapoint

from .Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class GroupDelayChart(FrequencyChart):
    def __init__(self, name="", reflective=True):
        super().__init__(name)

        self.name_unit = "ns"

        self.leftMargin = 40
        self.dim.width = 250
        self.dim.height = 250
        self.fstart = 0
        self.fstop = 0
        self.minDelay = 0
        self.maxDelay = 0
        self.span = 0

        self.reflective = reflective

        self.groupDelay = []
        self.groupDelayReference = []

        self.minDisplayValue = -180
        self.maxDisplayValue = 180

    def copy(self):
        new_chart: GroupDelayChart = super().copy()
        new_chart.reflective = self.reflective
        new_chart.groupDelay = self.groupDelay.copy()
        new_chart.groupDelayReference = self.groupDelay.copy()
        return new_chart

    def setReference(self, data):
        self.reference = data
        self.calculateGroupDelay()

    def setData(self, data):
        self.data = data
        self.calculateGroupDelay()

    def calculateGroupDelay(self):
        self.groupDelay = self.calc_data(self.data)
        self.groupDelayReference = self.calc_data(self.reference)
        self.update()

    def calc_data(self, data: list[Datapoint]):
        data_len = len(data)
        if data_len <= 1:
            return []
        unwrapped = np.degrees(np.unwrap([d.phase for d in data]))
        delay_data = []
        for i, d in enumerate(data):
            # TODO: Replace with call to RFTools.groupDelay
            if i == 0:
                phase_change = unwrapped[1] - unwrapped[i]
                freq_change = data[1].freq - d.freq
            elif i == data_len - 1:
                phase_change = unwrapped[-1] - unwrapped[-2]
                freq_change = d.freq - data[-2].freq
            else:
                phase_change = unwrapped[i + 1] - unwrapped[i - 1]
                freq_change = data[i + 1].freq - data[i - 1].freq
            delay = (-phase_change / (freq_change * 360)) * 10e8
            if not self.reflective:
                delay /= 2
            delay_data.append(delay)
        return delay_data

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(Chart.color.sweep)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Chart.color.sweep)
        line_pen.setWidth(self.dim.line)

        if self.fixedValues:
            min_delay = self.minDisplayValue
            max_delay = self.maxDisplayValue
        elif self.data:
            min_delay = math.floor(np.min(self.groupDelay))
            max_delay = math.ceil(np.max(self.groupDelay))
        elif self.reference:
            min_delay = math.floor(np.min(self.groupDelayReference))
            max_delay = math.ceil(np.max(self.groupDelayReference))

        span = max_delay - min_delay
        if span == 0:
            span = 0.01
        self.minDelay = min_delay
        self.maxDelay = max_delay
        self.span = span

        tickcount = math.floor(self.dim.height / 60)
        for i in range(tickcount):
            delay = min_delay + span * i / tickcount
            y = self.topMargin + round(
                (self.maxDelay - delay) / self.span * self.dim.height
            )
            if delay not in {min_delay, max_delay}:
                qp.setPen(QtGui.QPen(Chart.color.text))
                # TODO use format class
                digits = (
                    0
                    if delay == 0
                    else max(0, min(2, math.floor(3 - math.log10(abs(delay)))))
                )
                delaystr = str(round(delay, digits if digits != 0 else None))
                qp.drawText(3, y + 3, delaystr)
                qp.setPen(QtGui.QPen(Chart.color.foreground))
                qp.drawLine(
                    self.leftMargin - 5, y, self.leftMargin + self.dim.width, y
                )

        qp.drawLine(
            self.leftMargin - 5,
            self.topMargin,
            self.leftMargin + self.dim.width,
            self.topMargin,
        )
        qp.setPen(Chart.color.text)
        qp.drawText(3, self.topMargin + 5, str(max_delay))
        qp.drawText(3, self.dim.height + self.topMargin, str(min_delay))

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

        self.drawFrequencyTicks(qp)

        self.draw_data(qp, Chart.color.sweep, self.data, self.groupDelay)
        self.draw_data(
            qp, Chart.color.reference, self.reference, self.groupDelayReference
        )

        self.drawMarkers(qp)

    def draw_data(
        self,
        qp: QtGui.QPainter,
        color: QtGui.QColor,
        data: list[Datapoint],
        delay: list[Datapoint],
    ):
        pen = QtGui.QPen(color)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.dim.line)
        qp.setPen(pen)
        for i, d in enumerate(data):
            x = self.getXPosition(d)
            y = self.getYPositionFromDelay(delay[i])
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.flag.draw_lines and i > 0:
                prevx = self.getXPosition(data[i - 1])
                prevy = self.getYPositionFromDelay(delay[i - 1])
                qp.setPen(line_pen)
                if self.isPlotable(x, y):
                    if self.isPlotable(prevx, prevy):
                        qp.drawLine(x, y, prevx, prevy)
                    else:
                        new_x, new_y = self.getPlotable(x, y, prevx, prevy)
                        qp.drawLine(x, y, new_x, new_y)
                elif self.isPlotable(prevx, prevy):
                    new_x, new_y = self.getPlotable(prevx, prevy, x, y)
                    qp.drawLine(prevx, prevy, new_x, new_y)
                qp.setPen(pen)

    def getYPosition(self, d: Datapoint) -> int:
        # TODO: Find a faster way than these expensive "d in data" lookups
        try:
            delay = self.groupDelay[self.data.index(d)]
        except ValueError:
            try:
                delay = self.groupDelayReference[self.reference.index(d)]
            except ValueError:
                delay = 0
        return self.getYPositionFromDelay(delay)

    def getYPositionFromDelay(self, delay: float) -> int:
        return self.topMargin + int(
            (self.maxDelay - delay) / self.span * self.dim.height
        )

    def valueAtPosition(self, y) -> list[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.maxDelay)
        return [val]
