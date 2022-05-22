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

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Charts.Chart import Chart
from NanoVNASaver.Charts.Frequency import FrequencyChart

import os
import csv

logger = logging.getLogger(__name__)


class LogMagChart(FrequencyChart):
    def __init__(self, name=""):
        super().__init__(name)

        self.name_unit = "dB"

        self.minDisplayValue = -80
        self.maxDisplayValue = 10

        self.minValue = 0
        self.maxValue = 1
        self.span = 1

        self.isInverted = False
 
        self.menu.addSeparator()
        self.expdcsvdat = QtWidgets.QAction("Export S11 Return Loss to CSV")
        self.expdcsvdat.triggered.connect(self.exportDataToCSV)
        self.menu.addAction(self.expdcsvdat)
        self.exprcsvref = QtWidgets.QAction("Export reference Return Loss to CSV")
        self.exprcsvref.triggered.connect(self.exportReferenceToCSV)
        self.menu.addAction(self.exprcsvref)
        self.menu.addSeparator()
        self.impdcsvdat = QtWidgets.QAction("Import S11 Return Loss from CSV")
        self.impdcsvdat.triggered.connect(self.importDataFromCSV)
        self.menu.addAction(self.impdcsvdat)

    def importDataFromCSV(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="CSV files (*.csv);;All files (*.*)", initialFilter = 'CSV files (*.csv)')
        if filename:
            ref: List[Datapoint] = []
            with open(filename, newline='') as csvfile:
                spamreader = csv.reader(csvfile, delimiter=',')
                for row in spamreader:
                    try :
                        f = int(float(row[0])*1000000000.0)
                        re = math.pow(10,float(row[1])/20)
                        ref.append(Datapoint(f, re, 0))
                    except :
                        pass
            self.reference = ref
            self.update()

    def exportDataToCSV(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            filter="CSV files (*.csv);;All files (*.*)", initialFilter = 'CSV files (*.csv)')
        if filename:
            f, ext = os.path.splitext(filename)
            if ext!=".csv":
                filename = filename+".csv"
            dd = []
            for p in self.data:
                dd.append([p.freq, p.gain])
            csv.register_dialect('exppointvirgule', delimiter=';', quoting=csv.QUOTE_NONE)
            myFile = open(filename, 'w')
            with myFile:
                writer = csv.writer(myFile, dialect='exppointvirgule')
                writer.writerows(dd)

    def exportReferenceToCSV(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            filter="CSV files (*.csv);;All files (*.*)", initialFilter = 'CSV files (*.csv)')
        if filename:
            f, ext = os.path.splitext(filename)
            if ext!=".csv":
                filename = filename+".csv"
            dd = []
            for p in self.reference:
                dd.append([p.freq, p.gain])
            csv.register_dialect('exppointvirgule', delimiter=';', quoting=csv.QUOTE_NONE)
            myFile = open(filename, 'w')
            with myFile:
                writer = csv.writer(myFile, dialect='exppointvirgule')
                writer.writerows(dd)

    def drawValues(self, qp: QtGui.QPainter):
        if len(self.data) == 0 and len(self.reference) == 0:
            return

        self._set_start_stop()

        # Draw bands if required
        if self.bands.enabled:
            self.drawBands(qp, self.fstart, self.fstop)

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
            y = self.topMargin + round((self.maxValue - logMag) / self.span * self.dim.height)
            qp.drawLine(self.leftMargin, y, self.leftMargin + self.dim.width, y)
            qp.drawText(self.leftMargin + 3, y - 1, "VSWR: " + str(vswr))
        
        self.drawData(qp, self.data, Chart.color.sweep)
        self.drawData(qp, self.reference, Chart.color.reference)
        self.drawMarkers(qp)

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
        return new_chart
