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


class VSWRChart(FrequencyChart):
    logarithmicY = False
    maxVSWR = 3
    span = 2

    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 30
        self.chartWidth = 250
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.maxDisplayValue = 25
        self.minDisplayValue = 1

        self.setMinimumSize(self.chartWidth + self.rightMargin + self.leftMargin,
                            self.chartHeight + self.topMargin + self.bottomMargin)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                 QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.y_menu.addSeparator()
        self.y_log_lin_group = QtWidgets.QActionGroup(self.y_menu)
        self.y_action_linear = QtWidgets.QAction("Linear")
        self.y_action_linear.setCheckable(True)
        self.y_action_linear.setChecked(True)
        self.y_action_logarithmic = QtWidgets.QAction("Logarithmic")
        self.y_action_logarithmic.setCheckable(True)
        self.y_action_linear.triggered.connect(lambda: self.setLogarithmicY(False))
        self.y_action_logarithmic.triggered.connect(lambda: self.setLogarithmicY(True))
        self.y_log_lin_group.addAction(self.y_action_linear)
        self.y_log_lin_group.addAction(self.y_action_logarithmic)
        self.y_menu.addAction(self.y_action_linear)
        self.y_menu.addAction(self.y_action_logarithmic)

    def setLogarithmicY(self, logarithmic: bool):
        self.logarithmicY = logarithmic
        self.update()

    def copy(self):
        new_chart: VSWRChart = super().copy()
        new_chart.logarithmicY = self.logarithmicY
        return new_chart

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(self.sweepColor)
        pen.setWidth(self.pointSize)
        line_pen = QtGui.QPen(self.sweepColor)
        line_pen.setWidth(self.lineThickness)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)
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

        target_ticks = math.floor(self.chartHeight / 60)

        if self.logarithmicY:
            for i in range(target_ticks):
                y = int(self.topMargin + (i / target_ticks) * self.chartHeight)
                vswr = self.valueAtPosition(y)[0]
                qp.setPen(self.textColor)
                if vswr != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(vswr)))))
                    if digits == 0:
                        vswrstr = str(round(vswr))
                    else:
                        vswrstr = str(round(vswr, digits))
                    qp.drawText(3, y+3, vswrstr)
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            qp.drawLine(self.leftMargin - 5, self.topMargin + self.chartHeight,
                        self.leftMargin + self.chartWidth, self.topMargin + self.chartHeight)
            qp.setPen(self.textColor)
            digits = max(0, min(2, math.floor(3 - math.log10(abs(minVSWR)))))
            if digits == 0:
                vswrstr = str(round(minVSWR))
            else:
                vswrstr = str(round(minVSWR, digits))
            qp.drawText(3, self.topMargin + self.chartHeight, vswrstr)
        else:
            for i in range(target_ticks):
                vswr = minVSWR + i * self.span/target_ticks
                y = self.getYPositionFromValue(vswr)
                qp.setPen(self.textColor)
                if vswr != 0:
                    digits = max(0, min(2, math.floor(3 - math.log10(abs(vswr)))))
                    if digits == 0:
                        vswrstr = str(round(vswr))
                    else:
                        vswrstr = str(round(vswr, digits))
                    qp.drawText(3, y+3, vswrstr)
                qp.setPen(QtGui.QPen(self.foregroundColor))
                qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.chartWidth, y)
            qp.drawLine(self.leftMargin - 5,
                        self.topMargin,
                        self.leftMargin + self.chartWidth,
                        self.topMargin)
            qp.setPen(self.textColor)
            digits = max(0, min(2, math.floor(3 - math.log10(abs(maxVSWR)))))
            if digits == 0:
                vswrstr = str(round(maxVSWR))
            else:
                vswrstr = str(round(maxVSWR, digits))
            qp.drawText(3, 35, vswrstr)

        self.drawFrequencyTicks(qp)

        qp.setPen(self.swrColor)
        for vswr in self.swrMarkers:
            y = self.getYPositionFromValue(vswr)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.chartWidth, y)
            qp.drawText(self.leftMargin + 3, y - 1, str(vswr))

        self.drawData(qp, self.data, self.sweepColor)
        self.drawData(qp, self.reference, self.referenceColor)
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
                round((math.log(self.maxVSWR) - math.log(vswr)) / span * self.chartHeight))
        return self.topMargin + round((self.maxVSWR - vswr) / self.span * self.chartHeight)

    def getYPosition(self, d: Datapoint) -> int:
        return self.getYPositionFromValue(d.vswr)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        if self.logarithmicY:
            min_val = self.maxVSWR - self.span
            if self.maxVSWR > 0 and min_val > 0:
                span = math.log(self.maxVSWR) - math.log(min_val)
                step = span / self.chartHeight
                val = math.exp(math.log(self.maxVSWR) - absy * step)
            else:
                val = -1
        else:
            val = -1 * ((absy / self.chartHeight * self.span) - self.maxVSWR)
        return [val]

    def resetDisplayLimits(self):
        self.maxDisplayValue = 25
        self.logarithmicY = False
        super().resetDisplayLimits()
