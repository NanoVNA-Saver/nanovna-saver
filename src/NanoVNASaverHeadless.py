from .Hardware import Hardware as hw
from .Calibration import Calibration
from .CalibrationGuide import CalibrationGuide
from .Touchstone import Touchstone
from .SweepWorker import SweepWorker
import matplotlib.pyplot as plt
import math
from datetime import datetime


class NanoVNASaverHeadless:
    def __init__(self, vna_index=0, verbose=False):
        self.verbose = verbose
        self.iface = hw.get_interfaces()[vna_index]
        self.vna = hw.get_VNA(self.iface)
        self.calibration = Calibration()
        self.touchstone = Touchstone("Save.s2p")  # s2p for two port nanovnas.
        self.worker = SweepWorker(self.vna, self.calibration, self.touchstone, verbose)
        self.CalibrationGuide = CalibrationGuide(self.calibration, self.worker)
        if self.verbose:
            print("VNA is connected: ", self.vna.connected())
            print("Firmware: ", self.vna.readFirmware())
            print("Features: ", self.vna.read_features())

    def calibrate(self, savefile=None, load_file=False):
        if load_file:
            self.CalibrationGuide.loadCalibration(load_file)
            return
        proceed = self.CalibrationGuide.automaticCalibration()
        while proceed:
            proceed = self.CalibrationGuide.automaticCalibrationStep()
        if savefile is None:
            savefile = f"./Calibration_file_{datetime.now()}.s2p"
        self.CalibrationGuide.saveCalibration(savefile)

    def set_sweep(self, start, stop, segments, points):
        self.worker.sweep.update(start, stop, segments, points)
        print(
            "Sweep set from "
            + str(self.worker.sweep.start / 1e9)
            + "e9"
            + " to "
            + str(self.worker.sweep.end  / 1e9)
            + "e9"
        )

    def stream_data(self):
        self.worker.sweep.set_mode("CONTINOUS")
        self.worker.run()
        #await self.loop()
        for i in range (0, 20):
            data = self.get_data()
            print(data[0][30])

    async def loop(self):
        self.worker.sweep.set_mode("CONTINOUS")
        self.worker.run()

    def get_data(self):
        dataS11 = self.worker.data.s11
        dataS21 = self.worker.data.s21
        reflRe = []
        reflIm = []
        thruRe = []
        thruIm = []
        freq = []
        for datapoint in dataS11:
            reflRe.append(datapoint.re)
            reflIm.append(datapoint.im)
            freq.append(datapoint.freq)
        for datapoint in dataS21:
            thruRe.append(datapoint.re)
            thruIm.append(datapoint.im)

        return reflRe, reflIm, thruRe, thruIm, freq


    def kill(self):
        self.vna.disconnect()
        if self.vna.connected():
            raise Exception("The VNA was not successfully disconnected.")
        else:
            if self.verbose:
                print("Disconnected VNA.")
            return
