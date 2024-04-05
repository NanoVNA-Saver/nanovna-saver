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
        pass

    def set_sweep(self):
        pass

    def stream_data(self):
        pass

    def kill(self):
        self.vna.disconnect()
        if self.vna.connected():
            raise Exception("The VNA was not successfully disconnected.")
        else:
            if self.verbose:
                print("Disconnected VNA.")
            return