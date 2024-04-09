from .Hardware import Hardware as hw
from .Hardware.VNA import VNA


class NanoVNASaverHeadless:
    def __init__(self, vna_index=0, verbose=False):
        self.verbose = verbose
        self.iface = hw.get_interfaces()[vna_index]
        self.vna = hw.get_VNA(self.iface)
        if self.verbose:
            print("VNA is connected: ", self.vna.connected())
            print("Firmware: ", self.vna.readFirmware())
            print("Features: ", self.vna.read_features())

    def calibrate(self):
        print(str(self.vna.getCalibration()))

    def set_sweep(self, start, stop):
        self.vna.setSweep(start, stop)
        print(
            "Sweep set from "
            + str(self.vna.readFrequencies()[0] / 1e9)
            + "e9"
            + " to "
            + str(self.vna.readFrequencies()[-1] / 1e9)
            + "e9"
        )

    def stream_data(self):
        data = self.get_data()
        pass

    def get_data(self):
        dataS11 = self.vna.readValues("data 0")
        dataS21 = self.vna.readValues("data 1")
        reflRe, reflImag = self.split_data(dataS11)
        thruRe, thruImag = self.split_data(dataS21)
        return reflRe, reflImag, thruRe, thruImag

    def split_data(self, data):
        real = []
        imaginary = []
        for item in data:
            values = item.split()
            real.append(float(values[0]))
            imaginary.append(float(values[1]))
        # add exception handling
        return real, imaginary

    def kill(self):
        self.vna.disconnect()
        if self.vna.connected():
            raise Exception("The VNA was not successfully disconnected.")
        else:
            if self.verbose:
                print("Disconnected VNA.")
            return
