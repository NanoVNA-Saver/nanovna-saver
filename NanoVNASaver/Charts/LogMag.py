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
from NanoVNASaver.Charts.Frequency import FrequencyChart

logger = logging.getLogger(__name__)


def get_ticks(span: float, min_value: float) -> tuple[float, float, float]:
    span2step = (
        (50, 10), (20, 5), (10, 2),
        (5, 1), (2, 0.5), (1, 0.2),
        (0.0, 0.1),)
    for spn, step in span2step:
        if span >= spn:
            first_tick = math.ceil(min_value/step) * step
            if first_tick <= min_value:
                first_tick += step
            tick_count = math.floor(span/step)
            break
    return(first_tick, step, tick_count)


class LogMagChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.name_unit = "dB"

        self.minDisplayValue = -80
        self.maxDisplayValue = 10

        self.max_value = 1
        self.span = 1

        self.isInverted = False

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return

        self._set_start_stop()

        # Draw bands if required
        if Defaults.cfg.chart.show_bands:
            self.drawBands(qp, self.fstart, self.fstop)

        min_value, max_value = self.find_scaling()
        self.max_value = max_value
        span = max_value - min_value
        if span == 0:
            span = 0.01
        self.span = span

        first_tick, tick_step, tick_count = get_ticks(span, min_value)
        self.draw_grid(qp, max_value, min_value, span,
                       first_tick, tick_step, tick_count)

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
            y = self.topMargin + \
                round((self.max_value - logMag) / self.span * self.dim.height)
            qp.drawLine(self.leftMargin, y,
                        self.leftMargin + self.dim.width, y)
            qp.drawText(self.leftMargin + 3, y - 1, f"VSWR: {vswr}")

        self.drawData(qp, self.data, Defaults.cfg.chart_colors.sweep)
        self.drawData(qp, self.reference, Defaults.cfg.chart_colors.reference)
        self.drawMarkers(qp)

    def find_scaling(self) -> tuple[float, float]:
        if self.fixedValues:
            return(self.minDisplayValue, self.maxDisplayValue)
        min_value = 100
        max_value = -100
        for d in self.data:
            val = self.logMag(d)
            if math.isinf(val):
                continue
            min_value = min(min_value, val)
            max_value = max(max_value, val)
        for d in self.reference:  # Also check min/max for the reference sweep
            if d.freq < self.fstart or d.freq > self.fstop:
                continue
            val = self.logMag(d)
            if math.isinf(val):
                continue
            min_value = min(min_value, val)
            max_value = max(max_value, val)
        return(round_floor(min_value, -1), round_ceil(max_value, -1))

    def draw_grid(self, qp, max_value, min_value, span, first_tick, tick_step, tick_count):
        for i in range(tick_count):
            db = first_tick + i * tick_step
            y = self.topMargin + round((max_value - db)/span*self.dim.height)
            qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.foreground))
            qp.drawLine(self.leftMargin-5, y,
                        self.leftMargin+self.dim.width, y)
            if db > min_value and db != max_value:
                qp.setPen(QtGui.QPen(Defaults.cfg.chart_colors.text))
                dbstr = str(round(db, 1)) if tick_step < 1 else str(db)
                qp.drawText(3, y + 4, dbstr)

    def getYPosition(self, d: Datapoint) -> int:
        logMag = self.logMag(d)
        if math.isinf(logMag):
            return None
        return self.topMargin + round((self.max_value - logMag) / self.span * self.dim.height)

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
