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

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class VSWRChart(FrequencyChart):

    def __init__(self, name=""):
        super().__init__(name)

        self.maxDisplayValue = 25
        self.minDisplayValue = 1

        self.maxVSWR = 3
        self.span = 2

    def logarithmicYAllowed(self) -> bool:
        return True

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        if self.fixedSpan:
            fstart = self.minFrequency
            fstop = self.maxFrequency
        elif len(self.data) > 0:
            fstart = self.data[0].freq
            fstop = self.data[len(self.data)-1].freq
        else:
            fstart = self.reference[0].freq
            fstop = self.reference[len(self.reference) - 1].freq
        self.fstart = fstart
        self.fstop = fstop

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        # Find scaling
        if self.fixedValues:
            minVSWR = max(1, self.minDisplayValue)
            maxVSWR = self.maxDisplayValue
        else:
            minVSWR = 1
            maxVSWR = 3
            for d in self.data:
                vswr = d.vswr
                if vswr > maxVSWR:
                    maxVSWR = vswr
            maxVSWR = min(self.maxDisplayValue, math.ceil(maxVSWR))
        self.maxVSWR = maxVSWR
        span = maxVSWR-minVSWR
        if span == 0:
            span = 0.01
        self.span = span

        target_ticks = math.floor(self.dim.height / 60)

        if self.logarithmicY:
            for i in range(target_ticks):
                y = int(self.topMargin + (i / target_ticks) * self.dim.height)
                vswr = self.valueAtPosition(y)[0]
                qp.setPen(Chart.color.text)
                if vswr != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(vswr)))))
                    if digits == 0:
                        vswrstr = str(round(vswr))
                    else:
                        vswrstr = str(round(vswr, digits))
                    qp.drawText(3, y+3, vswrstr)
                qp.setPen(QtGui.QPen(Chart.color.foreground))
                qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.dim.width, y)
            qp.drawLine(self.leftMargin - 5, self.topMargin + self.dim.height,
                        self.leftMargin + self.dim.width, self.topMargin + self.dim.height)
            qp.setPen(Chart.color.text)
            digits = max(0, min(2, math.floor(3 - math.log10(abs(minVSWR)))))
            if digits == 0:
                vswrstr = str(round(minVSWR))
            else:
                vswrstr = str(round(minVSWR, digits))
            qp.drawText(3, self.topMargin + self.dim.height, vswrstr)
        else:
            for i in range(target_ticks):
                vswr = minVSWR + i * self.span/target_ticks
                y = self.getYPositionFromValue(vswr)
                qp.setPen(Chart.color.text)
                if vswr != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(vswr)))))
                    if digits == 0:
                        vswrstr = str(round(vswr))
                    else:
                        vswrstr = str(round(vswr, digits))
                    qp.drawText(3, y+3, vswrstr)
                qp.setPen(QtGui.QPen(Chart.color.foreground))
                qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.dim.width, y)
            qp.drawLine(self.leftMargin - 5,
                        self.topMargin,
                        self.leftMargin + self.dim.width,
                        self.topMargin)
            qp.setPen(Chart.color.text)
            digits = max(0, min(2, math.floor(3 - math.log10(abs(maxVSWR)))))
            if digits == 0:
                vswrstr = str(round(maxVSWR))
            else:
                vswrstr = str(round(maxVSWR, digits))
            qp.drawText(3, 35, vswrstr)

        qp.setPen(Chart.color.swr)
        for vswr in self.swrMarkers:
            y = self.getYPositionFromValue(vswr)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.dim.width, y)
            qp.drawText(self.leftMargin + 3, y - 1, str(vswr))

        self.drawFrequencyTicks(qp)
        self.drawData(qp, self.data, Chart.color.sweep)
        self.drawData(qp, self.reference, Chart.color.reference)
        self.drawMarkers(qp)

    def getYPositionFromValue(self, vswr) -> int:
        if self.logarithmicY:
            min_val = self.maxVSWR - self.span
            if self.maxVSWR > 0 and min_val > 0 and vswr > 0:
                span = math.log(self.maxVSWR) - math.log(min_val)
            else:
                return -1
            return (
                self.topMargin +
                round((math.log(self.maxVSWR) - math.log(vswr)) / span * self.dim.height))
        return self.topMargin + round((self.maxVSWR - vswr) / self.span * self.dim.height)

    def getYPosition(self, d: Datapoint) -> int:
        return self.getYPositionFromValue(d.vswr)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        if self.logarithmicY:
            min_val = self.maxVSWR - self.span
            if self.maxVSWR > 0 and min_val > 0:
                span = math.log(self.maxVSWR) - math.log(min_val)
                step = span / self.dim.height
                val = math.exp(math.log(self.maxVSWR) - absy * step)
            else:
                val = -1
        else:
            val = -1 * ((absy / self.dim.height * self.span) - self.maxVSWR)
        return [val]

    def resetDisplayLimits(self):
        self.maxDisplayValue = 25
        super().resetDisplayLimits()
