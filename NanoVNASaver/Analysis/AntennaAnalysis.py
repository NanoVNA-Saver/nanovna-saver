#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
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

from PyQt5.Qt import QTimer

'''
Created on May 30th 2020

@author: mauro
'''
import logging

from PyQt5 import QtWidgets

from NanoVNASaver.Analysis.VSWRAnalysis import VSWRAnalysis


logger = logging.getLogger(__name__)


class MagLoopAnalysis(VSWRAnalysis):
    '''
    Find min vswr and change sweep to zoom.
    Useful for tuning magloop.

    '''
    max_dips_shown = 1

    vswr_bandwith_value = 2.56  # -3 dB ?!?
    bandwith = 25000  # 25 kHz

    def __init__(self, app):
        # app.sweep_control.get_start() return -1 ?!?
        # will populate first runAnalysis()
        self.min_freq = None  # app.sweep_control.get_start()
        self.max_freq = None  # app.sweep_control.get_end()
        self.vswr_limit_value = self.vswr_bandwith_value

        super().__init__(app)

    def runAnalysis(self):
        super().runAnalysis()
        new_start = self.app.sweep_control.get_start()
        new_end = self.app.sweep_control.get_end()
        if self.min_freq is None:
            self.min_freq = new_start
            self.max_freq = new_end
            logger.debug("setting hard limits to %s - %s",
                         self.min_freq, self.max_freq)

        if len(self.minimums) > 1:
            self.layout.addRow("", QtWidgets.QLabel(
                "Multiple minimums, not magloop or try to lower VSWR limit"))
            return
        if len(self.minimums) == 1:
            m = self.minimums[0]
            start, lowest, end = m
            if start != end:
                if self.vswr_limit_value == self.vswr_bandwith_value:
                    Q = self.app.data.s11[lowest].freq / \
                        (self.app.data.s11[end].freq -
                         self.app.data.s11[start].freq)
                    self.layout.addRow(
                        "Q", QtWidgets.QLabel("{}".format(int(Q))))
                    new_start = self.app.data.s11[start].freq - self.bandwith
                    new_end = self.app.data.s11[end].freq + self.bandwith
                    logger.debug("Single Spot, new scan on %s-%s",
                                 new_start, new_end)

            else:
                new_start = self.app.data.s11[start].freq - 2 * self.bandwith
                new_end = self.app.data.s11[end].freq + 2 * self.bandwith
                logger.debug(" Zoom to %s-%s", new_start, new_end)

            if self.vswr_limit_value > self.vswr_bandwith_value:
                self.vswr_limit_value = max(
                    self.vswr_bandwith_value, self.vswr_limit_value - 1)
                self.input_vswr_limit.setValue(self.vswr_limit_value)
                logger.debug(
                    "found higher minimum, lowering vswr search to %s", self.vswr_limit_value)
        else:
            new_start = new_start - 5 * self.bandwith
            new_end = new_end + 5 * self.bandwith
            if all((new_start <= self.min_freq,
                    new_end >= self.max_freq)):
                if self.vswr_limit_value < 10:
                    self.vswr_limit_value += 2
                    self.input_vswr_limit.setValue(self.vswr_limit_value)
                    logger.debug(
                        "no minimum found, looking for higher value %s", self.vswr_limit_value)
        new_start = max(self.min_freq, new_start)
        new_end = min(self.max_freq, new_end)
        logger.debug("next search will be %s - %s for vswr %s",
                     new_start,
                     new_end,
                     self.vswr_limit_value)

        self.app.sweep_control.set_start(new_start)
        self.app.sweep_control.set_end(new_end)
        # set timer to let finish all stuff before new sweep
        QTimer.singleShot(2000, self._safe_sweep)

    def _safe_sweep(self):
        '''
        sweep only if button enabled
        to prevent multiple/concurrent sweep
        '''

        if self.app.sweep_control.btn_start.isEnabled():
            self.app.sweep_start()
        else:
            logger.error("sweep alredy running")
