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

from PyQt6 import QtGui, QtWidgets

from NanoVNASaver.Charts.Chart import Chart, ChartPosition
from NanoVNASaver.Charts.Frequency import FrequencyChart
from NanoVNASaver.Formatting import format_frequency_chart
from NanoVNASaver.Marker.Widget import Marker
from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.SITools import Format, Value

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

        self.y_action_automatic = QtGui.QAction("Automatic")
        self.y_action_automatic.setCheckable(True)
        self.y_action_automatic.setChecked(True)
        self.y_action_automatic.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked())
        )
        self.y_action_fixed_span = QtGui.QAction("Fixed span")
        self.y_action_fixed_span.setCheckable(True)
        self.y_action_fixed_span.changed.connect(
            lambda: self.setFixedValues(self.y_action_fixed_span.isChecked())
        )
        mode_group = QtGui.QActionGroup(self)
        mode_group.addAction(self.y_action_automatic)
        mode_group.addAction(self.y_action_fixed_span)
        self.y_menu.addAction(self.y_action_automatic)
        self.y_menu.addAction(self.y_action_fixed_span)

    def copy(self):
        new_chart: RealImaginaryChart = super().copy()

        new_chart.maxDisplayReal = self.maxDisplayReal
        new_chart.maxDisplayImag = self.maxDisplayImag
        new_chart.minDisplayReal = self.minDisplayReal
        new_chart.minDisplayImag = self.minDisplayImag
        return new_chart

    def drawValues(self, qp: QtGui.QPainter) -> None:
        if not self.data and not self.reference:
            return

        primary_pen = QtGui.QPen(Chart.color.sweep)
        primary_pen.setWidth(self.dim.point)
        secondary_pen = QtGui.QPen(Chart.color.sweep_secondary)
        secondary_pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Chart.color.sweep)
        line_pen.setWidth(self.dim.line)
        highlighter = QtGui.QPen(QtGui.QColor(20, 0, 255))
        highlighter.setWidth(1)

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

        min_real, max_real, min_imag, max_imag = self.find_scaling()

        self.max_real = max_real
        self.max_imag = max_imag

        self.span_real = (max_real - min_real) or 0.01
        self.span_imag = (max_imag - min_imag) or 0.01

        self.drawHorizontalTicks(qp)

        fmt = Format(max_nr_digits=3)
        qp.drawText(
            3, self.dim.height + self.topMargin, str(Value(min_real, fmt=fmt))
        )
        qp.drawText(
            self.leftMargin + self.dim.width + 8,
            self.dim.height + self.topMargin,
            str(Value(min_imag, fmt=fmt)),
        )

        self.drawFrequencyTicks(qp)

        self._draw_ri_labels(qp)
        self._draw_data(qp, line_pen, primary_pen, secondary_pen)

        if self.reference:
            primary_pen.setColor(Chart.color.reference)
            line_pen.setColor(Chart.color.reference)
            secondary_pen.setColor(Chart.color.reference_secondary)
            self._draw_ri_labels(qp, is_reference=True)
            self._draw_ref_data(qp, line_pen, primary_pen, secondary_pen)

        # Now draw the markers
        for m in self.markers:
            if m.location != -1:
                x = self.getXPosition(self.data[m.location])
                y_re = self.getReYPosition(self.data[m.location])
                y_im = self.getImYPosition(self.data[m.location])

                self.drawMarker(x, y_re, qp, m.color, self.markers.index(m) + 1)
                self.drawMarker(x, y_im, qp, m.color, self.markers.index(m) + 1)

    def _draw_ri_labels(self, qp: QtGui.QPainter, is_reference=False) -> None:
        c1, c2 = (
            (
                QtGui.QColor(Chart.color.sweep),
                QtGui.QColor(Chart.color.sweep_secondary),
            )
            if not is_reference
            else (
                QtGui.QColor(Chart.color.reference),
                QtGui.QColor(Chart.color.reference_secondary),
            )
        )
        y = 9 if not is_reference else 14
        c1.setAlpha(255)
        c2.setAlpha(255)
        pen = QtGui.QPen(c1)
        pen.setWidth(4)
        qp.setPen(pen)
        qp.drawLine(20, y, 25, y)

        pen.setColor(c2)
        qp.setPen(pen)
        qp.drawLine(
            self.leftMargin + self.dim.width,
            y,
            self.leftMargin + self.dim.width + 5,
            y,
        )

    def _draw_ref_data(self, qp, line_pen, primary_pen, secondary_pen):
        for i, reference in enumerate(self.reference):
            if reference.freq < self.fstart or reference.freq > self.fstop:
                continue
            x = self.getXPosition(reference)
            y_re = self.getReYPosition(reference)
            y_im = self.getImYPosition(reference)
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.flag.draw_lines and i > 0:
                prev_x = self.getXPosition(self.reference[i - 1])
                prev_y_re = self.getReYPosition(self.reference[i - 1])
                prev_y_im = self.getImYPosition(self.reference[i - 1])

                # Real part first
                line_pen.setColor(Chart.color.reference)
                self._draw_line(qp, line_pen, (x, y_re), (prev_x, prev_y_re))

                # Imag part second
                line_pen.setColor(Chart.color.reference_secondary)
                self._draw_line(qp, line_pen, (x, y_im), (prev_x, prev_y_im))

    def _draw_data(self, qp, line_pen, primary_pen, secondary_pen) -> None:
        for i, data in enumerate(self.data):
            x = self.getXPosition(data)
            y_re = self.getReYPosition(data)
            y_im = self.getImYPosition(data)
            qp.setPen(primary_pen)
            if self.isPlotable(x, y_re):
                qp.drawPoint(x, y_re)
            qp.setPen(secondary_pen)
            if self.isPlotable(x, y_im):
                qp.drawPoint(x, y_im)
            if self.flag.draw_lines and i > 0:
                prev_x = self.getXPosition(self.data[i - 1])
                prev_y_re = self.getReYPosition(self.data[i - 1])
                prev_y_im = self.getImYPosition(self.data[i - 1])

                # Real part first
                line_pen.setColor(Chart.color.sweep)
                self._draw_line(qp, line_pen, (x, y_re), (prev_x, prev_y_re))

                # Imag part second
                line_pen.setColor(Chart.color.sweep_secondary)
                self._draw_line(qp, line_pen, (x, y_im), (prev_x, prev_y_im))

    def _draw_line(
        self, qp, line_pen, p: ChartPosition, prev_p: ChartPosition
    ) -> None:
        x, y = p
        prev_x, prev_y = prev_p
        qp.setPen(line_pen)
        if self.isPlotable(x, y):
            if self.isPlotable(prev_x, prev_y):
                qp.drawLine(x, y, prev_x, prev_y)
            else:
                new_x, new_y = self.getPlotable(x, y, prev_x, prev_y)
                qp.drawLine(x, y, new_x, new_y)
        elif self.isPlotable(prev_x, prev_y):
            new_x, new_y = self.getPlotable(prev_x, prev_y, x, y)
            qp.drawLine(prev_x, prev_y, new_x, new_y)

    def drawHorizontalTicks(self, qp):
        # We want one horizontal tick per 50 pixels, at most
        fmt = Format(max_nr_digits=3)
        horizontal_ticks = self.dim.height // 50
        for i in range(horizontal_ticks):
            y = self.topMargin + i * self.dim.height // horizontal_ticks
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(
                self.leftMargin - 5, y, self.leftMargin + self.dim.width + 5, y
            )
            qp.setPen(QtGui.QPen(Chart.color.text))
            re = self.max_real - i * self.span_real / horizontal_ticks
            im = self.max_imag - i * self.span_imag / horizontal_ticks
            qp.drawText(3, y + 4, f"{Value(re, fmt=fmt)}")
            qp.drawText(
                self.leftMargin + self.dim.width + 8,
                y + 4,
                f"{Value(im, fmt=fmt)}",
            )

    def find_scaling(self):
        # Find scaling
        if self.fixedValues:
            min_real = self.minDisplayReal
            max_real = self.maxDisplayReal
            min_imag = self.minDisplayImag
            max_imag = self.maxDisplayImag
            return min_real, max_real, min_imag, max_imag

        min_real = 1000
        min_imag = 1000
        max_real = 0
        max_imag = -1000
        for d in self.data:
            imp = self.value(d)
            re, im = imp.real, imp.imag
            if math.isinf(re):  # Avoid infinite scales
                continue
            max_real = max(max_real, re)
            min_real = min(min_real, re)
            max_imag = max(max_imag, im)
            min_imag = min(min_imag, im)
        # Also check min/max for the reference sweep
        for d in self.reference:
            if d.freq < self.fstart or d.freq > self.fstop:
                continue
            imp = self.value(d)
            re, im = imp.real, imp.imag
            if math.isinf(re):  # Avoid infinite scales
                continue
            max_real = max(max_real, re)
            min_real = min(min_real, re)
            max_imag = max(max_imag, im)
            min_imag = min(min_imag, im)
        # Always have at least 8 numbered horizontal lines
        max_real = math.ceil(max_real)
        min_real = math.floor(min_real)
        max_imag = math.ceil(max_imag)
        min_imag = math.floor(min_imag)

        min_imag, max_imag = self.imag_scaling_constraints(min_imag, max_imag)
        return min_real, max_real, min_imag, max_imag

    def imag_scaling_constraints(self, min_imag, max_imag):
        if max_imag - min_imag < 8:  # noqa: PLR2004
            missing = 8 - (max_imag - min_imag)
            max_imag += math.ceil(missing / 2)
            min_imag -= math.floor(missing / 2)

        if 0 > max_imag > -2:  # noqa: PLR2004
            max_imag = 0
        if 0 < min_imag < 2:  # noqa: PLR2004
            min_imag = 0

        if (
            max_imag - min_imag
        ) > 8 and min_imag < 0 < max_imag:  # noqa: PLR2004
            # We should show a "0" line for the reactive part
            span = max_imag - min_imag
            step_size = span / 8
            if max_imag < step_size:
                # The 0 line is the first step after the top.
                # Scale accordingly.
                max_imag = -min_imag / 7
            elif -min_imag < step_size:
                # The 0 line is the last step before the bottom.
                # Scale accordingly.
                min_imag = -max_imag / 7
            else:
                # Scale max_imag to be a whole factor of min_imag
                num_min = math.floor(min_imag / step_size * -1)
                num_max = 8 - num_min
                max_imag = num_max * (min_imag / num_min) * -1
        return min_imag, max_imag

    def getImYPosition(self, d: Datapoint) -> int:
        im = self.value(d).imag
        return int(
            self.topMargin
            + (self.max_imag - im) / self.span_imag * self.dim.height
        )

    def getReYPosition(self, d: Datapoint) -> int:
        re = self.value(d).real
        return int(
            self.topMargin
            + (self.max_real - re) / self.span_real * self.dim.height
            if math.isfinite(re)
            else self.topMargin
        )

    def valueAtPosition(self, y) -> list[float]:
        absy = y - self.topMargin
        valRe = -1 * ((absy / self.dim.height * self.span_real) - self.max_real)
        valIm = -1 * ((absy / self.dim.height * self.span_imag) - self.max_imag)
        return [valRe, valIm]

    def zoomTo(self, x1, y1, x2, y2):
        val1 = self.valueAtPosition(y1)
        val2 = self.valueAtPosition(y2)

        if len(val1) == len(val2) == 2 and val1[0] != val2[0]:  # noqa: PLR2004
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

    def getNearestMarker(self, x, y) -> Marker | None:
        if not self.data:
            return None
        shortest = 10e6
        nearest = None
        for m in self.markers:
            mx, _ = self.getPosition(self.data[m.location])
            myr = self.getReYPosition(self.data[m.location])
            myi = self.getImYPosition(self.data[m.location])
            dx = abs(x - mx)
            dy = min(abs(y - myr), abs(y - myi))
            distance = math.sqrt(dx**2 + dy**2)
            if distance < shortest:
                shortest = distance
                nearest = m
        return nearest

    def setMinimumRealValue(self):
        min_val, selected = QtWidgets.QInputDialog.getDouble(
            self,
            "Minimum real value",
            "Set minimum real value",
            value=self.minDisplayReal,
            decimals=2,
        )
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayReal):
            self.minDisplayReal = min_val
        if self.fixedValues:
            self.update()

    def setMaximumRealValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(
            self,
            "Maximum real value",
            "Set maximum real value",
            value=self.maxDisplayReal,
            decimals=2,
        )
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minDisplayReal):
            self.maxDisplayReal = max_val
        if self.fixedValues:
            self.update()

    def setMinimumImagValue(self):
        min_val, selected = QtWidgets.QInputDialog.getDouble(
            self,
            "Minimum imaginary value",
            "Set minimum imaginary value",
            value=self.minDisplayImag,
            decimals=2,
        )
        if not selected:
            return
        if not (self.fixedValues and min_val >= self.maxDisplayImag):
            self.minDisplayImag = min_val
        if self.fixedValues:
            self.update()

    def setMaximumImagValue(self):
        max_val, selected = QtWidgets.QInputDialog.getDouble(
            self,
            "Maximum imaginary value",
            "Set maximum imaginary value",
            value=self.maxDisplayImag,
            decimals=2,
        )
        if not selected:
            return
        if not (self.fixedValues and max_val <= self.minDisplayImag):
            self.maxDisplayImag = max_val
        if self.fixedValues:
            self.update()

    def setFixedValues(self, fixed_values: bool):
        self.fixedValues = fixed_values
        if fixed_values and (
            self.minDisplayReal >= self.maxDisplayReal
            or self.minDisplayImag > self.maxDisplayImag
        ):
            self.fixedValues = False
            self.y_action_automatic.setChecked(True)
            self.y_action_fixed_span.setChecked(False)
        self.update()

    def contextMenuEvent(self, event):
        self.action_set_fixed_start.setText(
            f"Start ({format_frequency_chart(self.minFrequency)})"
        )
        self.action_set_fixed_stop.setText(
            f"Stop ({format_frequency_chart(self.maxFrequency)})"
        )
        self.action_set_fixed_minimum_real.setText(
            f"Minimum R ({self.minDisplayReal})"
        )
        self.action_set_fixed_maximum_real.setText(
            f"Maximum R ({self.maxDisplayReal})"
        )
        self.action_set_fixed_minimum_imag.setText(
            f"Minimum jX ({self.minDisplayImag})"
        )
        self.action_set_fixed_maximum_imag.setText(
            f"Maximum jX ({self.maxDisplayImag})"
        )
        self.menu.exec(event.globalPos())

    def value(self, p: Datapoint) -> complex:
        raise NotImplementedError()
