'''
Created on 30 giu 2020

@author: mauro
'''

from PyQt5 import QtWidgets, QtTest
import logging
import math

from NanoVNASaver.Analysis import Analysis

from NanoVNASaver.Hardware import VNA

import numpy as np
from NanoVNASaver.Marker import Marker
from NanoVNASaver import RFTools
from NanoVNASaver.Analysis.VSWRAnalysis import VSWRAnalysis
from NanoVNASaver.Formatting import format_frequency_sweep



logger = logging.getLogger(__name__)


class Antenna(object):

    @staticmethod
    def group_consecutives(vals, step=1):
        """
        https://stackoverflow.com/questions/7352684/how-to-find-the-groups-of-consecutive-elements-from-an-array-in-numpy

        Return list of consecutive lists of numbers from vals (number list).
        :param vals:
        :param step:
        """
        run = []
        result = [run]
        expect = None
        for v in vals:
            if (v == expect) or (expect is None):
                run.append(v)
            else:
                run = [v]
                result.append(run)
            expect = v + step
        return result

    @classmethod
    def analyze(cls, frequencies, values, FIELD_NAME, step=5000, vuoto=False):
        '''
        dati dati, prova a trovare minimi e bands passanti
        :param cls:
        '''

        if FIELD_NAME == "rl":
            BAND_THRESHOLD = -7.0
            MIN_CALCOLO_Q = -27

        elif FIELD_NAME == "vswr":
            BAND_THRESHOLD = 2.62
            MIN_CALCOLO_Q = 1.1
        else:
            raise ValueError("unknown threshold for {}".format(FIELD_NAME))

        bands_raw = np.where(values < BAND_THRESHOLD)[0]

        # raggruppo posizioni in cui il valore è sotto la soglia
        bands = cls.group_consecutives(bands_raw)
        # print("raggruppate in ", bands)
        out = []
        # print "bands", bands
        banda_dict = None
        for band in bands:
            if band:

                print("band ", band)
                fmin = frequencies[band[0]]

                fmax = frequencies[band[-1]]
                estensione = fmax - fmin
                x = np.argmin(values[band[0]:band[-1] + 1])
                prog = x + band[0]
                min_val = values[prog]

                if banda_dict:
                    salto = fmin - banda_dict["fmax"]
                    if salto < (10 * step):
                        logger.warning("unisco band e proseguo")
                        if min_val < banda_dict["min"]:
                            logger.debug("aggiusto nuovo minimo, da %s a %s",
                                         banda_dict["min"], min_val)
                            banda_dict["min"] = min_val
                            # invalido eventuale Q e band passante ?!?
                            banda_dict["q"] = None
                            banda_dict["banda_passante"] = None
                        banda_dict["fmax"] = fmax
                        # non servono ulteriori elaborazioni
                        continue

                    else:
                        logger.warning("finalizzo band precedente")
                        out.append(banda_dict)
                        banda_dict = None
                # se sono qui è nuova

                if estensione == 0 and vuoto:
                    logger.warning("ritorno minima estensione")
                    banda_dict = {"fmin": fmin - 30 * step,
                                  "fmax": fmin + 30 * step,
                                  "banda_passante": None,
                                  "q": None,
                                  "min":  min_val,
                                  "freq": fmin,
                                  "prog": prog,
                                  }
                else:
                    logger.warning("Nuova band")
                    if min_val <= MIN_CALCOLO_Q:

                        # FIXME: verificare che ci siano valori >
                        # BAND_THRESHOLD?!?
                        q = np.sqrt(fmax * fmin) / (fmax - fmin)
                        logger.info("Q=%s", q)
                    else:
                        logger.info(
                            "non calcolo Q perchè minimo %s non è abbastanza", min_val)
                        q = None
                    banda_dict = {"fmin": fmin,
                                  "fmax": fmax,
                                  "banda_passante": fmax - fmin,
                                  "q": q,
                                  "min":  min_val,
                                  "freq": frequencies[prog],
                                  "prog": prog,
                                  }

        if banda_dict:
            out.append(banda_dict)
        return out

