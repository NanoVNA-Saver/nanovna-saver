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
from NanoVNASaver.SITools import round_ceil, round_floor
from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.LogMag import LogMagChart, get_ticks

logger = logging.getLogger(__name__)


class CombinedLogMagChart(LogMagChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.data11: List[Datapoint] = []
        self.data21: List[Datapoint] = []

        self.reference11: List[Datapoint] = []
        self.reference21: List[Datapoint] = []

        self.isInverted = False

    def setCombinedData(self, data11, data21):
        self.data11 = data11
        self.data21 = data21
        self.update()

    def setCombinedReference(self, data11, data21):
        self.reference11 = data11
        self.reference21 = data21
        self.update()

    def resetReference(self):
        self.reference11 = []
        self.reference21 = []
        self.update()

    def resetDisplayLimits(self):
        self.reference11 = []
        self.reference21 = []
        self.update()

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.text))
        qp.drawText(int(round(self.dim.width / 2)) - 20, 15, f"{self.name} (dB)")
        qp.drawText(10, 15, "S11")
        qp.drawText(self.leftMargin + self.dim.width - 8, 15, "S21")
        qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.foreground))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin+self.dim.height+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.dim.height,
                    self.leftMargin+self.dim.width, self.topMargin + self.dim.height)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data11) == 0 and len(self.reference11) == 0:
            return
        pen = QtGui.QPen(Defaults.cfg.chart_colors.sweep)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Defaults.cfg.chart_colors.sweep)
        line_pen.setWidth(self.dim.line)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
        if not self.fixedSpan:
            if len(self.data11) > 0:
                fstart = self.data11[0].freq
                fstop = self.data11[len(self.data11)-1].freq
            else:
                fstart = self.reference11[0].freq
                fstop = self.reference11[len(self.reference11) - 1].freq
            self.fstart = fstart
            self.fstop = fstop
        else:
            fstart = self.fstart = self.minFrequency
            fstop = self.fstop = self.maxFrequency

        # Draw bands if required
        if Defaults.cfg.chart.show_bands:
            self.drawBands(qp, fstart, fstop)

        min_value, max_value = self.find_scaling()
        span = max_value-min_value
        if span == 0:
            span = 0.01
        self.span = span

        first_tick, tick_step, tick_count = get_ticks(span, min_value)
        self.draw_grid(qp, max_value, min_value, span, first_tick, tick_step, tick_count)

        qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.foreground))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.dim.width, self.topMargin)
        qp.setPen(Defaults.cfg.chart_colors.text)
        qp.drawText(3, self.topMargin + 4, str(max_value))
        qp.drawText(3, self.dim.height+self.topMargin, str(min_value))
        self.drawFrequencyTicks(qp)

        qp.setPen(Defaults.cfg.chart_colors.swr)
        for vswr in self.swrMarkers:
            if vswr <= 1:
                continue
            logMag = 20 * math.log10((vswr-1)/(vswr+1))
            if self.isInverted:
                logMag = logMag * -1
            y = self.topMargin + round((self.max_value - logMag) /
                                       self.span * self.dim.height)
            qp.drawLine(self.leftMargin, y,
                        self.leftMargin + self.dim.width, y)
            qp.drawText(self.leftMargin + 3, y - 1, f"VSWR: {vswr}")

        if len(self.data11) > 0:
            c = QtGui.QColor(Defaults.cfg.chart_colors.sweep)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 9, 38, 9)
            c = QtGui.QColor(Defaults.cfg.chart_colors.sweep_secondary)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.dim.width - 20, 9,
                        self.leftMargin + self.dim.width - 15, 9)

        if len(self.reference11) > 0:
            c = QtGui.QColor(Defaults.cfg.chart_colors.reference)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 14, 38, 14)
            c = QtGui.QColor(Defaults.cfg.chart_colors.reference_secondary)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.dim.width - 20, 14,
                        self.leftMargin + self.dim.width - 15, 14)

        self.drawData(qp, self.data11, Defaults.cfg.chart_colors.sweep)
        self.drawData(qp, self.data21, Defaults.cfg.chart_colors.sweep_secondary)
        self.drawData(qp, self.reference11, Defaults.cfg.chart_colors.reference)
        self.drawData(qp, self.reference21, Defaults.cfg.chart_colors.reference_secondary)
        self.drawMarkers(qp, data=self.data11)
        self.drawMarkers(qp, data=self.data21)

    def find_scaling(self) -> tuple[float, float]:
        if self.fixedValues:
            return (self.minDisplayValue, self.maxDisplayValue)
        # Find scaling
        min_value = 100
        max_value = -100
        for d in self.data11 + self.data21:
            val = self.logMag(d)
            if math.isinf(val):
                continue
            min_value = min(min_value, val)
            max_value = max(max_value, val)
        for d in self.reference11 + self.reference21:
            if d.freq < self.fstart or d.freq > self.fstop:
                continue
            val = self.logMag(d)
            if math.isinf(val):
                continue
            min_value = min(min_value, val)
            max_value = max(max_value, val)
        return(round_floor(min_value, -1), round_ceil(max_value, -1))

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        new_chart.data11 = self.data11
        new_chart.data21 = self.data21
        new_chart.reference11 = self.reference11
        new_chart.reference21 = self.reference21
        return new_chart
