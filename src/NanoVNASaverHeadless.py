from .Hardware import Hardware as hw
from .Hardware.VNA import VNA
from .Calibration import Calibration
from .RFTools import Datapoint
import matplotlib.pyplot as plt
import math

class NanoVNASaverHeadless:
    def __init__(self, vna_index=0, verbose=False):
        self.verbose = verbose
        self.iface = hw.get_interfaces()[vna_index]
        self.vna = hw.get_VNA(self.iface)
        self.calibration = Calibration()
        if self.verbose:
            print("VNA is connected: ", self.vna.connected())
            print("Firmware: ", self.vna.readFirmware())
            print("Features: ", self.vna.read_features())

    def calibrate(self):
        self.wait_for_ans("OPEN")
        data = self.get_data()
        open_dp_list = self.make_datapoint_list(data[4], data[0], data[1])
        self.calibration.insert("open", open_dp_list)

        self.wait_for_ans("SHORT")
        data = self.get_data()
        short_dp_list = self.make_datapoint_list(data[4], data[0], data[1])
        self.calibration.insert("short", short_dp_list)

        self.wait_for_ans("LOAD")
        data = self.get_data()
        load_dp_list = self.make_datapoint_list(data[4], data[0], data[1])
        self.calibration.insert("load", load_dp_list)

        self.wait_for_ans("THROUGH")
        data = self.get_data()
        thru_dp_list = self.make_datapoint_list(data[4], data[2], data[3])
        self.calibration.insert("through", thru_dp_list)

    def set_sweep(self, start, stop):
        self.vna.setSweep(start, stop)
        print("Sweep set from " + str(self.vna.readFrequencies()[0]/1e9) + "e9" + " to " + str(self.vna.readFrequencies()[-1]/1e9) + "e9")

    def stream_data(self):
        data = self.get_data()
        magnList = []
        for re, im in zip(data[0], data[1]):
            magn = (math.sqrt(re**2+im**2))
            magnList.append(magn)
        plt.plot(data[4], magnList)
        plt.show()

    def get_data(self):
        dataS11 = self.vna.readValues("data 0")
        dataS21 = self.vna.readValues("data 1")
        reflRe, reflImag = self.split_data(dataS11)
        thruRe, thruImag = self.split_data(dataS21)
        freq = self.vna.readFrequencies()
        return reflRe, reflImag, thruRe, thruImag, freq
    
    def make_datapoint_list(self, freqList, reList, imList):
        list = []
        for freq, re, im in zip(freqList, reList, imList):
            list.append(Datapoint(freq, re, im))
        return list
    
    def wait_for_ans(self, string):
        while True:
            answer = input("Connect " + string + ": ").lower()
            if answer == 'done':
                print("Proceeding...")
                break
            else:
                print("Invalid input. Please enter 'done' to continue.")

    def split_data(self, data):
        real = []
        imaginary = []
        for item in data:
            values = item.split()
            real.append(float(values[0]))
            imaginary.append(float(values[1]))
        #add exception handling
        return real, imaginary

    def kill(self):
        self.vna.disconnect()
        if self.vna.connected():
            raise Exception("The VNA was not successfully disconnected.")
        else:
            if self.verbose:
                print("Disconnected VNA.")
            return