'''
Created on 30 giu 2020

@author: mauro
'''

from PyQt5 import QtWidgets
import logging
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
                Q = self.app.data[lowest].freq / \
                    (self.app.data[end].freq - self.app.data[start].freq)
                self.layout.addRow(
                    "Q", QtWidgets.QLabel("{}".format(int(Q))))
                self.app.sweepStartInput.setText(self.app.data[start].freq)
                self.app.sweepStartInput.textEdited.emit(
                    self.app.sweepStartInput.text())
                self.app.sweepEndInput.setText(self.app.data[end].freq)
                self.app.sweepEndInput.textEdited.emit(
                    self.app.sweepEndInput.text())
            else:
                self.app.sweepStartInput.setText(
                    self.app.data[start].freq - self.bandwith)
                self.app.sweepStartInput.textEdited.emit(
                    self.app.sweepStartInput.text())
                self.app.sweepEndInput.setText(
                    self.app.data[end].freq + self.bandwith)
                self.app.sweepEndInput.textEdited.emit(
                    self.app.sweepEndInput.text())