class ChartFactory(object):
    
    @classmethod
    def NewChart(cls, chart_class, name, app):
        from NanoVNASaver.NanoVNASaver import BandsModel
        new_chart = chart_class(name)
        new_chart.isPopout = True
        new_chart.data = app.data
        new_chart.bands = BandsModel()
        i=0
        default_color = app.default_marker_colors[i]
        color = app.settings.value("Marker" + str(i+1) + "Color", default_color)
        marker = Marker("Marker " + str(i+1), color)
        marker.isMouseControlledRadioButton.setChecked(True)
        new_chart.setMarkers([marker])
        
        return new_chart
        
class MinVswrAnalysis(Antenna, Analysis):

    def __init__(self, app):
        super().__init__(app)
        self._widget = QtWidgets.QWidget()

    def runAnalysis(self):
        self.reset()

        if len(self.app.data) == 0:
            logger.debug("No data to analyse")
            self.result_label.setText("No data to analyse.")
            return

        frequencies = []
        values = []
        for p in self.app.data:
            frequencies.append(p.freq)
            vswr = p.vswr
            values.append(vswr)

        res = self.analyze(np.array(frequencies),
                           np.array(values),
                           "vswr")
        marker = 0
        for banda in res:
            if marker < 3:
                self.app.markers[marker].setFrequency(
                    str(round(banda["freq"])))
                marker += 1
            print("min {min}  a {freq}".format(**banda))

        # Charts
        progr = 0
        for c in self.app.subscribing_charts:
            if c.name == "S11 VSWR":
                new_chart = c.copy()
                new_chart.isPopout = True
                new_chart.show()
                new_chart.setWindowTitle("%s %s" % (new_chart.name, progr))

        vna = self.app.vna
        if isinstance(vna, InvalidVNA):
            logger.warning("end analysis, non valid vna")
        else:
            logger.warning("band zoom")
            for banda in res:
                progr += 1
                # scan
                self.app.sweepStartInput.setText(str(banda["fmin"]))
                self.app.sweepEndInput.setText(str(banda["fmax"]))
                self.app.sweep()
                while not self.app.btnSweep.isEnabled():
                    QtTest.QTest.qWait(500)
                for c in self.app.subscribing_charts:
                    if c.name == "S11 VSWR":
                        new_chart = c.copy()
                        new_chart.isPopout = True
                        new_chart.show()
                        new_chart.setWindowTitle("%s %s" % (new_chart.name, progr))


class ZeroCrossAnalysis(Antenna, Analysis):

    def __init__(self, app):
        super().__init__(app)
        self._widget = QtWidgets.QWidget()

    def runAnalysis(self):
        self.reset()

        if len(self.app.data) == 0:
            logger.debug("No data to analyse")
            self.result_label.setText("No data to analyse.")
            return

        frequencies = []
        values = []
        for p in self.app.data:

            frequencies.append(p.freq)

            values.append(p.z.imag)

        zero_crossings = np.where(np.diff(np.sign(np.array(values))))[0]

        marker = 0
        for pos in zero_crossings:
            freq = round(frequencies[pos])
            if marker < 3:
                self.app.markers[marker].setFrequency(
                    str(freq))
                marker += 1
            print("cross at {}".format(freq))

class MagLoopAnalysis(VSWRAnalysis):
    max_dips_shown = 1
    vswr_limit_value = 2.56

    def runAnalysis(self):

        super().runAnalysis()

        for m in self.minimums:
                start, lowest, end = m
                if start != end:
                    Q = self.app.data[lowest].freq/(self.app.data[end].freq-self.app.data[start].freq)
                    self.layout.addRow("Q",QtWidgets.QLabel("{}".format(int(Q))))
                    self.app.sweepStartInput.setText(self.app.data[start].freq)
                    self.app.sweepEndInput.setText(self.app.data[end].freq)
                    # self.app.sweepEndInput.textEdited.emit(self.app.sweepEndInput.text())
                    
