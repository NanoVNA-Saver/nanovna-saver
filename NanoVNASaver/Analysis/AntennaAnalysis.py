#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
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
    vswr_limit_value = 2.56
    bandwith = 250000

    def runAnalysis(self):
        super().runAnalysis()

        if len(self.minimums) > 1:
            self.layout.addRow("", QtWidgets.QLabel(
                "Not magloop or try to lower VSWR limit"))

        for m in self.minimums[:1]:
            # only one time
            start, lowest, end = m
            if start != end:
                Q = self.app.data11[lowest].freq / \
                    (self.app.data11[end].freq - self.app.data11[start].freq)
                self.layout.addRow(
                    "Q", QtWidgets.QLabel("{}".format(int(Q))))
                self.app.sweep_control.set_start(self.app.data11[start].freq)
                self.app.sweep_control.set_end(self.app.data11[end].freq)
            else:
                self.app.sweep_control.set_start(
                    self.app.data11[start].freq - self.bandwith)
                self.app.sweep_control.set_end(
                    self.app.data11[end].freq + self.bandwith)
