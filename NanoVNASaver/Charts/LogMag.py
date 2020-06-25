#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020 NanoVNA-Saver Authors
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

from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.RFTools import Datapoint
from .Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class LogMagChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.minDisplayValue = -80
        self.maxDisplayValue = 10

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.isInverted = False

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(3, 15, self.name + " (dB)")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin+self.chartHeight+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.chartHeight,
                    self.leftMargin+self.chartWidth, self.topMargin + self.chartHeight)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if not self.fixedSpan:
            if len(self.data) > 0:
                fstart = self.data[0].freq
                fstop = self.data[len(self.data)-1].freq
            else:
                fstart = self.reference[0].freq
                fstop = self.reference[len(self.reference) - 1].freq
            self.fstart = fstart
            self.fstop = fstop
        else:
            fstart = self.fstart = self.minFrequency
            fstop = self.fstop = self.maxFrequency

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, fstart, fstop)

        if self.fixedValues:
            maxValue = self.maxDisplayValue
            minValue = self.minDisplayValue
            self.maxValue = maxValue
            self.minValue = minValue
        else:
            # Find scaling
            minValue = 100
            maxValue = -100
            for d in self.data:
                logmag = self.logMag(d)
                if math.isinf(logmag):
                    continue
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                logmag = self.logMag(d)
                if math.isinf(logmag):
                    continue
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag

            minValue = 10*math.floor(minValue/10)
            self.minValue = minValue
            maxValue = 10*math.ceil(maxValue/10)
            self.maxValue = maxValue

        span = maxValue-minValue
        if span == 0:
            span = 0.01
        self.span = span

        if self.span >= 50:
            # Ticks per 10dB step
            tick_count = math.floor(self.span/10)
            first_tick = math.ceil(self.minValue/10) * 10
            tick_step = 10
            if first_tick == minValue:
                first_tick += 10
        elif self.span >= 20:
            # 5 dB ticks
            tick_count = math.floor(self.span/5)
            first_tick = math.ceil(self.minValue/5) * 5
            tick_step = 5
            if first_tick == minValue:
                first_tick += 5
        elif self.span >= 10:
            # 2 dB ticks
            tick_count = math.floor(self.span/2)
            first_tick = math.ceil(self.minValue/2) * 2
            tick_step = 2
            if first_tick == minValue:
                first_tick += 2
        elif self.span >= 5:
            # 1dB ticks
            tick_count = math.floor(self.span)
            first_tick = math.ceil(minValue)
            tick_step = 1
            if first_tick == minValue:
                first_tick += 1
        elif self.span >= 2:
            # .5 dB ticks
            tick_count = math.floor(self.span*2)
            first_tick = math.ceil(minValue*2) / 2
            tick_step = .5
            if first_tick == minValue:
                first_tick += .5
        else:
            # .1 dB ticks
            tick_count = math.floor(self.span*10)
            first_tick = math.ceil(minValue*10) / 10
            tick_step = .1
            if first_tick == minValue:
                first_tick += .1

        for i in range(tick_count):
            db = first_tick + i * tick_step
            y = self.topMargin + round((maxValue - db)/span*self.chartHeight)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            if db > minValue and db != maxValue:
                qp.setPen(QtGui.QPen(self.textColor))
                if tick_step < 1:
                    dbstr = str(round(db, 1))
                else:
                    dbstr = str(db)
                qp.drawText(3, y + 4, dbstr)

        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.chartWidth, self.topMargin)
        qp.setPen(self.textColor)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.chartHeight+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        qp.setPen(self.swrColor)
        for vswr in self.swrMarkers:
            if vswr <= 1:
                continue
            logMag = 20 * math.log10((vswr-1)/(vswr+1))
            if self.isInverted:
                logMag = logMag * -1
            y = self.topMargin + round((self.maxValue - logMag) / self.span * self.chartHeight)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.chartWidth, y)
            qp.drawText(self.leftMargin + 3, y - 1, "VSWR: " + str(vswr))

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
        self.drawMarkers(qp)

    def getYPosition(self, d: Datapoint) -> int:
        logMag = self.logMag(d)
        if math.isinf(logMag):
            return None
        return self.topMargin + round((self.maxValue - logMag) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.chartHeight * self.span) - self.maxValue)
        return [val]

    def logMag(self, p: Datapoint) -> float:
        if self.isInverted:
            return -p.gain
        return p.gain

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        return new_chart
