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

from PyQt5 import QtWidgets, QtGui, QtCore

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Frequency import FrequencyChart
from NanoVNASaver.Charts.LogMag import LogMagChart

import os
import csv

logger = logging.getLogger(__name__)


class CombinedLogMagChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.minDisplayValue = -80
        self.maxDisplayValue = 10

        self.data11: List[Datapoint] = []
        self.data21: List[Datapoint] = []

        self.reference11: List[Datapoint] = []
        self.reference21: List[Datapoint] = []

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.isInverted = False

        self.menu.addSeparator()
        self.expdcsvs11s21 = QtWidgets.QAction("Export S11 and S21 LogMag to CSV")
        self.expdcsvs11s21.triggered.connect(self.exportS11S21ToCSV)
        self.menu.addAction(self.expdcsvs11s21)
        self.exprcsvref1ref2 = QtWidgets.QAction("Export Ref1 and Ref2 LogMag to CSV")
        self.exprcsvref1ref2.triggered.connect(self.exportRef1Ref2ToCSV)
        self.menu.addAction(self.exprcsvref1ref2)

    def exportS11S21ToCSV(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            filter="CSV files (*.csv);;All files (*.*)", initialFilter = 'CSV files (*.csv)')
        if filename:
            f, ext = os.path.splitext(filename)
            if ext!=".csv":
                filename = filename+".csv"
            dd = []
            for i in range (0, len(self.data11)):
                dd.append([self.data11[i].freq, self.data11[i].gain, self.data21[i].gain])
            csv.register_dialect('exppointvirgule', delimiter=';', quoting=csv.QUOTE_NONE)
            myFile = open(filename, 'w')
            with myFile:
                writer = csv.writer(myFile, dialect='exppointvirgule')
                writer.writerows(dd)

    def exportRef1Ref2ToCSV(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            filter="CSV files (*.csv);;All files (*.*)", initialFilter = 'CSV files (*.csv)')
        if filename:
            f, ext = os.path.splitext(filename)
            if ext!=".csv":
                filename = filename+".csv"
            dd = []
            for i in range (0, len(self.reference11)):
                dd.append([self.reference11[i].freq, self.reference11[i].gain, self.reference21[i].gain])
            csv.register_dialect('exppointvirgule', delimiter=';', quoting=csv.QUOTE_NONE)
            myFile = open(filename, 'w')
            with myFile:
                writer = csv.writer(myFile, dialect='exppointvirgule')
                writer.writerows(dd)

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

    # def resetDisplayLimits(self):
    #     # self.reference11 = []
    #     # self.reference21 = []
    #     # self.update()

    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:
        if ((len(self.data11) == 0 and len(self.reference11) == 0) or
                a0.angleDelta().y() == 0):
            a0.ignore()
            return
        do_zoom_x = do_zoom_y = True
        if a0.modifiers() == QtCore.Qt.ShiftModifier:
            do_zoom_x = False
        if a0.modifiers() == QtCore.Qt.ControlModifier:
            do_zoom_y = False
        self._wheel_zomm(a0, do_zoom_x, do_zoom_y)

    def drawChart(self, qp: QtGui.QPainter):
        qp.setPen(QtGui.QPen(Chart.color.text))
        qp.drawText(int(round(self.dim.width / 2)) - 20, 15, self.name + " (dB)")
        qp.drawText(10, 15, "S11")
        qp.drawText(self.leftMargin + self.dim.width - 8, 15, "S21")
        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(self.leftMargin, self.topMargin - 5,
                    self.leftMargin, self.topMargin+self.dim.height+5)
        qp.drawLine(self.leftMargin-5, self.topMargin+self.dim.height,
                    self.leftMargin+self.dim.width, self.topMargin + self.dim.height)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data11) == 0 and len(self.reference11) == 0:
            return
        pen = QtGui.QPen(Chart.color.sweep)
        pen.setWidth(self.dim.point)
        line_pen = QtGui.QPen(Chart.color.sweep)
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
            maxValue = 0
            for d in self.data11:
                logmag = self.logMag(d)
                if math.isinf(logmag):
                    continue
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag
            for d in self.data21:
                logmag = self.logMag(d)
                if math.isinf(logmag):
                    continue
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag

            for d in self.reference11:
                if d.freq < self.fstart or d.freq > self.fstop:
                    continue
                logmag = self.logMag(d)
                if math.isinf(logmag):
                    continue
                if logmag > maxValue:
                    maxValue = logmag
                if logmag < minValue:
                    minValue = logmag
            for d in self.reference21:
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
            y = self.topMargin + round((maxValue - db)/span*self.dim.height)
            qp.setPen(QtGui.QPen(Chart.color.foreground))
            qp.drawLine(self.leftMargin-5, y, self.leftMargin+self.dim.width, y)
            if db > minValue and db != maxValue:
                qp.setPen(QtGui.QPen(Chart.color.text))
                if tick_step < 1:
                    dbstr = str(round(db, 1))
                else:
                    dbstr = str(db)
                qp.drawText(3, y + 4, dbstr)

        qp.setPen(QtGui.QPen(Chart.color.foreground))
        qp.drawLine(self.leftMargin - 5, self.topMargin,
                    self.leftMargin + self.dim.width, self.topMargin)
        qp.setPen(Chart.color.text)
        qp.drawText(3, self.topMargin + 4, str(maxValue))
        qp.drawText(3, self.dim.height+self.topMargin, str(minValue))
        self.drawFrequencyTicks(qp)

        qp.setPen(Chart.color.swr)
        for vswr in self.swrMarkers:
            if vswr <= 1:
                continue
            logMag = 20 * math.log10((vswr-1)/(vswr+1))
            if self.isInverted:
                logMag = logMag * -1
            y = self.topMargin + round((self.maxValue - logMag) /
                                       self.span * self.dim.height)
            qp.drawLine(self.leftMargin, y,
                        self.leftMargin + self.dim.width, y)
            qp.drawText(self.leftMargin + 3, y - 1, "VSWR: " + str(vswr))

        if len(self.data11) > 0:
            c = QtGui.QColor(Chart.color.sweep)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 9, 38, 9)
            c = QtGui.QColor(Chart.color.sweep_secondary)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.dim.width - 20, 9,
                        self.leftMargin + self.dim.width - 15, 9)

        if len(self.reference11) > 0:
            c = QtGui.QColor(Chart.color.reference)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(33, 14, 38, 14)
            c = QtGui.QColor(Chart.color.reference_secondary)
            c.setAlpha(255)
            pen = QtGui.QPen(c)
            pen.setWidth(2)
            qp.setPen(pen)
            qp.drawLine(self.leftMargin + self.dim.width - 20, 14,
                        self.leftMargin + self.dim.width - 15, 14)

        self.drawData(qp, self.data11, Chart.color.sweep)
        self.drawData(qp, self.data21, Chart.color.sweep_secondary)
        self.drawData(qp, self.reference11, Chart.color.reference)
        self.drawData(qp, self.reference21, Chart.color.reference_secondary)
        self.drawMarkers(qp, data=self.data11)
        self.drawMarkers(qp, data=self.data21)

    def getYPosition(self, d: Datapoint) -> int:
        logMag = self.logMag(d)
        if math.isinf(logMag):
            return None
        return self.topMargin + round((self.maxValue - logMag) / self.span * self.dim.height)

    def valueAtPosition(self, y) -> List[float]:
        absy = y - self.topMargin
        val = -1 * ((absy / self.dim.height * self.span) - self.maxValue)
        return [val]

    def logMag(self, p: Datapoint) -> float:
        if self.isInverted:
            return -p.gain
        return p.gain

    def copy(self):
        new_chart: LogMagChart = super().copy()
        new_chart.isInverted = self.isInverted
        new_chart.span = self.span
        new_chart.data11 = self.data11
        new_chart.data21 = self.data21
        new_chart.reference11 = self.reference11
        new_chart.reference21 = self.reference21
        return new_chart
