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

from NanoVNASaver.Marker import Marker
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.SITools import Format, Value
from .Frequency import FrequencyChart
logger = logging.getLogger(__name__)


class PermeabilityChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 40
        self.rightMargin = 30
        self.chartWidth = 230
        self.chartHeight = 250
        self.fstart = 0
        self.fstop = 0
        self.span = 0.01
        self.max = 0
        self.logarithmicY = True

        self.maxDisplayValue = 100
        self.minDisplayValue = -100

        #
        # Set up size policy and palette
        #

        self.setMinimumSize(self.chartWidth + self.leftMargin +
                            self.rightMargin, self.chartHeight + 40)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding))
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Background, self.backgroundColor)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        self.y_menu.addSeparator()
        self.y_log_lin_group = QtWidgets.QActionGroup(self.y_menu)
        self.y_action_linear = QtWidgets.QAction("Linear")
        self.y_action_linear.setCheckable(True)
        self.y_action_logarithmic = QtWidgets.QAction("Logarithmic")
        self.y_action_logarithmic.setCheckable(True)
        self.y_action_logarithmic.setChecked(True)
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
        new_chart: PermeabilityChart = super().copy()
        new_chart.logarithmicY = self.logarithmicY
        return new_chart

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(self.textColor))
        qp.drawText(self.leftMargin + 5, 15, self.name + " (\N{MICRO SIGN}\N{OHM SIGN} / Hz)")
        qp.drawText(10, 15, "R")
        qp.drawText(self.leftMargin + self.chartWidth + 10, 15, "X")
        qp.setPen(QtGui.QPen(self.foregroundColor))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin + self.chartHeight + 5)
        qp.drawLine(self.leftMargin-5, self.topMargin + self.chartHeight,
                    self.leftMargin + self.chartWidth + 5, self.topMargin + self.chartHeight)
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
        if self.fixedSpan:
            fstart = self.minFrequency
            fstop = self.maxFrequency
        else:
            if len(self.data) > 0:
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
            min_val = self.minDisplayValue
            max_val = self.maxDisplayValue
        else:
            min_val = 1000
            max_val = -1000
            for d in self.data:
                imp = d.impedance()
                re, im = imp.real, imp.imag
                re = re * 10e6 / d.freq
                im = im * 10e6 / d.freq
                if re > max_val:
                    max_val = re
                if re < min_val:
                    min_val = re
                if im > max_val:
                    max_val = im
                if im < min_val:
                    min_val = im
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < fstart or d.freq > fstop:
                    continue
                imp = d.impedance()
                re, im = imp.real, imp.imag
                re = re * 10e6 / d.freq
                im = im * 10e6 / d.freq
                if re > max_val:
                    max_val = re
                if re < min_val:
                    min_val = re
                if im > max_val:
                    max_val = im
                if im < min_val:
                    min_val = im

        if self.logarithmicY:
            min_val = max(0.01, min_val)

        self.max = max_val

        span = max_val - min_val
        if span == 0:
            span = 0.01
        self.span = span

        # We want one horizontal tick per 50 pixels, at most
        horizontal_ticks = math.floor(self.chartHeight/50)
        fmt = Format(max_nr_digits=4)
        for i in range(horizontal_ticks):
            y = self.topMargin + round(i * self.chartHeight / horizontal_ticks)
            qp.setPen(QtGui.QPen(self.foregroundColor))
            qp.drawLine(self.leftMargin - 5, y,
                        self.leftMargin + self.chartWidth + 5, y)
            qp.setPen(QtGui.QPen(self.textColor))
            val = Value(self.valueAtPosition(y)[0], fmt=fmt)
            qp.drawText(3, y + 4, str(val))

        qp.drawText(3,
                    self.chartHeight + self.topMargin,
                    str(Value(min_val, fmt=fmt)))

        self.drawFrequencyTicks(qp)

        primary_pen = pen
        secondary_pen = QtGui.QPen(self.secondarySweepColor)
        if len(self.data) > 0:
            c = QtGui.QColor(self.sweepColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 9, 25, 9)
            c = QtGui.QColor(self.secondarySweepColor)
            c.setAlpha(255)
            pen.setColor(c)
            qp.setPen(pen)
            qp.drawLine(
                self.leftMargin + self.chartWidth, 9,
                self.leftMargin + self.chartWidth + 5, 9)

        primary_pen.setWidth(self.pointSize)
        secondary_pen.setWidth(self.pointSize)
        line_pen.setWidth(self.lineThickness)

        for i in range(len(self.data)):
            x = self.getXPosition(self.data[i])
            y_re = self.getReYPosition(self.data[i])
            y_im = self.getImYPosition(self.data[i])
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.drawLines and i > 0:
                prev_x = self.getXPosition(self.data[i - 1])
                prev_y_re = self.getReYPosition(self.data[i-1])
                prev_y_im = self.getImYPosition(self.data[i-1])

                # Real part first
                line_pen.setColor(self.sweepColor)
                qp.setPen(line_pen)
                if self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    qp.drawLine(x, y_re, prev_x, prev_y_re)
                elif self.isPlotable(x, y_re) and not self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(x, y_re, prev_x, prev_y_re)
                    qp.drawLine(x, y_re, new_x, new_y)
                elif not self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_re, x, y_re)
                    qp.drawLine(prev_x, prev_y_re, new_x, new_y)

                # Imag part second
                line_pen.setColor(self.secondarySweepColor)
                qp.setPen(line_pen)
                if self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    qp.drawLine(x, y_im, prev_x, prev_y_im)
                elif self.isPlotable(x, y_im) and not self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(x, y_im, prev_x, prev_y_im)
                    qp.drawLine(x, y_im, new_x, new_y)
                elif not self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_im, x, y_im)
                    qp.drawLine(prev_x, prev_y_im, new_x, new_y)

        primary_pen.setColor(self.referenceColor)
        line_pen.setColor(self.referenceColor)
        secondary_pen.setColor(self.secondaryReferenceColor)
        qp.setPen(primary_pen)
        if len(self.reference) > 0:
            c = QtGui.QColor(self.referenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 14, 25, 14)
            c = QtGui.QColor(self.secondaryReferenceColor)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.chartWidth, 14,
                        self.leftMargin + self.chartWidth + 5, 14)

        for i in range(len(self.reference)):
            if self.reference[i].freq < fstart or self.reference[i].freq > fstop:
                continue
            x = self.getXPosition(self.reference[i])
            y_re = self.getReYPosition(self.reference[i])
            y_im = self.getImYPosition(self.reference[i])
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.drawLines and i > 0:
                prev_x = self.getXPosition(self.reference[i - 1])
                prev_y_re = self.getReYPosition(self.reference[i-1])
                prev_y_im = self.getImYPosition(self.reference[i-1])

                line_pen.setColor(self.referenceColor)
                qp.setPen(line_pen)
                # Real part first
                if self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    qp.drawLine(x, y_re, prev_x, prev_y_re)
                elif self.isPlotable(x, y_re) and not self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(x, y_re, prev_x, prev_y_re)
                    qp.drawLine(x, y_re, new_x, new_y)
                elif not self.isPlotable(x, y_re) and self.isPlotable(prev_x, prev_y_re):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_re, x, y_re)
                    qp.drawLine(prev_x, prev_y_re, new_x, new_y)

                line_pen.setColor(self.secondaryReferenceColor)
                qp.setPen(line_pen)
                # Imag part second
                if self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    qp.drawLine(x, y_im, prev_x, prev_y_im)
                elif self.isPlotable(x, y_im) and not self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(x, y_im, prev_x, prev_y_im)
                    qp.drawLine(x, y_im, new_x, new_y)
                elif not self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_im, x, y_im)
                    qp.drawLine(prev_x, prev_y_im, new_x, new_y)

        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                x = self.getXPosition(self.data[m.location])
                y_re = self.getReYPosition(self.data[m.location])
                y_im = self.getImYPosition(self.data[m.location])

                self.drawMarker(x, y_re, qp, m.color, self.markers.index(m)+1)
                self.drawMarker(x, y_im, qp, m.color, self.markers.index(m)+1)

    def getImYPosition(self, d: Datapoint) -> int:
        im = d.impedance().imag
        im = im * 10e6 / d.freq
        if self.logarithmicY:
            min_val = self.max - self.span
            if self.max > 0 and min_val > 0 and im > 0:
                span = math.log(self.max) - math.log(min_val)
            else:
                return -1
            return self.topMargin + round(
                (math.log(self.max) - math.log(im)) /
                span * self.chartHeight)
        return self.topMargin + round(
            (self.max - im) / self.span * self.chartHeight)

    def getReYPosition(self, d: Datapoint) -> int:
        re = d.impedance().real
        re = re * 10e6 / d.freq
        if self.logarithmicY:
            min_val = self.max - self.span
            if self.max > 0 and min_val > 0 and re > 0:
                span = math.log(self.max) - math.log(min_val)
            else:
                return -1
            return self.topMargin + round(
                (math.log(self.max) - math.log(re)) /
                span * self.chartHeight)
        return self.topMargin + round(
            (self.max - re) / self.span * self.chartHeight)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        if self.logarithmicY:
            min_val = self.max - self.span
            if self.max > 0 and min_val > 0:
                span = math.log(self.max) - math.log(min_val)
                step = span / self.chartHeight
                val = math.exp(math.log(self.max) - absy * step)
            else:
                val = -1
        else:
            val = -1 * ((absy / self.chartHeight * self.span) - self.max)
        return [val]

    def getNearestMarker(self, x, y) -> Marker:
        if len(self.data) == 0:
            return None
        shortest = 10**6
        nearest = None
        for m in self.markers:
            mx, _ = self.getPosition(self.data[m.location])
            myr = self.getReYPosition(self.data[m.location])
            myi = self.getImYPosition(self.data[m.location])
            dx = abs(x - mx)
            dy = min(abs(y - myr), abs(y-myi))
            distance = math.sqrt(dx**2 + dy**2)
            if distance < shortest:
                shortest = distance
                nearest = m
        return nearest
