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

import numpy as np

from PyQt5 import QtGui

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
        rawData = []
        for d in self.data:
            rawData.append(d.phase)

        rawReference = []
        for d in self.reference:
            rawReference.append(d.phase)

        if len(self.data) > 1:
            unwrappedData = np.degrees(np.unwrap(rawData))
            self.groupDelay = []
            for i in range(len(self.data)):
                # TODO: Replace with call to RFTools.groupDelay
                if i == 0:
                    phase_change = unwrappedData[1] - unwrappedData[0]
                    freq_change = self.data[1].freq - self.data[0].freq
                elif i == len(self.data)-1:
                    idx = len(self.data)-1
                    phase_change = unwrappedData[idx] - unwrappedData[idx-1]
                    freq_change = self.data[idx].freq - self.data[idx-1].freq
                else:
                    phase_change = unwrappedData[i+1] - unwrappedData[i-1]
                    freq_change = self.data[i+1].freq - self.data[i-1].freq
                delay = (-phase_change / (freq_change * 360)) * 10e8
                if not self.reflective:
                    delay /= 2
                self.groupDelay.append(delay)

        if len(self.reference) > 1:
            unwrappedReference = np.degrees(np.unwrap(rawReference))
            self.groupDelayReference = []
            for i in range(len(self.reference)):
                if i == 0:
                    phase_change = unwrappedReference[1] - unwrappedReference[0]
                    freq_change = self.reference[1].freq - self.reference[0].freq
                elif i == len(self.reference)-1:
                    idx = len(self.reference)-1
                    phase_change = unwrappedReference[idx] - unwrappedReference[idx-1]
                    freq_change = self.reference[idx].freq - self.reference[idx-1].freq
                else:
                    phase_change = unwrappedReference[i+1] - unwrappedReference[i-1]
                    freq_change = self.reference[i+1].freq - self.reference[i-1].freq
                delay = (-phase_change / (freq_change * 360)) * 10e8
                if not self.reflective:
                    delay /= 2
                self.groupDelayReference.append(delay)

        self.update()

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
            y = self.topMargin + round((self.maxDelay - delay) / self.span * self.dim.height)
            if delay != min_delay and delay != max_delay:
                qp.setPen(QtGui.QPen(Chart.color.text))
                if delay != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(delay)))))
                    if digits == 0:
                        delaystr = str(round(delay))
                    else:
                        delaystr = str(round(delay, digits))
                else:
                    delaystr = "0"
                qp.drawText(3, y + 3, delaystr)
                qp.setPen(QtGui.QPen(Chart.color.foreground))
                qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.dim.width, y)
        qp.drawLine(self.leftMargin - 5,
                    self.topMargin,
                    self.leftMargin + self.dim.width,
                    self.topMargin)
        qp.setPen(Chart.color.text)
        qp.drawText(3, self.topMargin + 5, str(max_delay))
        qp.drawText(3, self.dim.height + self.topMargin, str(min_delay))

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

        self.drawFrequencyTicks(qp)

        color = Chart.color.sweep
        pen = QtGui.QPen(color)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.dim.line)
        qp.setPen(pen)
        for i in range(len(self.data)):
            x = self.getXPosition(self.data[i])
            y = self.getYPositionFromDelay(self.groupDelay[i])
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.flag.draw_lines and i > 0:
                prevx = self.getXPosition(self.data[i - 1])
                prevy = self.getYPositionFromDelay(self.groupDelay[i - 1])
                qp.setPen(line_pen)
                if self.isPlotable(x, y) and self.isPlotable(prevx, prevy):
                    qp.drawLine(x, y, prevx, prevy)
                elif self.isPlotable(x, y) and not self.isPlotable(prevx, prevy):
                    new_x, new_y = self.getPlotable(x, y, prevx, prevy)
                    qp.drawLine(x, y, new_x, new_y)
                elif not self.isPlotable(x, y) and self.isPlotable(prevx, prevy):
                    new_x, new_y = self.getPlotable(prevx, prevy, x, y)
                    qp.drawLine(prevx, prevy, new_x, new_y)
                qp.setPen(pen)

        color = Chart.color.reference
        pen = QtGui.QPen(color)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(color)
        line_pen.setWidth(self.dim.line)
        qp.setPen(pen)
        for i in range(len(self.reference)):
            x = self.getXPosition(self.reference[i])
            y = self.getYPositionFromDelay(self.groupDelayReference[i])
            if self.isPlotable(x, y):
                qp.drawPoint(int(x), int(y))
            if self.flag.draw_lines and i > 0:
                prevx = self.getXPosition(self.reference[i - 1])
                prevy = self.getYPositionFromDelay(self.groupDelayReference[i - 1])
                qp.setPen(line_pen)
                if self.isPlotable(x, y) and self.isPlotable(prevx, prevy):
                    qp.drawLine(x, y, prevx, prevy)
                elif self.isPlotable(x, y) and not self.isPlotable(prevx, prevy):
                    new_x, new_y = self.getPlotable(x, y, prevx, prevy)
                    qp.drawLine(x, y, new_x, new_y)
                elif not self.isPlotable(x, y) and self.isPlotable(prevx, prevy):
                    new_x, new_y = self.getPlotable(prevx, prevy, x, y)
                    qp.drawLine(prevx, prevy, new_x, new_y)
                qp.setPen(pen)

        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        # TODO: Find a faster way than these expensive "d in self.data" lookups
        if d in self.data:
            delay = self.groupDelay[self.data.index(d)]
        elif d in self.reference:
            delay = self.groupDelayReference[self.reference.index(d)]
        else:
            delay = 0
        return self.getYPositionFromDelay(delay)

    def getYPositionFromDelay(self, delay: float):
        return self.topMargin + round((self.maxDelay - delay) / self.span * self.dim.height)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.maxDelay)
        return [val]
