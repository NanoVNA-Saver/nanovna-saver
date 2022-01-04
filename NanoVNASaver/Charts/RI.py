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

from PyQt5 import QtWidgets, QtGui

from NanoVNASaver.Formatting import format_frequency_chart
from NanoVNASaver.Marker import Marker
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.SITools import Format, Value

from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Frequency import FrequencyChart

logger = logging.getLogger(__name__)


class RealImaginaryChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)
        self.leftMargin = 45
        self.rightMargin = 45
        self.dim.width = 230
        self.dim.height = 250
        self.fstart = 0
        self.fstop = 0
        self.span_real = 0.01
        self.span_imag = 0.01
        self.max_real = 0
        self.max_imag = 0

        self.maxDisplayReal = 100
        self.maxDisplayImag = 100
        self.minDisplayReal = 0
        self.minDisplayImag = -100

        #
        #  Build the context menu
        #

        self.y_menu.clear()

        self.y_action_automatic = QtWidgets.QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        self.y_action_fixed_span = QtWidgets.QAction("Fixed span")
        self.y_action_fixed_span.setCheckable(True)
        self.y_action_fixed_span.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked()))
        mode_group = QtWidgets.QActionGroup(self)
        mode_group.addAction(self.y_action_automatic)
        mode_group.addAction(self.y_action_fixed_span)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed_span)
        self.y_menu.addSeparator()

        self.action_set_fixed_maximum_real = QtWidgets.QAction(
            f"Maximum R ({self.maxDisplayReal})")
        self.action_set_fixed_maximum_real.triggered.connect(
            self.setMaximumRealValue)

        self.action_set_fixed_minimum_real = QtWidgets.QAction(
            f"Minimum R ({self.minDisplayReal})")
        self.action_set_fixed_minimum_real.triggered.connect(
            self.setMinimumRealValue)

        self.action_set_fixed_maximum_imag = QtWidgets.QAction(
            f"Maximum jX ({self.maxDisplayImag})")
        self.action_set_fixed_maximum_imag.triggered.connect(
            self.setMaximumImagValue)

        self.action_set_fixed_minimum_imag = QtWidgets.QAction(
            f"Minimum jX ({self.minDisplayImag})")
        self.action_set_fixed_minimum_imag.triggered.connect(
            self.setMinimumImagValue)

        self.y_menu.addAction(self.action_set_fixed_maximum_real)
        self.y_menu.addAction(self.action_set_fixed_minimum_real)
        self.y_menu.addSeparator()
        self.y_menu.addAction(self.action_set_fixed_maximum_imag)
        self.y_menu.addAction(self.action_set_fixed_minimum_imag)

    def copy(self):
        new_chart: RealImaginaryChart = super().copy()

        new_chart.maxDisplayReal = self.maxDisplayReal
        new_chart.maxDisplayImag = self.maxDisplayImag
        new_chart.minDisplayReal = self.minDisplayReal
        new_chart.minDisplayImag = self.minDisplayImag
        return new_chart

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Chart.color.text))
        qp.drawText(self.leftMargin + 5, 15,
                    f"{self.name} (\N{OHM SIGN})")
        qp.drawText(10, 15, "R")
        qp.drawText(self.leftMargin + self.dim.width + 10, 15, "X")
        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(self.leftMargin,
                    self.topMargin - 5,
                    self.leftMargin,
                    self.topMargin + self.dim.height + 5)
        qp.drawLine(self.leftMargin-5,
                    self.topMargin + self.dim.height,
                    self.leftMargin + self.dim.width + 5,
                    self.topMargin + self.dim.height)
        self.drawTitle(qp)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return
        pen = QtGui.QPen(Chart.color.sweep)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Chart.color.sweep)
        line_pen.setWidth(self.dim.line)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

        # Find scaling
        if self.fixedValues:
            min_real = self.minDisplayReal
            max_real = self.maxDisplayReal
            min_imag = self.minDisplayImag
            max_imag = self.maxDisplayImag
        else:
            min_real = 1000
            min_imag = 1000
            max_real = 0
            max_imag = -1000
            for d in self.data:
                imp = self.impedance(d)
                re, im = imp.real, imp.imag
                if math.isinf(re): # Avoid infinite scales
                    continue
                if re > max_real:
                    max_real = re
                if re < min_real:
                    min_real = re
                if im > max_imag:
                    max_imag = im
                if im < min_imag:
                    min_imag = im
            for d in self.reference:  # Also check min/max for the reference sweep
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                imp = self.impedance(d)
                re, im = imp.real, imp.imag
                if math.isinf(re): # Avoid infinite scales
                    continue
                if re > max_real:
                    max_real = re
                if re < min_real:
                    min_real = re
                if im > max_imag:
                    max_imag = im
                if im < min_imag:
                    min_imag = im

            # Always have at least 8 numbered horizontal lines
            max_real = max(8, math.ceil(max_real))
            min_real = max(0, math.floor(min_real))  # Negative real resistance? No.
            max_imag = math.ceil(max_imag)
            min_imag = math.floor(min_imag)

            if max_imag - min_imag < 8:
                missing = 8 - (max_imag - min_imag)
                max_imag += math.ceil(missing/2)
                min_imag -= math.floor(missing/2)

            if 0 > max_imag > -2:
                max_imag = 0
            if 0 < min_imag < 2:
                min_imag = 0

            if (max_imag - min_imag) > 8 and min_imag < 0 < max_imag:
                # We should show a "0" line for the reactive part
                span = max_imag - min_imag
                step_size = span / 8
                if max_imag < step_size:
                    # The 0 line is the first step after the top. Scale accordingly.
                    max_imag = -min_imag/7
                elif -min_imag < step_size:
                    # The 0 line is the last step before the bottom. Scale accordingly.
                    min_imag = -max_imag/7
                else:
                    # Scale max_imag to be a whole factor of min_imag
                    num_min = math.floor(min_imag/step_size * -1)
                    num_max = 8 - num_min
                    max_imag = num_max * (min_imag / num_min) * -1

        self.max_real = max_real
        self.max_imag = max_imag

        span_real = max_real - min_real
        if span_real == 0:
            span_real = 0.01
        self.span_real = span_real

        span_imag = max_imag - min_imag
        if span_imag == 0:
            span_imag = 0.01
        self.span_imag = span_imag

        # We want one horizontal tick per 50 pixels, at most
        horizontal_ticks = math.floor(self.dim.height/50)

        fmt = Format(max_nr_digits=3)
        for i in range(horizontal_ticks):
            y = self.topMargin + round(i * self.dim.height / horizontal_ticks)
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(self.leftMargin - 5, y, self.leftMargin + self.dim.width + 5, y)
            qp.setPen(QtGui.QPen(Chart.color.text))
            re = max_real - i * span_real / horizontal_ticks
            im = max_imag - i * span_imag / horizontal_ticks
            qp.drawText(3, y + 4, str(Value(re, fmt=fmt)))
            qp.drawText(self.leftMargin + self.dim.width + 8, y + 4, str(Value(im, fmt=fmt)))

        qp.drawText(3, self.dim.height + self.topMargin, str(Value(min_real, fmt=fmt)))
        qp.drawText(self.leftMargin + self.dim.width + 8,
                    self.dim.height + self.topMargin,
                    str(Value(min_imag, fmt=fmt)))

        self.drawFrequencyTicks(qp)

        primary_pen = pen
        secondary_pen = QtGui.QPen(Chart.color.sweep_secondary)
        if len(self.data) > 0:
            c = QtGui.QColor(Chart.color.sweep)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 9, 25, 9)
            c = QtGui.QColor(Chart.color.sweep_secondary)
            c.setAlpha(255)
            pen.setColor(c)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.dim.width, 9,
                        self.leftMargin + self.dim.width + 5, 9)

        primary_pen.setWidth(self.dim.point)
        secondary_pen.setWidth(self.dim.point)
        line_pen.setWidth(self.dim.line)

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
            if self.flag.draw_lines and i > 0:
                prev_x = self.getXPosition(self.data[i - 1])
                prev_y_re = self.getReYPosition(self.data[i-1])
                prev_y_im = self.getImYPosition(self.data[i-1])

                # Real part first
                line_pen.setColor(Chart.color.sweep)
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
                line_pen.setColor(Chart.color.sweep_secondary)
                qp.setPen(line_pen)
                if self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    qp.drawLine(x, y_im, prev_x, prev_y_im)
                elif self.isPlotable(x, y_im) and not self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(x, y_im, prev_x, prev_y_im)
                    qp.drawLine(x, y_im, new_x, new_y)
                elif not self.isPlotable(x, y_im) and self.isPlotable(prev_x, prev_y_im):
                    new_x, new_y = self.getPlotable(prev_x, prev_y_im, x, y_im)
                    qp.drawLine(prev_x, prev_y_im, new_x, new_y)

        primary_pen.setColor(Chart.color.reference)
        line_pen.setColor(Chart.color.reference)
        secondary_pen.setColor(Chart.color.reference_secondary)
        qp.setPen(primary_pen)
        if len(self.reference) > 0:
            c = QtGui.QColor(Chart.color.reference)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(20, 14, 25, 14)
            c = QtGui.QColor(Chart.color.reference_secondary)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.dim.width, 14,
                        self.leftMargin + self.dim.width + 5, 14)

        for i in range(len(self.reference)):
            if self.reference[i].freq < self.fstart or self.reference[i].freq > self.fstop:
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
            if self.flag.draw_lines and i > 0:
                prev_x = self.getXPosition(self.reference[i - 1])
                prev_y_re = self.getReYPosition(self.reference[i-1])
                prev_y_im = self.getImYPosition(self.reference[i-1])

                line_pen.setColor(Chart.color.reference)
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

                line_pen.setColor(Chart.color.reference_secondary)
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
        im = self.impedance(d).imag
        return self.topMargin + round((self.max_imag - im) / self.span_imag * self.dim.height)

    def getReYPosition(self, d: Datapoint) -> int:
        re = self.impedance(d).real
        if math.isfinite(re):
            return self.topMargin + round((self.max_real - re) / self.span_real * self.dim.height)
        return self.topMargin

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        valRe = -1 * ((absy / self.dim.height * self.span_real) - self.max_real)
        valIm = -1 * ((absy / self.dim.height * self.span_imag) - self.max_imag)
        return [valRe, valIm]

    def zoomTo(self, x1, y1, x2, y2):
        val1 = self.valueAtPosition(y1)
        val2 = self.valueAtPosition(y2)

        if len(val1) == len(val2) == 2 and val1[0] != val2[0]:
            self.minDisplayReal = round(min(val1[0], val2[0]), 2)
            self.maxDisplayReal = round(max(val1[0], val2[0]), 2)
            self.minDisplayImag = round(min(val1[1], val2[1]), 2)
            self.maxDisplayImag = round(max(val1[1], val2[1]), 2)
            self.setFixedValues(True)

        freq1 = max(1, self.frequencyAtPosition(x1, limit=False))
        freq2 = max(1, self.frequencyAtPosition(x2, limit=False))

        if freq1 > 0 and freq2 > 0 and freq1 != freq2:
            self.minFrequency = min(freq1, freq2)
            self.maxFrequency = max(freq1, freq2)
            self.setFixedSpan(True)

        self.update()

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

    def setMinimumRealValue(self):
        min_val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Minimum real value",
            "Set minimum real value", value=self.minDisplayReal,
            decimals=2)
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayReal):
            self.minDisplayReal = min_val
        if self.fixedValues:
            self.update()

    def setMaximumRealValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Maximum real value",
            "Set maximum real value", value=self.maxDisplayReal,
            decimals=2)
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minDisplayReal):
            self.maxDisplayReal = max_val
        if self.fixedValues:
            self.update()

    def setMinimumImagValue(self):
        min_val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Minimum imaginary value",
            "Set minimum imaginary value", value=self.minDisplayImag,
            decimals=2)
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayImag):
            self.minDisplayImag = min_val
        if self.fixedValues:
            self.update()

    def setMaximumImagValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(
            self, "Maximum imaginary value",
            "Set maximum imaginary value", value=self.maxDisplayImag,
            decimals=2)
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minDisplayImag):
            self.maxDisplayImag = max_val
        if self.fixedValues:
            self.update()

    def setFixedValues(self, fixed_values: bool):
        self.fixedValues = fixed_values
        if (fixed_values and
                (self.minDisplayReal >= self.maxDisplayReal or
                 self.minDisplayImag > self.maxDisplayImag)):
            self.fixedValues = False
            self.y_action_automatic.setChecked(True)
            self.y_action_fixed_span.setChecked(False)
        self.update()

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText(
            f"Start ({format_frequency_chart(self.minFrequency)})")
        self.action_set_fixed_stop.setText(
            f"Stop ({format_frequency_chart(self.maxFrequency)})")
        self.action_set_fixed_minimum_real.setText(
            f"Minimum R ({self.minDisplayReal})")
        self.action_set_fixed_maximum_real.setText(
            f"Maximum R ({self.maxDisplayReal})")
        self.action_set_fixed_minimum_imag.setText(
            f"Minimum jX ({self.minDisplayImag})")
        self.action_set_fixed_maximum_imag.setText(
            f"Maximum jX ({self.maxDisplayImag})")
        self.menu.exec_(event.globalPos())

    def impedance(self, p: Datapoint) -> complex:
        return p.impedance()
