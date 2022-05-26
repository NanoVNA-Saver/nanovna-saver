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
from NanoVNASaver.SITools import Value, round_ceil, round_floor
from NanoVNASaver.Formatting import FMT_VSWR

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Frequency import FrequencyChart
logger = logging.getLogger(__name__)


class MagnitudeChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.minDisplayValue = 0
        self.maxDisplayValue = 1

        self.fixedValues = True
        self.y_action_fixed_span.setChecked(True)
        self.y_action_automatic.setChecked(False)

        self.min_value = 0
        self.max_value = 1
        self.span = 1

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return

        self._set_start_stop()

        # Draw bands if required
        if Defaults.cfg.chart.show_bands:
            self.drawBands(qp, self.fstart, self.fstop)

        self.min_value, self.max_value = self.find_scaling()

        self.span = self.max_value-self.min_value or 0.01

        target_ticks = math.floor(self.dim.height / 60)

        for i in range(target_ticks):
            val = self.min_value + i / target_ticks * self.span
            y = self.topMargin + round((self.max_value - val) / self.span * self.dim.height)
            qp.setPen(Chart.color.text)
            if val != self.min_value:
                qp.drawText(3, y + 3, Value(val, fmt=FMT_VSWR))
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.dim.width, y)

        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.dim.width, self.topMargin)
        qp.setPen(Chart.color.text)
        qp.drawText(3, self.topMargin + 4, Value(self.max_value, fmt=FMT_VSWR))
        qp.drawText(3, self.dim.height+self.topMargin, Value(self.min_value, fmt=FMT_VSWR))
        self.drawFrequencyTicks(qp)

        qp.setPen(Chart.color.swr)
        for vswr in self.swrMarkers:
            if vswr <= 1:
                continue
            mag = (vswr-1)/(vswr+1)
            y = self.topMargin + round((self.max_value - mag) / self.span * self.dim.height)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.dim.width, y)
            qp.drawText(self.leftMargin + 3, y - 1, f"VSWR: {Value(vswr, fmt=FMT_VSWR)}")

        self.drawData(qp, self.data, Chart.color.sweep)
        self.drawData(qp, self.reference, Chart.color.reference)
        self.drawMarkers(qp)

    def find_scaling(self) -> tuple[float, float]:
        if self.fixedValues:
            return(self.minDisplayValue, self.maxDisplayValue)
        min_value = 100
        max_value = 0
        for data in self.data:
            val = self.magnitude(data)
            min_value = min(min_value, val)
            max_value = max(max_value, val)
        for data in self.reference:  # Also check min/max for the reference sweep
            if data.freq < self.fstart or data.freq > self.fstop:
                continue
            val = self.magnitude(data)
            min_value = min(min_value, val)
            max_value = max(max_value, val)

        return(round_floor(min_value, -1), round_ceil(max_value, -1))

    def getYPosition(self, d: Datapoint) -> int:
        mag = self.magnitude(d)
        return self.topMargin + round((self.max_value - mag) / self.span * self.dim.height)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.max_value)
        return [val]

    @staticmethod
    def magnitude(p: Datapoint) -> float:
        return abs(p.z)

    def copy(self):
        new_chart = super().copy()
        new_chart.span = self.span
        return new_chart
